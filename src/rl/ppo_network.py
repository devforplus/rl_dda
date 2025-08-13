"""
PPO 네트워크 구현 (Actor-Critic)

게임 로그 데이터 + 실력값을 입력으로 받는 간결한 구조
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical
from typing import Tuple
import numpy as np


class PPONetwork(nn.Module):
    """PPO Actor-Critic 네트워크

    입력: 게임 로그 데이터 + 실력값 벡터
    출력: 액션 확률 분포 (Actor) + 상태 가치 (Critic)
    """

    def __init__(
        self,
        state_size: int = 153,
        action_size: int = 10,  # 9 → 10: ACTION_MAPPING에 0~9까지 10개 액션 존재
        hidden_size: int = 256,
        num_layers: int = 3,
        activation: str = "relu",
    ):
        """네트워크 초기화

        Args:
            state_size: 상태 벡터 크기
            action_size: 액션 공간 크기 (0~9: 8방향 + 정지 + 공격 = 10)
            hidden_size: 은닉층 뉴런 수
            num_layers: 은닉층 개수
            activation: 활성화 함수 ("relu", "tanh", "leaky_relu")
        """
        super(PPONetwork, self).__init__()

        self.state_size = state_size
        self.action_size = action_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # 활성화 함수 선택
        if activation == "relu":
            self.activation = nn.ReLU()
        elif activation == "tanh":
            self.activation = nn.Tanh()
        elif activation == "leaky_relu":
            self.activation = nn.LeakyReLU()
        else:
            self.activation = nn.ReLU()

        # 공통 특성 추출 네트워크 (동적 생성)
        shared_layers = []

        # 첫 번째 레이어
        shared_layers.extend([nn.Linear(state_size, hidden_size), self.activation])

        # 중간 레이어들
        for _ in range(num_layers - 1):
            shared_layers.extend([nn.Linear(hidden_size, hidden_size), self.activation])

        self.shared_layers = nn.Sequential(*shared_layers)

        # Actor 네트워크 (정책) - 더 간단하게
        self.actor = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            self.activation,
            nn.Linear(hidden_size // 2, action_size),
        )

        # Critic 네트워크 (가치) - 더 간단하게
        self.critic = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            self.activation,
            nn.Linear(hidden_size // 2, 1),
        )

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """순전파

        Args:
            state: 상태 벡터 [batch_size, state_size]

        Returns:
            action_logits: 액션 로그 확률 [batch_size, action_size]
            value: 상태 가치 [batch_size, 1]
        """
        # 공통 특성 추출
        shared_features = self.shared_layers(state)

        # Actor: 액션 확률 분포
        action_logits = self.actor(shared_features)

        # Critic: 상태 가치
        value = self.critic(shared_features)

        return action_logits, value

    def get_action_and_value(
        self, state: torch.Tensor, action: torch.Tensor = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """액션 선택 및 가치 계산

        Args:
            state: 상태 벡터
            action: 액션 (None이면 새로 샘플링)

        Returns:
            action: 선택된 액션
            log_prob: 액션 로그 확률
            entropy: 정책 엔트로피
            value: 상태 가치
        """
        action_logits, value = self.forward(state)
        action_probs = F.softmax(action_logits, dim=-1)
        dist = Categorical(action_probs)

        if action is None:
            action = dist.sample()

        log_prob = dist.log_prob(action)
        entropy = dist.entropy()

        return action, log_prob, entropy, value.squeeze(-1)

    def get_value(self, state: torch.Tensor) -> torch.Tensor:
        """상태 가치만 계산

        Args:
            state: 상태 벡터

        Returns:
            value: 상태 가치
        """
        _, value = self.forward(state)
        return value.squeeze(-1)
