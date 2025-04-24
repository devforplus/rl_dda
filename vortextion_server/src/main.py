import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import api_router
from src.db.mongodb import connect_to_mongodb, close_mongodb_connection

# FastAPI 애플리케이션 생성
app = FastAPI(
    title="Vortextion Game Server",
    description="게임 세션 및 데이터 관리를 위한 API 서버",
    version="0.1.0",
)

# CORS 미들웨어 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포환경에서는 구체적인 도메인으로 제한해야 함
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(api_router)


# MongoDB 연결 이벤트 핸들러
@app.on_event("startup")
async def startup_db_client():
    """애플리케이션 시작 시 MongoDB에 연결합니다."""
    await connect_to_mongodb()


@app.on_event("shutdown")
async def shutdown_db_client():
    """애플리케이션 종료 시 MongoDB 연결을 종료합니다."""
    await close_mongodb_connection()


# 정적 파일 제공 (선택 사항)
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# 루트 경로
@app.get("/")
async def root():
    return {
        "message": "Vortextion Game Server API",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }


def main():
    """애플리케이션 메인 진입점"""
    import uvicorn

    # 서버 설정
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    # 개발 모드에서 hot reload 활성화
    reload = os.getenv("ENV", "development") == "development"

    # 서버 실행
    uvicorn.run("src.main:app", host=host, port=port, reload=reload, log_level="info")


if __name__ == "__main__":
    main()
