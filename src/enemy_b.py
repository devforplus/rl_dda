import pyxel as px
from math import pi

from components.enemy import Enemy
from components.entity_types import EntityType

SPEED = 1.5

BULLET_SPEED = 2


class EnemyB(Enemy):
    def __init__(self, state, x, y) -> None:
        super().__init__(state, x, y)
        self.type = EntityType.ENEMY_B  # EnemyB 타입으로 설정
        self.colour = 3  # light green
        self.u = 16
        self.v = 80

    def update(self):
        super().update()  # hit frames

        self.x -= SPEED
        if self.x + self.w < 0:
            self.remove = True
            return

        self.y += px.sin(self.lifetime * pi)

        if self.lifetime == 20:
            self.shoot_at_player(BULLET_SPEED)
