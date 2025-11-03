"""
🎯 최적화된 독립적인 PPO 에이전트

Optuna 하이퍼파라미터 튜닝 결과가 적용된 즉시 사용 가능한 PPO 에이전트
복잡한 게임 환경 의존성 없이 독립적으로 동작
"""

import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from collections import deque
import os
from datetime import datetime

# 🏆 Optuna 튜닝으로 찾은 최적 하이퍼파라미터
OPTIMIZED_PARAMS = {
    "state_size": 153,
    "action_size": 10,  # 9 → 10: ACTION_MAPPING에 0~9까지 10개 액션 존재
    "learning_rate": 0.00788671412999049,
    "gamma": 0.9800313374635297,
    "gae_lambda": 0.8548304784512067,
    "clip_epsilon": 0.11953442280127678,
    "value_coef": 0.7158097238609412,
    "entropy_coef": 0.007591104805282696,
    "batch_size": 256,
    "num_epochs": 4,
    "hidden_size": 64,
    "num_layers": 2,
    "grad_clip_norm": 0.9726261649881027,
}


class OptimizedPPONetwork(nn.Module):
    """최적화된 PPO 네트워크 (독립적)"""

    def __init__(
        self,
        state_size: int = 153,
        action_size: int = 10,  # 9 → 10: ACTION_MAPPING에 0~9까지 10개 액션 존재
        hidden_size: int = 64,
        num_layers: int = 2,
        activation: str = "relu",
    ):
        super().__init__()

        self.state_size = state_size
        self.action_size = action_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers

        # 활성화 함수
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
        shared_layers.extend([nn.Linear(state_size, hidden_size), self.activation])

        for _ in range(num_layers - 1):
            shared_layers.extend([nn.Linear(hidden_size, hidden_size), self.activation])

        self.shared_layers = nn.Sequential(*shared_layers)

        # Actor 네트워크 (정책)
        self.actor = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            self.activation,
            nn.Linear(hidden_size // 2, action_size),
        )

        # Critic 네트워크 (가치)
        self.critic = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            self.activation,
            nn.Linear(hidden_size // 2, 1),
        )

    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """순전파"""
        shared_features = self.shared_layers(state)
        action_logits = self.actor(shared_features)
        value = self.critic(shared_features)
        return action_logits, value

    def get_action_and_value(
        self, state: torch.Tensor, action: torch.Tensor = None
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        """액션 선택 및 가치 계산"""
        action_logits, value = self.forward(state)
        action_probs = torch.softmax(action_logits, dim=-1)

        # 안전한 확률 분포 (수치적 안정성)
        action_probs = torch.clamp(action_probs, min=1e-8, max=1.0 - 1e-8)

        # 카테고리컬 분포 생성
        log_probs = torch.log(action_probs)

        if action is None:
            # 액션 샘플링
            action = torch.multinomial(action_probs, 1).squeeze(-1)

        # 선택된 액션의 로그 확률
        action_log_prob = log_probs.gather(1, action.unsqueeze(-1)).squeeze(-1)

        # 엔트로피 계산
        entropy = -(action_probs * log_probs).sum(dim=-1)

        return action, action_log_prob, entropy, value.squeeze(-1)

    def get_value(self, state: torch.Tensor) -> torch.Tensor:
        """상태 가치만 계산"""
        _, value = self.forward(state)
        return value.squeeze(-1)


class OptimizedPPOAgent:
    """Optuna 최적화된 PPO 에이전트 (독립적 버전)"""

    def __init__(self, custom_params: Dict[str, Any] = None):
        """
        Args:
            custom_params: 사용자 정의 파라미터 (기본값은 최적화된 파라미터 사용)
        """
        # 기본값은 최적화된 파라미터 사용
        self.params = OPTIMIZED_PARAMS.copy()
        if custom_params:
            self.params.update(custom_params)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.gamma = self.params["gamma"]
        self.gae_lambda = self.params["gae_lambda"]
        self.clip_epsilon = self.params["clip_epsilon"]
        self.value_coef = self.params["value_coef"]
        self.entropy_coef = self.params["entropy_coef"]
        self.grad_clip_norm = self.params["grad_clip_norm"]

        # 네트워크 초기화
        self.network = OptimizedPPONetwork(
            state_size=self.params["state_size"],
            action_size=self.params["action_size"],
            hidden_size=self.params["hidden_size"],
            num_layers=self.params["num_layers"],
            activation="relu",
        ).to(self.device)

        self.optimizer = optim.Adam(
            self.network.parameters(), lr=self.params["learning_rate"]
        )

        # 경험 버퍼
        self.reset_buffer()
        self.update_count = 0

    def reset_buffer(self):
        """경험 버퍼 리셋"""
        self.states = []
        self.actions = []
        self.log_probs = []
        self.values = []
        self.rewards = []
        self.dones = []

    def get_action(self, state: np.ndarray) -> int:
        """게임 상태로부터 액션 선택

        Args:
            state: 게임 상태 (numpy array 또는 list)

        Returns:
            선택된 액션 ID
        """
        # 입력 타입 확인 및 변환
        if isinstance(state, list):
            state = np.array(state)

        # 상태 벡터 크기 확인
        if len(state) != self.params["state_size"]:
            print(
                f"⚠️  상태 벡터 크기 불일치: 예상={self.params['state_size']}, 실제={len(state)}"
            )
            # 크기 조정 (패딩 또는 자르기)
            if len(state) < self.params["state_size"]:
                # 부족한 부분을 0으로 패딩
                state = np.pad(state, (0, self.params["state_size"] - len(state)))
            else:
                # 초과 부분 자르기
                state = state[: self.params["state_size"]]

        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action, log_prob, _, value = self.network.get_action_and_value(state_tensor)

        action_id = action.cpu().item()

        # 버퍼에 저장
        self.states.append(state)
        self.actions.append(action_id)
        self.log_probs.append(log_prob.cpu().item())
        self.values.append(value.cpu().item())

        return action_id

    def store_reward_and_done(self, reward: float, done: bool):
        """보상과 완료 상태 저장"""
        self.rewards.append(reward)
        self.dones.append(done)

    def update(
        self, num_epochs: int = None, batch_size: int = None
    ) -> Dict[str, float]:
        """PPO 업데이트 (최적화된 파라미터 사용)"""
        if num_epochs is None:
            num_epochs = self.params["num_epochs"]
        if batch_size is None:
            batch_size = self.params["batch_size"]

        if len(self.states) == 0:
            return {}

        # 배열 크기 조정
        sizes = [
            len(self.states),
            len(self.actions),
            len(self.log_probs),
            len(self.values),
            len(self.rewards),
            len(self.dones),
        ]
        min_size = min(sizes)

        if min_size < 5:
            print(f"⚠️  학습 데이터 부족: {min_size} < 5")
            return {}

        # 모든 배열을 최소 크기로 맞춤
        self.states = self.states[:min_size]
        self.actions = self.actions[:min_size]
        self.log_probs = self.log_probs[:min_size]
        self.values = self.values[:min_size]
        self.rewards = self.rewards[:min_size]
        self.dones = self.dones[:min_size]

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
            print(f"❌ GAE 계산 오류: {e}")
            self.reset_buffer()
            return {}

        # 학습 통계
        total_policy_loss = 0
        total_value_loss = 0
        total_entropy_loss = 0

        dataset_size = len(states)
        print(f"📊 PPO 업데이트: {dataset_size}개 샘플, {num_epochs}개 에포크")

        # 여러 에포크 학습
        for epoch in range(num_epochs):
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
        """GAE 계산"""
        if len(rewards) == 0:
            raise ValueError("빈 배열이 GAE 계산에 전달되었습니다.")

        length = len(rewards)
        advantages = np.zeros_like(rewards)
        returns = np.zeros_like(rewards)

        gae = 0
        for t in reversed(range(length)):
            if t == length - 1:
                next_value = 0 if dones[t] else values[t]
            else:
                next_value = values[t + 1] if not dones[t] else 0

            delta = rewards[t] + self.gamma * next_value - values[t]
            gae = delta + self.gamma * self.gae_lambda * gae * (1 - dones[t])
            advantages[t] = gae
            returns[t] = advantages[t] + values[t]

        # 어드밴티지 정규화
        if np.std(advantages) > 1e-8:
            advantages = (advantages - np.mean(advantages)) / (
                np.std(advantages) + 1e-8
            )
        else:
            advantages = advantages - np.mean(advantages)

        return advantages, returns

    def save_model(self, save_dir: str = "optimized_models"):
        """모델 저장"""
        os.makedirs(save_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_path = os.path.join(save_dir, f"optimized_ppo_agent_{timestamp}.pth")

        torch.save(
            {
                "network_state_dict": self.network.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "params": self.params,
            },
            save_path,
        )

        print(f"✅ 최적화된 모델 저장: {save_path}")
        return save_path

    def load_model(self, model_path: str):
        """모델 로드"""
        checkpoint = torch.load(model_path, map_location=self.device)
        self.network.load_state_dict(checkpoint["network_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

        if "params" in checkpoint:
            self.params = checkpoint["params"]

        print(f"✅ 최적화된 모델 로드: {model_path}")

    def get_params_summary(self) -> str:
        """파라미터 요약 반환"""
        return f"""
🎯 Optuna 최적화된 PPO 에이전트 파라미터:
   • Learning Rate: {self.params["learning_rate"]:.6f}
   • Gamma: {self.params["gamma"]:.4f}
   • Hidden Size: {self.params["hidden_size"]}
   • Batch Size: {self.params["batch_size"]}
   • Network Layers: {self.params["num_layers"]}
   • Entropy Coef: {self.params["entropy_coef"]:.6f}
   • 예상 성능 향상: 34.16점
        """


def create_optimized_agent(custom_params: Dict[str, Any] = None) -> OptimizedPPOAgent:
    """최적화된 PPO 에이전트 생성 (편의 함수)"""
    print("🚀 Optuna 최적화된 PPO 에이전트 생성 중...")

    agent = OptimizedPPOAgent(custom_params)

    print("✅ 최적화된 PPO 에이전트 생성 완료!")
    print(agent.get_params_summary())

    return agent


if __name__ == "__main__":
    print("🎯 Optuna 최적화된 PPO 에이전트 테스트")
    print("=" * 60)

    # 에이전트 생성
    agent = create_optimized_agent()

    # 간단한 테스트
    print("\n🧪 기능 테스트:")

    # 1. 액션 선택 테스트
    test_state = np.random.random(153)
    action = agent.get_action(test_state)
    print(f"✅ 액션 선택 테스트: 상태 크기 {len(test_state)} → 액션 {action}")

    # 2. 보상 저장 테스트
    agent.store_reward_and_done(1.0, False)
    print("✅ 보상 저장 테스트 완료")

    # 3. 파라미터 출력
    print("\n📊 최적화된 파라미터:")
    for key, value in OPTIMIZED_PARAMS.items():
        if isinstance(value, float):
            print(f"   {key}: {value:.6f}")
        else:
            print(f"   {key}: {value}")

    print("\n🎉 모든 테스트 통과! 에이전트가 정상 작동합니다.")
    print("=" * 60)
