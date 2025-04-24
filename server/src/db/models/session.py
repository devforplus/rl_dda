from datetime import datetime
from typing import Optional, Dict, Any
from prisma.models import Session as PrismaSession


class Session:
    """게임 세션을 나타내는 모델 클래스입니다."""

    def __init__(
        self,
        session_id: str,
        user_id: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        game_state: Optional[Dict[str, Any]] = None,
    ):
        """세션 객체를 초기화합니다.

        Args:
            session_id (str): 세션 ID
            user_id (str): 사용자 ID
            start_time (datetime): 세션 시작 시간
            end_time (Optional[datetime]): 세션 종료 시간
            game_state (Optional[Dict[str, Any]]): 게임 상태
        """
        self.session_id = session_id
        self.user_id = user_id
        self.start_time = start_time
        self.end_time = end_time
        self.game_state = game_state or {}

    @classmethod
    def from_prisma(cls, prisma_session: PrismaSession) -> "Session":
        """Prisma 세션 객체로부터 Session 객체를 생성합니다.

        Args:
            prisma_session (PrismaSession): Prisma 세션 객체

        Returns:
            Session: 생성된 Session 객체
        """
        return cls(
            session_id=prisma_session.sessionId,
            user_id=prisma_session.userId,
            start_time=prisma_session.startTime,
            end_time=prisma_session.endTime,
            game_state=prisma_session.gameState,
        )

    def to_dict(self) -> Dict[str, Any]:
        """세션 객체를 딕셔너리로 변환합니다.

        Returns:
            Dict[str, Any]: 세션 정보를 담은 딕셔너리
        """
        return {
            "sessionId": self.session_id,
            "userId": self.user_id,
            "startTime": self.start_time,
            "endTime": self.end_time,
            "gameState": self.game_state,
        }
