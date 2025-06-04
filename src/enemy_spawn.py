import time
import json
from enemy_a import EnemyA
from enemy_b import EnemyB
from enemy_c import EnemyC
from enemy_d import EnemyD
from enemy_e import EnemyE
from enemy_f import EnemyF
from enemy_g import EnemyG
from enemy_h import EnemyH
from enemy_i import EnemyI
from enemy_j import EnemyJ  # Defence Turret for Boss
from enemy_k import EnemyK  # Boss 1 circle
from enemy_l import EnemyL  # Boss 2: big leaves
from enemy_m import EnemyM  # Boss 3: eye
from enemy_n import EnemyN
from enemy_o import EnemyO
from enemy_p import EnemyP

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

    # 에이전트가 학습 모드인지 확인
    should_log = True
    if (
        hasattr(state, "game")
        and hasattr(state.game, "app")
        and hasattr(state.game.app, "agent")
        and state.game.app.agent is not None
        and hasattr(state.game.app.agent, "enable_learning")
        and getattr(state.game.app.agent, "enable_learning", False)
    ):
        should_log = False  # 학습 모드일 때는 로그 억제

    if tile_x in ENEMY_BOSS_SPAWN_TILE_X:
        f = ENEMY_BOSS_SPAWN_TILE_X[tile_x]
        enemy = f(state, x, y)
        state.add_boss(enemy)  # 보스 적 추가
        boss_type = f.__name__  # 클래스 이름 사용
        if should_log:
            print(
                json.dumps(
                    {
                        "type": "entity",
                        "event": "boss_created",
                        "timestamp": current_time,
                        "data": {
                            "entity_type": boss_type,
                            "position": {"x": x, "y": y},
                        },
                    }
                )
            )
    elif tile_x in ENEMY_SPAWN_TILE_X:
        f = ENEMY_SPAWN_TILE_X[tile_x]
        enemy = f(state, x, y)
        state.add_enemy(enemy)  # 일반 적 추가
        enemy_type = f.__name__  # 클래스 이름 사용
        if should_log:
            print(
                json.dumps(
                    {
                        "type": "entity",
                        "event": "enemy_created",
                        "timestamp": current_time,
                        "data": {
                            "entity_type": enemy_type,
                            "position": {"x": x, "y": y},
                        },
                    }
                )
            )
