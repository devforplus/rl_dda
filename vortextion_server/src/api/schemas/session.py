from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class SessionBase(BaseModel):
    """세션 기본 스키마"""

    user_id: str = Field(..., description="사용자 ID")


class SessionCreate(SessionBase):
    """세션 생성 요청 스키마"""

    pass


class SessionResponse(SessionBase):
    """세션 응답 스키마"""

    session_id: str = Field(..., description="세션 ID")
    start_time: datetime = Field(..., description="세션 시작 시간")
    end_time: Optional[datetime] = Field(None, description="세션 종료 시간")
    game_state: str = Field(..., description="게임 상태")
    created_at: datetime = Field(..., description="생성 시간")
    updated_at: datetime = Field(..., description="업데이트 시간")

    class Config:
        from_attributes = True
        populate_by_name = True

        # 필드 이름 매핑 (DB 모델 -> API 응답)
        field_customization = {
            "sessionId": {"api_field": "session_id"},
            "userId": {"api_field": "user_id"},
            "startTime": {"api_field": "start_time"},
            "endTime": {"api_field": "end_time"},
            "gameState": {"api_field": "game_state"},
            "createdAt": {"api_field": "created_at"},
            "updatedAt": {"api_field": "updated_at"},
        }

        json_schema_extra = {
            "example": {
                "session_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user_123",
                "start_time": "2023-05-01T12:00:00",
                "end_time": None,
                "game_state": "{}",
                "created_at": "2023-05-01T12:00:00",
                "updated_at": "2023-05-01T12:00:00",
            }
        }
