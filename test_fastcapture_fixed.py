#!/usr/bin/env python3
"""
수정된 FastCapture 테스트
"""

import sys
import time
import os

# src 디렉토리를 패키지 경로에 추가
sys.path.insert(0, "src")


def test_fastcapture():
    """FastCapture 기본 테스트"""
    print("🚀 FastCapture 테스트 시작")

    try:
        from utils.fast_capture import FastCapture

        print("✅ FastCapture import 성공")
    except ImportError as e:
        print(f"❌ FastCapture import 실패: {e}")
        return False

    # Mock Pyxel 객체 생성
    class MockPyxel:
        def __init__(self):
            self.pixel_data = {}
            # 테스트용 랜덤 픽셀 데이터 생성
            import random

            for y in range(192):
                for x in range(256):
                    self.pixel_data[(x, y)] = random.randint(0, 15)

        def pget(self, x, y):
            """pget 메서드 모의 구현"""
            return self.pixel_data.get((x, y), 0)

    mock_px = MockPyxel()

    # FastCapture 초기화
    try:
        fc = FastCapture(256, 192)
        print("✅ FastCapture 초기화 성공")
    except Exception as e:
        print(f"❌ FastCapture 초기화 실패: {e}")
        return False

    # 캡쳐 테스트
    palette_hex = [
        0x000000,
        0x2D1B69,
        0xC53031,
        0x9B59B6,
        0x2E8B57,
        0x8B4513,
        0xFF7F00,
        0xD3D3D3,
        0x696969,
        0x6495ED,
        0x4169E1,
        0x00FF00,
        0xFF00FF,
        0xA52A2A,
        0xFFFF00,
        0xFFFFFF,
    ]

    print("📸 캡쳐 테스트 시작...")

    try:
        start_time = time.time()
        result = fc.capture_optimized(mock_px, palette_hex)
        end_time = time.time()

        if result:
            image_data_b64, stats = result
            print(f"✅ 캡쳐 성공!")
            print(f"  - 캡쳐 시간: {(end_time - start_time) * 1000:.2f}ms")
            print(f"  - 이미지 데이터 크기: {len(image_data_b64)} 문자")
            print(f"  - 성능 통계: {stats}")

            # 성능 리포트
            report = fc.get_performance_report()
            print(f"  - 성능 리포트: {report}")

            print("🎉 FastCapture 테스트 성공!")
            return True
        else:
            print("❌ 캡쳐 실패 - 결과가 None")
            return False

    except Exception as e:
        print(f"❌ 캡쳐 중 오류: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_fastcapture()
    if success:
        print("✅ 모든 테스트 통과!")
    else:
        print("❌ 테스트 실패!")
        sys.exit(1)
