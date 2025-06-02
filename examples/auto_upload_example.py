#!/usr/bin/env python3
"""
RL DDA 자동 업로드 클라이언트 사용 예제
클라이언트에서 한 번만 설정하면, 모든 게임 데이터가 자동으로 DB에 저장됩니다! 🎉
"""

import asyncio
import numpy as np
import time
from typing import Dict, List, Optional
import json
from pathlib import Path

# 프로젝트 루트에서 실행하는 경우
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from .auto_game_client import (
    RLDDAAutoClient,
    GameFrameData,
    GameSessionConfig,
    create_auto_client_sync,
)

# NewServerClient는 해당 파일 끝부분에서 import
from .server_client import GameDataServerClient


class MockGame:
    """게임 시뮬레이션을 위한 모형 게임 클래스"""

    def __init__(self):
        self.player_x = 50
        self.player_y = 50
        self.score = 0
        self.level = 1
        self.enemies = []
        self.items = []
        self.current_action = "IDLE"

    def update(self):
        """게임 상태 업데이트"""
        # 플레이어 이동 시뮬레이션
        import random

        actions = ["IDLE", "MOVE_LEFT", "MOVE_RIGHT", "JUMP", "ATTACK"]
        self.current_action = random.choice(actions)

        if self.current_action == "MOVE_LEFT":
            self.player_x = max(0, self.player_x - 5)
        elif self.current_action == "MOVE_RIGHT":
            self.player_x = min(800, self.player_x + 5)
        elif self.current_action == "JUMP":
            self.player_y = max(0, self.player_y - 10)
        elif self.current_action == "ATTACK":
            self.score += 10

        # 적 생성/제거 시뮬레이션
        if random.random() < 0.3:  # 30% 확률로 적 생성
            enemy = {
                "x": random.random(),
                "y": random.random(),
                "width": 0.05,
                "height": 0.05,
                "type": "basic_enemy",
            }
            self.enemies.append(enemy)

        # 아이템 생성 시뮬레이션
        if random.random() < 0.2:  # 20% 확률로 아이템 생성
            item = {
                "x": random.random(),
                "y": random.random(),
                "width": 0.03,
                "height": 0.03,
                "type": "power_up",
            }
            self.items.append(item)

        # 적/아이템 수 제한
        if len(self.enemies) > 3:
            self.enemies.pop(0)
        if len(self.items) > 2:
            self.items.pop(0)

    def get_screen_array(self) -> np.ndarray:
        """게임 화면을 NumPy 배열로 반환 (모형)"""
        # 800x600 RGB 이미지 생성
        screen = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)

        # 플레이어 위치에 파란색 사각형 그리기 (시뮬레이션)
        px, py = int(self.player_x), int(self.player_y)
        screen[py : py + 20, px : px + 20] = [0, 0, 255]  # 파란색

        # 적들을 빨간색으로 표시
        for enemy in self.enemies:
            ex = int(enemy["x"] * 800)
            ey = int(enemy["y"] * 600)
            screen[ey : ey + 10, ex : ex + 10] = [255, 0, 0]  # 빨간색

        # 아이템을 녹색으로 표시
        for item in self.items:
            ix = int(item["x"] * 800)
            iy = int(item["y"] * 600)
            screen[iy : iy + 8, ix : ix + 8] = [0, 255, 0]  # 녹색

        return screen

    def get_player_position(self) -> Dict:
        """플레이어 위치 반환 (YOLO 형식)"""
        return {
            "x": self.player_x / 800,  # 정규화된 x 좌표
            "y": self.player_y / 600,  # 정규화된 y 좌표
            "width": 20 / 800,
            "height": 20 / 600,
        }


async def example_async_usage():
    """비동기 사용 예제"""
    print("🎮 RL DDA 자동 업로드 클라이언트 - 비동기 예제")
    print("=" * 50)

    # 게임 및 클라이언트 초기화
    game = MockGame()
    client = RLDDAAutoClient("http://localhost:3000")

    try:
        # 1. 게임 세션 시작
        config = GameSessionConfig(
            game_id="example_platformer",
            player_id="test_player_001",
            game_mode="training",
            auto_upload_interval=1.0,  # 1초마다 자동 업로드
            random_capture_rate=0.2,  # 20% 확률로 일반 프레임도 업로드
        )

        session_id = await client.start_game_session(
            "example_platformer", "test_player_001", config
        )
        print(f"📍 세션 ID: {session_id}")

        # 2. 프레임 캡처 콜백 함수 정의
        def capture_current_frame() -> GameFrameData:
            """현재 게임 프레임을 캡처하는 콜백"""
            screen_array = game.get_screen_array()

            return client.capture_frame_from_array(
                image_array=screen_array,
                player_action=game.current_action,
                game_score=game.score,
                game_level=game.level,
                player_position=game.get_player_position(),
                enemies=game.enemies.copy(),
                items=game.items.copy(),
                quality_score=0.9,
            )

        # 3. 자동 업로드 시작
        client.start_auto_upload(capture_current_frame)

        # 4. 게임 루프 시뮬레이션 (10초간)
        print("🎯 게임 시뮬레이션 시작 (10초간)...")
        for i in range(50):  # 50 프레임
            game.update()

            # 중요한 액션의 경우 즉시 업로드
            if game.current_action in ["JUMP", "ATTACK"]:
                frame_data = capture_current_frame()
                await client.upload_frame_if_important(frame_data)
                print(f"⚡ 즉시 업로드: {game.current_action}")

            # 게임 상태 출력
            if i % 10 == 0:
                stats = client.get_stats()
                print(
                    f"📊 프레임 {i}: 점수={game.score}, "
                    f"캡처={stats['total_frames_captured']}, "
                    f"업로드={stats['total_frames_uploaded']}"
                )

            await asyncio.sleep(0.2)  # 200ms 간격

        # 5. 세션 종료
        await client.end_game_session()

        # 6. 최종 통계
        final_stats = client.get_stats()
        print("\n📈 최종 통계:")
        for key, value in final_stats.items():
            print(f"   {key}: {value}")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        await client.end_game_session()


