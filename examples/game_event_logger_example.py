"""
GameEventLogger 사용 예제

게임에서 실제로 사용되는 이벤트 로깅 방식을 보여주는 예제입니다.
기존 print(json.dumps(...)) 패턴을 대체하는 구조화된 로깅을 시연합니다.
"""

import sys
import time
from pathlib import Path

# GameEventLogger import
sys.path.append(str(Path(__file__).parent.parent))
from .utils.game_event_logger import (
    GameEventLogger,
    PlayerData,
    PlayerHp,
    Position,
    setup_game_logger,
    get_game_logger,
    log_frame_data,
    log_entity_created,
    log_entity_destroyed,
    log_custom_event,
)


def basic_game_events_example():
    """기본 게임 이벤트 로깅 예제"""
    print("=" * 60)
    print("🎮 기본 게임 이벤트 로깅 예제")
    print("=" * 60)

    # 게임 이벤트 로거 설정
    logger = setup_game_logger(
        enable_console=True, enable_file=True, namespace="basic_game_example"
    )

    # 1. 프레임 데이터 로깅
    print("\n1. 프레임 데이터 로깅:")
    player_data = PlayerData(
        lives=3, score=1250, stage="1-1", hp=PlayerHp(current=85, max=100)
    )

    additional_data = {"image_size_chars": 12345, "yolo_objects_count": 5}

    log_frame_data(player_data, additional_data)

    # 2. 적 생성 이벤트
    print("\n2. 적 생성 이벤트:")
    log_entity_created("EnemyA", Position(120, 50), is_boss=False)
    log_entity_created("BossKnight", Position(128, 40), is_boss=True)

    # 3. 적 파괴 이벤트
    print("\n3. 적 파괴 이벤트:")
    log_entity_destroyed("EnemyA", Position(130, 60), reason="killed_by_player")
    log_entity_destroyed("EnemyB", Position(200, 80), reason="out_of_bounds")

    # 4. 커스텀 이벤트
    print("\n4. 커스텀 이벤트:")
    log_custom_event(
        "system",
        "level_completed",
        {
            "level": "1-1",
            "completion_time": 125.5,
            "final_score": 1250,
            "bonus_points": 500,
        },
    )

    print(f"\n📊 통계: {logger.get_statistics()}")
    return logger


def game_session_simulation():
    """실제 게임 세션 시뮬레이션"""
    print("=" * 60)
    print("🎯 게임 세션 시뮬레이션")
    print("=" * 60)

    # 새 로거 설정
    logger = setup_game_logger(
        enable_console=True, enable_file=True, namespace="game_session_sim"
    )

    print("\n🚀 게임 시작...")

    # 게임 시작
    log_custom_event(
        "system",
        "game_started",
        {"player_name": "TestPlayer", "difficulty": "normal", "stage": "1-1"},
    )

    # 게임플레이 시뮬레이션
    for frame in range(1, 6):
        print(f"\n📼 프레임 {frame}:")

        # 플레이어 상태 업데이트
        player_data = PlayerData(
            lives=3,
            score=frame * 100,
            stage="1-1",
            hp=PlayerHp(current=100 - frame * 5, max=100),
        )

        log_frame_data(
            player_data,
            {"frame_number": frame, "fps": 60.0, "objects_count": frame * 2},
        )

        # 가끔 적 생성
        if frame % 2 == 0:
            enemy_types = ["EnemyA", "EnemyB", "EnemyC"]
            enemy_type = enemy_types[frame % len(enemy_types)]
            log_entity_created(enemy_type, Position(frame * 30, 50), is_boss=False)

        # 적 파괴 (생성 다음 프레임)
        if frame > 1 and frame % 3 == 0:
            log_entity_destroyed(
                "EnemyA", Position(frame * 25, 55), reason="killed_by_player"
            )

        # 특별 이벤트
        if frame == 3:
            log_custom_event(
                "game",
                "powerup_collected",
                {
                    "powerup_type": "speed_boost",
                    "duration": 10.0,
                    "position": {"x": 150, "y": 100},
                },
            )

        time.sleep(0.2)  # 시뮬레이션 딜레이

    # 게임 종료
    log_custom_event(
        "system",
        "game_ended",
        {
            "reason": "level_completed",
            "final_score": 500,
            "duration_seconds": 30,
            "enemies_defeated": 2,
        },
    )

    print(f"\n📊 최종 통계: {logger.get_statistics()}")
    return logger


