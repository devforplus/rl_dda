"""
실제 게임 환경에서 동작하는 PPO 에이전트
랜덤 에이전트 모드 지원 (초기화된 가중치 또는 완전 랜덤 액션)
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
from rl import PPOAgent, GameEnvironment
import input as input_module

# GUI 없는 환경에서도 그래프 저장이 가능하도록 설정
matplotlib.use("Agg")


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
    """커리큘럼 러닝 기반 학습 관리자 (연구 데이터 반영 및 시각화 추가)"""
    
    def __init__(self, agent: RealGamePPOAgent, save_dir: str = "models", total_episodes: int = 2000):
        self.agent = agent
        self.save_dir = save_dir
        self.total_episodes = total_episodes
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        # 성능 추적 (시각화용)
        self.episode_rewards = []
        self.episode_lengths = []
        self.best_survival = 0
        self.best_score = 0
        
        # 커리큘럼 상태 (에피소드 분할 방식)
        self.skill_levels = [0.1, 0.5, 1.0]
        self.step_size = total_episodes // 3
        
    def record_episode(self, reward: float, length: int):
        """에피소드 데이터 기록"""
        self.episode_rewards.append(reward)
        self.episode_lengths.append(length)

    def update_skill_by_episode(self, current_episode: int):
        """에피소드 번호에 따라 스킬 레벨 강제 조정"""
        if current_episode <= self.step_size:
            new_skill = self.skill_levels[0]
        elif current_episode <= self.step_size * 2:
            new_skill = self.skill_levels[1]
        else:
            new_skill = self.skill_levels[2]
            
        if self.agent.skill_level != new_skill:
            old_skill = self.agent.skill_level
            self.agent.skill_level = new_skill
            print(f"🚀 커리큘럼 단계 전환! ({current_episode} 에피소드) {old_skill:.1f} -> {new_skill:.1f}")
            self.agent.ppo_agent.save(os.path.join(self.save_dir, f"ppo_skill_{new_skill:.1f}_start.pth"))
            # 단계 전환 시 그래프 생성
            self.plot_progress()

    def plot_progress(self):
        """학습 진행 상황 그래프 생성 (trainer.py 이식)"""
        if not self.episode_rewards:
            return
            
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # 1. 보상 그래프
        ax1.plot(self.episode_rewards, alpha=0.3, color='blue', label='Reward')
        if len(self.episode_rewards) >= 10:
            avg_rewards = np.convolve(self.episode_rewards, np.ones(10)/10, mode='valid')
            ax1.plot(range(9, len(self.episode_rewards)), avg_rewards, color='blue', linewidth=2, label='MA(10)')
        ax1.set_title('Training Progress - Reward')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 2. 생존 시간 그래프
        ax2.plot(self.episode_lengths, alpha=0.3, color='green', label='Survival Steps')
        if len(self.episode_lengths) >= 10:
            avg_lengths = np.convolve(self.episode_lengths, np.ones(10)/10, mode='valid')
            ax2.plot(range(9, len(self.episode_lengths)), avg_lengths, color='green', linewidth=2, label='MA(10)')
        ax2.set_title('Training Progress - Survival Time')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_path = os.path.join(self.save_dir, "training_progress.png")
        plt.savefig(plot_path)
        plt.close()

    def check_curriculum_advance(self, survival_time: int, score: int):
        pass

    def save_checkpoint(self, is_best=False):
        """모델 저장"""
        try:
            if not os.path.exists(self.save_dir):
                os.makedirs(self.save_dir, exist_ok=True)
                
            path = os.path.join(self.save_dir, "ppo_latest.pth")
            self.agent.ppo_agent.save(path)
            if is_best:
                best_path = os.path.join(self.save_dir, "ppo_best.pth")
                self.agent.ppo_agent.save(best_path)
        except Exception as e:
            print(f"⚠️ 모델 저장 실패: {e}")


# Pyxel 앱을 상속받아 학습용 환경 구현
class TrainingApp:
    def __init__(self, agent: RealGamePPOAgent, speed=9, total_episodes=2000):
        from const import APP_WIDTH, APP_HEIGHT, APP_NAME, APP_FPS, \
            APP_DISPLAY_SCALE, APP_CAPTURE_SCALE, APP_GFX_FILE, PALETTE, SOUNDS_RES_FILE
        from game import Game
        from input import Input
        from monospace_bitmap_font import MonospaceBitmapFont
        
        self.agent = agent
        self.speed = speed
        self.total_episodes = total_episodes
        self.trainer = CurriculumTrainer(agent, total_episodes=total_episodes)
        
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
        
        # 보상 합계 계산 (기록용)
        # PPOAgent의 마지막 rewards 버퍼를 합산하거나, 환경에서 실시간 누적값을 받아와야 함
        # 여기서는 단순화를 위해 마지막 보상값 또는 평균값을 활용하는 방식 대신
        # 에피소드 종료 시점의 생존/점수 지표를 기록
        self.trainer.record_episode(score, survival_time)
        
        print(f"🎬 Episode {self.episode_count}/{self.total_episodes} 종료 | 생존: {survival_time} | 점수: {score} | Skill: {self.agent.skill_level:.1f}")
        
        # 커리큘럼 체크 (에피소드 분할 방식)
        self.trainer.update_skill_by_episode(self.episode_count)
        
        # 학습 종료 체크
        if self.episode_count >= self.total_episodes:
            print("🏁 전체 학습 종료!")
            self.trainer.plot_progress() # 최종 그래프 생성
            self.trainer.save_checkpoint()
            px.quit()
            return
            
        # 베스트 갱신 체크 및 저장
        is_best = False
        if survival_time > self.trainer.best_survival:
            self.trainer.best_survival = survival_time
            is_best = True
        
        if score > self.trainer.best_score:
            self.trainer.best_score = score
            is_best = True
            
        if self.episode_count % 10 == 0:
            self.trainer.save_checkpoint(is_best)
            
        # 게임 리셋 및 에이전트 상태 리셋
        self.game.go_to_new_game()
        self.agent.current_steps = 0
        self.agent.prev_score = 0
        self.agent.env.previous_lives = 3  # 목숨 상태 초기화

    def draw(self):
        px.cls(0)
        self.game.draw()
        px.text(5, 5, f"EPISODE: {self.episode_count}", 7)
        px.text(5, 15, f"SKILL: {self.agent.skill_level:.1f}", 7)
        px.text(5, 25, f"BEST SURVIVAL: {self.trainer.best_survival}", 7)


def create_random_ppo_agent(
    state_size: int = 161,
    action_size: int = 10,
    skill_level: float = 0.1,
    random_mode: bool = True
) -> RealGamePPOAgent:
    """
    랜덤 PPO 에이전트 생성
    
    Args:
        state_size: 상태 벡터 크기
        action_size: 액션 공간 크기
        skill_level: 초기 스킬 레벨
        random_mode: True면 완전 랜덤, False면 초기화된 가중치 사용
    
    Returns:
        RealGamePPOAgent 인스턴스
    """
    env = GameEnvironment()
    ppo_agent = PPOAgent(state_size=state_size, action_size=action_size)
    
    return RealGamePPOAgent(
        ppo_agent=ppo_agent,
        env=env,
        skill_level=skill_level,
        random_mode=random_mode
    )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PPO 커리큘럼 트레이너")
    parser.add_argument("--speed", type=int, default=9, help="학습 속도 (기본: 9)")
    parser.add_argument("--episodes", type=int, default=2000, help="전체 에피소드 수 (기본: 2000)")
    parser.add_argument("--skill", type=float, default=0.1, help="시작 스킬 레벨 (기본: 0.1)")
    args = parser.parse_args()
    
    # 에이전트 생성 (random_mode=False로 실제 학습 진행)
    agent = create_random_ppo_agent(skill_level=args.skill, random_mode=False)
    
    print(f"🎮 학습 시작 (속도: x{args.speed}, 전체 에피소드: {args.episodes}, 초기 스킬: {args.skill})")
    TrainingApp(agent, speed=args.speed, total_episodes=args.episodes)


if __name__ == "__main__":
    main()
