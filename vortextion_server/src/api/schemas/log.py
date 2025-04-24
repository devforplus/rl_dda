from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class LogBase(BaseModel):
    """로그 기본 스키마"""

    session_id: str = Field(..., description="세션 ID")
    level: str = Field(..., description="로그 레벨")
    category: str = Field(..., description="로그 카테고리")
    message: str = Field(..., description="로그 메시지")
    data: Optional[str] = Field(None, description="추가 데이터 (JSON 문자열)")


class LogCreate(LogBase):
    """로그 생성 요청 스키마"""

    pass


class LogResponse(LogBase):
    """로그 응답 스키마"""

    id: str = Field(..., description="로그 ID")
    timestamp: datetime = Field(..., description="로그 생성 시간")

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "session_id": "123e4567-e89b-12d3-a456-426614174000",
                "level": "INFO",
                "category": "GAME_EVENT",
                "message": "플레이어가 레벨을 시작했습니다",
                "data": '{"level_id": "level_1", "difficulty": "normal"}',
                "timestamp": "2023-05-01T12:00:00",
            }
        }
