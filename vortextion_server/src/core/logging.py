import logging
import os
from typing import Optional
from .config import Config


def setup_logging(config: Optional[Config] = None) -> logging.Logger:
    """로깅을 설정합니다.

    Args:
        config (Optional[Config]): 설정 객체

    Returns:
        logging.Logger: 설정된 로거
    """
    if config is None:
        config = Config()

    # 로거 생성
    logger = logging.getLogger("vortexion")
    logger.setLevel(config.get("LOG_LEVEL", "INFO"))

    # 로그 포맷 설정
    formatter = logging.Formatter(config.get("LOG_FORMAT"))

    # 콘솔 핸들러 설정
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 파일 핸들러 설정
    log_file = config.get("LOG_FILE")
    if log_file:
        # 로그 디렉토리 생성
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
