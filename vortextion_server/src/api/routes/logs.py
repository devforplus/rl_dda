from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from src.db.repositories.log_repository import LogRepository
from src.api.schemas.log import LogCreate, LogResponse

router = APIRouter(prefix="/logs", tags=["logs"])
log_repo = LogRepository()


@router.post("/", response_model=LogResponse)
async def create_log(log_data: LogCreate):
    """새 로그를 생성합니다."""
    try:
        log = await log_repo.create_log(
            session_id=log_data.session_id,
            level=log_data.level,
            category=log_data.category,
            message=log_data.message,
            data=log_data.data,
        )
        return log
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 생성 실패: {str(e)}")


@router.get("/{log_id}", response_model=LogResponse)
async def get_log(log_id: str):
    """로그 ID로 로그를 조회합니다."""
    log = await log_repo.get_log(log_id)
    if not log:
        raise HTTPException(status_code=404, detail="로그를 찾을 수 없습니다")
    return log


@router.get("/session/{session_id}", response_model=List[LogResponse])
async def get_session_logs(
    session_id: str,
    level: Optional[str] = Query(None, description="로그 레벨 필터"),
    category: Optional[str] = Query(None, description="로그 카테고리 필터"),
    limit: int = Query(100, description="반환할 최대 로그 수"),
    offset: int = Query(0, description="건너뛸 로그 수"),
):
    """세션의 로그 목록을 조회합니다."""
    try:
        logs = await log_repo.get_logs_by_session(
            session_id=session_id,
            level=level,
            category=category,
            limit=limit,
            offset=offset,
        )
        return logs
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 목록 조회 실패: {str(e)}")


@router.delete("/{log_id}", response_model=LogResponse)
async def delete_log(log_id: str):
    """로그를 삭제합니다."""
    try:
        log = await log_repo.delete_log(log_id)
        if not log:
            raise HTTPException(status_code=404, detail="로그를 찾을 수 없습니다")
        return log
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"로그 삭제 실패: {str(e)}")
