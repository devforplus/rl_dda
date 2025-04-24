from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from src.db.repositories.user_action_repository import UserActionRepository
from src.api.schemas.user_action import UserActionCreate, UserActionResponse

router = APIRouter(prefix="/user-actions", tags=["user_actions"])
user_action_repo = UserActionRepository()


@router.post("/", response_model=UserActionResponse)
async def create_user_action(action_data: UserActionCreate):
    """새 유저 액션을 기록합니다."""
    try:
        action = await user_action_repo.create_user_action(
            session_id=action_data.session_id,
            action_type=action_data.action_type,
            data=action_data.data,
        )
        return action
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"유저 액션 생성 실패: {str(e)}")


@router.get("/{action_id}", response_model=UserActionResponse)
async def get_user_action(action_id: str):
    """액션 ID로 유저 액션을 조회합니다."""
    action = await user_action_repo.get_user_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="유저 액션을 찾을 수 없습니다")
    return action


@router.get("/session/{session_id}", response_model=List[UserActionResponse])
async def get_session_actions(
    session_id: str,
    action_type: Optional[str] = Query(None, description="액션 타입 필터"),
    limit: int = Query(100, description="반환할 최대 액션 수"),
    offset: int = Query(0, description="건너뛸 액션 수"),
    sort_order: str = Query("desc", description="정렬 순서 (asc 또는 desc)"),
):
    """세션의 유저 액션 목록을 조회합니다."""
    try:
        actions = await user_action_repo.get_session_actions(
            session_id=session_id,
            action_type=action_type,
            limit=limit,
            offset=offset,
            sort_order=sort_order,
        )
        return actions
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"유저 액션 목록 조회 실패: {str(e)}"
        )


@router.get("/session/{session_id}/types", response_model=List[str])
async def get_session_action_types(session_id: str):
    """세션에서 사용된 모든 액션 타입을 조회합니다."""
    try:
        types = await user_action_repo.get_action_types_by_session(session_id)
        return types
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"액션 타입 조회 실패: {str(e)}")


@router.delete("/{action_id}", response_model=UserActionResponse)
async def delete_user_action(action_id: str):
    """유저 액션을 삭제합니다."""
    try:
        action = await user_action_repo.delete_user_action(action_id)
        if not action:
            raise HTTPException(status_code=404, detail="유저 액션을 찾을 수 없습니다")
        return action
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"유저 액션 삭제 실패: {str(e)}")
