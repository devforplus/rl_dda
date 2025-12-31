"""
실제 게임 환경에서 동작하는 PPO 에이전트
3가지 학습 모드 지원: survival (생존 극한), balanced (균형), attack (공격 극한)
각 모드에서 skill은 0.1에서 1.0까지 선형으로 증가
"""

import numpy as np
import torch
import os
import sys
import time
import pyxel as px
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime
from rl import PPOAgent, GameEnvironment, TRAINING_MODES
import input as input_module

# GUI 없는 환경에서도 그래프 저장이 가능하도록 설정
matplotlib.use("Agg")

# 기본 학습 설정
DEFAULT_START_SKILL = 0.1
DEFAULT_END_SKILL = 1.0


class RealGamePPOAgent:
    """실제 게임과 연동되는 PPO 에이전트"""
    
    def __init__(
        self,
        ppo_agent: PPOAgent,
        env: GameEnvironment,
        skill_level: float = 0.5,
        random_mode: bool = False
    ):
        """
        RealGamePPOAgent 초기화
        
        Args:
            ppo_agent: PPOAgent 인스턴스
            env: GameEnvironment 인스턴스
            skill_level: 스킬 레벨 (0.0-1.0, 랜덤 모드에서 사용)
            random_mode: True면 완전 랜덤 액션 선택, False면 PPO 에이전트 사용
        """
        self.ppo_agent = ppo_agent
        self.env = env
        self.skill_level = skill_level
        self.random_mode = random_mode
        
        self.app = None
        self.game = None
        self.game_state = None
        
        # 리워드 추적
        self.prev_score = 0
        self.prev_lives = 3
        self.current_steps = 0
    
    def connect_game(self, app):
        """
        게임 인스턴스와 연결
        
        Args:
            app: App 또는 BenchmarkApp 인스턴스
        """
        self.app = app
        self.game = app.game
        # 게임 상태는 update 시점에 동적으로 가져옴
    
    def _get_current_game_state(self):
        """현재 게임 상태 가져오기"""
        if self.game is None:
            return None
        
        # GameStateStage 찾기
        if hasattr(self.game, 'state'):
            state = self.game.state
            # GameStateStage인지 확인
            if hasattr(state, 'player') and hasattr(state, 'enemies'):
                # 게임이 PLAY 상태 또는 GAME_OVER 상태일 때도 
                # 마지막 보상 계산을 위해 가져옴
                return state
        
        return None
    
    def select_action(self) -> int:
        """
        현재 상태에서 액션 선택 및 적용
        
        Returns:
            action: 선택된 액션 인덱스
        """
        self.game_state = self._get_current_game_state()
        
        if self.game_state is None or self.app is None:
            return 0
        
        # 상태 관찰
        state = self.env.get_state(self.game_state, self.skill_level, self.current_steps)
        
        # 액션 선택
        if self.random_mode:
            # 완전 랜덤 모드
            action = np.random.randint(0, self.ppo_agent.action_size)
        else:
            # PPO 에이전트 사용 (초기화된 가중치)
            action, log_prob, value = self.ppo_agent.select_action(state, deterministic=False)
            
            # 스텝 카운트 증가
            self.current_steps += 1
            
            # 경험 저장 (학습용)
            reward = self.env.get_reward(
                self.game_state, 
                self.skill_level, 
                self.current_steps, 
                self.prev_score
            )
            
            done = False
            if hasattr(self.game_state, 'state'):
                from game_state_stage import State
                if self.game_state.state == State.GAME_OVER:
                    done = True
            
            self.ppo_agent.store_transition(state, action, reward, log_prob, done, value)
            
            # 점수 업데이트
            if hasattr(self.game_state, 'game') and hasattr(self.game_state.game, 'game_vars'):
                self.prev_score = self.game_state.game.game_vars.score
            
            # 에피소드 종료 시 리셋
            if done:
                # 에피소드 종료 시에는 리셋하지 않음 (handle_episode_end에서 처리)
                pass
        
        # 액션 적용
        if self.app.input is not None:
            self.env.apply_action(action, self.app.input)
        
        return action
    
    def update_policy(self, next_state: np.ndarray = None):
        """정책 업데이트 (학습)"""
        if not self.random_mode:
            next_value = 0.0
            if next_state is not None:
                next_state_tensor = torch.FloatTensor(next_state).unsqueeze(0).to(self.ppo_agent.device)
                with torch.no_grad():
                    _, next_value_tensor = self.ppo_agent.policy(next_state_tensor)
                    next_value = next_value_tensor.cpu().item()
            
            self.ppo_agent.update(next_value)


