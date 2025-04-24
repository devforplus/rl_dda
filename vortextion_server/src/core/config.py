import os
from typing import Dict, Any
from dotenv import load_dotenv


class Config:
    """게임 설정을 관리하는 클래스입니다."""

    def __init__(self):
        """설정을 초기화합니다."""
        load_dotenv()
        self._config: Dict[str, Any] = {}
        self._load_config()

    def _load_config(self):
        """환경 변수에서 설정을 로드합니다."""
        self._config = {
            # 데이터베이스 설정
            "DATABASE_URL": os.getenv("DATABASE_URL"),
            # 로깅 설정
            "LOG_LEVEL": os.getenv("LOG_LEVEL", "INFO"),
            "LOG_FORMAT": os.getenv(
                "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
            ),
            "LOG_FILE": os.getenv("LOG_FILE", "game.log"),
            # 게임 설정
            "GAME_TITLE": os.getenv("GAME_TITLE", "Vortexion"),
            "GAME_VERSION": os.getenv("GAME_VERSION", "1.0.0"),
            "GAME_WIDTH": int(os.getenv("GAME_WIDTH", "800")),
            "GAME_HEIGHT": int(os.getenv("GAME_HEIGHT", "600")),
            "FPS": int(os.getenv("FPS", "60")),
            # 서버 설정
            "API_HOST": os.getenv("API_HOST", "0.0.0.0"),
            "API_PORT": int(os.getenv("API_PORT", "8000")),
        }

    def get(self, key: str, default: Any = None) -> Any:
        """설정 값을 가져옵니다.

        Args:
            key (str): 설정 키
            default (Any): 기본값

        Returns:
            Any: 설정 값
        """
        return self._config.get(key, default)

    def set(self, key: str, value: Any):
        """설정 값을 설정합니다.

        Args:
            key (str): 설정 키
            value (Any): 설정 값
        """
        self._config[key] = value

    def __getitem__(self, key: str) -> Any:
        """설정 값을 가져옵니다.

        Args:
            key (str): 설정 키

        Returns:
            Any: 설정 값
        """
        return self._config[key]

    def __setitem__(self, key: str, value: Any):
        """설정 값을 설정합니다.

        Args:
            key (str): 설정 키
            value (Any): 설정 값
        """
        self._config[key] = value
