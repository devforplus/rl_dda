"""
PPO (Proximal Policy Optimization) 알고리즘 구현
랜덤 에이전트 생성을 위한 기본 PPO 에이전트 및 게임 환경 클래스
PyTorch 기반 구현

학습 모드:
- survival: 생존 극한 (w_survival=0.95, w_attack=0.05)
- balanced: 균형 (w_survival=0.50, w_attack=0.50)
- attack: 공격 극한 (w_survival=0.05, w_attack=0.95)
"""

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from collections import deque
from dataclasses import dataclass
from typing import Optional, Tuple, List, Dict
from enum import IntEnum


# =============================================================================
# 학습 모드별 고정 가중치 정의
# =============================================================================
TRAINING_MODES: Dict[str, Dict[str, float]] = {
    "survival": {"w_survival": 0.95, "w_attack": 0.05},  # 생존 극한
    "balanced": {"w_survival": 0.50, "w_attack": 0.50},  # 균형
    "attack":   {"w_survival": 0.05, "w_attack": 0.95},  # 공격 극한
}


class EntityType(IntEnum):
    PLAYER = 0
    ENEMY = 1
    ENEMY_BULLET = 2


@dataclass
class EntityPosition:
    x: float
    y: float
    entity_type: int


@dataclass
class PlayerState:
    hp: int
    lives: int


def get_survival_target_steps(skill_level: float) -> float:
    """실력값에 따른 생존 목표 스텝 계산 (연속 선형 함수)
    
    수식: T_target(skill) = 300 + (skill - 0.1) * 1333.33
    - skill 0.1 → 300 스텝
    - skill 1.0 → 1500 스텝
    """
    # 연속 선형 보간: 0.1(300) ~ 1.0(1500)
    return 300.0 + (skill_level - 0.1) * (1500.0 - 300.0) / (1.0 - 0.1)


