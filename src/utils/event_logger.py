"""
이벤트 로그 처리 모듈

게임 이벤트, 시스템 이벤트, 콘솔 메시지 등을 구조화된 방식으로 처리하는 모듈입니다.
실시간 출력, 파일 저장, 이벤트 분류, 로그 레벨 관리 등의 기능을 제공합니다.
"""

import json
import time
import threading
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass


class LogLevel(Enum):
    """로그 레벨 정의"""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @property
    def priority(self) -> int:
        """로그 레벨 우선순위"""
        priorities = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50,
        }
        return priorities[self]


class EventType(Enum):
    """이벤트 타입 정의"""

    SYSTEM = "SYSTEM"  # 시스템 이벤트
    GAME = "GAME"  # 게임 이벤트
    USER = "USER"  # 사용자 이벤트
    CONSOLE = "CONSOLE"  # 콘솔 메시지
    NETWORK = "NETWORK"  # 네트워크 이벤트
    DATA = "DATA"  # 데이터 수집 이벤트
    PERFORMANCE = "PERFORMANCE"  # 성능 관련 이벤트


@dataclass
class LogEvent:
    """로그 이벤트 데이터 클래스"""

    timestamp: str
    level: LogLevel
    event_type: EventType
    message: str
    source: str
    data: Optional[Dict[str, Any]] = None
    session_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "timestamp": self.timestamp,
            "level": self.level.value,
            "event_type": self.event_type.value,
            "message": self.message,
            "source": self.source,
            "data": self.data,
            "session_id": self.session_id,
        }

    def to_console_format(self) -> str:
        """콘솔 출력용 포맷"""
        emoji_map = {
            LogLevel.DEBUG: "🔍",
            LogLevel.INFO: "ℹ️",
            LogLevel.WARNING: "⚠️",
            LogLevel.ERROR: "❌",
            LogLevel.CRITICAL: "🚨",
        }

        emoji = emoji_map.get(self.level, "📝")
        time_str = self.timestamp.split("T")[1].split(".")[0]  # HH:MM:SS만 추출

        # 데이터가 있으면 간단히 표시
        data_info = ""
        if self.data:
            data_info = f" | {json.dumps(self.data, ensure_ascii=False)[:50]}"
            if len(json.dumps(self.data, ensure_ascii=False)) > 50:
                data_info += "..."

        return (
            f"[{time_str}] {emoji} [{self.event_type.value}] {self.message}{data_info}"
        )


