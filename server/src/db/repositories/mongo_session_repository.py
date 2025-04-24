from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from bson import ObjectId
import uuid

from src.db.mongodb import get_db, COLLECTION_NAMES


class MongoSessionRepository:
    """
    MongoDB를 사용하여 세션 데이터를 관리하는 레포지토리입니다.
    사용자 세션의 CRUD 기능과 세션 메타데이터 관리 기능을 제공합니다.
    """

    def __init__(self):
        db = get_db()
        self.collection = db[COLLECTION_NAMES["SESSION"]]

    async def create_session(
        self, user_id: str, content_id: str, device_info: str
    ) -> Dict[str, Any]:
        """새로운 세션을 생성하고 저장합니다."""
        now = datetime.utcnow()

        session_doc = {
            "userId": user_id,
            "contentId": content_id,
            "deviceInfo": device_info,
            "startTime": now,
            "endTime": None,
            "status": "active",
            "createdAt": now,
            "updatedAt": now,
        }

        result = await self.collection.insert_one(session_doc)
        if result.inserted_id:
            return await self.collection.find_one({"_id": result.inserted_id})
        raise Exception("세션 생성 실패")

    async def end_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션을 종료 상태로 변경합니다."""
        if not ObjectId.is_valid(session_id):
            return None

        now = datetime.utcnow()

        result = await self.collection.update_one(
            {"_id": ObjectId(session_id), "status": "active"},
            {"$set": {"endTime": now, "status": "completed", "updatedAt": now}},
        )

        if result.modified_count:
            return await self.collection.find_one({"_id": ObjectId(session_id)})
        return None

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션 ID로 세션 정보를 조회합니다."""
        if not ObjectId.is_valid(session_id):
            return None

        return await self.collection.find_one({"_id": ObjectId(session_id)})

    async def get_active_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """사용자의 활성 세션 목록을 조회합니다."""
        cursor = self.collection.find({"userId": user_id, "status": "active"}).sort(
            "startTime", -1
        )

        return await cursor.to_list(length=None)

    async def get_user_sessions(
        self,
        user_id: str,
        content_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """사용자의 세션 기록을 조회합니다."""
        query = {"userId": user_id}

        if content_id:
            query["contentId"] = content_id

        cursor = self.collection.find(query)
        cursor = cursor.sort("startTime", -1).skip(offset).limit(limit)

        return await cursor.to_list(length=None)

    async def get_content_sessions(
        self, content_id: str, limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """특정 콘텐츠에 대한 모든 세션을 조회합니다."""
        cursor = self.collection.find({"contentId": content_id})
        cursor = cursor.sort("startTime", -1).skip(offset).limit(limit)

        return await cursor.to_list(length=None)

    async def count_user_sessions(
        self, user_id: str, content_id: Optional[str] = None
    ) -> int:
        """사용자의 세션 수를 계산합니다."""
        query = {"userId": user_id}
        if content_id:
            query["contentId"] = content_id

        return await self.collection.count_documents(query)

    async def delete_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """세션을 삭제합니다."""
        if not ObjectId.is_valid(session_id):
            return None

        # 삭제 전에 문서 가져오기
        session = await self.collection.find_one({"_id": ObjectId(session_id)})
        if not session:
            return None

        result = await self.collection.delete_one({"_id": ObjectId(session_id)})
        if result.deleted_count:
            return session
        return None

    async def update_session(
        self, session_id: str, update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        세션 정보를 업데이트합니다.

        Args:
            session_id: 세션 ID
            update_data: 업데이트할 필드와 값

        Returns:
            업데이트된 세션 문서 또는 None (실패 시)
        """
        try:
            update_data["updatedAt"] = datetime.utcnow()

            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(session_id)},
                {"$set": update_data},
                return_document=True,
            )

            return result
        except Exception:
            return None

    async def update_session_settings(
        self, session_id: str, settings: Dict[str, Any], merge: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        세션 설정을 업데이트합니다.

        Args:
            session_id: 세션 ID
            settings: 업데이트할 세션 설정
            merge: 기존 설정과 병합할지 여부 (True: 병합, False: 대체)

        Returns:
            업데이트된 세션 문서 또는 None (실패 시)
        """
        try:
            now = datetime.utcnow()

            if merge:
                # 설정 병합 (MongoDB 5.0 이상에서 지원)
                # 이전 버전에서는 $set과 함께 도트 표기법 사용 필요
                update_ops = {"$set": {"updatedAt": now}}

                # 병합 로직
                for key, value in settings.items():
                    update_ops["$set"][f"settings.{key}"] = value

                result = await self.collection.find_one_and_update(
                    {"_id": ObjectId(session_id)}, update_ops, return_document=True
                )
            else:
                # 설정 대체
                result = await self.collection.find_one_and_update(
                    {"_id": ObjectId(session_id)},
                    {"$set": {"settings": settings, "updatedAt": now}},
                    return_document=True,
                )

            return result
        except Exception:
            return None

    async def add_session_tags(
        self, session_id: str, tags: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        세션에 태그를 추가합니다.

        Args:
            session_id: 세션 ID
            tags: 추가할 태그 목록

        Returns:
            업데이트된 세션 문서 또는 None (실패 시)
        """
        try:
            now = datetime.utcnow()

            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(session_id)},
                {"$addToSet": {"tags": {"$each": tags}}, "$set": {"updatedAt": now}},
                return_document=True,
            )

            return result
        except Exception:
            return None

    async def remove_session_tags(
        self, session_id: str, tags: List[str]
    ) -> Optional[Dict[str, Any]]:
        """
        세션에서 태그를 제거합니다.

        Args:
            session_id: 세션 ID
            tags: 제거할 태그 목록

        Returns:
            업데이트된 세션 문서 또는 None (실패 시)
        """
        try:
            now = datetime.utcnow()

            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(session_id)},
                {"$pull": {"tags": {"$in": tags}}, "$set": {"updatedAt": now}},
                return_document=True,
            )

            return result
        except Exception:
            return None

    async def update_session_last_accessed(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        세션의 마지막 접근 시간을 업데이트합니다.

        Args:
            session_id: 세션 ID

        Returns:
            업데이트된 세션 문서 또는 None (실패 시)
        """
        try:
            now = datetime.utcnow()

            result = await self.collection.find_one_and_update(
                {"_id": ObjectId(session_id)},
                {"$set": {"lastAccessedAt": now}},
                return_document=True,
            )

            return result
        except Exception:
            return None

    async def archive_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        세션을 아카이브 상태로 변경합니다.

        Args:
            session_id: 세션 ID

        Returns:
            업데이트된 세션 문서 또는 None (실패 시)
        """
        return await self.update_session(
            session_id, {"status": "archived", "updatedAt": datetime.utcnow()}
        )

    async def restore_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        아카이브된 세션을 활성 상태로 복원합니다.

        Args:
            session_id: 세션 ID

        Returns:
            업데이트된 세션 문서 또는 None (실패 시)
        """
        return await self.update_session(
            session_id, {"status": "active", "updatedAt": datetime.utcnow()}
        )

    async def get_user_session_stats(self, user_id: str) -> Dict[str, Any]:
        """
        사용자의 세션 통계를 조회합니다.

        Args:
            user_id: 사용자 ID

        Returns:
            세션 통계 (상태별 세션 수, 총 세션 수 등)
        """
        pipeline = [
            {"$match": {"userId": user_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]

        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)

        # 결과를 딕셔너리로 변환
        stats = {"total": 0}
        for item in results:
            status = item["_id"]
            count = item["count"]
            stats[status] = count
            stats["total"] += count

        return stats

    async def get_all_tags(self, user_id: str) -> List[Dict[str, Any]]:
        """
        사용자의 모든 고유 태그를 조회합니다.

        Args:
            user_id: 사용자 ID

        Returns:
            태그 목록 (태그명과 사용 횟수)
        """
        pipeline = [
            {"$match": {"userId": user_id}},
            {"$unwind": "$tags"},
            {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
            {"$project": {"_id": 0, "tag": "$_id", "count": 1}},
            {"$sort": {"count": -1}},
        ]

        cursor = self.collection.aggregate(pipeline)
        results = await cursor.to_list(length=None)
        return results
