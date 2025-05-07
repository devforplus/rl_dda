import pyxel as px

from components.sprite import Sprite
from config.sound import SoundType
from audio import AudioManager

# 폭발 애니메이션 프레임 정보
FRAMES = ((0, 64), (16, 64), (32, 64))
MAX_FRAMES = len(FRAMES)  # 프레임 수
FRAME_DELAY = 5  # 프레임 지연 시간

# 오디오 매니저 인스턴스 생성
audio_manager = AudioManager()

class Explosion(Sprite):
    """
    폭발 효과를 나타내는 클래스

    폭발 효과의 애니메이션과 사운드를 관리합니다.
    """

    def __init__(self, game_state, x, y, delay) -> None:
        """
        폭발 효과 초기화

        :param game_state: 게임 상태 객체
        :param x: x좌표
        :param y: y좌표
        :param delay: 지연 시간
        """
        super().__init__(game_state)
        self.x = x
        self.y = y
        self.delay = delay  # 지연 시간
        self.frame = 0  # 현재 프레임
        self.frame_delay = FRAME_DELAY  # 프레임 지연 카운터
        self.u = FRAMES[self.frame][0]  # 초기 u좌표
        self.v = FRAMES[self.frame][1]  # 초기 v좌표

        if self.delay == 0:
            self.sound()  # 지연 없으면 바로 사운드 재생

    def sound(self):
        """
        폭발 사운드 재생
        """
        audio_manager.play_sound(SoundType.EXPLODE_SMALL)

    def update(self):
        """
        폭발 효과 상태 업데이트
        """
        if self.delay > 0:
            self.delay -= 1
            if self.delay == 0:
                self.sound()  # 지연 끝나면 사운드 재생
            return

        self.frame_delay -= 1
        if self.frame_delay == 0:
            self.frame += 1  # 다음 프레임으로
            if self.frame == MAX_FRAMES:
                self.remove = True  # 애니메이션 끝났으면 제거
                return
            self.frame_delay = FRAME_DELAY
            self.u = FRAMES[self.frame][0]  # u좌표 업데이트
            self.v = FRAMES[self.frame][1]  # v좌표 업데이트

        if self.frame == 0:
            audio_manager.play_sound(SoundType.EXPLOSION)

    def draw(self):
        """
        폭발 효과 그리기
        """
        if self.delay > 0:
            return  # 지연 중에는 그리지 않음

        super().draw()  # 부모 클래스의 draw 호출
        
    def collided_with(self, other):
        """
        다른 스프라이트와의 충돌 처리
        폭발은 충돌 처리가 필요 없으므로 아무 것도 하지 않음
        
        Args:
            other: 충돌한 다른 스프라이트
        """
        pass  # 폭발은 충돌 처리가 필요 없음
