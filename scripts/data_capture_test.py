#!/usr/bin/env python
"""
데이터 캡처 및 전송 안정성 테스트

고배속 모드에서 FastCapture의 데이터 캡처 성능과 안정성을 종합적으로 테스트합니다.
- 캡처 성공률
- 데이터 품질 (이미지 크기, 형식 유효성)
- 메모리 사용량
- 처리 시간
- 프레임 스킵 비율
"""

import sys
import os
import time
import numpy as np
import argparse
import gc
import psutil
from typing import Dict, List, Tuple, Optional

# 프로젝트 루트의 'src' 디렉토리를 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, project_root)

try:
    import pyxel as px
    from main import App
    from utils.fast_capture import FastCapture
    import base64
    from io import BytesIO
    from PIL import Image
except ImportError as e:
    print(
        f"Error: {e}. Make sure you are in the correct environment and all dependencies are installed."
    )
    sys.exit(1)


class DataCaptureTestApp(App):
    """데이터 캡처 테스트를 위해 App 클래스를 확장"""

    def __init__(self, speed_multiplier: int, test_duration: int = 10):
        super().__init__(speed_multiplier=speed_multiplier)

        self.speed_multiplier = speed_multiplier
        self.test_duration = test_duration
        self.start_time = time.time()

        # 데이터 캡처 통계
        self.capture_attempts = 0
        self.capture_successes = 0
        self.capture_failures = 0
        self.invalid_data_count = 0
        self.total_capture_time = 0
        self.capture_times = []
        self.data_sizes = []
        self.memory_usage = []

        # FastCapture 인스턴스
        self.fast_capture = FastCapture(width=256, height=192)

        # 메모리 프로세스 모니터링
        self.process = psutil.Process()
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        # 플레이어 무적 모드
        if (
            self.game
            and hasattr(self.game, "state")
            and hasattr(self.game.state, "player")
        ):
            self.game.state.player.invincible = True
            print("   - ✅ 플레이어 무적 모드 활성화됨")

        print(
            f"   - 🎯 {speed_multiplier}x 배속으로 {test_duration}초간 데이터 캡처 테스트 시작"
        )
        print(f"   - 💾 초기 메모리 사용량: {self.initial_memory:.1f} MB")

    def update(self):
        super().update()

        # 매 프레임마다 데이터 캡처 시도
        self._test_data_capture()

        # 1초마다 메모리 사용량 체크
        current_time = time.time()
        if len(self.memory_usage) == 0 or current_time - self.start_time > len(
            self.memory_usage
        ):
            current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
            self.memory_usage.append(current_memory)

        # 테스트 종료 조건
        if current_time - self.start_time > self.test_duration:
            self._print_results()
            px.quit()

    def _test_data_capture(self):
        """데이터 캡처 테스트 수행"""
        capture_start = time.perf_counter()
        self.capture_attempts += 1

        try:
            # Pyxel 색상 팔레트 정의 (main.py와 동일)
            palette_hex = [
                0x000000,  # 0: 검정
                0x2D1B69,  # 1: 짙은 파랑
                0xC53031,  # 2: 빨강
                0x9B59B6,  # 3: 보라
                0x2E8B57,  # 4: 녹색
                0x8B4513,  # 5: 갈색
                0xFF7F00,  # 6: 주황
                0xD3D3D3,  # 7: 연한 회색
                0x696969,  # 8: 진한 회색
                0x6495ED,  # 9: 연한 파랑
                0x4169E1,  # 10: 파랑
                0x00FF00,  # 11: 밝은 녹색
                0xFF00FF,  # 12: 마젠타
                0xA52A2A,  # 13: 갈색-빨강
                0xFFFF00,  # 14: 노랑
                0xFFFFFF,  # 15: 흰색
            ]

            # FastCapture를 사용한 화면 캡처
            result = self.fast_capture.capture_optimized(
                px, palette_hex, use_compression="png"
            )

            capture_time = (time.perf_counter() - capture_start) * 1000  # ms
            self.capture_times.append(capture_time)
            self.total_capture_time += capture_time

            if result is not None:
                base64_image, stats = result
                self.capture_successes += 1

                # 데이터 유효성 검사
                if self._validate_captured_data(base64_image):
                    # base64 데이터 크기 기록
                    data_size = len(base64_image)
                    self.data_sizes.append(data_size)
                else:
                    self.invalid_data_count += 1
            else:
                self.capture_failures += 1

        except Exception as e:
            self.capture_failures += 1
            print(f"   ⚠️ 캡처 오류: {e}")

    def _validate_captured_data(self, base64_image: str) -> bool:
        """캡처된 데이터의 유효성 검사"""
        try:
            # base64 디코딩 테스트
            image_data = base64.b64decode(base64_image)

            # PIL로 이미지 로드 테스트
            image = Image.open(BytesIO(image_data))

            # 예상 크기 확인
            if image.size != (256, 192):
                print(f"   ⚠️ 잘못된 이미지 크기: {image.size}, 예상: (256, 192)")
                return False

            return True

        except Exception as e:
            print(f"   ⚠️ 데이터 유효성 검사 실패: {e}")
            return False

    def _print_results(self):
        """테스트 결과 출력"""
        current_memory = self.process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = current_memory - self.initial_memory

        success_rate = (
            (self.capture_successes / self.capture_attempts * 100)
            if self.capture_attempts > 0
            else 0
        )
        failure_rate = (
            (self.capture_failures / self.capture_attempts * 100)
            if self.capture_attempts > 0
            else 0
        )
        invalid_rate = (
            (self.invalid_data_count / self.capture_successes * 100)
            if self.capture_successes > 0
            else 0
        )

        avg_capture_time = np.mean(self.capture_times) if self.capture_times else 0
        max_capture_time = np.max(self.capture_times) if self.capture_times else 0

        avg_data_size = np.mean(self.data_sizes) if self.data_sizes else 0

        print(f"\n📊 데이터 캡처 테스트 결과 ({self.speed_multiplier}x 배속)")
        print("=" * 50)
        print(f"🎯 캡처 통계:")
        print(f"   - 총 시도: {self.capture_attempts:,}")
        print(f"   - 성공: {self.capture_successes:,} ({success_rate:.1f}%)")
        print(f"   - 실패: {self.capture_failures:,} ({failure_rate:.1f}%)")
        print(f"   - 무효 데이터: {self.invalid_data_count:,} ({invalid_rate:.1f}%)")

        print(f"\n⏱️ 성능 통계:")
        print(f"   - 평균 캡처 시간: {avg_capture_time:.2f} ms")
        print(f"   - 최대 캡처 시간: {max_capture_time:.2f} ms")
        print(
            f"   - 초당 평균 캡처: {self.capture_successes / self.test_duration:.1f} 회"
        )

        print(f"\n💾 메모리 통계:")
        print(f"   - 초기 메모리: {self.initial_memory:.1f} MB")
        print(f"   - 최종 메모리: {current_memory:.1f} MB")
        print(f"   - 메모리 증가: {memory_increase:.1f} MB")
        print(f"   - 최대 메모리: {max(self.memory_usage):.1f} MB")

        print(f"\n📦 데이터 통계:")
        print(f"   - 평균 데이터 크기: {avg_data_size / 1024:.1f} KB")
        print(f"   - 총 데이터 전송량: {sum(self.data_sizes) / 1024 / 1024:.1f} MB")

        # 평가 결과
        print(f"\n🏆 종합 평가:")
        if success_rate >= 95 and invalid_rate <= 1 and memory_increase < 50:
            print(f"   ✅ 우수: {self.speed_multiplier}x 배속에서 안정적 동작")
        elif success_rate >= 90 and invalid_rate <= 5 and memory_increase < 100:
            print(f"   🟡 양호: {self.speed_multiplier}x 배속에서 실용적 동작")
        else:
            print(f"   🔴 주의: {self.speed_multiplier}x 배속에서 품질 저하 감지")


