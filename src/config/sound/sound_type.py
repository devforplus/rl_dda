from enum import IntEnum, auto


class SoundType(IntEnum):
    """
    사운드 효과음 타입 정의

    Attributes:
        RESERVED_MUSIC_*: 음악 로딩용 예약 사운드
        EXPLODE_SMALL: 작은 폭발 효과음
        BLIP: 기본 효과음
        WEAPON_POWERUP: 무기 업그레이드 효과음
        LIFE_POWERUP: 목숨 증가 효과음
        BOMB_POWERUP: 폭탄 업그레이드 효과음
    """

    # 음악 로딩용 예약 사운드 (0-3)
    RESERVED_MUSIC_0 = 0
    RESERVED_MUSIC_1 = auto()  # 예약 사운드 1
    RESERVED_MUSIC_2 = auto()  # 예약 사운드 2
    RESERVED_MUSIC_3 = auto()  # 예약 사운드 3

    # 게임 내 효과음
    EXPLODE_SMALL = auto()  # 작은 폭발 효과음
    BLIP = auto()  # 기본 UI 효과음
    WEAPON_POWERUP = auto()  # 무기 업그레이드 효과음
    LIFE_POWERUP = auto()  # 목숨 증가 효과음
    BOMB_POWERUP = auto()  # 폭탄 업그레이드 효과음
