from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from typing import Optional
from pydantic import BaseModel

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


class User(BaseModel):
    """사용자 정보를 나타내는 모델"""

    id: str
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: bool = True


# 인증 테스트용 더미 데이터
fake_users_db = {
    "test_user": {
        "id": "user_1234",
        "username": "testuser",
        "email": "test@example.com",
        "full_name": "Test User",
        "is_active": True,
    }
}


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    """
    토큰을 통해 현재 사용자 정보를 가져오는 의존성 함수

    현재는 테스트를 위해 토큰과 관계없이 test_user를 반환합니다.
    실제 구현에서는 토큰을 검증하고 해당 사용자를 찾아야 합니다.
    """
    # 테스트용 고정 유저 사용
    user_dict = fake_users_db["test_user"]
    return User(**user_dict)


# 개발 환경에서만 사용하는 간소화된 권한 검사 함수
def verify_user_permissions(user_id: str, resource_owner_id: str) -> bool:
    """
    사용자가 리소스에 접근할 권한이 있는지 확인합니다.

    Args:
        user_id: 요청 사용자 ID
        resource_owner_id: 리소스 소유자 ID

    Returns:
        bool: 권한 있음 여부
    """
    # 현재는 단순히 ID 일치 여부만 확인
    return user_id == resource_owner_id
