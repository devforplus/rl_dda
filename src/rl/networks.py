import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.distributions import Categorical
from typing import Tuple, Optional
import numpy as np


class PolicyNetwork(nn.Module):
    """PPO를 위한 정책 네트워크 (Actor)

    주어진 상태에서 각 액션의 확률을 출력하는 신경망입니다.

    Attributes:
        state_size: 입력 상태 벡터의 크기
        action_size: 출력 액션 공간의 크기
        hidden_size: 은닉층의 크기

    ---

    상태를 입력받아 액션 확률 분포를 출력하는 정책 네트워크
    """

    def __init__(self, state_size: int, action_size: int, hidden_size: int = 256):
        """정책 네트워크 초기화

        Args:
            state_size: 상태 벡터 크기
            action_size: 액션 공간 크기
            hidden_size: 은닉층 크기

        ---

        다층 퍼셉트론 구조로 정책 네트워크를 구성
        """
        super(PolicyNetwork, self).__init__()

        self.state_size = state_size
        self.action_size = action_size
        self.hidden_size = hidden_size

        # 네트워크 레이어 정의
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, hidden_size // 2)
        self.action_head = nn.Linear(hidden_size // 2, action_size)

        # 드롭아웃 레이어 (과적합 방지)
        self.dropout = nn.Dropout(0.1)

        # 레이어 노름 (학습 안정성 향상)
        self.layer_norm1 = nn.LayerNorm(hidden_size)
        self.layer_norm2 = nn.LayerNorm(hidden_size)

        # 가중치 초기화
        self._initialize_weights()

    def _initialize_weights(self):
        """네트워크 가중치 초기화

        Xavier uniform 초기화를 사용하여 학습 안정성을 향상시킵니다.

        ---

        신경망의 가중치를 효과적으로 초기화하여 학습 성능 개선
        """
        for layer in [self.fc1, self.fc2, self.fc3, self.action_head]:
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """순전파 수행

        Args:
            state: 입력 상태 텐서

        Returns:
            액션 확률 분포 (softmax 적용된 확률값)

        ---

        상태를 입력받아 각 액션의 선택 확률을 계산
        """
        x = F.relu(self.layer_norm1(self.fc1(state)))
        x = self.dropout(x)

        x = F.relu(self.layer_norm2(self.fc2(x)))
        x = self.dropout(x)

        x = F.relu(self.fc3(x))
        action_probs = F.softmax(self.action_head(x), dim=-1)

        return action_probs

    def get_action_and_log_prob(
        self, state: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """액션 선택과 로그 확률 계산

        Args:
            state: 입력 상태 텐서

        Returns:
            선택된 액션과 해당 액션의 로그 확률

        ---

        정책 네트워크를 사용하여 액션을 샘플링하고 로그 확률을 계산
        """
        action_probs = self.forward(state)

        # 확률 분포에서 액션 샘플링
        dist = Categorical(action_probs)
        action = dist.sample()
        log_prob = dist.log_prob(action)

        return action, log_prob

    def evaluate_actions(
        self, states: torch.Tensor, actions: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """주어진 상태-액션 쌍에 대한 로그 확률과 엔트로피 계산

        Args:
            states: 상태 텐서 배치
            actions: 액션 텐서 배치

        Returns:
            로그 확률과 엔트로피

        ---

        PPO 학습을 위해 과거 상태-액션에 대한 확률을 재평가
        """
        action_probs = self.forward(states)
        dist = Categorical(action_probs)

        log_probs = dist.log_prob(actions)
        entropy = dist.entropy()

        return log_probs, entropy


class ValueNetwork(nn.Module):
    """PPO를 위한 가치 함수 네트워크 (Critic)

    주어진 상태의 가치(Value)를 추정하는 신경망입니다.

    Attributes:
        state_size: 입력 상태 벡터의 크기
        hidden_size: 은닉층의 크기

    ---

    상태를 입력받아 해당 상태의 가치를 추정하는 가치 함수 네트워크
    """

    def __init__(self, state_size: int, hidden_size: int = 256):
        """가치 네트워크 초기화

        Args:
            state_size: 상태 벡터 크기
            hidden_size: 은닉층 크기

        ---

        다층 퍼셉트론 구조로 가치 네트워크를 구성
        """
        super(ValueNetwork, self).__init__()

        self.state_size = state_size
        self.hidden_size = hidden_size

        # 네트워크 레이어 정의
        self.fc1 = nn.Linear(state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size)
        self.fc3 = nn.Linear(hidden_size, hidden_size // 2)
        self.value_head = nn.Linear(hidden_size // 2, 1)

        # 드롭아웃 레이어
        self.dropout = nn.Dropout(0.1)

        # 레이어 노름
        self.layer_norm1 = nn.LayerNorm(hidden_size)
        self.layer_norm2 = nn.LayerNorm(hidden_size)

        # 가중치 초기화
        self._initialize_weights()

    def _initialize_weights(self):
        """네트워크 가중치 초기화

        ---

        가치 함수 네트워크의 가중치를 초기화
        """
        for layer in [self.fc1, self.fc2, self.fc3, self.value_head]:
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)

    def forward(self, state: torch.Tensor) -> torch.Tensor:
        """순전파 수행

        Args:
            state: 입력 상태 텐서

        Returns:
            상태 가치 추정값

        ---

        상태를 입력받아 해당 상태의 가치를 추정
        """
        x = F.relu(self.layer_norm1(self.fc1(state)))
        x = self.dropout(x)

        x = F.relu(self.layer_norm2(self.fc2(x)))
        x = self.dropout(x)

        x = F.relu(self.fc3(x))
        value = self.value_head(x)

        return value


class ActorCriticNetwork(nn.Module):
    """Actor-Critic 통합 네트워크

    정책 네트워크와 가치 네트워크를 하나로 통합한 구조입니다.
    일부 레이어를 공유하여 효율성을 높입니다.

    ---

    공유된 특성 추출 레이어와 분리된 출력 헤드를 가진 네트워크
    """

    def __init__(self, state_size: int, action_size: int, hidden_size: int = 256):
        """Actor-Critic 네트워크 초기화

        Args:
            state_size: 상태 벡터 크기
            action_size: 액션 공간 크기
            hidden_size: 은닉층 크기

        ---

        공유 레이어와 별도의 Actor/Critic 헤드를 구성
        """
        super(ActorCriticNetwork, self).__init__()

        self.state_size = state_size
        self.action_size = action_size
        self.hidden_size = hidden_size

        # 공유 특성 추출 레이어
        self.shared_fc1 = nn.Linear(state_size, hidden_size)
        self.shared_fc2 = nn.Linear(hidden_size, hidden_size)

        # Actor (정책) 헤드
        self.actor_fc = nn.Linear(hidden_size, hidden_size // 2)
        self.action_head = nn.Linear(hidden_size // 2, action_size)

        # Critic (가치) 헤드
        self.critic_fc = nn.Linear(hidden_size, hidden_size // 2)
        self.value_head = nn.Linear(hidden_size // 2, 1)

        # 정규화 및 드롭아웃
        self.layer_norm1 = nn.LayerNorm(hidden_size)
        self.layer_norm2 = nn.LayerNorm(hidden_size)
        self.dropout = nn.Dropout(0.1)

        # 가중치 초기화
        self._initialize_weights()

    def _initialize_weights(self):
        """네트워크 가중치 초기화

        ---

        모든 레이어의 가중치를 효과적으로 초기화
        """
        layers = [
            self.shared_fc1,
            self.shared_fc2,
            self.actor_fc,
            self.action_head,
            self.critic_fc,
            self.value_head,
        ]

        for layer in layers:
            nn.init.xavier_uniform_(layer.weight)
            nn.init.zeros_(layer.bias)

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """순전파 수행

        Args:
            state: 입력 상태 텐서

        Returns:
            액션 확률 분포와 상태 가치

        ---

        공유 레이어를 통과한 후 Actor와 Critic 출력을 각각 계산
        """
        # 공유 특성 추출
        x = F.relu(self.layer_norm1(self.shared_fc1(state)))
        x = self.dropout(x)
        shared_features = F.relu(self.layer_norm2(self.shared_fc2(x)))

        # Actor 출력 (액션 확률)
        actor_x = F.relu(self.actor_fc(shared_features))
        action_probs = F.softmax(self.action_head(actor_x), dim=-1)

        # Critic 출력 (상태 가치)
        critic_x = F.relu(self.critic_fc(shared_features))
        value = self.value_head(critic_x)

        return action_probs, value

    def get_action_and_value(
        self, state: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """액션 선택과 가치 추정을 동시에 수행

        Args:
            state: 입력 상태 텐서

        Returns:
            선택된 액션, 로그 확률, 상태 가치

        ---

        효율적인 추론을 위해 액션 선택과 가치 추정을 한 번에 수행
        """
        action_probs, value = self.forward(state)

        dist = Categorical(action_probs)
        action = dist.sample()
        log_prob = dist.log_prob(action)

        return action, log_prob, value

    def evaluate_actions(
        self, states: torch.Tensor, actions: torch.Tensor
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """상태-액션 쌍에 대한 평가

        Args:
            states: 상태 텐서 배치
            actions: 액션 텐서 배치

        Returns:
            로그 확률, 상태 가치, 엔트로피

        ---

        PPO 학습을 위한 정책과 가치 함수 평가
        """
        action_probs, values = self.forward(states)

        dist = Categorical(action_probs)
        log_probs = dist.log_prob(actions)
        entropy = dist.entropy()

        return log_probs, values.squeeze(), entropy


def compute_gae(
    rewards: torch.Tensor,
    values: torch.Tensor,
    next_values: torch.Tensor,
    dones: torch.Tensor,
    gamma: float = 0.99,
    lam: float = 0.95,
) -> Tuple[torch.Tensor, torch.Tensor]:
    """Generalized Advantage Estimation (GAE) 계산

    GAE는 분산을 줄이면서도 편향을 적절히 조절하는 어드밴티지 추정 방법입니다.

    Args:
        rewards: 보상 텐서
        values: 현재 상태 가치
        next_values: 다음 상태 가치
        dones: 에피소드 종료 여부
        gamma: 할인 계수
        lam: GAE 람다 파라미터

    Returns:
        어드밴티지와 가치 타겟

    ---

    PPO 학습에서 사용할 어드밴티지와 가치 타겟을 GAE 방식으로 계산
    """
    batch_size = rewards.size(0)
    advantages = torch.zeros_like(rewards)

    gae = 0
    for step in reversed(range(batch_size)):
        if step == batch_size - 1:
            next_value = next_values[step]
        else:
            next_value = values[step + 1]

        # TD error 계산
        delta = rewards[step] + gamma * next_value * (1 - dones[step]) - values[step]

        # GAE 어드밴티지 계산
        gae = delta + gamma * lam * (1 - dones[step]) * gae
        advantages[step] = gae

    # 가치 타겟 = 어드밴티지 + 현재 가치
    value_targets = advantages + values

    return advantages, value_targets


def normalize_advantages(advantages: torch.Tensor, eps: float = 1e-8) -> torch.Tensor:
    """어드밴티지 정규화

    어드밴티지의 평균을 0, 표준편차를 1로 정규화하여 학습 안정성을 향상시킵니다.

    Args:
        advantages: 정규화할 어드밴티지 텐서
        eps: 0으로 나누기 방지를 위한 작은 값

    Returns:
        정규화된 어드밴티지

    ---

    PPO 학습에서 어드밴티지를 표준화하여 학습 성능 개선
    """
    return (advantages - advantages.mean()) / (advantages.std() + eps)
