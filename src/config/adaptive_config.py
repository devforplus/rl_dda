"""
Adaptive Configuration Manager

Automatically detects the environment (web vs desktop) and loads appropriate configuration.
This solves the .env loading issue in web builds by using fallback strategies.

---

적응형 설정 관리자
환경을 자동 감지하여 적절한 설정을 로드합니다.
웹 빌드에서의 .env 로딩 문제를 fallback 전략으로 해결합니다.
"""

import platform
import sys
from typing import Dict, Any


# Environment detection
# 환경 감지
def is_web_environment() -> bool:
    """
    Detect if running in web environment (Pyodide/PyScript)

    ---

    웹 환경(Pyodide/PyScript)에서 실행 중인지 감지합니다.
    """
    # Multiple detection methods for reliability
    # 신뢰성을 위한 다중 감지 방법
    web_indicators = [
        platform.system() == "Emscripten",  # Pyodide
        "pyodide" in sys.modules,  # PyScript/Pyodide
        hasattr(sys, "platform") and "emscripten" in sys.platform.lower(),
    ]

    return any(web_indicators)


def load_configuration() -> Dict[str, Any]:
    """
    Load configuration based on environment detection
    Priority: Web Config > .env Config > Default Values

    ---

    환경 감지에 따라 설정을 로드합니다.
    우선순위: 웹 설정 > .env 설정 > 기본값
    """
    config = {}

    if is_web_environment():
        # Web environment - use hardcoded config
        # 웹 환경 - 하드코딩된 설정 사용
        try:
            from config.web_config import get_web_config, print_web_config

            config = get_web_config()
            print_web_config()
            print("✅ 웹 환경 설정 로드됨")
            return config
        except ImportError as e:
            print(f"⚠️  웹 설정 로드 실패: {e}")

    # Desktop environment - try .env config first
    # 데스크톱 환경 - .env 설정 우선 시도
    try:
        from config.env_config import (
            ENABLE_FAST_CAPTURE,
            CAPTURE_INTERVAL,
            ENABLE_PERFORMANCE_LOGGING,
            AUTO_COLLECT_DATA,
            MAX_COLLECTED_FRAMES,
            DEBUG_MODE,
            FORCE_WEB_MODE,
            ENABLE_AI_AGENT,
            GAME_WIDTH,
            GAME_HEIGHT,
            GAME_FPS,
            DISPLAY_SCALE,
        )

        config = {
            "ENABLE_FAST_CAPTURE": ENABLE_FAST_CAPTURE,
            "CAPTURE_INTERVAL": CAPTURE_INTERVAL,
            "ENABLE_PERFORMANCE_LOGGING": ENABLE_PERFORMANCE_LOGGING,
            "AUTO_COLLECT_DATA": AUTO_COLLECT_DATA,
            "MAX_COLLECTED_FRAMES": MAX_COLLECTED_FRAMES,
            "DEBUG_MODE": DEBUG_MODE,
            "FORCE_WEB_MODE": FORCE_WEB_MODE,
            "ENABLE_AI_AGENT": ENABLE_AI_AGENT,
            "GAME_WIDTH": GAME_WIDTH,
            "GAME_HEIGHT": GAME_HEIGHT,
            "GAME_FPS": GAME_FPS,
            "DISPLAY_SCALE": DISPLAY_SCALE,
        }

        print("✅ .env 환경 설정 로드됨")
        return config

    except ImportError as e:
        print(f"⚠️  .env 설정 로드 실패: {e}")

    # Fallback to default values
    # 기본값으로 fallback
    print("📋 기본 설정 사용")
    return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """
    Default configuration values as final fallback

    ---

    최종 fallback용 기본 설정값들
    """
    return {
        # Performance settings / 성능 설정
        "ENABLE_FAST_CAPTURE": True,
        "CAPTURE_INTERVAL": 5,
        "ENABLE_PERFORMANCE_LOGGING": True,
        # Data collection settings / 데이터 수집 설정
        "AUTO_COLLECT_DATA": False,
        "MAX_COLLECTED_FRAMES": 1000,
        # Developer settings / 개발자 설정
        "DEBUG_MODE": False,
        "FORCE_WEB_MODE": False,
        "ENABLE_AI_AGENT": False,
        # Game settings / 게임 설정
        "GAME_WIDTH": 256,
        "GAME_HEIGHT": 192,
        "GAME_FPS": 60,
        "DISPLAY_SCALE": 3,
    }


# Global configuration instance
# 전역 설정 인스턴스
_global_config = None


def get_config() -> Dict[str, Any]:
    """
    Get the current configuration (singleton pattern)

    ---

    현재 설정을 가져옵니다 (싱글톤 패턴)
    """
    global _global_config
    if _global_config is None:
        _global_config = load_configuration()
    return _global_config


def get_setting(key: str, default=None):
    """
    Get a specific setting value

    ---

    특정 설정값을 가져옵니다.
    """
    config = get_config()
    return config.get(key, default)


def print_environment_info():
    """
    Print detailed environment information for debugging

    ---

    디버깅용 상세 환경 정보를 출력합니다.
    """
    print("🔍 환경 정보:")
    print(f"  - Platform: {platform.system()}")
    print(f"  - Python: {sys.version}")
    print(f"  - 웹 환경: {is_web_environment()}")

    # Check available modules
    # 사용 가능한 모듈 확인
    modules_to_check = ["pyodide", "js", "dotenv", "numpy", "PIL"]
    for module in modules_to_check:
        try:
            __import__(module)
            print(f"  - {module}: ✅")
        except ImportError:
            print(f"  - {module}: ❌")


# Auto-initialize when imported
# 임포트 시 자동 초기화
if __name__ == "__main__":
    print_environment_info()
    config = get_config()
    print("\n📋 로드된 설정:")
    for key, value in config.items():
        print(f"  - {key}: {value}")
