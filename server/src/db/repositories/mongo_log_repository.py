from datetime import datetime
from typing import Optional, List, Dict, Any
import uuid
from bson.objectid import ObjectId
from src.db.mongodb import get_db, COLLECTION_NAMES


class MongoLogRepository:
    """게임 로그를 관리하는 리포지토리 클래스입니다."""

    def __init__(self):
        db = get_db()
        self.collection = db[COLLECTION_NAMES["GAME_LOG"]]

    async def create_log(
        self, session_id: str, level: str, category: str, message: str, data: str
    ) -> Dict[str, Any]:
        """새로운 게임 로그를 기록합니다."""
        now = datetime.utcnow()

        log_doc = {
            "sessionId": session_id,
            "level": level,
            "category": category,
            "message": message,
            "data": data,
            "timestamp": now,
        }

        result = await self.collection.insert_one(log_doc)
        if result.inserted_id:
            return await self.collection.find_one({"_id": result.inserted_id})
        raise Exception("로그 기록 실패")

    async def get_log(self, log_id: str) -> Optional[Dict[str, Any]]:
        """로그 ID로 특정 로그를 조회합니다."""
        if not ObjectId.is_valid(log_id):
            return None
        return await self.collection.find_one({"_id": ObjectId(log_id)})

    async def get_session_logs(
        self,
        session_id: str,
        level: Optional[str] = None,
        category: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        sort_order: str = "desc",
    ) -> List[Dict[str, Any]]:
        """특정 세션의 로그를 필터링하여 조회합니다."""
        query = {"sessionId": session_id}

        if level:
            query["level"] = level

        if category:
            query["category"] = category

        if start_time or end_time:
            time_query = {}
            if start_time:
                time_query["$gte"] = start_time
            if end_time:
                time_query["$lte"] = end_time

            if time_query:
                query["timestamp"] = time_query

        cursor = self.collection.find(query)
        cursor = cursor.sort("timestamp", -1 if sort_order == "desc" else 1)
        cursor = cursor.skip(offset).limit(limit)

        return await cursor.to_list(length=None)

    async def get_log_categories(self, session_id: str) -> List[str]:
        """특정 세션에서 사용된 모든 로그 카테고리를 조회합니다."""
        pipeline = [
            {"$match": {"sessionId": session_id}},
            {"$group": {"_id": "$category"}},
            {"$project": {"_id": 0, "category": "$_id"}},
        ]

        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        return [doc["category"] for doc in results]

    async def get_log_levels(self, session_id: str) -> List[str]:
        """특정 세션에서 사용된 모든 로그 레벨을 조회합니다."""
        pipeline = [
            {"$match": {"sessionId": session_id}},
            {"$group": {"_id": "$level"}},
            {"$project": {"_id": 0, "level": "$_id"}},
        ]

        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        return [doc["level"] for doc in results]

    async def delete_log(self, log_id: str) -> Optional[Dict[str, Any]]:
        """로그를 삭제합니다."""
        if not ObjectId.is_valid(log_id):
            return None

        # 삭제 전에 문서 가져오기
        log = await self.collection.find_one({"_id": ObjectId(log_id)})
        if not log:
            return None

        result = await self.collection.delete_one({"_id": ObjectId(log_id)})
        if result.deleted_count:
            return log
        return None

    async def delete_session_logs(self, session_id: str) -> int:
        """세션의 모든 로그를 삭제합니다."""
        result = await self.collection.delete_many({"sessionId": session_id})
        return result.deleted_count

    async def count_session_logs(
        self,
        session_id: str,
        level: Optional[str] = None,
        category: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> int:
        """특정 세션의 로그 수를 계산합니다."""
        query = {"sessionId": session_id}

        if level:
            query["level"] = level

        if category:
            query["category"] = category

        if start_time or end_time:
            time_query = {}
            if start_time:
                time_query["$gte"] = start_time
            if end_time:
                time_query["$lte"] = end_time

            if time_query:
                query["timestamp"] = time_query

        return await self.collection.count_documents(query)
