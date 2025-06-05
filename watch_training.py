#!/usr/bin/env python
"""
훈련 진행도 모니터링 스크립트

백그라운드에서 실행 중인 PPO 훈련의 진행 상황을 실시간으로 모니터링합니다.
로그 파일을 주기적으로 확인하여 최신 진행 상황을 표시합니다.

---

Training progress monitoring script for background PPO training
"""

import os
import glob
import time
import pandas as pd
from datetime import datetime
import argparse


class TrainingWatcher:
    """훈련 진행도 감시 클래스

    ---

    백그라운드 훈련 진행상황을 주기적으로 확인하고 표시
    """

    def __init__(self, log_dir="logs", watch_interval=5):
        """감시자 초기화

        Args:
            log_dir: 로그 파일 디렉토리
            watch_interval: 확인 간격 (초)
        """
        self.log_dir = log_dir
        self.watch_interval = watch_interval
        self.episode_log_file = None
        self.training_log_file = None
        self.last_episode = 0
        self.last_step = 0

    def find_latest_logs(self):
        """최신 로그 파일 찾기"""
        if not os.path.exists(self.log_dir):
            return False

        # 에피소드 로그 파일 찾기
        episode_files = glob.glob(os.path.join(self.log_dir, "episodes_*.csv"))
        if episode_files:
            self.episode_log_file = max(episode_files, key=os.path.getctime)

        # 훈련 메트릭 로그 파일 찾기
        training_files = glob.glob(os.path.join(self.log_dir, "training_metrics_*.csv"))
        if training_files:
            self.training_log_file = max(training_files, key=os.path.getctime)

        return self.episode_log_file or self.training_log_file

    def get_latest_episode_info(self):
        """최신 에피소드 정보 가져오기"""
        if not self.episode_log_file or not os.path.exists(self.episode_log_file):
            return None

        try:
            df = pd.read_csv(self.episode_log_file)
            if len(df) == 0:
                return None

            latest = df.iloc[-1]
            return {
                "episode": int(latest["episode"]),
                "duration": float(latest["duration_sec"]),
                "total_reward": float(latest["total_reward"]),
                "final_score": int(latest["final_score"]),
                "final_stage": int(latest["final_stage"]),
                "end_reason": str(latest["end_reason"]),
                "timestamp": latest["timestamp"],
            }
        except Exception as e:
            return None

    def get_latest_training_info(self):
        """최신 훈련 정보 가져오기"""
        if not self.training_log_file or not os.path.exists(self.training_log_file):
            return None

        try:
            df = pd.read_csv(self.training_log_file)
            if len(df) == 0:
                return None

            latest = df.iloc[-1]
            return {
                "step": int(latest["step"]),
                "episode": int(latest["episode"]),
                "total_loss": float(latest["total_loss"]),
                "current_reward": float(latest["current_reward"]),
                "steps_per_sec": float(latest["steps_per_sec"]),
                "timestamp": latest["timestamp"],
            }
        except Exception as e:
            return None

    def print_status(self):
        """현재 상태 출력"""
        # 화면 클리어 (Windows 호환)
        os.system("cls" if os.name == "nt" else "clear")

        print("=" * 60)
        print("🚀 PPO Training Monitor - Background Training Watcher")
        print("=" * 60)
        print(f"⏰ Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📁 Log Directory: {self.log_dir}")
        print()

        # 에피소드 정보
        episode_info = self.get_latest_episode_info()
        if episode_info:
            print("📊 Latest Episode:")
            print(f"   Episode: {episode_info['episode']}")
            print(f"   Duration: {episode_info['duration']:.1f}s")
            print(f"   Total Reward: {episode_info['total_reward']:.2f}")
            print(f"   Final Score: {episode_info['final_score']:,}")
            print(f"   Final Stage: {episode_info['final_stage']}")
            print(f"   End Reason: {episode_info['end_reason']}")

            # 새 에피소드 감지
            if episode_info["episode"] > self.last_episode:
                self.last_episode = episode_info["episode"]
                print("   🆕 NEW EPISODE!")
        else:
            print("📊 Episode Data: Not available")

        print()

        # 훈련 정보
        training_info = self.get_latest_training_info()
        if training_info:
            print("🧠 Latest Training:")
            print(f"   Training Step: {training_info['step']:,}")
            print(f"   Episode: {training_info['episode']}")
            print(f"   Total Loss: {training_info['total_loss']:.6f}")
            print(f"   Current Reward: {training_info['current_reward']:.2f}")
            print(f"   Performance: {training_info['steps_per_sec']:.1f} steps/sec")

            # 새 훈련 스텝 감지
            if training_info["step"] > self.last_step:
                steps_diff = training_info["step"] - self.last_step
                self.last_step = training_info["step"]
                print(f"   📈 Progress: +{steps_diff} steps")
        else:
            print("🧠 Training Data: Not available")

        print()

        # 그래프 파일 확인
        plots_dir = "plots"
        if os.path.exists(plots_dir):
            latest_plots = []
            for pattern in ["latest_*.png"]:
                files = glob.glob(os.path.join(plots_dir, pattern))
                latest_plots.extend(files)

            if latest_plots:
                print("📊 Available Plots:")
                for plot_file in latest_plots:
                    filename = os.path.basename(plot_file)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(plot_file))
                    print(f"   📈 {filename} ({mod_time.strftime('%H:%M:%S')})")
            else:
                print("📊 Plots: Not generated yet")
        else:
            print("📊 Plots: Directory not found")

        print()
        print(f"🔄 Next update in {self.watch_interval} seconds... (Ctrl+C to stop)")
        print("=" * 60)

    def start_watching(self):
        """감시 시작"""
        print("🎯 Starting training watcher...")

        if not self.find_latest_logs():
            print(f"❌ No log files found in {self.log_dir}")
            print("   Make sure training is running with --learn flag")
            return

        print(f"📊 Watching logs: {self.episode_log_file}")
        print(f"📈 Watching metrics: {self.training_log_file}")
        print(f"⏱️ Update interval: {self.watch_interval}s\n")

        try:
            while True:
                self.print_status()
                time.sleep(self.watch_interval)

        except KeyboardInterrupt:
            print("\n\n⏹️ Training watcher stopped by user")
        except Exception as e:
            print(f"\n\n❌ Error: {e}")


def main():
    """메인 실행 함수"""
    parser = argparse.ArgumentParser(description="Watch PPO training progress")
    parser.add_argument("--log-dir", default="logs", help="Log directory path")
    parser.add_argument(
        "--interval", type=int, default=5, help="Update interval in seconds"
    )

    args = parser.parse_args()

    watcher = TrainingWatcher(log_dir=args.log_dir, watch_interval=args.interval)
    watcher.start_watching()


if __name__ == "__main__":
    main()