def run_data_capture_test(speed: int, duration: int = 10):
    """단일 배속에 대한 데이터 캡처 테스트 실행"""
    app = DataCaptureTestApp(speed_multiplier=speed, test_duration=duration)
    app.run()


def run_comprehensive_test(speeds: List[int] = None, duration: int = 10):
    """여러 배속에 대한 종합 테스트"""
    if speeds is None:
        speeds = [1, 8, 32, 128, 512, 1024]

    print("🚀 데이터 캡처 종합 테스트를 시작합니다.")
    print(f"   - 테스트 배속: {speeds}")
    print(f"   - 각 배속별 테스트 시간: {duration}초")
    print("=" * 50)

    results = {}

    for speed in speeds:
        print(f"\n⏱️ {speed}x 배속 테스트 중...")
        try:
            # 메모리 정리
            gc.collect()
            time.sleep(1)

            run_data_capture_test(speed, duration)

        except Exception as e:
            print(f"   ❌ 오류: {speed}x 배속 테스트 중 예외 발생: {e}")

        print("-" * 30)

    print("\n🎉 모든 테스트 완료!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="데이터 캡처 안정성 테스트")
    parser.add_argument("--speed", type=int, help="단일 배속 테스트를 위한 배속 값")
    parser.add_argument("--duration", type=int, default=10, help="테스트 시간(초)")
    parser.add_argument("--comprehensive", action="store_true", help="종합 테스트 실행")
    args = parser.parse_args()

    if args.speed:
        run_data_capture_test(args.speed, args.duration)
    elif args.comprehensive:
        run_comprehensive_test(duration=args.duration)
    else:
        # 기본: 주요 배속들 테스트
        run_comprehensive_test([1, 32, 256, 1024], args.duration)
