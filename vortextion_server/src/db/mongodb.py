import os
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# MongoDB 연결 URI
MONGODB_URI = os.getenv(
    "DATABASE_URL", "mongodb://localhost:27017/vortextion?directConnection=true"
)

# 전역 클라이언트 및 데이터베이스 인스턴스
_client = None
_db = None


async def connect_to_mongodb():
    """
    MongoDB에 연결하고 연결 상태를 반환합니다.
    애플리케이션 시작 시 호출해야 합니다.
    """
    global _client, _db

    if _client is not None:
        # 이미 연결되어 있음
        return True

    try:
        _client = AsyncIOMotorClient(MONGODB_URI)
        _db = _client.get_database()

        # 연결 테스트
        await _client.admin.command("ping")
        print(f"MongoDB 연결 성공: {MONGODB_URI}")
        return True
    except Exception as e:
        print(f"MongoDB 연결 실패: {str(e)}")
        return False


async def close_mongodb_connection():
    """
    MongoDB 연결을 종료합니다.
    애플리케이션 종료 시 호출해야 합니다.
    """
    global _client

    if _client is not None:
        _client.close()
        _client = None
        print("MongoDB 연결 종료")


def get_db():
    """
    데이터베이스 인스턴스를 반환합니다.
    이 함수는 리포지토리 클래스에서 DB 접근에 사용됩니다.
    """
    global _db

    if _db is None:
        # 클라이언트가 연결되지 않은 경우 기본값으로 초기화
        # 실제 연결은 첫 번째 쿼리 시 수행됨
        if _client is None:
            _client = AsyncIOMotorClient(MONGODB_URI)
            _db = _client.get_database()
            print(f"MongoDB 지연 연결 초기화: {MONGODB_URI}")

    return _db


# 컬렉션 이름 상수
COLLECTION_NAMES = {
    "SESSION": "sessions",
    "USER_ACTION": "user_actions",
    "DDA_ACTION": "dda_actions",
    "GAME_LOG": "game_logs",
    "PLAYER": "players",
    "GAME": "games",
    "USER": "users",
}


def get_collection(collection_name):
    """
    지정된 컬렉션에 대한 참조를 반환합니다.

    Args:
        collection_name: 컬렉션 이름 (COLLECTION_NAMES 상수 사용 권장)

    Returns:
        컬렉션 참조
    """
    return get_db()[collection_name]
