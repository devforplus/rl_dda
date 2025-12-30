
import pyxel as px
from const import APP_WIDTH, APP_HEIGHT, EntityType
from sprite import Sprite
import player_shot
import input

MOVE_SPEED = 2
MOVE_SPEED_DIAGONAL = MOVE_SPEED * 0.707
SHOT_DELAY = 10 # frames
INVINCIBILITY_FRAMES = 120

class Player(Sprite):
    def __init__(self, state) -> None:
        super().__init__(state)
        self.game_vars = state.game.game_vars
        self.input = state.input
        self.type = EntityType.PLAYER
        self.x = 0
        self.y = 92
        self.h = 8
        self.colour = 15 # white
        self.shot_delay = 0

        self.invincibility_frames = INVINCIBILITY_FRAMES
        self.hp = 2
        self.hit_frames = 0

    def explode(self):
        for i in range(12):
            self.game_state.add_explosion(
                self.x + px.rndi(-12,12), 
                self.y - 4 + px.rndi(-6,6), i*8)
            
    def is_invincible(self):
        return self.god_mode or self.invincibility_frames > 0
    
    @property
    def god_mode(self):
        return self.game_vars.god_mode
    
    def collide_background(self, bg):
        if bg.is_point_colliding(self.x + 8, self.y + 4): # centre pixel
            self.collided_with(bg)
            return True
        return False
    
    def kill(self):
        self.remove = True
        self.explode()
        self.game_vars.subtract_life()
        self.game_vars.decrease_all_weapon_levels(2)
        self.game_vars.change_weapon(0)

    def hit(self):
        if self.is_invincible():
            return
        
        self.hp -= 1
        if self.hp <= 0:
            self.kill()
        else:
            self.invincibility_frames = INVINCIBILITY_FRAMES
            self.hit_frames = 10 # short flash

    def collided_with(self, other):
        if other.type == EntityType.ENEMY or \
            other.type == EntityType.ENEMY_SHOT or \
            other.type == EntityType.BACKGROUND:
            self.hit()

    def move(self):
        move_x = 0
        move_y = 0
        if self.input.is_pressing(input.LEFT):
            move_x = -1
        elif self.input.is_pressing(input.RIGHT):
            move_x = 1
        if self.input.is_pressing(input.UP):
            move_y = -1
        elif self.input.is_pressing(input.DOWN):
            move_y = 1
            
        if move_x != 0 and move_y != 0:
            move_x *= MOVE_SPEED_DIAGONAL
            move_y *= MOVE_SPEED_DIAGONAL
            self.x = max(0, min(APP_WIDTH-self.w, self.x + move_x))
            self.y = max(16, min(APP_HEIGHT-16-self.h, self.y + move_y))
        elif move_x != 0:
            move_x *= MOVE_SPEED
            self.x = max(0, min(APP_WIDTH-self.w, self.x + move_x))
        elif move_y != 0:
            move_y *= MOVE_SPEED
            self.y = max(16, min(APP_HEIGHT-16-self.h, self.y + move_y))

    def shoot(self):
        if player_shot.create(
            self.game_state, 
            self.x, 
            self.y,
            self.game_vars.current_weapon,
            self.game_vars.weapon_levels[self.game_vars.current_weapon]):
            self.shot_delay = SHOT_DELAY
            

    def update_spawned(self):
        self.x += MOVE_SPEED

    def update(self):
        self.move()

        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1
        
        if self.hit_frames > 0:
            self.hit_frames -= 1

        if not self.is_invincible():
            if self.collide_background(self.game_state.background):
                return

        if self.shot_delay > 0:
            self.shot_delay -= 1
        elif self.input.is_pressing(input.BUTTON_1):
            self.shoot()

    def draw(self):
        if self.is_invincible() and px.frame_count % 2 == 0:
            return
        
        if self.hit_frames > 0:
            px.pal(self.colour, 8) # flash red
            px.blt(self.x, self.y, 0, 0, 4, self.w, self.h, 0)
            px.pal()
        else:
            px.blt(self.x, self.y, 0, 0, 4, self.w, self.h, 0)
    