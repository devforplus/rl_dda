"""
적 생성 시스템

다양한 적들을 생성하고 관리하는 시스템입니다.
게임 이벤트 로거를 사용하여 적 생성 이벤트를 기록합니다.
"""

import time
import json
from src.enemy_a import EnemyA
from src.enemy_b import EnemyB
from src.enemy_c import EnemyC
from src.enemy_d import EnemyD
from src.enemy_e import EnemyE
from src.enemy_f import EnemyF
from src.enemy_g import EnemyG
from src.enemy_h import EnemyH
from src.enemy_i import EnemyI
from src.enemy_j import EnemyJ  # Defence Turret for Boss
from src.enemy_k import EnemyK  # Boss 1 circle
from src.enemy_l import EnemyL  # Boss 2: big leaves
from src.enemy_m import EnemyM  # Boss 3: eye
from src.enemy_n import EnemyN
from src.enemy_o import EnemyO
from src.enemy_p import EnemyP
from .utils.game_event_logger import log_entity_created, Position

ENEMY_SPAWN_TILE_X = {
    0: EnemyA,
    16: EnemyB,
    32: EnemyC,
    48: EnemyD,
    64: EnemyE,
    80: EnemyF,
    96: EnemyG,
    112: EnemyH,
    128: EnemyI,
    144: EnemyJ,
    208: EnemyN,
    224: EnemyO,
    240: EnemyP,
}

ENEMY_BOSS_SPAWN_TILE_X = {
    160: EnemyK,
    176: EnemyL,
    192: EnemyM,
}

ENEMY_SPAWN_TILE_INDEX_Y = 10


def create(state, tile_x, x, y):
    """
    적 생성

    :param state: 게임 상태
    :param tile_x: 타일 x좌표
    :param x: x좌표
    :param y: y좌표
    """
    current_time = time.time()

    if tile_x in ENEMY_BOSS_SPAWN_TILE_X:
        f = ENEMY_BOSS_SPAWN_TILE_X[tile_x]
        enemy = f(state, x, y)
        state.add_boss(enemy)  # 보스 적 추가
        boss_type = f.__name__  # 클래스 이름 사용
        log_entity_created(boss_type, Position(x, y), is_boss=True)
    elif tile_x in ENEMY_SPAWN_TILE_X:
        f = ENEMY_SPAWN_TILE_X[tile_x]
        enemy = f(state, x, y)
        state.add_enemy(enemy)  # 일반 적 추가
        enemy_type = f.__name__  # 클래스 이름 사용
        log_entity_created(enemy_type, Position(x, y), is_boss=False)
