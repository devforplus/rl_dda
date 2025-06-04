import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
import numpy as np
from typing import List, Dict, Any, Tuple, Optional
from collections import deque
import random

from rl.agents.base_agent import BaseAgent
from rl.environment import GameEnvironment, GameState, EntityData, ActionType
from rl.networks import ActorCriticNetwork, compute_gae, normalize_advantages


class ExperienceBuffer:
    """PPO 학습을 위한 경험 버퍼

    에이전트가 환경과 상호작용하며 얻은 경험을 저장하고 관리합니다.

    ---

    상태, 액션, 보상, 로그 확률 등의 경험 데이터를 효율적으로 저장
    """

    def __init__(self, buffer_size: int = 2048):
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
        self.states = []
        self.actions = []
        self.rewards = []
        self.log_probs = []
        self.values = []
        self.dones = []

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

        # 버퍼 크기 제한
        if len(self.states) > self.buffer_size:
            self.states.pop(0)
            self.actions.pop(0)
            self.rewards.pop(0)
            self.log_probs.pop(0)
            self.values.pop(0)
            self.dones.pop(0)

    def get_batch(self) -> Dict[str, torch.Tensor]:
        """배치 데이터 반환

        Returns:
            텐서로 변환된 배치 데이터

        ---

        저장된 경험을 배치 텐서로 변환하여 반환
        """
        return {
            "states": torch.stack(self.states),
            "actions": torch.tensor(self.actions, dtype=torch.long),
            "rewards": torch.tensor(self.rewards, dtype=torch.float32),
            "log_probs": torch.tensor(self.log_probs, dtype=torch.float32),
            "values": torch.tensor(self.values, dtype=torch.float32),
            "dones": torch.tensor(self.dones, dtype=torch.float32),
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
        learning_rate: float = 3e-4,
        gamma: float = 0.99,
        lam: float = 0.95,
        clip_epsilon: float = 0.2,
        value_loss_coef: float = 0.5,
        entropy_coef: float = 0.01,
        max_grad_norm: float = 0.5,
        ppo_epochs: int = 10,
        batch_size: int = 64,
        buffer_size: int = 2048,
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
            entropy_coef: 엔트로피 보너스 가중치
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
        self.entropy_coef = entropy_coef
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

    def select_action(self, game_state: GameState) -> int:
        """액션 선택

        Args:
            game_state: 현재 게임 상태

        Returns:
            선택된 액션 ID

        ---

        현재 정책을 사용하여 액션을 선택
        """
        state = self.env.encode_state(game_state).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action, log_prob, value = self.network.get_action_and_value(state)

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
            action, log_prob, value = self.network.get_action_and_value(state)

        return action.item(), log_prob.item(), value.item()

    def store_experience(
        self,
        state: GameState,
        action: int,
        reward: float,
        log_prob: float,
        value: float,
        done: bool,
    ):
        """경험 저장

        Args:
            state: 상태
            action: 액션
            reward: 보상
            log_prob: 로그 확률
            value: 상태 가치
            done: 에피소드 종료 여부

        ---

        한 스텝의 경험을 버퍼에 저장
        """
        state_tensor = self.env.encode_state(state).to(self.device)
        self.buffer.add(state_tensor, action, reward, log_prob, value, done)

        # 에피소드 통계 업데이트
        self.current_episode_reward += reward
        self.current_episode_length += 1

        if done:
            self.episode_rewards.append(self.current_episode_reward)
            self.episode_lengths.append(self.current_episode_length)
            self.current_episode_reward = 0.0
            self.current_episode_length = 0

    def train(self) -> Dict[str, float]:
        """PPO 학습 수행

        Returns:
            학습 통계 딕셔너리

        ---

        저장된 경험을 사용하여 PPO 알고리즘으로 네트워크를 업데이트
        """
        if self.buffer.size() < self.batch_size:
            return {}

        # 배치 데이터 준비
        batch = self.buffer.get_batch()
        states = batch["states"].to(self.device)
        actions = batch["actions"].to(self.device)
        old_log_probs = batch["log_probs"].to(self.device)
        rewards = batch["rewards"].to(self.device)
        old_values = batch["values"].to(self.device)
        dones = batch["dones"].to(self.device)

        # 다음 상태 가치 계산 (GAE용)
        with torch.no_grad():
            next_values = torch.zeros_like(old_values)
            if len(states) > 1:
                # 마지막을 제외한 모든 상태의 다음 상태 가치
                _, next_vals = self.network(states[1:])
                next_values[:-1] = next_vals.squeeze()

        # GAE로 어드밴티지 계산
        advantages, value_targets = compute_gae(
            rewards, old_values, next_values, dones, self.gamma, self.lam
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

                # PPO 정책 손실 계산
                ratio = torch.exp(log_probs - batch_old_log_probs)
                surr1 = ratio * batch_advantages
                surr2 = (
                    torch.clamp(ratio, 1 - self.clip_epsilon, 1 + self.clip_epsilon)
                    * batch_advantages
                )
                policy_loss = -torch.min(surr1, surr2).mean()

                # 가치 함수 손실 계산
                value_loss = F.mse_loss(values, batch_value_targets)

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
                    "entropy_coef": self.entropy_coef,
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

    def update_reward_weights(
        self, survival_weight: float, combat_weight: float, consistency_weight: float
    ):
        """보상 가중치 업데이트

        Args:
            survival_weight: 생존 지표 가중치
            combat_weight: 공격 지표 가중치
            consistency_weight: 일관성 지표 가중치

        ---

        학습 도중에 보상 함수의 가중치를 동적으로 조정
        """
        self.env.reward_weights = {
            "survival": survival_weight,
            "combat": combat_weight,
            "consistency": consistency_weight,
        }


# 유틸리티 함수
def create_ppo_agent(
    skill_level: float = 0.5, personality: int = 0, max_entities: int = 50, **kwargs
) -> PPOAgent:
    """PPO 에이전트 생성 헬퍼 함수

    Args:
        skill_level: 초기 실력 수준 (0~1)
        personality: 성향 (0: 방어적, 1: 공격적)
        max_entities: 최대 엔티티 수
        **kwargs: PPO 하이퍼파라미터

    Returns:
        초기화된 PPO 에이전트

    ---

    간편하게 PPO 에이전트를 생성하는 팩토리 함수
    """
    env = GameEnvironment(max_entities=max_entities)
    agent = PPOAgent(env, **kwargs)

    return agent