class ActorCritic(nn.Module):
    """PPO Actor-Critic 네트워크 (연구 최적화 구조)"""
    
    def __init__(self, state_size: int, action_size: int, hidden_size: int = 128, num_layers: int = 2, activation: str = "relu"):
        super(ActorCritic, self).__init__()
        
        if activation == "relu":
            self.act = nn.ReLU()
        elif activation == "tanh":
            self.act = nn.Tanh()
        else:
            self.act = nn.ReLU()
            
        # 1. 공통 특성 추출 (Shared Layers)
        layers = []
        layers.extend([nn.Linear(state_size, hidden_size), self.act])
        for _ in range(num_layers - 1):
            layers.extend([nn.Linear(hidden_size, hidden_size), self.act])
        self.shared = nn.Sequential(*layers)
        
        # 2. Actor Head
        self.actor = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            self.act,
            nn.Linear(hidden_size // 2, action_size),
            nn.Softmax(dim=-1)
        )
        
        # 3. Critic Head
        self.critic = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            self.act,
            nn.Linear(hidden_size // 2, 1)
        )
    
    def forward(self, state: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        features = self.shared(state)
        return self.actor(features), self.critic(features)


class PPOAgent:
    """PPO 에이전트 (Optuna 최적화 하이퍼파라미터 적용)"""
    
    def __init__(
        self,
        state_size: int = 161,
        action_size: int = 10,
        lr: float = 7.672115813828463e-05,
        gamma: float = 0.9658767382045985,
        gae_lambda: float = 0.9592342803721876,
        eps_clip: float = 0.23713775795384281,
        entropy_coef: float = 0.01, # 탐색 촉진을 위해 연구값(0.0016)보다 약간 높게 유지
        vf_coef: float = 0.16579175341634528,
        k_epochs: int = 4,
        batch_size: int = 256,  # 안정성 향상을 위해 64 -> 256 상향
        max_grad_norm: float = 1.5008088126812362,
        hidden_size: int = 128
    ):
        """PPO 에이전트 초기화 (Optuna 최적화 결과 반영)"""
        self.state_size = state_size
        self.action_size = action_size
        self.lr = lr
        self.gamma = gamma
        self.gae_lambda = gae_lambda
        self.eps_clip = eps_clip
        self.entropy_coef = entropy_coef
        self.vf_coef = vf_coef
        self.k_epochs = k_epochs
        self.batch_size = batch_size
        self.max_grad_norm = max_grad_norm
        
        # Actor-Critic 네트워크
        self.policy = ActorCritic(state_size, action_size, hidden_size)
        self.optimizer = optim.Adam(self.policy.parameters(), lr=lr)
        
        # 경험 버퍼
        self.states = []
        self.actions = []
        self.rewards = []
        self.log_probs = []
        self.dones = []
        self.values = []
        
        # 디바이스 설정
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.policy.to(self.device)

        # 벤치마크용
        self.last_inference_time = 0.0
    
    def select_action(self, state: np.ndarray, deterministic: bool = False) -> Tuple[int, float, float]:
        """
        상태를 받아서 액션을 선택
        
        Args:
            state: 상태 벡터 [state_size]
            deterministic: True면 확률이 가장 높은 액션 선택, False면 확률 분포에서 샘플링
            
        Returns:
            action: 선택된 액션 인덱스
            log_prob: 선택된 액션의 로그 확률
            value: 상태 가치 (Critic 출력)
        """
        import time
        start_time = time.time()
        
        state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            action_probs, state_value = self.policy(state_tensor)
            action_probs = action_probs.cpu().numpy()[0]
            state_value = state_value.cpu().item()
        
        if deterministic:
            action = np.argmax(action_probs)
        else:
            action = np.random.choice(self.action_size, p=action_probs)
        
        log_prob = np.log(action_probs[action] + 1e-8)
        
        self.last_inference_time = time.time() - start_time
        
        return action, log_prob, state_value
    
    def store_transition(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        log_prob: float,
        done: bool,
        value: float
    ):
        """경험 저장"""
        self.states.append(state)
        self.actions.append(action)
        self.rewards.append(reward)
        self.log_probs.append(log_prob)
        self.dones.append(done)
        self.values.append(value)
    
    def update(self, next_state_value: float = 0.0):
        """
        PPO 알고리즘으로 정책 업데이트
        GAE (Generalized Advantage Estimation) 및 신규 하이퍼파라미터 적용
        """
        if len(self.states) < self.batch_size:
            return
        
        # 텐서 변환
        states = torch.FloatTensor(np.array(self.states)).to(self.device)
        actions = torch.LongTensor(np.array(self.actions)).to(self.device)
        old_log_probs = torch.FloatTensor(np.array(self.log_probs)).to(self.device)
        rewards = np.array(self.rewards)
        dones = np.array(self.dones)
        values = np.array(self.values + [next_state_value])
        
        # GAE 계산
        advantages = []
        gae = 0
        for i in reversed(range(len(rewards))):
            delta = rewards[i] + self.gamma * values[i+1] * (1 - dones[i]) - values[i]
            gae = delta + self.gamma * self.gae_lambda * (1 - dones[i]) * gae
            advantages.insert(0, gae)
        
        advantages = torch.FloatTensor(np.array(advantages)).to(self.device)
        returns = advantages + torch.FloatTensor(np.array(self.values)).to(self.device)
        
        # 정규화
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
        
        # K번 업데이트
        for _ in range(self.k_epochs):
            # 현재 정책으로 확률 및 가치 계산
            action_probs, state_values = self.policy(states)
            dist = torch.distributions.Categorical(action_probs)
            new_log_probs = dist.log_prob(actions)
            entropy = dist.entropy().mean()
            
            # Policy Loss (PPO Clip)
            ratio = torch.exp(new_log_probs - old_log_probs)
            surr1 = ratio * advantages
            surr2 = torch.clamp(ratio, 1 - self.eps_clip, 1 + self.eps_clip) * advantages
            policy_loss = -torch.min(surr1, surr2).mean()
            
            # Value Loss (MSE)
            value_loss = nn.MSELoss()(state_values.squeeze(), returns)
            
            # Total Loss
            loss = policy_loss + self.vf_coef * value_loss - self.entropy_coef * entropy
            
            # 역전파
            self.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.policy.parameters(), self.max_grad_norm)
            self.optimizer.step()
        
        # 버퍼 초기화
        self.states.clear()
        self.actions.clear()
        self.rewards.clear()
        self.log_probs.clear()
        self.dones.clear()
        self.values.clear()
    
    def _compute_returns(self) -> np.ndarray:
        """할인된 반환값 계산"""
        returns = []
        discounted_reward = 0
        
        for reward, done in zip(reversed(self.rewards), reversed(self.dones)):
            if done:
                discounted_reward = 0
            discounted_reward = reward + self.gamma * discounted_reward
            returns.insert(0, discounted_reward)
        
        return np.array(returns)
    
    def save(self, filepath: str):
        """모델 저장"""
        torch.save({
            'policy_state_dict': self.policy.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
        }, filepath)
    
    def load(self, filepath: str):
        """모델 로드"""
        checkpoint = torch.load(filepath, map_location=self.device)
        self.policy.load_state_dict(checkpoint['policy_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])


class GameEnvironment:
    """게임 환경 래퍼 클래스
    
    Args:
        training_mode: 학습 모드 ("survival", "balanced", "attack")
    """
    
    def __init__(self, training_mode: str = "balanced"):
        """게임 환경 초기화
        
        Args:
            training_mode: 학습 모드 ("survival", "balanced", "attack")
        """
        self.state_size = 161
        self.action_size = 10
        self.previous_lives = 3
        self.previous_score = 0
        
        # 학습 모드 설정
        if training_mode not in TRAINING_MODES:
            raise ValueError(f"Unknown training_mode: {training_mode}. "
                           f"Available modes: {list(TRAINING_MODES.keys())}")
        self.training_mode = training_mode
        self.w_survival = TRAINING_MODES[training_mode]["w_survival"]
        self.w_attack = TRAINING_MODES[training_mode]["w_attack"]

    def get_state(self, game_state, skill_level: float, current_steps: int) -> np.ndarray:
        """
        게임 상태를 연구 기반 고차원 상태 벡터로 변환
        """
        if game_state is None:
            return np.zeros(self.state_size, dtype=np.float32)
            
        entities = []
        # 1. 엔티티 수집 (플레이어, 적, 탄환)
        if hasattr(game_state, 'player') and game_state.player and not game_state.player.remove:
            entities.append(EntityPosition(game_state.player.x, game_state.player.y, EntityType.PLAYER))
            
        enemies = getattr(game_state, 'enemies', [])
        for e in enemies:
            if not e.remove:
                entities.append(EntityPosition(e.x, e.y, EntityType.ENEMY))
                
        enemy_shots = getattr(game_state, 'enemy_shots', [])
        for s in enemy_shots:
            if not s.remove:
                entities.append(EntityPosition(s.x, s.y, EntityType.ENEMY_BULLET))

        # 2. 엔티티 데이터 정규화 (최대 50개)
        max_entities = 50
        entity_data = np.zeros(max_entities * 3)
        for i, ent in enumerate(entities[:max_entities]):
            idx = i * 3
            entity_data[idx] = ent.x / 256.0
            entity_data[idx+1] = ent.y / 192.0
            entity_data[idx+2] = ent.entity_type / 2.0

        # 3. 플레이어 상태 및 실력값
        player_hp = getattr(game_state.player, 'hp', 3) if hasattr(game_state, 'player') and game_state.player else 0
        game_vars = getattr(game_state, 'game', None)
        lives = game_vars.game_vars.lives if game_vars and hasattr(game_vars, 'game_vars') else 0
        
        player_data = np.array([player_hp / 3.0, lives / 3.0])
        skill_data = np.array([skill_level])

        # 4. 목표 및 성과 지표 (핵심 개선)
        target_kills_per_100 = skill_level * 2.0
        target_surv = get_survival_target_steps(skill_level)
        
        current_score = game_vars.game_vars.score if game_vars and hasattr(game_vars, 'game_vars') else 0
        current_kill_rate = (current_score / 100.0) / max(current_steps / 100.0, 1.0)
        
        surv_progress = min(current_steps / target_surv, 2.0)
        kill_progress = current_kill_rate / max(target_kills_per_100, 0.1)

        target_data = np.array([
            skill_level,
            target_kills_per_100 / 2.0,
            target_surv / 1500.0,
            min(surv_progress, 1.0),
            min(kill_progress, 2.0) / 2.0,
            current_steps / 1000.0,
            (current_score / 100.0) / 10.0,
            min(current_score / 1000.0, 1.0)
        ])

        # 5. 전체 결합 (150 + 2 + 1 + 8 = 161)
        state_vector = np.concatenate([entity_data, player_data, skill_data, target_data])
        return state_vector.astype(np.float32)

    def apply_action(self, action: int, input_obj) -> None:
        """
        액션을 게임 Input 객체에 적용
        
        Args:
            action: 액션 인덱스 (0-9)
            input_obj: Input 인스턴스
        """
        import input as input_module
        
        # 1. 기존 입력 초기화 (필수)
        # TrainingApp.update에서 input_obj.update()를 먼저 호출하므로
        # 여기서는 추가로 clear할 필요는 없지만 명확성을 위해 유지
        input_obj.pressing.clear()
        input_obj.tapped.clear()
        
        # 2. 액션 매핑 적용
        # 0: 정지
        # 1: 상, 2: 하, 3: 좌, 4: 우
        # 5: 상좌, 6: 상우, 7: 하좌, 8: 하우
        # 9: 발사만 (이동 없이 발사)
        
        if action == 1:
            input_obj.pressing.append(input_module.UP)
            input_obj.tapped.append(input_module.UP)
        elif action == 2:
            input_obj.pressing.append(input_module.DOWN)
            input_obj.tapped.append(input_module.DOWN)
        elif action == 3:
            input_obj.pressing.append(input_module.LEFT)
            input_obj.tapped.append(input_module.LEFT)
        elif action == 4:
            input_obj.pressing.append(input_module.RIGHT)
            input_obj.tapped.append(input_module.RIGHT)
        elif action == 5:
            input_obj.pressing.append(input_module.UP)
            input_obj.pressing.append(input_module.LEFT)
            input_obj.tapped.append(input_module.UP)
            input_obj.tapped.append(input_module.LEFT)
        elif action == 6:
            input_obj.pressing.append(input_module.UP)
            input_obj.pressing.append(input_module.RIGHT)
            input_obj.tapped.append(input_module.UP)
            input_obj.tapped.append(input_module.RIGHT)
        elif action == 7:
            input_obj.pressing.append(input_module.DOWN)
            input_obj.pressing.append(input_module.LEFT)
            input_obj.tapped.append(input_module.DOWN)
            input_obj.tapped.append(input_module.LEFT)
        elif action == 8:
            input_obj.pressing.append(input_module.DOWN)
            input_obj.pressing.append(input_module.RIGHT)
            input_obj.tapped.append(input_module.DOWN)
            input_obj.tapped.append(input_module.RIGHT)
        elif action == 9:
            input_obj.pressing.append(input_module.BUTTON_1)
            input_obj.tapped.append(input_module.BUTTON_1)
            
        # 모든 액션 시 기본적으로 발사 버튼을 누르게 하고 싶다면 아래 주석 해제
        # if action != 0: input_obj.pressing.append(input_module.BUTTON_1)
    
    def get_reward(self, game_state, skill_level: float, current_steps: int, prev_score: int) -> float:
        """
        모드별 고정 가중치 기반 보상 함수 (개선된 공격 보상)
        
        수식:
        - 생존 보상: 매 스텝 0.01 (기본 생존 인센티브)
        - 공격 보상: 적 처치 시 즉시 보상 (점수 증가량 기반)
        - 사망 페널티: -(1.0 + skill * 2.0)
        
        모드별 가중치:
        - survival: 생존 중심, 공격은 작은 보너스
        - balanced: 생존과 공격 균형
        - attack: 공격 중심, 생존은 기본 유지
        
        Args:
            game_state: GameStateStage 인스턴스
            skill_level: 실력값 (0.0 ~ 1.0)
            current_steps: 에피소드 진행 스텝
            prev_score: 이전 점수 (즉각적 공격 보상 계산용)
            
        Returns:
            final_reward: 계산된 보상
        """
        if not game_state:
            return 0.0
            
        game_vars = getattr(game_state, 'game', None)
        if game_vars and hasattr(game_vars, 'game_vars'):
            gv = game_vars.game_vars
        else:
            return 0.0

        current_score = gv.score
        current_lives = gv.lives
        
        # 1. 사망 페널티 (최우선 체크)
        if current_lives < self.previous_lives:
            death_penalty = 1.0 + (skill_level * 2.0)
            self.previous_lives = current_lives
            self.previous_score = current_score
            return float(-death_penalty)
        
        # 에피소드 종료/리셋 시 상태 복구
        if current_lives > self.previous_lives:
            self.previous_lives = current_lives
            self.previous_score = current_score

        # 2. 생존 보상 (매 스텝 기본 보상)
        # 목표 스텝에 가까워질수록 보상 증가
        t_target = get_survival_target_steps(skill_level)
        
        # 기본 생존 보상 (스텝당 0.01)
        base_survival_reward = 0.01
        
        # 목표 진행도에 따른 추가 보상
        progress = min(current_steps / t_target, 1.5)  # 최대 150%
        survival_bonus = progress * 0.005  # 진행도 보너스
        
        survival_reward = base_survival_reward + survival_bonus
        
        # 3. 공격 보상 (즉각적 - 적 처치 시 바로 보상)
        score_diff = current_score - self.previous_score
        attack_reward = 0.0
        
        if score_diff > 0:
            # 100점당 1킬로 가정, 킬당 0.5 보상
            kills = score_diff / 100.0
            attack_reward = kills * 0.5
        
        self.previous_score = current_score
        
        # 4. 모드별 가중치 적용
        # survival: w_survival=0.95, w_attack=0.05 → 생존 중심
        # balanced: w_survival=0.50, w_attack=0.50 → 균형
        # attack:   w_survival=0.05, w_attack=0.95 → 공격 중심
        
        final_reward = (
            self.w_survival * survival_reward + 
            self.w_attack * attack_reward
        )
        
        # 최소 보상 보장 (자살 방지)
        final_reward = max(final_reward, 0.005)

        return float(final_reward)

