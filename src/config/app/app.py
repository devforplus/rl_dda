"""애플리케이션 기본 정보를 관리하는 모듈"""
import tomli
from pathlib import Path
from typing import Dict
import platform
import os

IS_WEB = platform.system() == "Emscripten"

def load_app_config() -> Dict[str, str]:
    """pyproject.toml에서 앱 설정을 로드합니다.
    
    Returns:
        Dict[str, str]: 앱 설정 딕셔너리
        
    Raises:
        FileNotFoundError: pyproject.toml 파일을 찾을 수 없는 경우
        tomli.TOMLDecodeError: TOML 파일 형식이 잘못된 경우
        PermissionError: 파일 읽기 권한이 없는 경우
        Exception: 그 외 오류가 발생한 경우
    """
    content = "" 
    pyproject_path = None

    if IS_WEB:
        pyproject_path = Path("pyproject.toml")
    else: # 로컬 환경
        pyproject_path = Path(__file__).resolve().parent.parent.parent.parent / "pyproject.toml"
        
    try:
        with open(pyproject_path, "rb") as f:
            content = f.read().decode('utf-8')
            pyproject = tomli.loads(content)
        
        game_config = pyproject.get("tool", {}).get("game", {})
        return {
            "APP_NAME": game_config.get("app_name", "VORTEXION"),
            "APP_VERSION": game_config.get("app_version", "1.0")
        }
    except FileNotFoundError:
        pyproject_path_str = str(pyproject_path)
        # 이전 디버그 print문 대신, FileNotFoundError 발생 시 기본값으로 처리하도록 수정 가능 (이전 제안 참고)
        # 여기서는 일단 에러 메시지만 간결하게 유지
        raise FileNotFoundError(f"Configuration file 'pyproject.toml' not found at expected path: {pyproject_path_str}.")
    except tomli.TOMLDecodeError as e:
        raise tomli.TOMLDecodeError(msg=str(e), doc=content if content else "Error: content not read", pos=getattr(e, 'pos', 0))
    except PermissionError as e:
        raise PermissionError(f"Permission denied for pyproject.toml: {str(e)}")
    except Exception as e:
        pyproject_path_str = str(pyproject_path)
        raise Exception(f"Error loading configuration from {pyproject_path_str}: {str(e)}")

# 앱 설정 로드
config = load_app_config()
APP_NAME = config["APP_NAME"]
APP_VERSION = config["APP_VERSION"]

