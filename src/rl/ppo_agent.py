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
        state_size: int = 161,
        action_size: int = 10,
        learning_rate: float = 7.672115813828463e-05,
        gamma: float = 0.9658767382045985,
        gae_lambda: float = 0.9592342803721876,
        clip_epsilon: float = 0.23713775795384281,
        value_coef: float = 0.16579175341634528,
        entropy_coef: float = 0.001669841290831729,
        hidden_size: int = 128,
        num_layers: int = 2,
        activation: str = "relu",
        grad_clip_norm: float = 1.5008088126812362,
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
            hidden_size: 네트워크 은닉층 크기
            num_layers: 네트워크 은닉층 수
            activation: 활성화 함수
            grad_clip_norm: 그래디언트 클리핑 노름
            device: 연산 장치
        """
        self.device = device
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.clip_epsilon = clip_epsilon
        self.value_coef = value_coef
        self.entropy_coef = entropy_coef
        self.grad_clip_norm = grad_clip_norm

        # 네트워크 초기화 (더 많은 하이퍼파라미터 적용)
        self.network = PPONetwork(
            state_size=state_size,
            action_size=action_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            activation=activation,
        ).to(device)
        self.optimizer = optim.Adam(self.network.parameters(), lr=learning_rate)

        # 경험 버퍼
        self.reset_buffer()

        # 초기 학습 단계 추적 (첫 몇 번의 업데이트에서 관대하게 처리)
        self.update_count = 0

    def reset_buffer(self):
        """경험 버퍼 리셋"""
        self.states = []
        self.actions = []
        self.log_probs = []
        self.values = []
        self.rewards = []
        self.dones = []

    def get_action(self, game_log_data: GameLogData) -> int:
        """게임 로그 데이터로부터 액션 선택 (스킬값 기반 행동 제약 적용)

        DDA를 위한 사용자 모델링: 스킬값에 따라 완전히 다른 행동 패턴 강제
        - 낮은 스킬값: 수비적, 안전한 플레이 (초보자 모델링)
        - 높은 스킬값: 공격적, 위험 감수 플레이 (고수 모델링)

        Args:
            game_log_data: 게임 상태 데이터

        Returns:
            선택된 액션 ID (스킬값 기반 제약 적용)
        """
        state_vector = game_log_data.to_state_vector()
        state_tensor = torch.FloatTensor(state_vector).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action, log_prob, _, value = self.network.get_action_and_value(state_tensor)

        action_id = action.cpu().item()
        skill_level = game_log_data.skill_level

        # DDA를 위한 스킬값 기반 행동 제약 시스템
        action_id = self._apply_skill_based_constraints(
            action_id, game_log_data, skill_level
        )

        # 버퍼에 저장 (원래 액션이 아닌 제약된 액션 저장)
        self.states.append(state_vector)
        self.actions.append(action_id)
        self.log_probs.append(log_prob.cpu().item())
        self.values.append(value.cpu().item())

        return action_id

    def store_reward_and_done(self, reward: float, done: bool):
        """보상과 완료 상태 저장

        Args:
            reward: 보상값
            done: 에피소드 완료 여부
        """
        self.rewards.append(reward)
        self.dones.append(done)

    def update(
        self, num_epochs: int = 4, batch_size: int = 64
    ) -> Dict[str, float]:  # 에포크 3->4, 배치 128->64로 변경 (더 안정적인 학습)
        """PPO 업데이트

        Args:
            num_epochs: 업데이트 에포크 수
            batch_size: 배치 크기

        Returns:
            학습 통계
        """
        if len(self.states) == 0:
            return {}

        # 초기 학습 단계에서는 더 관대하게 처리
        is_early_training = self.update_count < 5

        # 간단한 배열 크기 조정
        sizes = [
            len(self.states),
            len(self.actions),
            len(self.log_probs),
            len(self.values),
            len(self.rewards),
            len(self.dones),
        ]

        min_size = min(sizes)
        max_size = max(sizes)

        if min_size == 0:
            print("⚠️  버퍼가 비어있습니다. 업데이트를 건너뜁니다.")
            return {}

        # 배열 크기 차이 확인
        size_diff = max_size - min_size
        if size_diff > 0:
            if is_early_training:
                print(f"🔧 초기 학습 단계: 배열 크기 차이 {size_diff} 감지, 자동 조정")
            else:
                print(f"⚠️  배열 크기 불일치: 최소={min_size}, 최대={max_size}")

        # 모든 배열을 최소 크기로 맞춤 (간단한 방법)
        self.states = self.states[:min_size]
        self.actions = self.actions[:min_size]
        self.log_probs = self.log_probs[:min_size]
        self.values = self.values[:min_size]
        self.rewards = self.rewards[:min_size]
        self.dones = self.dones[:min_size]

        if min_size < 10 and not is_early_training:
            print(f"⚠️  학습 데이터 부족: {min_size} < 10")
            return {}
        elif min_size < 5:  # 초기에도 최소 5개는 필요
            print(f"⚠️  데이터가 너무 적음: {min_size} < 5")
            return {}

        # 데이터 준비
        states = torch.FloatTensor(np.array(self.states)).to(self.device)
        actions = torch.LongTensor(self.actions).to(self.device)
        old_log_probs = torch.FloatTensor(self.log_probs).to(self.device)
        old_values = torch.FloatTensor(self.values).to(self.device)
        rewards = np.array(self.rewards)
        dones = np.array(self.dones)

        # GAE 계산
        try:
            advantages, returns = self._compute_gae(
                rewards, old_values.cpu().numpy(), dones
            )
            advantages = torch.FloatTensor(advantages).to(self.device)
            returns = torch.FloatTensor(returns).to(self.device)
        except Exception as e:
            if is_early_training:
                print(f"🔧 초기 GAE 계산 실패 (정상): {e}")
                self.reset_buffer()
                return {}
            else:
                print(f"❌ GAE 계산 오류: {e}")
                self.reset_buffer()
                return {}

        # 데이터셋 크기
        dataset_size = len(states)
        print(f"📊 업데이트 #{self.update_count + 1}: {dataset_size}개 샘플로 학습")

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
                torch.nn.utils.clip_grad_norm_(
                    self.network.parameters(), self.grad_clip_norm
                )
                self.optimizer.step()

                # 통계 누적
                total_policy_loss += policy_loss.item()
                total_value_loss += value_loss.item()
                total_entropy_loss += entropy_loss.item()

        # 버퍼 리셋 및 카운터 증가
        self.reset_buffer()
        self.update_count += 1

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
        """Generalized Advantage Estimation 계산 (안전한 버전)

        Args:
            rewards: 보상 배열
            values: 가치 배열
            dones: 종료 상태 배열

        Returns:
            advantages: 어드밴티지
            returns: 리턴값
        """
        # 입력 검증
        if len(rewards) == 0 or len(values) == 0 or len(dones) == 0:
            raise ValueError("빈 배열이 GAE 계산에 전달되었습니다.")

        if not (len(rewards) == len(values) == len(dones)):
            raise ValueError(
                f"배열 크기 불일치: rewards={len(rewards)}, values={len(values)}, dones={len(dones)}"
            )

        length = len(rewards)
        advantages = np.zeros_like(rewards)
        returns = np.zeros_like(rewards)

        gae = 0
        for t in reversed(range(length)):
            # 안전한 next_value 계산
            if t == length - 1:
                # 마지막 스텝: 다음 값이 없으므로 0 또는 현재 값
                next_value = 0 if dones[t] else values[t]
            else:
                # 일반 스텝: 다음 값 사용 (안전한 인덱스 확인)
                next_idx = t + 1
                if next_idx < length:  # 추가 안전 검사
                    next_value = values[next_idx] if not dones[t] else 0
                else:
                    next_value = 0  # 인덱스가 범위를 벗어나면 0

            delta = rewards[t] + self.gamma * next_value - values[t]
            gae = delta + self.gamma * self.gae_lambda * gae * (1 - dones[t])
            advantages[t] = gae
            returns[t] = advantages[t] + values[t]

        # 어드밴티지 정규화 (안전한 버전)
        if np.std(advantages) > 1e-8:
            advantages = (advantages - np.mean(advantages)) / (
                np.std(advantages) + 1e-8
            )
        else:
            # 표준편차가 너무 작으면 정규화하지 않음
            advantages = advantages - np.mean(advantages)

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

    def _apply_skill_based_constraints(
        self, original_action: int, game_log_data: GameLogData, skill_level: float
    ) -> int:
        """행동 제약 완전 제거

        사용자 요구사항에 따라 모든 행동 제약을 제거:
        - 100% 원래 액션 그대로 사용
        - 어떤 제약이나 변경도 적용하지 않음

        Args:
            original_action: 네트워크가 선택한 원래 액션
            game_log_data: 현재 게임 상태 (사용하지 않음)
            skill_level: 스킬값 (사용하지 않음)

        Returns:
            원래 액션 그대로 (제약 없음)
        """
        # 완전한 제약 제거: 항상 원래 액션 반환
        return original_action
