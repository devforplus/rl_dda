"""
PPO 에이전트 구현

게임 로그 데이터와 실력값을 입력으로 받는 간결한 PPO 에이전트
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from collections import deque
import os
from datetime import datetime

from .ppo_network import PPONetwork
from .data_types import GameLogData, ActionType


class PPOAgent:
    """PPO 에이전트

    게임 로그 데이터와 실력값을 입력으로 받아 학습하는 PPO 에이전트
    """

    def __init__(
        self,
        state_size: int = 153,
        action_size: int = 9,
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        gae_lambda: float = 0.95,
        clip_epsilon: float = 0.2,
        value_coef: float = 0.5,
        entropy_coef: float = 0.01,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        """PPO 에이전트 초기화

        Args:
            state_size: 상태 벡터 크기
            action_size: 액션 공간 크기
            learning_rate: 학습률
            gamma: 할인 인수
            gae_lambda: GAE lambda
            clip_epsilon: PPO 클리핑 파라미터
            value_coef: 가치 손실 계수
            entropy_coef: 엔트로피 계수
            device: 연산 장치
        """
        self.device = device
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef

        # 네트워크 초기화
        self.network = PPONetwork(state_size, action_size).to(device)
        self.optimizer = optim.Adam(self.network.parameters(), lr=learning_rate)

        # 경험 버퍼
        self.reset_buffer()

    def reset_buffer(self):
        """경험 버퍼 리셋"""
        self.states = []
        self.actions = []
        self.log_probs = []
        self.values = []
        self.rewards = []
        self.dones = []

    def get_action(self, game_log_data: GameLogData) -> int:
        """게임 로그 데이터로부터 액션 선택

        Args:
            game_log_data: 게임 로그 데이터

        Returns:
            선택된 액션 ID
        """
        state_vector = game_log_data.to_state_vector()
        state_tensor = torch.FloatTensor(state_vector).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action, log_prob, _, value = self.network.get_action_and_value(state_tensor)

        # 경험 저장
        self.states.append(state_vector)
        self.actions.append(action.cpu().item())
        self.log_probs.append(log_prob.cpu().item())
        self.values.append(value.cpu().item())

        return action.cpu().item()

    def store_reward_and_done(self, reward: float, done: bool):
        """보상과 종료 상태 저장

        Args:
            reward: 보상값
            done: 에피소드 종료 여부
        """
        self.rewards.append(reward)
        self.dones.append(done)

    def update(self, num_epochs: int = 4, batch_size: int = 64) -> Dict[str, float]:
        """PPO 업데이트

        Args:
            num_epochs: 업데이트 에포크 수
            batch_size: 배치 크기

        Returns:
            학습 통계
        """
        if len(self.states) == 0:
            return {}

        # 데이터 준비
        states = torch.FloatTensor(np.array(self.states)).to(self.device)
        actions = torch.LongTensor(self.actions).to(self.device)
        old_log_probs = torch.FloatTensor(self.log_probs).to(self.device)
        old_values = torch.FloatTensor(self.values).to(self.device)
        rewards = np.array(self.rewards)
        dones = np.array(self.dones)

        # GAE 계산
        advantages, returns = self._compute_gae(
            rewards, old_values.cpu().numpy(), dones
        )
        advantages = torch.FloatTensor(advantages).to(self.device)
        returns = torch.FloatTensor(returns).to(self.device)

        # 데이터셋 크기
        dataset_size = len(states)

        # 학습 통계
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy_loss = 0

        # 여러 에포크 학습
        for epoch in range(num_epochs):
            # 배치별 학습
            indices = torch.randperm(dataset_size)

            for start in range(0, dataset_size, batch_size):
                end = min(start + batch_size, dataset_size)
                batch_indices = indices[start:end]

                # 배치 데이터
                batch_states = states[batch_indices]
                batch_actions = actions[batch_indices]
                batch_old_log_probs = old_log_probs[batch_indices]
                batch_advantages = advantages[batch_indices]
                batch_returns = returns[batch_indices]

                # 현재 정책으로 평가
                _, new_log_probs, entropy, new_values = (
                    self.network.get_action_and_value(batch_states, batch_actions)
                )

                # 정책 손실 (PPO 클리핑)
                ratio = torch.exp(new_log_probs - batch_old_log_probs)
                clipped_ratio = torch.clamp(
                    ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon
                )
                policy_loss = -torch.min(
                    ratio * batch_advantages, clipped_ratio * batch_advantages
                ).mean()

                # 가치 손실
                value_loss = nn.MSELoss()(new_values, batch_returns)

                # 엔트로피 손실
                entropy_loss = -entropy.mean()

                # 전체 손실
                total_loss = (
                    policy_loss
                    + self.value_coef * value_loss
                    + self.entropy_coef * entropy_loss
                )

                # 역전파
                self.optimizer.zero_grad()
                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(self.network.parameters(), 0.5)
                self.optimizer.step()

                # 통계 누적
                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy_loss += entropy_loss.item()

        # 버퍼 리셋
        self.reset_buffer()

        num_updates = num_epochs * (dataset_size // batch_size + 1)

        return {
            "policy_loss": total_policy_loss / num_updates,
            "value_loss": total_value_loss / num_updates,
            "entropy_loss": total_entropy_loss / num_updates,
            "total_samples": dataset_size,
        }

    def _compute_gae(
        self, rewards: np.ndarray, values: np.ndarray, dones: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Generalized Advantage Estimation 계산

        Args:
            rewards: 보상 배열
            values: 가치 배열
            dones: 종료 상태 배열

        Returns:
            advantages: 어드밴티지
            returns: 리턴값
        """
        advantages = np.zeros_like(rewards)
        returns = np.zeros_like(rewards)

        gae = 0
        for t in reversed(range(len(rewards))):
            if t == len(rewards) - 1:
                next_value = 0 if dones[t] else values[t]
            else:
                next_value = values[t + 1] if not dones[t] else 0

            delta = rewards[t] + self.gamma * next_value - values[t]
            gae = delta + self.gamma * self.gae_lambda * gae * (1 - dones[t])
            advantages[t] = gae
            returns[t] = advantages[t] + values[t]

        # 어드밴티지 정규화
        advantages = (advantages - np.mean(advantages)) / (np.std(advantages) + 1e-8)

        return advantages, returns

    def save_model(self, save_dir: str = "src/models/ppo"):
        """모델 저장

        Args:
            save_dir: 저장 디렉토리
        """
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(save_dir, f"ppo_agent_{timestamp}.pth")

        torch.save(
            {
                "network_state_dict": self.network.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
            },
            save_path,
        )

        print(f"모델이 저장되었습니다: {save_path}")
        return save_path

    def load_model(self, model_path: str):
        """모델 로드

        Args:
            model_path: 모델 파일 경로
        """
        checkpoint = torch.load(model_path, map_location=self.device)
        self.network.load_state_dict(checkpoint["network_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        print(f"모델이 로드되었습니다: {model_path}")
