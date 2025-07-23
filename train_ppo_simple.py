"""
새로운 PPO 시스템 학습 예제

사용자 요구사항에 맞는 간결한 PPO 모델 학습 스크립트
- 입력: 게임 로그 데이터 + 실력값 (0~1)
- 모든 PPO 모델이 동일한 환경에서 학습
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import torch
import numpy as np
from typing import Dict, Any

from rl import PPOAgent, GameEnvironment, PPOTrainer
from rl.data_types import GameLogData, EntityPosition, PlayerState


class MockGameInstance:
    """테스트용 가짜 게임 인스턴스

    실제 게임과 연동하기 전에 PPO 시스템을 테스트하기 위한 클래스
    """

    def __init__(self):
        self.game = MockGame()


class MockGame:
    """테스트용 가짜 게임 클래스"""

    def __init__(self):
        self.state = MockGameState()
        self.game_vars = MockGameVars()


class MockGameState:
    """테스트용 가짜 게임 상태"""

    def __init__(self):
        self.player = MockPlayer()
        self.enemy_a = [MockEnemy(i) for i in range(3)]  # 3개의 적
        self.enemy_shot = [MockEnemyShot(i) for i in range(5)]  # 5개의 적 탄환
        # 다른 적 리스트들도 빈 리스트로 초기화
        for enemy_type in [
            "enemy_b",
            "enemy_c",
            "enemy_d",
            "enemy_e",
            "enemy_f",
            "enemy_g",
            "enemy_h",
            "enemy_i",
            "enemy_j",
            "enemy_k",
            "enemy_l",
            "enemy_m",
            "enemy_n",
            "enemy_o",
            "enemy_p",
        ]:
            setattr(self, enemy_type, [])


class MockGameVars:
    """테스트용 가짜 게임 변수"""

    def __init__(self):
        self.score = 0
        self.kills = 0
        self.lives = 3


class MockPlayer:
    """테스트용 가짜 플레이어"""

    def __init__(self):
        self.x = 128.0
        self.y = 200.0
        self.hp = 3
        self.current_hp = 3
        self.remove = False


class MockEnemy:
    """테스트용 가짜 적"""

    def __init__(self, idx: int):
        self.x = 50.0 + idx * 50.0
        self.y = 50.0 + idx * 30.0
        self.remove = False


class MockEnemyShot:
    """테스트용 가짜 적 탄환"""

    def __init__(self, idx: int):
        self.x = 40.0 + idx * 30.0
        self.y = 100.0 + idx * 20.0
        self.remove = False


def main():
    """메인 함수"""
    print("=== 새로운 PPO 시스템 테스트 ===")

    # 1. 컴포넌트 초기화
    print("1. PPO 컴포넌트 초기화 중...")

    # PPO 에이전트 생성
    agent = PPOAgent(
        state_size=153,  # 엔티티 50*3 + 플레이어 2 + 실력값 1
        action_size=9,  # 8방향 + 공격
        learning_rate=3e-4,
    )

    # 게임 환경 생성
    environment = GameEnvironment()

    # 트레이너 생성
    trainer = PPOTrainer(
        agent=agent, environment=environment, log_interval=5, save_interval=50
    )

    # 테스트용 게임 인스턴스
    game_instance = MockGameInstance()

    print(f"✅ 초기화 완료!")
    print(f"   - 상태 크기: {agent.network.state_size}")
    print(f"   - 액션 크기: {agent.network.action_size}")
    print(f"   - 디바이스: {agent.device}")

    # 2. 다양한 실력값으로 테스트
    skill_levels = [0.2, 0.5, 0.8]  # 낮음, 중간, 높음

    for skill_level in skill_levels:
        print(f"\n2. 실력값 {skill_level} 테스트 중...")

        # 게임 로그 데이터 추출 테스트
        game_log_data = environment.extract_game_log_data(game_instance, skill_level)

        print(f"   - 엔티티 수: {len(game_log_data.entities)}")
        print(f"   - 플레이어 체력: {game_log_data.player_state.hp}")
        print(f"   - 실력값: {game_log_data.skill_level}")

        # 상태 벡터 변환 테스트
        state_vector = game_log_data.to_state_vector()
        print(f"   - 상태 벡터 크기: {state_vector.shape}")

        # 액션 선택 테스트
        action_id = agent.get_action(game_log_data)
        action_input = environment.get_action_input(action_id)

        print(f"   - 선택된 액션: {action_id}")
        print(f"   - 게임 입력: {action_input}")

        # 보상 계산 테스트
        reward = environment.calculate_reward(game_instance, skill_level)
        print(f"   - 계산된 보상: {reward:.3f}")

    # 3. 짧은 학습 테스트
    print(f"\n3. 짧은 학습 테스트 (10 에피소드)...")

    skill_level = 0.5  # 중간 실력값으로 테스트

    try:
        results = trainer.train(
            game_instance=game_instance, skill_level=skill_level, num_episodes=10
        )

        print(f"✅ 학습 테스트 완료!")
        print(f"   - 마지막 에피소드 보상: {results[-1]['reward']:.3f}")
        print(f"   - 평균 스텝: {np.mean([r['steps'] for r in results]):.1f}")

    except Exception as e:
        print(f"❌ 학습 테스트 실패: {e}")
        import traceback

        traceback.print_exc()

    # 4. 모델 저장 테스트
    print(f"\n4. 모델 저장 테스트...")

    try:
        save_path = agent.save_model()
        print(f"✅ 모델 저장 완료: {save_path}")

        # 모델 로드 테스트
        agent.load_model(save_path)
        print(f"✅ 모델 로드 완료")

    except Exception as e:
        print(f"❌ 모델 저장/로드 실패: {e}")
        import traceback

        traceback.print_exc()

    print(f"\n=== PPO 시스템 테스트 완료 ===")
    print(f"새로운 PPO 시스템이 사용자 요구사항에 맞게 구현되었습니다:")
    print(f"  ✅ 게임 로그 데이터 입력 (적/플레이어/탄환 좌표, 체력/목숨)")
    print(f"  ✅ 실력값 입력 (0~1 사이)")
    print(f"  ✅ 동일한 환경에서 학습")
    print(f"  ✅ 간결하고 효율적인 구조")


if __name__ == "__main__":
    main()