class EventLogger:
    """이벤트 로깅 시스템"""

    def __init__(
        self,
        namespace: str = "default",
        log_level: LogLevel = LogLevel.INFO,
        enable_console: bool = True,
        enable_file: bool = True,
        output_dir: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.namespace = namespace
        self.log_level = log_level
        self.enable_console = enable_console
        self.enable_file = enable_file
        self.session_id = session_id or self._generate_session_id()

        # 출력 디렉토리 설정
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path("data") / namespace

        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 로그 저장소
        self.events: List[LogEvent] = []
        self.event_counts: Dict[str, int] = {}

        # 파일 핸들러들
        self.file_handlers: Dict[str, Any] = {}
        self._lock = threading.Lock()

        # 실시간 콜백
        self.event_callbacks: List[Callable[[LogEvent], None]] = []

        # 파일 초기화
        if self.enable_file:
            self._setup_file_handlers()

    def _generate_session_id(self) -> str:
        """세션 ID 생성"""
        return f"session_{int(time.time())}"

    def _setup_file_handlers(self) -> None:
        """파일 핸들러 설정 (동적 생성 방식)"""
        if not self.enable_file:
            return

        # 출력 디렉토리 생성
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 메인 로그 파일 (항상 생성)
        main_log_file = self.output_dir / "events.log"
        self.file_handlers["main"] = open(main_log_file, "w", encoding="utf-8")

        # JSON 로그 파일 (항상 생성)
        json_log_file = self.output_dir / "events.json"
        self.file_handlers["json"] = open(json_log_file, "w", encoding="utf-8")

        # 이벤트 타입별 파일들은 동적 생성으로 변경
        # (실제 데이터가 있을 때만 생성됨)

    def _get_or_create_type_file_handler(self, event_type: EventType):
        """이벤트 타입별 파일 핸들러를 동적으로 생성"""
        type_key = event_type.value

        if type_key not in self.file_handlers:
            type_file = self.output_dir / f"events_{event_type.value.lower()}.log"
            self.file_handlers[type_key] = open(type_file, "w", encoding="utf-8")

        return self.file_handlers[type_key]

    def add_event_callback(self, callback: Callable[[LogEvent], None]) -> None:
        """이벤트 콜백 추가"""
        self.event_callbacks.append(callback)

    def remove_event_callback(self, callback: Callable[[LogEvent], None]) -> None:
        """이벤트 콜백 제거"""
        if callback in self.event_callbacks:
            self.event_callbacks.remove(callback)

    def log(
        self,
        level: LogLevel,
        event_type: EventType,
        message: str,
        source: str = "unknown",
        data: Optional[Dict[str, Any]] = None,
    ) -> Optional[LogEvent]:
        """로그 이벤트 기록"""
        # 로그 레벨 필터링
        if level.priority < self.log_level.priority:
            return None

        # 이벤트 생성
        event = LogEvent(
            timestamp=datetime.now().isoformat(),
            level=level,
            event_type=event_type,
            message=message,
            source=source,
            data=data,
            session_id=self.session_id,
        )

        with self._lock:
            # 이벤트 저장
            self.events.append(event)

            # 카운트 업데이트
            count_key = f"{event_type.value}_{level.value}"
            self.event_counts[count_key] = self.event_counts.get(count_key, 0) + 1

            # 콘솔 출력
            if self.enable_console:
                print(event.to_console_format())

            # 파일 저장
            if self.enable_file:
                self._write_to_files(event)

            # 콜백 실행
            for callback in self.event_callbacks:
                try:
                    callback(event)
                except Exception as e:
                    # 콜백 에러는 무시하고 계속 진행
                    pass

        return event

    def _write_to_files(self, event: LogEvent) -> None:
        """파일에 이벤트 기록 (동적 파일 생성 적용)"""
        try:
            # 메인 로그 파일
            if "main" in self.file_handlers:
                self.file_handlers["main"].write(event.to_console_format() + "\n")
                self.file_handlers["main"].flush()

            # JSON 로그 파일
            if "json" in self.file_handlers:
                json.dump(
                    event.to_dict(), self.file_handlers["json"], ensure_ascii=False
                )
                self.file_handlers["json"].write("\n")
                self.file_handlers["json"].flush()

            # 이벤트 타입별 파일 (동적 생성)
            type_handler = self._get_or_create_type_file_handler(event.event_type)
            type_handler.write(event.to_console_format() + "\n")
            type_handler.flush()

        except Exception as e:
            # 파일 쓰기 에러는 콘솔에 출력하고 계속 진행
            print(f"파일 쓰기 에러: {e}")

    # 편의 메서드들
    def debug(
        self,
        message: str,
        source: str = "debug",
        event_type: EventType = EventType.SYSTEM,
        data: Optional[Dict] = None,
    ) -> Optional[LogEvent]:
        return self.log(LogLevel.DEBUG, event_type, message, source, data)

    def info(
        self,
        message: str,
        source: str = "info",
        event_type: EventType = EventType.SYSTEM,
        data: Optional[Dict] = None,
    ) -> Optional[LogEvent]:
        return self.log(LogLevel.INFO, event_type, message, source, data)

    def warning(
        self,
        message: str,
        source: str = "warning",
        event_type: EventType = EventType.SYSTEM,
        data: Optional[Dict] = None,
    ) -> Optional[LogEvent]:
        return self.log(LogLevel.WARNING, event_type, message, source, data)

    def error(
        self,
        message: str,
        source: str = "error",
        event_type: EventType = EventType.SYSTEM,
        data: Optional[Dict] = None,
    ) -> Optional[LogEvent]:
        return self.log(LogLevel.ERROR, event_type, message, source, data)

    def critical(
        self,
        message: str,
        source: str = "critical",
        event_type: EventType = EventType.SYSTEM,
        data: Optional[Dict] = None,
    ) -> Optional[LogEvent]:
        return self.log(LogLevel.CRITICAL, event_type, message, source, data)

    # 게임 이벤트 전용 메서드들
    def game_event(
        self,
        message: str,
        source: str = "game",
        level: LogLevel = LogLevel.INFO,
        data: Optional[Dict] = None,
    ) -> Optional[LogEvent]:
        return self.log(level, EventType.GAME, message, source, data)

    def user_event(
        self,
        message: str,
        source: str = "user",
        level: LogLevel = LogLevel.INFO,
        data: Optional[Dict] = None,
    ) -> Optional[LogEvent]:
        return self.log(level, EventType.USER, message, source, data)

    def console_event(
        self,
        message: str,
        source: str = "console",
        level: LogLevel = LogLevel.INFO,
        data: Optional[Dict] = None,
    ) -> Optional[LogEvent]:
        return self.log(level, EventType.CONSOLE, message, source, data)

    def network_event(
        self,
        message: str,
        source: str = "network",
        level: LogLevel = LogLevel.INFO,
        data: Optional[Dict] = None,
    ) -> Optional[LogEvent]:
        return self.log(level, EventType.NETWORK, message, source, data)

    def data_event(
        self,
        message: str,
        source: str = "data_collector",
        level: LogLevel = LogLevel.INFO,
        data: Optional[Dict] = None,
    ) -> Optional[LogEvent]:
        return self.log(level, EventType.DATA, message, source, data)

    def performance_event(
        self,
        message: str,
        source: str = "performance",
        level: LogLevel = LogLevel.INFO,
        data: Optional[Dict] = None,
    ) -> Optional[LogEvent]:
        return self.log(level, EventType.PERFORMANCE, message, source, data)

    def get_statistics(self) -> Dict[str, Any]:
        """로그 통계 정보 반환"""
        return {
            "session_id": self.session_id,
            "namespace": self.namespace,
            "total_events": len(self.events),
            "event_counts": self.event_counts.copy(),
            "log_level": self.log_level.value,
            "output_dir": str(self.output_dir),
            "start_time": self.events[0].timestamp if self.events else None,
            "last_event_time": self.events[-1].timestamp if self.events else None,
        }

    def save_statistics(self) -> None:
        """통계 정보를 파일로 저장"""
        stats_file = self.output_dir / "event_statistics.json"
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(self.get_statistics(), f, ensure_ascii=False, indent=2)

    def export_events(
        self,
        output_file: Optional[str] = None,
        event_types: Optional[List[EventType]] = None,
        log_levels: Optional[List[LogLevel]] = None,
    ) -> str:
        """이벤트를 필터링하여 내보내기"""
        if output_file is None:
            output_file = str(self.output_dir / "filtered_events.json")

        filtered_events = []
        for event in self.events:
            # 이벤트 타입 필터
            if event_types and event.event_type not in event_types:
                continue
            # 로그 레벨 필터
            if log_levels and event.level not in log_levels:
                continue

            filtered_events.append(event.to_dict())

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(filtered_events, f, ensure_ascii=False, indent=2)

        return output_file

    def cleanup(self) -> None:
        """리소스 정리"""
        # 통계 저장
        self.save_statistics()

        # 파일 핸들러 닫기
        for handler in self.file_handlers.values():
            try:
                handler.close()
            except Exception:
                pass

        self.file_handlers.clear()


# 전역 로거 인스턴스 (싱글톤 패턴)
_global_logger: Optional[EventLogger] = None


def get_logger(
    namespace: str = "default", log_level: LogLevel = LogLevel.INFO, **kwargs
) -> EventLogger:
    """전역 로거 인스턴스 가져오기 또는 생성"""
    global _global_logger

    if _global_logger is None or _global_logger.namespace != namespace:
        _global_logger = EventLogger(namespace=namespace, log_level=log_level, **kwargs)

    return _global_logger  # type: ignore


def setup_logger(
    namespace: str = "default", log_level: LogLevel = LogLevel.INFO, **kwargs
) -> EventLogger:
    """로거 설정 및 초기화"""
    global _global_logger

    _global_logger = EventLogger(namespace=namespace, log_level=log_level, **kwargs)

    return _global_logger


# 편의 함수들 (전역 로거 사용)
def log_info(
    message: str,
    source: str = "app",
    event_type: EventType = EventType.SYSTEM,
    data: Optional[Dict] = None,
) -> Optional[LogEvent]:
    """정보 로그 (전역 로거 사용)"""
    return get_logger().info(message, source, event_type, data)


def log_warning(
    message: str,
    source: str = "app",
    event_type: EventType = EventType.SYSTEM,
    data: Optional[Dict] = None,
) -> Optional[LogEvent]:
    """경고 로그 (전역 로거 사용)"""
    return get_logger().warning(message, source, event_type, data)


def log_error(
    message: str,
    source: str = "app",
    event_type: EventType = EventType.SYSTEM,
    data: Optional[Dict] = None,
) -> Optional[LogEvent]:
    """에러 로그 (전역 로거 사용)"""
    return get_logger().error(message, source, event_type, data)


def log_game_event(
    message: str, source: str = "game", data: Optional[Dict] = None
) -> Optional[LogEvent]:
    """게임 이벤트 로그 (전역 로거 사용)"""
    return get_logger().game_event(message, source, data=data)


def log_user_event(
    message: str, source: str = "user", data: Optional[Dict] = None
) -> Optional[LogEvent]:
    """사용자 이벤트 로그 (전역 로거 사용)"""
    return get_logger().user_event(message, source, data=data)


# 컨텍스트 매니저 (자동 정리)
class LoggerContext:
    """로거 컨텍스트 매니저"""

    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.logger: Optional[EventLogger] = None

    def __enter__(self) -> EventLogger:
        self.logger = setup_logger(**self.kwargs)
        return self.logger

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.logger:
            self.logger.cleanup()
