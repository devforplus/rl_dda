"""애플리케이션 기본 정보를 관리하는 모듈"""
import tomli
from pathlib import Path
from typing import Dict

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
    try:
        pyproject_path = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            content = f.read().decode('utf-8')
            pyproject = tomli.loads(content)
        
        game_config = pyproject.get("tool", {}).get("game", {})
        return {
            "APP_NAME": game_config.get("app_name", "VORTEXION"),
            "APP_VERSION": game_config.get("app_version", "1.0")
        }
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found at {pyproject_path}")
    except tomli.TOMLDecodeError as e:
        # 원본 에러의 속성을 유지하면서 새로운 에러를 생성
        raise tomli.TOMLDecodeError(msg=str(e), doc=content, pos=getattr(e, 'pos', 0))
    except PermissionError as e:
        raise PermissionError(f"Permission denied: {str(e)}")
    except Exception as e:
        raise Exception(f"Error loading configuration: {str(e)}")

# 앱 설정 로드
config = load_app_config()
APP_NAME = config["APP_NAME"]
APP_VERSION = config["APP_VERSION"]

