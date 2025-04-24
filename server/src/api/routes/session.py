from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Query,
    Path,
    Body,
    BackgroundTasks,
    status,
)
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
import jwt

from src.api.auth import get_current_user, User
from src.db.repositories.mongo_session_repository import MongoSessionRepository
from src.db.repositories.mongo_game_repository import MongoGameRepository
from src.config import get_settings
from src.api.models.session import (
    SessionCreate,
    SessionEnd,
    SessionResponse,
    SessionListResponse,
    SessionUpdateStatus,
)
from src.db.repositories.mongo_user_action_repository import MongoUserActionRepository
from src.db.repositories.mongo_dda_action_repository import MongoDDAActionRepository


router = APIRouter(
    prefix="/sessions",
    tags=["sessions"],
    responses={404: {"description": "Not found"}},
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

settings = get_settings()


# 의존성 주입
def get_session_repository():
    return MongoSessionRepository()


def get_game_repository():
    return MongoGameRepository()


# DTO 모델들
class SessionCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = []
    settings: Optional[Dict[str, Any]] = {}


class SessionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None


class SessionTagsUpdate(BaseModel):
    tags: List[str]


class SessionSettingsUpdate(BaseModel):
    settings: Dict[str, Any]
    merge: bool = True


class SessionResponse(BaseModel):
    id: str = Field(..., alias="_id")
    userId: str
    name: str
    description: str
    tags: List[str]
    status: str
    settings: Dict[str, Any]
    createdAt: str
    updatedAt: str
    lastAccessedAt: str
    gameCount: Optional[int] = 0

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            # MongoDB ObjectId를 문자열로 변환
            Any: lambda v: str(v) if hasattr(v, "__str__") else v
        }


class SessionListItem(BaseModel):
    id: str
    userId: str
    name: str
    description: str
    status: str
    createdAt: datetime
    updatedAt: datetime
    lastAccessedAt: datetime
    gameCount: int


class SessionListResponse(BaseModel):
    sessions: List[SessionListItem]
    total: int


