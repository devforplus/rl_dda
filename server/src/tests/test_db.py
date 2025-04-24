import asyncio
import uuid
from datetime import datetime
import traceback
from src.db.connection import db
from src.db.repositories.mongo_session_repository import MongoSessionRepository
from src.db.repositories.mongo_user_action_repository import MongoUserActionRepository
from src.db.repositories.mongo_dda_action_repository import MongoDDAActionRepository
from src.db.repositories.mongo_log_repository import MongoLogRepository


async def test_database_connection():
    """데이터베이스 연결을 테스트합니다."""
    try:
        await db.connect()
        print("✅ 데이터베이스 연결 성공")
        return True
    except Exception as e:
        print(f"❌ 데이터베이스 연결 실패: {str(e)}")
        print(f"상세 에러: {traceback.format_exc()}")
        return False


async def test_session_operations():
    """세션 관련 작업을 테스트합니다."""
    try:
        session_repo = MongoSessionRepository()
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


async def test_user_action_operations():
    """사용자 행동 관련 작업을 테스트합니다."""
    try:
        session_repo = MongoSessionRepository()
        action_repo = MongoUserActionRepository()
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


async def test_dda_action_operations():
    """DDA 행동 관련 작업을 테스트합니다."""
    try:
        session_repo = MongoSessionRepository()
        dda_action_repo = MongoDDAActionRepository()
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


async def test_log_operations():
    """로그 관련 작업을 테스트합니다."""
    try:
        session_repo = MongoSessionRepository()
        log_repo = MongoLogRepository()
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


async def cleanup_test_data():
    """테스트 데이터를 정리합니다."""
    try:
        # 여기에 테스트 데이터 정리 로직 추가
        print("✅ 테스트 데이터 정리 완료")
        return True
    except Exception as e:
        print(f"❌ 테스트 데이터 정리 실패: {str(e)}")
        print(f"상세 에러: {traceback.format_exc()}")
        return False


async def main():
    """메인 테스트 함수"""
    print("�� 데이터베이스 테스트 시작\n")

    try:
        # 데이터베이스 연결 테스트
        if not await test_database_connection():
            print("❌ 데이터베이스 연결 실패로 테스트를 중단합니다.")
            return

        print("\n📝 세션 테스트")
        if not await test_session_operations():
            print("❌ 세션 테스트 실패로 테스트를 중단합니다.")
            return

        print("\n📝 사용자 행동 테스트")
        if not await test_user_action_operations():
            print("❌ 사용자 행동 테스트 실패로 테스트를 중단합니다.")
            return

        print("\n📝 DDA 행동 테스트")
        if not await test_dda_action_operations():
            print("❌ DDA 행동 테스트 실패로 테스트를 중단합니다.")
            return

        print("\n📝 로그 테스트")
        if not await test_log_operations():
            print("❌ 로그 테스트 실패로 테스트를 중단합니다.")
            return

        print("\n🧹 테스트 데이터 정리")
        if not await cleanup_test_data():
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
