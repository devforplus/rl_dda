"""
Pyxel 게임 데이터 수집을 위한 CLI 인터페이스

Simple Pyxel Collector를 사용하여 웹 기반 Pyxel 게임에서 데이터를 수집합니다.
"""

import argparse
import subprocess
import sys
from pathlib import Path

# EventLogger import 추가
sys.path.append(str(Path(__file__).parent.parent.parent))
from .utils.event_logger import EventLogger, LogLevel, EventType, setup_logger


def main():
    """Pyxel 데이터 수집 CLI 메인 함수"""
    parser = argparse.ArgumentParser(
        description="🎮 Pyxel 게임 데이터 수집기 v2.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 기본 수집 (무한 모드 - Ctrl+C로 종료)
  python -m scripts.cli --url http://localhost:5176/ --namespace my-game

  # 시간 제한 수집
  python -m scripts.cli --url http://localhost:5176/ --namespace my-game --duration 30

  # 모든 console.* 타입 수집 + Raw 데이터 저장
  python -m scripts.cli --url http://localhost:5176/ --namespace experiment --collect-all --save-raw --verbose
""",
    )

    # 필수 인자
    parser.add_argument(
        "--url",
        default="http://0.0.0.0:5175/test_pyxel",
        help="Pyxel 게임 URL (기본값: http://0.0.0.0:5175/test_pyxel)",
    )

    parser.add_argument(
        "--namespace",
        "-n",
        default="default",
        help="데이터 저장 네임스페이스 (기본값: default)",
    )

    # 선택적 인자
    parser.add_argument(
        "--duration",
        type=int,
        help="수집 시간 (초). 지정하지 않으면 무한 수집 모드 (Ctrl+C로 종료)",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="헤드리스 모드로 브라우저 실행",
    )

    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그 출력")

    parser.add_argument("--debug", action="store_true", help="디버그 모드 활성화")

    parser.add_argument(
        "--save-raw", action="store_true", help="Raw console 데이터도 JSON으로 저장"
    )

    parser.add_argument(
        "--collect-all",
        action="store_true",
        help="모든 console.* 타입을 개별 파일로 수집 (기본: log, info만)",
    )

    args = parser.parse_args()

    # 로거 설정
    logger = setup_logger(
        namespace=f"cli-{args.namespace}",
        log_level=LogLevel.DEBUG if args.verbose else LogLevel.INFO,
        enable_console=True,
        enable_file=True,
    )

    # 출력 디렉토리 생성 (data/{namespace}/ 구조)
    output_dir = Path(f"data/{args.namespace}")
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(
            f"📁 출력 디렉토리 생성: {output_dir}",
            source="cli",
            event_type=EventType.SYSTEM,
        )

    # 수집기 실행을 위한 명령 구성
    command = [
        sys.executable,
        "scripts/cli/simple_pyxel_collector.py",
        "--url",
        args.url,
        "--namespace",
        args.namespace,
    ]

    # duration이 지정된 경우에만 추가
    if args.duration is not None:
        command.extend(["--duration", str(args.duration)])

    if args.headless:
        command.append("--headless")
    if args.verbose:
        command.append("--verbose")
    if args.save_raw:
        command.append("--save-raw")
    if args.collect_all:
        command.append("--collect-all")

    logger.info(
        f"🎮 Pyxel 데이터 수집 시작...", source="cli", event_type=EventType.SYSTEM
    )
    logger.info(f"   URL: {args.url}", source="cli", event_type=EventType.SYSTEM)
    logger.info(
        f"   네임스페이스: {args.namespace}", source="cli", event_type=EventType.SYSTEM
    )
    logger.info(
        f"   출력 디렉토리: data/{args.namespace}/",
        source="cli",
        event_type=EventType.SYSTEM,
    )
    if args.duration is not None:
        logger.info(
            f"   수집 시간: {args.duration}초",
            source="cli",
            event_type=EventType.SYSTEM,
        )
    else:
        logger.info(
            f"   수집 시간: 무한 (Ctrl+C로 종료)",
            source="cli",
            event_type=EventType.SYSTEM,
        )
    logger.info(
        f"   헤드리스 모드: {'ON' if args.headless else 'OFF'}",
        source="cli",
        event_type=EventType.SYSTEM,
    )
    logger.info(
        f"   상세 로그: {'ON' if args.verbose else 'OFF'}",
        source="cli",
        event_type=EventType.SYSTEM,
    )
    logger.info(
        f"   Raw 데이터 저장: {'ON' if args.save_raw else 'OFF'}",
        source="cli",
        event_type=EventType.SYSTEM,
    )
    logger.info(
        f"   모든 console.* 수집: {'ON' if args.collect_all else 'OFF'}",
        source="cli",
        event_type=EventType.SYSTEM,
    )
    print()

    try:
        # Simple Pyxel Collector 실행
        result = subprocess.run(command, check=True)
        logger.info(
            f"\n✅ 데이터 수집이 완료되었습니다: data/{args.namespace}/",
            source="cli",
            event_type=EventType.SYSTEM,
        )
        return result.returncode

    except subprocess.CalledProcessError as e:
        logger.error(
            f"\n❌ 데이터 수집 중 오류가 발생했습니다: {e}",
            source="cli",
            event_type=EventType.SYSTEM,
        )
        return e.returncode

    except FileNotFoundError:
        logger.error(
            f"\n❌ Simple Pyxel Collector를 찾을 수 없습니다.",
            source="cli",
            event_type=EventType.SYSTEM,
        )
        logger.error(
            "scripts/cli/simple_pyxel_collector.py 파일이 존재하는지 확인해주세요.",
            source="cli",
            event_type=EventType.SYSTEM,
        )
        return 1

    except KeyboardInterrupt:
        logger.warning(
            f"\n⚠️ 사용자에 의해 중단되었습니다.",
            source="cli",
            event_type=EventType.SYSTEM,
        )
        return 130

    finally:
        # 로거 정리
        logger.cleanup()


if __name__ == "__main__":
    sys.exit(main())
