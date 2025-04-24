from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserActionBase(BaseModel):
    """유저 액션 기본 스키마"""

    session_id: str = Field(..., description="세션 ID")
    action_type: str = Field(..., description="액션 타입")
    data: str = Field(..., description="액션 데이터 (JSON 문자열)")


class UserActionCreate(UserActionBase):
    """유저 액션 생성 요청 스키마"""

    pass


class UserActionResponse(UserActionBase):
    """유저 액션 응답 스키마"""

    id: str = Field(..., description="액션 ID")
    timestamp: datetime = Field(..., description="액션 발생 시간")
    created_at: datetime = Field(..., description="생성 시간")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "action_type": "MOVEMENT",
                "data": '{"x": 100, "y": 200, "direction": "right"}',
                "timestamp": "2023-05-01T12:00:00",
                "created_at": "2023-05-01T12:00:00",
            }
        }
