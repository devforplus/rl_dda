"""
Pyxel 게임 데이터 수집을 위한 CLI 인터페이스

Simple Pyxel Collector를 사용하여 웹 기반 Pyxel 게임에서 데이터를 수집합니다.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from loguru import logger

# 기존 EventLogger import 제거
sys.path.append(str(Path(__file__).parent.parent.parent))


# Loguru 설정
def setup_logging(namespace: str, verbose: bool = False):
    """Loguru 기반 로깅 설정

    Args:
        namespace: 로그 파일 네임스페이스
        verbose: 상세 로그 여부

    ---

    Loguru 기반의 로깅을 설정합니다.
    """
    # 기본 핸들러 제거
    logger.remove()

    # 콘솔 로그 설정
    log_level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{extra[source]}</cyan> | <level>{message}</level>",
        colorize=True,
    )

    # 파일 로그 설정
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_dir / f"{namespace}.log",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[source]} | {message}",
        rotation="10 MB",
        retention="7 days",
        encoding="utf-8",
    )

    return logger.bind(source="cli")


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
    cli_logger = setup_logging(
        namespace=f"cli-{args.namespace}", verbose=args.verbose or args.debug
    )

    # 출력 디렉토리 생성 (data/{namespace}/ 구조)
    output_dir = Path(f"data/{args.namespace}")
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        cli_logger.info(f"📁 출력 디렉토리 생성: {output_dir}")

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

    cli_logger.info("🎮 Pyxel 데이터 수집 시작...")
    cli_logger.info(f"   URL: {args.url}")
    cli_logger.info(f"   네임스페이스: {args.namespace}")
    cli_logger.info(f"   출력 디렉토리: data/{args.namespace}/")
    if args.duration is not None:
        cli_logger.info(f"   수집 시간: {args.duration}초")
    else:
        cli_logger.info("   수집 시간: 무한 (Ctrl+C로 종료)")
    cli_logger.info(f"   헤드리스 모드: {'ON' if args.headless else 'OFF'}")
    cli_logger.info(f"   상세 로그: {'ON' if args.verbose else 'OFF'}")
    cli_logger.info(f"   Raw 데이터 저장: {'ON' if args.save_raw else 'OFF'}")
    cli_logger.info(f"   모든 console.* 수집: {'ON' if args.collect_all else 'OFF'}")
    print()

    try:
        # Simple Pyxel Collector 실행
        result = subprocess.run(command, check=True)
        cli_logger.info(f"\n✅ 데이터 수집이 완료되었습니다: data/{args.namespace}/")
        return result.returncode

    except subprocess.CalledProcessError as e:
        cli_logger.error(f"\n❌ 데이터 수집 중 오류가 발생했습니다: {e}")
        return e.returncode

    except FileNotFoundError:
        cli_logger.error("\n❌ Simple Pyxel Collector를 찾을 수 없습니다.")
        cli_logger.error(
            "scripts/cli/simple_pyxel_collector.py 파일이 존재하는지 확인해주세요."
        )
        return 1

    except KeyboardInterrupt:
        cli_logger.warning("\n⚠️ 사용자에 의해 중단되었습니다.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
