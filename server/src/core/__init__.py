"""
게임의 핵심 기능을 포함하는 패키지입니다.
이 패키지는 설정 관리, 로깅 등의 기능을 제공합니다.
"""

from .config import Config
from .logging import setup_logging

__all__ = ["Config", "setup_logging"]
