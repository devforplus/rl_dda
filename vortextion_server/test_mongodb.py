import asyncio
import sys
from datetime import datetime

from src.db.mongodb import connect_to_mongodb, close_mongodb_connection
from src.db.repositories.mongo_session_repository import MongoSessionRepository
from src.db.repositories.mongo_user_action_repository import MongoUserActionRepository
from src.db.repositories.mongo_dda_action_repository import MongoDDAActionRepository


async def test_mongodb_connection():
    """MongoDB 연결 테스트"""
    print("MongoDB 연결 테스트 시작...")

    # 연결 시도
    connection_success = await connect_to_mongodb()

    if connection_success:
        print("✅ MongoDB 연결 성공")
    else:
        print("❌ MongoDB 연결 실패")
        return False

    return True


async def test_session_repository():
    """세션 저장소 기능 테스트"""
    print("\n세션 저장소 테스트 시작...")

    try:
        repo = MongoSessionRepository()

        # 테스트용 사용자 ID와 콘텐츠 ID
        test_user_id = "test_user_123"
        test_content_id = "test_content_456"

        # 1. 세션 생성 테스트
        print("1. 세션 생성 테스트...")
        session = await repo.create_session(
            user_id=test_user_id, content_id=test_content_id, device_info="테스트 기기"
        )

        if session and "_id" in session:
            print(f"✅ 세션 생성 성공: {session['_id']}")
            session_id = str(session["_id"])
        else:
            print("❌ 세션 생성 실패")
            return False

        # 2. 세션 조회 테스트
        print("2. 세션 조회 테스트...")
        fetched_session = await repo.get_session(session_id)

        if fetched_session and fetched_session["userId"] == test_user_id:
            print(f"✅ 세션 조회 성공: {fetched_session['userId']}")
        else:
            print("❌ 세션 조회 실패")
            return False

        # 3. 세션 업데이트 테스트
        print("3. 세션 업데이트 테스트...")
        update_data = {"deviceInfo": "업데이트된 테스트 기기"}
        updated_session = await repo.update_session(session_id, update_data)

        if (
            updated_session
            and updated_session["deviceInfo"] == "업데이트된 테스트 기기"
        ):
            print("✅ 세션 업데이트 성공")
        else:
            print("❌ 세션 업데이트 실패")
            return False

        # 4. 세션 종료 테스트
        print("4. 세션 종료 테스트...")
        ended_session = await repo.end_session(session_id)

        if (
            ended_session
            and ended_session["status"] == "completed"
            and ended_session["endTime"]
        ):
            print("✅ 세션 종료 성공")
        else:
            print("❌ 세션 종료 실패")
            return False

        # 5. 세션 삭제 테스트
        print("5. 세션 삭제 테스트...")
        deleted_session = await repo.delete_session(session_id)

        if deleted_session:
            print("✅ 세션 삭제 성공")
        else:
            print("❌ 세션 삭제 실패")
            return False

        return True

    except Exception as e:
        print(f"❌ 세션 저장소 테스트 중 오류 발생: {str(e)}")
        return False


async def test_user_action_repository():
    """사용자 액션 저장소 기능 테스트"""
    print("\n사용자 액션 저장소 테스트 시작...")

    try:
        session_repo = MongoSessionRepository()
        action_repo = MongoUserActionRepository()

        # 테스트용 세션 생성
        test_user_id = "test_user_123"
        test_content_id = "test_content_456"

        session = await session_repo.create_session(
            user_id=test_user_id, content_id=test_content_id, device_info="테스트 기기"
        )

        session_id = str(session["_id"])
        print(f"테스트용 세션 생성: {session_id}")

        # 1. 사용자 액션 생성 테스트
        print("1. 사용자 액션 생성 테스트...")
        action_data = {"button": "play", "position": {"x": 100, "y": 200}}

        action = await action_repo.create_user_action(
            session_id=session_id, action_type="click", data=action_data
        )

        if action and "_id" in action:
            print(f"✅ 사용자 액션 생성 성공: {action['_id']}")
            action_id = str(action["_id"])
        else:
            print("❌ 사용자 액션 생성 실패")
            await session_repo.delete_session(session_id)
            return False

        # 2. 사용자 액션 조회 테스트
        print("2. 사용자 액션 조회 테스트...")
        fetched_action = await action_repo.get_user_action(action_id)

        if fetched_action and fetched_action["sessionId"] == session_id:
            print(f"✅ 사용자 액션 조회 성공")
        else:
            print("❌ 사용자 액션 조회 실패")
            await session_repo.delete_session(session_id)
            return False

        # 3. 세션 액션 목록 조회 테스트
        print("3. 세션 액션 목록 조회 테스트...")
        actions = await action_repo.get_session_actions(session_id)

        if actions and len(actions) > 0:
            print(f"✅ 세션 액션 목록 조회 성공: {len(actions)}개")
        else:
            print("❌ 세션 액션 목록 조회 실패")
            await session_repo.delete_session(session_id)
            return False

        # 4. 액션 타입 조회 테스트
        print("4. 액션 타입 조회 테스트...")
        action_types = await action_repo.get_action_types_by_session(session_id)

        if action_types and "click" in action_types:
            print(f"✅ 액션 타입 조회 성공: {action_types}")
        else:
            print("❌ 액션 타입 조회 실패")
            await session_repo.delete_session(session_id)
            return False

        # 5. 사용자 액션 삭제 테스트
        print("5. 사용자 액션 삭제 테스트...")
        deleted_action = await action_repo.delete_user_action(action_id)

        if deleted_action:
            print("✅ 사용자 액션 삭제 성공")
        else:
            print("❌ 사용자 액션 삭제 실패")
            await session_repo.delete_session(session_id)
            return False

        # 테스트용 세션 삭제
        await session_repo.delete_session(session_id)
        print(f"테스트용 세션 삭제 완료")

        return True

    except Exception as e:
        print(f"❌ 사용자 액션 저장소 테스트 중 오류 발생: {str(e)}")
        return False


