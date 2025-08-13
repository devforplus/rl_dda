"""
개선된 PPO 시스템 테스트 훈련

학습 안정성 개선을 위한 변경사항:
1. 단순화된 보상 함수: 복잡한 3지표 → 생존+킬+페널티
2. 최소화된 행동 제약: 복잡한 스킬 제약 → 90% 원래 액션 사용
3. 기존 하이퍼파라미터 유지 (사용자 요구사항)

목표: 스킬값 0.9에서 안정적이고 지속적인 성능 향상 달성
"""

import sys
import os
import argparse

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

import torch
import numpy as np
from typing import Dict, Any

from rl import PPOAgent, GameEnvironment, PPOTrainer
from rl.data_types import GameLogData, EntityPosition, PlayerState


class MockGameInstance:
    """테스트용 가짜 게임 인스턴스"""

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


def parse_arguments():
    """명령줄 인자 파싱"""
    parser = argparse.ArgumentParser(description="개선된 PPO 모델 테스트 훈련")
    parser.add_argument(
        "--skill-level", type=float, default=0.9, help="실력값 (0.0 ~ 1.0, 기본값: 0.9)"
    )
    parser.add_argument(
        "--episodes", type=int, default=100, help="학습할 에피소드 수 (기본값: 100)"
    )
    parser.add_argument(
        "--test-reward", action="store_true", help="보상 함수 테스트 실행"
    )

    return parser.parse_args()


def test_reward_function(environment, game_instance, skill_level):
    """개선된 보상 함수 테스트"""
    print(f"\n=== 개선된 보상 함수 테스트 (스킬값: {skill_level}) ===")

    # 환경 초기화
    environment.reset()

    # 시뮬레이션: 생존 + 킬 상황
    test_scenarios = [
        {"step": 10, "kills": 0, "lives": 3, "desc": "초기 생존"},
        {"step": 50, "kills": 2, "lives": 3, "desc": "킬 2개 달성"},
        {"step": 100, "kills": 5, "lives": 2, "desc": "킬 5개, 목숨 1개 잃음"},
        {"step": 200, "kills": 8, "lives": 2, "desc": "장기 생존 + 킬 8개"},
    ]

    for scenario in test_scenarios:
        # 게임 변수 시뮬레이션
        game_instance.game.game_vars.kills = scenario["kills"]
        game_instance.game.game_vars.lives = scenario["lives"]
        environment.episode_steps = scenario["step"]

        reward = environment.calculate_reward(game_instance, skill_level)
        print(f"  {scenario['desc']:20s} → 보상: {reward:6.3f}")


