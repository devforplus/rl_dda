"""
RL DDA 자동 게임 데이터 업로드 클라이언트
게임에서 한 번만 설정하면 모든 게임 데이터가 자동으로 DB에 저장됩니다!
"""

import asyncio
import threading
import time
import json
import base64
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, asdict
import numpy as np

try:
    from src.server_client import GameDataServerClient, IS_WEB
except ImportError:
    # 패키지 외부에서 실행되는 경우
    from server_client import GameDataServerClient, IS_WEB


@dataclass
class GameFrameData:
    """게임 프레임 데이터 구조"""

    image_base64: str
    player_action: str
    game_score: int = 0
    game_level: int = 1
    player_position: Optional[Dict] = None
    enemies: Optional[List[Dict]] = None
    items: Optional[List[Dict]] = None
    timestamp: Optional[float] = None
    quality_score: float = 0.8
    is_training_data: bool = True
    description: str = ""
    labels: Optional[List[str]] = None


@dataclass
class GameSessionConfig:
    """게임 세션 설정"""

    game_id: str
    player_id: str
    game_mode: str = "training"
    difficulty_level: str = "auto"
    auto_upload_interval: float = 2.0  # 초
    capture_important_actions: bool = True
    random_capture_rate: float = 0.1  # 10%
    max_retry_count: int = 3
    max_queue_size: int = 100


