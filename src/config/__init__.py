"""Configuration package for RL DDA Game."""

from src.config.player import player_config

# 웹 환경 호환을 위해 enemy_config 추가
try:
    from .enemy import EnemyConfig

    enemy_config = EnemyConfig()
except ImportError:
    # 기본 설정 클래스
    class EnemyConfig:
        def __init__(self):
            self.base_hp = 10
            self.base_damage = 5
            self.base_score = 100
            self.speed = 1.0
            self.shot_interval = 60
            self.shot_speed = 2.0

    enemy_config = EnemyConfig()

__all__ = ["player_config", "enemy_config"]
