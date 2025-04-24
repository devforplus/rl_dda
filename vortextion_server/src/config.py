from functools import lru_cache
from pydantic import BaseSettings
import os
from typing import Dict, Any, Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # 기본 API 설정
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Vortextion Server"
    DEBUG: bool = True

    # DB 설정
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017/vortextion")
    DB_NAME: str = os.getenv("DB_NAME", "vortextion")

    # JWT 설정
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7일

    # 게임 관련 설정
    MAX_PLAYERS_PER_GAME: int = 4
    TICK_RATE: int = 60  # 게임 틱 레이트 (Hz)

    # 로깅 설정
    LOG_LEVEL: str = "INFO"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """설정 인스턴스를 캐싱하여 반환합니다."""
    return Settings()
