import json
from typing import List, Optional, Any

# 사운드 관련 설정 및 경로 임포트
from config.sound import SoundType, SoundConfig  # 사운드 타입 및 상수 정의
from config.paths import ASSETS_DIR  # 에셋 디렉토리 경로

import pyxel as px


class AudioManager:
    """
    오디오 관리 클래스

    게임 내 음악과 사운드 효과음을 관리합니다.

    ### 속성
    - `last_sound_played`: 마지막으로 재생된 사운드
    - `gain`: 현재 게인값

    ### 주요 기능
    - 음악 로드 및 재생
    - 사운드 효과음 재생
    - 음악 볼륨 제어
    """

    last_sound_played: Optional[SoundType]
    gain: float

    def __init__(self) -> None:
        """
        오디오 관리자를 초기화합니다.

        마지막으로 재생된 사운드와 게인값을 초기화합니다.
        """
        # 마지막으로 재생된 사운드 저장
        self.last_sound_played = None
        # 현재 게인값 초기화
        self.gain = SoundConfig.SOUND_CHANNEL_GAIN_DEFAULT

    def load_music(self, file: str) -> List[List[Any]]:
        """
        JSON 파일로부터 음악 데이터를 로드합니다.

        ### 파라미터
        - `file` (`str`): 로드할 음악 파일명 (확장자 포함)

        ### 반환값
        - (`List[List[Any]]`): 로드된 음악 데이터

        ### 사용 예시
        ```python
        music_data = audio_manager.load_music("title_music.json")
        ```
        """
        with open(
            ASSETS_DIR / file, "rt"
        ) as fin:  # 지정된 경로의 파일을 텍스트 모드로 읽기 위해 오픈
            return json.loads(
                fin.read()
            )  # 파일 내용을 읽어 JSON 데이터로 파싱하여 반환

    def play_music(
        self,
        music: List[List[Any]],
        doLoop: bool = True,
        num_channels: int = 4,
        theTick: Optional[int] = None,
    ) -> None:
        """
        음악을 재생합니다.

        ### 파라미터
        - `music` (`List[List[Any]]`): 재생할 음악 데이터
        - `doLoop` (`bool`): 루프 재생 여부 (기본값: `True`)
        - `num_channels` (`int`): 사용 채널 수 (기본값: 4)
        - `theTick` (`Optional[int]`): 시작 틱 (기본값: `None`)

        ### 사용 예시
        ```python
        audio_manager.play_music(music_data, doLoop=True, num_channels=3)
        ```
        """
        for ch, sound in enumerate(music):  # 음악 데이터 내 각 사운드에 대해 반복
            px.sounds[ch].set(*sound)  # type: ignore  # 사운드 설정
            px.play(ch, ch, tick=theTick, loop=doLoop)  # 사운드 재생
            if ch == num_channels - 1:  # 지정된 채널 수까지만 재생
                break

    def reset_music_gain(self, num_channels: int = 4) -> None:
        """
        모든 채널의 게인을 기본값으로 초기화합니다.

        ### 파라미터
        - `num_channels` (`int`): 초기화할 채널 수 (기본값: 4)

        ### 사용 예시
        ```python
        audio_manager.reset_music_gain(num_channels=3)
        ```
        """
        # 지정된 수의 채널에 대해 게인값 초기화
        for i in range(num_channels):
            px.channels[
                i
            ].gain = (
                SoundConfig.SOUND_CHANNEL_GAIN_DEFAULT
            )  # 각 채널의 게인을 기본값으로 설정

    def fade_out_music(self, num_channels: int = 4) -> float:
        """
        음악의 볼륨을 점진적으로 낮춰서 페이드아웃합니다.

        ### 파라미터
        - `num_channels` (`int`): 페이드아웃할 채널 수 (기본값: 4)

        ### 반환값
        - (`float`): 업데이트된 게인값

        ### 사용 예시
        ```python
        gain = audio_manager.fade_out_music(num_channels=3)
        ```
        """
        # 게인값이 0보다 큰 경우에만 페이드아웃 진행
        if self.gain > 0:
            self.gain = max(0, self.gain - 0.001)  # 게인값을 점진적으로 감소
            if self.gain == 0:  # 게인값이 0이 되면 음악 정지
                self.stop_music(num_channels)
            else:
                # 모든 채널의 게인을 현재 게인값으로 업데이트
                for i in range(num_channels):
                    px.channels[i].gain = self.gain
        return self.gain  # 현재 게인값 반환

    def stop_music(self, num_channels: int = 4) -> None:
        """
        지정된 수의 채널에서 음악 재생을 중지합니다.

        ### 파라미터
        - `num_channels` (`int`): 중지할 채널 수 (기본값: 4)

        ### 사용 예시
        ```python
        audio_manager.stop_music(num_channels=3)
        ```
        """
        # 지정된 수의 채널에 대해 음악 재생 중지
        for i in range(num_channels):
            px.stop(i)  # 각 채널의 음악 재생을 중지

    def is_music_playing(self) -> bool:
        """
        음악이 재생 중인지 확인합니다.

        ### 반환값
        - (`bool`): 음악 재생 중이면 `True`, 아니면 `False`

        ### 사용 예시
        ```python
        is_playing = audio_manager.is_music_playing()
        ```
        """
        # 채널 0의 재생 위치를 확인하여 음악 재생 여부 판단
        return px.play_pos(0) is not None

    def play_sound(
        self, sound: SoundType, doLoop: bool = False, priority: bool = False
    ) -> None:
        """
        사운드 효과음을 재생합니다.

        ### 파라미터
        - `sound` (`SoundType`): 재생할 사운드 타입
        - `doLoop` (`bool`): 루프 재생 여부 (기본값: `False`)
        - `priority` (`bool`): 우선 재생 여부 (기본값: `False`)

        ### 사용 예시
        ```python
        audio_manager.play_sound(SoundType.EXPLODE_SMALL, doLoop=False, priority=True)
        ```
        """
        # 현재 사운드 채널이 사용 중인지 확인
        is_channel_busy = px.play_pos(SoundConfig.SOUND_CHANNEL) is not None

        if not is_channel_busy:  # 채널이 비어있으면 바로 재생
            px.play(SoundConfig.SOUND_CHANNEL, snd=sound, loop=doLoop)
            self.last_sound_played = sound  # 마지막으로 재생된 사운드 업데이트
        else:  # 채널이 사용 중인 경우
            if self.last_sound_played is not None:
                # 우선 재생이거나 현재 사운드의 우선순위가 더 높을 때 재생
                if (
                    priority
                    or SoundConfig.SND_PRIORITY[sound]
                    >= SoundConfig.SND_PRIORITY[self.last_sound_played]
                ):
                    px.play(SoundConfig.SOUND_CHANNEL, snd=sound, loop=doLoop)
                    self.last_sound_played = sound  # 마지막으로 재생된 사운드 업데이트
            else:  # last_sound_played가 None인 경우 (첫 사운드 재생)
                px.play(SoundConfig.SOUND_CHANNEL, snd=sound, loop=doLoop)
                self.last_sound_played = sound  # 마지막으로 재생된 사운드 업데이트

    def stop_sound(self) -> None:
        """
        사운드 채널의 사운드 재생을 중지합니다.

        ### 사용 예시
        ```python
        audio_manager.stop_sound()
        ```
        """
        # 사운드 채널의 사운드 재생을 중지
        px.stop(SoundConfig.SOUND_CHANNEL)
