from config.player.player_config import PlayerConfig


def test_player_config_initialization():
    """
    PlayerConfig 초기화 테스트

    목적: PlayerConfig가 올바르게 초기화되는지 검증

    Notes:
        이 테스트는 PlayerConfig의 기본 속성값에 의존합니다.
        기본값이 변경될 경우 이 테스트도 함께 수정해야 합니다.
    """
    config = PlayerConfig()
    assert config.starting_lives == 3
    assert config.max_lives == 9
    assert config.max_weapons == 3
    assert config.max_weapon_level == 5
    assert config.weapon_names == ["A", "B", "C"]
    assert config.max_hp == 3
    assert config.invincibility_frames == 120
    assert config.damage_invincibility_frames == 60


def test_player_config_custom_initialization():
    """
    PlayerConfig 사용자 정의 초기화 테스트

    목적: PlayerConfig에 사용자 정의 값을 설정하여 올바르게 초기화되는지 검증

    Notes:
        이 테스트는 특정 사용자 정의 값에 의존합니다.
        요구사항이 변경되어 사용자 정의 값이 달라질 경우 이 테스트도 함께 수정해야 합니다.
    """
    custom_config = PlayerConfig(
        starting_lives=5,
        max_lives=10,
        max_weapons=4,
        max_weapon_level=6,
        weapon_names=["X", "Y", "Z"],
        max_hp=5,
        invincibility_frames=180,
        damage_invincibility_frames=90,
    )
    assert custom_config.starting_lives == 5
    assert custom_config.max_lives == 10
    assert custom_config.max_weapons == 4
    assert custom_config.max_weapon_level == 6
    assert custom_config.weapon_names == ["X", "Y", "Z"]
    assert custom_config.max_hp == 5
    assert custom_config.invincibility_frames == 180
    assert custom_config.damage_invincibility_frames == 90


def test_player_config_type_validation():
    """
    PlayerConfig 속성 타입 검증 테스트

    목적: PlayerConfig의 속성들이 올바른 타입으로 유지되는지 검증
    """
    config = PlayerConfig()
    assert isinstance(config.starting_lives, int)
    assert isinstance(config.max_lives, int)
    assert isinstance(config.max_weapons, int)
    assert isinstance(config.max_weapon_level, int)
    assert isinstance(config.weapon_names, list)
    assert all(isinstance(name, str) for name in config.weapon_names)
    assert isinstance(config.max_hp, int)
    assert isinstance(config.invincibility_frames, int)
    assert isinstance(config.damage_invincibility_frames, int)


def test_player_config_equality():
    """
    PlayerConfig 동등성 테스트

    목적: 동일한 속성값을 가진 두 PlayerConfig 인스턴스가 동등한지 검증
    """
    config1 = PlayerConfig(
        starting_lives=5,
        max_lives=10,
        max_hp=5,
        invincibility_frames=180,
        damage_invincibility_frames=90,
    )
    config2 = PlayerConfig(
        starting_lives=5,
        max_lives=10,
        max_hp=5,
        invincibility_frames=180,
        damage_invincibility_frames=90,
    )
    assert config1 == config2


def test_player_config_inequality():
    """
    PlayerConfig 비동등성 테스트

    목적: 다른 속성값을 가진 두 PlayerConfig 인스턴스가 다른지 검증
    """
    config1 = PlayerConfig(
        starting_lives=5,
        max_lives=10,
        max_hp=5,
        invincibility_frames=180,
        damage_invincibility_frames=90,
    )
    config2 = PlayerConfig(
        starting_lives=3,
        max_lives=9,
        max_hp=3,
        invincibility_frames=120,
        damage_invincibility_frames=60,
    )
    assert config1 != config2
