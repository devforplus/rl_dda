#!/usr/bin/env python
"""
캡처되는 데이터 내용 표시 스크립트

실제로 어떤 데이터가 캡처되는지 샘플을 보여줍니다.
"""

import sys
import os
import time
import json
import base64
from io import BytesIO

# 프로젝트 루트의 'src' 디렉토리를 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, project_root)

try:
    import pyxel as px
    from main import App
    from utils.fast_capture import FastCapture
    from PIL import Image
except ImportError as e:
    print(f"Error: {e}. Make sure you are in the correct environment.")
    sys.exit(1)


class DataShowApp(App):
    """캡처 데이터를 보여주는 App"""

    def __init__(self):
        super().__init__(speed_multiplier=1)

        self.sample_count = 0
        self.max_samples = 3
        self.data_samples = []

        # 플레이어 무적 모드
        if (
            self.game
            and hasattr(self.game, "state")
            and hasattr(self.game.state, "player")
        ):
            self.game.state.player.invincible = True

        print("🔍 데이터 캡처 샘플 수집 중...")
        print("   게임이 1-2초 실행된 후 샘플 데이터를 보여드립니다.")

    def update(self):
        super().update()

        # 1초마다 샘플 수집
        if px.frame_count % 60 == 0 and px.frame_count > 60:
            self._collect_sample()

        # 3개 샘플 수집 후 종료
        if self.sample_count >= self.max_samples:
            self._show_results()
            px.quit()

    def _collect_sample(self):
        """데이터 샘플 수집"""
        if self.sample_count >= self.max_samples:
            return

        print(f"\n📸 샘플 {self.sample_count + 1} 수집 중...")

        # 현재 프레임 데이터 수집
        frame_data = self._collect_current_frame_data()

        if frame_data:
            frame_dict, pil_image, label_rows = frame_data

            # 샘플 데이터 저장
            sample = {
                "sample_id": self.sample_count + 1,
                "timestamp": frame_dict["timestamp"],
                "image_data": frame_dict["image_png_base64"],
                "labels": frame_dict["labels"],
                "game_state": frame_dict["game_state"],
                "image_size_kb": len(frame_dict["image_png_base64"]) / 1024,
                "total_objects": len(frame_dict["labels"]) - 1,  # "header" 제외
            }

            self.data_samples.append(sample)
            self.sample_count += 1

            print(f"✅ 샘플 {self.sample_count} 수집 완료")
        else:
            print(f"❌ 샘플 {self.sample_count + 1} 수집 실패")

    def _show_results(self):
        """수집된 데이터 샘플 분석 결과 표시"""
        print("\n" + "=" * 60)
        print("📋 **캡처되는 데이터 내용 분석**")
        print("=" * 60)

        if not self.data_samples:
            print("❌ 수집된 샘플이 없습니다.")
            return

        # 전체 통계
        total_size = sum(sample["image_size_kb"] for sample in self.data_samples)
        avg_size = total_size / len(self.data_samples)
        total_objects = sum(sample["total_objects"] for sample in self.data_samples)
        avg_objects = total_objects / len(self.data_samples)

        print(f"📊 **전체 통계** (샘플 {len(self.data_samples)}개)")
        print(f"   - 평균 이미지 크기: {avg_size:.1f} KB")
        print(f"   - 평균 게임 객체 수: {avg_objects:.1f}개")
        print(f"   - 총 데이터 크기: {total_size:.1f} KB")

        # 각 샘플 상세 정보
        for i, sample in enumerate(self.data_samples, 1):
            print(f"\n🔍 **샘플 {i} 상세 정보**")
            print(
                f"   📅 타임스탬프: {time.strftime('%H:%M:%S', time.localtime(sample['timestamp']))}"
            )
            print(f"   🎮 게임 상태:")
            print(f"      - 점수: {sample['game_state']['score']}")
            print(f"      - 스테이지: {sample['game_state']['stage']}")
            print(f"   🖼️  이미지 데이터:")
            print(f"      - 형식: PNG (base64 인코딩)")
            print(f"      - 크기: {sample['image_size_kb']:.1f} KB")
            print(f"      - 해상도: 256x192 픽셀")
            print(f"   🎯 객체 라벨 ({sample['total_objects']}개):")

            if len(sample["labels"]) > 1:  # "header" 제외
                for label in sample["labels"][1:]:  # "header" 스킵
                    if len(label.split()) >= 3:
                        obj_type, x, y = label.split()[:3]
                        print(f"      - {obj_type}: 위치 ({x}, {y})")
            else:
                print("      - 감지된 객체 없음")

        # 데이터 구조 설명
        print(f"\n📚 **데이터 구조 설명**")
        print(f"   🖼️  이미지 데이터: 게임 화면의 RGB 이미지")
        print(f"      - Pyxel의 16색 팔레트를 RGB로 변환")
        print(f"      - PNG 압축 후 base64 인코딩")
        print(f"      - 실시간 화면 캡처 (픽셀별 읽기)")
        print(f"   🎯 라벨 데이터: 게임 객체들의 위치 정보")
        print(f"      - player: 플레이어 위치")
        print(f"      - enemy: 적 객체들의 위치")
        print(f"      - powerup: 파워업 아이템 위치")
        print(f"      - explosion: 폭발 이펙트 위치")
        print(f"   🎮 게임 상태: 점수, 스테이지 등 메타 정보")

        # 성능 특성
        print(f"\n⚡ **성능 특성**")
        print(f"   🔄 캡처 빈도: 매 프레임 또는 설정된 간격")
        print(f"   🚀 최적화: FastCapture 사용 (NumPy 벡터화)")
        print(f"   💾 메모리: 버퍼 재사용으로 메모리 효율성 확보")
        print(f"   🎯 품질: 무손실 PNG 압축 (정확한 픽셀 정보)")

        print("\n" + "=" * 60)
        print("✅ 데이터 분석 완료!")


def main():
    print("🚀 데이터 캡처 내용 확인 도구 시작")
    print("   잠시 후 캡처되는 데이터의 실제 내용을 보여드립니다.")

    app = DataShowApp()
    app.run()


if __name__ == "__main__":
    main()