def logger_comparison_example():
    """기존 방식 vs 새 방식 비교"""
    print("=" * 60)
    print("🔄 로깅 방식 비교")
    print("=" * 60)

    print("\n❌ 기존 방식 (print + json.dumps):")
    print("```python")
    print("print(json.dumps({")
    print('    "type": "entity",')
    print('    "event": "enemy_created",')
    print('    "timestamp": time.time(),')
    print('    "data": {"entity_type": "EnemyA", "position": {"x": 120, "y": 50}}')
    print("}))")
    print("```")

    print("\n✅ 새 방식 (GameEventLogger):")
    print("```python")
    print('log_entity_created("EnemyA", Position(120, 50), is_boss=False)')
    print("```")

    print("\n🎯 장점:")
    print("  • 타입 안전성 (dataclass 사용)")
    print("  • 코드 가독성 향상")
    print("  • 재사용성 증가")
    print("  • 유지보수 용이성")
    print("  • 일관된 출력 형식")
    print("  • 파일 저장 자동화")

    # 실제 비교 시연
    logger = setup_game_logger(
        enable_console=True, enable_file=False, namespace="comparison"
    )

    print("\n📝 실제 출력 비교:")
    print("새 방식으로 출력된 결과:")
    log_entity_created("EnemyA", Position(120, 50), is_boss=False)

    return logger


def file_output_example():
    """파일 출력 기능 예제"""
    print("=" * 60)
    print("📁 파일 출력 기능 예제")
    print("=" * 60)

    # 파일 출력 활성화
    logger = setup_game_logger(
        enable_console=True, enable_file=True, namespace="file_output_test"
    )

    print("📝 이벤트 생성 중...")

    # 다양한 이벤트 생성
    events_data = [
        ("플레이어 초기화", lambda: log_frame_data(PlayerData(3, 0, "1-1"))),
        ("첫 번째 적 생성", lambda: log_entity_created("EnemyA", Position(100, 50))),
        (
            "보스 등장",
            lambda: log_entity_created("BossKnight", Position(128, 30), is_boss=True),
        ),
        (
            "적 처치",
            lambda: log_entity_destroyed(
                "EnemyA", Position(110, 60), "killed_by_player"
            ),
        ),
        (
            "레벨 클리어",
            lambda: log_custom_event("game", "level_cleared", {"score": 1500}),
        ),
    ]

    for description, event_func in events_data:
        print(f"  • {description}")
        event_func()

    stats = logger.get_statistics()
    print(f"\n📊 총 {stats['total_events']}개 이벤트 생성됨")
    print(f"📁 파일 위치: {stats['output_dir']}")

    if stats["output_dir"]:
        file_path = Path(stats["output_dir"]) / "file_output_test_events.json"
        if file_path.exists():
            print(f"✅ 파일 저장 완료: {file_path}")
            print(f"📏 파일 크기: {file_path.stat().st_size} bytes")
        else:
            print("❌ 파일이 생성되지 않았습니다.")

    return logger


def main():
    """모든 예제 실행"""
    print("🚀 GameEventLogger 종합 예제 시작\n")

    try:
        basic_game_events_example()
        print("\n")

        game_session_simulation()
        print("\n")

        logger_comparison_example()
        print("\n")

        file_output_example()

        print("\n" + "=" * 60)
        print("✅ 모든 예제가 성공적으로 완료되었습니다!")
        print("📁 생성된 로그 파일들을 data/ 디렉토리에서 확인하세요.")
        print(
            "🎯 이제 게임 코드에서 print(json.dumps(...))를 GameEventLogger로 교체할 수 있습니다!"
        )
        print("=" * 60)

    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 예제 실행 중 오류: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
