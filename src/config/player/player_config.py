from dataclasses import dataclass, field
from typing import List


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