# 엔드포인트 구현
@router.post("", response_model=SessionResponse)
async def create_session(
    session_data: SessionCreate,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """새로운 세션을 생성합니다."""
    session_repo = MongoSessionRepository()

    # 새 세션 생성
    session = await session_repo.create_session(
        user_id=current_user["id"],
        content_id=session_data.content_id,
        content_type=session_data.content_type,
        version=session_data.version,
        start_time=session_data.start_time
        if session_data.start_time
        else datetime.utcnow(),
        status=session_data.status,
        context=session_data.context,
    )

    if not session:
        raise HTTPException(status_code=500, detail="세션 생성 중 오류가 발생했습니다.")

    return {
        "id": str(session["_id"]),
        "userId": session["userId"],
        "contentId": session["contentId"],
        "contentType": session["contentType"],
        "version": session["version"],
        "startTime": session["startTime"],
        "endTime": session.get("endTime"),
        "status": session["status"],
        "context": session["context"],
        "createdAt": session["createdAt"],
        "updatedAt": session["updatedAt"],
    }


@router.get("", response_model=List[SessionListResponse])
async def get_user_sessions(
    content_id: Optional[str] = None,
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    active_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """사용자의 세션 목록을 조회합니다."""
    session_repo = MongoSessionRepository()

    if active_only:
        sessions = await session_repo.get_active_sessions(
            user_id=current_user["id"],
            content_id=content_id,
            content_type=content_type,
            status=status,
            limit=limit,
            offset=offset,
        )
    else:
        sessions = await session_repo.get_user_sessions(
            user_id=current_user["id"],
            content_id=content_id,
            content_type=content_type,
            status=status,
            limit=limit,
            offset=offset,
        )

    return [
        {
            "id": str(session["_id"]),
            "userId": session["userId"],
            "contentId": session["contentId"],
            "contentType": session["contentType"],
            "version": session["version"],
            "startTime": session["startTime"],
            "endTime": session.get("endTime"),
            "status": session["status"],
            "createdAt": session["createdAt"],
            "updatedAt": session["updatedAt"],
        }
        for session in sessions
    ]


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """특정 세션의 상세 정보를 조회합니다."""
    session_repo = MongoSessionRepository()

    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if session["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="이 세션에 대한 권한이 없습니다.")

    return {
        "id": str(session["_id"]),
        "userId": session["userId"],
        "contentId": session["contentId"],
        "contentType": session["contentType"],
        "version": session["version"],
        "startTime": session["startTime"],
        "endTime": session.get("endTime"),
        "status": session["status"],
        "context": session["context"],
        "createdAt": session["createdAt"],
        "updatedAt": session["updatedAt"],
    }


@router.put("/{session_id}/end", response_model=SessionResponse)
async def end_session(
    session_id: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """세션을 종료합니다."""
    session_repo = MongoSessionRepository()

    # 세션 조회 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if session["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="이 세션에 대한 권한이 없습니다.")

    if session.get("endTime"):
        raise HTTPException(status_code=400, detail="이미 종료된 세션입니다.")

    # 세션 종료
    updated_session = await session_repo.end_session(
        session_id=session_id, end_time=datetime.utcnow()
    )

    if not updated_session:
        raise HTTPException(status_code=500, detail="세션 종료 중 오류가 발생했습니다.")

    return {
        "id": str(updated_session["_id"]),
        "userId": updated_session["userId"],
        "contentId": updated_session["contentId"],
        "contentType": updated_session["contentType"],
        "version": updated_session["version"],
        "startTime": updated_session["startTime"],
        "endTime": updated_session["endTime"],
        "status": updated_session["status"],
        "context": updated_session["context"],
        "createdAt": updated_session["createdAt"],
        "updatedAt": updated_session["updatedAt"],
    }


@router.patch("/{session_id}/status", response_model=SessionResponse)
async def update_session_status(
    session_id: str,
    status_data: SessionUpdateStatus,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """세션의 상태를 업데이트합니다."""
    session_repo = MongoSessionRepository()

    # 세션 조회 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if session["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="이 세션에 대한 권한이 없습니다.")

    if session.get("endTime"):
        raise HTTPException(
            status_code=400, detail="종료된 세션의 상태는 변경할 수 없습니다."
        )

    # MongoDB의 업데이트 작업 - 여기서는 repository로 구현
    updated_session = await session_repo.update_status(
        session_id=session_id, status=status_data.status
    )

    if not updated_session:
        raise HTTPException(
            status_code=500, detail="세션 상태 업데이트 중 오류가 발생했습니다."
        )

    return {
        "id": str(updated_session["_id"]),
        "userId": updated_session["userId"],
        "contentId": updated_session["contentId"],
        "contentType": updated_session["contentType"],
        "version": updated_session["version"],
        "startTime": updated_session["startTime"],
        "endTime": updated_session.get("endTime"),
        "status": updated_session["status"],
        "context": updated_session["context"],
        "createdAt": updated_session["createdAt"],
        "updatedAt": updated_session["updatedAt"],
    }


@router.delete("/{session_id}", status_code=204)
async def delete_session(
    session_id: str, current_user: Dict[str, Any] = Depends(get_current_user)
):
    """세션과 관련된 모든 데이터를 삭제합니다."""
    session_repo = MongoSessionRepository()
    user_action_repo = MongoUserActionRepository()
    dda_action_repo = MongoDDAActionRepository()

    # 세션 조회 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if session["userId"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="이 세션에 대한 권한이 없습니다.")

    # 관련된 모든 액션 삭제
    await user_action_repo.delete_session_actions(session_id)
    await dda_action_repo.delete_session_dda_actions(session_id)

    # 세션 삭제
    success = await session_repo.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=500, detail="세션 삭제 중 오류가 발생했습니다.")

    return None


@router.get("/active", response_model=Optional[SessionResponse])
async def get_active_session(current_user: Dict[str, Any] = Depends(get_current_user)):
    """사용자의 활성화된 세션을 조회합니다."""
    session_repo = MongoSessionRepository()

    active_sessions = await session_repo.get_active_sessions(current_user["id"])
    if not active_sessions:
        return JSONResponse(content=None, status_code=200)

    active_session = active_sessions[0]
    return {
        "id": str(active_session["_id"]),
        "userId": active_session["userId"],
        "appVersion": active_session["appVersion"],
        "deviceInfo": active_session["deviceInfo"],
        "sessionType": active_session["sessionType"],
        "startTime": active_session["startTime"],
        "endTime": active_session.get("endTime"),
        "summary": active_session.get("summary", ""),
        "createdAt": active_session["createdAt"],
    }


@router.put("/{session_id}", response_model=SessionResponse)
async def update_session(
    update_data: SessionUpdate,
    session_id: str = Path(..., description="세션 ID"),
    current_user: User = Depends(get_current_user),
    session_repo: MongoSessionRepository = Depends(get_session_repository),
    game_repo: MongoGameRepository = Depends(get_game_repository),
):
    """
    세션 정보를 업데이트합니다.
    """
    # 세션 존재 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    if session.get("userId") != str(current_user.id):
        raise HTTPException(status_code=403, detail="이 세션에 접근할 권한이 없습니다")

    # 요청 데이터에서 None 값 제거
    update_dict = update_data.dict(exclude_unset=True)

    # 업데이트 수행
    updated_session = await session_repo.update_session(session_id, update_dict)

    if not updated_session:
        raise HTTPException(status_code=500, detail="세션 업데이트에 실패했습니다")

    # 게임 개수 추가
    game_count = await game_repo.count_session_games(session_id)
    updated_session["gameCount"] = game_count

    return updated_session


@router.put("/{session_id}/settings", response_model=SessionResponse)
async def update_session_settings(
    settings_data: SessionSettingsUpdate,
    session_id: str = Path(..., description="세션 ID"),
    current_user: User = Depends(get_current_user),
    session_repo: MongoSessionRepository = Depends(get_session_repository),
    game_repo: MongoGameRepository = Depends(get_game_repository),
):
    """
    세션 설정을 업데이트합니다.
    """
    # 세션 존재 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    if session.get("userId") != str(current_user.id):
        raise HTTPException(status_code=403, detail="이 세션에 접근할 권한이 없습니다")

    # 설정 업데이트
    updated_session = await session_repo.update_session_settings(
        session_id, settings_data.settings, settings_data.merge
    )

    if not updated_session:
        raise HTTPException(status_code=500, detail="세션 설정 업데이트에 실패했습니다")

    # 게임 개수 추가
    game_count = await game_repo.count_session_games(session_id)
    updated_session["gameCount"] = game_count

    return updated_session


@router.post("/{session_id}/tags", response_model=SessionResponse)
async def add_session_tags(
    tags_data: SessionTagsUpdate,
    session_id: str = Path(..., description="세션 ID"),
    current_user: User = Depends(get_current_user),
    session_repo: MongoSessionRepository = Depends(get_session_repository),
    game_repo: MongoGameRepository = Depends(get_game_repository),
):
    """
    세션에 태그를 추가합니다.
    """
    # 세션 존재 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    if session.get("userId") != str(current_user.id):
        raise HTTPException(status_code=403, detail="이 세션에 접근할 권한이 없습니다")

    # 태그 추가
    updated_session = await session_repo.add_session_tags(session_id, tags_data.tags)

    if not updated_session:
        raise HTTPException(status_code=500, detail="태그 추가에 실패했습니다")

    # 게임 개수 추가
    game_count = await game_repo.count_session_games(session_id)
    updated_session["gameCount"] = game_count

    return updated_session


@router.delete("/{session_id}/tags", response_model=SessionResponse)
async def remove_session_tags(
    tags_data: SessionTagsUpdate,
    session_id: str = Path(..., description="세션 ID"),
    current_user: User = Depends(get_current_user),
    session_repo: MongoSessionRepository = Depends(get_session_repository),
    game_repo: MongoGameRepository = Depends(get_game_repository),
):
    """
    세션에서 태그를 제거합니다.
    """
    # 세션 존재 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    if session.get("userId") != str(current_user.id):
        raise HTTPException(status_code=403, detail="이 세션에 접근할 권한이 없습니다")

    # 태그 제거
    updated_session = await session_repo.remove_session_tags(session_id, tags_data.tags)

    if not updated_session:
        raise HTTPException(status_code=500, detail="태그 제거에 실패했습니다")

    # 게임 개수 추가
    game_count = await game_repo.count_session_games(session_id)
    updated_session["gameCount"] = game_count

    return updated_session


@router.post("/{session_id}/archive", response_model=SessionResponse)
async def archive_session(
    session_id: str = Path(..., description="세션 ID"),
    current_user: User = Depends(get_current_user),
    session_repo: MongoSessionRepository = Depends(get_session_repository),
    game_repo: MongoGameRepository = Depends(get_game_repository),
):
    """
    세션을 아카이브 상태로 변경합니다.
    """
    # 세션 존재 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    if session.get("userId") != str(current_user.id):
        raise HTTPException(status_code=403, detail="이 세션에 접근할 권한이 없습니다")

    # 이미 아카이브된 경우 확인
    if session.get("status") == "archived":
        raise HTTPException(status_code=400, detail="이미 아카이브된 세션입니다")

    # 세션 아카이브
    updated_session = await session_repo.archive_session(session_id)

    if not updated_session:
        raise HTTPException(status_code=500, detail="세션 아카이브에 실패했습니다")

    # 게임 개수 추가
    game_count = await game_repo.count_session_games(session_id)
    updated_session["gameCount"] = game_count

    return updated_session


@router.post("/{session_id}/restore", response_model=SessionResponse)
async def restore_session(
    session_id: str = Path(..., description="세션 ID"),
    current_user: User = Depends(get_current_user),
    session_repo: MongoSessionRepository = Depends(get_session_repository),
    game_repo: MongoGameRepository = Depends(get_game_repository),
):
    """
    아카이브된 세션을 활성 상태로 복원합니다.
    """
    # 세션 존재 및 권한 확인
    session = await session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다")

    if session.get("userId") != str(current_user.id):
        raise HTTPException(status_code=403, detail="이 세션에 접근할 권한이 없습니다")

    # 이미 활성화된 경우 확인
    if session.get("status") != "archived":
        raise HTTPException(status_code=400, detail="아카이브되지 않은 세션입니다")

    # 세션 복원
    updated_session = await session_repo.restore_session(session_id)

    if not updated_session:
        raise HTTPException(status_code=500, detail="세션 복원에 실패했습니다")

    # 게임 개수 추가
    game_count = await game_repo.count_session_games(session_id)
    updated_session["gameCount"] = game_count

    return updated_session


@router.get("", response_model=List[SessionResponse])
async def get_user_sessions(
    status: Optional[List[str]] = Query(
        None, description="세션 상태 필터링 (쉼표로 구분)"
    ),
    tags: Optional[List[str]] = Query(None, description="태그 필터링 (쉼표로 구분)"),
    search: Optional[str] = Query(None, description="검색어"),
    limit: int = Query(20, ge=1, le=100, description="페이지당 결과 수"),
    offset: int = Query(0, ge=0, description="결과 오프셋"),
    sort_by: str = Query("updatedAt", description="정렬 기준 필드"),
    sort_order: int = Query(-1, description="정렬 순서 (1: 오름차순, -1: 내림차순)"),
    current_user: User = Depends(get_current_user),
    session_repo: MongoSessionRepository = Depends(get_session_repository),
    game_repo: MongoGameRepository = Depends(get_game_repository),
):
    """
    현재 사용자의 세션 목록을 가져옵니다.
    """
    user_id = str(current_user.id)

    sessions = await session_repo.get_user_sessions(
        user_id=user_id,
        status=status,
        tags=tags,
        search_term=search,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # 각 세션에 게임 개수 추가
    for session in sessions:
        session_id = str(session["_id"])
        game_count = await game_repo.count_session_games(session_id)
        session["gameCount"] = game_count

    return sessions


@router.get("/count", response_model=Dict[str, int])
async def count_user_sessions(
    status: Optional[List[str]] = Query(
        None, description="세션 상태 필터링 (쉼표로 구분)"
    ),
    tags: Optional[List[str]] = Query(None, description="태그 필터링 (쉼표로 구분)"),
    search: Optional[str] = Query(None, description="검색어"),
    current_user: User = Depends(get_current_user),
    session_repo: MongoSessionRepository = Depends(get_session_repository),
):
    """
    현재 사용자의 세션 수를 반환합니다.
    """
    user_id = str(current_user.id)

    count = await session_repo.count_user_sessions(
        user_id=user_id, status=status, tags=tags, search_term=search
    )

    return {"count": count}


@router.get("/stats", response_model=Dict[str, Any])
async def get_user_session_stats(
    current_user: User = Depends(get_current_user),
    session_repo: MongoSessionRepository = Depends(get_session_repository),
):
    """
    현재 사용자의 세션 통계를 반환합니다.
    """
    user_id = str(current_user.id)
    stats = await session_repo.get_user_session_stats(user_id)
    return stats


@router.get("/tags", response_model=List[Dict[str, Any]])
async def get_all_tags(
    current_user: User = Depends(get_current_user),
    session_repo: MongoSessionRepository = Depends(get_session_repository),
):
    """
    현재 사용자의 모든 태그 목록을 반환합니다.
    """
    user_id = str(current_user.id)
    tags = await session_repo.get_all_tags(user_id)
    return tags
