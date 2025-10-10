"""
EventLogger 사용 예제

게임 개발에서 실제로 사용되는 다양한 로깅 패턴을 보여주는 예제입니다.
성능 측정, 오류 추적, 디버깅 정보 등을 구조화된 방식으로 기록합니다.
"""

import sys
import time
import json
from pathlib import Path

# src 모듈들을 import하기 위한 경로 설정
sys.path.append(str(Path(__file__).parent.parent))

from .utils.event_logger import (
    EventLogger,
    LogLevel,
    EventType,
    LogEvent,
    setup_logger,
    get_logger,
    LoggerContext,
    log_info,
    log_warning,
    log_error,
    log_game_event,
    log_user_event,
)


def basic_logging_example():
    """기본 로깅 사용 예제"""
    print("=" * 60)
    print("🔥 기본 로깅 예제")
    print("=" * 60)

    # 로거 설정
    logger = setup_logger(
        namespace="basic_example",
        log_level=LogLevel.DEBUG,
        enable_console=True,
        enable_file=True,
    )

    # 다양한 로그 레벨 테스트
    logger.debug("디버그 메시지입니다", source="test_app")
    logger.info("정보 메시지입니다", source="test_app")
    logger.warning("경고 메시지입니다", source="test_app")
    logger.error("에러 메시지입니다", source="test_app")
    logger.critical("치명적 오류 메시지입니다", source="test_app")

    # 데이터와 함께 로깅
    logger.info(
        "플레이어 상태 업데이트",
        source="game_engine",
        data={
            "player_id": "player_001",
            "position": {"x": 150, "y": 200},
            "health": 85,
            "score": 12300,
        },
    )

    print(f"\n📊 로그 통계: {logger.get_statistics()}")

    # 정리
    logger.cleanup()


def event_type_example():
    """이벤트 타입별 로깅 예제"""
    print("=" * 60)
    print("🎮 이벤트 타입별 로깅 예제")
    print("=" * 60)

    logger = setup_logger(
        namespace="event_type_example",
        log_level=LogLevel.INFO,
        enable_console=True,
        enable_file=True,
    )

    # 시스템 이벤트
    logger.info("애플리케이션 시작", source="system", event_type=EventType.SYSTEM)

    # 게임 이벤트
    logger.game_event(
        "새 레벨 시작", source="level_manager", data={"level": 3, "difficulty": "hard"}
    )
    logger.game_event(
        "적 처치", source="combat_system", data={"enemy_type": "boss", "reward": 500}
    )

    # 사용자 이벤트
    logger.user_event(
        "키 입력", source="input_handler", data={"key": "SPACE", "action": "shoot"}
    )
    logger.user_event("화면 클릭", source="mouse_handler", data={"x": 320, "y": 240})

    # 네트워크 이벤트
    logger.network_event(
        "서버 연결",
        source="network_client",
        data={"server": "game.example.com", "port": 8080},
    )

    # 데이터 수집 이벤트
    logger.data_event(
        "게임 데이터 저장",
        source="data_collector",
        data={"file_count": 15, "size_mb": 2.3},
    )

    # 성능 이벤트
    logger.performance_event(
        "프레임레이트 체크",
        source="performance_monitor",
        data={"fps": 58.2, "frame_time_ms": 17.1},
    )

    print(f"\n📊 로그 통계: {logger.get_statistics()}")

    # 정리
    logger.cleanup()


