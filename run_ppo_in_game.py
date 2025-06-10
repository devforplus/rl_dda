#!/usr/bin/env python
"""
PPO 에이전트와 실제 게임 연동 스크립트

훈련된 PPO 에이전트가 실제 게임 환경에서 플레이하도록 합니다.
게임 상태를 실시간으로 추출하여 에이전트에 전달하고,
에이전트의 액션을 게임 입력으로 변환합니다.

---

실제 게임과 강화학습 에이전트를 연동하는 통합 스크립트
"""

import sys
import os
import time
import traceback
import csv
import json
from datetime import datetime
from typing import Optional, Dict, Any

# src 디렉토리를 시스템 경로에 추가
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

try:
    import pyxel as px
    from main import App
    from rl.agents.ppo_agent import PPOAgent, create_ppo_agent
    from rl.environment import GameEnvironment
    from rl.game_adapter import GameStateAdapter
    from components.entity_types import EntityType
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    print(
        "Make sure all required modules are installed and paths are correct.",
        file=sys.stderr,
    )
    sys.exit(1)


class GamePPOAgent:
    """실제 게임과 연동되는 PPO 에이전트 래퍼

    게임 상태를 추출하고 PPO 에이전트의 액션을 적용하는 브리지 역할을 합니다.

    ---

    게임과 PPO 에이전트 사이의 인터페이스를 제공하는 어댑터 클래스
    """

    def __init__(
        self,
        ppo_agent: PPOAgent,
        skill_level: float = 0.5,
        personality: int = 0,
        enable_learning: bool = False,
        model_path: Optional[str] = None,
        save_interval: int = 1000,
    ):
        """게임 PPO 에이전트 초기화

        Args:
            ppo_agent: PPO 에이전트 인스턴스
            skill_level: 플레이어 실력 수준 (0~1)
            personality: 플레이어 성향 (0: 방어적, 1: 공격적)
            enable_learning: 학습 모드 여부
            model_path: 모델 저장 경로 (학습 시에만 사용)
            save_interval: 모델 저장 간격 (스텝 단위)

        ---

        PPO 에이전트와 게임 어댑터를 초기화
        """
        self.ppo_agent = ppo_agent
        self.skill_level = skill_level
        self.personality = personality
        self.enable_learning = enable_learning
        self.model_path = model_path
        self.save_interval = save_interval

        # 게임 상태 어댑터
        self.adapter = GameStateAdapter()

        # 게임 인스턴스 참조 (나중에 설정됨)
        self.game_instance = None

        # 성능 통계
        self.step_count = 0
        self.episode_count = 0
        self.total_reward = 0.0
        self.episode_start_time = time.time()
        self.episode_start_step = 0  # 에피소드 시작 스텝 추가
        self.last_game_state = None
        self.last_action = None
        self.last_action_time = time.time()

        # 에피소드별 상세 통계
        self.episode_rewards = []  # 각 스텝별 보상 기록
        self.episode_actions = []  # 각 스텝별 액션 기록
        self.max_score_in_episode = 0  # 에피소드 내 최고 스코어
        self.max_lives_in_episode = 0  # 에피소드 내 최대 생명 수
        self.final_stage = 1  # 에피소드 종료 시 스테이지

        # 통계 출력 간격
        self.stats_interval = 600  # 10초마다 (60 FPS 기준) - 기존 300에서 증가

        # 로깅 시스템 초기화
        self.log_dir = "logs"
        self.training_log_file = None
        self.episode_log_file = None
        self.plot_interval = 0  # 주기적 그래프 생성 비활성화 (0으로 설정)
        self.target_episodes = None  # 목표 에피소드 수 (외부에서 설정)
        self.training_complete = False  # 훈련 완료 플래그 추가
        self.setup_logging()

        # 안정적인 학습을 위한 최적화 설정
        self.fast_mode = enable_learning  # 학습 모드에서만 빠른 모드 활성화
        if self.fast_mode:
            self.stats_interval = 900  # 더 긴 간격 (15초마다) - 기존 150에서 증가
            print(f"🚀 Stable learning mode enabled!")
            print(f"📊 Performance tracking optimized for consistency")

        # 실시간 메트릭 추적
        self.best_score = 0
        self.best_reward = float("-inf")
        self.best_survival_time = 0.0  # 최고 생존 시간 추가
        self.last_survival_time = 0.0  # 이전 에피소드 생존 시간 추가
        self.training_start_time = time.time()

        print(f"🤖 GamePPOAgent initialized:")
        print(f"   Skill Level: {skill_level}")
        print(f"   Personality: {'Aggressive' if personality == 1 else 'Defensive'}")
        print(f"   Learning: {'Enabled' if enable_learning else 'Disabled'}")
        if enable_learning and model_path:
            print(f"   Model Save: {model_path} every {save_interval} steps")
            print(f"   Logs: {self.log_dir}/")

    def setup_logging(self):
        """로깅 시스템 설정

        ---

        훈련 메트릭과 에피소드 데이터를 CSV 파일로 저장하는 시스템 초기화
        """
        if not self.enable_learning:
            return

        # 로그 디렉토리 생성
        os.makedirs(self.log_dir, exist_ok=True)

        # 타임스탬프로 고유한 로그 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 훈련 메트릭 로그 파일
        self.training_log_file = os.path.join(
            self.log_dir, f"training_metrics_{timestamp}.csv"
        )
        with open(self.training_log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "step",
                    "episode",
                    "total_loss",
                    "policy_loss",
                    "value_loss",
                    "entropy_loss",
                    "current_reward",
                    "steps_per_sec",
                ]
            )

        # 에피소드 로그 파일
        self.episode_log_file = os.path.join(self.log_dir, f"episodes_{timestamp}.csv")
        with open(self.episode_log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "episode",
                    "duration_sec",
                    "steps",
                    "total_reward",
                    "avg_reward_per_step",
                    "final_score",
                    "max_score",
                    "final_stage",
                    "final_lives",
                    "positive_rewards",
                    "negative_rewards",
                    "end_reason",
                ]
            )

        print(f"📊 Logging initialized:")
        print(f"   Training metrics: {self.training_log_file}")
        print(f"   Episode data: {self.episode_log_file}")

    def log_training_metrics(self, training_stats: Dict[str, float]):
        """훈련 메트릭을 로그 파일에 기록

        Args:
            training_stats: 훈련 통계 딕셔너리

        ---

        실시간 그래프 생성을 위한 훈련 메트릭 저장
        """
        if not self.enable_learning or not self.training_log_file:
            return

        try:
            # 파일이 존재하는지 확인하고 없으면 헤더 다시 생성
            if not os.path.exists(self.training_log_file):
                print(
                    f"⚠️ Training log file missing, recreating: {self.training_log_file}"
                )
                os.makedirs(os.path.dirname(self.training_log_file), exist_ok=True)
                with open(
                    self.training_log_file, "w", newline="", encoding="utf-8"
                ) as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            "timestamp",
                            "step",
                            "episode",
                            "total_loss",
                            "policy_loss",
                            "value_loss",
                            "entropy_loss",
                            "current_reward",
                            "steps_per_sec",
                        ]
                    )

            current_time = time.time()
            elapsed_time = current_time - self.episode_start_time
            steps_per_second = self.step_count / max(1, elapsed_time)

            with open(self.training_log_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        datetime.now().isoformat(),
                        self.step_count,
                        self.episode_count,
                        training_stats.get("total_loss", 0),
                        training_stats.get("policy_loss", 0),
                        training_stats.get("value_loss", 0),
                        training_stats.get("entropy_loss", 0),
                        self.total_reward,
                        steps_per_second,
                    ]
                )
        except Exception as e:
            print(f"⚠️ Failed to log training metrics: {e}")

    def log_episode_data(self, episode_data: Dict[str, Any]):
        """에피소드 데이터를 로그 파일에 기록

        Args:
            episode_data: 에피소드 통계 딕셔너리

        ---

        에피소드별 성과 데이터를 CSV 파일에 저장
        """
        if not self.enable_learning or not self.episode_log_file:
            return

        try:
            # 파일이 존재하는지 확인하고 없으면 헤더 다시 생성
            if not os.path.exists(self.episode_log_file):
                print(
                    f"⚠️ Episode log file missing, recreating: {self.episode_log_file}"
                )
                os.makedirs(os.path.dirname(self.episode_log_file), exist_ok=True)
                with open(
                    self.episode_log_file, "w", newline="", encoding="utf-8"
                ) as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            "timestamp",
                            "episode",
                            "duration_sec",
                            "steps",
                            "total_reward",
                            "avg_reward_per_step",
                            "final_score",
                            "max_score",
                            "final_stage",
                            "final_lives",
                            "positive_rewards",
                            "negative_rewards",
                            "end_reason",
                        ]
                    )

            with open(self.episode_log_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        datetime.now().isoformat(),
                        episode_data["episode"],
                        episode_data["duration"],
                        episode_data["steps"],
                        episode_data["total_reward"],
                        episode_data["avg_reward_per_step"],
                        episode_data["final_score"],
                        episode_data["max_score"],
                        episode_data["final_stage"],
                        episode_data["final_lives"],
                        episode_data["positive_rewards"],
                        episode_data["negative_rewards"],
                        episode_data["end_reason"],
                    ]
                )
        except Exception as e:
            print(f"⚠️ Failed to log episode data: {e}")

    def generate_training_plots(self):
        """훈련 진행도 그래프 생성

        ---

        에피소드 종료 시점에 현재까지의 훈련 진행도를 시각화
        """
        if not self.enable_learning:
            return

        try:
            # plot_training_progress 모듈 임포트
            from plot_training_progress import TrainingPlotter

            plotter = TrainingPlotter(log_dir=self.log_dir, output_dir="plots")
            success = plotter.generate_all_plots()

            if success:
                print(f"📊 Training plots generated in plots/ directory")

        except ImportError:
            print("⚠️ plot_training_progress.py not found - plots not generated")
        except Exception as e:
            print(f"⚠️ Failed to generate plots: {e}")

    def set_game_instance(self, game_instance):
        """게임 인스턴스 설정

        Args:
            game_instance: App 인스턴스

        ---

        게임과의 연결을 설정하여 실제 게임 상태에 접근 가능하게 함
        """
        self.game_instance = game_instance
        print("🔗 Game instance connected to PPO agent")

    def connect_game(self, game_instance):
        """게임과 연결 설정 (App.py에서 호출되는 메서드)

        Args:
            game_instance: 게임 인스턴스

        ---

        App 클래스에서 에이전트 초기화 시 호출되는 메서드
        """
        self.set_game_instance(game_instance)
        print(f"🎮 PPO Agent connected to game (Learning Mode: {self.enable_learning})")

        # 게임 종료 시그널 처리를 위한 핸들러 등록 (가능한 경우)
        if hasattr(game_instance, "on_exit"):
            original_exit = game_instance.on_exit

            def exit_with_plots():
                print("🔚 Game is closing - generating final plots...")
                self.generate_final_plots("Game closed by user")
                if original_exit:
                    original_exit()

            game_instance.on_exit = exit_with_plots

    def select_action(self) -> int:
        """게임에서 호출되는 액션 선택 메서드

        Returns:
            선택된 액션 ID (0~8)

        ---

        게임 루프에서 매 프레임 호출되어 에이전트의 액션을 반환
        """
        if self.training_complete:
            return 4  # Return a neutral action if training is done

        try:
            game_state = self._extract_current_game_state()
            if game_state is None:
                return 4  # Return a neutral action if game state is not available

            if self.enable_learning:
                action, log_prob, value = self.ppo_agent.select_action_with_exploration(
                    game_state
                )
                if self.last_game_state is not None and self.last_action is not None:
                    reward = self.ppo_agent.env.calculate_reward(
                        game_state, self.last_action
                    )
                    done = self._is_episode_done(game_state)
                    self.ppo_agent.store_experience(
                        self.last_game_state,
                        self.last_action,
                        reward,
                        self.last_log_prob,
                        self.last_value,
                        done,
                    )
                    self.total_reward += reward
                    self.episode_rewards.append(reward)
                    self.episode_actions.append(self.last_action)
                    if done:
                        self._handle_episode_end()
                self.last_log_prob = log_prob
                self.last_value = value

                # 버퍼가 가득 차면 학습을 수행합니다.
                if self.ppo_agent.is_buffer_full():
                    print("🧠 Buffer is full, starting training...")
                    training_stats = self.ppo_agent.train()
                    if training_stats:
                        self.log_training_metrics(training_stats)
            else:
                action = self.ppo_agent.select_action(game_state)

            self.last_game_state = game_state
            self.last_action = action
            self.step_count += 1

            # 모델 저장 로직 추가
            if (
                self.enable_learning
                and self.model_path
                and self.step_count % self.save_interval == 0
            ):
                self.ppo_agent.save_model(self.model_path)
                print(f"💾 Model saved to {self.model_path} at step {self.step_count}")

            return action
        except Exception as e:
            print(
                f"Error in select_action: {e}\n{traceback.format_exc()}",
                file=sys.stderr,
            )
            return 4  # Return a neutral action in case of error

    def _extract_current_game_state(self):
        """현재 게임 상태 추출

        Returns:
            GameState 인스턴스 또는 None

        ---

        실제 게임 인스턴스에서 상태를 추출하여 PPO 모델용으로 변환
        """
        try:
            if self.game_instance is None:
                # 게임 인스턴스가 없으면 더미 상태 생성
                return self._create_dummy_game_state()

            # 게임 어댑터를 사용하여 실제 게임 상태 추출
            return self.adapter.extract_game_state(
                self.game_instance,
                self.skill_level,
                self.personality,
            )

        except Exception as e:
            print(f"Error extracting game state: {e}", file=sys.stderr)
            # 오류 발생 시 더미 상태로 대체
            return self._create_dummy_game_state()

    def _create_dummy_game_state(self):
        """더미 게임 상태 생성

        Returns:
            기본 GameState 인스턴스

        ---

        게임 인스턴스에 접근할 수 없을 때 사용하는 대체 상태
        """
        from rl.environment import GameState, EntityData

        # 기본 게임 상태 생성
        entities = [
            EntityData(EntityType.PLAYER, 100, 100, 8, 8, 0),
        ]

        return GameState(
            entities=entities,
            skill_level=self.skill_level,
            personality=self.personality,
            player_hp=2,  # 체력 (10에서 2로 변경)
            player_lives=1,  # 기본 목숨 수 (3에서 1로 변경)
            score=self.step_count * 10,  # 임시 점수
            survival_time=self.step_count,
            kills=self.step_count // 100,
            current_stage=1,  # 기본 스테이지
            game_cleared=False,  # 기본값
        )

    def _is_episode_done(self, game_state) -> bool:
        """에피소드 종료 여부 확인

        Args:
            game_state: 현재 게임 상태

        Returns:
            에피소드 종료 여부

        ---

        플레이어 사망이나 게임 종료 조건을 확인
        """
        # 플레이어 목숨이 0이하면 에피소드 종료
        if game_state.player_lives <= 0:
            print(
                f"🏁 Episode done: Player lives exhausted ({game_state.player_lives})"
            )
            return True

        # 게임 클리어 시 에피소드 종료 (모든 스테이지 완주)
        if game_state.game_cleared:
            print(f"🏁 Episode done: Game cleared!")
            return True

        # 게임 인스턴스에서 직접 게임 오버 상태 확인
        if self.game_instance and hasattr(self.game_instance, "game"):
            game = self.game_instance.game

            # 게임 상태 확인
            if hasattr(game, "state") and hasattr(game.state, "state"):
                current_state = game.state.state
                if hasattr(current_state, "name"):
                    if current_state.name in ["GAME_OVER", "GAMEOVER", "GAME_END"]:
                        print(f"🏁 Episode done: Game state is {current_state.name}")
                        return True

            # 게임 변수에서 직접 확인
            if hasattr(game, "game_vars"):
                game_vars = game.game_vars
                if hasattr(game_vars, "lives") and getattr(game_vars, "lives", 1) <= 0:
                    print(
                        f"🏁 Episode done: Game vars lives = {getattr(game_vars, 'lives', 'unknown')}"
                    )
                    return True

                # 스테이지 완주 확인 (최종 스테이지 도달)
                if hasattr(game_vars, "stage_num"):
                    current_stage = getattr(game_vars, "stage_num", 1)
                    if current_stage >= 8:  # 최종 스테이지 (게임에 따라 조정)
                        print(f"🏁 Episode done: Final stage {current_stage} reached")
                        return True

        # 매우 긴 에피소드 강제 종료 (무한 루프 방지)
        episode_length = self.step_count - self.episode_start_step
        max_episode_length = (
            8000 if not self.fast_mode else 5000
        )  # 더 긴 에피소드 허용 (기존 5000/2000에서 증가)

        if episode_length > max_episode_length:
            print(
                f"🏁 Episode done: Maximum episode length reached ({episode_length} steps)"
            )
            return True

        return False

    def _handle_episode_end(self):
        """에피소드 종료 처리

        ---

        에피소드 통계 출력 및 학습 수행
        """
        self.episode_count += 1
        episode_length = self.step_count - self.episode_start_step
        episode_duration = time.time() - self.episode_start_time

        # 현재 게임 상태에서 최종 정보 추출
        final_score = 0
        final_lives = 0
        final_stage = 1
        episode_end_reason = "Unknown"

        if self.game_instance and hasattr(self.game_instance, "game"):
            game = self.game_instance.game

            # 게임 변수에서 정보 추출
            if hasattr(game, "game_vars"):
                final_score = getattr(game.game_vars, "score", 0)
                final_lives = getattr(game.game_vars, "lives", 0)
                final_stage = getattr(game.game_vars, "stage_num", 1)

            # 게임 상태에서 종료 이유 판단
            if hasattr(game, "state") and hasattr(game.state, "state"):
                from states.game_state.game_state_stage import State

                if hasattr(game.state, "state"):
                    game_state = game.state.state
                    if game_state.name == "GAME_OVER":
                        episode_end_reason = "Game Over - All Lives Lost"
                    elif game_state.name == "STAGE_CLEAR":
                        if (
                            final_stage >= 8
                        ):  # 최종 스테이지 클리어 (게임에 따라 조정 필요)
                            episode_end_reason = "Game Complete - All Stages Cleared!"
                        else:
                            episode_end_reason = f"Stage {final_stage} Cleared"
                    elif game_state.name == "PLAYER_DEAD":
                        if final_lives <= 0:
                            episode_end_reason = "Player Death - Last Life Lost"
                        else:
                            episode_end_reason = (
                                f"Player Death - {final_lives} Lives Remaining"
                            )
                    else:
                        episode_end_reason = f"Game State: {game_state.name}"

        # 최종 게임 상태 기반으로도 종료 이유 판단
        if episode_end_reason == "Unknown":
            current_game_state = self._extract_current_game_state()
            if current_game_state:
                if current_game_state.player_lives <= 0:
                    episode_end_reason = "No Lives Remaining"
                elif current_game_state.game_cleared:
                    episode_end_reason = "All Stages Completed"
                else:
                    episode_end_reason = "Episode Terminated"

        # 보상 통계 계산
        total_positive_reward = sum(r for r in self.episode_rewards if r > 0)
        total_negative_reward = sum(r for r in self.episode_rewards if r < 0)
        avg_reward_per_step = self.total_reward / max(1, episode_length)

        # 액션 분포 계산
        action_distribution = {}
        fire_actions = 0
        movement_actions = 0
        for action in self.episode_actions:
            action_distribution[action] = action_distribution.get(action, 0) + 1
            if action == 8:  # FIRE action
                fire_actions += 1
            elif action in [0, 1, 2, 3, 5, 6, 7]:  # Movement actions
                movement_actions += 1

        # 전투 및 플레이 스타일 분석
        total_actions = len(self.episode_actions)
        fire_ratio = (fire_actions / max(1, total_actions)) * 100
        movement_ratio = (movement_actions / max(1, total_actions)) * 100

        # 액션 분포 출력
        print(f"🎮 Action Distribution:")
        action_names = ["↖", "↑", "↗", "←", "•", "→", "↙", "↓", "↘", "🔥"]
        for action_id in sorted(action_distribution.keys()):
            if action_id < len(action_names):
                action_name = action_names[action_id]
                count = action_distribution[action_id]
                percentage = (count / max(1, episode_length)) * 100
                if action_id == 8:  # Fire action - highlight
                    print(
                        f"   🔥 {action_name} (#{action_id}): {count} times ({percentage:.1f}%) ⭐"
                    )
                else:
                    print(
                        f"   {action_name} (#{action_id}): {count} times ({percentage:.1f}%)"
                    )

        # 플레이 스타일 분석
        print(f"⚔️ Combat Analysis:")
        print(
            f"   Fire Ratio: {fire_ratio:.1f}% ({fire_actions}/{total_actions} actions)"
        )
        print(f"   Movement Ratio: {movement_ratio:.1f}%")

        # 플레이 스타일 평가
        if fire_ratio < 5:
            print(f"   📊 Style: Very Defensive (too passive)")
        elif fire_ratio < 15:
            print(f"   📊 Style: Defensive (could be more aggressive)")
        elif fire_ratio < 25:
            print(f"   📊 Style: Balanced (good mix of survival and combat)")
        elif fire_ratio < 40:
            print(f"   📊 Style: Aggressive (good combat engagement)")
        else:
            print(f"   📊 Style: Very Aggressive (high combat focus)")

        # 최고 기록 업데이트
        if self.total_reward > self.best_reward:
            self.best_reward = self.total_reward
        if final_score > self.best_score:
            self.best_score = final_score

        # 생존 시간 계산 및 기록 업데이트
        survival_seconds = episode_length / 60.0  # 60 FPS 기준
        if survival_seconds > self.best_survival_time:
            self.best_survival_time = survival_seconds

        # 상세한 에피소드 요약 출력
        print(f"\n🏁 ===== Episode {self.episode_count} Summary =====")
        print(f"📊 Episode Stats:")
        print(f"   Duration: {episode_duration:.1f}s ({episode_length} steps)")
        print(f"   Steps/sec: {episode_length / max(0.1, episode_duration):.1f}")
        print(f"   End Reason: {episode_end_reason}")

        print(f"🎯 Game Performance:")
        print(f"   Final Score: {final_score:,}")
        print(f"   Max Score: {self.max_score_in_episode:,}")
        print(f"   Final Stage: {final_stage}")
        print(f"   Final Lives: {final_lives}")

        print(f"💰 Reward Analysis:")
        print(f"   Total Reward: {self.total_reward:.3f}")
        print(f"   Average Reward/Step: {avg_reward_per_step:.6f}")
        print(f"   Positive Rewards: {total_positive_reward:.3f}")
        print(f"   Negative Rewards: {total_negative_reward:.3f}")
        print(f"   Reward Steps: {len(self.episode_rewards)}")

        # 생존 분석 추가
        print(f"⏱️  Survival Analysis:")
        print(f"   Survival Time: {survival_seconds:.1f} seconds")
        print(f"   Survival Steps: {episode_length}")
        print(f"   Best Survival: {self.best_survival_time:.1f} seconds")

        if self.last_survival_time > 0:
            improvement = survival_seconds - self.last_survival_time
            if improvement > 0:
                print(f"   📈 Improvement: +{improvement:.1f}s from last episode!")
            elif improvement < 0:
                print(f"   📉 Decline: {improvement:.1f}s from last episode")
            else:
                print(f"   ➡️ Same as last episode")

        # 생존 시간이 5초 미만이면 경고
        if survival_seconds < 5.0:
            print(f"   ⚠️ WARNING: Very short survival time ({survival_seconds:.1f}s)")
            print(f"   💡 Agent needs to learn better survival strategies!")
        elif survival_seconds > 10.0:
            print(f"   🎉 Good survival time! Agent is learning!")

        self.last_survival_time = survival_seconds

        print(f"📈 Overall Progress:")
        print(f"   Total Steps: {self.step_count}")
        print(f"   Episodes Completed: {self.episode_count}")
        print("=" * 50 + "\n")

        # 게임을 먼저 재시작하여 환경을 초기화합니다.
        if (
            self.game_instance
            and hasattr(self.game_instance, "game")
            and hasattr(self.game_instance.game, "restart_game")
        ):
            self.game_instance.game.restart_game()
            print("🔄 Game restarted for new episode.")

        # 에피소드 데이터 로깅 (리셋하기 전에 수행!)
        episode_total_reward = self.total_reward  # 현재 에피소드의 총 보상 저장
        self.log_episode_data(
            {
                "episode": self.episode_count,
                "duration": episode_duration,
                "steps": episode_length,
                "total_reward": episode_total_reward,  # 리셋 전 값 사용
                "avg_reward_per_step": avg_reward_per_step,
                "final_score": final_score,
                "max_score": self.max_score_in_episode,
                "final_stage": final_stage,
                "final_lives": final_lives,
                "positive_rewards": total_positive_reward,
                "negative_rewards": total_negative_reward,
                "end_reason": episode_end_reason,
            }
        )

        # 통계 리셋 (에피소드 데이터 로깅 후에 수행)
        self.total_reward = 0.0
        self.episode_start_time = time.time()
        self.episode_start_step = self.step_count
        self.episode_rewards.clear()
        self.episode_actions.clear()
        self.max_score_in_episode = 0
        self.max_lives_in_episode = 0
        self.final_stage = 1

        # 이전 상태 정보 초기화 (새 에피소드 시작)
        self.last_game_state = None
        self.last_action = None
        if hasattr(self, "last_log_prob"):
            delattr(self, "last_log_prob")
        if hasattr(self, "last_value"):
            delattr(self, "last_value")

        # 환경 리셋 (PPO 환경의 이전 상태 초기화)
        self.ppo_agent.env.reset()

        # 목표 에피소드 수 달성 시에만 그래프 생성
        should_generate_plots = False
        should_terminate_game = False  # 게임 종료 플래그 추가

        if self.target_episodes and self.episode_count >= self.target_episodes:
            should_generate_plots = True
            should_terminate_game = True  # 목표 달성 시 게임 종료
            self.training_complete = True  # 훈련 완료 표시
            print(
                f"\n🎯 Target episodes ({self.target_episodes}) reached! Generating final plots and terminating..."
            )

        if should_generate_plots:
            # 목표 달성 시 최종 요약과 함께 그래프 생성
            self.generate_final_plots(
                f"Target episodes ({self.target_episodes}) completed"
            )

        # 게임 자동 종료 처리
        if should_terminate_game:
            print(f"\n🏁 Training completed successfully!")
            print(f"📊 Final Statistics:")
            print(f"   Episodes: {self.episode_count}")
            print(f"   Best Survival: {self.best_survival_time:.1f}s")
            print(f"   Best Score: {self.best_score:,}")
            print(f"🔚 Automatically terminating game...")

            # 게임 종료 요청
            if self.game_instance and hasattr(self.game_instance, "quit"):
                self.game_instance.quit()
            elif hasattr(self.game_instance, "running"):
                self.game_instance.running = False

            # Pyxel 게임 종료
            try:
                px.quit()
            except:
                pass

            # 프로그램 종료
            import sys

            print("✅ Game terminated successfully!")
            sys.exit(0)

    def _print_performance_stats(self):
        """성능 통계 출력

        ---

        주기적으로 에이전트 성능 통계를 출력
        """
        current_time = time.time()
        elapsed_time = current_time - self.episode_start_time

        steps_per_second = self.step_count / max(1, elapsed_time)

        # PPO 에이전트 통계
        agent_stats = self.ppo_agent.get_stats()

        print(f"📊 Stats @ Step {self.step_count} (Episode {self.episode_count}):")
        print(f"   Current Reward: {self.total_reward:.2f}")
        print(f"   Steps/sec: {steps_per_second:.1f}")

    def set_target_episodes(self, target: int):
        """목표 에피소드 수 설정

        Args:
            target: 목표 에피소드 수

        ---

        지정된 에피소드 수에 도달하면 그래프를 생성
        """
        self.target_episodes = target
        print(f"🎯 Target episodes set to: {target}")

    def is_training_complete(self) -> bool:
        """훈련 완료 여부 확인

        Returns:
            훈련 완료 여부

        ---

        외부에서 훈련 상태를 확인할 수 있는 메서드
        """
        return self.training_complete

    def generate_final_plots(self, reason: str = "Training completed"):
        """최종 그래프 생성

        Args:
            reason: 그래프 생성 이유

        ---

        훈련 완료 시 최종 결과 그래프를 생성
        """
        print(f"📊 Generating final training plots - {reason}")
        self.generate_training_plots()

        # 최종 통계 출력
        print("\n" + "=" * 80)
        print("🎯 Training Summary")
        print(f"📊 Total Episodes: {self.episode_count}")
        print(f"📈 Total Steps: {self.step_count}")
        print(f"🏆 Best Score: {self.best_score:,}")
        print(f"💰 Best Reward: {self.best_reward:.3f}")
        print(f"⏱️ Best Survival: {self.best_survival_time:.1f} seconds")
        print(f"⚡ Training Time: {time.time() - self.training_start_time:.1f}s")
        print("=" * 80)


