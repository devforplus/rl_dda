"""
환경 변수 설정 관리 모듈

.env 파일과 환경 변수를 로드하고 타입 변환을 처리합니다.
"""

import os
from typing import Optional, Union
from pathlib import Path

# python-dotenv 임포트 (선택적)
try:
    from dotenv import load_dotenv

    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


# 프로젝트 루트 디렉토리 찾기
def find_project_root() -> Path:
    """프로젝트 루트 디렉토리를 찾습니다."""
    current_dir = Path(__file__).parent
    # pyproject.toml 파일이 있는 디렉토리를 찾을 때까지 상위로 이동
    while current_dir != current_dir.parent:
        if (current_dir / "pyproject.toml").exists():
            return current_dir
        current_dir = current_dir.parent
    return Path.cwd()


# .env 파일 로드
PROJECT_ROOT = find_project_root()
ENV_FILE = PROJECT_ROOT / ".env"

if HAS_DOTENV and ENV_FILE.exists():
    load_dotenv(ENV_FILE)
    print(f"✅ .env 파일 로드됨: {ENV_FILE}")
elif ENV_FILE.exists():
    print(
        f"⚠️  python-dotenv가 설치되지 않음. 수동으로 .env 파일을 확인하세요: {ENV_FILE}"
    )
else:
    print(f"ℹ️  .env 파일이 없음: {ENV_FILE}")


def get_env_bool(key: str, default: bool = False) -> bool:
    """환경 변수를 불린값으로 변환합니다."""
    value = os.getenv(key, "").lower().strip()
    if value in ("true", "1", "yes", "on"):
        return True
    elif value in ("false", "0", "no", "off"):
        return False
    else:
        return default


def get_env_int(key: str, default: int = 0) -> int:
    """환경 변수를 정수로 변환합니다."""
    try:
        return int(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def get_env_float(key: str, default: float = 0.0) -> float:
    """환경 변수를 실수로 변환합니다."""
    try:
        return float(os.getenv(key, str(default)))
    except (ValueError, TypeError):
        return default


def get_env_str(key: str, default: str = "") -> str:
    """환경 변수를 문자열로 가져옵니다."""
    return os.getenv(key, default)


def get_env_path(key: str, default: Optional[str] = None) -> Optional[Path]:
    """환경 변수를 Path 객체로 변환합니다."""
    value = os.getenv(key, default)
    if value:
        path = Path(value)
        # 상대 경로인 경우 프로젝트 루트 기준으로 변환
        if not path.is_absolute():
            path = PROJECT_ROOT / path
        return path
    return None


# ===== 성능 최적화 설정 =====
ENABLE_FAST_CAPTURE = get_env_bool("ENABLE_FAST_CAPTURE", True)
CAPTURE_INTERVAL = get_env_int("CAPTURE_INTERVAL", 5)
ENABLE_PERFORMANCE_LOGGING = get_env_bool("ENABLE_PERFORMANCE_LOGGING", True)

# ===== 데이터 수집 설정 =====
AUTO_COLLECT_DATA = get_env_bool("AUTO_COLLECT_DATA", False)
MAX_COLLECTED_FRAMES = get_env_int("MAX_COLLECTED_FRAMES", 1000)

# ===== 개발자 설정 =====
DEBUG_MODE = get_env_bool("DEBUG_MODE", False)
FORCE_WEB_MODE = get_env_bool("FORCE_WEB_MODE", False)
ENABLE_AI_AGENT = get_env_bool("ENABLE_AI_AGENT", False)

# ===== AI 에이전트 전용 설정 =====
# PPO 에이전트는 이미지 데이터를 사용하지 않으므로 기본적으로 비활성화
# 디버그/분석 목적으로만 활성화 권장
ENABLE_IMAGE_CAPTURE_IN_AGENT_MODE = get_env_bool(
    "ENABLE_IMAGE_CAPTURE_IN_AGENT_MODE", False
)

# ===== 게임 설정 =====
GAME_WIDTH = get_env_int("GAME_WIDTH", 256)
GAME_HEIGHT = get_env_int("GAME_HEIGHT", 192)
GAME_FPS = get_env_int("GAME_FPS", 60)
DISPLAY_SCALE = get_env_int("DISPLAY_SCALE", 3)


def print_config_summary():
    """현재 설정 요약을 출력합니다."""
    print("🔧 환경 변수 설정 요약:")
    print(f"  🚀 고성능 캡쳐: {ENABLE_FAST_CAPTURE}")
    print(f"  📊 성능 로깅: {ENABLE_PERFORMANCE_LOGGING}")
    print(f"  🎮 게임 크기: {GAME_WIDTH}x{GAME_HEIGHT}")
    print(f"  🔧 디버그 모드: {DEBUG_MODE}")
    if DEBUG_MODE:
        print(f"  🔍 캡쳐 간격: {CAPTURE_INTERVAL}")
        print(f"  📈 최대 프레임: {MAX_COLLECTED_FRAMES}")


# 환경 변수 검증
def validate_config():
    """환경 변수 설정을 검증합니다."""
    errors = []
    warnings = []

    # 범위 검증
    if GAME_WIDTH <= 0 or GAME_HEIGHT <= 0:
        errors.append(f"게임 크기가 잘못되었습니다: {GAME_WIDTH}x{GAME_HEIGHT}")

    if GAME_FPS <= 0 or GAME_FPS > 120:
        warnings.append(f"게임 FPS가 비정상적입니다: {GAME_FPS}")

    if CAPTURE_INTERVAL <= 0:
        warnings.append(f"캡쳐 간격이 비정상적입니다: {CAPTURE_INTERVAL}")

    # 결과 출력
    if errors:
        print("❌ 환경 설정 오류:")
        for error in errors:
            print(f"  - {error}")
        return False

    if warnings:
        print("⚠️  환경 설정 경고:")
        for warning in warnings:
            print(f"  - {warning}")

    return True


# 모듈 로드 시 자동 검증
if __name__ == "__main__":
    print_config_summary()
    validate_config()
else:
    # 라이브러리로 임포트될 때는 간단한 메시지만
    if DEBUG_MODE:
        print_config_summary()
        validate_config()
