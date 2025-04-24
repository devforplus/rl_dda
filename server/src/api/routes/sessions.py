from fastapi import APIRouter, HTTPException, Depends
from src.db.repositories.session_repository import SessionRepository
from src.api.schemas.session import SessionCreate, SessionResponse

router = APIRouter(prefix="/sessions", tags=["sessions"])
session_repo = SessionRepository()


@router.post("/", response_model=SessionResponse)
async def create_session(session_data: SessionCreate):
    """새 게임 세션을 생성합니다."""
    try:
        session = await session_repo.create_session(session_data.user_id)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 생성 실패: {str(e)}")


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str):
    """세션 ID로 세션을 조회합니다."""
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")
    return session


@router.put("/{session_id}/end", response_model=SessionResponse)
async def end_session(session_id: str):
    """세션을 종료합니다."""
    try:
        session = await session_repo.end_session(session_id)
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 종료 실패: {str(e)}")


@router.get("/user/{user_id}", response_model=list[SessionResponse])
async def get_user_sessions(user_id: str):
    """사용자의 활성 세션 목록을 조회합니다."""
    try:
        sessions = await session_repo.get_active_sessions(user_id)
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"세션 목록 조회 실패: {str(e)}")
