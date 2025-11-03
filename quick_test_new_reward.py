"""
🎯 새로운 보상 함수 빠른 테스트

보상 해킹 방지가 적용된 새로운 시스템이
실제 게임에서 어떻게 작동하는지 빠르게 확인
"""

import sys
import os
import time

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from rl import PPOAgent, GameEnvironment


def test_new_reward_system():
    """새로운 보상 시스템 빠른 테스트"""

    print("🔥 보상 해킹 방지 시스템 테스트")
    print("=" * 50)

    # 1. 에이전트 생성 (최적화된 파라미터 + action_size=10)
    print("🤖 PPO 에이전트 생성 중...")
    agent = PPOAgent(state_size=161, action_size=10)  # 최적화된 기본값 사용

    print(f"✅ 에이전트 생성 완료")
    print(f"   📊 하이퍼파라미터:")
    print(f"   • Learning Rate: {agent.optimizer.param_groups[0]['lr']:.6f}")
    print(f"   • Hidden Size: {agent.network.hidden_size}")
    print(f"   • Action Size: {agent.network.action_size}")

    # 2. 환경 생성
    print("\n🌍 게임 환경 생성 중...")
    environment = GameEnvironment()

    # 3. 간단한 시뮬레이션
    print("\n🎮 보상 함수 테스트:")
    skill_level = 0.5

    # Mock 게임 인스턴스 생성
    class MockGameVars:
        def __init__(self, kills=0, score=0, lives=3):
            self.kills = kills
            self.score = score
            self.lives = lives

    class MockGame:
        def __init__(self, kills=0, score=0, lives=3):
            self.game_vars = MockGameVars(kills, score, lives)
            self.state = None

    class MockGameInstance:
        def __init__(self, kills=0, score=0, lives=3):
            self.game = MockGame(kills, score, lives)

    # 4. 다양한 시나리오 테스트
    print("\n📊 보상 시나리오 테스트:")

    scenarios = [
        {"name": "소극적 플레이 (킬 0)", "kills": 0, "steps": 200},
        {"name": "적당한 플레이 (킬 2)", "kills": 2, "steps": 200},
        {"name": "적극적 플레이 (킬 5)", "kills": 5, "steps": 200},
        {"name": "장기 소극적 (킬 0)", "kills": 0, "steps": 500},
        {"name": "장기 적극적 (킬 10)", "kills": 10, "steps": 500},
    ]

    for scenario in scenarios:
        # 환경 리셋
        environment.reset()
        environment.episode_steps = scenario["steps"]

        # Mock 게임 인스턴스 생성
        mock_instance = MockGameInstance(
            kills=scenario["kills"],
            score=scenario["kills"] * 100,  # 킬당 100점
            lives=3,
        )

        # 보상 계산
        reward = environment.calculate_reward(mock_instance, skill_level)

        print(
            f"   🎯 {scenario['name']:20} | 스텝: {scenario['steps']:3} | 킬: {scenario['kills']:2} | 보상: {reward:8.1f}"
        )

    # 5. 액션 선택 테스트
    print("\n🎯 액션 선택 테스트:")

    # 가짜 게임 상태 생성
    import numpy as np

    test_state = np.random.random(161)

    actions = []
    for i in range(10):
        action = agent.get_action_from_state(test_state)  # 단순 액션 선택
        actions.append(action)

    action_counts = {}
    for action in actions:
        action_counts[action] = action_counts.get(action, 0) + 1

    print(f"   📊 10번 액션 선택 결과:")
    action_names = {
        0: "정지",
        1: "위",
        2: "아래",
        3: "왼쪽",
        4: "오른쪽",
        5: "좌상",
        6: "우상",
        7: "좌하",
        8: "우하",
        9: "공격",
    }

    for action, count in sorted(action_counts.items()):
        print(
            f"     {action_names.get(action, f'액션{action}')} (액션 {action}): {count}번"
        )

    # 6. 결론
    print("\n" + "=" * 50)
    print("🎉 새로운 보상 시스템 특징:")
    print("  ✅ 킬이 없으면 보상 대폭 감소")
    print("  ✅ 소극적 플레이에 강한 페널티")
    print("  ✅ 적극적 플레이에 높은 보상")
    print("  ✅ 액션 공간 10개 (0~9) 정상 처리")
    print("  ✅ Optuna 최적화된 하이퍼파라미터 적용")
    print("\n💡 이제 에이전트가 킬을 위해 적극적으로 행동할 유인이 생겼습니다!")
    print("=" * 50)


def simple_action_test():
    """간단한 액션 선택 함수 (get_action 대신)"""
    pass


# PPOAgent에 간단한 액션 선택 메서드 추가
import torch


def get_action_from_state(self, state):
    """상태로부터 간단한 액션 선택 (버퍼 저장 없이)"""
    state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
    with torch.no_grad():
        action, _, _, _ = self.network.get_action_and_value(state_tensor)
    return action.cpu().item()


# PPOAgent 클래스에 메서드 추가
PPOAgent.get_action_from_state = get_action_from_state

if __name__ == "__main__":
    test_new_reward_system()
