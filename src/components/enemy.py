import pyxel as px

from components.sprite import Sprite
from components.entity_types import EntityType
from src.config.enemy.enemy_config import EnemyConfig
from src.config.score.score_config import ENEMY_SCORE_NORMAL
from components.enemy_shot import EnemyShot
import powerup
from audio import play_sound, SoundType

# 적 설정 인스턴스 생성
enemy_config = EnemyConfig()

# 적중 시 무적 프레임 수
HIT_FRAMES: int = 5
# 생성 시 무적 프레임 수
INVINCIBLE_START_FRAMES: int = 15
# 적 기본 데미지
ENEMY_DAMAGE: int = 1


class Enemy(Sprite):
    """
    적 캐릭터를 나타내는 클래스.

    속성:
        type (EntityType): 엔티티 타입 (적)
        x, y (int): 위치 좌표
        hp (int): 체력
        hit_frames (int): 피격 시 무적 프레임 수
        score (int): 적 처치 시 획득 점수
        lifetime (int): 생존 시간
        damage (int): 플레이어에게 주는 데미지
    """

    type: EntityType
    x: int
    y: int
    hp: int
    hit_frames: int
    score: int
    lifetime: int
    damage: int

    def __init__(self, game_state, x: int, y: int) -> None:
        """
        적 캐릭터 초기화.

        매개변수:
            game_state: 게임 상태 객체
            x, y (int): 초기 위치 좌표
        """
        super().__init__(game_state)
        self.type = EntityType.ENEMY
        self.x = x
        self.y = y
        self.hp = enemy_config.base_hp  # 기본 체력
        self.hit_frames = 0
        self.score = ENEMY_SCORE_NORMAL  # 처치 시 획득 점수
        self.lifetime = 0  # 생존 시간 초기화
        self.damage = enemy_config.base_damage  # 기본 데미지 설정

    def explode(self) -> None:
        """적 폭발 효과 처리."""
        self.game_state.add_explosion(self.x, self.y, 0)

    def destroy(self) -> None:
        """
        적 제거 처리.

        점수 추가, 폭발 효과, 파워업 아이템 생성 체크 등을 수행.
        """
        if self.remove:
            return
        self.remove = True
        self.game_state.add_score(self.score)  # 점수 추가
        self.explode()  # 폭발 효과
        powerup.check_create_next(
            self.game_state, self.x, self.y
        )  # 파워업 아이템 생성 체크

    def hit(self, dmg: int) -> None:
        """
        적 피격 처리.

        매개변수:
            dmg (int): 입은 피해량
        """
        self.hp = max(0, self.hp - dmg)  # 체력 감소
        if self.hp == 0:
            self.destroy()  # 체력이 0이면 제거 처리
        else:
            self.hit_frames = enemy_config.hit_invincibility_frames  # 무적 프레임 설정
            play_sound(SoundType.BLIP)  # 피격 사운드 재생

    def hit_with_bomb(self) -> None:
        """폭탄에 의한 피격 처리."""
        self.hit(enemy_config.bomb_damage)  # 폭탄 데미지로 피격 처리

    def collided_with(self, other) -> None:
        """
        충돌 처리.

        매개변수:
            other: 충돌한 객체
        """
        if self.lifetime < enemy_config.spawn_invincibility_frames:
            return  # 초기 무적 시간 중에는 충돌 무시

        if other.type == EntityType.PLAYER_SHOT:
            self.hit(other.damage)  # 플레이어 총알과 충돌 시 피격 처리
        elif other.type == EntityType.PLAYER:
            other.take_damage(self.damage)  # 플레이어와 충돌 시 데미지 주기

    def shoot_at_angle(
        self,
        speed: float,
        degrees: float,
        delay: int = 0,
        offset_x: int = 0,
        offset_y: int = 0,
    ) -> None:
        """
        특정 각도로 총알 발사.

        매개변수:
            speed (float): 총알 속도
            degrees (float): 발사 각도
            delay (int): 발사 지연 시간
            offset_x, offset_y (int): 발사 위치 오프셋
        """
        s = EnemyShot(
            self.game_state,
            self.x + (self.w / 2) + offset_x,
            self.y + (self.h / 2) + offset_y,
            px.cos(degrees) * speed,
            px.sin(degrees) * speed,
            delay,
        )
        self.game_state.add_enemy_shot(s)  # 게임 상태에 총알 추가

    def shoot_at_player(self, speed: float, delay: int = 0) -> None:
        """
        플레이어를 향해 총알 발사.

        매개변수:
            speed (float): 총알 속도
            delay (int): 발사 지연 시간
        """
        target_x = self.game_state.player.x + 8
        target_y = self.game_state.player.y + 4
        a = px.atan2(target_y - (self.y + self.h / 2), target_x - (self.x + self.w / 2))
        self.shoot_at_angle(speed, a, delay)  # 플레이어 방향으로 발사

    def update(self) -> None:
        """적 상태 업데이트."""
        self.lifetime += 1  # 생존 시간 증가
        if self.hit_frames > 0:
            self.hit_frames -= 1  # 무적 프레임 감소

    def draw(self) -> None:
        """적 그리기."""
        if self.hit_frames > 0:
            # 피격 시 색상 변경
            px.pal(self.colour, 15)
            super().draw()
            px.pal()  # 색상 원래대로 복원
        else:
            super().draw()  # 일반 상태로 그리기
