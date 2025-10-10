"""
게임 이벤트 전용 로거

게임에서 발생하는 실제 이벤트들(frame data, entity events 등)을
구조화된 방식으로 처리하고 출력하는 모듈입니다.
기존 print(json.dumps(...)) 패턴을 logger.print(...) 형태로 통합합니다.
"""

import json
import time
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, Optional, Union
from pathlib import Path


@dataclass
class Position:
    """위치 정보"""

    x: float
    y: float


@dataclass
class PlayerHp:
    """플레이어 체력 정보"""

    current: int
    max: int


@dataclass
class PlayerData:
    """플레이어 데이터"""

    lives: int
    score: int
    stage: str
    hp: Optional[PlayerHp] = None


@dataclass
class FrameEventData:
    """프레임 수집 이벤트 데이터"""

    type: str = "event"
    event: str = "frame_collected"
    timestamp: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class EntityEventData:
    """엔티티 이벤트 데이터"""

    type: str = "entity"
    event: str = ""  # enemy_created, boss_created, enemy_destroyed
    timestamp: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


class GameEventLogger:
    """게임 이벤트 전용 로거

    게임에서 발생하는 이벤트들을 구조화된 방식으로 출력하고 관리합니다.
    기존 print(json.dumps(...)) 패턴을 대체합니다.
    """

    def __init__(
        self,
        enable_console: bool = True,
        enable_file: bool = False,
        output_dir: Optional[str] = None,
        namespace: str = "game_events",
    ):
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.namespace = namespace

        # 출력 디렉토리 설정
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path("data") / namespace

        if self.enable_file:
            self.output_dir.mkdir(parents=True, exist_ok=True)

        # 이벤트 저장소
        self.events = []

    def print_frame_data(
        self, player_data: PlayerData, additional_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """프레임 데이터 출력

        Args:
            player_data: 플레이어 데이터
            additional_data: 추가 데이터
        """
        frame_event = FrameEventData()
        frame_event.data["player"] = self._to_dict(player_data)

        if additional_data:
            frame_event.data.update(additional_data)

        self._output_event(frame_event)

    def print_entity_created(
        self,
        entity_type: str,
        position: Position,
        is_boss: bool = False,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """엔티티 생성 이벤트 출력

        Args:
            entity_type: 엔티티 타입 (클래스명)
            position: 생성 위치
            is_boss: 보스 여부
            additional_data: 추가 데이터
        """
        event_name = "boss_created" if is_boss else "enemy_created"
        entity_event = EntityEventData(event=event_name)

        entity_event.data = {
            "entity_type": entity_type,
            "position": self._to_dict(position),
        }

        if additional_data:
            entity_event.data.update(additional_data)

        self._output_event(entity_event)

    def print_entity_destroyed(
        self,
        entity_type: str,
        position: Position,
        reason: str = "unknown",
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """엔티티 파괴 이벤트 출력

        Args:
            entity_type: 엔티티 타입
            position: 파괴 위치
            reason: 파괴 사유
            additional_data: 추가 데이터
        """
        entity_event = EntityEventData(event="enemy_destroyed")

        entity_event.data = {
            "entity_type": entity_type,
            "position": self._to_dict(position),
            "reason": reason,
        }

        if additional_data:
            entity_event.data.update(additional_data)

        self._output_event(entity_event)

    def print_custom_event(
        self,
        event_type: str,
        event_name: str,
        data: Dict[str, Any],
        timestamp: Optional[float] = None,
    ) -> None:
        """커스텀 이벤트 출력

        Args:
            event_type: 이벤트 타입 (event, entity, system 등)
            event_name: 이벤트 이름
            data: 이벤트 데이터
            timestamp: 타임스탬프 (None이면 자동 생성)
        """
        if timestamp is None:
            timestamp = time.time()

        event_data = {
            "type": event_type,
            "event": event_name,
            "timestamp": timestamp,
            "data": data,
        }

        self._output_event(event_data)

    def _to_dict(self, obj: Any) -> Dict[str, Any]:
        """dataclass 객체를 dict로 변환"""
        try:
            return asdict(obj)
        except Exception:
            # asdict 실패 시 기본 dict 변환
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            return {}

    def _output_event(
        self, event_data: Union[FrameEventData, EntityEventData, Dict]
    ) -> None:
        """이벤트 출력 처리

        Args:
            event_data: 출력할 이벤트 데이터
        """
        # dataclass를 dict로 변환
        if isinstance(event_data, dict):
            event_dict = event_data
        else:
            # dataclass인지 확인하고 변환
            if hasattr(event_data, "__dataclass_fields__"):
                try:
                    event_dict = asdict(event_data)
                except Exception:
                    # asdict 실패 시 기본 변환
                    event_dict = {
                        "type": getattr(event_data, "type", "unknown"),
                        "event": getattr(event_data, "event", "unknown"),
                        "timestamp": getattr(event_data, "timestamp", time.time()),
                        "data": getattr(event_data, "data", {}),
                    }
            else:
                # dataclass가 아닌 경우 기본 변환
                event_dict = {
                    "type": getattr(event_data, "type", "unknown"),
                    "event": getattr(event_data, "event", "unknown"),
                    "timestamp": getattr(event_data, "timestamp", time.time()),
                    "data": getattr(event_data, "data", {}),
                }

        # 이벤트 저장
        self.events.append(event_dict)

        # 콘솔 출력
        if self.enable_console:
            print(json.dumps(event_dict, ensure_ascii=False))

        # 파일 출력
        if self.enable_file:
            self._save_to_file(event_dict)

    def _save_to_file(self, event_dict: Dict[str, Any]) -> None:
        """파일에 이벤트 저장"""
        try:
            file_path = self.output_dir / f"{self.namespace}_events.json"

            # 파일이 존재하면 기존 데이터 읽기
            existing_events = []
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        existing_events = json.load(f)
                except (json.JSONDecodeError, FileNotFoundError):
                    existing_events = []

            # 새 이벤트 추가
            existing_events.append(event_dict)

            # 파일에 저장
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(existing_events, f, ensure_ascii=False, indent=2)

        except Exception as e:
            # 파일 저장 실패 시 무시 (콘솔 출력은 계속)
            pass

    def get_statistics(self) -> Dict[str, Any]:
        """이벤트 통계 반환"""
        event_types = {}
        for event in self.events:
            # 모든 이벤트는 dict로 저장되므로 .get() 사용 가능
            event_type = event.get("type", "unknown")
            event_name = event.get("event", "unknown")
            key = f"{event_type}_{event_name}"
            event_types[key] = event_types.get(key, 0) + 1

        return {
            "namespace": self.namespace,
            "total_events": len(self.events),
            "event_types": event_types,
            "output_dir": str(self.output_dir) if self.enable_file else None,
        }

    def clear_events(self) -> None:
        """저장된 이벤트 클리어"""
        self.events.clear()


# 전역 게임 이벤트 로거 인스턴스
_game_logger: Optional[GameEventLogger] = None


def setup_game_logger(
    enable_console: bool = True,
    enable_file: bool = False,
    output_dir: Optional[str] = None,
    namespace: str = "game_events",
) -> GameEventLogger:
    """게임 이벤트 로거 설정"""
    global _game_logger
    _game_logger = GameEventLogger(
        enable_console=enable_console,
        enable_file=enable_file,
        output_dir=output_dir,
        namespace=namespace,
    )
    return _game_logger


def get_game_logger() -> GameEventLogger:
    """전역 게임 이벤트 로거 반환"""
    global _game_logger
    if _game_logger is None:
        _game_logger = GameEventLogger()
    return _game_logger  # type: ignore


# 편의 함수들
def log_frame_data(
    player_data: PlayerData, additional_data: Optional[Dict[str, Any]] = None
) -> None:
    """프레임 데이터 로그 (전역 로거 사용)"""
    get_game_logger().print_frame_data(player_data, additional_data)


def log_entity_created(
    entity_type: str, position: Position, is_boss: bool = False, **kwargs
) -> None:
    """엔티티 생성 로그 (전역 로거 사용)"""
    get_game_logger().print_entity_created(entity_type, position, is_boss, kwargs)


def log_entity_destroyed(
    entity_type: str, position: Position, reason: str = "unknown", **kwargs
) -> None:
    """엔티티 파괴 로그 (전역 로거 사용)"""
    get_game_logger().print_entity_destroyed(entity_type, position, reason, kwargs)


def log_custom_event(
    event_type: str,
    event_name: str,
    data: Dict[str, Any],
    timestamp: Optional[float] = None,
) -> None:
    """커스텀 이벤트 로그 (전역 로거 사용)"""
    get_game_logger().print_custom_event(event_type, event_name, data, timestamp)
