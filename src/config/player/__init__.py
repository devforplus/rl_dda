from .player_config import PlayerConfig

# Create default instance
player_config = PlayerConfig()

# Export variables
max_weapons = player_config.max_weapons
max_weapon_level = player_config.max_weapon_level
weapon_names = player_config.weapon_names

__all__ = [
    "PlayerConfig",
    "player_config",
    "max_weapons",
    "max_weapon_level",
    "weapon_names",
]
