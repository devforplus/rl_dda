from .sound_type import SoundType
from dataclasses import dataclass


@dataclass
class SoundConfig:
    """
    사운드 관련 상수 정의 클래스

    Attributes:
        SND_PRIORITY (dict): 사운드 타입별 우선순위 정의
        SOUND_CHANNEL_GAIN_DEFAULT (float): 기본 사운드 채널 게인값
        sounds_res_file (str): 사운드 리소스 파일 이름 (기본값: "sounds.pyxres")
    """

    # 사운드 우선순위 딕셔너리
    # 키: SoundType - 사운드 효과음 타입
    # 값: 우선순위 (높을수록 우선 재생)
    SND_PRIORITY = {
        SoundType.EXPLODE_SMALL: 5,  # 작은 폭발 효과음 우선순위
        SoundType.BLIP: 4,  # 기본 UI 효과음 우선순위
        SoundType.WEAPON_POWERUP: 10,  # 무기 업그레이드 효과음 우선순위
        SoundType.LIFE_POWERUP: 10,  # 목숨 증가 효과음 우선순위
        SoundType.BOMB_POWERUP: 10,  # 폭탄 업그레이드 효과음 우선순위
    }

    # 기본 사운드 채널 게인값 (0.0 ~ 1.0 범위)
    SOUND_CHANNEL_GAIN_DEFAULT = 0.125  # 기본 게인값 (12.5%)

    # 사운드 채널 상수 정의
    # 타이틀 화면 음악은 모든 채널(0-3)을 사용
    # 스테이지 내 음악은 채널 0-2를 사용
    SOUND_CHANNEL = 3  # 사운드 효과음 전용 채널

    sounds_res_file: str = "sounds.pyxres"  # 사운드 리소스 파일 이름
