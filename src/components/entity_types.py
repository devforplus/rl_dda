from enum import IntEnum, auto


# 엔티티 타입 열거형 정의
class EntityType(IntEnum):
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

    # 적 종류별 ID
    ENEMY_A = 10  # 기본 적
    ENEMY_B = 11  # 사인파 이동 적
    ENEMY_C = 12  # 수직 이동 적
    ENEMY_D = 13  # 수직 이동 적
    ENEMY_E = 14  # 좌측에서 등장하는 적
    ENEMY_F = 15  # 수직 발사 적
    ENEMY_G = 16  # 좌우 이동 적
    ENEMY_H = 17  # 점프하는 적
    ENEMY_I = 18  # 수직 이동 적
    ENEMY_J = 19  # 보스 방어 포탑
    ENEMY_K = 20  # 보스 1 (원형)
    ENEMY_L = 21  # 보스 2 (큰 잎)
    ENEMY_M = 22  # 보스 3 (눈)
    ENEMY_N = 23  # 수직 이동 적
    ENEMY_O = 24  # 기본 적
    ENEMY_P = 25  # 각도 발사 적