class PPOGameApp(App):
    """PPO 에이전트와 연동되는 게임 앱"""

    def __init__(self, game_ppo_agent: "GamePPOAgent"):
        """앱 초기화

        Args:
            game_ppo_agent: PPO 에이전트 래퍼
        """
        self.game_agent = game_ppo_agent
        # game_agent에 self(App 인스턴스)를 연결합니다.
        self.game_agent.set_game_instance(self)
        # App의 생성자를 호출합니다. 이 안에서 px.run()이 호출되어 게임이 시작됩니다.
        super().__init__(agent=game_ppo_agent)

    def update(self):
        """게임 업데이트 (에이전트 연동)"""
        # 에이전트로부터 액션 받아오기
        action = self.game_agent.select_action()

        # 액션을 게임 입력으로 변환하여 적용
        self.apply_agent_action(action)

        # self.input.update()와 self.game.update()를 직접 호출하여
        # App.update()의 중복된 에이전트 로직을 피합니다.
        self.input.update()
        self.game.update()


def create_trained_ppo_agent(
    model_path: Optional[str] = None, enable_learning: bool = False
) -> PPOAgent:
    """훈련된 PPO 에이전트를 생성하거나 새로 초기화합니다."""
    from rl.environment import GameEnvironment
    from rl.agents.ppo_agent import create_ppo_agent

    env = GameEnvironment()
    agent = create_ppo_agent(env=env)

    if model_path and os.path.exists(model_path):
        try:
            agent.load_model(model_path)
            print(f"✅ Model loaded successfully from {model_path}")
        except Exception as e:
            print(
                f"⚠️ Failed to load model from {model_path}, starting fresh. Error: {e}"
            )
            print("Using newly initialized model instead.")
    else:
        print("🆕 No model found or specified, starting with a new model.")

    if enable_learning:
        agent.set_train_mode()
    else:
        agent.set_eval_mode()

    return agent


