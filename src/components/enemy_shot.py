import pyxel as px

from components.sprite import Sprite
from components.entity_types import EntityType
from config.enemy.enemy_config import EnemyConfig

# 적 설정 인스턴스 생성
enemy_config = EnemyConfig()


class EnemyShot(Sprite):
    """
    적의 발사체를 나타내는 클래스.

    속성:
        type (EntityType): 엔티티 타입 (적 발사체)
        x, y (int): 위치 좌표
        dx, dy (float): 이동 속도
        delay (int): 발사 지연 시간
        damage (int): 플레이어에게 주는 데미지
        colour (int): 발사체의 색상
    """

    type: EntityType
    x: int
    y: int
    dx: float
    dy: float
    delay: int
    damage: int
    colour: int

    def __init__(
        self, game_state, x: int, y: int, dx: float, dy: float, delay: int = 0
    ) -> None:
        """
        적 발사체 초기화.

        매개변수:
            game_state: 게임 상태 객체
            x, y (int): 초기 위치 좌표
            dx, dy (float): 이동 속도
            delay (int): 발사 지연 시간
        """
        super().__init__(game_state)
        self.type = EntityType.ENEMY_SHOT
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.delay = delay
        self.damage = enemy_config.shot_damage
        self.w = 8
        self.h = 8
        self.u = 6
        self.v = 102
        self.colour = 8  # 초기 색상

    def update(self) -> None:
        """적 발사체 상태 업데이트."""
        if self.delay > 0:
            self.delay -= 1
            return

        self.x += self.dx
        self.y += self.dy

        # 색상 변경 (10프레임마다)
        if px.frame_count % 10 == 0:
            self.colour = 8 if (self.colour == 11) else 11

        # 화면 밖으로 나가면 제거
        if self.x < -self.w or self.x > 256 or self.y < -self.h or self.y > 192:
            self.remove = True

    def draw(self) -> None:
        """적 발사체 그리기 - 색상 이펙트 포함."""
        if self.delay > 0:
            return  # 지연 중에는 그리지 않음

        px.pal(15, self.colour)  # 색상 변경 (빨강/주황 교체)
        super().draw()
        px.pal()  # 색상 초기화

    def collided_with(self, other) -> None:
        """
        충돌 처리.

        매개변수:
            other: 충돌한 객체
        """
        if other.type == EntityType.PLAYER:
            other.take_damage(self.damage)  # 플레이어에게 데미지 주기
            self.remove = True  # 발사체 제거
