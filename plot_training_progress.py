#!/usr/bin/env python
"""
훈련 진행도 그래프 생성 유틸리티

PPO 에이전트의 훈련 로그를 분석하여 정적 그래프를 생성합니다.
에피소드 종료 시점이나 필요할 때 호출하여 현재까지의 학습 진행도를 시각화합니다.

---

Training progress visualization utility for PPO agent
"""

import os
import glob
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.style as style
import numpy as np
from datetime import datetime
import argparse


class TrainingPlotter:
    """훈련 진행도 그래프 생성 클래스

    ---

    CSV 로그 파일을 읽어서 훈련 진행도를 시각화하는 정적 그래프 생성
    """

    def __init__(
        self,
        log_dir="logs",
        output_dir="plots",
        random_log_file=None,
        episode_log_file=None,
    ):
        """플로터 초기화

        Args:
            log_dir: 로그 파일 디렉토리
            output_dir: 그래프 출력 디렉토리
            random_log_file: 랜덤 에이전트 로그 파일 경로
            episode_log_file: 특정 에피소드 로그 파일 경로
        """
        self.log_dir = log_dir
        self.output_dir = output_dir
        self.random_log_file = random_log_file
        self.episode_log_file = episode_log_file

        # 출력 디렉토리 생성
        os.makedirs(output_dir, exist_ok=True)

        # 데이터 저장용
        self.episode_data = pd.DataFrame()
        self.training_data = pd.DataFrame()
        self.random_data = pd.DataFrame()

        # 로그 파일 경로
        self.training_log_file = None

        # 그래프 스타일 설정
        plt.style.use("default")
        plt.rcParams["figure.facecolor"] = "white"
        plt.rcParams["axes.facecolor"] = "white"

    def find_latest_logs(self):
        """가장 최신 로그 파일 찾기"""
        if self.episode_log_file and os.path.exists(self.episode_log_file):
            print(f"📊 Using specified episode log: {self.episode_log_file}")
            # training log는 여전히 찾아야 함
        elif self.episode_log_file:
            print(f"❌ Specified episode log not found: {self.episode_log_file}")
            return False
        else:
            # 지정된 파일이 없으면 최신 파일 찾기
            if not os.path.exists(self.log_dir):
                print(f"❌ Log directory not found: {self.log_dir}")
                return False

            episode_files = glob.glob(os.path.join(self.log_dir, "episodes_*.csv"))
            if episode_files:
                self.episode_log_file = max(episode_files, key=os.path.getctime)
                print(f"📊 Found latest episode log: {self.episode_log_file}")

        # 훈련 메트릭 로그 파일 찾기 (항상 최신)
        training_files = glob.glob(os.path.join(self.log_dir, "training_metrics_*.csv"))
        if training_files:
            self.training_log_file = max(training_files, key=os.path.getctime)
            print(f"📈 Found latest training log: {self.training_log_file}")

        if not self.episode_log_file:
            print(f"⚠️ No episode log file found or specified.")
            return False

        return True

    def load_data(self):
        """로그 파일에서 데이터 로드"""
        try:
            # 에피소드 데이터 로드
            if self.episode_log_file and os.path.exists(self.episode_log_file):
                # 데이터가 비어있는 경우를 대비해 예외 처리 추가
                try:
                    self.episode_data = pd.read_csv(self.episode_log_file)
                    if "timestamp" in self.episode_data.columns:
                        self.episode_data["timestamp"] = pd.to_datetime(
                            self.episode_data["timestamp"]
                        )
                    if self.episode_data.empty:
                        print(
                            f"⚠️ Warning: Episode log is empty: {self.episode_log_file}"
                        )
                    else:
                        print(
                            f"  Loaded {len(self.episode_data)} records from {self.episode_log_file}"
                        )
                except pd.errors.EmptyDataError:
                    print(
                        f"⚠️ Warning: Episode log is empty (pandas EmptyDataError): {self.episode_log_file}"
                    )
                    self.episode_data = pd.DataFrame()

            # 훈련 메트릭 데이터 로드
            if self.training_log_file and os.path.exists(self.training_log_file):
                self.training_data = pd.read_csv(self.training_log_file)
                if "timestamp" in self.training_data.columns:
                    self.training_data["timestamp"] = pd.to_datetime(
                        self.training_data["timestamp"]
                    )

            # 랜덤 에이전트 데이터 로드
            if self.random_log_file and os.path.exists(self.random_log_file):
                self.random_data = pd.read_csv(self.random_log_file)
                print(f"📊 Found random agent log: {self.random_log_file}")

            return True

        except Exception as e:
            print(f"⚠️ Error loading data: {e}")
            return False

    def generate_episode_plots(self):
        """에피소드 관련 그래프 생성"""
        if self.episode_data.empty:
            return

        df = self.episode_data

        # 데이터 범위 디버그 정보 출력
        print(f"📊 Episode Data Debug Info:")
        print(f"   Episodes: {len(df)}")
        if "total_reward" in df.columns:
            reward_min, reward_max = df["total_reward"].min(), df["total_reward"].max()
            reward_mean, reward_std = (
                df["total_reward"].mean(),
                df["total_reward"].std(),
            )
            print(f"   Reward Range: [{reward_min:.6f}, {reward_max:.6f}]")
            print(f"   Reward Mean±Std: {reward_mean:.6f}±{reward_std:.6f}")

            # 매우 작은 보상값들 확인
            if abs(reward_max - reward_min) < 0.001:
                print(f"   ⚠️ Warning: Very small reward range detected!")

        # 에피소드 그래프 (2x2 레이아웃)
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(
            f"Episode Progress - {len(df)} Episodes Completed",
            fontsize=16,
            fontweight="bold",
        )

        # 랜덤 에이전트 평균값 계산
        random_avg = {}
        if not self.random_data.empty:
            random_avg["reward"] = self.random_data["total_reward"].mean()
            random_avg["score"] = self.random_data["final_score"].mean()
            random_avg["duration"] = self.random_data["duration_sec"].mean()
            if (
                "total_reward" in self.random_data.columns
                and "duration_sec" in self.random_data.columns
            ):
                random_avg["efficiency"] = (
                    self.random_data["total_reward"]
                    / (self.random_data["duration_sec"] + 1e-8)
                ).mean()

        # 1. 에피소드 보상
        ax = axes[0, 0]
        ax.plot(
            df["episode"],
            df["total_reward"],
            "b-",
            linewidth=2,
            alpha=0.7,
            label="Total Reward",
        )

        # 이동평균 추가
        if len(df) >= 5:
            window = min(10, len(df) // 2)
            ma_reward = df["total_reward"].rolling(window=window).mean()
            ax.plot(
                df["episode"],
                ma_reward,
                "r-",
                linewidth=3,
                label=f"Moving Avg ({window})",
            )

            if "reward" in random_avg:
                ax.axhline(
                    y=random_avg["reward"],
                    color="grey",
                    linestyle="--",
                    linewidth=2,
                    label=f"Random Avg ({random_avg['reward']:.2f})",
                )

            ax.legend()

        latest_reward = df["total_reward"].iloc[-1] if len(df) > 0 else 0
        ax.set_title(
            f"Episode Rewards (Latest: {latest_reward:.6f})"
        )  # 소수점 6자리로 표시
        ax.set_xlabel("Episode")
        ax.set_ylabel("Total Reward")
        ax.grid(True, alpha=0.3)

        # Y축 범위 조정 (매우 작은 값들을 더 잘 보이게)
        if "total_reward" in df.columns and len(df) > 0:
            y_min, y_max = df["total_reward"].min(), df["total_reward"].max()
            y_range = abs(y_max - y_min)
            if y_range > 0:
                padding = y_range * 0.1
                ax.set_ylim(y_min - padding, y_max + padding)

        # 2. 게임 스코어
        ax = axes[0, 1]
        ax.plot(
            df["episode"],
            df["final_score"],
            "g-",
            linewidth=2,
            alpha=0.8,
            label="Final Score",
        )
        if "max_score" in df.columns:
            ax.plot(
                df["episode"],
                df["max_score"],
                "orange",
                linewidth=2,
                alpha=0.8,
                label="Max Score",
            )
        latest_score = df["final_score"].iloc[-1] if len(df) > 0 else 0
        ax.set_title(f"Game Scores (Latest: {latest_score:,})")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Score")

        if "score" in random_avg:
            ax.axhline(
                y=random_avg["score"],
                color="grey",
                linestyle="--",
                linewidth=2,
                label=f"Random Avg ({random_avg['score']:.0f})",
            )

        ax.legend()
        ax.grid(True, alpha=0.3)

        # 3. 에피소드 지속시간
        ax = axes[1, 0]
        ax.plot(df["episode"], df["duration_sec"], "m-", linewidth=2, alpha=0.8)

        # 지속시간 이동평균도 표시
        if len(df) >= 5:
            window = min(10, len(df) // 2)
            ma_duration = df["duration_sec"].rolling(window=window).mean()
            ax.plot(
                df["episode"],
                ma_duration,
                "purple",
                linewidth=3,
                alpha=0.9,
                label=f"Moving Avg ({window})",
            )

            if "duration" in random_avg:
                ax.axhline(
                    y=random_avg["duration"],
                    color="grey",
                    linestyle="--",
                    linewidth=2,
                    label=f"Random Avg ({random_avg['duration']:.1f}s)",
                )

            ax.legend()

        latest_duration = df["duration_sec"].iloc[-1] if len(df) > 0 else 0
        ax.set_title(f"Episode Duration (Latest: {latest_duration:.1f}s)")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Duration (seconds)")
        ax.grid(True, alpha=0.3)

        # 4. 보상 효율성 (보상/시간)
        ax = axes[1, 1]
        if len(df) > 0 and "duration_sec" in df.columns:
            reward_efficiency = df["total_reward"] / (
                df["duration_sec"] + 1e-8
            )  # 0으로 나누기 방지
            ax.plot(df["episode"], reward_efficiency, "cyan", linewidth=2, alpha=0.8)

            if len(df) >= 5:
                window = min(10, len(df) // 2)
                ma_efficiency = reward_efficiency.rolling(window=window).mean()
                ax.plot(
                    df["episode"],
                    ma_efficiency,
                    "darkblue",
                    linewidth=3,
                    alpha=0.9,
                    label=f"Moving Avg ({window})",
                )
                ax.legend()

            latest_efficiency = (
                reward_efficiency.iloc[-1] if len(reward_efficiency) > 0 else 0
            )
            ax.set_title(f"Reward Efficiency (Latest: {latest_efficiency:.6f})")
        else:
            ax.set_title("Reward Efficiency (No Data)")

        ax.set_xlabel("Episode")
        ax.set_ylabel("Reward/Second")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"episode_progress_{timestamp}.png")
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f"📊 Episode progress saved: {filename}")

        # 최신 파일로도 저장 (덮어쓰기)
        latest_filename = os.path.join(self.output_dir, "latest_episode_progress.png")
        plt.savefig(latest_filename, dpi=300, bbox_inches="tight")

        plt.close()

    def generate_training_plots(self):
        """훈련 메트릭 그래프 생성"""
        if self.training_data.empty:
            return

        df = self.training_data

        # 훈련 메트릭 그래프 (2x2 레이아웃)
        fig, axes = plt.subplots(2, 2, figsize=(12, 10))
        fig.suptitle(
            f"Training Metrics - {len(df)} Training Steps",
            fontsize=16,
            fontweight="bold",
        )

        # 1. 훈련 손실
        ax = axes[0, 0]
        if "total_loss" in df.columns:
            ax.plot(
                df["step"],
                df["total_loss"],
                "r-",
                linewidth=2,
                alpha=0.8,
                label="Total Loss",
            )
        if "policy_loss" in df.columns:
            ax.plot(
                df["step"],
                df["policy_loss"],
                "b-",
                linewidth=1.5,
                alpha=0.7,
                label="Policy Loss",
            )
        if "value_loss" in df.columns:
            ax.plot(
                df["step"],
                df["value_loss"],
                "g-",
                linewidth=1.5,
                alpha=0.7,
                label="Value Loss",
            )

        latest_loss = df["total_loss"].iloc[-1] if "total_loss" in df.columns else 0
        ax.set_title(f"Training Loss (Latest: {latest_loss:.6f})")
        ax.set_xlabel("Training Step")
        ax.set_ylabel("Loss")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 2. 현재 보상 트렌드
        ax = axes[0, 1]
        if "current_reward" in df.columns:
            ax.plot(df["step"], df["current_reward"], "purple", linewidth=2, alpha=0.8)

            # 보상 이동평균
            if len(df) >= 10:
                window = min(50, len(df) // 4)
                ma_reward = df["current_reward"].rolling(window=window).mean()
                ax.plot(
                    df["step"],
                    ma_reward,
                    "darkred",
                    linewidth=3,
                    alpha=0.9,
                    label=f"Moving Avg ({window})",
                )
                ax.legend()

            latest_reward = df["current_reward"].iloc[-1]
            ax.set_title(f"Current Reward Trend (Latest: {latest_reward:.2f})")
        ax.set_xlabel("Training Step")
        ax.set_ylabel("Current Reward")
        ax.grid(True, alpha=0.3)

        # 3. 성능 (Steps/sec)
        ax = axes[1, 0]
        if "steps_per_sec" in df.columns:
            ax.plot(df["step"], df["steps_per_sec"], "orange", linewidth=2, alpha=0.8)
            latest_fps = df["steps_per_sec"].iloc[-1]
            ax.set_title(f"Training Performance (Latest: {latest_fps:.1f} steps/sec)")
        ax.set_xlabel("Training Step")
        ax.set_ylabel("Steps/sec")
        ax.grid(True, alpha=0.3)

        # 4. 에피소드 진행도
        ax = axes[1, 1]
        if "episode" in df.columns:
            ax.plot(df["step"], df["episode"], "teal", linewidth=2, alpha=0.8)
            latest_episode = df["episode"].iloc[-1]
            ax.set_title(f"Episode Progress (Latest: {latest_episode})")
        ax.set_xlabel("Training Step")
        ax.set_ylabel("Episode Number")
        ax.grid(True, alpha=0.3)

        plt.tight_layout()

        # 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"training_metrics_{timestamp}.png")
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f"📈 Training metrics saved: {filename}")

        # 최신 파일로도 저장
        latest_filename = os.path.join(self.output_dir, "latest_training_metrics.png")
        plt.savefig(latest_filename, dpi=300, bbox_inches="tight")

        plt.close()

    def generate_reward_trend_plot(self):
        """에피소드 보상 추세 그래프 생성"""
        if self.episode_data.empty:
            return

        df = self.episode_data

        fig, ax = plt.subplots(1, 1, figsize=(8, 6))

        # 랜덤 에이전트 평균값 계산
        random_avg = {}
        if not self.random_data.empty:
            random_avg["reward"] = self.random_data["total_reward"].mean()

        # 보상 추세
        ax.plot(df["episode"], df["total_reward"], "b-", linewidth=2, alpha=0.6)

        if len(df) >= 5:
            window = min(10, len(df) // 2)
            ma_reward = df["total_reward"].rolling(window=window).mean()
            ax.plot(
                df["episode"],
                ma_reward,
                "r-",
                linewidth=3,
                label=f"Trend (MA {window})",
            )

            if "reward" in random_avg:
                ax.axhline(
                    y=random_avg["reward"],
                    color="grey",
                    linestyle="--",
                    linewidth=2,
                    label=f"Random Avg ({random_avg['reward']:.2f})",
                )
            ax.legend()

        ax.set_title(f"Learning Progress - {len(df)} Episodes")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Total Reward")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        # 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"reward_trend_{timestamp}.png")
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f"📋 Reward trend plot saved: {filename}")

        latest_filename = os.path.join(self.output_dir, "latest_reward_trend.png")
        plt.savefig(latest_filename, dpi=300, bbox_inches="tight")

        plt.close()

    def generate_performance_plot(self):
        """게임 성과(점수) 그래프 생성"""
        if self.episode_data.empty:
            return

        df = self.episode_data
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))

        # 랜덤 에이전트 평균값 계산
        random_avg = {}
        if not self.random_data.empty:
            random_avg["score"] = self.random_data["final_score"].mean()

        # 게임 성과
        ax.plot(
            df["episode"],
            df["final_score"],
            "g-",
            linewidth=2,
            alpha=0.8,
            label="Final Score",
        )

        if len(df) >= 5:
            window = min(10, len(df) // 2)
            ma_score = df["final_score"].rolling(window=window).mean()
            ax.plot(
                df["episode"],
                ma_score,
                "orange",
                linewidth=3,
                label=f"Trend (MA {window})",
            )

            if "score" in random_avg:
                ax.axhline(
                    y=random_avg["score"],
                    color="grey",
                    linestyle="--",
                    linewidth=2,
                    label=f"Random Avg ({random_avg['score']:.0f})",
                )

            ax.legend()

        ax.set_title(f"Game Performance - {len(df)} Episodes")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Score")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        # 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"performance_{timestamp}.png")
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f"📋 Performance plot saved: {filename}")

        latest_filename = os.path.join(self.output_dir, "latest_performance.png")
        plt.savefig(latest_filename, dpi=300, bbox_inches="tight")

        plt.close()

    def generate_survival_time_plot(self):
        """생존 시간 그래프 생성"""
        if self.episode_data.empty:
            return

        df = self.episode_data
        fig, ax = plt.subplots(1, 1, figsize=(8, 6))

        # 랜덤 에이전트 평균값 계산
        random_avg = {}
        if not self.random_data.empty:
            random_avg["duration"] = self.random_data["duration_sec"].mean()

        # 생존 시간
        ax.plot(df["episode"], df["duration_sec"], "m-", linewidth=2, alpha=0.8)

        if len(df) >= 5:
            window = min(10, len(df) // 2)
            ma_duration = df["duration_sec"].rolling(window=window).mean()
            ax.plot(
                df["episode"],
                ma_duration,
                "purple",
                linewidth=3,
                label=f"Trend (MA {window})",
            )

            if "duration" in random_avg:
                ax.axhline(
                    y=random_avg["duration"],
                    color="grey",
                    linestyle="--",
                    linewidth=2,
                    label=f"Random Avg ({random_avg['duration']:.1f}s)",
                )

            ax.legend()

        ax.set_title(f"Survival Time - {len(df)} Episodes")
        ax.set_xlabel("Episode")
        ax.set_ylabel("Duration (sec)")
        ax.grid(True, alpha=0.3)
        plt.tight_layout()

        # 파일 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(self.output_dir, f"survival_time_{timestamp}.png")
        plt.savefig(filename, dpi=300, bbox_inches="tight")
        print(f"📋 Survival time plot saved: {filename}")

        latest_filename = os.path.join(self.output_dir, "latest_survival_time.png")
        plt.savefig(latest_filename, dpi=300, bbox_inches="tight")

        plt.close()

    def generate_summary_plot(self):
        """요약 그래프들을 각각 생성"""
        print("📊 Generating summary plots...")
        self.generate_reward_trend_plot()
        self.generate_performance_plot()
        self.generate_survival_time_plot()
        print("✅ Summary plots generated.")

    def generate_all_plots(self):
        """모든 그래프 생성"""
        print(f"📊 Generating training plots from {self.log_dir}")

        if not self.find_latest_logs():
            return False

        if not self.load_data():
            return False

        # 각종 그래프 생성
        self.generate_episode_plots()
        self.generate_training_plots()
        self.generate_summary_plot()

        print(f"✅ All plots saved to {self.output_dir}")
        return True


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="Generate training progress plots")
    parser.add_argument("--log-dir", default="logs", help="Log directory path")
    parser.add_argument(
        "--output-dir", default="plots", help="Output directory for plots"
    )
    parser.add_argument(
        "--episode-only", action="store_true", help="Generate only episode plots"
    )
    parser.add_argument(
        "--training-only", action="store_true", help="Generate only training plots"
    )
    parser.add_argument(
        "--summary-only", action="store_true", help="Generate only summary plot"
    )
    parser.add_argument(
        "--random-log",
        type=str,
        default="logs/random_episodes.csv",
        help="Path to random agent's episode log file",
    )
    parser.add_argument(
        "--episode-log-file",
        type=str,
        default=None,
        help="Path to a specific episode log file to plot.",
    )

    args = parser.parse_args()

    print("🚀 Training Plot Generator Starting...")
    print(f"📁 Log directory: {args.log_dir}")
    print(f"📊 Output directory: {args.output_dir}")
    if os.path.exists(args.random_log):
        print(f"🎲 Comparing with random agent log: {args.random_log}")

    plotter = TrainingPlotter(
        log_dir=args.log_dir,
        output_dir=args.output_dir,
        random_log_file=args.random_log,
        episode_log_file=args.episode_log_file,
    )

    if not plotter.find_latest_logs():
        return

    if not plotter.load_data():
        return

    # 선택적 그래프 생성
    if args.episode_only:
        plotter.generate_episode_plots()
    elif args.training_only:
        plotter.generate_training_plots()
    elif args.summary_only:
        plotter.generate_summary_plot()
    else:
        # self.generate_all_plots() # generate_all_plots() 대신 아래처럼 개별적으로 호출해야
        # 스크립트 실행 인수가 적용됩니다.
        if not any([args.episode_only, args.training_only, args.summary_only]):
            plotter.generate_all_plots()
        else:
            if args.episode_only:
                plotter.generate_episode_plots()
            if args.training_only:
                plotter.generate_training_plots()
            if args.summary_only:
                plotter.generate_summary_plot()

    print("✅ Plot generation complete.")


if __name__ == "__main__":
    main()