class CurriculumTrainer:
    """순수 이산적 커리큘럼 러닝 기반 학습 관리자
    
    skill을 0.1 단위로 10단계(0.1, 0.2, ..., 1.0)로 나누어
    각 단계에서 해당 skill을 고정하고 일정 에피소드 동안 학습합니다.
    
    학습 구조:
    - Stage 1:  skill=0.1 고정, 목표  300 스텝
    - Stage 2:  skill=0.2 고정, 목표  433 스텝
    - Stage 3:  skill=0.3 고정, 목표  567 스텝
    - ...
    - Stage 10: skill=1.0 고정, 목표 1500 스텝
    
    특징:
    - 쉬운 목표(낮은 skill)부터 점진적으로 어려운 목표로 학습
    - 각 단계에서 해당 skill만 집중 학습
    - 단계별 체크포인트 저장
    """
    
    def __init__(
        self, 
        agent: RealGamePPOAgent, 
        training_mode: str = "balanced",
        save_dir: str = "models", 
        total_episodes: int = 2000
    ):
        self.agent = agent
        self.training_mode = training_mode
        self.total_episodes = total_episodes
        
        # 모드별 저장 디렉토리 분리
        self.save_dir = os.path.join(save_dir, training_mode)
        if not os.path.exists(self.save_dir):
            os.makedirs(self.save_dir)
            
        # 성능 추적 (시각화용)
        self.episode_rewards = []
        self.episode_lengths = []  # 생존 시간
        self.episode_kills = []    # 킬 수 (점수/100)
        self.episode_skills = []   # 스킬 레벨 추적
        self.best_survival = 0
        self.best_score = 0
        self.best_kills = 0
        
        # 이산적 커리큘럼 설정 (0.1 단위, 10단계)
        self.start_skill = DEFAULT_START_SKILL
        self.end_skill = DEFAULT_END_SKILL
        self.skill_step = 0.1
        self.num_stages = int((self.end_skill - self.start_skill) / self.skill_step) + 1  # 10단계
        self.episodes_per_stage = total_episodes // self.num_stages
        
        # 현재 단계 추적
        self.current_stage = 0  # 0-indexed (0 = skill 0.1, 9 = skill 1.0)
        self.stage_episode_count = 0
        
    def record_episode(self, reward: float, length: int, kills: int, skill: float):
        """에피소드 데이터 기록
        
        Args:
            reward: 에피소드 총 보상 (점수)
            length: 생존 시간 (스텝)
            kills: 처치한 적 수 (점수/100)
            skill: 현재 스킬 레벨
        """
        self.episode_rewards.append(reward)
        self.episode_lengths.append(length)
        self.episode_kills.append(kills)
        self.episode_skills.append(skill)

    def get_current_stage_skill(self) -> float:
        """현재 단계의 skill 값 반환"""
        return self.start_skill + self.current_stage * self.skill_step
    
    def get_skill_for_episode(self, episode: int) -> float:
        """순수 이산적 커리큘럼 러닝
        
        각 단계에서 해당 skill 값만 고정으로 사용합니다.
        
        Stage 1: skill = 0.1 (고정)
        Stage 2: skill = 0.2 (고정)
        ...
        Stage 10: skill = 1.0 (고정)
        
        Args:
            episode: 현재 에피소드 번호 (사용하지 않음)
            
        Returns:
            skill_level: 현재 단계의 고정 skill 값
        """
        return self.get_current_stage_skill()

    def update_skill_by_episode(self, current_episode: int):
        """이산적 커리큘럼: 단계별 skill 업데이트"""
        self.stage_episode_count += 1
        
        # 단계 전환 체크
        if self.stage_episode_count >= self.episodes_per_stage:
            if self.current_stage < self.num_stages - 1:
                # 현재 단계 완료, 다음 단계로 진행
                self.current_stage += 1
                self.stage_episode_count = 0
                new_max_skill = self.get_current_stage_skill()
                
                print(f"\n{'='*60}")
                print(f"🎓 커리큘럼 단계 {self.current_stage + 1}/{self.num_stages} 진입!")
                print(f"   현재 Skill: {new_max_skill:.1f}")
                
                # 모드별 목표 표시
                if self.training_mode == "attack":
                    target_kills = int(new_max_skill * 10)  # skill * 10 킬 목표
                    print(f"   목표 킬: {target_kills} 킬")
                elif self.training_mode == "balanced":
                    target_survival = int(300 + (new_max_skill - 0.1) * 1333.33)
                    target_kills = int(new_max_skill * 10)
                    print(f"   목표 생존: {target_survival} 스텝 | 목표 킬: {target_kills}")
                else:  # survival
                    target_survival = int(300 + (new_max_skill - 0.1) * 1333.33)
                    print(f"   목표 생존 시간: {target_survival} 스텝")
                print(f"{'='*60}\n")
                
                # 단계별 체크포인트 저장
                self.agent.ppo_agent.save(
                    os.path.join(self.save_dir, f"ppo_{self.training_mode}_stage_{self.current_stage + 1}.pth")
                )
                self.plot_progress()
        
        # 현재 에피소드의 skill 결정
        new_skill = self.get_skill_for_episode(current_episode)
        self.agent.skill_level = new_skill

    def plot_progress(self):
        """학습 진행 상황 그래프 생성 (모드별 다른 지표 표시)
        
        - survival 모드: 보상, 생존시간, 스킬
        - attack 모드: 보상, 킬 수, 스킬
        - balanced 모드: 보상, 생존시간+킬수, 스킬
        """
        if not self.episode_rewards:
            return
            
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 10))
        
        # 1. 보상 그래프 (공통)
        ax1.plot(self.episode_rewards, alpha=0.3, color='blue', label='Reward')
        if len(self.episode_rewards) >= 10:
            avg_rewards = np.convolve(self.episode_rewards, np.ones(10)/10, mode='valid')
            ax1.plot(range(9, len(self.episode_rewards)), avg_rewards, color='blue', linewidth=2, label='MA(10)')
        ax1.set_title(f'Training Progress - Reward (Mode: {self.training_mode})')
        ax1.set_xlabel('Episode')
        ax1.set_ylabel('Score')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 모드별 핵심 지표 그래프
        if self.training_mode == "attack":
            # Attack 모드: 킬 수 그래프
            ax2.plot(self.episode_kills, alpha=0.3, color='red', label='Kills')
            if len(self.episode_kills) >= 10:
                avg_kills = np.convolve(self.episode_kills, np.ones(10)/10, mode='valid')
                ax2.plot(range(9, len(self.episode_kills)), avg_kills, color='darkred', linewidth=2, label='MA(10)')
            ax2.set_title('Training Progress - Kills (Attack Mode)')
            ax2.set_xlabel('Episode')
            ax2.set_ylabel('Kills')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            
        elif self.training_mode == "balanced":
            # Balanced 모드: 생존시간과 킬 수 동시 표시 (이중 Y축)
            ax2.plot(self.episode_lengths, alpha=0.3, color='green', label='Survival Steps')
            if len(self.episode_lengths) >= 10:
                avg_lengths = np.convolve(self.episode_lengths, np.ones(10)/10, mode='valid')
                ax2.plot(range(9, len(self.episode_lengths)), avg_lengths, color='green', linewidth=2, label='Survival MA(10)')
            ax2.set_xlabel('Episode')
            ax2.set_ylabel('Steps', color='green')
            ax2.tick_params(axis='y', labelcolor='green')
            
            # 두 번째 Y축 (킬 수)
            ax2_twin = ax2.twinx()
            ax2_twin.plot(self.episode_kills, alpha=0.3, color='red', label='Kills')
            if len(self.episode_kills) >= 10:
                avg_kills = np.convolve(self.episode_kills, np.ones(10)/10, mode='valid')
                ax2_twin.plot(range(9, len(self.episode_kills)), avg_kills, color='darkred', linewidth=2, label='Kills MA(10)')
            ax2_twin.set_ylabel('Kills', color='red')
            ax2_twin.tick_params(axis='y', labelcolor='red')
            
            ax2.set_title('Training Progress - Survival & Kills (Balanced Mode)')
            # 범례 통합
            lines1, labels1 = ax2.get_legend_handles_labels()
            lines2, labels2 = ax2_twin.get_legend_handles_labels()
            ax2.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
            ax2.grid(True, alpha=0.3)
            
        else:
            # Survival 모드: 생존 시간 그래프
            ax2.plot(self.episode_lengths, alpha=0.3, color='green', label='Survival Steps')
            if len(self.episode_lengths) >= 10:
                avg_lengths = np.convolve(self.episode_lengths, np.ones(10)/10, mode='valid')
                ax2.plot(range(9, len(self.episode_lengths)), avg_lengths, color='green', linewidth=2, label='MA(10)')
            ax2.set_title('Training Progress - Survival Time')
            ax2.set_xlabel('Episode')
            ax2.set_ylabel('Steps')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
        
        # 3. 스킬 레벨 진행 그래프 (커리큘럼 단계 표시)
        if self.episode_skills:
            ax3.scatter(range(len(self.episode_skills)), self.episode_skills, 
                       alpha=0.3, s=2, color='red', label='Skill (per episode)')
            
            # 단계 경계선 표시
            for stage in range(1, self.num_stages):
                boundary = stage * self.episodes_per_stage
                if boundary < len(self.episode_skills):
                    ax3.axvline(x=boundary, color='blue', linestyle='--', alpha=0.3)
            
            # 각 단계의 최대 skill 표시
            if len(self.episode_skills) >= 10:
                avg_skills = np.convolve(self.episode_skills, np.ones(10)/10, mode='valid')
                ax3.plot(range(9, len(self.episode_skills)), avg_skills, 
                        color='darkred', linewidth=2, label='MA(10)')
            
            ax3.set_title(f'Curriculum Learning - Skill Progression ({self.num_stages} Stages)')
            ax3.set_xlabel('Episode')
            ax3.set_ylabel('Skill')
            ax3.set_ylim(0, 1.1)
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = os.path.join(self.save_dir, f"training_progress_{self.training_mode}.png")
        plt.savefig(plot_path)
        plt.close()

    def check_curriculum_advance(self, survival_time: int, score: int):
        """선형 커리큘럼에서는 사용하지 않음 (호환성 유지)"""
        pass

    def save_checkpoint(self, is_best=False):
        """모델 저장 (모드명 포함)"""
        try:
            if not os.path.exists(self.save_dir):
                os.makedirs(self.save_dir, exist_ok=True)
                
            path = os.path.join(self.save_dir, f"ppo_{self.training_mode}_latest.pth")
            self.agent.ppo_agent.save(path)
            if is_best:
                best_path = os.path.join(self.save_dir, f"ppo_{self.training_mode}_best.pth")
                self.agent.ppo_agent.save(best_path)
        except Exception as e:
            print(f"⚠️ 모델 저장 실패: {e}")


