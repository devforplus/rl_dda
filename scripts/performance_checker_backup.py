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
    3  # 각 배속 단계별 테스트 시간(초) (Test duration per step in seconds)
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
        self.speed_multiplier = speed_multiplier
        self.fps_records = []
        self.start_time = time.time()
        self.test_duration = TEST_DURATION_PER_STEP

        # FPS 계산용 변수
        self.frame_count_for_fps = 0
        self.last_fps_check_time = time.time()
        self.last_debug_time = time.time()
        self.total_frames = 0

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

        # FPS 계산 로직
        self.frame_count_for_fps += 1
        self.total_frames += 1
        current_time = time.time()
        elapsed = current_time - self.last_fps_check_time

        # 0.5초마다 FPS 계산 (더 정확한 측정)
        if elapsed >= 0.5 and current_time - self.start_time > 1.0:  # 첫 1초는 무시
            current_fps = self.frame_count_for_fps / elapsed
            self.fps_records.append(current_fps)
            self.frame_count_for_fps = 0
            self.last_fps_check_time = current_time

        # 테스트 종료 조건
        if time.time() - self.start_time > self.test_duration:
            # 마지막 FPS도 기록
            if self.frame_count_for_fps > 0 and elapsed > 0:
                final_fps = self.frame_count_for_fps / elapsed
                self.fps_records.append(final_fps)

            avg_fps = self.get_average_fps()
            print(
                f"   Completed: {len(self.fps_records)} FPS records, Average: {avg_fps:.2f}"
            )
            px.quit()
            return

    def get_average_fps(self) -> float:
        """테스트 기간 동안의 평균 FPS를 반환"""
        if not self.fps_records:
            return 0.0
        return np.mean(self.fps_records)


def run_single_test(speed: int):
    """단일 배속에 대한 성능 테스트 실행"""
    app = PerformanceCheckApp(speed_multiplier=speed)
    print(f"   Testing {speed}x speed for {TEST_DURATION_PER_STEP} seconds...")
    app.run()
    return app.get_average_fps()


def run_direct_test():
    """직접 반복 테스트 방식 (서브프로세스 없음)"""
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
            avg_fps = run_single_test(speed)
            results[speed] = avg_fps
            print(f"   - 평균 FPS: {avg_fps:.2f}")

            if avg_fps >= MIN_ACCEPTABLE_FPS:
                max_supported_speed = speed
            else:
                print(
                    f"   ⚠️  성능 저하 감지됨. 허용 FPS({MIN_ACCEPTABLE_FPS}) 이하입니다."
                )
                break

        except Exception as e:
            print(f"   ❌ 오류: {speed}x 배속 테스트 중 예외 발생: {e}")
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
        run_direct_test()
