from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime


class SessionCreate(BaseModel):
    """세션 생성 모델"""

    content_id: str = Field(..., description="콘텐츠 ID")
    content_type: str = Field(..., description="콘텐츠 타입 (예: game, video, book)")
    version: Optional[str] = None
    start_time: Optional[datetime] = None
    status: str = "active"
    context: Optional[Dict[str, Any]] = None


class SessionEnd(BaseModel):
    end_time: Optional[datetime] = None


class SessionResponse(BaseModel):
    """세션 응답 모델"""

    id: str
    userId: str
    contentId: str
    contentType: str
    version: Optional[str]
    startTime: datetime
    endTime: Optional[datetime]
    status: str
    context: Optional[Dict[str, Any]]
    createdAt: datetime
    updatedAt: datetime


class SessionListResponse(BaseModel):
    """세션 목록 응답 모델"""

    id: str
    userId: str
    contentId: str
    contentType: str
    version: Optional[str]
    startTime: datetime
    endTime: Optional[datetime]
    status: str
    createdAt: datetime
    updatedAt: datetime


class SessionUpdateStatus(BaseModel):
    """세션 상태 업데이트 모델"""

    status: str
