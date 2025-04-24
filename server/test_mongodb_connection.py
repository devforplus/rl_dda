#!/usr/bin/env python
"""
MongoDB 연결 테스트 스크립트
"""

import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# MongoDB 연결 URI
MONGODB_URI = os.getenv(
    "DATABASE_URL", "mongodb://localhost:27017/vortextion?directConnection=true"
)


async def test_connection():
    """MongoDB 연결을 테스트합니다."""
    print(f"🔄 MongoDB에 연결 중: {MONGODB_URI}")

    try:
        # 클라이언트 생성
        client = AsyncIOMotorClient(MONGODB_URI, serverSelectionTimeoutMS=5000)

        # 연결 테스트
        await client.admin.command("ping")

        # 데이터베이스 이름 출력
        database_names = await client.list_database_names()
        print(f"✅ MongoDB 연결 성공!")
        print(f"📊 사용 가능한 데이터베이스: {', '.join(database_names)}")

        # 레플리카셋 상태 확인
        try:
            rs_status = await client.admin.command("replSetGetStatus")
            print(f"🔄 레플리카셋 상태: {rs_status['set']}")
            print(f"🔄 레플리카셋 멤버:")
            for member in rs_status["members"]:
                print(f"   - {member['name']}: {member['stateStr']}")
        except Exception as e:
            print(f"⚠️ 레플리카셋이 구성되지 않았거나 접근할 수 없습니다: {str(e)}")

        # 연결 종료
        client.close()
        return True

    except Exception as e:
        print(f"❌ MongoDB 연결 실패: {str(e)}")
        return False


if __name__ == "__main__":
    print("🚀 MongoDB 연결 테스트 시작")
    result = asyncio.run(test_connection())
    if result:
        print("✨ 테스트 완료: 연결 성공")
    else:
        print("❌ 테스트 완료: 연결 실패")
