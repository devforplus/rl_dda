import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from collections import deque
import random
import os

from rl.agents.base_agent import BaseAgent
from rl.environment import GameEnvironment, GameState, EntityData, ActionType
from rl.networks import ActorCriticNetwork, compute_gae, normalize_advantages


class ExperienceBuffer:
    """PPO 학습을 위한 경험 버퍼

    에이전트가 환경과 상호작용하며 얻은 경험을 저장하고 관리합니다.

    ---

    상태, 액션, 보상, 로그 확률 등의 경험 데이터를 효율적으로 저장
    """

    def __init__(self, buffer_size: int = 4096):  # 2048 → 4096 (일관성)
        """경험 버퍼 초기화

        Args:
            buffer_size: 버퍼 최대 크기

        ---

        고정 크기의 순환 버퍼로 경험 데이터를 관리
        """
        self.buffer_size = buffer_size
        self.clear()

    def clear(self):
        """버퍼 초기화

        ---

        모든 경험 데이터를 삭제하고 버퍼를 리셋
        """
        self.states = deque(maxlen=self.buffer_size)
        self.actions = deque(maxlen=self.buffer_size)
        self.rewards = deque(maxlen=self.buffer_size)
        self.log_probs = deque(maxlen=self.buffer_size)
        self.values = deque(maxlen=self.buffer_size)
        self.dones = deque(maxlen=self.buffer_size)

    def is_full(self) -> bool:
        """버퍼가 가득 찼는지 확인"""
        return len(self.states) >= self.buffer_size

    def add(
        self,
        state: torch.Tensor,
        action: int,
        reward: float,
        log_prob: float,
        value: float,
        done: bool,
    ):
        """경험 추가

        Args:
            state: 상태
            action: 액션
            reward: 보상
            log_prob: 액션의 로그 확률
            value: 상태 가치
            done: 에피소드 종료 여부

        ---

        한 스텝의 경험을 버퍼에 추가
        """
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.log_probs.append(log_prob)
        self.values.append(value)
        self.dones.append(done)

    def get_batch(self) -> Dict[str, torch.Tensor]:
        """배치 데이터 반환

        Returns:
            텐서로 변환된 배치 데이터

        ---

        저장된 경험을 배치 텐서로 변환하여 반환
        """
        return {
            "states": torch.stack(list(self.states)),
            "actions": torch.tensor(list(self.actions), dtype=torch.long),
            "rewards": torch.tensor(list(self.rewards), dtype=torch.float32),
            "log_probs": torch.tensor(list(self.log_probs), dtype=torch.float32),
            "values": torch.tensor(list(self.values), dtype=torch.float32),
            "dones": torch.tensor(list(self.dones), dtype=torch.float32),
        }

    def size(self) -> int:
        """버퍼 크기 반환

        Returns:
            현재 저장된 경험의 개수
        """
        return len(self.states)


