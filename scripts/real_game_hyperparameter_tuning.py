"""
🎯 실제 게임 환경 연동 하이퍼파라미터 튜닝

train_ppo_real_game.py와 직접 연동하여
실제 Pyxel 게임에서 PPO 성능을 최적화
"""

import optuna
import sys
import os
import time
import subprocess
import json
from typing import Dict, Any, List
import tempfile
import shutil
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)


class RealGameHyperparameterTuner:
    """실제 게임 환경과 연동된 하이퍼파라미터 튜너"""

    def __init__(
        self,
        n_trials: int = 30,  # 테스트용으로 줄임
        n_eval_episodes: int = 100,  # 테스트용으로 줄임
        max_steps_per_episode: int = 1000,  # 테스트용으로 줄임
        skill_level: float = 0.9,
        study_name: str = "real_game_ppo_tuning",
    ):
        """튜너 초기화"""
        self.n_trials = n_trials
        self.n_eval_episodes = n_eval_episodes
        self.max_steps_per_episode = max_steps_per_episode
        self.skill_level = skill_level
        self.study_name = study_name

        # 결과 저장 디렉토리
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.results_dir = f"real_game_tuning_results_{timestamp}"
        os.makedirs(self.results_dir, exist_ok=True)

        print(f"🎮 실제 게임 하이퍼파라미터 튜닝 시작")
        print(f"📁 결과 저장: {self.results_dir}")
        print(f"🎯 평가 조건: {n_eval_episodes}에피소드 x {max_steps_per_episode}스텝")
        print(f"🎪 스킬레벨: {skill_level}")

    def suggest_hyperparameters(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Optuna trial에서 하이퍼파라미터 제안"""
        return {
            # === PPO 핵심 파라미터 ===
            "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-2, log=True),
            "gamma": trial.suggest_float("gamma", 0.9, 0.999),
            "gae_lambda": trial.suggest_float("gae_lambda", 0.8, 0.98),
            "clip_epsilon": trial.suggest_float("clip_epsilon", 0.1, 0.3),
            "value_coef": trial.suggest_float("value_coef", 0.1, 1.0),
            "entropy_coef": trial.suggest_float("entropy_coef", 0.001, 0.1, log=True),
            # === 네트워크 구조 ===
            "hidden_size": trial.suggest_categorical("hidden_size", [32, 64, 128]),
            "num_layers": trial.suggest_int("num_layers", 2, 3),
            "activation": trial.suggest_categorical("activation", ["relu", "tanh"]),
            "grad_clip_norm": trial.suggest_float("grad_clip_norm", 0.1, 2.0),
            # === 훈련 파라미터 ===
            "batch_size": trial.suggest_categorical("batch_size", [64, 128, 256]),
            "num_epochs": trial.suggest_int("num_epochs", 3, 6),
        }

    def run_real_game_training(self, hyperparams: Dict[str, Any]) -> Dict[str, float]:
        """실제 게임에서 주어진 하이퍼파라미터로 훈련 실행"""
        try:
            # 실제 게임 훈련 실행 (간단한 명령어로)
            cmd = [
                "rye",
                "run",
                "python",
                "train_ppo_real_game.py",
                "--episodes",
                str(self.n_eval_episodes),
                "--skill-level",
                str(self.skill_level),
                "--max-steps",
                str(self.max_steps_per_episode),
                "--learning-rate",
                str(hyperparams["learning_rate"]),
                "--gamma",
                str(hyperparams["gamma"]),
                "--gae-lambda",
                str(hyperparams["gae_lambda"]),
                "--clip-epsilon",
                str(hyperparams["clip_epsilon"]),
                "--value-coef",
                str(hyperparams["value_coef"]),
                "--entropy-coef",
                str(hyperparams["entropy_coef"]),
                "--hidden-size",
                str(hyperparams["hidden_size"]),
                "--num-layers",
                str(hyperparams["num_layers"]),
                "--activation",
                str(hyperparams["activation"]),
                "--grad-clip-norm",
                str(hyperparams["grad_clip_norm"]),
                "--batch-size",
                str(hyperparams["batch_size"]),
                "--num-epochs",
                str(hyperparams["num_epochs"]),
                # 복잡한 옵션들 제거 - 출력 파싱으로 해결
            ]

            print(f"🎮 실행 중: {' '.join(cmd[:5])}...")

            # subprocess로 실행하고 결과 캡처
            env = os.environ.copy()
            env["PYTHONIOENCODING"] = "utf-8"
            env["PYTHONLEGACYWINDOWSSTDIO"] = "1"
            env["PYTHONUNBUFFERED"] = "1"  # Python stdout 버퍼링 비활성화
            env["PYTHONFAULTHANDLER"] = "1"  # 오류 추적 활성화

            result = subprocess.run(
                cmd,
                cwd=project_root,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",  # 인코딩 오류 시 대체 문자 사용
                timeout=1800,  # 30분으로 크게 늘림 (50에피소드 대응)
                env=env,
                shell=False,  # shell 비활성화로 더 직접적인 실행
            )

            # 디버깅: subprocess 결과 출력
            print(f"📋 Return code: {result.returncode}")
            if result.stderr:
                print(f"⚠️ stderr: {result.stderr[:200]}...")  # 처음 200자만
            if result.stdout is not None:
                print(f"📄 stdout 길이: {len(result.stdout)} 문자")
                print(
                    f"📄 stdout 마지막 500자:\n{result.stdout[-500:]}"
                )  # 마지막 500자 확인
            else:
                print("❌ stdout이 None입니다!")

            # 결과 파싱
            if result.returncode == 0 and result.stdout is not None:
                performance = self._parse_training_output(result.stdout)
                print(f"🔍 파싱된 성능: {performance}")
                return performance
            else:
                print(
                    f"❌ 훈련 실패: Return code {result.returncode}, stdout: {result.stdout is not None}"
                )
                return {
                    "score": 0.0,
                    "kills": 0.0,
                    "survival_time": 0.0,
                    "avg_reward": 0.0,
                }

        except subprocess.TimeoutExpired:
            print("⏰ 훈련 타임아웃")
            return {"score": 0.0, "kills": 0.0, "survival_time": 0.0, "avg_reward": 0.0}
        except Exception as e:
            print(f"💥 예외 발생: {e}")
            return {"score": 0.0, "kills": 0.0, "survival_time": 0.0, "avg_reward": 0.0}

    def _parse_training_output(self, output: str) -> Dict[str, float]:
        """훈련 출력에서 성능 지표 추출 (개선된 버전)"""
        performance = {
            "score": 0.0,
            "kills": 0.0,
            "survival_time": 0.0,
            "avg_reward": 0.0,
        }

        if not output or not isinstance(output, str):
            print(f"⚠️ 출력이 비어있거나 잘못된 타입입니다: {type(output)}")
            return performance

        try:
            lines = output.split("\n")

            # 에피소드 완료 메시지에서 정확한 패턴으로 추출
            for line in lines:
                # "📊 에피소드 1/1 완료" 패턴 찾기
                if "에피소드" in line and "완료" in line:
                    # 다음 몇 줄에서 성능 데이터 찾기
                    continue

                # "   - 보상: 341.68" 패턴
                if "- 보상:" in line:
                    import re

                    match = re.search(r"보상:\s*([\d.-]+)", line)
                    if match:
                        performance["avg_reward"] = float(match.group(1))

                # "   - 생존시간: 672 스텝" 패턴
                elif "- 생존시간:" in line:
                    import re

                    match = re.search(r"생존시간:\s*([\d.]+)", line)
                    if match:
                        performance["survival_time"] = float(match.group(1))

                # "   - 점수: 600" 패턴
                elif "- 점수:" in line:
                    import re

                    match = re.search(r"점수:\s*([\d.]+)", line)
                    if match:
                        performance["score"] = float(match.group(1))

                # "   - 킬 수: 6" 패턴
                elif "- 킬 수:" in line:
                    import re

                    match = re.search(r"킬 수:\s*([\d.]+)", line)
                    if match:
                        performance["kills"] = float(match.group(1))

            # 대안: 성과 통계 섹션에서 찾기
            in_performance_section = False
            for line in lines:
                if "📊 성과 통계:" in line:
                    in_performance_section = True
                    continue

                if in_performance_section:
                    # "   - 평균 보상: 341.68" 패턴
                    if "평균 보상:" in line:
                        import re

                        match = re.search(r"평균 보상:\s*([\d.-]+)", line)
                        if match:
                            performance["avg_reward"] = float(match.group(1))

                    # "   - 평균 생존시간: 672.0 스텝" 패턴
                    elif "평균 생존시간:" in line:
                        import re

                        match = re.search(r"평균 생존시간:\s*([\d.]+)", line)
                        if match:
                            performance["survival_time"] = float(match.group(1))

                    # "   - 평균 점수: 600" 패턴
                    elif "평균 점수:" in line:
                        import re

                        match = re.search(r"평균 점수:\s*([\d.]+)", line)
                        if match:
                            performance["score"] = float(match.group(1))

                    # "   - 평균 킬/에피소드: 6.0" 패턴
                    elif "평균 킬/에피소드:" in line:
                        import re

                        match = re.search(r"평균 킬/에피소드:\s*([\d.]+)", line)
                        if match:
                            performance["kills"] = float(match.group(1))

                    # 성과 통계 섹션 끝 감지
                    elif line.strip() and not line.startswith("   -"):
                        in_performance_section = False

        except Exception as e:
            print(f"⚠️ 출력 파싱 오류: {e}")

        return performance

    def objective(self, trial: optuna.Trial) -> float:
        """Optuna 목적 함수"""
        # 하이퍼파라미터 제안
        hyperparams = self.suggest_hyperparameters(trial)

        print(f"\n🔬 Trial {trial.number + 1}/{self.n_trials}")
        print(f"📊 주요 파라미터:")
        print(f"   learning_rate: {hyperparams['learning_rate']:.6f}")
        print(f"   hidden_size: {hyperparams['hidden_size']}")
        print(f"   batch_size: {hyperparams['batch_size']}")

        # 실제 게임에서 성능 측정
        performance = self.run_real_game_training(hyperparams)

        # 복합 성능 점수 계산
        composite_score = (
            performance["score"] * 0.4
            + performance["kills"] * 100 * 0.3
            + performance["survival_time"] * 0.3
        )

        print(f"📈 성능 결과:")
        print(f"   점수: {performance['score']:.1f}")
        print(f"   킬수: {performance['kills']:.1f}")
        print(f"   생존시간: {performance['survival_time']:.1f}")
        print(f"   복합점수: {composite_score:.2f}")

        # trial에 추가 정보 저장
        trial.set_user_attr("score", performance["score"])
        trial.set_user_attr("kills", performance["kills"])
        trial.set_user_attr("survival_time", performance["survival_time"])
        trial.set_user_attr("avg_reward", performance["avg_reward"])

        return composite_score

    def run_tuning(self) -> optuna.Study:
        """하이퍼파라미터 튜닝 실행"""
        print(f"\n🚀 실제 게임 하이퍼파라미터 튜닝 시작")
        print(f"🎯 목표: {self.n_trials}회 시행으로 최적 파라미터 찾기")
        print("=" * 60)

        # Optuna 로깅 비활성화
        optuna.logging.set_verbosity(optuna.logging.WARNING)

        # Optuna 스터디 생성 (간단한 설정)
        study = optuna.create_study(direction="maximize")

        # 튜닝 실행
        start_time = time.time()

        try:
            study.optimize(self.objective, n_trials=self.n_trials)
        except KeyboardInterrupt:
            print("\n⚠️ 사용자에 의해 중단됨")

        elapsed_time = time.time() - start_time

        # 결과 저장 및 분석
        self._save_results(study, elapsed_time)

        return study

    def _save_results(self, study: optuna.Study, elapsed_time: float):
        """결과 저장 및 분석"""
        print(f"\n🎉 하이퍼파라미터 튜닝 완료!")
        print(f"⏱️  소요시간: {elapsed_time / 60:.1f}분")
        print(f"🔬 완료된 시행: {len(study.trials)}")

        if len(study.trials) == 0:
            print("❌ 완료된 시행이 없습니다.")
            return

        # 최적 결과
        best_trial = study.best_trial
        best_params = best_trial.params
        best_score = best_trial.value

        print(f"\n🏆 최적 결과:")
        print(f"   복합 점수: {best_score:.2f}")
        print(f"   게임 점수: {best_trial.user_attrs.get('score', 0):.1f}")
        print(f"   킬 수: {best_trial.user_attrs.get('kills', 0):.1f}")
        print(f"   생존시간: {best_trial.user_attrs.get('survival_time', 0):.1f}")

        print(f"\n🔧 최적 하이퍼파라미터:")
        for key, value in best_params.items():
            print(f"   {key}: {value}")

        # JSON 저장
        results = {
            "best_params": best_params,
            "best_score": best_score,
            "best_performance": {
                "score": best_trial.user_attrs.get("score", 0),
                "kills": best_trial.user_attrs.get("kills", 0),
                "survival_time": best_trial.user_attrs.get("survival_time", 0),
            },
        }

        results_file = os.path.join(self.results_dir, "best_results.json")
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 결과 저장 완료: {results_file}")


def main():
    """메인 실행 함수"""
    print("🎮 실제 게임 연동 하이퍼파라미터 튜닝")
    print("=" * 50)

    # 파라미터 설정 (현실적이고 효율적인 튜닝을 위해)
    tuner = RealGameHyperparameterTuner(
        n_trials=10,  # 10회 시행 (적당한 샘플링)
        n_eval_episodes=30,  # 3에피소드로 안정적 평가
        max_steps_per_episode=1000,  # 1000스텝으로 충분히 늘림
        skill_level=0.7,  # 0.7로 조정 (높지만 과도하지 않게)
        study_name="real_game_test",
    )

    # 튜닝 실행
    study = tuner.run_tuning()

    # 결과 분석
    if len(study.trials) > 0:
        print(f"\n📊 튜닝 완료!")
        print(f"최적 성능: {study.best_value:.2f}")
        print(f"결과 저장: {tuner.results_dir}")
    else:
        print("❌ 튜닝 실패")


if __name__ == "__main__":
    main()
