import pyxel as px

from config.const import APP_WIDTH, EntityType
from components.sprite import Sprite

# 적의 발사체 크기 정의
SIZE = 4


class EnemyShot(Sprite):
    """
    적의 발사체를 나타내는 클래스

    적의 발사체의 위치, 속도, 그래픽 표현 등을 관리합니다.
    """

    def __init__(self, game_state, x, y, vx, vy, delay=0) -> None:
        """
        적의 발사체 초기화

        :param game_state: 게임 상태 객체
        :param x: 초기 x좌표
        :param y: 초기 y좌표
        :param vx: x축 속도
        :param vy: y축 속도
        :param delay: 발사 지연 시간
        """
        super().__init__(game_state)
        self.type = EntityType.ENEMY_SHOT  # 엔티티 타입 설정
        self.x = x
        self.y = y
        self.w = SIZE  # 발사체 너비
        self.h = SIZE  # 발사체 높이
        self.vx = vx  # x축 속도
        self.vy = vy  # y축 속도

        # 그래픽 관련 속성
        self.colour = 11  # 색상 (노랑)
        self.u = 6  # 텍스처 u좌표
        self.v = 102  # 텍스처 v좌표

        self.delay = delay  # 발사 지연 시간

    def collide_background(self, bg):
        """
        배경과의 충돌 여부 확인

        :param bg: 배경 객체
        :return: 충돌 여부
        """
        if bg.is_point_colliding(self.x + 2, self.y + 2):  # 중심 픽셀 충돌 확인
            self.collided_with(bg)
            return True
        return False

    def collided_with(self, other):
        """
        다른 엔티티와의 충돌 처리

        :param other: 다른 엔티티
        """
        if self.delay > 0:
            return  # 지연 중에는 충돌 처리 안 함
        if other.type == EntityType.PLAYER:
            if not other.is_invincible():  # 플레이어가 무적 상태가 아니면
                self.remove = True  # 발사체 제거

    def update(self):
        """
        적의 발사체 상태 업데이트
        """
        if self.delay > 0:
            self.delay -= 1
            return

        self.x += self.vx  # x좌표 업데이트
        self.y += self.vy  # y좌표 업데이트

        if self.collide_background(self.game_state.background):
            return

        # 화면 밖으로 나가면 제거
        if (
            self.x > APP_WIDTH
            or self.x + self.w < 0
            or self.y < 16
            or self.y + self.h >= 176
        ):
            self.remove = True
            return

        # 색상 변경 (10프레임마다)
        if px.frame_count % 10 == 0:
            self.colour = 11 if (self.colour == 6) else 6

    def draw(self):
        """
        적의 발사체 그리기
        """
        if self.delay > 0:
            return  # 지연 중에는 그리지 않음

        px.pal(15, self.colour)  # 색상 변경
        super().draw()
        px.pal()  # 색상 초기화
