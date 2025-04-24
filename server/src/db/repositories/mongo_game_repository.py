from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from bson import ObjectId

from src.db.mongodb import get_db, COLLECTION_NAMES


class MongoGameRepository:
    """
    MongoDB를 사용하여 게임 데이터를 관리하는 레포지토리입니다.
    세션 내 게임 데이터의 CRUD 기능을 제공합니다.
    """

    def __init__(self):
        db = get_db()
        self.collection = db[COLLECTION_NAMES["GAME"]]

    async def create_game(
        self,
        session_id: str,
        user_id: str,
        name: str,
        game_type: str,
        status: str = "active",
        settings: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        새로운 게임을 생성합니다.

        Args:
            session_id: 게임이 속한 세션 ID
            user_id: 게임을 생성한 사용자 ID
            name: 게임 이름
            game_type: 게임 유형 (example: 'textGame', 'imageGame', 등)
            status: 게임 상태 (기본값: 'active')
            settings: 게임 설정
            data: 게임 데이터

        Returns:
            생성된 게임 문서
        """
        now = datetime.utcnow()

        game = {
            "sessionId": session_id,
            "userId": user_id,
            "name": name,
            "gameType": game_type,
            "status": status,
            "settings": settings or {},
            "data": data or {},
            "createdAt": now,
            "updatedAt": now,
            "lastAccessedAt": now,
        }

        result = await self.collection.insert_one(game)
        game["_id"] = result.inserted_id

        return game

    async def get_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        ID로 게임을 조회합니다.

        Args:
            game_id: 게임 ID

        Returns:
            게임 문서 또는 None (없는 경우)
        """
        try:
            game = await self.collection.find_one({"_id": ObjectId(game_id)})
            return game
        except Exception:
            return None

    async def get_session_games(
        self,
        session_id: str,
        game_type: Optional[List[str]] = None,
        status: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "updatedAt",
        sort_order: int = -1,
    ) -> List[Dict[str, Any]]:
        """
        세션에 속한 게임 목록을 조회합니다.

        Args:
            session_id: 세션 ID
            game_type: 필터링할 게임 유형 목록
            status: 필터링할 게임 상태 목록
            limit: 최대 결과 수
            offset: 시작 오프셋
            sort_by: 정렬 기준 필드
            sort_order: 정렬 순서 (1: 오름차순, -1: 내림차순)

        Returns:
            게임 문서 목록
        """
        query = {"sessionId": session_id}

        if game_type:
            query["gameType"] = {"$in": game_type}

        if status:
            query["status"] = {"$in": status}

        cursor = self.collection.find(query)
        cursor = cursor.sort(sort_by, sort_order).skip(offset).limit(limit)

        games = await cursor.to_list(length=limit)
        return games

    async def count_session_games(
        self,
        session_id: str,
        game_type: Optional[List[str]] = None,
        status: Optional[List[str]] = None,
    ) -> int:
        """
        세션에 속한 게임 수를 계산합니다.

        Args:
            session_id: 세션 ID
            game_type: 필터링할 게임 유형 목록
            status: 필터링할 게임 상태 목록

        Returns:
            게임 수
        """
        query = {"sessionId": session_id}

        if game_type:
            query["gameType"] = {"$in": game_type}

        if status:
            query["status"] = {"$in": status}

        count = await self.collection.count_documents(query)
        return count

    async def update_game(
        self, game_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        게임 정보를 업데이트합니다.

        Args:
            game_id: 게임 ID
            update_data: 업데이트할 필드와 값

        Returns:
            업데이트된 게임 문서 또는 None (실패 시)
        """
        try:
            update_data["updatedAt"] = datetime.utcnow()

            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(game_id)}, {"$set": update_data}, return_document=True
            )

            return result
        except Exception:
            return None

    async def update_game_data(
        self, game_id: str, data: Dict[str, Any], merge: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        게임 데이터를 업데이트합니다.

        Args:
            game_id: 게임 ID
            data: 업데이트할 게임 데이터
            merge: 기존 데이터와 병합할지 여부 (True: 병합, False: 대체)

        Returns:
            업데이트된 게임 문서 또는 None (실패 시)
        """
        try:
            now = datetime.utcnow()

            if merge:
                # 데이터 병합
                result = await self.collection.find_one_and_update(
                    {"_id": ObjectId(game_id)},
                    {
                        "$set": {"updatedAt": now, "lastAccessedAt": now},
                        "$merge": {"data": data},
                    },
                    return_document=True,
                )
            else:
                # 데이터 대체
                result = await self.collection.find_one_and_update(
                    {"_id": ObjectId(game_id)},
                    {"$set": {"data": data, "updatedAt": now, "lastAccessedAt": now}},
                    return_document=True,
                )

            return result
        except Exception:
            return None

    async def update_game_settings(
        self, game_id: str, settings: Dict[str, Any], merge: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        게임 설정을 업데이트합니다.

        Args:
            game_id: 게임 ID
            settings: 업데이트할 게임 설정
            merge: 기존 설정과 병합할지 여부 (True: 병합, False: 대체)

        Returns:
            업데이트된 게임 문서 또는 None (실패 시)
        """
        try:
            now = datetime.utcnow()

            if merge:
                # 설정 병합
                result = await self.collection.find_one_and_update(
                    {"_id": ObjectId(game_id)},
                    {"$set": {"updatedAt": now}, "$merge": {"settings": settings}},
                    return_document=True,
                )
            else:
                # 설정 대체
                result = await self.collection.find_one_and_update(
                    {"_id": ObjectId(game_id)},
                    {"$set": {"settings": settings, "updatedAt": now}},
                    return_document=True,
                )

            return result
        except Exception:
            return None

    async def update_game_last_accessed(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        게임의 마지막 접근 시간을 업데이트합니다.

        Args:
            game_id: 게임 ID

        Returns:
            업데이트된 게임 문서 또는 None (실패 시)
        """
        try:
            now = datetime.utcnow()

            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(game_id)},
                {"$set": {"lastAccessedAt": now}},
                return_document=True,
            )

            return result
        except Exception:
            return None

    async def delete_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        게임을 삭제합니다.

        Args:
            game_id: 게임 ID

        Returns:
            삭제된 게임 문서 또는 None (실패 시)
        """
        try:
            result = await self.collection.find_one_and_delete(
                {"_id": ObjectId(game_id)}
            )
            return result
        except Exception:
            return None

    async def delete_session_games(self, session_id: str) -> int:
        """
        세션에 속한 모든 게임을 삭제합니다.

        Args:
            session_id: 세션 ID

        Returns:
            삭제된 게임 수
        """
        try:
            result = await self.collection.delete_many({"sessionId": session_id})
            return result.deleted_count
        except Exception:
            return 0

    async def archive_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        게임을 아카이브 상태로 변경합니다.

        Args:
            game_id: 게임 ID

        Returns:
            업데이트된 게임 문서 또는 None (실패 시)
        """
        return await self.update_game(
            game_id, {"status": "archived", "updatedAt": datetime.utcnow()}
        )

    async def restore_game(self, game_id: str) -> Optional[Dict[str, Any]]:
        """
        아카이브된 게임을 활성 상태로 복원합니다.

        Args:
            game_id: 게임 ID

        Returns:
            업데이트된 게임 문서 또는 None (실패 시)
        """
        return await self.update_game(
            game_id, {"status": "active", "updatedAt": datetime.utcnow()}
        )
