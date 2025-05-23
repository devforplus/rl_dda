import pyxel as px
from components.sprite import Sprite
from components.entity_types import EntityType
from components.enemy import Enemy
from config.score.score_config import ENEMY_SCORE_BOSS

BULLET_SPEED = 2.5
MOVE_SPEED_Y = 0.5


class EnemyK(Enemy):
    def __init__(self, state, x, y) -> None:
        super().__init__(state, x, y)
        self.type = EntityType.ENEMY_K  # EnemyK 타입으로 설정
        self.colour = 11  # yellow
        self.u = 160
        self.v = 80

        self.w = 32
        self.h = 32
        self.hp = 200
        self.score = ENEMY_SCORE_BOSS

        self.speed_x = state.get_scroll_x_speed()
        self.speed_y = MOVE_SPEED_Y

    def shoot(self):
        self.shoot_at_player(BULLET_SPEED)
        self.shoot_at_player(BULLET_SPEED, 5)
        self.shoot_at_player(BULLET_SPEED, 10)

    def update(self):
        super().update()  # hit frames

        self.speed_x = self.game_state.get_scroll_x_speed()

        self.x -= self.speed_x
        if self.x + self.w < 0:
            self.remove = True
            return

        self.y += self.speed_y
        if self.speed_y > 0:
            if self.y >= 120:
                self.speed_y *= -1
        elif self.speed_y < 0:
            if self.y <= 40:
                self.speed_y *= -1

        if self.game_state.get_num_enemies() == 0:
            if self.lifetime % 60 == 0:
                self.shoot()
        else:
            if self.lifetime % 200 == 0:
                self.shoot()

    def explode(self):
        for i in range(12):
            self.game_state.add_explosion(
                self.x + 8 + px.rndi(-12, 12), self.y + 8 + px.rndi(-6, 6), i * 5
            )

    def destroy(self):
        super().destroy()
        self.game_state.check_stage_clear = True

    def draw_composite(self, is_hit):
        # top left
        px.blt(self.x, self.y, 0, self.u, self.v, 16, 16, 0)
        # top right
        if not is_hit:
            px.pal(self.colour, 6)  # red
        px.blt(self.x + 16, self.y, 0, self.u, self.v, -16, 16, 0)
        # bottom left
        if not is_hit:
            px.pal(self.colour, 9)  # pink
        px.blt(self.x, self.y + 16, 0, self.u, self.v, 16, -16, 0)
        # bottom right
        if not is_hit:
            px.pal(self.colour, 13)  # purple
        px.blt(self.x + 16, self.y + 16, 0, self.u, self.v, -16, -16, 0)

        if not is_hit:
            px.pal()

    def draw(self):
        if self.hit_frames > 0:
            px.pal(self.colour, 15)
            self.draw_composite(True)
            px.pal()
        else:
            self.draw_composite(False)
