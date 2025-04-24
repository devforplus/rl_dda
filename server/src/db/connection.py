from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from typing import Optional
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

# MongoDB 연결 URI
MONGODB_URI = os.getenv(
    "DATABASE_URL", "mongodb://localhost:27017/vortextion?directConnection=true"
)


class Database:
    """데이터베이스 연결을 관리하는 싱글톤 클래스입니다."""

    _instance: Optional["Database"] = None
    _client: Optional[AsyncIOMotorClient] = None
    _db: Optional[AsyncIOMotorDatabase] = None

    def __new__(cls):
        """싱글톤 패턴을 구현합니다."""
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """MongoDB 클라이언트를 초기화합니다."""
        if self._client is None:
            self._client = AsyncIOMotorClient(MONGODB_URI)
            self._db = self._client.get_database()

    async def connect(self):
        """데이터베이스에 연결합니다."""
        try:
            # 연결 테스트
            await self._client.admin.command("ping")
            print(f"MongoDB 연결 성공: {MONGODB_URI}")
            return True
        except Exception as e:
            print(f"MongoDB 연결 실패: {str(e)}")
            return False

    async def disconnect(self):
        """데이터베이스 연결을 종료합니다."""
        if self._client:
            self._client.close()
            print("MongoDB 연결 종료")

    @property
    def db(self) -> AsyncIOMotorDatabase:
        """데이터베이스 인스턴스를 반환합니다."""
        return self._db

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

    @property
    def sessions(self):
        """세션 컬렉션에 접근하기 위한 속성입니다."""
        return self._db[self.COLLECTION_NAMES["SESSION"]]

    @property
    def user_actions(self):
        """사용자 행동 컬렉션에 접근하기 위한 속성입니다."""
        return self._db[self.COLLECTION_NAMES["USER_ACTION"]]

    @property
    def dda_actions(self):
        """DDA 행동 컬렉션에 접근하기 위한 속성입니다."""
        return self._db[self.COLLECTION_NAMES["DDA_ACTION"]]

    @property
    def game_logs(self):
        """게임 로그 컬렉션에 접근하기 위한 속성입니다."""
        return self._db[self.COLLECTION_NAMES["GAME_LOG"]]

    @property
    def users(self):
        """사용자 컬렉션에 접근하기 위한 속성입니다."""
        return self._db[self.COLLECTION_NAMES["USER"]]

    @property
    def games(self):
        """게임 컬렉션에 접근하기 위한 속성입니다."""
        return self._db[self.COLLECTION_NAMES["GAME"]]


# 싱글톤 인스턴스 생성
db = Database()