# Pyxel 앱을 상속받아 학습용 환경 구현
class TrainingApp:
    def __init__(self, agent: RealGamePPOAgent, training_mode: str = "balanced", speed=9, total_episodes=2000):
        from const import APP_WIDTH, APP_HEIGHT, APP_NAME, APP_FPS, \
            APP_DISPLAY_SCALE, APP_CAPTURE_SCALE, APP_GFX_FILE, PALETTE, SOUNDS_RES_FILE
        from game import Game
        from input import Input
        from monospace_bitmap_font import MonospaceBitmapFont
        
        self.agent = agent
        self.speed = speed
        self.total_episodes = total_episodes
        self.training_mode = training_mode
        self.trainer = CurriculumTrainer(
            agent, 
            training_mode=training_mode,
            total_episodes=total_episodes
        )
        
        px.init(
            APP_WIDTH, APP_HEIGHT, 
            title=f"{APP_NAME} - Training (x{speed})",
            fps=APP_FPS,
            display_scale=APP_DISPLAY_SCALE,
            capture_scale=APP_CAPTURE_SCALE
        )
        px.colors.from_list(PALETTE)
        
        # 에셋 로드 (src/assets 기준)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.join(current_dir, "assets")
        px.images[0].load(0, 0, os.path.join(assets_dir, APP_GFX_FILE))
        
        self.main_font = MonospaceBitmapFont()
        self.input = Input()
        self.game = Game(self)
        self.game.go_to_new_game()
        self.agent.connect_game(self)
        
        self.episode_count = 0
        self.total_steps = 0
        
        px.run(self.update, self.draw)

    def update(self):
        for _ in range(self.speed):
            # 게임 업데이트 (키보드 입력 처리)
            self.input.update()
            
            # 에이전트 액션 결정 및 Input 객체 강제 수정
            self.agent.select_action()
            
            # 게임 상태 업데이트 (수정된 Input 반영)
            self.game.update()
            
            self.total_steps += 1
            
            # 게임 오버 체크
            from game_state_stage import State
            if hasattr(self.game.state, 'state') and self.game.state.state == State.GAME_OVER:
                self.handle_episode_end()
                break
        
        # 학습 업데이트 (배치 사이즈마다)
        if len(self.agent.ppo_agent.states) >= self.agent.ppo_agent.batch_size:
            # 현재 상태를 next_state로 전달하여 가치 추정치 계산
            current_game_state = self.agent._get_current_game_state()
            next_state = self.agent.env.get_state(current_game_state, self.agent.skill_level, self.agent.current_steps)
            self.agent.update_policy(next_state)

    def handle_episode_end(self):
        self.episode_count += 1
        survival_time = self.agent.current_steps
        score = self.agent.prev_score
        kills = score // 100  # 100점당 1킬
        current_skill = self.agent.skill_level
        
        # 에피소드 데이터 기록 (킬 수 포함)
        self.trainer.record_episode(score, survival_time, kills, current_skill)
        
        # 모드별 로그 출력
        if self.training_mode == "attack":
            # Attack 모드: 킬 수 중심
            target_kills = int(current_skill * 10)  # 목표 킬 수 (예시)
            print(f"🎬 Ep {self.episode_count}/{self.total_episodes} | "
                  f"Mode: ATTACK | "
                  f"킬: {kills} (목표: {target_kills}) | 생존: {survival_time} | Skill: {current_skill:.2f}")
        elif self.training_mode == "balanced":
            # Balanced 모드: 둘 다 표시
            print(f"🎬 Ep {self.episode_count}/{self.total_episodes} | "
                  f"Mode: BALANCED | "
                  f"생존: {survival_time} | 킬: {kills} | Skill: {current_skill:.2f}")
        else:
            # Survival 모드: 생존 시간 중심
            from rl import get_survival_target_steps
            target_survival = int(get_survival_target_steps(current_skill))
            print(f"🎬 Ep {self.episode_count}/{self.total_episodes} | "
                  f"Mode: SURVIVAL | "
                  f"생존: {survival_time} (목표: {target_survival}) | 킬: {kills} | Skill: {current_skill:.2f}")
        
        # 선형 스킬 업데이트
        self.trainer.update_skill_by_episode(self.episode_count)
        
        # 학습 종료 체크
        if self.episode_count >= self.total_episodes:
            print("🏁 전체 학습 종료!")
            self.trainer.plot_progress() # 최종 그래프 생성
            self.trainer.save_checkpoint()
            px.quit()
            return
            
        # 베스트 갱신 체크 (모드별 핵심 지표 기준)
        is_best = False
        
        if self.training_mode == "attack":
            # Attack 모드: 킬 수 기준
            if kills > self.trainer.best_kills:
                self.trainer.best_kills = kills
                is_best = True
        elif self.training_mode == "balanced":
            # Balanced 모드: 생존 또는 킬 중 하나라도 갱신
            if survival_time > self.trainer.best_survival:
                self.trainer.best_survival = survival_time
                is_best = True
            if kills > self.trainer.best_kills:
                self.trainer.best_kills = kills
                is_best = True
        else:
            # Survival 모드: 생존 시간 기준
            if survival_time > self.trainer.best_survival:
                self.trainer.best_survival = survival_time
                is_best = True
        
        # 점수는 항상 추적
        if score > self.trainer.best_score:
            self.trainer.best_score = score
            
        if self.episode_count % 10 == 0:
            self.trainer.save_checkpoint(is_best)
            
        # 게임 리셋 및 에이전트 상태 리셋
        self.game.go_to_new_game()
        self.agent.current_steps = 0
        self.agent.prev_score = 0
        self.agent.env.previous_lives = 3   # 목숨 상태 초기화
        self.agent.env.previous_score = 0   # 점수 상태 초기화 (공격 보상용)

    def draw(self):
        px.cls(0)
        self.game.draw()
        px.text(5, 5, f"MODE: {self.training_mode.upper()}", 7)
        px.text(5, 15, f"EPISODE: {self.episode_count}/{self.total_episodes}", 7)
        px.text(5, 25, f"SKILL: {self.agent.skill_level:.3f}", 7)
        
        # 모드별 BEST 표시
        if self.training_mode == "attack":
            px.text(5, 35, f"BEST KILLS: {self.trainer.best_kills}", 7)
        elif self.training_mode == "balanced":
            px.text(5, 35, f"BEST: {self.trainer.best_survival}steps/{self.trainer.best_kills}kills", 7)
        else:
            px.text(5, 35, f"BEST: {self.trainer.best_survival} steps", 7)


