from config.sound.sound_config import SoundConfig
from config.sound.sound_type import SoundType


def test_sound_config_snd_priority_structure():
    """
    사운드 우선순위 딕셔너리 구조 테스트

    목적: SND_PRIORITY가 올바른 구조로 정의되었는지 검증
    """
    assert isinstance(SoundConfig.SND_PRIORITY, dict)
    assert all(isinstance(key, SoundType) for key in SoundConfig.SND_PRIORITY.keys())
    assert all(isinstance(value, int) for value in SoundConfig.SND_PRIORITY.values())


def test_sound_config_snd_priority_values():
    """
    사운드 우선순위 값 테스트

    목적: SND_PRIORITY의 값이 올바른 범위 내에 있는지 검증
    """
    for priority in SoundConfig.SND_PRIORITY.values():
        assert isinstance(priority, int)
        assert priority >= 0  # 우선순위는 음수가 아니어야 함


def test_sound_config_sound_channel_gain_default():
    """
    기본 사운드 채널 게인값 테스트

    목적: SOUND_CHANNEL_GAIN_DEFAULT가 올바른 범위 내에 있는지 검증
    """
    assert isinstance(SoundConfig.SOUND_CHANNEL_GAIN_DEFAULT, float)
    assert (
        0.0 <= SoundConfig.SOUND_CHANNEL_GAIN_DEFAULT <= 1.0
    )  # 게인값은 0.0 ~ 1.0 사이여야 함


def test_sound_config_sound_channel():
    """
    사운드 채널 상수 테스트

    목적: SOUND_CHANNEL가 올바른 값인지 검증
    """
    assert SoundConfig.SOUND_CHANNEL == 3  # 사운드 효과음 전용 채널이 3인지 확인
