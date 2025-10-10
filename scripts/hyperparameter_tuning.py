"""
Optuna 기반 PPO 하이퍼파라미터 자동 튜닝 시스템

이 스크립트는 베이지안 최적화를 통해 PPO 에이전트의 최적 하이퍼파라미터를 찾습니다.
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
import warnings

import optuna
import numpy as np
import torch
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 프로젝트 루트를 Python 패스에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.rl.trainer import PPOTrainer
from src.rl.environment import GameEnvironment
from src.rl.ppo_agent import PPOAgent


class HyperparameterTuner:
    """Optuna 기반 하이퍼파라미터 튜너"""

    def __init__(
        self,
        n_trials: int = 50,
        n_eval_episodes: int = 10,
        max_steps_per_episode: int = 1000,
        study_name: str = None,
        storage_url: str = None,
        results_dir: str = "tuning_results",
    ):
        """
        Args:
            n_trials: 튜닝할 trial 수
            n_eval_episodes: 각 trial 평가용 에피소드 수
            max_steps_per_episode: 에피소드당 최대 스텝 수
            study_name: Optuna study 이름
            storage_url: 결과 저장소 URL (None이면 메모리에만 저장)
            results_dir: 결과 저장 디렉토리
        """
        self.n_trials = n_trials
        self.n_eval_episodes = n_eval_episodes
        self.max_steps_per_episode = max_steps_per_episode
        self.results_dir = Path(results_dir)
        self.results_dir.mkdir(exist_ok=True)

        # Study 설정
        if study_name is None:
            study_name = f"ppo_tuning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self.study = optuna.create_study(
            study_name=study_name,
            direction="maximize",  # 점수를 최대화
            storage=storage_url,
            load_if_exists=True,
            sampler=optuna.samplers.TPESampler(seed=42),  # 재현 가능한 결과
        )

        # 결과 저장용
        self.trial_results = []

    def suggest_hyperparameters(self, trial: optuna.Trial) -> Dict[str, Any]:
        """Optuna trial에서 하이퍼파라미터 샘플링

        Args:
            trial: Optuna trial 객체

        Returns:
            샘플링된 하이퍼파라미터 딕셔너리
        """
        return {
            # PPO 핵심 파라미터
            "learning_rate": trial.suggest_float("learning_rate", 1e-5, 1e-2, log=True),
            "gamma": trial.suggest_float("gamma", 0.9, 0.999),
            "gae_lambda": trial.suggest_float("gae_lambda", 0.8, 0.98),
            "clip_epsilon": trial.suggest_float("clip_epsilon", 0.1, 0.3),
            "value_coef": trial.suggest_float("value_coef", 0.1, 1.0),
            "entropy_coef": trial.suggest_float("entropy_coef", 0.001, 0.1, log=True),
            # 학습 파라미터
            "batch_size": trial.suggest_categorical("batch_size", [32, 64, 128, 256]),
            "num_epochs": trial.suggest_int("num_epochs", 3, 6),
            # 네트워크 파라미터
            "hidden_size": trial.suggest_categorical(
                "hidden_size", [64, 128, 256, 512]
            ),
            "num_layers": trial.suggest_int("num_layers", 2, 4),
            # 기타 파라미터
            "grad_clip_norm": trial.suggest_float("grad_clip_norm", 0.1, 1.0),
        }

    def objective(self, trial: optuna.Trial) -> float:
        """Optuna 목적 함수

        Args:
            trial: Optuna trial 객체

        Returns:
            최대화할 목적 함수 값 (평균 점수)
        """
        try:
            # 하이퍼파라미터 샘플링
            params = self.suggest_hyperparameters(trial)

            print(f"\n🔍 Trial {trial.number}: {params}")

            # 환경과 에이전트 초기화
            env = GameEnvironment()
            agent = PPOAgent(
                state_size=153,
                action_size=9,  # ActionType 기준 (0-8)
                learning_rate=params["learning_rate"],
                gamma=params["gamma"],
                gae_lambda=params["gae_lambda"],
                clip_epsilon=params["clip_epsilon"],
                value_coef=params["value_coef"],
                entropy_coef=params["entropy_coef"],
                hidden_size=params["hidden_size"],
                num_layers=params["num_layers"],
                grad_clip_norm=params["grad_clip_norm"],
            )

            # 트레이너 초기화
            trainer = PPOTrainer(
                agent=agent,
                environment=env,
                batch_size=params["batch_size"],
                num_epochs=params["num_epochs"],
            )

            # 짧은 학습 (빠른 평가를 위해)
            training_steps = 500  # 튜닝용으로 짧게 설정
            trainer.train(
                total_steps=training_steps,
                save_interval=None,  # 저장 안함 (튜닝용)
                verbose=False,
            )

            # 성능 평가
            scores = self.evaluate_agent(agent, env)
            avg_score = np.mean(scores)

            print(f"📊 Trial {trial.number} 결과: 평균 점수 = {avg_score:.2f}")

            # 결과 저장
            self.trial_results.append(
                {
                    "trial": trial.number,
                    "params": params,
                    "scores": scores,
                    "avg_score": avg_score,
                    "timestamp": datetime.now().isoformat(),
                }
            )

            # 중간 결과를 trial에 보고 (조기 종료용)
            trial.report(avg_score, step=0)

            # 조기 종료 체크
            if trial.should_prune():
                raise optuna.TrialPruned()

            return avg_score

        except Exception as e:
            print(f"❌ Trial {trial.number} 실패: {e}")
            return -float("inf")  # 실패한 trial에 대해 매우 낮은 점수

    def evaluate_agent(self, agent: PPOAgent, env: GameEnvironment) -> List[float]:
        """에이전트 성능 평가

        Args:
            agent: 평가할 PPO 에이전트
            env: 게임 환경

        Returns:
            각 에피소드의 점수 리스트
        """
        scores = []

        for episode in range(self.n_eval_episodes):
            state = env.reset()
            total_score = 0
            steps = 0

            while steps < self.max_steps_per_episode:
                action = agent.get_action(state)
                next_state, reward, done, info = env.step(action)

                total_score += reward
                steps += 1

                if done:
                    break

                state = next_state

            scores.append(total_score)

        return scores

    def run_tuning(self):
        """하이퍼파라미터 튜닝 실행"""
        print(f"🚀 PPO 하이퍼파라미터 튜닝 시작")
        print(f"   • Trials: {self.n_trials}")
        print(f"   • 평가 에피소드: {self.n_eval_episodes}")
        print(f"   • 결과 저장: {self.results_dir}")

        # 튜닝 실행
        self.study.optimize(self.objective, n_trials=self.n_trials)

        # 결과 분석 및 저장
        self.analyze_results()

        print(f"✅ 튜닝 완료! 최고 점수: {self.study.best_value:.2f}")
        print(f"🎯 최적 파라미터: {self.study.best_params}")

        return self.study.best_params

    def analyze_results(self):
        """튜닝 결과 분석 및 시각화"""
        print("\n📈 결과 분석 중...")

        # 1. 결과를 JSON으로 저장
        results_file = (
            self.results_dir
            / f"tuning_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        with open(results_file, "w") as f:
            json.dump(
                {
                    "best_params": self.study.best_params,
                    "best_value": self.study.best_value,
                    "n_trials": len(self.study.trials),
                    "trial_results": self.trial_results,
                },
                f,
                indent=2,
            )

        # 2. Optuna 기본 시각화
        self.create_optuna_plots()

        # 3. 커스텀 분석 플롯
        self.create_analysis_plots()

        print(f"📁 결과가 저장되었습니다: {results_file}")

    def create_optuna_plots(self):
        """Optuna 기본 시각화 생성"""
        try:
            # 최적화 히스토리
            fig = optuna.visualization.plot_optimization_history(self.study)
            fig.write_html(self.results_dir / "optimization_history.html")

            # 파라미터 중요도
            fig = optuna.visualization.plot_param_importances(self.study)
            fig.write_html(self.results_dir / "param_importances.html")

            # 파라미터 상관관계
            fig = optuna.visualization.plot_parallel_coordinate(self.study)
            fig.write_html(self.results_dir / "parallel_coordinates.html")

            print("📊 Optuna 시각화 완료 (HTML 파일)")

        except Exception as e:
            print(f"⚠️  Optuna 시각화 오류: {e}")

    def create_analysis_plots(self):
        """커스텀 분석 플롯 생성"""
        try:
            # 1. 점수 분포 히스토그램
            plt.figure(figsize=(12, 8))

            plt.subplot(2, 2, 1)
            scores = [result["avg_score"] for result in self.trial_results]
            plt.hist(scores, bins=20, alpha=0.7, edgecolor="black")
            plt.title("점수 분포")
            plt.xlabel("평균 점수")
            plt.ylabel("빈도")

            # 2. 학습률 vs 점수
            plt.subplot(2, 2, 2)
            lrs = [result["params"]["learning_rate"] for result in self.trial_results]
            plt.scatter(lrs, scores, alpha=0.6)
            plt.xscale("log")
            plt.title("학습률 vs 점수")
            plt.xlabel("학습률")
            plt.ylabel("평균 점수")

            # 3. 감마 vs 점수
            plt.subplot(2, 2, 3)
            gammas = [result["params"]["gamma"] for result in self.trial_results]
            plt.scatter(gammas, scores, alpha=0.6)
            plt.title("Gamma vs 점수")
            plt.xlabel("Gamma")
            plt.ylabel("평균 점수")

            # 4. Trial별 점수 변화
            plt.subplot(2, 2, 4)
            trial_nums = [result["trial"] for result in self.trial_results]
            plt.plot(trial_nums, scores, "o-", alpha=0.7)
            plt.title("Trial별 점수 변화")
            plt.xlabel("Trial 번호")
            plt.ylabel("평균 점수")

            plt.tight_layout()
            plt.savefig(
                self.results_dir / "analysis_plots.png", dpi=300, bbox_inches="tight"
            )
            plt.close()

            print("📊 분석 플롯 생성 완료")

        except Exception as e:
            print(f"⚠️  분석 플롯 오류: {e}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="PPO 하이퍼파라미터 튜닝")
    parser.add_argument("--trials", type=int, default=50, help="튜닝할 trial 수")
    parser.add_argument("--episodes", type=int, default=10, help="평가용 에피소드 수")
    parser.add_argument(
        "--max-steps", type=int, default=1000, help="에피소드당 최대 스텝"
    )
    parser.add_argument("--study-name", type=str, help="Study 이름")
    parser.add_argument(
        "--results-dir", type=str, default="tuning_results", help="결과 저장 디렉토리"
    )

    args = parser.parse_args()

    # 경고 메시지 억제 (클린한 출력을 위해)
    warnings.filterwarnings("ignore", category=UserWarning)

    # 튜너 초기화 및 실행
    tuner = HyperparameterTuner(
        n_trials=args.trials,
        n_eval_episodes=args.episodes,
        max_steps_per_episode=args.max_steps,
        study_name=args.study_name,
        results_dir=args.results_dir,
    )

    try:
        best_params = tuner.run_tuning()

        print("\n" + "=" * 60)
        print("🎉 튜닝 완료!")
        print("=" * 60)
        print(f"최적 파라미터:")
        for key, value in best_params.items():
            print(f"  {key}: {value}")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n⏹️  사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 튜닝 중 오류 발생: {e}")
        raise


if __name__ == "__main__":
    main()