class PPOAgent(BaseAgent):
    """Proximal Policy Optimization (PPO) 에이전트

    PPO 알고리즘을 사용하여 게임 환경에서 학습하는 강화학습 에이전트입니다.

    Attributes:
        env: 게임 환경
        network: Actor-Critic 네트워크
        optimizer: 최적화기
        buffer: 경험 버퍼

    ---

    PPO 알고리즘으로 최적 정책을 학습하는 에이전트 클래스
    """

    def __init__(
        self,
        env: GameEnvironment,
        learning_rate: float = 5e-4,  # 3e-4 → 5e-4 (학습 속도 향상)
        gamma: float = 0.99,
        lam: float = 0.95,
        clip_epsilon: float = 0.15,
        value_loss_coef: float = 0.5,
        entropy_coef_start: float = 0.02,
        entropy_coef_end: float = 0.001,
        entropy_decay_batches: int = 250,
        max_grad_norm: float = 0.5,
        ppo_epochs: int = 8,  # 4 → 8 (더 많은 업데이트)
        batch_size: int = 256,  # 128 → 256 (안정적 그래디언트)
        buffer_size: int = 4096,  # 2048 → 4096 (더 많은 경험)
        device: str = None,
    ):
        """PPO 에이전트 초기화

        Args:
            env: 게임 환경
            learning_rate: 학습률
            gamma: 할인 계수
            lam: GAE 람다 파라미터
            clip_epsilon: PPO 클리핑 값
            value_loss_coef: 가치 함수 손실 가중치
            entropy_coef_start: 엔트로피 계수 시작값
            entropy_coef_end: 엔트로피 계수 종료값
            entropy_decay_batches: 엔트로피 계수 감쇠 배치 수
            max_grad_norm: 그래디언트 클리핑 최대값
            ppo_epochs: PPO 업데이트 에포크 수
            batch_size: 배치 크기
            buffer_size: 경험 버퍼 크기
            device: 계산 장치 (cpu/cuda)

        ---

        PPO 하이퍼파라미터와 네트워크를 초기화
        """
        super().__init__(env.get_action_space_size())

        # 환경 및 디바이스 설정
        self.env = env
        self.device = (
            device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        )

        # 하이퍼파라미터 설정
        self.learning_rate = learning_rate
        self.gamma = gamma
        self.lam = lam
        self.clip_epsilon = clip_epsilon
        self.value_loss_coef = value_loss_coef
        self.entropy_coef_start = entropy_coef_start
        self.entropy_coef_end = entropy_coef_end
        self.entropy_decay_batches = entropy_decay_batches
        self.entropy_coef = entropy_coef_start
        self.max_grad_norm = max_grad_norm
        self.ppo_epochs = ppo_epochs
        self.batch_size = batch_size

        # 네트워크 초기화
        state_size = env.get_state_size()
        action_size = env.get_action_space_size()

        self.network = ActorCriticNetwork(state_size, action_size).to(self.device)
        self.optimizer = optim.Adam(self.network.parameters(), lr=learning_rate)

        # 경험 버퍼
        self.buffer = ExperienceBuffer(buffer_size)

        # 학습 통계
        self.episode_rewards = deque(maxlen=100)
        self.episode_lengths = deque(maxlen=100)
        self.training_step = 0

        # 현재 에피소드 통계
        self.current_episode_reward = 0.0
        self.current_episode_length = 0

    def _update_entropy_coef(self):
        """엔트로피 계수 업데이트 (선형 감쇠)"""
        if self.training_step > self.entropy_decay_batches:
            self.entropy_coef = self.entropy_coef_end
        else:
            decay_ratio = self.training_step / self.entropy_decay_batches
            self.entropy_coef = (
                self.entropy_coef_start
                - (self.entropy_coef_start - self.entropy_coef_end) * decay_ratio
            )

    def select_action(self, game_state: GameState, deterministic: bool = True) -> int:
        """액션 선택

        Args:
            game_state: 현재 게임 상태
            deterministic: True이면 탐험 없이 가장 확률이 높은 액션을 선택

        Returns:
            선택된 액션 ID

        ---

        현재 정책을 사용하여 액션을 선택
        """
        state = self.env.encode_state(game_state).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action, _, _ = self.network.get_action_and_value(
                state, deterministic=deterministic
            )

        return action.item()

    def select_action_with_exploration(
        self, game_state: GameState
    ) -> Tuple[int, float, float]:
        """탐험을 포함한 액션 선택 (학습용)

        Args:
            game_state: 현재 게임 상태

        Returns:
            선택된 액션, 로그 확률, 상태 가치

        ---

        학습 중에 사용할 액션 선택 (확률적 정책 사용)
        """
        state = self.env.encode_state(game_state).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action, log_prob, value = self.network.get_action_and_value(
                state, deterministic=False
            )

        return action.item(), log_prob.item(), value.item()

    def store_experience(self, state, action, reward, log_prob, value, done):
        """경험을 버퍼에 저장 (state는 GameState 또는 이미 인코딩된 Tensor일 수 있음)

        Args:
            state: 게임 상태 (GameState 객체 또는 이미 인코딩된 Tensor)
            action: 수행한 액션 (int 또는 Tensor)
            reward: 받은 보상 (float)
            log_prob: 액션의 로그 확률 (Tensor)
            value: 상태 가치 (Tensor)
            done: 에피소드 종료 여부 (bool)
        """
        if not isinstance(state, torch.Tensor):
            state_tensor = self.env.encode_state(state).cpu()
        else:
            state_tensor = state.cpu()

        self.buffer.add(state_tensor, action, reward, log_prob, value, done)

        # 에피소드 통계 업데이트
        self.current_episode_reward += reward
        self.current_episode_length += 1

        if done:
            self.episode_rewards.append(self.current_episode_reward)
            self.episode_lengths.append(self.current_episode_length)
            self.current_episode_reward = 0.0
            self.current_episode_length = 0

    def is_buffer_full(self) -> bool:
        """경험 버퍼가 가득 찼는지 확인"""
        return self.buffer.is_full()

    def train(self) -> Dict[str, float]:
        """PPO 학습 수행

        Returns:
            학습 통계 딕셔너리

        ---

        저장된 경험을 사용하여 PPO 알고리즘으로 네트워크를 업데이트
        """
        if self.buffer.size() < self.batch_size:
            return {}

        # 엔트로피 계수 업데이트
        self._update_entropy_coef()

        # 배치 데이터 준비
        batch = self.buffer.get_batch()
        states = batch["states"].to(self.device)
        actions = batch["actions"].to(self.device)
        old_log_probs = batch["log_probs"].to(self.device)
        rewards = batch["rewards"].to(self.device)
        old_values = batch["values"].to(self.device)
        dones = batch["dones"].to(self.device)

        # GAE로 어드밴티지 계산
        with torch.no_grad():
            # 마지막 상태가 done이 아닐 경우, network를 통해 bootstrap value 계산
            if not dones[-1]:
                last_state = states[-1].unsqueeze(0)
                _, _, last_value = self.network.get_action_and_value(
                    last_state, deterministic=True
                )
                last_next_value = last_value.squeeze()
            else:
                last_next_value = torch.tensor(0.0).to(self.device)

        advantages, value_targets = compute_gae(
            rewards, old_values.squeeze(), dones, last_next_value, self.gamma, self.lam
        )

        # 어드밴티지 정규화
        advantages = normalize_advantages(advantages)

        # PPO 업데이트
        total_loss = 0.0
        policy_loss_total = 0.0
        value_loss_total = 0.0
        entropy_total = 0.0

        # 데이터를 무작위로 섞어서 미니배치 생성
        dataset_size = len(states)
        indices = torch.randperm(dataset_size)

        for epoch in range(self.ppo_epochs):
            for start_idx in range(0, dataset_size, self.batch_size):
                end_idx = min(start_idx + self.batch_size, dataset_size)
                batch_indices = indices[start_idx:end_idx]

                # 미니배치 추출
                batch_states = states[batch_indices]
                batch_actions = actions[batch_indices]
                batch_old_log_probs = old_log_probs[batch_indices]
                batch_advantages = advantages[batch_indices]
                batch_value_targets = value_targets[batch_indices]

                # 현재 정책으로 평가
                log_probs, values, entropy = self.network.evaluate_actions(
                    batch_states, batch_actions
                )
                values = values.squeeze()

                # PPO 정책 손실 계산
                ratio = torch.exp(log_probs - batch_old_log_probs)
                surr1 = ratio * batch_advantages
                surr2 = (
                    torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon)
                    * batch_advantages
                )
                policy_loss = -torch.min(surr1, surr2).mean()

                # 가치 함수 손실 계산 (Clipped Value Loss)
                batch_old_values = old_values[batch_indices].squeeze()
                values_clipped = batch_old_values + torch.clamp(
                    values - batch_old_values, -self.clip_epsilon, self.clip_epsilon
                )
                value_loss_unclipped = F.mse_loss(
                    values, batch_value_targets, reduction="none"
                )
                value_loss_clipped = F.mse_loss(
                    values_clipped, batch_value_targets, reduction="none"
                )
                value_loss = (
                    0.5 * torch.max(value_loss_unclipped, value_loss_clipped).mean()
                )

                # 엔트로피 보너스
                entropy_loss = -entropy.mean()

                # 총 손실
                loss = (
                    policy_loss
                    + self.value_loss_coef * value_loss
                    + self.entropy_coef * entropy_loss
                )

                # 역전파 및 최적화
                self.optimizer.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.network.parameters(), self.max_grad_norm)
                self.optimizer.step()

                # 통계 누적
                total_loss += loss.item()
                policy_loss_total += policy_loss.item()
                value_loss_total += value_loss.item()
                entropy_total += entropy.mean().item()

        # 버퍼 클리어
        self.buffer.clear()
        self.training_step += 1

        # 학습 통계 반환
        num_updates = self.ppo_epochs * (dataset_size // self.batch_size)
        if num_updates == 0:
            num_updates = 1

        return {
            "total_loss": total_loss / num_updates,
            "policy_loss": policy_loss_total / num_updates,
            "value_loss": value_loss_total / num_updates,
            "entropy": entropy_total / num_updates,
            "training_step": self.training_step,
            "current_entropy_coef": self.entropy_coef,
        }

    def get_stats(self) -> Dict[str, float]:
        """학습 통계 반환

        Returns:
            평균 보상, 에피소드 길이 등의 통계

        ---

        최근 에피소드들의 성능 지표를 반환
        """
        if len(self.episode_rewards) == 0:
            return {}

        return {
            "mean_episode_reward": np.mean(self.episode_rewards),
            "std_episode_reward": np.std(self.episode_rewards),
            "mean_episode_length": np.mean(self.episode_lengths),
            "episodes_played": len(self.episode_rewards),
        }

    def save_model(self, path: str):
        """모델 저장

        Args:
            path: 저장할 파일 경로

        ---

        학습된 네트워크와 옵티마이저 상태를 파일에 저장
        """
        # 저장 경로의 디렉토리가 존재하지 않으면 생성
        save_dir = os.path.dirname(path)
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)

        torch.save(
            {
                "network_state_dict": self.network.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "training_step": self.training_step,
                "episode_rewards": list(self.episode_rewards),
                "episode_lengths": list(self.episode_lengths),
                "hyperparameters": {
                    "learning_rate": self.learning_rate,
                    "gamma": self.gamma,
                    "lam": self.lam,
                    "clip_epsilon": self.clip_epsilon,
                    "value_loss_coef": self.value_loss_coef,
                    "entropy_coef_start": self.entropy_coef_start,
                    "entropy_coef_end": self.entropy_coef_end,
                    "entropy_decay_batches": self.entropy_decay_batches,
                    "max_grad_norm": self.max_grad_norm,
                    "ppo_epochs": self.ppo_epochs,
                    "batch_size": self.batch_size,
                },
            },
            path,
        )

    def load_model(self, path: str):
        """모델 불러오기

        Args:
            path: 불러올 파일 경로

        ---

        저장된 네트워크와 옵티마이저 상태를 파일에서 불러오기
        """
        checkpoint = torch.load(path, map_location=self.device)

        self.network.load_state_dict(checkpoint["network_state_dict"])
        self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])
        self.training_step = checkpoint.get("training_step", 0)

        if "episode_rewards" in checkpoint:
            self.episode_rewards.extend(checkpoint["episode_rewards"])
        if "episode_lengths" in checkpoint:
            self.episode_lengths.extend(checkpoint["episode_lengths"])

    def set_eval_mode(self):
        """평가 모드 설정

        ---

        네트워크를 평가 모드로 설정 (드롭아웃 등 비활성화)
        """
        self.network.eval()

    def set_train_mode(self):
        """학습 모드 설정

        ---

        네트워크를 학습 모드로 설정
        """
        self.network.train()


