import pyxel as px
from system.const import APP_WIDTH, APP_HEIGHT, EntityType
from components.sprite import Sprite
import player_shot
import input as input

# 플레이어 이동 속도
MOVE_SPEED: int = 2
# 대각선 이동 시 속도 조정 계수
MOVE_SPEED_DIAGONAL: float = MOVE_SPEED * 0.707
# 총알 발사 간격 (프레임 단위)
SHOT_DELAY: int = 10
# 초기 무적 상태 지속 프레임 수
INVINCIBILITY_FRAMES: int = 120


class Player(Sprite):
    """
    플레이어 캐릭터를 나타내는 클래스.

    속성:
        game_vars: 게임 변수 관리 객체
        input: 사용자 입력 처리 객체
        type (EntityType): 엔티티 타입 (플레이어)
        x, y (int): 위치 좌표
        h (int): 높이
        colour (int): 색상
        shot_delay (int): 총알 발사 지연 시간
        invincibility_frames (int): 초기 무적 상태 남은 프레임 수
        forced_invincible (bool): 강제 무적 상태 여부 (I 키 입력 시 토글)
    """

    game_vars: object
    input: object
    type: EntityType
    x: int
    y: int
    h: int
    colour: int
    shot_delay: int
    invincibility_frames: int
    forced_invincible: bool

    def __init__(self, state) -> None:
        """
        플레이어 초기화.

        초기 무적 상태로 설정됩니다.
        """
        super().__init__(state)
        self.game_vars = state.game.game_vars
        self.input = state.input
        self.type = EntityType.PLAYER
        self.x = 0
        self.y = 92
        self.h = 8
        self.colour = 15  # 흰색
        self.shot_delay = 0

        # 초기 무적 상태 설정
        self.invincibility_frames = INVINCIBILITY_FRAMES
        self.forced_invincible = False  # 강제 무적 상태는 아님

    def explode(self) -> None:
        """플레이어 폭발 효과 처리."""
        for i in range(12):
            self.game_state.add_explosion(
                self.x + px.rndi(-12, 12), self.y - 4 + px.rndi(-6, 6), i * 8
            )

    def is_invincible(self) -> bool:
        """
        플레이어가 무적 상태인지 확인.

        초기 무적 상태 또는 강제 무적 상태일 때 True를 반환합니다.
        """
        return self.invincibility_frames > 0 or self.forced_invincible

    def collide_background(self, bg) -> bool:
        """
        배경과의 충돌 확인.

        충돌 시 `collided_with` 메서드를 호출합니다.
        """
        if bg.is_point_colliding(self.x + 8, self.y + 4):  # 중심 픽셀 충돌 체크
            self.collided_with(bg)
            return True
        return False

    def kill(self) -> None:
        """플레이어 제거 처리."""
        self.remove = True
        self.explode()
        self.game_vars.subtract_life()  # 생명 수 감소
        self.game_vars.decrease_all_weapon_levels(2)  # 모든 무기 레벨 감소
        self.game_vars.change_weapon(0)  # 기본 무기로 변경

    def collided_with(self, other) -> None:
        """
        충돌 처리.

        무적 상태가 아닐 때만 충돌 처리를 수행합니다.
        """
        if (
            other.type == EntityType.ENEMY
            or other.type == EntityType.ENEMY_SHOT
            or other.type == EntityType.BACKGROUND
        ):
            if not self.is_invincible():
                self.kill()

    def move(self) -> None:
        """플레이어 이동 처리."""
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
            # 대각선 이동 시 속도 조정
            move_x *= MOVE_SPEED_DIAGONAL
            move_y *= MOVE_SPEED_DIAGONAL
            self.x = max(0, min(APP_WIDTH - self.w, self.x + move_x))
            self.y = max(16, min(APP_HEIGHT - 16 - self.h, self.y + move_y))
        elif move_x != 0:
            move_x *= MOVE_SPEED
            self.x = max(0, min(APP_WIDTH - self.w, self.x + move_x))
        elif move_y != 0:
            move_y *= MOVE_SPEED
            self.y = max(16, min(APP_HEIGHT - 16 - self.h, self.y + move_y))

    def shoot(self) -> None:
        """총알 발사 처리."""
        if player_shot.create(
            self.game_state,
            self.x,
            self.y,
            self.game_vars.current_weapon,
            self.game_vars.weapon_levels[self.game_vars.current_weapon],
        ):
            self.shot_delay = SHOT_DELAY

    def update_spawned(self) -> None:
        """스폰 시 플레이어 위치 업데이트."""
        self.x += MOVE_SPEED

    def update(self) -> None:
        """플레이어 상태 업데이트."""
        self.move()

        # 초기 무적 상태 업데이트
        if self.invincibility_frames > 0:
            self.invincibility_frames -= 1

        # 배경과의 충돌 체크 (무적 상태가 아닐 때)
        if not self.is_invincible():
            if self.collide_background(self.game_state.background):
                return

        # 총알 발사 지연 시간 업데이트
        if self.shot_delay > 0:
            self.shot_delay -= 1
        elif self.input.is_pressing(input.BUTTON_1):
            self.shoot()

    def draw(self) -> None:
        """플레이어 그리기."""
        if self.is_invincible() and px.frame_count % 2 == 0:
            return  # 무적 상태일 때 깜빡임 효과
        px.blt(self.x, self.y, 0, 0, 4, self.w, self.h, 0)

    def toggle_invincibility(self) -> None:
        """
        강제 무적 상태 토글.

        I 키 입력 시 `GameStateStage`의 `update_play` 메서드에서 호출됩니다.
        플레이어의 무적 상태를 강제로 활성화하거나 비활성화합니다.
        """
        self.forced_invincible = not self.forced_invincible
        self.invincibility_frames = (
            INVINCIBILITY_FRAMES if self.forced_invincible else 0
        )
