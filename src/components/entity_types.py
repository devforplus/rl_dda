from enum import Enum, auto


# 엔티티 타입 열거형 정의
class EntityType(Enum):
    """게임 내 엔티티 타입 정의.

    Attributes:
        PLAYER: 플레이어 객체를 나타냅니다.
        PLAYER_SHOT: 플레이어가 발사하는 발사체를 나타냅니다.
        ENEMY: 적 객체를 나타냅니다.
        ENEMY_SHOT: 적이 발사하는 발사체를 나타냅니다.
        POWERUP: 플레이어에게 특별한 능력을 부여하는 파워업 아이템을 나타냅니다.
        BACKGROUND: 게임의 배경을 나타냅니다.
    """

    PLAYER = 0  # 플레이어
    PLAYER_SHOT = auto()  # 플레이어 발사체
    ENEMY = auto()  # 적
    ENEMY_SHOT = auto()  # 적 발사체
    POWERUP = auto()  # 파워업 아이템
    BACKGROUND = auto()  # 배경
