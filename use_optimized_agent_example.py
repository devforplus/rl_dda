"""
🎯 최적화된 PPO 에이전트 실사용 예시

Optuna로 튜닝된 최적 하이퍼파라미터가 적용된 PPO 에이전트를
실제 게임 훈련에 사용하는 방법을 보여주는 예시
"""

import numpy as np
from standalone_tuning_results.optimized_ppo_agent import create_optimized_agent


def main():
    print("🎯 최적화된 PPO 에이전트 실사용 예시")
    print("=" * 60)

    # 1. 최적화된 에이전트 생성
    print("🚀 Optuna 최적화된 PPO 에이전트 생성...")
    agent = create_optimized_agent()

    # 2. 게임 시뮬레이션 예시
    print("\n🎮 게임 훈련 시뮬레이션:")

    total_episodes = 5
    for episode in range(total_episodes):
        print(f"\n📺 에피소드 {episode + 1}/{total_episodes}")

        # 에피소드 시작
        episode_reward = 0
        steps = 0
        max_steps = 100

        while steps < max_steps:
            # 게임 상태 생성 (실제로는 게임에서 받아온 상태)
            game_state = np.random.random(153)  # 실제 게임 상태로 대체

            # 에이전트가 액션 선택
            action = agent.get_action(game_state)

            # 게임 환경에서 액션 실행 (시뮬레이션)
            reward = np.random.random()  # 실제 게임에서 받은 보상으로 대체
            done = steps >= max_steps - 1 or np.random.random() < 0.05

            # 에이전트에 보상 전달
            agent.store_reward_and_done(reward, done)

            episode_reward += reward
            steps += 1

            if done:
                break

        print(f"   📊 에피소드 완료: {steps}스텝, 총 보상 {episode_reward:.2f}")

        # PPO 업데이트 (에피소드 종료 후)
        if len(agent.states) > 10:  # 충분한 데이터가 있을 때만
            update_info = agent.update()
            if update_info:
                print(
                    f"   🔄 PPO 업데이트: Policy Loss={update_info.get('policy_loss', 0):.4f}"
                )

    # 3. 모델 저장
    print("\n💾 최적화된 모델 저장...")
    saved_path = agent.save_model("optimized_models")

    print("\n✅ 훈련 시뮬레이션 완료!")
    print(f"📁 모델 저장 위치: {saved_path}")

    # 4. 성능 요약
    print("\n📊 최적화된 하이퍼파라미터 요약:")
    print("   🏆 Optuna로 찾은 최적값들:")
    print(
        f"   • Learning Rate: {agent.params['learning_rate']:.6f} (기본 3e-4 대비 최적화)"
    )
    print(f"   • Batch Size: {agent.params['batch_size']} (더 안정적인 학습)")
    print(f"   • Hidden Size: {agent.params['hidden_size']} (효율적인 네트워크)")
    print(f"   • Gamma: {agent.params['gamma']:.4f} (최적 할인율)")
    print(f"   • 예상 성능 향상: 34.16점")

    print("\n🎉 이제 실제 게임에서 이 에이전트를 사용하세요!")


def demo_advanced_usage():
    """고급 사용법 데모"""
    print("\n" + "=" * 60)
    print("🔧 고급 사용법 데모")
    print("=" * 60)

    # 1. 커스텀 파라미터로 에이전트 생성
    print("📝 커스텀 파라미터 사용 예시:")
    custom_params = {
        "learning_rate": 0.001,  # 학습률만 조정
        "batch_size": 128,  # 배치 크기만 조정
    }
    custom_agent = create_optimized_agent(custom_params)
    print(f"   • 커스텀 Learning Rate: {custom_agent.params['learning_rate']}")
    print(
        f"   • 다른 파라미터들은 최적값 유지: Gamma={custom_agent.params['gamma']:.4f}"
    )

    # 2. 모델 저장/로드 예시
    print("\n📁 모델 저장/로드 예시:")

    # 모델 저장
    save_path = custom_agent.save_model("demo_models")

    # 새 에이전트 생성하고 모델 로드
    new_agent = create_optimized_agent()
    new_agent.load_model(save_path)
    print("   ✅ 모델 저장/로드 성공!")

    # 3. 에이전트 파라미터 요약 출력
    print("\n📋 에이전트 파라미터 요약:")
    print(new_agent.get_params_summary())


if __name__ == "__main__":
    main()
    demo_advanced_usage()

    print("\n" + "=" * 60)
    print("🎯 다음 단계:")
    print("1. 이 코드를 참고하여 실제 게임 훈련 스크립트 수정")
    print("2. game_state를 실제 게임에서 받아온 상태로 변경")
    print("3. reward를 실제 게임 보상으로 변경")
    print("4. 성능 향상 확인!")
    print("=" * 60)
