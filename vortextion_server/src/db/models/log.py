from datetime import datetime
from typing import Optional, Dict, Any
from prisma.models import GameLog as PrismaGameLog


class Log:
    """게임 로그를 나타내는 모델 클래스입니다."""

    def __init__(
        self,
        session_id: str,
        level: str,
        category: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
    ):
        """로그 객체를 초기화합니다.

        Args:
            session_id (str): 세션 ID
            level (str): 로그 레벨
            category (str): 로그 카테고리
            message (str): 로그 메시지
            data (Optional[Dict[str, Any]]): 추가 데이터
            timestamp (Optional[datetime]): 로그 발생 시간
        """
        self.session_id = session_id
        self.level = level
        self.category = category
        self.message = message
        self.data = data or {}
        self.timestamp = timestamp or datetime.now()

    @classmethod
    def from_prisma(cls, prisma_log: PrismaGameLog) -> "Log":
        """Prisma 게임 로그 객체로부터 Log 객체를 생성합니다.

        Args:
            prisma_log (PrismaGameLog): Prisma 게임 로그 객체

        Returns:
            Log: 생성된 Log 객체
        """
        return cls(
            session_id=prisma_log.sessionId,
            level=prisma_log.level,
            category=prisma_log.category,
            message=prisma_log.message,
            data=prisma_log.data,
            timestamp=prisma_log.timestamp,
        )

    def to_dict(self) -> Dict[str, Any]:
        """로그 객체를 딕셔너리로 변환합니다.

        Returns:
            Dict[str, Any]: 로그 정보를 담은 딕셔너리
        """
        return {
            "sessionId": self.session_id,
            "level": self.level,
            "category": self.category,
            "message": self.message,
            "data": self.data,
            "timestamp": self.timestamp,
        }
