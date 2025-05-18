"""
수정된 FixedVortexionEnv 환경과 호환되는 랜덤 에이전트
"""

import torch
from tensordict import TensorDict
import random

class FixedRandomAgent:
    """
    간단한 랜덤 행동을 선택하는 에이전트
    개선된 환경에 맞게 수정됨
    """
    
    def __init__(self, env):
        """
        랜덤 에이전트 초기화
        
        Args:
            env: 상호작용할 환경 (FixedVortexionEnv)
        """
        self.env = env
        
        # 이전 행동을 기억하기 위한 변수 (지속성 부여)
        self.last_movement = 1  # 초기값: 정지
        self.movement_counter = 0
        self.max_movement_duration = 10  # 최대 지속 프레임
    
    def reset(self):
        """환경과 에이전트 상태 초기화"""
        self.last_movement = 1
        self.movement_counter = 0
        return self.env.reset()
    
    def act(self, obs=None):
        """
        현재 상태에 기반하여 랜덤 행동 선택
        지속성을 가진 움직임 생성
        
        Args:
            obs: 관측값 (사용하지 않음)
            
        Returns:
            TensorDict: 선택된 행동을 포함한 TensorDict
        """
        # 이동 행동 결정 (지속성 부여)
        if self.movement_counter >= self.max_movement_duration or random.random() < 0.2:
            # 새로운 이동 방향 선택
            movement_probs = torch.tensor([0.45, 0.1, 0.45])  # 왼쪽, 정지, 오른쪽 확률
            self.last_movement = torch.multinomial(movement_probs, 1).item()
            self.movement_counter = 0
            self.max_movement_duration = random.randint(5, 15)  # 지속 시간 랜덤 설정
        else:
            # 이전 이동 방향 유지
            self.movement_counter += 1
        
        # 90% 확률로 발사
        shooting = 1 if random.random() < 0.9 else 0
        
        # 행동 결합
        action = torch.tensor([self.last_movement, shooting], dtype=torch.int64)
        
        # TensorDict로 변환
        tensordict = TensorDict({"action": action}, batch_size=[])
        
        return tensordict
    
    def step(self, action_td):
        """
        환경에서 행동 수행
        
        Args:
            action_td: 행동 정보를 포함한 TensorDict
        
        Returns:
            TensorDict: 다음 상태, 보상 등의 정보를 포함한 TensorDict
        """
        return self.env.step(action_td)
    
    def evaluate(self, num_episodes=5, render=False):
        """
        에이전트 평가
        
        Args:
            num_episodes: 평가할 에피소드 수
            render: 게임 시각화 여부
            
        Returns:
            dict: 평가 결과 (평균 보상, 평균 에피소드 길이 등)
        """
        total_rewards = []
        episode_lengths = []
        
        for episode in range(num_episodes):
            print(f"\n===== 에피소드 {episode+1}/{num_episodes} 시작 =====")
            episode_reward = 0.0
            episode_length = 0
            
            # 환경 초기화
            tensordict = self.reset()
            done = False
            
            # 에피소드 진행
            while not done:
                # 행동 선택
                action_td = self.act(tensordict)
                
                # 환경에서 행동 수행
                next_td = self.step(action_td)
                
                # 보상 누적
                reward = next_td["reward"].item()
                episode_reward += reward
                episode_length += 1
                
                # 종료 여부 확인
                done = next_td["done"].item()
                
                # 다음 상태로 이동
                tensordict = next_td
                
                # 프레임 수 출력 (100프레임마다)
                if episode_length % 100 == 0:
                    print(f"프레임: {episode_length}, 현재 보상: {episode_reward:.2f}")
            
            # 에피소드 결과 기록
            print(f"에피소드 {episode+1} 종료 - 보상: {episode_reward:.2f}, 길이: {episode_length}")
            total_rewards.append(episode_reward)
            episode_lengths.append(episode_length)
        
        # 평가 결과 계산
        mean_reward = sum(total_rewards) / num_episodes
        mean_length = sum(episode_lengths) / num_episodes
        
        print(f"\n===== 평가 결과 =====")
        print(f"평균 보상: {mean_reward:.2f}")
        print(f"평균 에피소드 길이: {mean_length:.2f}")
        
        return {
            "mean_reward": mean_reward,
            "mean_episode_length": mean_length,
            "rewards": total_rewards,
            "lengths": episode_lengths,
        } 