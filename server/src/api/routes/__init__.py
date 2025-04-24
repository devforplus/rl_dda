"""
API 라우트를 포함하는 패키지입니다.
이 패키지는 세션, 사용자 행동, DDA 행동, 로그 등에 대한 엔드포인트를 정의합니다.
"""

from fastapi import APIRouter

# 라우트 모듈 가져오기
from src.api.routes.session import router as session_router

# API 라우터
api_router = APIRouter()

# 개별 라우터 등록
api_router.include_router(session_router, prefix="/api", tags=["sessions"])

# 나중에 추가될 라우터들을 여기에 등록하세요
# api_router.include_router(game_router, prefix="/api", tags=["games"])
# api_router.include_router(log_router, prefix="/api", tags=["logs"])
# api_router.include_router(user_action_router, prefix="/api", tags=["user-actions"])
# api_router.include_router(dda_action_router, prefix="/api", tags=["dda-actions"])

__all__ = [
    "session_router",
]