async def test_dda_action_repository():
    """DDA 액션 저장소 기능 테스트"""
    print("\nDDA 액션 저장소 테스트 시작...")

    try:
        session_repo = MongoSessionRepository()
        dda_repo = MongoDDAActionRepository()

        # 테스트용 세션 생성
        test_user_id = "test_user_123"
        test_content_id = "test_content_456"

        session = await session_repo.create_session(
            user_id=test_user_id, content_id=test_content_id, device_info="테스트 기기"
        )

        session_id = str(session["_id"])
        print(f"테스트용 세션 생성: {session_id}")

        # 1. DDA 액션 생성 테스트
        print("1. DDA 액션 생성 테스트...")
        action_data = {
            "difficulty": "medium",
            "reason": "player_score_average",
            "old_value": 0.5,
            "new_value": 0.7,
        }

        action = await dda_repo.create_dda_action(
            session_id=session_id, action_type="difficulty_adjustment", data=action_data
        )

        if action and "_id" in action:
            print(f"✅ DDA 액션 생성 성공: {action['_id']}")
            action_id = str(action["_id"])
        else:
            print("❌ DDA 액션 생성 실패")
            await session_repo.delete_session(session_id)
            return False

        # 2. DDA 액션 조회 테스트
        print("2. DDA 액션 조회 테스트...")
        fetched_action = await dda_repo.get_dda_action(action_id)

        if fetched_action and fetched_action["sessionId"] == session_id:
            print(f"✅ DDA 액션 조회 성공")
        else:
            print("❌ DDA 액션 조회 실패")
            await session_repo.delete_session(session_id)
            return False

        # 3. 세션 DDA 액션 목록 조회 테스트
        print("3. 세션 DDA 액션 목록 조회 테스트...")
        actions = await dda_repo.get_session_dda_actions(session_id)

        if actions and len(actions) > 0:
            print(f"✅ 세션 DDA 액션 목록 조회 성공: {len(actions)}개")
        else:
            print("❌ 세션 DDA 액션 목록 조회 실패")
            await session_repo.delete_session(session_id)
            return False

        # 4. DDA 액션 타입 조회 테스트
        print("4. DDA 액션 타입 조회 테스트...")
        action_types = await dda_repo.get_dda_action_types_by_session(session_id)

        if action_types and "difficulty_adjustment" in action_types:
            print(f"✅ DDA 액션 타입 조회 성공: {action_types}")
        else:
            print("❌ DDA 액션 타입 조회 실패")
            await session_repo.delete_session(session_id)
            return False

        # 5. DDA 액션 삭제 테스트
        print("5. DDA 액션 삭제 테스트...")
        deleted_action = await dda_repo.delete_dda_action(action_id)

        if deleted_action:
            print("✅ DDA 액션 삭제 성공")
        else:
            print("❌ DDA 액션 삭제 실패")
            await session_repo.delete_session(session_id)
            return False

        # 테스트용 세션 삭제
        await session_repo.delete_session(session_id)
        print(f"테스트용 세션 삭제 완료")

        return True

    except Exception as e:
        print(f"❌ DDA 액션 저장소 테스트 중 오류 발생: {str(e)}")
        return False


async def run_tests():
    """모든 테스트 실행"""
    print("=== MongoDB 테스트 시작 ===\n")

    # 1. 연결 테스트
    connection_successful = await test_mongodb_connection()
    if not connection_successful:
        print("❌ MongoDB 연결 실패로 테스트 중단")
        return False

    # 2. 세션 저장소 테스트
    session_repo_successful = await test_session_repository()
    if not session_repo_successful:
        print("❌ 세션 저장소 테스트 실패")

    # 3. 사용자 액션 저장소 테스트
    user_action_successful = await test_user_action_repository()
    if not user_action_successful:
        print("❌ 사용자 액션 저장소 테스트 실패")

    # 4. DDA 액션 저장소 테스트
    dda_action_successful = await test_dda_action_repository()
    if not dda_action_successful:
        print("❌ DDA 액션 저장소 테스트 실패")

    # 모든 테스트 결과 확인
    all_tests_passed = (
        connection_successful
        and session_repo_successful
        and user_action_successful
        and dda_action_successful
    )

    if all_tests_passed:
        print("\n✅ 모든 테스트 성공!")
    else:
        print("\n⚠️ 일부 테스트 실패")

    # MongoDB 연결 종료
    await close_mongodb_connection()
    print("\nMongoDB 연결 종료")

    return all_tests_passed


if __name__ == "__main__":
    # 테스트 실행
    print("MongoDB 테스트 스크립트 실행\n")

    result = asyncio.run(run_tests())

    # 종료 코드 설정 (성공: 0, 실패: 1)
    sys.exit(0 if result else 1)
