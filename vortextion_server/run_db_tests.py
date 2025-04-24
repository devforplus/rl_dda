#!/usr/bin/env python
"""
데이터베이스 테스트 실행 스크립트
"""

import os
import sys
import asyncio
import uuid
from datetime import datetime
import traceback
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# MongoDB 연결 URI
MONGODB_URI = os.getenv(
    "DATABASE_URL", "mongodb://localhost:27017/vortextion?directConnection=true"
)


class Database:
    """데이터베이스 연결을 관리하는 클래스입니다."""

    def __init__(self):
        """MongoDB 클라이언트를 초기화합니다."""
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
            print(f"상세 에러: {traceback.format_exc()}")
            return False

    async def disconnect(self):
        """데이터베이스 연결을 종료합니다."""
        if self._client:
            self._client.close()
            print("MongoDB 연결 종료")

    @property
    def db(self):
        """데이터베이스 인스턴스를 반환합니다."""
        return self._db

    @property
    def sessions(self):
        """세션 컬렉션에 접근하기 위한 속성입니다."""
        return self._db["sessions"]

    @property
    def user_actions(self):
        """사용자 행동 컬렉션에 접근하기 위한 속성입니다."""
        return self._db["user_actions"]

    @property
    def dda_actions(self):
        """DDA 행동 컬렉션에 접근하기 위한 속성입니다."""
        return self._db["dda_actions"]

    @property
    def game_logs(self):
        """게임 로그 컬렉션에 접근하기 위한 속성입니다."""
        return self._db["game_logs"]


class Session:
    """세션 모델 클래스입니다."""

    def __init__(self, session_id, user_id, start_time, end_time=None):
        self.sessionId = session_id
        self.userId = user_id
        self.startTime = start_time
        self.endTime = end_time
        self.isActive = end_time is None


class UserAction:
    """사용자 행동 모델 클래스입니다."""

    def __init__(self, action_id, session_id, action_type, data, timestamp):
        self.id = action_id
        self.sessionId = session_id
        self.actionType = action_type
        self.data = data
        self.timestamp = timestamp


class DDAAction:
    """DDA 행동 모델 클래스입니다."""

    def __init__(self, action_id, session_id, action_type, data, timestamp):
        self.id = action_id
        self.sessionId = session_id
        self.actionType = action_type
        self.data = data
        self.timestamp = timestamp


class GameLog:
    """게임 로그 모델 클래스입니다."""

    def __init__(self, log_id, session_id, level, source, message, data, timestamp):
        self.id = log_id
        self.sessionId = session_id
        self.level = level
        self.source = source
        self.message = message
        self.data = data
        self.timestamp = timestamp


class SessionRepository:
    """세션 리포지토리 클래스입니다."""

    def __init__(self, db):
        self.db = db

    async def create_session(self, user_id):
        """새 세션을 생성합니다."""
        session_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        session_data = {
            "sessionId": session_id,
            "userId": user_id,
            "startTime": now,
            "endTime": None,
            "isActive": True,
        }

        await self.db.sessions.insert_one(session_data)
        return Session(session_id, user_id, now)

    async def get_session(self, session_id):
        """세션을 조회합니다."""
        session_data = await self.db.sessions.find_one({"sessionId": session_id})
        if session_data:
            return Session(
                session_data["sessionId"],
                session_data["userId"],
                session_data["startTime"],
                session_data.get("endTime"),
            )
        return None

    async def end_session(self, session_id):
        """세션을 종료합니다."""
        now = datetime.now().isoformat()

        result = await self.db.sessions.update_one(
            {"sessionId": session_id}, {"$set": {"endTime": now, "isActive": False}}
        )

        if result.modified_count > 0:
            session = await self.get_session(session_id)
            return session

        return None


class UserActionRepository:
    """사용자 행동 리포지토리 클래스입니다."""

    def __init__(self, db):
        self.db = db

    async def create_action(self, session_id, action_type, data):
        """새 사용자 행동을 생성합니다."""
        action_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        action_data = {
            "id": action_id,
            "sessionId": session_id,
            "actionType": action_type,
            "data": data,
            "timestamp": now,
        }

        await self.db.user_actions.insert_one(action_data)
        return UserAction(action_id, session_id, action_type, data, now)

    async def get_session_actions(self, session_id):
        """세션의 모든 사용자 행동을 조회합니다."""
        cursor = self.db.user_actions.find({"sessionId": session_id})
        actions = []

        async for doc in cursor:
            actions.append(
                UserAction(
                    doc["id"],
                    doc["sessionId"],
                    doc["actionType"],
                    doc["data"],
                    doc["timestamp"],
                )
            )

        return actions


