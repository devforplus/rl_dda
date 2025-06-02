"""
적 캐릭터 시스템 모듈
"""

import time
import json

try:
    import pyxel
except ImportError:
    pyxel = None

from .sprite import Sprite
from .entity_types import EntityType

# 안전한 import - 기존 구조 유지
try:
    from .player import Player
except ImportError:
    Player = None

try:
    from .enemy_shot import EnemyShot
except ImportError:
    EnemyShot = None

# config에서 enemy_config import (수정된 경로)
try:
    from config import enemy_config
except ImportError:
    # 기본값 설정
    class DefaultEnemyConfig:
        def __init__(self):
            self.base_hp = 10
            self.base_damage = 5
            self.base_score = 100
            self.speed = 1.0
            self.shot_interval = 60
            self.shot_speed = 2.0
            self.hit_invincibility_frames = 5

    enemy_config = DefaultEnemyConfig()

# 나머지 import들도 안전하게 처리
try:
    from components import powerup
except ImportError:
    powerup = None

try:
    from sound import audio_manager
    from sound.sound_type import SoundType
except ImportError:

    class AudioManager:
        @staticmethod
        def play_sound(*args, **kwargs):
            pass

    audio_manager = AudioManager()

    class SoundType:
        ENEMY_EXPLOSION = "enemy_explosion"


try:
    from config.score.score_config import ENEMY_SCORE_NORMAL
except ImportError:
    ENEMY_SCORE_NORMAL = 100

# GameEventLogger import
try:
    from utils.game_event_logger import log_entity_destroyed, Position
except ImportError:

    def log_entity_destroyed(entity_type, position, reason):
        if pyxel is not None:
            print(f"Entity destroyed: {entity_type} at {position}, reason: {reason}")

    class Position:
        def __init__(self, x=0, y=0):
            self.x = x
            self.y = y


# 적중 시 무적 프레임 수
HIT_FRAMES: int = 5
# 생성 시 무적 프레임 수
INVINCIBLE_START_FRAMES: int = 15
# 적 기본 데미지
ENEMY_DAMAGE: int = 1

# 오디오 매니저 인스턴스 생성
audio_manager = AudioManager()


class Enemy(Sprite):
    """
    적 객체를 나타내는 기본 클래스.

    속성:
        type (EntityType): 엔티티 타입 (적)
        x, y (int): 위치 좌표
        w, h (int): 크기
        hp (int): 체력
        colour (int): 색상
        u, v (int): 스프라이트 UV 좌표
        hit_frames (int): 피격 시 무적 프레임
        lifetime (int): 생존 시간
        remove (bool): 제거 여부
    """

    type: EntityType
    x: int
    y: int
    w: int
    h: int
    hp: int
    colour: int
    u: int
    v: int
    hit_frames: int
    lifetime: int
    remove: bool
    removal_reason: str
    flip_x: bool
    flip_y: bool
    score: int
    damage: int

    def __init__(self, state, x: int, y: int) -> None:
        """
        적 초기화.

        매개변수:
            state: 게임 상태 객체
            x, y (int): 초기 위치 좌표
        """
        super().__init__(state)
        self.type = EntityType.ENEMY  # 기본 적 타입
        self.x = x
        self.y = y
        self.w = 16
        self.h = 16
        self.hp = enemy_config.base_hp  # 기본 체력
        self.colour = 7  # cyan
        self.u = 0
        self.v = 80
        self.hit_frames = 0
        self.lifetime = 0
        self.remove = False
        self.removal_reason = ""  # 제거 사유 추가
        self.flip_x = False
        self.flip_y = False
        self.score = ENEMY_SCORE_NORMAL  # 처치 시 획득 점수
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
        self.removal_reason = "killed_by_player"  # 플레이어에 의한 제거 사유 설정
        self.game_state.add_score(self.score)  # 점수 추가
        self.explode()  # 폭발 효과
        powerup.check_create_next(
            self.game_state, self.x, self.y
        )  # 파워업 아이템 생성 체크

        # 적 제거 로그 출력
        current_time = time.time()
        entity_type = type(self).__name__
        log_entity_destroyed(
            entity_type, Position(x=self.x, y=self.y), reason=self.removal_reason
        )

    def hit(self, dmg: int) -> None:
        """
        적 피격 처리.

        매개변수:
            dmg (int): 입은 피해량
        """
        self.hp = max(0, self.hp - dmg)  # 체력 감소
        if self.hp == 0:
            self.destroy()  # 체력이 0이면 제거 처리
            audio_manager.play_sound(SoundType.ENEMY_EXPLOSION)
        else:
            self.hit_frames = enemy_config.hit_invincibility_frames  # 무적 프레임 설정
            audio_manager.play_sound(SoundType.BLIP)  # 피격 사운드 재생

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
            pyxel.cos(degrees) * speed,
            pyxel.sin(degrees) * speed,
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
        a = pyxel.atan2(
            target_y - (self.y + self.h / 2), target_x - (self.x + self.w / 2)
        )
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
            pyxel.pal(self.colour, 15)
            super().draw()
            pyxel.pal()  # 색상 원래대로 복원
        else:
            super().draw()  # 일반 상태로 그리기

    def remove_out_of_bounds(self, reason="out_of_bounds") -> None:
        """
        화면 밖으로 나간 적을 제거하고 로그를 출력합니다.

        매개변수:
            reason (str): 제거 사유
        """
        if not self.remove:  # 이미 제거되지 않은 경우만
            self.remove = True
            self.removal_reason = reason

            # 적 제거 로그 출력
            current_time = time.time()
            entity_type = type(self).__name__
            log_entity_destroyed(
                entity_type, Position(x=self.x, y=self.y), reason=self.removal_reason
            )
