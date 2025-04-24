import asyncio
import json
import random
import uuid
import aiohttp
import logging
from datetime import datetime

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("game_test")

# 서버 URL
BASE_URL = "http://localhost:8000/api"

# 테스트 사용자 ID
TEST_USER_ID = f"test_user_{uuid.uuid4().hex[:8]}"


async def start_game():
    """게임을 시작하고 세션 ID를 반환합니다."""
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/game/start"
        params = {"user_id": TEST_USER_ID}

        logger.info(f"게임 시작 요청: 사용자 ID = {TEST_USER_ID}")
        async with session.post(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                # session_id 또는 sessionId 필드에서 세션 ID 추출
                session_id = data.get("session_id", data.get("sessionId"))
                logger.info(f"게임 시작 성공: 세션 ID = {session_id}")
                return session_id
            else:
                error = await response.text()
                logger.error(f"게임 시작 실패: {error}")
                return None


async def send_user_action(session_id, action_type, action_data):
    """유저 액션을 서버에 전송합니다."""
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/user-actions/"
        data = {
            "session_id": session_id,
            "action_type": action_type,
            "data": json.dumps(action_data),
        }

        logger.info(f"유저 액션 전송: 타입 = {action_type}")
        async with session.post(url, json=data) as response:
            if response.status == 200:
                logger.info("유저 액션 전송 성공")
                return await response.json()
            else:
                error = await response.text()
                logger.error(f"유저 액션 전송 실패: {error}")
                return None


async def apply_dda(session_id, action_type, parameters):
    """DDA 액션을 서버에 전송합니다."""
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/dda-actions/"
        data = {
            "session_id": session_id,
            "action_type": action_type,
            "parameters": json.dumps(parameters),
        }

        logger.info(f"DDA 액션 전송: 타입 = {action_type}")
        async with session.post(url, json=data) as response:
            if response.status == 200:
                logger.info("DDA 액션 전송 성공")
                return await response.json()
            else:
                error = await response.text()
                logger.error(f"DDA 액션 전송 실패: {error}")
                return None


async def add_log(session_id, level, category, message, data=None):
    """로그를 서버에 기록합니다."""
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/logs/"
        log_data = {
            "session_id": session_id,
            "level": level,
            "category": category,
            "message": message,
            "data": json.dumps(data) if data else "{}",
        }

        logger.info(f"로그 기록: 카테고리 = {category}, 메시지 = {message}")
        async with session.post(url, json=log_data) as response:
            if response.status == 200:
                logger.info("로그 기록 성공")
                return await response.json()
            else:
                error = await response.text()
                logger.error(f"로그 기록 실패: {error}")
                return None


async def get_game_status(session_id):
    """게임 상태를 조회합니다."""
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/game/status/{session_id}"

        logger.info(f"게임 상태 조회: 세션 ID = {session_id}")
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                logger.info("게임 상태 조회 성공")
                return data
            else:
                error = await response.text()
                logger.error(f"게임 상태 조회 실패: {error}")
                return None


async def end_game(session_id):
    """게임을 종료합니다."""
    async with aiohttp.ClientSession() as session:
        url = f"{BASE_URL}/game/end"
        params = {"session_id": session_id}

        logger.info(f"게임 종료 요청: 세션 ID = {session_id}")
        async with session.post(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                logger.info("게임 종료 성공")
                return data
            else:
                error = await response.text()
                logger.error(f"게임 종료 실패: {error}")
                return None


async def simulate_gameplay(session_id):
    """게임 플레이를 시뮬레이션합니다."""
    # 게임 레벨 시작 로그
    await add_log(
        session_id=session_id,
        level="INFO",
        category="LEVEL",
        message="레벨 1 시작",
        data={"level_id": "level_1", "difficulty": "normal"},
    )

    # 플레이어 움직임 시뮬레이션
    for i in range(5):
        x = random.randint(0, 800)
        y = random.randint(0, 600)
        direction = random.choice(["up", "down", "left", "right"])

        await send_user_action(
            session_id=session_id,
            action_type="MOVEMENT",
            action_data={"x": x, "y": y, "direction": direction},
        )

        await asyncio.sleep(0.5)  # 액션 간 지연

    # 아이템 사용 시뮬레이션
    await send_user_action(
        session_id=session_id,
        action_type="ITEM_USE",
        action_data={"item_id": "health_potion", "effect": "heal", "amount": 50},
    )

    # DDA 적용 시뮬레이션
    await apply_dda(
        session_id=session_id,
        action_type="DIFFICULTY_ADJUST",
        parameters={"difficulty": 0.75, "spawn_rate": 1.2, "enemy_speed": 0.9},
    )

    # 게임 이벤트 로그
    await add_log(
        session_id=session_id,
        level="INFO",
        category="GAME_EVENT",
        message="보스 등장",
        data={"boss_id": "dragon", "hp": 1000},
    )

    # 몬스터 처치 시뮬레이션
    await send_user_action(
        session_id=session_id,
        action_type="COMBAT",
        action_data={"target_id": "dragon", "damage": 250, "weapon": "sword"},
    )

    # 레벨 클리어 로그
    await add_log(
        session_id=session_id,
        level="INFO",
        category="LEVEL",
        message="레벨 1 클리어",
        data={"time_taken": 120, "score": 850},
    )


async def main():
    """메인 테스트 함수"""
    logger.info("===== 게임 테스트 시작 =====")

    # 게임 시작
    session_id = await start_game()
    if not session_id:
        logger.error("게임 시작 실패로 테스트를 종료합니다")
        return

    # 게임 플레이 시뮬레이션
    await simulate_gameplay(session_id)

    # 게임 상태 조회
    status = await get_game_status(session_id)
    if status:
        logger.info(f"세션 상태: active = {status['is_active']}")
        logger.info(f"유저 액션 수: {len(status['recent_actions'])}")
        logger.info(f"DDA 액션 수: {len(status['recent_dda_actions'])}")

    # 게임 종료
    await end_game(session_id)

    logger.info("===== 게임 테스트 완료 =====")


if __name__ == "__main__":
    asyncio.run(main())
