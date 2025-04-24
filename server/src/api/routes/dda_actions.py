from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from src.db.repositories.dda_action_repository import DDAActionRepository
from src.api.schemas.dda_action import DDAActionCreate, DDAActionResponse

router = APIRouter(prefix="/dda-actions", tags=["dda_actions"])
dda_action_repo = DDAActionRepository()


@router.post("/", response_model=DDAActionResponse)
async def create_dda_action(action_data: DDAActionCreate):
    """새 DDA 액션을 기록합니다."""
    try:
        action = await dda_action_repo.create_dda_action(
            session_id=action_data.session_id,
            action_type=action_data.action_type,
            parameters=action_data.parameters,
        )
        return action
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DDA 액션 생성 실패: {str(e)}")


@router.get("/{action_id}", response_model=DDAActionResponse)
async def get_dda_action(action_id: str):
    """액션 ID로 DDA 액션을 조회합니다."""
    action = await dda_action_repo.get_dda_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="DDA 액션을 찾을 수 없습니다")
    return action


@router.get("/session/{session_id}", response_model=List[DDAActionResponse])
async def get_session_dda_actions(
    session_id: str,
    action_type: Optional[str] = Query(None, description="DDA 액션 타입 필터"),
    limit: int = Query(100, description="반환할 최대 액션 수"),
    offset: int = Query(0, description="건너뛸 액션 수"),
    sort_order: str = Query("desc", description="정렬 순서 (asc 또는 desc)"),
):
    """세션의 DDA 액션 목록을 조회합니다."""
    try:
        actions = await dda_action_repo.get_session_dda_actions(
            session_id=session_id,
            action_type=action_type,
            limit=limit,
            offset=offset,
            sort_order=sort_order,
        )
        return actions
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"DDA 액션 목록 조회 실패: {str(e)}"
        )


@router.get("/session/{session_id}/types", response_model=List[str])
async def get_session_dda_action_types(session_id: str):
    """세션에서 사용된 모든 DDA 액션 타입을 조회합니다."""
    try:
        types = await dda_action_repo.get_dda_action_types_by_session(session_id)
        return types
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"DDA 액션 타입 조회 실패: {str(e)}"
        )


@router.delete("/{action_id}", response_model=DDAActionResponse)
async def delete_dda_action(action_id: str):
    """DDA 액션을 삭제합니다."""
    try:
        action = await dda_action_repo.delete_dda_action(action_id)
        if not action:
            raise HTTPException(status_code=404, detail="DDA 액션을 찾을 수 없습니다")
        return action
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DDA 액션 삭제 실패: {str(e)}")
