"""
빠른 PPO 하이퍼파라미터 튜닝 (테스트용)

개발 및 테스트를 위한 간소화된 버전
- 적은 trial 수 (10-20)
- 짧은 평가 시간
- 빠른 결과 확인
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 패스에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.hyperparameter_tuning import HyperparameterTuner


def main():
    """빠른 튜닝 실행"""
    print("🚀 빠른 PPO 하이퍼파라미터 튜닝 시작")
    print("=" * 50)

    # 빠른 설정으로 튜너 초기화
    tuner = HyperparameterTuner(
        n_trials=10,  # 적은 trial 수
        n_eval_episodes=3,  # 짧은 평가
        max_steps_per_episode=200,  # 짧은 에피소드
        results_dir="quick_tuning_results",
    )

    try:
        print("📝 설정:")
        print(f"  • Trials: {tuner.n_trials}")
        print(f"  • 평가 에피소드: {tuner.n_eval_episodes}")
        print(f"  • 최대 스텝: {tuner.max_steps_per_episode}")
        print()

        # 튜닝 실행
        best_params = tuner.run_tuning()

        print("\n" + "=" * 50)
        print("🎉 빠른 튜닝 완료!")
        print("=" * 50)
        print("🏆 최고 성능 파라미터:")
        for key, value in best_params.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.6f}")
            else:
                print(f"  {key}: {value}")

        print(f"\n📊 최고 점수: {tuner.study.best_value:.3f}")
        print(f"📁 결과 저장: {tuner.results_dir}")

    except KeyboardInterrupt:
        print("\n⏹️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