def example_sync_usage():
    """동기 사용 예제 (간단한 버전)"""
    print("\n🎮 RL DDA 자동 업로드 클라이언트 - 동기 예제")
    print("=" * 50)

    try:
        # 1. 클라이언트 생성 및 세션 시작 (한 번에)
        client = create_auto_client_sync(
            server_url="http://localhost:3000",
            game_id="simple_game",
            player_id="player_002",
            auto_upload_interval=2.0,
        )

        # 2. 게임 초기화
        game = MockGame()

        # 3. 수동으로 몇 개 프레임 업로드
        for i in range(5):
            game.update()

            # 프레임 생성
            screen_array = game.get_screen_array()
            frame_data = client.capture_frame_from_array(
                image_array=screen_array,
                player_action=game.current_action,
                game_score=game.score,
                game_level=game.level,
                player_position=game.get_player_position(),
                enemies=game.enemies.copy(),
                items=game.items.copy(),
            )

            # 레거시 방식으로도 업로드 가능
            asyncio.run(
                client.upload_legacy_data(
                    game_screen_base64=frame_data.image_base64,
                    labeling_code="\n".join(client._generate_yolo_labels(frame_data)),
                    metadata={"manual_upload": True, "frame_number": i},
                )
            )

            print(f"✅ 수동 업로드 완료: 프레임 {i} - {game.current_action}")
            time.sleep(1)

        # 4. 세션 종료
        asyncio.run(client.end_game_session())

    except Exception as e:
        print(f"❌ 동기 예제 오류: {e}")


def example_custom_callbacks():
    """사용자 정의 콜백 예제"""
    print("\n🎮 사용자 정의 콜백 예제")
    print("=" * 50)

    async def custom_example():
        client = RLDDAAutoClient("http://localhost:3000")
        game = MockGame()

        try:
            await client.start_game_session("custom_game", "player_003")

            # 사용자 정의 업로드 조건
            def should_upload_custom(frame_data: GameFrameData) -> bool:
                """커스텀 업로드 조건: 점수가 50 이상이거나 적이 2명 이상일 때만"""
                return frame_data.game_score >= 50 or (
                    frame_data.enemies and len(frame_data.enemies) >= 2
                )

            client.set_should_upload_callback(should_upload_custom)

            # 게임 시뮬레이션
            for i in range(20):
                game.update()
                game.score += 5  # 점수 증가

                frame_data = client.capture_frame_from_array(
                    image_array=game.get_screen_array(),
                    player_action=game.current_action,
                    game_score=game.score,
                    enemies=game.enemies.copy(),
                )

                # 커스텀 조건에 따른 업로드
                uploaded = await client.upload_frame_if_important(frame_data)
                if uploaded:
                    print(
                        f"🎯 커스텀 조건 만족 - 업로드: 점수={game.score}, 적={len(game.enemies)}"
                    )

                await asyncio.sleep(0.5)

            await client.end_game_session()

        except Exception as e:
            print(f"❌ 커스텀 예제 오류: {e}")
            await client.end_game_session()

    asyncio.run(custom_example())


def example_batch_upload():
    """배치 업로드 예제 (기존 이미지 파일들)"""
    print("\n🎮 배치 업로드 예제")
    print("=" * 50)

    try:
        # 기존 server_client 사용
        client = GameDataServerClient("http://localhost:3000")

        # 예시: data/images와 data/labels 디렉토리가 있는 경우
        images_dir = "data/images"
        labels_dir = "data/labels"

        if os.path.exists(images_dir) and os.path.exists(labels_dir):
            uploaded_ids = client.batch_upload_directory(
                images_dir=images_dir,
                labels_dir=labels_dir,
                metadata={"batch_upload": True, "source": "example"},
            )
            print(f"✅ 배치 업로드 완료: {len(uploaded_ids)}개 파일")
            print(
                f"   업로드된 ID들: {uploaded_ids[:5]}{'...' if len(uploaded_ids) > 5 else ''}"
            )
        else:
            print("⚠️ 배치 업로드를 위한 디렉토리가 없습니다.")
            print(
                f"   {images_dir} 및 {labels_dir} 디렉토리를 생성하고 파일을 추가해보세요."
            )

    except Exception as e:
        print(f"❌ 배치 업로드 오류: {e}")


if __name__ == "__main__":
    print("🚀 RL DDA 자동 업로드 클라이언트 예제 실행")
    print("서버가 http://localhost:3000 에서 실행 중인지 확인하세요!")
    print()

    # 각 예제 실행
    try:
        # 1. 비동기 예제 (메인)
        asyncio.run(example_async_usage())

        # 2. 동기 예제
        example_sync_usage()

        # 3. 커스텀 콜백 예제
        example_custom_callbacks()

        # 4. 배치 업로드 예제
        example_batch_upload()

        print("\n🎉 모든 예제 실행 완료!")

    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 예제 실행 중 오류: {e}")
        import traceback

        traceback.print_exc()
