from datetime import datetime
from typing import Optional, List, Dict, Any
from bson.objectid import ObjectId
from src.db.mongodb import get_db, COLLECTION_NAMES


class MongoDDAActionRepository:
    """DDA 액션을 관리하는 리포지토리 클래스입니다."""

    def __init__(self):
        db = get_db()
        self.collection = db[COLLECTION_NAMES["DDA_ACTION"]]

    async def create_dda_action(
        self,
        session_id: str,
        action_type: str,
        data: Dict[str, Any],
        timestamp: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """새로운 DDA 액션을 생성하고 저장합니다."""
        now = timestamp or datetime.utcnow()

        action_doc = {
            "sessionId": session_id,
            "actionType": action_type,
            "data": data,
            "timestamp": now,
            "createdAt": now,
        }

        result = await self.collection.insert_one(action_doc)
        if result.inserted_id:
            return await self.collection.find_one({"_id": result.inserted_id})
        raise Exception("DDA 액션 생성 실패")

    async def get_dda_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        """액션 ID로 DDA 액션을 조회합니다."""
        if not ObjectId.is_valid(action_id):
            return None

        return await self.collection.find_one({"_id": ObjectId(action_id)})

    async def get_session_dda_actions(
        self,
        session_id: str,
        action_types: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """세션의 DDA 액션 목록을 조회합니다."""
        query = {"sessionId": session_id}

        if action_types:
            query["actionType"] = {"$in": action_types}

        if start_time or end_time:
            time_query = {}
            if start_time:
                time_query["$gte"] = start_time
            if end_time:
                time_query["$lte"] = end_time
            if time_query:
                query["timestamp"] = time_query

        cursor = self.collection.find(query)
        cursor = cursor.sort("timestamp", 1).skip(offset).limit(limit)

        return await cursor.to_list(length=None)

    async def get_dda_action_types_by_session(self, session_id: str) -> List[str]:
        """세션에서 사용된 DDA 액션 타입 목록을 조회합니다."""
        pipeline = [
            {"$match": {"sessionId": session_id}},
            {"$group": {"_id": "$actionType"}},
            {"$project": {"_id": 0, "actionType": "$_id"}},
        ]

        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        return [doc["actionType"] for doc in results]

    async def delete_dda_action(self, action_id: str) -> Optional[Dict[str, Any]]:
        """DDA 액션을 삭제합니다."""
        if not ObjectId.is_valid(action_id):
            return None

        # 삭제 전에 문서 가져오기
        action = await self.collection.find_one({"_id": ObjectId(action_id)})
        if not action:
            return None

        result = await self.collection.delete_one({"_id": ObjectId(action_id)})
        if result.deleted_count:
            return action
        return None

    async def delete_session_dda_actions(self, session_id: str) -> int:
        """세션의 모든 DDA 액션을 삭제합니다."""
        result = await self.collection.delete_many({"sessionId": session_id})
        return result.deleted_count

    async def count_session_dda_actions(
        self, session_id: str, action_types: Optional[List[str]] = None
    ) -> int:
        """세션의 DDA 액션 수를 계산합니다."""
        query = {"sessionId": session_id}
        if action_types:
            query["actionType"] = {"$in": action_types}

        return await self.collection.count_documents(query)
