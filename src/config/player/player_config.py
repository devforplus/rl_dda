from dataclasses import dataclass, field
from typing import List, Dict, Tuple


@dataclass
class PlayerConfig:
    """
    플레이어 설정 데이터 클래스

    Attributes:
        starting_lives (int): 초기 목숨 수 (기본값: 3)
        max_lives (int): 최대 목숨 수 (기본값: 9)
        max_weapons (int): 최대 무기의 수 (기본값: 3)
        max_weapon_level (int): 최대 무기 레벨 (기본값: 5)
        weapon_names (list[str]): 무기 이름 목록 (기본값: ["A", "B", "C"])
        max_shots (int): 최대 발사체 수 (기본값: 4)
        uv_frame_offset (int): UV 프레임 오프셋 (기본값: 1)
        shot_size (int): 발사체 크기 (기본값: 14)
        uv_offset_y (int): UV Y축 오프셋 (기본값: 16)
        speed_levels (Tuple[int, ...]): 무기 레벨별 속도 (기본값: (10, 10, 11, 11, 12, 12))
        damage_levels (Dict[int, List[int]]): 무기 타입별 데미지 레벨 (기본값: {0: [1,1,1,1,1,2], 1: [1,1,1,2,2,3], 2: [1,1,2,2,3,3]})
        max_hp (int): 최대 체력 (기본값: 3)
        invincibility_frames (int): 피격 후 무적 시간 (기본값: 60)
        damage_invincibility_frames (int): 피격 후 무적 시간 (기본값: 60)
        bomb_damage (int): 폭탄 데미지 (기본값: 30)

    Examples:
        >>> config = PlayerConfig()
        >>> config.starting_lives
        3
        >>> config.weapon_names
        ['A', 'B', 'C']

    Notes:
        현재 속성들의 기본값들은 기존 레거시 코드의 상수값을 기반으로 합니다.
        현재 `weapon_names`는 게임 내에서 직접 사용되지 않으며,
        기본적으로 ["A", "B", "C"] 값을 가집니다.
        향후 게임 설정에서 무기 이름을 변경하는 기능을 구현할 때 유용할 수 있습니다.

        `starting_lives`, `max_lives`, `max_weapons`, `max_weapon_level`은
        `src/system/const.py`에서 상수로 정의되어 게임 전반에 걸쳐 사용됩니다.

        ### TODO: 코드 리팩토링 과정에서 이 클래스의 위치가 변경될 수 있습니다.
        ### 향후 리팩토링 시 주석의 정확성을 다시 확인해야 합니다.
    """

    starting_lives: int = 3  # 초기 목숨 수
    max_lives: int = 9  # 최대 목숨 수
    max_weapons: int = 3  # 최대 무기의 수
    max_weapon_level: int = 5  # 최대 무기 레벨
    weapon_names: List[str] = field(
        default_factory=lambda: ["A", "B", "C"]
    )  # 무기 이름 목록
    
    # 발사체 관련 설정
    max_shots: int = 4  # 최대 발사체 수
    uv_frame_offset: int = 1  # UV 프레임 오프셋
    shot_size: int = 14  # 발사체 크기
    uv_offset_y: int = 16  # UV Y축 오프셋
    speed_levels: Tuple[int, ...] = field(
        default_factory=lambda: (10, 10, 11, 11, 12, 12)
    )  # 무기 레벨별 속도
    damage_levels: Dict[int, List[int]] = field(
        default_factory=lambda: {
            0: [1, 1, 1, 1, 1, 2],  # fwd
            1: [1, 1, 1, 2, 2, 3],  # spread/diagonal
            2: [1, 1, 2, 2, 3, 3],  # back/fwd
        }
    )

    # HP 관련 설정
    max_hp: int = 3  # 최대 체력
    invincibility_frames: int = 120  # 초기 무적 시간
    damage_invincibility_frames: int = 60  # 피격 후 무적 시간

    # 폭탄 관련 설정
    bomb_damage: int = 30  # 폭탄 데미지
