import pyxel as px

from .sprite import Sprite
from .entity_types import EntityType
from src.config.app.constants import APP_WIDTH, APP_HEIGHT

# enemy_config import 수정
try:
    from src.config.enemy import enemy_config
except ImportError:

    class DefaultEnemyConfig:
        def __init__(self):
            self.shot_damage = 1

    enemy_config = DefaultEnemyConfig()


class EnemyShot(Sprite):
    """
    적의 발사체를 나타내는 클래스.

    속성:
        type (EntityType): 엔티티 타입 (적 발사체)
        x, y (int): 위치 좌표
        dx, dy (float): 이동 속도
        delay (int): 발사 지연 시간
        damage (int): 플레이어에게 주는 데미지
    """

    type: EntityType
    x: int
    y: int
    dx: float
    dy: float
    delay: int
    damage: int

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
        self.u = 32
        self.v = 0

    def update(self) -> None:
        """적 발사체 상태 업데이트."""
        if self.delay > 0:
            self.delay -= 1
            return

        self.x += int(self.dx)
        self.y += int(self.dy)

        # 화면 밖으로 나가면 제거
        if self.x < -self.w or self.x > 256 or self.y < -self.h or self.y > 192:
            self.remove = True

    def collided_with(self, other) -> None:
        """
        충돌 처리.

        매개변수:
            other: 충돌한 객체
        """
        if other.type == EntityType.PLAYER:
            other.take_damage(self.damage)  # 플레이어에게 데미지 주기
            self.remove = True  # 발사체 제거
