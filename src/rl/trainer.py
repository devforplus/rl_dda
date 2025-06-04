import os
import time
import numpy as np
from typing import Dict, Any, Optional, Callable, List
from collections import deque
import torch

from .agents.ppo_agent import PPOAgent
from .environment import GameEnvironment
from .game_adapter import GameStateAdapter


class PPOTrainer:
    """PPO 에이전트 학습 및 평가를 위한 트레이너 클래스

    에이전트의 학습, 평가, 모델 저장 등을 관리합니다.

    Attributes:
        agent: PPO 에이전트
        game_adapter: 게임 상태 어댑터
        save_dir: 모델 저장 디렉토리

    ---

    PPO 에이전트의 전체 학습 파이프라인을 관리하는 클래스
    """

    def __init__(
        self,
        agent: PPOAgent,
        save_dir: str = "models",
        log_interval: int = 10,
        save_interval: int = 100,
        eval_interval: int = 50,
    ):
        """트레이너 초기화

        Args:
            agent: PPO 에이전트
            save_dir: 모델 저장 디렉토리
            log_interval: 로그 출력 간격 (에피소드)
            save_interval: 모델 저장 간격 (에피소드)
            eval_interval: 평가 수행 간격 (에피소드)

        ---

        학습 환경과 로깅 시스템을 초기화
        """
        self.agent = agent
        self.game_adapter = GameStateAdapter()
        self.save_dir = save_dir
        self.log_interval = log_interval
        self.save_interval = save_interval
        self.eval_interval = eval_interval

        # 디렉토리 생성
        os.makedirs(save_dir, exist_ok=True)

        # 학습 통계 추적
        self.total_episodes = 0
        self.total_steps = 0
        self.best_reward = float("-inf")

        # 최근 성능 추적
        self.recent_rewards = deque(maxlen=100)
        self.recent_episode_lengths = deque(maxlen=100)

        # 텐서보드 로거 (옵션)
        self.tensorboard_logger = None
        try:
            from torch.utils.tensorboard import SummaryWriter

            log_dir = os.path.join(save_dir, "logs")
            self.tensorboard_logger = SummaryWriter(log_dir)
        except ImportError:
            print("TensorBoard not available. Logging will be done to console only.")

    def train_episode(
        self,
        game_instance,
        skill_level: float = 0.5,
        personality: int = 0,
        max_steps: int = 5000,
    ) -> Dict[str, float]:
        """단일 에피소드 학습

        Args:
            game_instance: 게임 인스턴스
            skill_level: 플레이어 실력 수준
            personality: 플레이어 성향
            max_steps: 최대 스텝 수

        Returns:
            에피소드 통계

        ---

        하나의 에피소드를 실행하며 경험을 수집하고 모델을 업데이트
        """
        self.agent.set_train_mode()
        self.game_adapter.reset_tracking()

        episode_reward = 0.0
        episode_length = 0
        done = False

        # 에피소드 시작
        start_time = time.time()

        while not done and episode_length < max_steps:
            # 현재 게임 상태 추출
            current_state = self.game_adapter.extract_game_state(
                game_instance, skill_level, personality
            )

            # 에이전트 액션 선택 (탐험 포함)
            action, log_prob, value = self.agent.select_action_with_exploration(
                current_state
            )

            # 게임에 액션 적용
            self.game_adapter.apply_action_to_game(game_instance, action)

            # 게임 한 스텝 실행 (이 부분은 게임 루프에서 처리됨)
            # 여기서는 다음 상태를 얻기 위해 잠시 대기
            time.sleep(0.016)  # 약 60FPS

            # 다음 상태 추출
            next_state = self.game_adapter.extract_game_state(
                game_instance, skill_level, personality
            )

            # 보상 계산
            reward = self.agent.env.calculate_reward(next_state, action)

            # 에피소드 종료 조건 확인
            done = self._check_episode_done(
                game_instance, next_state, episode_length, max_steps
            )

            # 경험 저장
            self.agent.store_experience(
                current_state, action, reward, log_prob, value, done
            )

            episode_reward += reward
            episode_length += 1
            self.total_steps += 1

        # 에피소드 종료 후 학습
        training_stats = self.agent.train()

        # 통계 업데이트
        self.total_episodes += 1
        self.recent_rewards.append(episode_reward)
        self.recent_episode_lengths.append(episode_length)

        # 최고 성능 업데이트
        if episode_reward > self.best_reward:
            self.best_reward = episode_reward
            self._save_best_model()

        episode_time = time.time() - start_time

        # 에피소드 통계 반환
        stats = {
            "episode_reward": episode_reward,
            "episode_length": episode_length,
            "episode_time": episode_time,
            "total_episodes": self.total_episodes,
            "total_steps": self.total_steps,
            "best_reward": self.best_reward,
        }

        # 학습 통계 추가
        if training_stats:
            stats.update(training_stats)

        return stats

    def evaluate_agent(
        self,
        game_instance,
        skill_level: float = 0.5,
        personality: int = 0,
        num_episodes: int = 5,
        max_steps: int = 5000,
    ) -> Dict[str, float]:
        """에이전트 평가

        Args:
            game_instance: 게임 인스턴스
            skill_level: 플레이어 실력 수준
            personality: 플레이어 성향
            num_episodes: 평가 에피소드 수
            max_steps: 에피소드당 최대 스텝 수

        Returns:
            평가 통계

        ---

        학습된 에이전트를 여러 에피소드에 걸쳐 평가
        """
        self.agent.set_eval_mode()

        eval_rewards = []
        eval_lengths = []
        eval_survival_times = []

        for episode in range(num_episodes):
            self.game_adapter.reset_tracking()
            episode_reward = 0.0
            episode_length = 0
            done = False

            while not done and episode_length < max_steps:
                # 현재 상태 추출
                current_state = self.game_adapter.extract_game_state(
                    game_instance, skill_level, personality
                )

                # 결정적 액션 선택 (탐험 없음)
                action = self.agent.select_action(current_state)

                # 액션 적용
                self.game_adapter.apply_action_to_game(game_instance, action)

                # 게임 스텝 실행
                time.sleep(0.016)

                # 다음 상태와 보상
                next_state = self.game_adapter.extract_game_state(
                    game_instance, skill_level, personality
                )
                reward = self.agent.env.calculate_reward(next_state, action)

                # 종료 조건 확인
                done = self._check_episode_done(
                    game_instance, next_state, episode_length, max_steps
                )

                episode_reward += reward
                episode_length += 1

            eval_rewards.append(episode_reward)
            eval_lengths.append(episode_length)
            eval_survival_times.append(current_state.survival_time)

        # 평가 통계 계산
        return {
            "eval_mean_reward": np.mean(eval_rewards),
            "eval_std_reward": np.std(eval_rewards),
            "eval_max_reward": np.max(eval_rewards),
            "eval_min_reward": np.min(eval_rewards),
            "eval_mean_length": np.mean(eval_lengths),
            "eval_mean_survival_time": np.mean(eval_survival_times),
        }

    def train(
        self,
        game_factory: Callable,
        num_episodes: int = 1000,
        skill_level: float = 0.5,
        personality: int = 0,
        max_steps_per_episode: int = 5000,
    ) -> Dict[str, List[float]]:
        """전체 학습 프로세스 실행

        Args:
            game_factory: 게임 인스턴스를 생성하는 팩토리 함수
            num_episodes: 총 학습 에피소드 수
            skill_level: 플레이어 실력 수준
            personality: 플레이어 성향
            max_steps_per_episode: 에피소드당 최대 스텝 수

        Returns:
            학습 과정의 통계 히스토리

        ---

        지정된 에피소드 수만큼 학습을 수행하고 주기적으로 평가 및 저장
        """
        print(f"Starting PPO training for {num_episodes} episodes...")
        print(f"Skill Level: {skill_level}, Personality: {personality}")
        print(f"Save Directory: {self.save_dir}")

        # 통계 히스토리
        history = {
            "episode_rewards": [],
            "episode_lengths": [],
            "training_losses": [],
            "eval_rewards": [],
        }

        for episode in range(num_episodes):
            # 게임 인스턴스 생성
            game_instance = game_factory()

            # 에피소드 학습
            episode_stats = self.train_episode(
                game_instance, skill_level, personality, max_steps_per_episode
            )

            # 통계 기록
            history["episode_rewards"].append(episode_stats["episode_reward"])
            history["episode_lengths"].append(episode_stats["episode_length"])
            if "total_loss" in episode_stats:
                history["training_losses"].append(episode_stats["total_loss"])

            # 주기적 로깅
            if episode % self.log_interval == 0:
                self._log_training_progress(episode, episode_stats)

            # 주기적 평가
            if episode % self.eval_interval == 0 and episode > 0:
                eval_game = game_factory()
                eval_stats = self.evaluate_agent(eval_game, skill_level, personality)
                history["eval_rewards"].append(eval_stats["eval_mean_reward"])
                self._log_evaluation_results(episode, eval_stats)

            # 주기적 모델 저장
            if episode % self.save_interval == 0 and episode > 0:
                self._save_checkpoint(episode)

            # 텐서보드 로깅
            if self.tensorboard_logger:
                self._log_to_tensorboard(episode, episode_stats)

        # 최종 모델 저장
        self._save_final_model()

        print(f"Training completed! Best reward: {self.best_reward:.2f}")
        return history

    def _check_episode_done(
        self, game_instance, game_state, episode_length: int, max_steps: int
    ) -> bool:
        """에피소드 종료 조건 확인

        Args:
            game_instance: 게임 인스턴스
            game_state: 현재 게임 상태
            episode_length: 현재 에피소드 길이
            max_steps: 최대 스텝 수

        Returns:
            에피소드 종료 여부

        ---

        게임 종료 상태와 최대 스텝 수를 고려하여 에피소드 종료 여부 결정
        """
        # 최대 스텝 수 도달
        if episode_length >= max_steps:
            return True

        # 플레이어 체력이 0 이하
        if game_state.player_hp <= 0:
            return True

        # 게임 상태에 따른 종료 조건 (게임마다 다를 수 있음)
        if hasattr(game_instance, "game") and game_instance.game:
            game_state_obj = getattr(game_instance.game, "state", None)
            if game_state_obj and hasattr(game_state_obj, "state"):
                # 게임오버 상태인지 확인
                if hasattr(game_state_obj, "state") and str(
                    game_state_obj.state
                ).endswith("GAME_OVER"):
                    return True

        return False

    def _log_training_progress(self, episode: int, stats: Dict[str, float]):
        """학습 진행 상황 로깅

        Args:
            episode: 에피소드 번호
            stats: 에피소드 통계

        ---

        콘솔에 학습 진행 상황을 출력
        """
        recent_mean_reward = np.mean(self.recent_rewards) if self.recent_rewards else 0
        recent_mean_length = (
            np.mean(self.recent_episode_lengths) if self.recent_episode_lengths else 0
        )

        print(
            f"Episode {episode:4d} | "
            f"Reward: {stats['episode_reward']:6.2f} | "
            f"Length: {stats['episode_length']:4d} | "
            f"Recent Avg: {recent_mean_reward:6.2f} | "
            f"Best: {self.best_reward:6.2f}"
        )

        if "total_loss" in stats:
            print(
                f"         Loss: {stats['total_loss']:8.4f} | "
                f"Policy: {stats.get('policy_loss', 0):8.4f} | "
                f"Value: {stats.get('value_loss', 0):8.4f}"
            )

    def _log_evaluation_results(self, episode: int, eval_stats: Dict[str, float]):
        """평가 결과 로깅

        Args:
            episode: 에피소드 번호
            eval_stats: 평가 통계

        ---

        평가 결과를 콘솔에 출력
        """
        print(f"=== Evaluation at Episode {episode} ===")
        print(
            f"Mean Reward: {eval_stats['eval_mean_reward']:6.2f} ± {eval_stats['eval_std_reward']:6.2f}"
        )
        print(f"Max Reward:  {eval_stats['eval_max_reward']:6.2f}")
        print(f"Mean Length: {eval_stats['eval_mean_length']:6.2f}")
        print(f"Mean Survival: {eval_stats['eval_mean_survival_time']:6.2f}")
        print("=" * 40)

    def _log_to_tensorboard(self, episode: int, stats: Dict[str, float]):
        """텐서보드에 통계 로깅

        Args:
            episode: 에피소드 번호
            stats: 통계 정보

        ---

        텐서보드를 사용한 시각적 로깅
        """
        if not self.tensorboard_logger:
            return

        # 기본 통계
        self.tensorboard_logger.add_scalar(
            "Training/EpisodeReward", stats["episode_reward"], episode
        )
        self.tensorboard_logger.add_scalar(
            "Training/EpisodeLength", stats["episode_length"], episode
        )

        # 학습 손실
        if "total_loss" in stats:
            self.tensorboard_logger.add_scalar(
                "Training/TotalLoss", stats["total_loss"], episode
            )
            self.tensorboard_logger.add_scalar(
                "Training/PolicyLoss", stats.get("policy_loss", 0), episode
            )
            self.tensorboard_logger.add_scalar(
                "Training/ValueLoss", stats.get("value_loss", 0), episode
            )
            self.tensorboard_logger.add_scalar(
                "Training/Entropy", stats.get("entropy", 0), episode
            )

        # 최근 평균 성능
        if self.recent_rewards:
            recent_mean = np.mean(self.recent_rewards)
            self.tensorboard_logger.add_scalar(
                "Training/RecentMeanReward", recent_mean, episode
            )

    def _save_checkpoint(self, episode: int):
        """체크포인트 저장

        Args:
            episode: 에피소드 번호

        ---

        주기적으로 모델 체크포인트를 저장
        """
        checkpoint_path = os.path.join(
            self.save_dir, f"checkpoint_episode_{episode}.pth"
        )
        self.agent.save_model(checkpoint_path)
        print(f"Checkpoint saved: {checkpoint_path}")

    def _save_best_model(self):
        """최고 성능 모델 저장

        ---

        현재까지 최고 성능을 기록한 모델을 저장
        """
        best_path = os.path.join(self.save_dir, "best_model.pth")
        self.agent.save_model(best_path)

    def _save_final_model(self):
        """최종 모델 저장

        ---

        학습 완료 후 최종 모델을 저장
        """
        final_path = os.path.join(self.save_dir, "final_model.pth")
        self.agent.save_model(final_path)
        print(f"Final model saved: {final_path}")

    def load_checkpoint(self, checkpoint_path: str):
        """체크포인트 불러오기

        Args:
            checkpoint_path: 체크포인트 파일 경로

        ---

        저장된 체크포인트로부터 모델을 복원
        """
        self.agent.load_model(checkpoint_path)
        print(f"Model loaded from: {checkpoint_path}")

    def close(self):
        """트레이너 종료

        ---

        텐서보드 로거 등 리소스를 정리
        """
        if self.tensorboard_logger:
            self.tensorboard_logger.close()


def create_trainer(
    skill_level: float = 0.5,
    personality: int = 0,
    save_dir: str = "models/ppo",
    **agent_kwargs,
) -> PPOTrainer:
    """PPO 트레이너 생성 헬퍼 함수

    Args:
        skill_level: 플레이어 실력 수준
        personality: 플레이어 성향
        save_dir: 모델 저장 디렉토리
        **agent_kwargs: PPO 에이전트 하이퍼파라미터

    Returns:
        초기화된 PPO 트레이너

    ---

    간편하게 PPO 트레이너를 생성하는 팩토리 함수
    """
    from .agents.ppo_agent import create_ppo_agent

    # PPO 에이전트 생성
    agent = create_ppo_agent(
        skill_level=skill_level, personality=personality, **agent_kwargs
    )

    # 트레이너 생성
    trainer = PPOTrainer(agent, save_dir=save_dir)

    return trainer