class DDAActionRepository:
    """DDA 행동 리포지토리 클래스입니다."""

    def __init__(self, db):
        self.db = db

    async def create_dda_action(self, session_id, action_type, data):
        """새 DDA 행동을 생성합니다."""
        action_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        action_data = {
            "id": action_id,
            "sessionId": session_id,
            "actionType": action_type,
            "data": data,
            "timestamp": now,
        }

        await self.db.dda_actions.insert_one(action_data)
        return DDAAction(action_id, session_id, action_type, data, now)

    async def get_session_dda_actions(self, session_id):
        """세션의 모든 DDA 행동을 조회합니다."""
        cursor = self.db.dda_actions.find({"sessionId": session_id})
        actions = []

        async for doc in cursor:
            actions.append(
                DDAAction(
                    doc["id"],
                    doc["sessionId"],
                    doc["actionType"],
                    doc["data"],
                    doc["timestamp"],
                )
            )

        return actions


class LogRepository:
    """로그 리포지토리 클래스입니다."""

    def __init__(self, db):
        self.db = db

    async def create_log(self, session_id, level, source, message, data):
        """새 로그를 생성합니다."""
        log_id = str(uuid.uuid4())
        now = datetime.now().isoformat()

        log_data = {
            "id": log_id,
            "sessionId": session_id,
            "level": level,
            "source": source,
            "message": message,
            "data": data,
            "timestamp": now,
        }

        await self.db.game_logs.insert_one(log_data)
        return GameLog(log_id, session_id, level, source, message, data, now)

    async def get_session_logs(self, session_id):
        """세션의 모든 로그를 조회합니다."""
        cursor = self.db.game_logs.find({"sessionId": session_id})
        logs = []

        async for doc in cursor:
            logs.append(
                GameLog(
                    doc["id"],
                    doc["sessionId"],
                    doc["level"],
                    doc["source"],
                    doc["message"],
                    doc["data"],
                    doc["timestamp"],
                )
            )

        return logs


async def test_database_connection(db):
    """데이터베이스 연결을 테스트합니다."""
    return await db.connect()


async def test_session_operations(db):
    """세션 관련 작업을 테스트합니다."""
    try:
        session_repo = SessionRepository(db)
        print("📌 세션 리포지토리 초기화 성공")

        # 세션 생성
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        print(f"📌 테스트 사용자 ID 생성: {test_user_id}")

        session = await session_repo.create_session(test_user_id)
        print(f"✅ 세션 생성 성공: {session.sessionId}")

        # 세션 조회
        retrieved_session = await session_repo.get_session(session.sessionId)
        if retrieved_session:
            print(f"✅ 세션 조회 성공: {retrieved_session.sessionId}")
        else:
            print("❌ 세션 조회 실패: 세션을 찾을 수 없음")
            return False

        # 세션 종료
        ended_session = await session_repo.end_session(session.sessionId)
        print(f"✅ 세션 종료 성공: {ended_session.sessionId}")

        return True
    except Exception as e:
        print(f"❌ 세션 테스트 실패: {str(e)}")
        print(f"상세 에러: {traceback.format_exc()}")
        return False


async def test_user_action_operations(db):
    """사용자 행동 관련 작업을 테스트합니다."""
    try:
        session_repo = SessionRepository(db)
        action_repo = UserActionRepository(db)
        print("📌 사용자 행동 리포지토리 초기화 성공")

        # 테스트용 세션 생성
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session = await session_repo.create_session(test_user_id)
        print(f"📌 테스트 세션 생성: {session.sessionId}")

        # 사용자 행동 생성
        action = await action_repo.create_action(
            session.sessionId, "GAME_START", {"level": 1, "difficulty": "normal"}
        )
        print(f"✅ 사용자 행동 생성 성공: {action.id}")

        # 사용자 행동 조회
        actions = await action_repo.get_session_actions(session.sessionId)
        print(f"✅ 사용자 행동 조회 성공: {len(actions)} 개 조회됨")

        return True
    except Exception as e:
        print(f"❌ 사용자 행동 테스트 실패: {str(e)}")
        print(f"상세 에러: {traceback.format_exc()}")
        return False


