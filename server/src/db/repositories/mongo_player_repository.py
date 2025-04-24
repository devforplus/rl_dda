from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
from bson.objectid import ObjectId
from src.db.mongodb import get_db, COLLECTION_NAMES


class MongoPlayerRepository:
    """플레이어 데이터를 관리하는 리포지토리 클래스입니다."""

    def __init__(self):
        db = get_db()
        self.collection = db[COLLECTION_NAMES["PLAYER"]]

    async def create_player(
        self, user_id: str, session_id: str, name: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """새 플레이어를 생성합니다."""
        now = datetime.utcnow()

        player_doc = {
            "userId": user_id,
            "sessionId": session_id,
            "name": name,
            "data": data,
            "createdAt": now,
            "updatedAt": now,
        }

        result = await self.collection.insert_one(player_doc)
        if result.inserted_id:
            return await self.collection.find_one({"_id": result.inserted_id})
        raise Exception("플레이어 생성 실패")

    async def get_player(self, player_id: str) -> Optional[Dict[str, Any]]:
        """플레이어 ID로 특정 플레이어를 조회합니다."""
        if not ObjectId.is_valid(player_id):
            return None
        return await self.collection.find_one({"_id": ObjectId(player_id)})

    async def get_player_by_user_and_session(
        self, user_id: str, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """유저 ID와 세션 ID로 플레이어를 조회합니다."""
        return await self.collection.find_one(
            {"userId": user_id, "sessionId": session_id}
        )

    async def get_session_players(self, session_id: str) -> List[Dict[str, Any]]:
        """특정 세션의 모든 플레이어를 조회합니다."""
        cursor = self.collection.find({"sessionId": session_id})
        return await cursor.to_list(length=None)

    async def update_player(
        self, player_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """플레이어 정보를 업데이트합니다."""
        if not ObjectId.is_valid(player_id):
            return None

        # updatedAt 필드 자동 업데이트
        update_data["updatedAt"] = datetime.utcnow()

        # 업데이트 필드만 설정
        update_fields = {}
        if "name" in update_data:
            update_fields["name"] = update_data["name"]
        if "data" in update_data:
            update_fields["data"] = update_data["data"]
        update_fields["updatedAt"] = update_data["updatedAt"]

        result = await self.collection.update_one(
            {"_id": ObjectId(player_id)}, {"$set": update_fields}
        )

        if result.modified_count:
            return await self.collection.find_one({"_id": ObjectId(player_id)})
        return None

    async def update_player_data(
        self, player_id: str, data: Dict[str, Any], merge: bool = True
    ) -> Optional[Dict[str, Any]]:
        """플레이어의 데이터 필드만 업데이트합니다."""
        if not ObjectId.is_valid(player_id):
            return None

        now = datetime.utcnow()

        if merge:
            # 데이터 병합
            update_ops = {"$set": {"updatedAt": now}}

            # 병합 로직
            for key, value in data.items():
                update_ops["$set"][f"data.{key}"] = value

            result = await self.collection.update_one(
                {"_id": ObjectId(player_id)}, update_ops
            )
        else:
            # 데이터 대체
            result = await self.collection.update_one(
                {"_id": ObjectId(player_id)}, {"$set": {"data": data, "updatedAt": now}}
            )

        if result.modified_count:
            return await self.collection.find_one({"_id": ObjectId(player_id)})
        return None

    async def delete_player(self, player_id: str) -> Optional[Dict[str, Any]]:
        """플레이어를 삭제합니다."""
        if not ObjectId.is_valid(player_id):
            return None

        # 삭제 전에 문서 가져오기
        player = await self.collection.find_one({"_id": ObjectId(player_id)})
        if not player:
            return None

        result = await self.collection.delete_one({"_id": ObjectId(player_id)})
        if result.deleted_count:
            return player
        return None

    async def delete_session_players(self, session_id: str) -> int:
        """세션의 모든 플레이어를 삭제합니다."""
        result = await self.collection.delete_many({"sessionId": session_id})
        return result.deleted_count