# 유틸리티 함수
def create_ppo_agent(
    env: GameEnvironment,
    agent_class: type = PPOAgent,
    skill_level: float = 0.5,
    personality: int = 0,
    max_entities: int = 50,
    learning_rate: float = 5e-4,  # 1e-4 → 5e-4 (일관성 있는 학습률)
    gamma: float = 0.99,
    lam: float = 0.95,
    clip_epsilon: float = 0.15,
    value_loss_coef: float = 0.5,
    entropy_coef_start: float = 0.02,
    entropy_coef_end: float = 0.001,
    entropy_decay_batches: int = 250,
    max_grad_norm: float = 0.5,
    ppo_epochs: int = 8,  # 4 → 8 (더 많은 업데이트)
    batch_size: int = 256,  # 128 → 256 (안정적 그래디언트)
    buffer_size: int = 4096,  # 2048 → 4096 (더 많은 경험)
    device: str = None,
) -> PPOAgent:
    """PPO 에이전트 생성

    PPO 알고리즘에 필요한 하이퍼파라미터를 사용하여 PPOAgent 인스턴스를 생성합니다.

    ---

    간편하게 PPO 에이전트를 생성하는 팩토리 함수
    """
    kwargs = locals()
    env = kwargs.pop("env")
    kwargs.pop("agent_class", None)
    kwargs.pop("skill_level", None)
    kwargs.pop("personality", None)
    kwargs.pop("max_entities", None)

    agent = PPOAgent(env, **kwargs)
    return agent
