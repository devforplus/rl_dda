"""
🔍 Optuna 최적화된 파라미터 적용 검증 스크립트

실제 게임에서 사용되는 PPO 에이전트의 파라미터들이
Optuna 최적화된 값들로 정확히 설정되었는지 확인
"""

import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from rl import PPOAgent, GameEnvironment


def verify_optimized_parameters():
    """실제 사용되는 파라미터가 Optuna 최적화된 값인지 검증"""

    print("🔍 Optuna 최적화된 파라미터 적용 검증")
    print("=" * 60)

    # 1. 기본값으로 PPO 에이전트 생성 (최적화된 기본값 사용)
    print("📊 기본값 PPO 에이전트 생성 중...")
    agent = PPOAgent(state_size=161, action_size=10)  # 9 → 10: 액션 공간 수정

    # 2. 실제 사용되는 파라미터 값들 확인
    print("\n🎯 현재 적용된 하이퍼파라미터:")

    # Learning Rate
    lr = agent.optimizer.param_groups[0]["lr"]
    print(f"   • Learning Rate: {lr:.8f}")

    # Gamma
    print(f"   • Gamma: {agent.gamma:.8f}")

    # GAE Lambda
    print(f"   • GAE Lambda: {agent.gae_lambda:.8f}")

    # Clip Epsilon
    print(f"   • Clip Epsilon: {agent.clip_epsilon:.8f}")

    # Value Coefficient
    print(f"   • Value Coef: {agent.value_coef:.8f}")

    # Entropy Coefficient
    print(f"   • Entropy Coef: {agent.entropy_coef:.8f}")

    # Gradient Clipping Norm
    print(f"   • Grad Clip Norm: {agent.grad_clip_norm:.8f}")

    # Network Architecture
    print(f"   • Hidden Size: {agent.network.hidden_size}")
    print(f"   • Num Layers: {agent.network.num_layers}")
    print(f"   • State Size: {agent.network.state_size}")
    print(f"   • Action Size: {agent.network.action_size}")

    # 3. Optuna 최적화된 값들과 비교
    print("\n📈 Optuna 최적화된 목표값과 비교:")

    optuna_values = {
        "learning_rate": 0.00788671412999049,
        "gamma": 0.9800313374635297,
        "gae_lambda": 0.8548304784512067,
        "clip_epsilon": 0.11953442280127678,
        "value_coef": 0.7158097238609412,
        "entropy_coef": 0.007591104805282696,
        "grad_clip_norm": 0.9726261649881027,
        "hidden_size": 64,
        "num_layers": 2,
    }

    current_values = {
        "learning_rate": lr,
        "gamma": agent.gamma,
        "gae_lambda": agent.gae_lambda,
        "clip_epsilon": agent.clip_epsilon,
        "value_coef": agent.value_coef,
        "entropy_coef": agent.entropy_coef,
        "grad_clip_norm": agent.grad_clip_norm,
        "hidden_size": agent.network.hidden_size,
        "num_layers": agent.network.num_layers,
    }

    all_match = True
    for param_name, target_value in optuna_values.items():
        current_value = current_values[param_name]
        match = abs(current_value - target_value) < 1e-10

        if isinstance(target_value, float):
            status = "✅" if match else "❌"
            print(
                f"   {status} {param_name}: {current_value:.8f} (목표: {target_value:.8f})"
            )
        else:
            status = "✅" if current_value == target_value else "❌"
            print(f"   {status} {param_name}: {current_value} (목표: {target_value})")

        if not match and abs(current_value - target_value) > 1e-10:
            all_match = False

    # 4. 최종 결과
    print("\n" + "=" * 60)
    if all_match:
        print("🎉 모든 파라미터가 Optuna 최적화된 값으로 정확히 설정되었습니다!")
        print("✅ 실제 게임에서 최적화된 성능을 기대할 수 있습니다.")
        print("📈 예상 성능 향상: 34.16점")
    else:
        print("⚠️  일부 파라미터가 최적화된 값과 다릅니다.")
        print("🔧 train_ppo_real_game.py에서 하드코딩된 값들을 확인해주세요.")

    print("=" * 60)


if __name__ == "__main__":
    verify_optimized_parameters()
