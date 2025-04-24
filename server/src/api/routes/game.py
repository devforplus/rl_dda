from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
from src.db.repositories.session_repository import SessionRepository
from src.db.repositories.user_action_repository import UserActionRepository
from src.db.repositories.dda_action_repository import DDAActionRepository
from src.db.repositories.log_repository import LogRepository
from src.api.schemas.session import SessionResponse, SessionCreate
from src.core.logging import setup_logging

router = APIRouter(prefix="/game", tags=["game"])
session_repo = SessionRepository()
user_action_repo = UserActionRepository()
dda_action_repo = DDAActionRepository()
log_repo = LogRepository()
logger = setup_logging()


@router.post("/start", response_model=SessionResponse)
async def start_game(user_id: str = Query(..., description="사용자 ID")):
    """
    게임을 시작하고 새 세션을 생성합니다.

    Parameters:
    - user_id: 사용자 ID

    Returns:
    - 생성된 세션 정보
    """
    try:
        # 새 세션 생성
        session = await session_repo.create_session(user_id)

        # 게임 시작 로그 기록
        try:
            await log_repo.create_log(
                session_id=session.sessionId,
                level="INFO",
                category="GAME_EVENT",
                message=f"사용자 {user_id}가 게임을 시작했습니다.",
                data="{}",
            )
        except Exception as log_error:
            # 로그 기록 실패는 세션 생성에 영향을 주지 않도록 함
            logger.warning(f"게임 시작 로그 기록 실패: {str(log_error)}")

        logger.info(f"게임 시작: 사용자={user_id}, 세션={session.sessionId}")

        # 세션 객체를 직접 반환합니다. FastAPI가 Pydantic 모델로 변환합니다.
        return session
    except Exception as e:
        logger.error(f"게임 시작 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"게임 시작 실패: {str(e)}")


@router.post("/end", response_model=SessionResponse)
async def end_game(session_id: str = Query(..., description="세션 ID")):
    """
    게임을 종료하고 세션을 닫습니다.

    Parameters:
    - session_id: 세션 ID

    Returns:
    - 종료된 세션 정보
    """
    try:
        # 세션 조회
        session = await session_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

        # 게임 종료 로그 기록
        await log_repo.create_log(
            session_id=session_id,
            level="INFO",
            category="GAME_EVENT",
            message=f"사용자 {session.userId}가 게임을 종료했습니다.",
            data="{}",
        )

        # 세션 종료
        updated_session = await session_repo.end_session(session_id)

        logger.info(f"게임 종료: 세션={session_id}")
        return updated_session
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"게임 종료 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"게임 종료 실패: {str(e)}")


@router.get("/status/{session_id}")
async def get_game_status(session_id: str):
    """
    현재 게임 상태를 조회합니다.

    Parameters:
    - session_id: 세션 ID

    Returns:
    - 게임 상태 정보
    """
    try:
        # 세션 조회
        session = await session_repo.get_session(session_id)
        if not session:
            raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

        # 유저 액션 조회 (최근 10개)
        recent_actions = await user_action_repo.get_session_actions(
            session_id=session_id, limit=10
        )

        # DDA 액션 조회 (최근 5개)
        recent_dda_actions = await dda_action_repo.get_session_dda_actions(
            session_id=session_id, limit=5
        )

        return {
            "session": session,
            "is_active": session.endTime is None,
            "recent_actions": recent_actions,
            "recent_dda_actions": recent_dda_actions,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"게임 상태 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail=f"게임 상태 조회 실패: {str(e)}")
