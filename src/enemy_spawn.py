import time
import json
from components.boss.enemy_k import EnemyK
from components.boss.enemy_l import EnemyL
from components.boss.enemy_m import EnemyM
from components.enemy.enemy_a import EnemyA
from components.enemy.enemy_b import EnemyB
from components.enemy.enemy_c import EnemyC
from components.enemy.enemy_d import EnemyD
from components.enemy.enemy_e import EnemyE
from components.enemy.enemy_f import EnemyF
from components.enemy.enemy_g import EnemyG
from components.enemy.enemy_h import EnemyH
from components.enemy.enemy_i import EnemyI
from components.enemy.enemy_j import EnemyJ
from components.enemy.enemy_n import EnemyN
from components.enemy.enemy_o import EnemyO
from components.enemy.enemy_p import EnemyP

ENEMY_SPAWN_TILE_X = {
    0: EnemyA,
    1: EnemyB,
    2: EnemyC,
    3: EnemyD,
    4: EnemyE,
    5: EnemyF,
    6: EnemyG,
    7: EnemyH,
    8: EnemyI,
    9: EnemyJ,
    10: EnemyN,
    11: EnemyO,
    12: EnemyP,
    13: EnemyK,
    14: EnemyL,
    15: EnemyM,
}

ENEMY_SPAWN_TILE_INDEX_Y = 10


def create(game_state_stage, tile_x, x, y):
    current_time = time.time()

    if tile_x in [13, 14, 15]:  # 보스 타일 (EnemyK, EnemyL, EnemyM)
        f = ENEMY_SPAWN_TILE_X[tile_x]
        boss = f(game_state_stage, x, y)
        game_state_stage.add_boss(boss)
        boss_type = type(boss).__name__
        print(
            json.dumps(
                {
                    "type": "entity",
                    "event": "boss_created",
                    "timestamp": current_time,
                    "data": {"entity_type": boss_type, "position": {"x": x, "y": y}},
                }
            )
        )
    elif tile_x in ENEMY_SPAWN_TILE_X:
        f = ENEMY_SPAWN_TILE_X[tile_x]
        enemy = f(game_state_stage, x, y)
        game_state_stage.add_enemy(enemy)
        enemy_type = type(enemy).__name__
        print(
            json.dumps(
                {
                    "type": "entity",
                    "event": "enemy_created",
                    "timestamp": current_time,
                    "data": {"entity_type": enemy_type, "position": {"x": x, "y": y}},
                }
            )
        )
