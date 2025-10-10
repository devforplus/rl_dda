#!/usr/bin/env python3
"""
RL DDA 자동 업로드 빠른 시작 헬퍼
기존 게임 코드에 몇 줄만 추가하면 자동 업로드가 가능합니다!
"""

import asyncio
import numpy as np
from typing import Optional, Callable, Dict, Any
import platform

try:
    from src.auto_game_client import (
        RLDDAAutoClient,
        GameFrameData,
        create_auto_client_sync,
    )
except ImportError:
    # 패키지 외부에서 실행되는 경우
    from auto_game_client import RLDDAAutoClient, GameFrameData, create_auto_client_sync


class QuickAutoUpload:
    """
    기존 게임 코드에 쉽게 통합할 수 있는 자동 업로드 래퍼

    사용법:
        # 게임 시작 시
        uploader = QuickAutoUpload.setup("my_game", "player1")

        # 게임 루프에서
        uploader.capture_and_upload(screen_array, "JUMP", score=100)

        # 게임 종료 시
        uploader.finish()
    """

    def __init__(self, client: RLDDAAutoClient):
        self.client = client
        self.is_web = platform.system() == "Emscripten"

    @classmethod
    def setup(
        cls,
        game_id: str,
        player_id: str,
        server_url: str = "http://localhost:3000",
        auto_interval: float = 2.0,
        enable_auto_upload: bool = True,
    ) -> "QuickAutoUpload":
        """
        빠른 설정 - 한 줄로 자동 업로드 시작

        Args:
            game_id: 게임 ID
            player_id: 플레이어 ID
            server_url: 서버 URL
            auto_interval: 자동 업로드 간격 (초)
            enable_auto_upload: 자동 업로드 활성화 여부

        Returns:
            QuickAutoUpload: 설정된 업로더 인스턴스
        """
        try:
            # 클라이언트 생성 및 세션 시작
            client = create_auto_client_sync(
                server_url=server_url,
                game_id=game_id,
                player_id=player_id,
                auto_upload_interval=auto_interval,
            )

            uploader = cls(client)

            # 자동 업로드 시작 (콜백은 나중에 설정)
            if enable_auto_upload:
                client.start_auto_upload()
                print(f"🤖 자동 업로드 시작: {game_id} ({auto_interval}초 간격)")

            print(f"✅ QuickAutoUpload 설정 완료: {game_id}")
            return uploader

        except Exception as e:
            print(f"❌ QuickAutoUpload 설정 실패: {e}")
            # 실패해도 게임은 계속 실행되도록 더미 객체 반환
            return cls._create_dummy()

    @classmethod
    def _create_dummy(cls) -> "QuickAutoUpload":
        """실패 시 더미 객체 생성 (게임 중단 방지)"""

        class DummyClient:
            def capture_frame_from_array(self, *args, **kwargs):
                return None

            def upload_frame_if_important(self, *args, **kwargs):
                return None

            def end_game_session(self):
                return None

            def get_stats(self):
                return {}

        dummy = cls.__new__(cls)
        dummy.client = DummyClient()
        dummy.is_web = False
        dummy._is_dummy = True
        return dummy

    def capture_and_upload(
        self, screen_array: np.ndarray, player_action: str, **game_state
    ) -> bool:
        """
        화면 캡처 및 업로드 (원라이너)

        Args:
            screen_array: 게임 화면 배열
            player_action: 플레이어 액션
            **game_state: 게임 상태 (score, level, enemies 등)

        Returns:
            bool: 업로드 성공 여부
        """
        if hasattr(self, "_is_dummy"):
            return False

        try:
            # 프레임 데이터 생성
            frame_data = self.client.capture_frame_from_array(
                image_array=screen_array, player_action=player_action, **game_state
            )

            # 중요한 프레임이면 즉시 업로드
            if self.is_web:
                # 웹 환경에서는 논블로킹
                asyncio.create_task(self.client.upload_frame_if_important(frame_data))
                return True
            else:
                # 데스크톱에서는 동기 실행
                result = asyncio.run(self.client.upload_frame_if_important(frame_data))
                return result is not None

        except Exception as e:
            print(f"❌ 캡처/업로드 실패: {e}")
            return False

    def force_upload(
        self, screen_array: np.ndarray, player_action: str, **game_state
    ) -> bool:
        """
        강제 즉시 업로드 (중요한 순간)

        Args:
            screen_array: 게임 화면 배열
            player_action: 플레이어 액션
            **game_state: 게임 상태

        Returns:
            bool: 업로드 성공 여부
        """
        if hasattr(self, "_is_dummy"):
            return False

        try:
            frame_data = self.client.capture_frame_from_array(
                image_array=screen_array, player_action=player_action, **game_state
            )

            if self.is_web:
                asyncio.create_task(self.client.upload_game_frame(frame_data))
                return True
            else:
                result = asyncio.run(self.client.upload_game_frame(frame_data))
                return result is not None

        except Exception as e:
            print(f"❌ 강제 업로드 실패: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """업로드 통계 반환"""
        if hasattr(self, "_is_dummy"):
            return {}
        return self.client.get_stats()

    def print_stats(self):
        """통계 출력 (디버깅용)"""
        stats = self.get_stats()
        if stats:
            print(
                f"📊 업로드 통계: 캡처={stats.get('total_frames_captured', 0)}, "
                f"업로드={stats.get('total_frames_uploaded', 0)}, "
                f"실패={stats.get('total_upload_failures', 0)}"
            )

    def finish(self):
        """세션 종료 및 정리"""
        if hasattr(self, "_is_dummy"):
            return

        try:
            if self.is_web:
                asyncio.create_task(self.client.end_game_session())
            else:
                asyncio.run(self.client.end_game_session())
            print("✅ 자동 업로드 세션 종료")
        except Exception as e:
            print(f"❌ 세션 종료 실패: {e}")


# 전역 변수로 간편 사용
_global_uploader: Optional[QuickAutoUpload] = None


def init_auto_upload(
    game_id: str, player_id: str, server_url: str = "http://localhost:3000", **kwargs
) -> QuickAutoUpload:
    """
    전역 자동 업로더 초기화 (가장 간단한 방식)

    Args:
        game_id: 게임 ID
        player_id: 플레이어 ID
        server_url: 서버 URL
        **kwargs: 추가 설정

    Returns:
        QuickAutoUpload: 업로더 인스턴스
    """
    global _global_uploader
    _global_uploader = QuickAutoUpload.setup(game_id, player_id, server_url, **kwargs)
    return _global_uploader


def upload_frame(screen_array: np.ndarray, action: str, **game_state) -> bool:
    """
    전역 업로더로 프레임 업로드 (초간단)

    Args:
        screen_array: 게임 화면
        action: 플레이어 액션
        **game_state: 게임 상태

    Returns:
        bool: 업로드 성공 여부
    """
    if _global_uploader:
        return _global_uploader.capture_and_upload(screen_array, action, **game_state)
    return False


def finish_upload():
    """전역 업로더 종료"""
    if _global_uploader:
        _global_uploader.finish()


# 데코레이터 방식
def auto_upload_frame(action_name: Optional[str] = None):
    """
    함수 데코레이터로 자동 업로드 적용

    사용법:
        @auto_upload_frame("JUMP")
        def player_jump(screen):
            # 점프 로직
            pass
    """

    def decorator(func):
        def wrapper(*args, **kwargs):
            # 함수 실행
            result = func(*args, **kwargs)

            # 첫 번째 인자가 화면 배열이라고 가정
            if args and isinstance(args[0], np.ndarray):
                screen = args[0]
                action = action_name or func.__name__.upper()
                upload_frame(screen, action)

            return result

        return wrapper

    return decorator


# 컨텍스트 매니저 방식
class AutoUploadSession:
    """
    with 문으로 자동 업로드 세션 관리

    사용법:
        with AutoUploadSession("my_game", "player1") as uploader:
            # 게임 루프
            uploader.upload(screen, "MOVE")
    """

    def __init__(self, game_id: str, player_id: str, **kwargs):
        self.game_id = game_id
        self.player_id = player_id
        self.kwargs = kwargs
        self.uploader = None

    def __enter__(self) -> QuickAutoUpload:
        self.uploader = QuickAutoUpload.setup(
            self.game_id, self.player_id, **self.kwargs
        )
        return self.uploader

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.uploader:
            self.uploader.finish()


# 기존 게임 코드 통합을 위한 패치 함수들
def patch_pygame_game(game_object, screen_attr: str = "screen"):
    """
    Pygame 게임 객체에 자동 업로드 기능 패치

    Args:
        game_object: 게임 객체
        screen_attr: 화면 속성명
    """
    if not hasattr(game_object, "auto_uploader"):
        game_object.auto_uploader = None

    def start_auto_upload(self, game_id: str, player_id: str):
        self.auto_uploader = QuickAutoUpload.setup(game_id, player_id)

    def upload_current_frame(self, action: str, **game_state):
        if self.auto_uploader and hasattr(self, screen_attr):
            import pygame

            screen_surface = getattr(self, screen_attr)
            screen_array = pygame.surfarray.array3d(screen_surface)
            screen_array = np.transpose(screen_array, (1, 0, 2))
            return self.auto_uploader.capture_and_upload(
                screen_array, action, **game_state
            )
        return False

    def end_auto_upload(self):
        if self.auto_uploader:
            self.auto_uploader.finish()
            self.auto_uploader = None

    # 메서드 추가
    game_object.start_auto_upload = start_auto_upload.__get__(game_object)
    game_object.upload_current_frame = upload_current_frame.__get__(game_object)
    game_object.end_auto_upload = end_auto_upload.__get__(game_object)


if __name__ == "__main__":
    # 빠른 테스트
    print("🚀 QuickAutoUpload 테스트")

    # 방법 1: 클래스 방식
    uploader = QuickAutoUpload.setup("test_game", "test_player")

    # 가짜 화면 데이터
    fake_screen = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)

    # 업로드 테스트
    success = uploader.capture_and_upload(fake_screen, "TEST_ACTION", game_score=100)
    print(f"업로드 결과: {success}")

    # 통계 출력
    uploader.print_stats()

    # 종료
    uploader.finish()

    print("✅ 테스트 완료!")