def callback_example():
    """콜백 기능 예제"""
    print("=" * 60)
    print("📞 콜백 기능 예제")
    print("=" * 60)

    # 콜백 함수들 정의
    def error_alert_callback(event: LogEvent):
        """에러 발생 시 알림"""
        if event.level == LogLevel.ERROR or event.level == LogLevel.CRITICAL:
            print(f"🚨 [알림] 심각한 이벤트 감지: {event.message}")

    def game_stats_callback(event: LogEvent):
        """게임 통계 수집"""
        if event.event_type == EventType.GAME and event.data:
            if "score" in str(event.data):
                print(f"📈 [게임 통계] 점수 이벤트: {event.data}")

    # 로거 설정
    logger = setup_logger(
        namespace="callback_example",
        log_level=LogLevel.INFO,
        enable_console=True,
        enable_file=True,
    )

    # 콜백 등록
    logger.add_event_callback(error_alert_callback)
    logger.add_event_callback(game_stats_callback)

    # 다양한 이벤트 발생
    logger.info("게임 시작", source="game_manager")
    logger.game_event(
        "점수 획득", source="score_system", data={"score": 1000, "bonus": True}
    )
    logger.warning(
        "메모리 사용량 높음", source="memory_monitor", data={"usage_percent": 85}
    )
    logger.error("파일 로드 실패", source="asset_loader", data={"file": "texture.png"})
    logger.game_event(
        "레벨 완료", source="level_manager", data={"score": 5000, "time": 120}
    )

    print(f"\n📊 로그 통계: {logger.get_statistics()}")

    # 정리
    logger.cleanup()


def context_manager_example():
    """컨텍스트 매니저 사용 예제"""
    print("=" * 60)
    print("🔄 컨텍스트 매니저 예제")
    print("=" * 60)

    # 컨텍스트 매니저로 자동 정리
    with LoggerContext(
        namespace="context_example",
        log_level=LogLevel.INFO,
        enable_console=True,
        enable_file=True,
    ) as logger:
        logger.info("컨텍스트 내에서 로깅", source="context_test")
        logger.game_event(
            "임시 게임 세션", source="temp_session", data={"duration": 30}
        )
        logger.warning("컨텍스트 종료 예정", source="context_test")

        print(f"📊 컨텍스트 내 통계: {logger.get_statistics()}")

    print("✅ 컨텍스트 매니저가 자동으로 정리를 완료했습니다!")


def global_logger_example():
    """전역 로거 사용 예제"""
    print("=" * 60)
    print("🌐 전역 로거 예제")
    print("=" * 60)

    # 전역 로거 설정
    setup_logger(
        namespace="global_example",
        log_level=LogLevel.INFO,
        enable_console=True,
        enable_file=True,
    )

    # 편의 함수들 사용
    log_info("전역 로거로 정보 로그", source="global_test", event_type=EventType.SYSTEM)
    log_warning(
        "전역 로거로 경고 로그", source="global_test", event_type=EventType.SYSTEM
    )
    log_error(
        "전역 로거로 에러 로그", source="global_test", event_type=EventType.SYSTEM
    )

    log_game_event("전역 게임 이벤트", source="global_game", data={"action": "jump"})
    log_user_event(
        "전역 사용자 이벤트", source="global_user", data={"input": "keyboard"}
    )

    # 전역 로거 가져오기
    logger = get_logger()
    print(f"📊 전역 로거 통계: {logger.get_statistics()}")

    # 정리
    logger.cleanup()


def filtering_export_example():
    """필터링 및 내보내기 예제"""
    print("=" * 60)
    print("🔍 필터링 및 내보내기 예제")
    print("=" * 60)

    logger = setup_logger(
        namespace="filtering_example",
        log_level=LogLevel.DEBUG,
        enable_console=True,
        enable_file=True,
    )

    # 다양한 이벤트 생성
    for i in range(10):
        logger.debug(f"디버그 메시지 {i}", source="debug_source")
        logger.info(f"정보 메시지 {i}", source="info_source")
        logger.game_event(f"게임 이벤트 {i}", source="game_source", data={"round": i})
        logger.user_event(
            f"사용자 이벤트 {i}", source="user_source", data={"action": f"action_{i}"}
        )
        if i % 3 == 0:
            logger.warning(f"경고 메시지 {i}", source="warning_source")
        if i % 5 == 0:
            logger.error(f"에러 메시지 {i}", source="error_source")

    # 게임 이벤트만 필터링하여 내보내기
    game_events_file = logger.export_events(
        output_file="data/filtering_example/game_events_only.json",
        event_types=[EventType.GAME],
    )
    print(f"📁 게임 이벤트만 저장됨: {game_events_file}")

    # 에러와 경고만 필터링하여 내보내기
    error_warnings_file = logger.export_events(
        output_file="data/filtering_example/errors_warnings.json",
        log_levels=[LogLevel.WARNING, LogLevel.ERROR],
    )
    print(f"📁 에러와 경고만 저장됨: {error_warnings_file}")

    # 게임 이벤트 중 에러만 필터링
    game_errors_file = logger.export_events(
        output_file="data/filtering_example/game_errors.json",
        event_types=[EventType.GAME],
        log_levels=[LogLevel.ERROR],
    )
    print(f"📁 게임 에러만 저장됨: {game_errors_file}")

    print(f"\n📊 최종 통계: {logger.get_statistics()}")

    # 정리
    logger.cleanup()


