#!/usr/bin/env python
"""
PPO 에이전트와 실제 게임 연동 스크립트 (개선된 보상 시스템 통합)

훈련된 PPO 에이전트가 실제 게임 환경에서 플레이하도록 합니다.
게임 상태를 실시간으로 추출하여 에이전트에 전달하고,
에이전트의 액션을 게임 입력으로 변환합니다.

개선사항:
- 향상된 보상 시스템 (10배 생존 보상, 세분화된 마일스톤)
- 감소된 사망 페널티 (50% 감소)
- 공격 행동 장려 시스템
- 완전한 시각화 및 로깅

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


class ImprovedGameEnvironment(GameEnvironment):
    """개선된 보상 시스템을 가진 게임 환경"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 개선된 생존 마일스톤 (더 세분화된 보상)
        self.improved_survival_milestones = [
            (60, 15.0),  # 1초 - 첫 생존
            (120, 25.0),  # 2초 - 기본 생존
            (180, 40.0),  # 3초 - 안정적 생존
            (240, 60.0),  # 4초 - 좋은 생존
            (300, 100.0),  # 5초 - 우수한 생존
            (420, 150.0),  # 7초 - 뛰어난 생존
            (600, 250.0),  # 10초 - 탁월한 생존
            (900, 400.0),  # 15초 - 마스터 레벨
            (1200, 600.0),  # 20초 - 전문가 레벨
        ]

        print("🚀 Improved reward system activated!")

    def calculate_reward_improved(self, game_state, last_action: int) -> float:
        """개선된 보상 계산 시스템

        기존 보상 시스템을 기반으로 하되, 초기 학습 효율성을 높이는 개선사항 포함:
        1. 생존 보상 10배 증가 (0.01 → 0.1)
        2. 세분화된 마일스톤 (1초부터 시작)
        3. 감소된 사망 페널티 (-100 → -50)
        4. 공격 행동 장려 (추가 보상)
        5. 적극적 움직임 보상
        """
        total_reward = 0.0

        # 1. 향상된 기본 생존 보상 (기존의 10배)
        survival_reward = 0.1  # 기존 0.01에서 증가
        total_reward += survival_reward

        # 2. 개선된 생존 마일스톤 보상
        if self.previous_state is not None:
            for milestone_time, milestone_reward in self.improved_survival_milestones:
                if (
                    self.previous_state.survival_time
                    < milestone_time
                    <= game_state.survival_time
                ):
                    total_reward += milestone_reward
                    print(
                        f"🎉 IMPROVED MILESTONE: +{milestone_reward:.1f} ({milestone_time / 60:.1f}s)"
                    )

        # 3. 점수 증가 보상 (기존의 2배)
        if game_state.score > self.last_score:
            score_reward = (
                game_state.score - self.last_score
            ) * 0.2  # 기존 0.1에서 증가
            total_reward += score_reward

        # 4. 감소된 사망 페널티 (기존의 50%)
        if game_state.player_lives < self.last_lives:
            death_penalty = -50.0  # 기존 -100.0에서 감소
            total_reward += death_penalty
            print(f"💀 REDUCED DEATH PENALTY: {death_penalty:.1f}")

        # 5. 공격 행동 장려 보상
        if last_action == 8:  # FIRE 액션
            fire_reward = 1.0  # 공격 시 추가 보상
            total_reward += fire_reward

        # 6. 적극적 움직임 보상 (정적 상태 방지)
        if last_action != 4:  # 정지 액션이 아닐 때
            movement_reward = 0.1
            total_reward += movement_reward

        # 상태 업데이트
        self.last_score = game_state.score
        self.last_lives = game_state.player_lives
        self.previous_state = game_state

        return total_reward


