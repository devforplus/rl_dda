from config.sound.sound_type import SoundType


def test_sound_type_enum_values():
    """
    SoundType enum 값 테스트

    목적: SoundType enum 값이 올바르게 정의되었는지 검증
    """
    assert isinstance(SoundType.RESERVED_MUSIC_0, SoundType)
    assert isinstance(SoundType.EXPLODE_SMALL, SoundType)
    assert isinstance(SoundType.BLIP, SoundType)


def test_sound_type_enum_uniqueness():
    """
    SoundType enum 값 유일성 테스트

    목적: SoundType enum 값들이 유일한지 검증
    """
    values = [item.value for item in SoundType]
    assert len(values) == len(set(values))  # 중복된 값이 없어야 함
