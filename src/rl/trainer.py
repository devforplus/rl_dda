"""
PPO 트레이너 구현

PPO 에이전트의 학습 및 평가를 관리하는 클래스
"""

import os
import time
import numpy as np
from typing import Dict, Any, Optional, List, Callable, Tuple
from collections import deque
import torch
import matplotlib.pyplot as plt
import matplotlib
from datetime import datetime

# 백엔드 설정 (GUI 없는 환경 대응)
matplotlib.use("Agg")

from .ppo_agent import PPOAgent
from .environment import GameEnvironment
from .data_types import GameLogData
from .curriculum import StepCurriculum, LinearCurriculum, CurriculumStage


class PPOTrainer:
    """PPO 에이전트 학습 및 평가를 위한 트레이너 클래스

    에이전트의 학습, 평가, 모델 저장 등을 관리합니다.
    """

    def __init__(
        self,
        agent: PPOAgent,
        environment: GameEnvironment,
        save_dir: str = "src/models/ppo",
        log_interval: int = 10,
        save_interval: int = 100,
        max_episode_steps: int = 1000,
        batch_size: int = 256,  # Optuna 최적화: 64 → 256 (안정성 4배 향상)
        num_epochs: int = 4,  # 이미 최적값
    ):
        """트레이너 초기화

        Args:
            agent: PPO 에이전트
            environment: 게임 환경
            save_dir: 모델 저장 디렉토리
            log_interval: 로그 출력 간격 (에피소드)
            save_interval: 모델 저장 간격 (에피소드)
            max_episode_steps: 에피소드당 최대 스텝 수
            batch_size: PPO 업데이트 배치 크기
            num_epochs: PPO 업데이트 에포크 수
        """
        self.agent = agent
        self.environment = environment
        self.save_dir = save_dir
        self.log_interval = log_interval
        self.save_interval = save_interval
        self.max_episode_steps = max_episode_steps
        self.batch_size = batch_size
        self.num_epochs = num_epochs

        # 학습 통계
        self.episode_rewards = deque(maxlen=100)
        self.episode_lengths = deque(maxlen=100)
        self.episode_kills = deque(maxlen=100)
        self.episode_scores = deque(maxlen=100)

        # 학습 상태
        self.total_episodes = 0
        self.total_steps = 0
        self.best_reward = float("-inf")

        # 디렉토리 생성
        os.makedirs(save_dir, exist_ok=True)

    def train_episode(self, game_instance, skill_level: float) -> Dict[str, Any]:
        """단일 에피소드 학습

        Args:
            game_instance: 게임 인스턴스
            skill_level: 실력값 (0.0 ~ 1.0)

        Returns:
            에피소드 결과 통계
        """
        # 환경 및 에이전트 초기화
        self.environment.reset()
        self.agent.reset_buffer()

        episode_reward = 0.0
        episode_steps = 0
        episode_kills = 0
        episode_score = 0

        # 게임 루프
        for step in range(self.max_episode_steps):
            # 현재 게임 상태 추출
            game_log_data = self.environment.extract_game_log_data(
                game_instance, skill_level
            )

            # 에이전트 액션 선택
            action_id = self.agent.get_action(game_log_data)

            # 게임에 액션 적용 (실제 게임과의 연동은 상위 레벨에서 처리)
            action_input = self.environment.get_action_input(action_id)

            # 한 스텝 진행 (여기서는 가정적으로 처리, 실제로는 게임 루프에서 처리)
            # game_instance.update(action_input)  # 실제 구현 시 필요

            # 보상 계산
            reward = self.environment.calculate_reward(game_instance, skill_level)

            # 종료 조건 확인
            done = self.environment.is_episode_done(game_instance)

            # 에이전트에 보상과 종료 상태 저장
            self.agent.store_reward_and_done(reward, done)

            # 통계 업데이트
            episode_reward += reward
            episode_steps += 1

            if done:
                break

        # 에피소드 종료 후 통계 수집
        if hasattr(game_instance, "game") and game_instance.game:
            game_vars = getattr(game_instance.game, "game_vars", None)
            if game_vars:
                episode_kills = getattr(game_vars, "kills", 0)
                episode_score = getattr(game_vars, "score", 0)

        # 에이전트 업데이트 (하이퍼파라미터 전달)
        update_info = self.agent.update(
            num_epochs=self.num_epochs, batch_size=self.batch_size
        )

        # 통계 저장
        self.episode_rewards.append(episode_reward)
        self.episode_lengths.append(episode_steps)
        self.episode_kills.append(episode_kills)
        self.episode_scores.append(episode_score)

        self.total_episodes += 1
        self.total_steps += episode_steps

        # 최고 보상 업데이트
        if episode_reward > self.best_reward:
            self.best_reward = episode_reward

        return {
            "episode": self.total_episodes,
            "reward": episode_reward,
            "steps": episode_steps,
            "kills": episode_kills,
            "score": episode_score,
            "update_info": update_info,
        }

    def train(
        self,
        game_instance,
        skill_level: float,
        num_episodes: int,
    ) -> List[Dict[str, Any]]:
        """다중 에피소드 학습

        Args:
            game_instance: 게임 인스턴스
            skill_level: 실력값
            num_episodes: 학습할 에피소드 수

        Returns:
            모든 에피소드 결과 리스트
        """
        results = []

        print(f"PPO 학습 시작: {num_episodes} 에피소드, 실력값 = {skill_level:.2f}")

        for episode in range(num_episodes):
            start_time = time.time()

            # 에피소드 학습
            episode_result = self.train_episode(game_instance, skill_level)

            episode_time = time.time() - start_time
            episode_result["time"] = episode_time

            results.append(episode_result)

            # 로그 출력
            if episode % self.log_interval == 0:
                self._log_progress(episode_result)

            # 모델 저장
            if episode % self.save_interval == 0 and episode > 0:
                self.agent.save_model(self.save_dir)

        # 최종 모델 저장
        self.agent.save_model(self.save_dir)

        # 학습 진행 그래프 생성
        plot_path = self.plot_training_progress()

        print(f"학습 완료! 총 {num_episodes} 에피소드")
        self._print_final_stats()

        return results

    def train_with_curriculum(
        self,
        game_instance,
        num_episodes: int,
        curriculum: "StepCurriculum | LinearCurriculum",
    ) -> List[Dict[str, Any]]:
        """커리큘럼 기반 다중 에피소드 학습

        Args:
            game_instance: 게임 인스턴스
            num_episodes: 학습할 에피소드 수
            curriculum: skill_level 스케줄러 (단계형/선형)

        Returns:
            모든 에피소드 결과 리스트
        """
        results: List[Dict[str, Any]] = []

        print(
            f"PPO 커리큘럼 학습 시작: {num_episodes} 에피소드, 스케줄러={type(curriculum).__name__}"
        )

        for episode in range(num_episodes):
            skill_level, stage_name = curriculum.skill_for_episode(episode)

            # 로그: 단계와 스킬 표시
            if episode % self.log_interval == 0:
                print(
                    f"[Curriculum] Ep {episode:4d} | Stage: {stage_name} | skill={skill_level:.2f}"
                )

            start_time = time.time()
            episode_result = self.train_episode(game_instance, skill_level)
            episode_time = time.time() - start_time
            episode_result["time"] = episode_time
            episode_result["skill_level"] = skill_level
            episode_result["stage"] = stage_name
            results.append(episode_result)

            if episode % self.log_interval == 0:
                self._log_progress(episode_result)

            if episode % self.save_interval == 0 and episode > 0:
                self.agent.save_model(self.save_dir)

        self.agent.save_model(self.save_dir)
        plot_path = self.plot_training_progress()
        print(f"학습 완료! 총 {num_episodes} 에피소드 (커리큘럼)")
        self._print_final_stats()
        return results

    def evaluate(
        self, game_instance, skill_level: float, num_episodes: int = 10
    ) -> Dict[str, Any]:
        """에이전트 평가

        Args:
            game_instance: 게임 인스턴스
            skill_level: 실력값
            num_episodes: 평가할 에피소드 수

        Returns:
            평가 결과 통계
        """
        eval_rewards = []
        eval_kills = []
        eval_scores = []
        eval_steps = []

        print(f"PPO 에이전트 평가 시작: {num_episodes} 에피소드")

        for episode in range(num_episodes):
            # 환경 초기화
            self.environment.reset()

            episode_reward = 0.0
            episode_steps = 0

            # 평가 루프 (학습 없이)
            for step in range(self.max_episode_steps):
                game_log_data = self.environment.extract_game_log_data(
                    game_instance, skill_level
                )

                # 액션 선택 (탐험 없이)
                state_vector = game_log_data.to_state_vector()
                state_tensor = (
                    torch.FloatTensor(state_vector).unsqueeze(0).to(self.agent.device)
                )

                with torch.no_grad():
                    action_logits, _ = self.agent.network.forward(state_tensor)
                    action = torch.argmax(action_logits, dim=-1)

                action_id = action.cpu().item()
                action_input = self.environment.get_action_input(action_id)

                # 보상 계산
                reward = self.environment.calculate_reward(game_instance, skill_level)
                episode_reward += reward
                episode_steps += 1

                # 종료 조건 확인
                if self.environment.is_episode_done(game_instance):
                    break

            # 통계 수집
            episode_kills = 0
            episode_score = 0
            if hasattr(game_instance, "game") and game_instance.game:
                game_vars = getattr(game_instance.game, "game_vars", None)
                if game_vars:
                    episode_kills = getattr(game_vars, "kills", 0)
                    episode_score = getattr(game_vars, "score", 0)

            eval_rewards.append(episode_reward)
            eval_kills.append(episode_kills)
            eval_scores.append(episode_score)
            eval_steps.append(episode_steps)

        # 평가 결과 계산
        eval_stats = {
            "mean_reward": np.mean(eval_rewards),
            "std_reward": np.std(eval_rewards),
            "mean_kills": np.mean(eval_kills),
            "mean_score": np.mean(eval_scores),
            "mean_steps": np.mean(eval_steps),
            "episodes": num_episodes,
        }

        print(f"평가 완료:")
        print(
            f"  평균 보상: {eval_stats['mean_reward']:.2f} ± {eval_stats['std_reward']:.2f}"
        )
        print(f"  평균 킬수: {eval_stats['mean_kills']:.2f}")
        print(f"  평균 점수: {eval_stats['mean_score']:.2f}")

        return eval_stats

    def _log_progress(self, episode_result: Dict[str, Any]):
        """학습 진행 상황 로그 출력"""
        episode = episode_result["episode"]
        reward = episode_result["reward"]
        steps = episode_result["steps"]
        kills = episode_result["kills"]
        score = episode_result["score"]

        # 최근 통계
        recent_rewards = list(self.episode_rewards)[-10:]
        recent_kills = list(self.episode_kills)[-10:]

        avg_reward = np.mean(recent_rewards) if recent_rewards else 0
        avg_kills = np.mean(recent_kills) if recent_kills else 0

        print(
            f"Episode {episode:4d} | "
            f"Reward: {reward:7.2f} | "
            f"Steps: {steps:4d} | "
            f"Kills: {kills:3d} | "
            f"Score: {score:6d} | "
            f"Avg10: {avg_reward:6.2f} | "
            f"AvgKills: {avg_kills:4.1f}"
        )

    def _print_final_stats(self):
        """최종 학습 통계 출력"""
        if len(self.episode_rewards) > 0:
            print(f"\n=== 학습 완료 통계 ===")
            print(f"총 에피소드: {self.total_episodes}")
            print(f"총 스텝: {self.total_steps}")
            print(f"최고 보상: {self.best_reward:.2f}")
            print(f"평균 보상 (최근 100): {np.mean(self.episode_rewards):.2f}")
            print(f"평균 킬수 (최근 100): {np.mean(self.episode_kills):.2f}")
            print(f"평균 점수 (최근 100): {np.mean(self.episode_scores):.2f}")
            print(f"평균 스텝 (최근 100): {np.mean(self.episode_lengths):.2f}")

    def get_training_stats(self) -> Dict[str, Any]:
        """현재 학습 통계 반환"""
        if len(self.episode_rewards) == 0:
            return {}

        return {
            "total_episodes": self.total_episodes,
            "total_steps": self.total_steps,
            "best_reward": self.best_reward,
            "recent_avg_reward": np.mean(list(self.episode_rewards)[-10:]),
            "recent_avg_kills": np.mean(list(self.episode_kills)[-10:]),
            "recent_avg_score": np.mean(list(self.episode_scores)[-10:]),
            "recent_avg_steps": np.mean(list(self.episode_lengths)[-10:]),
        }

    def plot_training_progress(self, save_dir: str = "plots") -> str:
        """학습 진행 상황 그래프 생성

        Args:
            save_dir: 그래프 저장 디렉토리

        Returns:
            저장된 그래프 파일 경로
        """
        if len(self.episode_rewards) == 0:
            print("저장할 학습 데이터가 없습니다.")
            return ""

        # 디렉토리 생성
        os.makedirs(save_dir, exist_ok=True)

        # 타임스탬프로 고유한 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        plot_path = os.path.join(save_dir, f"training_progress_{timestamp}.png")

        # 데이터 준비
        episodes = list(range(1, len(self.episode_rewards) + 1))
        rewards = list(self.episode_rewards)
        survival_times = list(self.episode_lengths)

        # 이동 평균 계산 (스무딩)
        window_size = min(10, len(rewards))
        if len(rewards) >= window_size:
            rewards_smooth = []
            survival_smooth = []
            for i in range(len(rewards)):
                start_idx = max(0, i - window_size + 1)
                end_idx = i + 1
                rewards_smooth.append(np.mean(rewards[start_idx:end_idx]))
                survival_smooth.append(np.mean(survival_times[start_idx:end_idx]))
        else:
            rewards_smooth = rewards
            survival_smooth = survival_times

        # 그래프 생성
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        # Reward 그래프
        ax1.plot(episodes, rewards, alpha=0.3, color="blue", label="Episode Reward")
        ax1.plot(
            episodes,
            rewards_smooth,
            color="blue",
            linewidth=2,
            label=f"Moving Average ({window_size})",
        )
        ax1.set_xlabel("Episode")
        ax1.set_ylabel("Reward")
        ax1.set_title(f"Training Progress - Reward (Total Episodes: {len(episodes)})")
        ax1.legend()
        ax1.grid(True, alpha=0.3)

        # 최고 보상 표시
        if rewards:
            max_reward_ep = episodes[rewards.index(max(rewards))]
            ax1.axhline(
                y=max(rewards),
                color="red",
                linestyle="--",
                alpha=0.7,
                label=f"Best: {max(rewards):.2f}",
            )
            ax1.legend()

        # Survival Time 그래프
        ax2.plot(
            episodes,
            survival_times,
            alpha=0.3,
            color="green",
            label="Episode Survival Time",
        )
        ax2.plot(
            episodes,
            survival_smooth,
            color="green",
            linewidth=2,
            label=f"Moving Average ({window_size})",
        )
        ax2.set_xlabel("Episode")
        ax2.set_ylabel("Survival Time (Steps)")
        ax2.set_title("Training Progress - Survival Time")
        ax2.legend()
        ax2.grid(True, alpha=0.3)

        # 최대 생존 시간 표시
        if survival_times:
            max_survival = max(survival_times)
            ax2.axhline(
                y=max_survival,
                color="orange",
                linestyle="--",
                alpha=0.7,
                label=f"Best: {max_survival} steps",
            )
            ax2.legend()

        # 전체 제목 추가
        fig.suptitle("PPO Training Progress", fontsize=16, fontweight="bold")

        # 레이아웃 조정
        plt.tight_layout()

        # 저장
        plt.savefig(plot_path, dpi=300, bbox_inches="tight")
        plt.close()

        print(f"학습 진행 그래프가 저장되었습니다: {plot_path}")
        return plot_path