def create_ppo_agent(
    training_mode: str = "balanced",
    state_size: int = 161,
    action_size: int = 10,
    skill_level: float = 0.1,
    random_mode: bool = False
) -> RealGamePPOAgent:
    """
    학습 모드별 PPO 에이전트 생성
    
    Args:
        training_mode: 학습 모드 ("survival", "balanced", "attack")
        state_size: 상태 벡터 크기
        action_size: 액션 공간 크기
        skill_level: 초기 스킬 레벨 (0.1 ~ 1.0)
        random_mode: True면 완전 랜덤, False면 PPO 에이전트 사용
    
    Returns:
        RealGamePPOAgent 인스턴스
    """
    # 모드 검증
    if training_mode not in TRAINING_MODES:
        raise ValueError(f"Unknown training_mode: {training_mode}. "
                        f"Available modes: {list(TRAINING_MODES.keys())}")
    
    # 모드별 환경 생성 (가중치 자동 설정)
    env = GameEnvironment(training_mode=training_mode)
    ppo_agent = PPOAgent(state_size=state_size, action_size=action_size)
    
    return RealGamePPOAgent(
        ppo_agent=ppo_agent,
        env=env,
        skill_level=skill_level,
        random_mode=random_mode
    )


# 하위 호환성을 위한 별칭
def create_random_ppo_agent(
    state_size: int = 161,
    action_size: int = 10,
    skill_level: float = 0.1,
    random_mode: bool = True
) -> RealGamePPOAgent:
    """하위 호환성을 위한 래퍼 (기본 balanced 모드 사용)"""
    return create_ppo_agent(
        training_mode="balanced",
        state_size=state_size,
        action_size=action_size,
        skill_level=skill_level,
        random_mode=random_mode
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="PPO 선형 커리큘럼 트레이너 (3가지 학습 모드 지원)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
학습 모드:
  survival  생존 극한 (w_survival=95%, w_attack=5%)  - 회피 우선
  balanced  균형 (w_survival=50%, w_attack=50%)      - 생존과 공격 동일 비중
  attack    공격 극한 (w_survival=5%, w_attack=95%)  - 적 처치 우선

사용 예시:
  python train_ppo_real_game.py --mode survival --episodes 2000
  python train_ppo_real_game.py --mode balanced --episodes 2000
  python train_ppo_real_game.py --mode attack --episodes 2000
        """
    )
    parser.add_argument(
        "--mode", 
        type=str, 
        default="balanced",
        choices=["survival", "balanced", "attack"],
        help="학습 모드: survival(생존 극한), balanced(균형), attack(공격 극한)"
    )
    parser.add_argument("--speed", type=int, default=9, help="학습 속도 (기본: 9)")
    parser.add_argument("--episodes", type=int, default=2000, help="전체 에피소드 수 (기본: 2000)")
    args = parser.parse_args()
    
    # 커리큘럼 정보 계산
    num_stages = int((DEFAULT_END_SKILL - DEFAULT_START_SKILL) / 0.1) + 1  # 10단계
    episodes_per_stage = args.episodes // num_stages
    
    # 가중치 정보 출력
    weights = TRAINING_MODES[args.mode]
    print("=" * 60)
    print(f"🎮 PPO 순수 커리큘럼 러닝 시작 (단계별 고정 skill)")
    print("=" * 60)
    print(f"  학습 모드: {args.mode.upper()}")
    print(f"  가중치: w_survival={weights['w_survival']:.0%}, w_attack={weights['w_attack']:.0%}")
    print(f"  스킬 범위: {DEFAULT_START_SKILL} → {DEFAULT_END_SKILL} (0.1 단위)")
    print(f"  총 단계: {num_stages}단계")
    print(f"  단계당 에피소드: {episodes_per_stage}")
    print(f"  총 에피소드: {args.episodes}")
    print(f"  학습 속도: x{args.speed}")
    print("=" * 60)
    print(f"  📚 커리큘럼 구조:")
    for i in range(num_stages):
        skill = DEFAULT_START_SKILL + i * 0.1
        ep_start = i * episodes_per_stage + 1
        ep_end = (i + 1) * episodes_per_stage
        
        # 모드별 목표 표시
        if args.mode == "attack":
            target_kills = int(skill * 10)
            print(f"     Stage {i+1}: Ep {ep_start:4d}-{ep_end:4d} | "
                  f"skill={skill:.1f} | 목표 {target_kills:2d}킬")
        elif args.mode == "balanced":
            target_steps = int(300 + (skill - 0.1) * 1333.33)
            target_kills = int(skill * 10)
            print(f"     Stage {i+1}: Ep {ep_start:4d}-{ep_end:4d} | "
                  f"skill={skill:.1f} | 목표 {target_steps:4d}스텝/{target_kills:2d}킬")
        else:  # survival
            target_steps = int(300 + (skill - 0.1) * 1333.33)
            print(f"     Stage {i+1}: Ep {ep_start:4d}-{ep_end:4d} | "
                  f"skill={skill:.1f} | 목표 {target_steps:4d}스텝")
    print("=" * 60)
    
    # 에이전트 생성 (모드별 환경 설정)
    agent = create_ppo_agent(
        training_mode=args.mode,
        skill_level=DEFAULT_START_SKILL,
        random_mode=False
    )
    
    TrainingApp(
        agent, 
        training_mode=args.mode,
        speed=args.speed, 
        total_episodes=args.episodes
    )


if __name__ == "__main__":
    main()
