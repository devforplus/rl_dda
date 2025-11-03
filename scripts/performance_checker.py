#!/usr/bin/env python
"""
배속 모드 성능 체커

학습 환경(App)이 어느 정도의 배속까지 안정적으로 성능을 유지하는지 테스트합니다.
배속을 점진적으로 증가시키면서 각 단계의 평균 FPS를 측정하고,
목표 FPS 이하로 떨어지는 시점의 최대 배속을 확인합니다.

---

Performance checker for high-speed mode.

This script tests how much of a speed multiplier the training environment (App)
can handle while maintaining stable performance. It gradually increases the
speed multiplier, measures the average FPS at each step, and identifies the
maximum multiplier at which the FPS drops below a target threshold.
"""

import sys
import os
import time
import numpy as np
import argparse
import subprocess

# 프로젝트 루트의 'src' 디렉토리를 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, project_root)

try:
    import pyxel as px
    from main import App
    # from config.adaptive_config import get_config # 오케스트레이터에서는 직접 사용하지 않음
except ImportError as e:
    print(
        f"Error: {e}. Make sure you are in the correct environment and all dependencies are installed."
    )
    sys.exit(1)

# --- 설정 (Configuration) ---
TARGET_FPS = 60.0  # 목표 FPS (Target FPS)
MIN_ACCEPTABLE_FPS = 55.0  # 허용 가능한 최소 FPS (Minimum acceptable FPS)
TEST_DURATION_PER_STEP = (
    10  # 각 배속 단계별 테스트 시간(초) (Test duration per step in seconds)
)
SPEED_MULTIPLIERS = [
    1,
    2,
    4,
    6,
    8,
    10,
    12,
    14,
    16,
    20,
    24,
    30,
    40,
    50,
    60,
]  # 테스트할 배속 단계 (Speed multipliers to test)


class PerformanceCheckApp(App):
    """성능 측정을 위해 App 클래스를 확장"""

    def __init__(self, speed_multiplier: int):
        # App의 생성자를 먼저 호출
        super().__init__(speed_multiplier=speed_multiplier)

        # App 초기화가 성공적으로 완료된 후 속성 설정
        self.fps_records = []
        self.start_time = time.time()
        self.test_duration = TEST_DURATION_PER_STEP

        # FPS 계산용 변수
        self.frame_count_for_fps = 0
        self.last_fps_check_time = time.time()

        # 성능 테스트 중에는 플레이어가 죽지 않도록 무적 모드 활성화
        if (
            self.game
            and hasattr(self.game, "state")
            and hasattr(self.game.state, "player")
        ):
            self.game.state.player.invincible = True
            print("   - ✅ 플레이어 무적 모드 활성화됨")

    def update(self):
        super().update()

        # 테스트 종료 조건
        if time.time() - self.start_time > self.test_duration:
            px.quit()
            return

        # FPS 계산 로직
        self.frame_count_for_fps += 1
        current_time = time.time()
        elapsed = current_time - self.last_fps_check_time

        if elapsed >= 1.0:  # 1초마다 FPS 계산
            current_fps = self.frame_count_for_fps / elapsed
            self.fps_records.append(current_fps)
            self.frame_count_for_fps = 0
            self.last_fps_check_time = current_time

    def get_average_fps(self) -> float:
        """테스트 기간 동안의 평균 FPS를 반환"""
        if not self.fps_records:
            return 0.0
        return np.mean(self.fps_records)


def run_single_test(speed: int):
    """단일 배속에 대한 성능 테스트 실행"""
    app = PerformanceCheckApp(speed_multiplier=speed)
    app.run()
    avg_fps = app.get_average_fps()
    print(f"Average FPS: {avg_fps}")


def run_orchestrator():
    """모든 배속 단계에 대해 테스트를 조율하고 실행"""
    print("🚀 배속 모드 성능 테스트를 시작합니다.")
    print(f"   - 목표 FPS: {TARGET_FPS}")
    print(f"   - 허용 최소 FPS: {MIN_ACCEPTABLE_FPS}")
    print(f"   - 단계별 테스트 시간: {TEST_DURATION_PER_STEP}초")
    print("-" * 40)

    results = {}
    max_supported_speed = 0

    for speed in SPEED_MULTIPLIERS:
        print(f"⏱️  테스트 중... 배속: {speed}x")
        try:
            script_path = os.path.abspath(__file__)
            # 서브프로세스를 위한 환경 변수 설정
            sub_env = os.environ.copy()
            sub_env["PYTHONIOENCODING"] = "utf-8"

            process = subprocess.run(
                [sys.executable, script_path, "--speed", str(speed)],
                capture_output=True,
                text=True,
                check=True,
                timeout=TEST_DURATION_PER_STEP + 5,
                encoding="utf-8",
                errors="ignore",
                env=sub_env,  # 인코딩 설정이 적용된 환경 변수 전달
            )

            output = process.stdout
            avg_fps = 0.0
            for line in output.strip().split("\\n"):
                if "Average FPS:" in line:
                    avg_fps = float(line.split(":")[1].strip())
                    break

            results[speed] = avg_fps
            print(f"   - 평균 FPS: {avg_fps:.2f}")

            if avg_fps >= MIN_ACCEPTABLE_FPS:
                max_supported_speed = speed
            else:
                print(
                    f"   ⚠️  성능 저하 감지됨. 허용 FPS({MIN_ACCEPTABLE_FPS}) 이하입니다."
                )
                break
        except subprocess.TimeoutExpired:
            print(f"   ❌ 오류: {speed}x 배속 테스트 시간 초과.")
            break
        except subprocess.CalledProcessError as e:
            print(f"   ❌ 오류: {speed}x 배속 테스트 중단. 원인:\n{e.stderr}")
            break
        except Exception as e:
            print(f"   ❌ 오케스트레이터 오류 발생: {e}")
            break

    print("-" * 40)
    print("📊 테스트 결과 요약")
    for speed, fps in results.items():
        print(f"   - {speed:2d}x 배속: {fps:.2f} FPS")
    print("-" * 40)
    if max_supported_speed > 0:
        print(
            f"✅ 최대 지원 가능 배속: {max_supported_speed}x (허용 FPS: {MIN_ACCEPTABLE_FPS} 이상)"
        )
    else:
        print("❌ 1배속에서도 성능 목표를 달성하지 못했습니다. 환경을 확인해주세요.")
    print("-" * 40)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="배속 모드 성능 체커")
    parser.add_argument("--speed", type=int, help="단일 배속 테스트를 위한 배속 값")
    args = parser.parse_args()

    if args.speed:
        run_single_test(args.speed)
    else:
        run_orchestrator()
