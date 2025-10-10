"""애플리케이션 기본 정보를 관리하는 모듈"""

import tomli
import platform
from pathlib import Path

IS_WEB = platform.system() == "Emscripten"

# 기본값
DEFAULT_APP_NAME = "VORTEXION"
DEFAULT_APP_VERSION = "1.0"


def load_app_config():
    """pyproject.toml에서 앱 설정을 로드합니다.

    Returns:
        tuple: (APP_NAME, APP_VERSION)
    """
    toml_path = None

    if IS_WEB:
        # 웹 환경에서는 현재 디렉토리에서 찾기
        toml_path = Path("pyproject.toml")
    else:
        # 로컬 환경에서는 프로젝트 루트에서 찾기
        toml_path = Path(__file__).resolve().parent.parent.parent / "pyproject.toml"

    try:
        with open(toml_path, "rb") as f:
            config = tomli.load(f)

        game_config = config.get("tool", {}).get("game", {})
        app_name = game_config.get("app_name", DEFAULT_APP_NAME)
        app_version = game_config.get("app_version", DEFAULT_APP_VERSION)

        return app_name, app_version

    except (FileNotFoundError, tomli.TOMLDecodeError, Exception):
        # 파일이 없거나 읽기 실패 시 기본값 사용
        return DEFAULT_APP_NAME, DEFAULT_APP_VERSION


# 앱 설정 로드
APP_NAME, APP_VERSION = load_app_config()