class GamePPOAgent:
    """실제 게임과 연동되는 PPO 에이전트 래퍼 (개선된 보상 시스템 통합)

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
        speed_multiplier: int = 1,
        use_improved_rewards: bool = True,  # 개선된 보상 시스템 사용 여부
    ):
        """게임 PPO 에이전트 초기화

        Args:
            ppo_agent: PPO 에이전트 인스턴스
            skill_level: 플레이어 실력 수준 (0~1)
            personality: 플레이어 성향 (0: 방어적, 1: 공격적)
            enable_learning: 학습 모드 여부
            model_path: 모델 저장 경로 (학습 시에만 사용)
            save_interval: 모델 저장 간격 (스텝 단위)
            use_improved_rewards: 개선된 보상 시스템 사용 여부

        ---

        PPO 에이전트와 게임 어댑터를 초기화
        """
        self.ppo_agent = ppo_agent
        self.skill_level = skill_level
        self.personality = personality
        self.enable_learning = enable_learning
        self.model_path = model_path
        self.save_interval = save_interval
        self.speed_multiplier = speed_multiplier
        self.use_improved_rewards = use_improved_rewards

        # 개선된 환경으로 교체 (활성화된 경우)
        if use_improved_rewards:
            original_env = self.ppo_agent.env
            improved_env = ImprovedGameEnvironment(
                max_entities=original_env.max_entities,
                max_lives=original_env.max_lives,
                final_stage_num=original_env.final_stage_num,
            )
            self.ppo_agent.env = improved_env

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

        # 실시간 메트릭 추적
        self.best_score = 0
        self.best_reward = float("-inf")
        self.best_survival_time = 0.0  # 최고 생존 시간 추가
        self.last_survival_time = 0.0  # 이전 에피소드 생존 시간 추가
        self.training_start_time = time.time()

        # 시각화를 위한 통계 히스토리
        self.training_stats_history = []
        self.episode_survival_times = []
        self.episode_total_rewards = []

        if enable_learning:
            print(
                f"🤖 Learning Agent: {'Improved' if use_improved_rewards else 'Standard'} rewards"
            )
            if model_path:
                print(f"💾 Model saves to: {model_path}")

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

        # 통계 히스토리에 추가 (시각화용)
        self.training_stats_history.append(training_stats)

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
        """훈련 진행도 그래프 생성 (matplotlib 기반)

        ---

        에피소드 종료 시점에 현재까지의 훈련 진행도를 시각화
        """
        if not self.enable_learning:
            return

        try:
            import matplotlib.pyplot as plt
            import numpy as np

            if len(self.episode_total_rewards) < 2:
                print("📊 Not enough data for plotting (need at least 2 episodes)")
                return

            # 플롯 디렉토리 생성
            plot_dir = "src/plots"
            os.makedirs(plot_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 그래프 생성
            plt.figure(figsize=(15, 10))

            # 1. 에피소드 보상 그래프
            plt.subplot(2, 3, 1)
            episodes = range(1, len(self.episode_total_rewards) + 1)
            plt.plot(
                episodes,
                self.episode_total_rewards,
                alpha=0.7,
                color="blue",
                linewidth=1,
            )
            if len(self.episode_total_rewards) >= 10:
                # 이동 평균
                window = min(10, len(self.episode_total_rewards))
                moving_avg = []
                for i in range(len(self.episode_total_rewards)):
                    start_idx = max(0, i - window + 1)
                    moving_avg.append(
                        np.mean(self.episode_total_rewards[start_idx : i + 1])
                    )
                plt.plot(
                    episodes,
                    moving_avg,
                    color="red",
                    linewidth=2,
                    label=f"Moving Avg ({window})",
                )
                plt.legend()
            plt.title("Episode Total Rewards")
            plt.xlabel("Episode")
            plt.ylabel("Total Reward")
            plt.grid(True, alpha=0.3)

            # 2. 생존 시간 그래프
            plt.subplot(2, 3, 2)
            if self.episode_survival_times:
                plt.plot(
                    episodes,
                    self.episode_survival_times,
                    alpha=0.7,
                    color="green",
                    linewidth=1,
                )
                if len(self.episode_survival_times) >= 10:
                    window = min(10, len(self.episode_survival_times))
                    moving_avg = []
                    for i in range(len(self.episode_survival_times)):
                        start_idx = max(0, i - window + 1)
                        moving_avg.append(
                            np.mean(self.episode_survival_times[start_idx : i + 1])
                        )
                    plt.plot(
                        episodes,
                        moving_avg,
                        color="orange",
                        linewidth=2,
                        label=f"Moving Avg ({window})",
                    )
                    plt.legend()
                plt.title("Survival Time per Episode")
                plt.xlabel("Episode")
                plt.ylabel("Survival Time (seconds)")
                plt.grid(True, alpha=0.3)

            # 3. 학습 손실 (훈련 통계가 있는 경우)
            if self.training_stats_history:
                plt.subplot(2, 3, 3)
                policy_losses = [
                    stats.get("policy_loss", 0) for stats in self.training_stats_history
                ]
                value_losses = [
                    stats.get("value_loss", 0) for stats in self.training_stats_history
                ]
                training_steps = range(1, len(policy_losses) + 1)

                plt.plot(
                    training_steps,
                    policy_losses,
                    label="Policy Loss",
                    alpha=0.7,
                    linewidth=1,
                )
                plt.plot(
                    training_steps,
                    value_losses,
                    label="Value Loss",
                    alpha=0.7,
                    linewidth=1,
                )
                plt.title("Training Losses")
                plt.xlabel("Training Update")
                plt.ylabel("Loss")
                plt.legend()
                plt.grid(True, alpha=0.3)

            # 4. 보상 분포 히스토그램
            plt.subplot(2, 3, 4)
            if self.episode_total_rewards:
                plt.hist(
                    self.episode_total_rewards,
                    bins=min(20, len(self.episode_total_rewards)),
                    alpha=0.7,
                    color="skyblue",
                )
                plt.title("Reward Distribution")
                plt.xlabel("Total Reward")
                plt.ylabel("Frequency")
                plt.grid(True, alpha=0.3)

            # 5. 성능 트렌드 (최근 성과)
            plt.subplot(2, 3, 5)
            if len(self.episode_total_rewards) >= 20:
                recent_rewards = self.episode_total_rewards[-20:]
                recent_episodes = range(
                    len(self.episode_total_rewards) - 19,
                    len(self.episode_total_rewards) + 1,
                )
                plt.plot(
                    recent_episodes,
                    recent_rewards,
                    "o-",
                    alpha=0.8,
                    color="purple",
                    linewidth=2,
                )
                plt.title("Recent Performance (Last 20 Episodes)")
                plt.xlabel("Episode")
                plt.ylabel("Total Reward")
                plt.grid(True, alpha=0.3)

            # 6. 성능 요약 텍스트
            plt.subplot(2, 3, 6)
            plt.text(
                0.1,
                0.9,
                f"📊 Training Summary",
                fontsize=14,
                fontweight="bold",
                transform=plt.gca().transAxes,
            )
            plt.text(
                0.1,
                0.8,
                f"Episodes: {len(self.episode_total_rewards)}",
                fontsize=12,
                transform=plt.gca().transAxes,
            )
            plt.text(
                0.1,
                0.7,
                f"Best Survival: {self.best_survival_time:.1f}s",
                fontsize=12,
                transform=plt.gca().transAxes,
            )

            if self.episode_total_rewards:
                plt.text(
                    0.1,
                    0.6,
                    f"Best Reward: {max(self.episode_total_rewards):+.1f}",
                    fontsize=12,
                    transform=plt.gca().transAxes,
                )
                plt.text(
                    0.1,
                    0.5,
                    f"Avg Reward: {np.mean(self.episode_total_rewards):+.1f}",
                    fontsize=12,
                    transform=plt.gca().transAxes,
                )

                recent_10 = (
                    self.episode_total_rewards[-10:]
                    if len(self.episode_total_rewards) >= 10
                    else self.episode_total_rewards
                )
                plt.text(
                    0.1,
                    0.4,
                    f"Recent 10 Avg: {np.mean(recent_10):+.1f}",
                    fontsize=12,
                    transform=plt.gca().transAxes,
                )

            plt.text(
                0.1,
                0.3,
                f"Best Score: {self.best_score:,}",
                fontsize=12,
                transform=plt.gca().transAxes,
            )
            plt.text(
                0.1,
                0.2,
                f"Reward System: {'Improved' if self.use_improved_rewards else 'Standard'}",
                fontsize=12,
                transform=plt.gca().transAxes,
            )
            plt.text(
                0.1,
                0.1,
                f"Training Steps: {self.step_count:,}",
                fontsize=12,
                transform=plt.gca().transAxes,
            )

            plt.axis("off")

            plt.tight_layout()

            # 저장
            plot_path = os.path.join(plot_dir, f"training_progress_{timestamp}.png")
            plt.savefig(plot_path, dpi=150, bbox_inches="tight")

            # 최신 버전으로도 저장
            latest_path = os.path.join(plot_dir, "latest_training_progress.png")
            plt.savefig(latest_path, dpi=150, bbox_inches="tight")

            print(f"📊 Enhanced training plots saved: {plot_path}")
            plt.close()

        except ImportError:
            print("⚠️ matplotlib not available - using fallback plot generator")
            try:
                # plot_training_progress 모듈 사용 (기존 방식)
                from plot_training_progress import TrainingPlotter

                plotter = TrainingPlotter(log_dir=self.log_dir, output_dir="plots")
                success = plotter.generate_all_plots()
                if success:
                    print(f"📊 Training plots generated in plots/ directory")
            except ImportError:
                print("⚠️ plot_training_progress.py not found - plots not generated")
        except Exception as e:
            print(f"⚠️ Failed to generate plots: {e}")
            print(f"Error details: {traceback.format_exc()}")

    def set_game_instance(self, game_instance):
        """게임 인스턴스 설정

        Args:
            game_instance: App 인스턴스

        ---

        게임과의 연결을 설정하여 실제 게임 상태에 접근 가능하게 함
        """
        self.game_instance = game_instance

    def connect_game(self, game_instance):
        """게임과 연결 설정 (App.py에서 호출되는 메서드)

        Args:
            game_instance: 게임 인스턴스

        ---

        App 클래스에서 에이전트 초기화 시 호출되는 메서드
        """
        self.set_game_instance(game_instance)

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

            # 목표 에피소드 달성 체크 (더 자주 확인)
            if self.target_episodes and self.episode_count >= self.target_episodes:
                if not self.training_complete:
                    print(f"\n🎯 Target episodes ({self.target_episodes}) reached!")
                    self.training_complete = True
                    self.generate_final_plots(
                        f"Target episodes ({self.target_episodes}) completed"
                    )

                    # 게임 종료 시도
                    print(f"🔚 Automatically terminating game...")
                    if self.game_instance and hasattr(self.game_instance, "quit"):
                        self.game_instance.quit()
                    elif hasattr(self.game_instance, "running"):
                        self.game_instance.running = False

                    try:
                        px.quit()
                    except:
                        pass

                    import sys

                    print("✅ Training completed and game terminated!")
                    sys.exit(0)
                return 4

            # 에피소드 종료 감지 (학습/비학습 모드 공통)
            done = self._is_episode_done(game_state)

            if self.enable_learning:
                action, log_prob, value = self.ppo_agent.select_action_with_exploration(
                    game_state
                )
                if self.last_game_state is not None and self.last_action is not None:
                    # 개선된 보상 시스템 사용
                    if self.use_improved_rewards and hasattr(
                        self.ppo_agent.env, "calculate_reward_improved"
                    ):
                        reward = self.ppo_agent.env.calculate_reward_improved(
                            game_state, self.last_action
                        )
                    else:
                        reward = self.ppo_agent.env.calculate_reward(
                            game_state, self.last_action
                        )

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

                        # 목표 달성 즉시 체크
                        if (
                            self.target_episodes
                            and self.episode_count >= self.target_episodes
                        ):
                            self.training_complete = True
                            return 4  # 즉시 중립 액션 반환

                self.last_log_prob = log_prob
                self.last_value = value

                # 버퍼가 가득 차면 학습을 수행합니다.
                if self.ppo_agent.is_buffer_full():
                    print("🧠 Buffer is full, starting training...")
                    training_stats = self.ppo_agent.train()
                    if training_stats:
                        self.log_training_metrics(training_stats)
            else:
                # 비학습 모드에서도 에피소드 관리
                action = self.ppo_agent.select_action(game_state)

                # 비학습 모드에서도 에피소드 종료 처리
                if self.last_game_state is not None and done:
                    self._handle_episode_end()

                    # 목표 달성 즉시 체크
                    if (
                        self.target_episodes
                        and self.episode_count >= self.target_episodes
                    ):
                        self.training_complete = True
                        return 4

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
                return self._create_dummy_game_state()

            # 게임 어댑터를 사용하여 실제 게임 상태 추출
            extracted_state = self.adapter.extract_game_state(
                self.game_instance,
                self.skill_level,
                self.personality,
            )

            # 추출된 상태 검증
            if extracted_state is None:
                return self._create_dummy_game_state()

            return extracted_state

        except Exception as e:
            print(f"❌ Error extracting game state: {e}", file=sys.stderr)
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
                    state_name = current_state.name
                    if state_name in ["GAME_OVER", "GAMEOVER", "GAME_END"]:
                        print(f"🏁 Episode done: Game state is {state_name}")
                        return True

            # 게임 변수에서 직접 확인
            if hasattr(game, "game_vars"):
                game_vars = game.game_vars
                lives_count = getattr(game_vars, "lives", None)
                if lives_count is not None and lives_count <= 0:
                    print(f"🏁 Episode done: Game vars lives = {lives_count}")
                    return True

                # 스테이지 완주 확인 (최종 스테이지 도달)
                if hasattr(game_vars, "stage_num"):
                    current_stage = getattr(game_vars, "stage_num", 1)
                    if current_stage >= 8:  # 최종 스테이지 (게임에 따라 조정)
                        print(f"🏁 Episode done: Final stage {current_stage} reached")
                        return True

        # 매우 긴 에피소드 강제 종료 (무한 루프 방지)
        episode_length = self.step_count - self.episode_start_step
        max_episode_length = 8000 if not self.fast_mode else 5000

        if episode_length > max_episode_length:
            print(
                f"🏁 Episode done: Maximum episode length reached ({episode_length} steps)"
            )
            return True

        # 강제 에피소드 종료 조건 추가 (매우 짧은 생존 시간 연속 발생)
        survival_seconds = episode_length / 60.0
        if survival_seconds < 0.5 and episode_length > 30:  # 0.5초 미만이고 30스텝 이상
            print(
                f"🏁 Episode done: Very short survival detected ({survival_seconds:.2f}s)"
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

        # 액션 분포 출력 (간소화)
        if self.episode_count % 5 == 0:  # 5 에피소드마다만 상세 출력
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

        # 최고 기록 업데이트
        if self.total_reward > self.best_reward:
            self.best_reward = self.total_reward
        if final_score > self.best_score:
            self.best_score = final_score

        # 생존 시간 계산 및 기록 업데이트 (실제 플레이 시간)
        survival_seconds = episode_length / 60.0  # 에이전트가 취한 액션 수 기준
        if survival_seconds > self.best_survival_time:
            self.best_survival_time = survival_seconds

        # 시각화용 데이터 저장
        self.episode_survival_times.append(survival_seconds)
        self.episode_total_rewards.append(self.total_reward)

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
            print(f"   ✅ Good survival time!")

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
            print(f"\n🎯 Target episodes ({self.target_episodes}) reached!")
            print(f"📊 Episodes: {self.episode_count}, Steps: {self.step_count}")

            # 그래프 생성
            try:
                self.generate_final_plots(
                    f"Target episodes ({self.target_episodes}) completed"
                )
                print("📊 Final plots generated.")
            except Exception as e:
                print(f"⚠️ Failed to generate plots: {e}")

            # 게임 종료
            print(f"🔚 Terminating game...")
            try:
                if self.game_instance and hasattr(self.game_instance, "quit"):
                    self.game_instance.quit()
                elif hasattr(self.game_instance, "running"):
                    self.game_instance.running = False

                px.quit()
                import sys

                sys.exit(0)

            except Exception as e:
                print(f"⚠️ Error during termination: {e}")
                import os

                os._exit(0)

        # 주기적 그래프 생성 (매 20 에피소드마다)
        if (
            self.enable_learning
            and self.episode_count % 20 == 0
            and self.episode_count > 0
        ):
            print(
                f"📊 Generating periodic training plots (Episode {self.episode_count})..."
            )
            self.generate_training_plots()

        # 주기적 그래프 생성만 처리 (목표 달성 시는 위에서 이미 처리됨)
        if should_generate_plots and not should_terminate_game:
            self.generate_final_plots(
                f"Target episodes ({self.target_episodes}) completed"
            )

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

    def __init__(self, game_ppo_agent: "GamePPOAgent", speed_multiplier: int = 1):
        """앱 초기화

        Args:
            game_ppo_agent: PPO 에이전트 래퍼
            speed_multiplier: 게임 배속 (1=정상속도, 2=2배속, 등...)
        """
        self.game_agent = game_ppo_agent
        # game_agent에 self(App 인스턴스)를 연결합니다.
        self.game_agent.set_game_instance(self)
        # App의 생성자를 호출합니다. 이 안에서 px.run()이 호출되어 게임이 시작됩니다.
        super().__init__(agent=game_ppo_agent, speed_multiplier=speed_multiplier)

    def update(self):
        """게임 업데이트 (에이전트 연동 + 속도 모드 적용)"""
        # 에이전트로부터 액션 받아오기 (입력 처리는 프레임당 한 번만)
        action = self.game_agent.select_action()

        # 액션을 게임 입력으로 변환하여 적용
        self.apply_agent_action(action)

        # 입력 처리는 프레임당 한 번만 (배속 영향 없음)
        self.input.update()

        # 게임 로직을 speed_multiplier만큼 반복 실행 (배속 적용!)
        for _ in range(self.speed_multiplier):
            self.game.update()


def find_latest_model() -> Optional[str]:
    """가장 최근 PPO 모델 찾기"""
    model_dir = "src/models/ppo"
    if not os.path.exists(model_dir):
        return None

    models = [f for f in os.listdir(model_dir) if f.endswith(".pth")]
    if not models:
        return None

    # 파일명의 타임스탬프로 정렬
    models.sort(reverse=True)
    latest_model = os.path.join(model_dir, models[0])
    return latest_model


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
            print(f"✅ Model loaded from {model_path}")
        except Exception as e:
            print(f"⚠️ Failed to load model, starting fresh.")
    else:
        print("🆕 Starting with new model.")

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
    speed_multiplier: int = 1,
    use_improved_rewards: bool = True,
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
        speed_multiplier: 게임 배속 (1=정상속도, 2=2배속, 등...)
        use_improved_rewards: 개선된 보상 시스템 사용 여부
    """
    try:
        # 학습 모드이고 모델 경로가 지정되지 않은 경우, 자동 경로 생성
        if enable_learning and not model_path:
            model_dir = os.path.join("models", "ppo")
            os.makedirs(model_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = os.path.join(model_dir, f"ppo_agent_{timestamp}.pth")

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
            speed_multiplier=speed_multiplier,
            use_improved_rewards=use_improved_rewards,
        )

        # 목표 에피소드 설정
        if target_episodes is not None:
            game_agent.set_target_episodes(target_episodes)

        if speed_multiplier > 1:
            print(f"🚀 Speed: {speed_multiplier}x")
        print("🎮 Starting game...")
        app = PPOGameApp(game_agent, speed_multiplier=speed_multiplier)
        app.run()

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
        description="Run PPO agent in the game environment with improved reward system."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Path to the saved PPO model (default: auto-detect latest)",
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
    parser.add_argument(
        "--speed",
        type=int,
        default=1,
        help="Game speed multiplier (1=normal, 2=2x speed, etc.). Higher values reduce training time.",
    )
    parser.add_argument(
        "--no-improved-rewards",
        action="store_true",
        help="Disable improved reward system (use standard rewards)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start with fresh model (ignore existing models)",
    )
    args = parser.parse_args()

    # 모델 경로 결정
    model_path = None
    if not args.fresh:
        if args.model:
            if os.path.exists(args.model):
                model_path = args.model
            else:
                print(f"❌ 지정된 모델을 찾을 수 없습니다: {args.model}")
                return
        else:
            model_path = find_latest_model()
            if model_path:
                print(f"🔍 자동 감지된 최신 모델: {model_path}")

    use_improved_rewards = not args.no_improved_rewards

    print(f"🎮 PPO Agent Launch")
    print(
        f"📋 Config: Learning={args.learn}, Speed={args.speed}x, Episodes={args.target_episodes or 'unlimited'}"
    )
    if model_path:
        print(f"📁 Model: {model_path}")
    else:
        print(f"📁 Starting with new model")

    run_ppo_in_game(
        model_path=model_path,
        skill_level=args.skill,
        personality=args.personality,
        enable_learning=args.learn,
        save_interval=args.save_interval,
        target_episodes=args.target_episodes,
        speed_multiplier=args.speed,
        use_improved_rewards=use_improved_rewards,
    )


if __name__ == "__main__":
    main()
