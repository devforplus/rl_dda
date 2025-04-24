from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.core.config import Config
from src.core.logging import setup_logging
from src.db.connection import db
from .routes import sessions, logs, user_actions, dda_actions, game

# 설정 및 로깅 초기화
config = Config()
logger = setup_logging(config)

# FastAPI 애플리케이션 생성
app = FastAPI(
    title=config.get("GAME_TITLE"),
    version=config.get("GAME_VERSION"),
    description="Vortextion 게임 서버 API",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경에서는 모든 오리진 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
app.include_router(sessions.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(user_actions.router, prefix="/api")
app.include_router(dda_actions.router, prefix="/api")
app.include_router(game.router, prefix="/api")


# 시작 이벤트 핸들러 - 데이터베이스 연결
@app.on_event("startup")
async def startup_event():
    logger.info("서버 시작 중...")
    await db.connect()
    logger.info("데이터베이스 연결 성공")


# 종료 이벤트 핸들러 - 데이터베이스 연결 종료
@app.on_event("shutdown")
async def shutdown_event():
    logger.info("서버 종료 중...")
    await db.disconnect()
    logger.info("데이터베이스 연결 종료")


# 상태 확인 엔드포인트
@app.get("/")
async def health_check():
    return {"status": "healthy", "version": config.get("GAME_VERSION")}
