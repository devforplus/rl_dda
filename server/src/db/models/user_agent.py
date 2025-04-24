from datetime import datetime
from typing import Dict, Any
from prisma.models import UserAction as PrismaUserAction


class UserAgent:
    """사용자 에이전트를 나타내는 모델 클래스입니다."""

    def __init__(
        self,
        session_id: str,
        action_type: str,
        action_data: Dict[str, Any],
        timestamp: datetime,
    ):
        """사용자 에이전트 객체를 초기화합니다.

        Args:
            session_id (str): 세션 ID
            action_type (str): 행동 유형
            action_data (Dict[str, Any]): 행동 데이터
            timestamp (datetime): 행동 발생 시간
        """
        self.session_id = session_id
        self.action_type = action_type
        self.action_data = action_data
        self.timestamp = timestamp

    @classmethod
    def from_prisma(cls, prisma_action: PrismaUserAction) -> "UserAgent":
        """Prisma 사용자 행동 객체로부터 UserAgent 객체를 생성합니다.

        Args:
            prisma_action (PrismaUserAction): Prisma 사용자 행동 객체

        Returns:
            UserAgent: 생성된 UserAgent 객체
        """
        return cls(
            session_id=prisma_action.sessionId,
            action_type=prisma_action.actionType,
            action_data=prisma_action.data,
            timestamp=prisma_action.timestamp,
        )

    def to_dict(self) -> Dict[str, Any]:
        """사용자 에이전트 객체를 딕셔너리로 변환합니다.

        Returns:
            Dict[str, Any]: 사용자 에이전트 정보를 담은 딕셔너리
        """
        return {
            "sessionId": self.session_id,
            "actionType": self.action_type,
            "actionData": self.action_data,
            "timestamp": self.timestamp,
        }
