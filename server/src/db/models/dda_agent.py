from datetime import datetime
from typing import Dict, Any
from prisma.models import DDAAction as PrismaDDAAction


class DDAAgent:
    """DDA(Dynamic Difficulty Adjustment) 에이전트를 나타내는 모델 클래스입니다."""

    def __init__(
        self,
        session_id: str,
        action_type: str,
        parameters: Dict[str, Any],
        timestamp: datetime,
    ):
        """DDA 에이전트 객체를 초기화합니다.

        Args:
            session_id (str): 세션 ID
            action_type (str): 행동 유형
            parameters (Dict[str, Any]): DDA 파라미터
            timestamp (datetime): 행동 발생 시간
        """
        self.session_id = session_id
        self.action_type = action_type
        self.parameters = parameters
        self.timestamp = timestamp

    @classmethod
    def from_prisma(cls, prisma_action: PrismaDDAAction) -> "DDAAgent":
        """Prisma DDA 행동 객체로부터 DDAAgent 객체를 생성합니다.

        Args:
            prisma_action (PrismaDDAAction): Prisma DDA 행동 객체

        Returns:
            DDAAgent: 생성된 DDAAgent 객체
        """
        return cls(
            session_id=prisma_action.sessionId,
            action_type=prisma_action.actionType,
            parameters=prisma_action.parameters,
            timestamp=prisma_action.timestamp,
        )

    def to_dict(self) -> Dict[str, Any]:
        """DDA 에이전트 객체를 딕셔너리로 변환합니다.

        Returns:
            Dict[str, Any]: DDA 에이전트 정보를 담은 딕셔너리
        """
        return {
            "sessionId": self.session_id,
            "actionType": self.action_type,
            "parameters": self.parameters,
            "timestamp": self.timestamp,
        }
