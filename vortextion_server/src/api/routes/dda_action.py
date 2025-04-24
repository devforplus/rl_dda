from fastapi import APIRouter, HTTPException, Depends, Query, Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from src.api.models.dda_action import (
    DDAActionCreate,
    DDAActionResponse,
    DDAActionListResponse,
)
from src.api.dependencies.auth import get_current_user
from src.db.repositories.mongo_session_repository import MongoSessionRepository
from src.db.repositories.mongo_dda_action_repository import MongoDDAActionRepository

router = APIRouter(prefix="/sessions/{session_id}/dda-actions", tags=["dda actions"])


@router.post("", response_model=DDAActionResponse)
async def create_dda_action(
    session_id: str,
    action_data: DDAActionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """세션에 DDA 액션을 기록합니다."""
    session_repo = MongoSessionRepository()
    dda_action_repo = MongoDDAActionRepository()

    # 세션 존재 여부 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if session["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="이 세션에 대한 권한이 없습니다.")

    if session.get("endTime"):
        raise HTTPException(
            status_code=400, detail="종료된 세션에는 액션을 추가할 수 없습니다."
        )

    # DDA 액션 생성
    action = await dda_action_repo.create_dda_action(
        session_id=session_id,
        action_type=action_data.action_type,
        parameters=action_data.parameters,
        timestamp=action_data.timestamp if action_data.timestamp else datetime.utcnow(),
    )

    if not action:
        raise HTTPException(
            status_code=500, detail="DDA 액션 생성 중 오류가 발생했습니다."
        )

    return {
        "id": str(action["_id"]),
        "sessionId": action["sessionId"],
        "actionType": action["actionType"],
        "parameters": action["parameters"],
        "timestamp": action["timestamp"],
        "createdAt": action["createdAt"],
    }


@router.get("", response_model=List[DDAActionListResponse])
async def get_session_dda_actions(
    session_id: str,
    action_types: Optional[List[str]] = Query(None),
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """세션의 DDA 액션 목록을 조회합니다."""
    session_repo = MongoSessionRepository()
    dda_action_repo = MongoDDAActionRepository()

    # 세션 존재 여부 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if session["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="이 세션에 대한 권한이 없습니다.")

    # DDA 액션 조회
    actions = await dda_action_repo.get_session_dda_actions(
        session_id=session_id,
        action_types=action_types,
        start_time=start_time,
        end_time=end_time,
        limit=limit,
        offset=offset,
    )

    return [
        {
            "id": str(action["_id"]),
            "sessionId": action["sessionId"],
            "actionType": action["actionType"],
            "parameters": action["parameters"],
            "timestamp": action["timestamp"],
            "createdAt": action["createdAt"],
        }
        for action in actions
    ]


@router.get("/types", response_model=List[str])
async def get_dda_action_types(
    session_id: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """세션에서 사용된 모든 DDA 액션 유형을 조회합니다."""
    session_repo = MongoSessionRepository()
    dda_action_repo = MongoDDAActionRepository()

    # 세션 존재 여부 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if session["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="이 세션에 대한 권한이 없습니다.")

    # 액션 유형 조회
    action_types = await dda_action_repo.get_dda_action_types_by_session(session_id)
    return action_types


@router.get("/{action_id}", response_model=DDAActionResponse)
async def get_dda_action(
    session_id: str,
    action_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """특정 DDA 액션의 상세 정보를 조회합니다."""
    session_repo = MongoSessionRepository()
    dda_action_repo = MongoDDAActionRepository()

    # 세션 존재 여부 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if session["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="이 세션에 대한 권한이 없습니다.")

    # 액션 조회
    action = await dda_action_repo.get_dda_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="액션을 찾을 수 없습니다.")

    if action["sessionId"] != session_id:
        raise HTTPException(
            status_code=400, detail="요청한 세션에 속하지 않는 액션입니다."
        )

    return {
        "id": str(action["_id"]),
        "sessionId": action["sessionId"],
        "actionType": action["actionType"],
        "parameters": action["parameters"],
        "timestamp": action["timestamp"],
        "createdAt": action["createdAt"],
    }


@router.delete("/{action_id}", status_code=204)
async def delete_dda_action(
    session_id: str,
    action_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """DDA 액션을 삭제합니다."""
    session_repo = MongoSessionRepository()
    dda_action_repo = MongoDDAActionRepository()

    # 세션 존재 여부 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if session["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="이 세션에 대한 권한이 없습니다.")

    # 액션 조회
    action = await dda_action_repo.get_dda_action(action_id)
    if not action:
        raise HTTPException(status_code=404, detail="액션을 찾을 수 없습니다.")

    if action["sessionId"] != session_id:
        raise HTTPException(
            status_code=400, detail="요청한 세션에 속하지 않는 액션입니다."
        )

    # 액션 삭제
    success = await dda_action_repo.delete_dda_action(action_id)
    if not success:
        raise HTTPException(status_code=500, detail="액션 삭제 중 오류가 발생했습니다.")

    return None