async def test_dda_action_operations(db):
    """DDA 행동 관련 작업을 테스트합니다."""
    try:
        session_repo = SessionRepository(db)
        dda_action_repo = DDAActionRepository(db)
        print("📌 DDA 행동 리포지토리 초기화 성공")

        # 테스트용 세션 생성
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session = await session_repo.create_session(test_user_id)
        print(f"📌 테스트 세션 생성: {session.sessionId}")

        # DDA 행동 생성
        dda_action = await dda_action_repo.create_dda_action(
            session.sessionId, "DIFFICULTY_ADJUST", {"level": 2, "factor": 0.8}
        )
        print(f"✅ DDA 행동 생성 성공: {dda_action.id}")

        # DDA 행동 조회
        dda_actions = await dda_action_repo.get_session_dda_actions(session.sessionId)
        print(f"✅ DDA 행동 조회 성공: {len(dda_actions)} 개 조회됨")

        return True
    except Exception as e:
        print(f"❌ DDA 행동 테스트 실패: {str(e)}")
        print(f"상세 에러: {traceback.format_exc()}")
        return False


async def test_log_operations(db):
    """로그 관련 작업을 테스트합니다."""
    try:
        session_repo = SessionRepository(db)
        log_repo = LogRepository(db)
        print("📌 로그 리포지토리 초기화 성공")

        # 테스트용 세션 생성
        test_user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        session = await session_repo.create_session(test_user_id)
        print(f"📌 테스트 세션 생성: {session.sessionId}")

        # 로그 생성
        log = await log_repo.create_log(
            session.sessionId,
            "INFO",
            "SYSTEM",
            "게임 시작",
            {"timestamp": datetime.now().isoformat()},
        )
        print(f"✅ 로그 생성 성공")

        # 로그 조회
        logs = await log_repo.get_session_logs(session.sessionId)
        print(f"✅ 로그 조회 성공: {len(logs)} 개 조회됨")

        return True
    except Exception as e:
        print(f"❌ 로그 테스트 실패: {str(e)}")
        print(f"상세 에러: {traceback.format_exc()}")
        return False


async def cleanup_test_data(db):
    """테스트 데이터를 정리합니다."""
    try:
        # 테스트 사용자 ID로 시작하는 데이터 정리
        await db.sessions.delete_many({"userId": {"$regex": "^test_user_"}})
        print("✅ 테스트 세션 데이터 정리 완료")
        return True
    except Exception as e:
        print(f"❌ 테스트 데이터 정리 실패: {str(e)}")
        print(f"상세 에러: {traceback.format_exc()}")
        return False


async def main():
    """메인 테스트 함수"""
    print("🚀 데이터베이스 테스트 시작\n")

    # 데이터베이스 연결
    db = Database()

    try:
        # 데이터베이스 연결 테스트
        if not await test_database_connection(db):
            print("❌ 데이터베이스 연결 실패로 테스트를 중단합니다.")
            return

        print("\n📝 세션 테스트")
        if not await test_session_operations(db):
            print("❌ 세션 테스트 실패로 테스트를 중단합니다.")
            return

        print("\n📝 사용자 행동 테스트")
        if not await test_user_action_operations(db):
            print("❌ 사용자 행동 테스트 실패로 테스트를 중단합니다.")
            return

        print("\n📝 DDA 행동 테스트")
        if not await test_dda_action_operations(db):
            print("❌ DDA 행동 테스트 실패로 테스트를 중단합니다.")
            return

        print("\n📝 로그 테스트")
        if not await test_log_operations(db):
            print("❌ 로그 테스트 실패로 테스트를 중단합니다.")
            return

        print("\n🧹 테스트 데이터 정리")
        if not await cleanup_test_data(db):
            print("⚠️ 테스트 데이터 정리 실패")
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {str(e)}")
        print(f"상세 에러: {traceback.format_exc()}")
    finally:
        # 데이터베이스 연결 종료
        try:
            await db.disconnect()
            print("\n✅ 데이터베이스 연결 종료")
        except Exception as e:
            print(f"\n❌ 데이터베이스 연결 종료 실패: {str(e)}")

    print("\n✨ 테스트 완료")


if __name__ == "__main__":
    asyncio.run(main())