class RLDDAAutoClient:
    """
    RL DDA 자동 게임 데이터 업로드 클라이언트

    사용법:
        client = RLDDAAutoClient("http://localhost:3000")
        await client.start_game_session("my-game", "player123")
        client.start_auto_upload()

        # 게임 루프에서
        frame_data = client.capture_frame_from_array(screen_array, "JUMP")
        await client.upload_frame_if_important(frame_data)

        # 게임 종료 시
        await client.end_game_session()
    """

    def __init__(self, server_url: str = "http://localhost:3000"):
        """
        자동 클라이언트 초기화

        Args:
            server_url: 서버 URL
        """
        self.server_client = GameDataServerClient(server_url)
        self.server_url = server_url

        # 세션 상태
        self.current_session_id: Optional[str] = None
        self.config: Optional[GameSessionConfig] = None
        self.is_auto_uploading = False

        # 업로드 큐 및 재시도 관리
        self.upload_queue: List[GameFrameData] = []
        self.retry_count = 0
        self.is_processing_queue = False

        # 자동 업로드 스레드
        self.auto_upload_thread: Optional[threading.Thread] = None
        self.stop_auto_upload = threading.Event()

        # 콜백 함수들
        self.frame_capture_callback: Optional[Callable[[], GameFrameData]] = None
        self.should_upload_callback: Optional[Callable[[GameFrameData], bool]] = None

        # 통계
        self.stats = {
            "total_frames_captured": 0,
            "total_frames_uploaded": 0,
            "total_upload_failures": 0,
            "session_start_time": None,
        }

    async def start_game_session(
        self, game_id: str, player_id: str, config: Optional[GameSessionConfig] = None
    ) -> str:
        """
        게임 세션 시작

        Args:
            game_id: 게임 ID
            player_id: 플레이어 ID
            config: 세션 설정 (선택사항)

        Returns:
            str: 세션 ID
        """
        try:
            # 설정 초기화
            if config is None:
                config = GameSessionConfig(game_id=game_id, player_id=player_id)
            self.config = config

            # 서버 연결 확인
            if not await self.server_client.check_server_status():
                raise ConnectionError("서버에 연결할 수 없습니다")

            # 세션 정보 생성 (실제 서버 API가 있다면 사용)
            session_data = {
                "game_id": game_id,
                "player_id": player_id,
                "game_mode": config.game_mode,
                "difficulty_level": config.difficulty_level,
                "metadata": {
                    "client_version": "1.0.0",
                    "platform": "python",
                    "started_at": datetime.now().isoformat(),
                    "config": asdict(config),
                },
            }

            # 현재는 로컬 세션 ID 생성 (서버 API 구현 시 실제 API 호출)
            self.current_session_id = (
                f"session_{game_id}_{player_id}_{int(time.time())}"
            )

            # 통계 초기화
            self.stats["session_start_time"] = datetime.now()
            self.stats["total_frames_captured"] = 0
            self.stats["total_frames_uploaded"] = 0
            self.stats["total_upload_failures"] = 0

            print(f"✅ 게임 세션 시작: {self.current_session_id}")
            print(f"   게임: {game_id}, 플레이어: {player_id}")
            print(
                f"   모드: {config.game_mode}, 자동 업로드 간격: {config.auto_upload_interval}초"
            )

            return self.current_session_id

        except Exception as e:
            print(f"❌ 세션 시작 실패: {e}")
            raise

    def start_auto_upload(
        self, capture_callback: Optional[Callable[[], GameFrameData]] = None
    ):
        """
        자동 업로드 시작

        Args:
            capture_callback: 프레임 캡처 콜백 함수 (선택사항)
        """
        if self.is_auto_uploading:
            print("⚠️ 자동 업로드가 이미 실행 중입니다")
            return

        if not self.current_session_id:
            raise RuntimeError("게임 세션이 시작되지 않았습니다")

        if capture_callback:
            self.frame_capture_callback = capture_callback

        self.is_auto_uploading = True
        self.stop_auto_upload.clear()

        # 별도 스레드에서 자동 업로드 실행
        self.auto_upload_thread = threading.Thread(
            target=self._auto_upload_loop, daemon=True
        )
        self.auto_upload_thread.start()

        print(f"🤖 자동 업로드 시작 (간격: {self.config.auto_upload_interval}초)")

    def _auto_upload_loop(self):
        """자동 업로드 루프 (별도 스레드에서 실행)"""
        while not self.stop_auto_upload.is_set():
            try:
                # 프레임 캡처
                frame_data = None
                if self.frame_capture_callback:
                    frame_data = self.frame_capture_callback()

                if frame_data and self._should_upload_frame(frame_data):
                    # 비동기 업로드를 동기 환경에서 실행
                    if IS_WEB:
                        # 웹 환경에서는 메인 스레드의 이벤트 루프 사용
                        asyncio.create_task(self.upload_game_frame(frame_data))
                    else:
                        # 데스크톱 환경에서는 새 이벤트 루프 생성
                        asyncio.run(self.upload_game_frame(frame_data))

            except Exception as e:
                print(f"❌ 자동 업로드 중 오류: {e}")

            # 설정된 간격만큼 대기
            self.stop_auto_upload.wait(self.config.auto_upload_interval)

    async def upload_game_frame(self, frame_data: GameFrameData) -> Optional[str]:
        """
        게임 프레임 데이터 업로드

        Args:
            frame_data: 게임 프레임 데이터

        Returns:
            str: 업로드 성공 시 데이터 ID, 실패 시 None
        """
        try:
            # 라벨이 없으면 자동 생성
            if not frame_data.labels:
                frame_data.labels = self._generate_labels(frame_data)

            # 라벨 문자열 생성
            label_content = "\n".join(frame_data.labels)

            # 메타데이터 구성
            metadata = {
                "session_id": self.current_session_id,
                "player_action": frame_data.player_action,
                "game_score": frame_data.game_score,
                "game_level": frame_data.game_level,
                "timestamp_unix": frame_data.timestamp or time.time(),
                "quality_score": frame_data.quality_score,
                "is_training_data": frame_data.is_training_data,
                "description": frame_data.description
                or f"Auto captured - {frame_data.player_action}",
                "player_position": frame_data.player_position,
                "enemies_count": len(frame_data.enemies) if frame_data.enemies else 0,
                "items_count": len(frame_data.items) if frame_data.items else 0,
            }

            # 이미지 배열로 변환 (base64에서)
            try:
                from PIL import Image as PILImage
                import io

                # base64 → PIL Image → numpy array
                image_data = base64.b64decode(frame_data.image_base64)
                pil_image = PILImage.open(io.BytesIO(image_data))
                image_array = np.array(pil_image)

                # RGB → BGR 변환 (OpenCV 형식으로)
                if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                    image_array = image_array[:, :, ::-1]  # RGB to BGR

            except Exception as e:
                print(f"❌ 이미지 변환 실패: {e}")
                return None

            # 메모리에서 직접 업로드
            result = await self.server_client.upload_game_data_from_memory(
                image_array=image_array,
                label_content=label_content,
                filename_prefix=f"auto_frame_{frame_data.player_action}",
                metadata=metadata,
            )

            if result:
                self.stats["total_frames_uploaded"] += 1
                print(f"✅ 프레임 업로드 완료: {frame_data.player_action} -> {result}")
            else:
                self.stats["total_upload_failures"] += 1
                # 재시도 큐에 추가
                self._add_to_retry_queue(frame_data)

            return result

        except Exception as e:
            print(f"❌ 프레임 업로드 실패: {e}")
            self.stats["total_upload_failures"] += 1
            self._add_to_retry_queue(frame_data)
            return None

    def capture_frame_from_array(
        self, image_array: np.ndarray, player_action: str, **kwargs
    ) -> GameFrameData:
        """
        NumPy 배열에서 프레임 데이터 생성

        Args:
            image_array: 게임 화면 이미지 배열
            player_action: 플레이어 액션
            **kwargs: 추가 게임 상태 정보

        Returns:
            GameFrameData: 프레임 데이터
        """
        # 이미지를 base64로 인코딩
        try:
            from PIL import Image as PILImage
            import io

            # BGR을 RGB로 변환 (OpenCV 형식인 경우)
            if len(image_array.shape) == 3 and image_array.shape[2] == 3:
                rgb_array = image_array[:, :, ::-1]
            else:
                rgb_array = image_array

            pil_image = PILImage.fromarray(rgb_array.astype(np.uint8))
            buffered = io.BytesIO()
            pil_image.save(buffered, format="PNG")
            image_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

        except Exception as e:
            print(f"⚠️ 이미지 인코딩 실패: {e}")
            image_base64 = ""

        # 프레임 데이터 생성
        frame_data = GameFrameData(
            image_base64=image_base64,
            player_action=player_action,
            game_score=kwargs.get("game_score", 0),
            game_level=kwargs.get("game_level", 1),
            player_position=kwargs.get("player_position"),
            enemies=kwargs.get("enemies"),
            items=kwargs.get("items"),
            timestamp=time.time(),
            quality_score=kwargs.get("quality_score", 0.8),
            is_training_data=kwargs.get("is_training_data", True),
            description=kwargs.get("description", f"Captured frame - {player_action}"),
        )

        self.stats["total_frames_captured"] += 1
        return frame_data

    async def upload_frame_if_important(
        self, frame_data: GameFrameData
    ) -> Optional[str]:
        """
        중요한 프레임인 경우에만 즉시 업로드

        Args:
            frame_data: 프레임 데이터

        Returns:
            str: 업로드된 데이터 ID 또는 None
        """
        if self._should_upload_frame(frame_data):
            return await self.upload_game_frame(frame_data)
        return None

    def _should_upload_frame(self, frame_data: GameFrameData) -> bool:
        """
        업로드 필요 여부 판단

        Args:
            frame_data: 프레임 데이터

        Returns:
            bool: 업로드 필요 여부
        """
        # 사용자 정의 콜백이 있으면 우선 사용
        if self.should_upload_callback:
            return self.should_upload_callback(frame_data)

        # 기본 로직
        important_actions = {
            "JUMP",
            "ATTACK",
            "MOVE_LEFT",
            "MOVE_RIGHT",
            "SPECIAL",
            "SHOOT",
            "USE_ITEM",
        }

        # 중요한 액션
        if frame_data.player_action in important_actions:
            return True

        # 적이 있는 경우
        if frame_data.enemies and len(frame_data.enemies) > 0:
            return True

        # 아이템이 있는 경우
        if frame_data.items and len(frame_data.items) > 0:
            return True

        # 랜덤 캡처
        import random

        if random.random() < self.config.random_capture_rate:
            return True

        return False

    def _generate_labels(self, frame_data: GameFrameData) -> List[str]:
        """
        게임 상태에서 객체 라벨 자동 생성

        Args:
            frame_data: 프레임 데이터

        Returns:
            List[str]: 객체 탐지 형식 라벨 목록
        """
        labels = []

        # 플레이어 위치 (클래스 0)
        if frame_data.player_position:
            pos = frame_data.player_position
            labels.append(
                f"0 {pos.get('x', 0.5)} {pos.get('y', 0.5)} {pos.get('width', 0.1)} {pos.get('height', 0.1)}"
            )

        # 적 위치들 (클래스 1부터)
        if frame_data.enemies:
            for i, enemy in enumerate(frame_data.enemies):
                labels.append(
                    f"{i + 1} {enemy.get('x', 0.5)} {enemy.get('y', 0.5)} {enemy.get('width', 0.1)} {enemy.get('height', 0.1)}"
                )

        # 아이템들 (클래스 100부터)
        if frame_data.items:
            for i, item in enumerate(frame_data.items):
                labels.append(
                    f"{i + 100} {item.get('x', 0.5)} {item.get('y', 0.5)} {item.get('width', 0.05)} {item.get('height', 0.05)}"
                )

        return labels

    def _add_to_retry_queue(self, frame_data: GameFrameData):
        """재시도 큐에 프레임 추가"""
        if len(self.upload_queue) < self.config.max_queue_size:
            self.upload_queue.append(frame_data)
            # 큐 처리 시작
            if not self.is_processing_queue:
                threading.Thread(target=self._process_retry_queue, daemon=True).start()
        else:
            print("⚠️ 업로드 큐가 가득 참. 프레임을 삭제합니다.")

    def _process_retry_queue(self):
        """재시도 큐 처리 (별도 스레드에서 실행)"""
        if self.is_processing_queue:
            return

        self.is_processing_queue = True

        while self.upload_queue and self.retry_count < self.config.max_retry_count:
            frame_data = self.upload_queue.pop(0)

            try:
                # 재시도 업로드
                if IS_WEB:
                    asyncio.create_task(self.upload_game_frame(frame_data))
                else:
                    result = asyncio.run(self.upload_game_frame(frame_data))
                    if result:
                        self.retry_count = 0  # 성공 시 재시도 카운트 리셋
                    else:
                        self.retry_count += 1

            except Exception as e:
                print(f"❌ 재시도 업로드 실패: {e}")
                self.retry_count += 1

            # 재시도 간격
            time.sleep(1 * self.retry_count)

        self.is_processing_queue = False

    async def end_game_session(self):
        """게임 세션 종료"""
        try:
            # 자동 업로드 중단
            if self.is_auto_uploading:
                self.stop_auto_upload.set()
                if self.auto_upload_thread:
                    self.auto_upload_thread.join(timeout=5)
                self.is_auto_uploading = False

            # 남은 큐 처리
            if self.upload_queue:
                print(f"📤 남은 {len(self.upload_queue)}개 프레임 업로드 중...")
                self._process_retry_queue()

            # 세션 통계 출력
            if self.current_session_id:
                duration = datetime.now() - self.stats["session_start_time"]
                print(f"✅ 게임 세션 종료: {self.current_session_id}")
                print(f"   세션 시간: {duration}")
                print(f"   캡처된 프레임: {self.stats['total_frames_captured']}")
                print(f"   업로드된 프레임: {self.stats['total_frames_uploaded']}")
                print(f"   업로드 실패: {self.stats['total_upload_failures']}")

                # 성공률 계산
                if self.stats["total_frames_captured"] > 0:
                    success_rate = (
                        self.stats["total_frames_uploaded"]
                        / self.stats["total_frames_captured"]
                    ) * 100
                    print(f"   업로드 성공률: {success_rate:.1f}%")

                self.current_session_id = None

        except Exception as e:
            print(f"❌ 세션 종료 중 오류: {e}")

    def set_frame_capture_callback(self, callback: Callable[[], GameFrameData]):
        """프레임 캡처 콜백 설정"""
        self.frame_capture_callback = callback

    def set_should_upload_callback(self, callback: Callable[[GameFrameData], bool]):
        """업로드 필요 여부 판단 콜백 설정"""
        self.should_upload_callback = callback

    def get_stats(self) -> Dict[str, Any]:
        """현재 통계 반환"""
        current_stats = self.stats.copy()
        if self.stats["session_start_time"]:
            current_stats["session_duration"] = str(
                datetime.now() - self.stats["session_start_time"]
            )
        return current_stats

    async def upload_legacy_data(
        self,
        game_screen_base64: str,
        labeling_code: str,
        metadata: Optional[Dict] = None,
    ) -> Optional[str]:
        """
        레거시 형식으로 데이터 업로드 (기존 코드와 호환)

        Args:
            game_screen_base64: 게임 화면 base64 인코딩
            labeling_code: 라벨링 코드
            metadata: 추가 메타데이터

        Returns:
            str: 업로드된 데이터 ID 또는 None
        """
        try:
            # 메타데이터에 세션 정보 추가
            upload_metadata = metadata or {}
            upload_metadata.update(
                {
                    "session_id": self.current_session_id,
                    "timestamp": datetime.now().isoformat(),
                    "uploaded_by": "legacy_client",
                }
            )

            # 임시 파일로 저장 후 업로드
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as img_file:
                img_data = base64.b64decode(game_screen_base64)
                img_file.write(img_data)
                img_path = img_file.name

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            ) as label_file:
                label_file.write(labeling_code)
                label_path = label_file.name

            try:
                result = await self.server_client.upload_game_data(
                    img_path, label_path, upload_metadata
                )
                print(f"✅ 레거시 데이터 업로드 완료: {result}")
                return result
            finally:
                # 임시 파일 정리
                os.unlink(img_path)
                os.unlink(label_path)

        except Exception as e:
            print(f"❌ 레거시 업로드 실패: {e}")
            return None


