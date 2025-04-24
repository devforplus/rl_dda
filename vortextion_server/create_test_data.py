import asyncio
from datetime import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

# MongoDB 연결 URI
MONGODB_URI = os.getenv("DATABASE_URL", "mongodb://localhost:27017/vortextion")


async def create_test_data():
    """MongoDB에 테스트 데이터를 삽입합니다."""
    print(f"MongoDB 연결 중: {MONGODB_URI}")
    client = AsyncIOMotorClient(MONGODB_URI)
    db = client.get_database()

    # 테스트 사용자 ID 및 콘텐츠 ID
    test_user_id = "test_user_123"
    test_content_id = "test_content_456"
    now = datetime.utcnow()

    # 1. 세션 생성
    print("세션 데이터 생성 중...")
    session = {
        "userId": test_user_id,
        "contentId": test_content_id,
        "deviceInfo": "테스트 기기",
        "startTime": now,
        "endTime": None,
        "status": "active",
        "createdAt": now,
        "updatedAt": now,
    }

    session_result = await db.sessions.insert_one(session)
    session_id = str(session_result.inserted_id)
    print(f"세션 생성됨, ID: {session_id}")

    # 2. 사용자 액션 생성
    print("사용자 액션 데이터 생성 중...")
    for i in range(5):
        user_action = {
            "sessionId": session_id,
            "actionType": f"test_action_{i}",
            "data": {
                "button": "play",
                "position": {"x": 100 + i * 10, "y": 200 + i * 10},
            },
            "timestamp": now,
            "createdAt": now,
        }

        user_action_result = await db.user_actions.insert_one(user_action)
        print(f"사용자 액션 생성됨, ID: {user_action_result.inserted_id}")

    # 3. DDA 액션 생성
    print("DDA 액션 데이터 생성 중...")
    for i in range(3):
        dda_action = {
            "sessionId": session_id,
            "actionType": f"dda_action_{i}",
            "data": {
                "difficulty": f"level_{i}",
                "parameter": 0.5 + i * 0.1,
                "reason": "test_reason",
            },
            "timestamp": now,
            "createdAt": now,
        }

        dda_action_result = await db.dda_actions.insert_one(dda_action)
        print(f"DDA 액션 생성됨, ID: {dda_action_result.inserted_id}")

    # 4. 게임 로그 생성
    print("게임 로그 데이터 생성 중...")
    game_log = {
        "sessionId": session_id,
        "level": 1,
        "score": 100,
        "duration": 300,
        "completed": True,
        "timestamp": now,
        "createdAt": now,
    }

    game_log_result = await db.game_logs.insert_one(game_log)
    print(f"게임 로그 생성됨, ID: {game_log_result.inserted_id}")

    print("\n모든 테스트 데이터가 성공적으로 생성되었습니다.")
    print("이제 MongoDB Compass에서 데이터를 확인할 수 있습니다.")
    print(f"연결 문자열: {MONGODB_URI}")


if __name__ == "__main__":
    # 테스트 실행
    print("MongoDB 테스트 데이터 생성 스크립트 실행\n")
    asyncio.run(create_test_data())
