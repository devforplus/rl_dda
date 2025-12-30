"""
PPO (Proximal Policy Optimization) 알고리즘 구현
랜덤 에이전트 생성을 위한 기본 PPO 에이전트 및 게임 환경 클래스
PyTorch 기반 구현
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
    """실력값에 따른 생존 목표 스텝 계산 (targets.py 동기화)"""
    # 이산적인 주요 지점 정의
    targets = {0.1: 300, 0.5: 1000, 1.0: 1500}
    
    # 정확한 매칭 확인
    for k, v in targets.items():
        if abs(skill_level - k) < 1e-7:
            return float(v)
            
    # 선형 보간 (Fallback)
    if skill_level <= 0.5:
        return 300 + (max(0, skill_level - 0.1)) * (700 / 0.4) # 0.1(300) ~ 0.5(1000)
    else:
        return 1000 + (skill_level - 0.5) * (500 / 0.5) # 0.5(1000) ~ 1.0(1500)


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
    """게임 환경 래퍼 클래스"""
    
    def __init__(self):
        """게임 환경 초기화"""
        self.state_size = 161
        self.action_size = 10
        self.previous_lives = 3
        self.previous_score = 0

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
        연구 기반 커리큘럼 러닝 보상 함수
        
        Args:
            game_state: GameStateStage 인스턴스
            skill_level: 실력값 (0.0 ~ 1.0)
            current_steps: 에피소드 진행 스텝
            prev_score: 이전 점수 (여기서는 사용하지 않고 game_vars에서 직접 가져옴)
            
        Returns:
            final_reward: 계산된 보상 (0.0 ~ 1.0 스케일)
        """
        if not game_state:
            return 0.0
            
        game_vars = getattr(game_state, 'game', None)
        if game_vars and hasattr(game_vars, 'game_vars'):
            gv = game_vars.game_vars
        else:
            return 0.0

        # 1. 실력값 기반 적응적 목표 설정
        # 생존 목표: 0.1(300), 0.5(900), 1.0(1500)
        if skill_level <= 0.5:
            t_target = 300 + (max(0, skill_level - 0.1)) * (600 / 0.4)
        else:
            t_target = 900 + (skill_level - 0.5) * (600 / 0.5)
            
        # 공격 목표: 0.1(0.3), 0.5(1.5), 1.0(3.0) -> skill * 3.0
        target_kill_rate = skill_level * 3.0

        # 2. 지표 계산
        # 생존 지표 (Survival Score)
        # [개선] 목표 달성 후에도 보상이 계속 증가하도록 캡 제거 및 로직 수정
        if current_steps <= t_target:
            survival_score = current_steps / t_target
        else:
            # 목표 달성 이후에는 보너스 구간으로 진입 (지속적인 동기 부여)
            survival_score = 1.0 + (current_steps - t_target) / 1000.0
        
        # 공격 지표 (Attack Score)
        current_score = gv.score
        kills_so_far = current_score / 100.0
        if current_steps > 0:
            current_kill_rate = (kills_so_far / current_steps) * 100.0
            # [개선] 공격 목표 달성 시에도 추가 보너스 부여
            if target_kill_rate > 0:
                attack_score = current_kill_rate / target_kill_rate
            else:
                attack_score = 1.0
        else:
            attack_score = 0.0

        # 3. 커리큘럼 단계별 가중치 설정
        if skill_level <= 0.3:
            # 초보자: 생존 마스터 단계 (80% → 65% 생존)
            progress = skill_level / 0.3
            w_survival = 0.8 - (progress * 0.15)
            w_attack = 0.2 + (progress * 0.15)
        elif skill_level <= 0.6:
            # 중급자: 안전한 공격 단계 (65% → 50% 생존)
            progress = (skill_level - 0.3) / 0.3
            w_survival = 0.65 - (progress * 0.15)
            w_attack = 0.35 + (progress * 0.15)
        elif skill_level <= 0.8:
            # 중고급자: 균형잡힌 전투 단계 (50% → 40% 생존)
            progress = (skill_level - 0.6) / 0.2
            w_survival = 0.5 - (progress * 0.1)
            w_attack = 0.5 + (progress * 0.1)
        else:
            # 고수: 공격적 플레이 단계 (40% → 35% 생존)
            progress = (skill_level - 0.8) / 0.2
            w_survival = 0.4 - (progress * 0.05)
            w_attack = 0.6 + (progress * 0.05)

        # 4. 최종 보상 계산 및 사망 페널티
        # 기본 생존/공격 보상 합산
        final_reward = (w_survival * survival_score + w_attack * attack_score)
        
        # [수정] 매 스텝 아주 작은 생존 보너스를 주어 목표 달성 후에도 자살하지 않도록 유도
        final_reward += 0.01
        
        # 사망 페널티 (목숨 감소 시 발생)
        current_lives = gv.lives
        death_penalty = 0.0
        if current_lives < self.previous_lives:
            # [수정] 사망 페널티를 더 강력한 음수값으로 설정하고 클리핑 제거
            death_penalty = 1.0 + (skill_level * 2.0) # Skill 0.1 -> 1.2 페널티
            self.previous_lives = current_lives
            # 사망한 순간에는 확실한 마이너스 보상 반환
            return float(-death_penalty)
        
        # 에피소드 종료/리셋 시 목숨 값 복구
        if current_lives > self.previous_lives:
            self.previous_lives = current_lives

        return float(final_reward)