# 편의 함수들
async def create_auto_client(
    server_url: str = "http://localhost:3000",
    game_id: str = "default_game",
    player_id: str = "default_player",
    **config_kwargs,
) -> RLDDAAutoClient:
    """
    자동 클라이언트 생성 및 세션 시작

    Args:
        server_url: 서버 URL
        game_id: 게임 ID
        player_id: 플레이어 ID
        **config_kwargs: 세션 설정 추가 파라미터

    Returns:
        RLDDAAutoClient: 초기화된 클라이언트
    """
    client = RLDDAAutoClient(server_url)
    config = GameSessionConfig(game_id=game_id, player_id=player_id, **config_kwargs)
    await client.start_game_session(game_id, player_id, config)
    return client


def create_auto_client_sync(
    server_url: str = "http://localhost:3000",
    game_id: str = "default_game",
    player_id: str = "default_player",
    **config_kwargs,
) -> RLDDAAutoClient:
    """
    자동 클라이언트 생성 및 세션 시작 (동기 버전)

    Args:
        server_url: 서버 URL
        game_id: 게임 ID
        player_id: 플레이어 ID
        **config_kwargs: 세션 설정 추가 파라미터

    Returns:
        RLDDAAutoClient: 초기화된 클라이언트
    """
    try:
        return asyncio.run(
            create_auto_client(server_url, game_id, player_id, **config_kwargs)
        )
    except Exception as e:
        print(f"❌ 동기 클라이언트 생성 실패: {e}")
        raise
