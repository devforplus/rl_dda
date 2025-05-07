"""
적 관련 설정을 정의하는 모듈입니다.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class EnemyConfig:
    """
    적 관련 설정 데이터 클래스

    Attributes:
        bomb_damage (int): 폭탄 데미지 (기본값: 2)
        base_damage (int): 적 기본 데미지 (기본값: 1)
        hit_invincibility_frames (int): 피격 시 무적 프레임 수 (기본값: 5)
        spawn_invincibility_frames (int): 생성 시 무적 프레임 수 (기본값: 15)
        base_hp (int): 기본 체력 (기본값: 2)
        shot_speed (int): 적 총알 기본 속도 (기본값: 2)
        shot_size (int): 적 총알 크기 (기본값: 4)
        shot_colour (int): 적 총알 색상 (기본값: 8)
        shot_uv_offset (Tuple[int, int]): 적 총알 UV 오프셋 (기본값: (6, 102))

    Examples:
        >>> config = EnemyConfig()
        >>> config.bomb_damage
        2
        >>> config.base_hp
        2

    Notes:
        현재 속성들의 기본값들은 기존 레거시 코드의 상수값을 기반으로 합니다.
        적의 종류별로 다른 설정이 필요한 경우, 이 클래스를 상속하여 구현할 수 있습니다.
    """

    # 데미지 관련 설정
    bomb_damage: int = 2  # 폭탄 데미지
    base_damage: int = 1  # 적 기본 데미지

    # 무적 상태 관련 설정
    hit_invincibility_frames: int = 5  # 피격 시 무적 프레임 수
    spawn_invincibility_frames: int = 15  # 생성 시 무적 프레임 수

    # 체력 관련 설정
    base_hp: int = 2  # 기본 체력

    # 발사체 관련 설정
    shot_speed: int = 2  # 적 총알 기본 속도
    shot_size: int = 4  # 적 총알 크기
    shot_colour: int = 8  # 적 총알 색상 (빨간색)
    shot_uv_offset: Tuple[int, int] = field(
        default_factory=lambda: (6, 102)
    )  # 적 총알 UV 오프셋 (u, v) 