def run_ppo_in_game(
    model_path: Optional[str] = None,
    skill_level: float = 0.7,
    personality: int = 1,
    enable_learning: bool = False,
    save_interval: int = 1000,
    target_episodes: Optional[int] = None,
):
    """
    PPO 에이전트를 실제 게임에 연동하여 실행합니다.

    Args:
        model_path: 불러올 PPO 모델 파일 경로 (없으면 새로 생성)
        skill_level: 플레이어 실력 수준
        personality: 플레이어 성향 (0: 방어적, 1: 공격적)
        enable_learning: 학습 모드 활성화 여부
        save_interval: 모델 저장 간격 (스텝 단위)
        target_episodes: 목표 에피소드 수 (도달 시 학습 종료)
    """
    try:
        # 학습 모드이고 모델 경로가 지정되지 않은 경우, 자동 경로 생성
        if enable_learning and not model_path:
            model_dir = os.path.join("models", "ppo")
            os.makedirs(model_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = os.path.join(model_dir, f"ppo_agent_{timestamp}.pth")
            print(f"✨ New model path generated: {model_path}")

        # 에이전트 생성
        ppo_agent = create_trained_ppo_agent(
            model_path=model_path, enable_learning=enable_learning
        )

        # 게임-PPO 에이전트 래퍼 생성
        game_agent = GamePPOAgent(
            ppo_agent=ppo_agent,
            skill_level=skill_level,
            personality=personality,
            enable_learning=enable_learning,
            model_path=model_path,
            save_interval=save_interval,
        )

        # 목표 에피소드 설정
        if target_episodes is not None:
            game_agent.set_target_episodes(target_episodes)

        print("🎮 Starting game with PPO agent...")
        PPOGameApp(game_agent)

    except KeyboardInterrupt:
        print("\n⚠️ Training interrupted by user (Ctrl+C).")
        if "game_agent" in locals() and enable_learning:
            game_agent.generate_final_plots("Training interrupted by user")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run PPO agent in the game environment."
    )
    parser.add_argument(
        "--model", type=str, default=None, help="Path to the saved PPO model"
    )
    parser.add_argument(
        "--skill", type=float, default=0.7, help="Player skill level (0 to 1)"
    )
    parser.add_argument(
        "--personality",
        type=int,
        default=1,
        help="Player personality (0: Defensive, 1: Aggressive)",
    )
    parser.add_argument(
        "--learn", action="store_true", help="Enable learning mode for the agent"
    )
    parser.add_argument(
        "--save-interval", type=int, default=1000, help="Model save interval (steps)"
    )
    parser.add_argument(
        "--target-episodes",
        type=int,
        default=None,
        help="Target number of episodes to run before auto-terminating.",
    )
    args = parser.parse_args()

    run_ppo_in_game(
        model_path=args.model,
        skill_level=args.skill,
        personality=args.personality,
        enable_learning=args.learn,
        save_interval=args.save_interval,
        target_episodes=args.target_episodes,
    )


if __name__ == "__main__":
    main()