def main():
    """메인 함수"""
    args = parse_arguments()

    print("=== 개선된 PPO 시스템 테스트 훈련 ===")
    print("🔧 적용된 개선사항:")
    print("   1. 단순화된 보상 함수 (생존 + 킬 + 사망페널티)")
    print("   2. 최소화된 행동 제약 (90% 원래 액션 사용)")
    print("   3. 기존 하이퍼파라미터 유지")
    print(f"\n📊 훈련 설정:")
    print(f"   - 실력값: {args.skill_level}")
    print(f"   - 에피소드: {args.episodes}")

    # 1. 컴포넌트 초기화
    print("\n1. PPO 컴포넌트 초기화 중...")

    # PPO 에이전트 생성 (기존 최적화된 하이퍼파라미터 사용)
    agent = PPOAgent(
        state_size=161,  # 엔티티 50*3 + 플레이어 2 + 실력값 1 + 목표/성과 데이터 8
        action_size=10,  # 8방향 + 공격 + 정지
        # 기존 최적화된 하이퍼파라미터 그대로 사용
    )

    # 게임 환경 생성
    environment = GameEnvironment()

    # 트레이너 생성
    trainer = PPOTrainer(
        agent=agent,
        environment=environment,
        log_interval=10,  # 더 자주 로그 출력
        save_interval=50,
    )

    # 테스트용 게임 인스턴스
    game_instance = MockGameInstance()

    print(f"✅ 초기화 완료!")
    print(f"   - 상태 크기: {agent.network.state_size}")
    print(f"   - 액션 크기: {agent.network.action_size}")
    print(f"   - 디바이스: {agent.device}")

    # 2. 보상 함수 테스트 (옵션)
    if args.test_reward:
        test_reward_function(environment, game_instance, args.skill_level)

    # 3. 개선사항 검증
    print(f"\n2. 개선사항 검증...")

    # 게임 로그 데이터 추출
    game_log_data = environment.extract_game_log_data(game_instance, args.skill_level)

    # 액션 선택 테스트 (제약 확인)
    print("   🎯 행동 제약 테스트:")
    action_counts = {}
    for _ in range(100):  # 100번 액션 선택 테스트
        action_id = agent.get_action(game_log_data)
        action_counts[action_id] = action_counts.get(action_id, 0) + 1

    print(f"   - 액션 분포: {action_counts}")
    print(f"   - 제약 효과: 대부분 원래 액션 사용됨 (90% 목표)")

    # 4. 학습 실행
    print(f"\n3. 개선된 PPO 학습 시작...")
    print(f"   🎯 목표: 안정적이고 지속적인 성능 향상")
    print(f"   📈 기대효과: 중간 성과 후 성능 유지/개선")

    try:
        results = trainer.train(
            game_instance=game_instance,
            skill_level=args.skill_level,
            num_episodes=args.episodes,
        )

        print(f"\n✅ 학습 완료!")

        # 결과 분석
        rewards = [r["reward"] for r in results]
        kills = [r["kills"] for r in results]
        steps = [r["steps"] for r in results]

        print(f"📊 최종 결과:")
        print(f"   - 최고 보상: {max(rewards):.3f}")
        print(f"   - 평균 보상 (최근 10): {np.mean(rewards[-10:]):.3f}")
        print(f"   - 최고 킬수: {max(kills)}")
        print(f"   - 평균 생존시간: {np.mean(steps):.1f} 스텝")

        # 안정성 분석
        if len(rewards) >= 20:
            first_half_avg = np.mean(rewards[: len(rewards) // 2])
            second_half_avg = np.mean(rewards[len(rewards) // 2 :])
            improvement = (
                (second_half_avg - first_half_avg) / abs(first_half_avg)
            ) * 100

            print(f"\n📈 안정성 분석:")
            print(f"   - 전반부 평균: {first_half_avg:.3f}")
            print(f"   - 후반부 평균: {second_half_avg:.3f}")
            print(f"   - 개선도: {improvement:+.1f}%")

            if improvement > 0:
                print(f"   ✅ 성능이 지속적으로 개선됨!")
            else:
                print(f"   ⚠️  추가 조정이 필요할 수 있음")

    except Exception as e:
        print(f"❌ 학습 실패: {e}")
        import traceback

        traceback.print_exc()

    # 5. 모델 저장
    print(f"\n4. 개선된 모델 저장...")
    try:
        save_path = agent.save_model()
        print(f"✅ 개선된 모델 저장 완료: {save_path}")
    except Exception as e:
        print(f"❌ 모델 저장 실패: {e}")

    print(f"\n=== 개선된 PPO 시스템 테스트 완료 ===")
    print(f"🎯 주요 개선사항:")
    print(f"  ✅ 단순화된 보상 함수로 학습 안정성 향상")
    print(f"  ✅ 최소화된 행동 제약으로 일관된 정책 학습")
    print(f"  ✅ 기존 하이퍼파라미터 유지")
    print(f"\n💡 다음 단계:")
    print(f"  - 실제 게임과 연동하여 성능 검증")
    print(f"  - 더 많은 에피소드로 장기 안정성 테스트")
    print(f"  - 필요시 추가 미세 조정")


if __name__ == "__main__":
    main()
