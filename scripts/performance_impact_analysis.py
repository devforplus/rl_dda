#!/usr/bin/env python
"""
이미지 캡처 유무에 따른 성능 영향 분석

현재 불필요한 이미지 캡처가 성능에 미치는 영향을 측정합니다.
"""

import sys
import os
import time
import psutil
from typing import Dict, Any

# 프로젝트 루트의 'src' 디렉토리를 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, project_root)

try:
    import pyxel as px
    from main import App
except ImportError as e:
    print(f"Error: {e}. Make sure you are in the correct environment.")
    sys.exit(1)


class PerformanceTestApp(App):
    """성능 테스트용 App 클래스"""

    def __init__(self, enable_capture: bool, test_duration: int = 10):
        super().__init__(speed_multiplier=32)  # 32배속으로 테스트

        self.enable_capture = enable_capture
        self.test_duration = test_duration
        self.start_time = time.time()

        # 성능 측정 변수
        self.frame_count = 0
        self.capture_count = 0
        self.capture_time_total = 0
        self.memory_samples = []

        # 메모리 모니터링
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        # 플레이어 무적 모드
        if (
            self.game
            and hasattr(self.game, "state")
            and hasattr(self.game.state, "player")
        ):
            self.game.state.player.invincible = True

        print(f"🧪 성능 테스트 시작 - 이미지 캡처: {'ON' if enable_capture else 'OFF'}")
        print(f"   - 테스트 시간: {test_duration}초")
        print(f"   - 배속: 32x")
        print(f"   - 초기 메모리: {self.initial_memory:.1f} MB")

    def update(self):
        super().update()

        self.frame_count += 1

        # 0.5초마다 메모리 샘플링
        current_time = time.time()
        if (
            len(self.memory_samples) == 0
            or current_time - self.start_time > len(self.memory_samples) * 0.5
        ):
            current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            self.memory_samples.append(current_memory)

        # 이미지 캡처 시뮬레이션 (enable_capture가 True일 때만)
        if self.enable_capture:
            capture_start = time.perf_counter()
            self._simulate_capture()
            capture_time = (time.perf_counter() - capture_start) * 1000  # ms
            self.capture_time_total += capture_time
            self.capture_count += 1

        # 테스트 종료
        if current_time - self.start_time > self.test_duration:
            self._show_results()
            px.quit()

    def _simulate_capture(self):
        """이미지 캡처 시뮬레이션 (실제 캡처 호출)"""
        try:
            frame_data = self._collect_current_frame_data()
            # 실제로는 이 데이터를 사용하지 않음
        except Exception:
            pass

    def _show_results(self):
        """성능 테스트 결과 출력"""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - self.initial_memory
        max_memory = max(self.memory_samples) if self.memory_samples else current_memory

        elapsed_time = time.time() - self.start_time
        avg_fps = self.frame_count / elapsed_time

        capture_mode = "이미지 캡처 ON" if self.enable_capture else "이미지 캡처 OFF"

        print(f"\n📊 성능 테스트 결과 - {capture_mode}")
        print("=" * 50)
        print(f"⏱️  프레임 성능:")
        print(f"   - 총 프레임: {self.frame_count:,}")
        print(f"   - 평균 FPS: {avg_fps:.1f}")
        print(f"   - 테스트 시간: {elapsed_time:.1f}초")

        if self.enable_capture:
            avg_capture_time = (
                self.capture_time_total / self.capture_count
                if self.capture_count > 0
                else 0
            )
            print(f"📸 캡처 성능:")
            print(f"   - 총 캡처 시도: {self.capture_count:,}")
            print(f"   - 평균 캡처 시간: {avg_capture_time:.2f} ms")
            print(f"   - 총 캡처 시간: {self.capture_time_total:.1f} ms")

        print(f"💾 메모리 사용:")
        print(f"   - 초기 메모리: {self.initial_memory:.1f} MB")
        print(f"   - 최종 메모리: {current_memory:.1f} MB")
        print(f"   - 메모리 증가: {memory_increase:.1f} MB")
        print(f"   - 최대 메모리: {max_memory:.1f} MB")


def run_comparison_test():
    """이미지 캡처 ON/OFF 비교 테스트"""
    print("🚀 이미지 캡처 성능 영향 분석 시작")
    print("=" * 50)

    test_duration = 8  # 각 테스트별 8초
    results = {}

    # 1. 이미지 캡처 OFF 테스트
    print("\n🟢 1단계: 이미지 캡처 비활성화 테스트")
    app_off = PerformanceTestApp(enable_capture=False, test_duration=test_duration)
    app_off.run()

    print("\n" + "=" * 30)
    print("잠시 대기 중... (메모리 정리)")
    time.sleep(2)

    # 2. 이미지 캡처 ON 테스트
    print("\n🔴 2단계: 이미지 캡처 활성화 테스트")
    app_on = PerformanceTestApp(enable_capture=True, test_duration=test_duration)
    app_on.run()

    print("\n" + "=" * 50)
    print("📋 **종합 비교 분석**")
    print("=" * 50)
    print("💡 결론:")
    print("   현재 PPO 에이전트는 이미지 데이터를 사용하지 않으므로,")
    print("   이미지 캡처는 순수한 성능 오버헤드입니다.")
    print("\n💰 권장사항:")
    print("   ✅ 학습 모드에서 이미지 캡처 비활성화")
    print("   ✅ 디버그/분석 목적으로만 선택적 활성화")
    print("   ✅ 메모리 사용량 최소화로 더 긴 학습 가능")


if __name__ == "__main__":
    run_comparison_test()