def real_game_scenario_example():
    """실제 게임 시나리오 예제"""
    print("=" * 60)
    print("🎯 실제 게임 시나리오 예제")
    print("=" * 60)

    logger = setup_logger(
        namespace="game_scenario",
        log_level=LogLevel.INFO,
        enable_console=True,
        enable_file=True,
    )

    # 게임 시작
    logger.info("게임 엔진 초기화", source="engine", event_type=EventType.SYSTEM)
    logger.info("리소스 로딩 시작", source="asset_manager", event_type=EventType.SYSTEM)

    # 플레이어 관련 이벤트
    logger.game_event(
        "플레이어 생성",
        source="player_manager",
        data={
            "player_id": "player_001",
            "name": "TestPlayer",
            "starting_position": {"x": 100, "y": 100},
        },
    )

    # 게임플레이 시뮬레이션
    for frame in range(1, 6):
        # 사용자 입력
        if frame % 2 == 0:
            logger.user_event(
                "키 입력",
                source="input_system",
                data={"frame": frame, "key": "SPACE", "action": "shoot"},
            )

        # 게임 로직
        logger.game_event(
            "프레임 업데이트",
            source="game_loop",
            data={
                "frame": frame,
                "player_pos": {"x": 100 + frame * 10, "y": 100},
                "enemies": frame * 2,
            },
        )

        # 성능 모니터링
        logger.performance_event(
            "프레임 성능",
            source="profiler",
            data={
                "frame": frame,
                "fps": 60.0 - frame * 0.5,
                "memory_mb": 128 + frame * 5,
            },
        )

        # 가끔 경고나 에러
        if frame == 3:
            logger.warning(
                "메모리 사용량 증가",
                source="memory_monitor",
                data={"current_mb": 145, "threshold_mb": 150},
            )

        if frame == 5:
            logger.error(
                "네트워크 연결 끊김",
                source="network_client",
                data={"error_code": "CONN_LOST", "retry_attempt": 1},
            )

        time.sleep(0.1)  # 시뮬레이션을 위한 짧은 대기

    # 게임 종료
    logger.game_event(
        "게임 세션 종료",
        source="session_manager",
        data={"duration_seconds": 30, "final_score": 8500, "reason": "player_quit"},
    )

    logger.info(
        "게임 데이터 저장 완료", source="save_system", event_type=EventType.DATA
    )
    logger.info("게임 엔진 종료", source="engine", event_type=EventType.SYSTEM)

    # 최종 통계
    stats = logger.get_statistics()
    print(f"\n📊 게임 세션 통계:")
    print(f"   총 이벤트: {stats['total_events']}개")
    print(f"   세션 시간: {stats['start_time']} ~ {stats['last_event_time']}")
    print(f"   이벤트 타입별:")
    for event_type, count in stats["event_counts"].items():
        print(f"     {event_type}: {count}개")

    # 정리
    logger.cleanup()


def main():
    """모든 예제 실행"""
    print("🚀 EventLogger 종합 예제 시작\n")

    try:
        basic_logging_example()
        print("\n")

        event_type_example()
        print("\n")

        callback_example()
        print("\n")

        context_manager_example()
        print("\n")

        global_logger_example()
        print("\n")

        filtering_export_example()
        print("\n")

        real_game_scenario_example()

        print("\n" + "=" * 60)
        print("✅ 모든 예제가 성공적으로 완료되었습니다!")
        print("📁 생성된 로그 파일들을 data/ 디렉토리에서 확인하세요.")
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 예제 실행 중 오류: {e}")


if __name__ == "__main__":
    main()
