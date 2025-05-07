from .player_config import PlayerConfig

# Create default instance
default_config = PlayerConfig()

# Export variables
max_weapons = default_config.max_weapons
max_weapon_level = default_config.max_weapon_level
weapon_names = default_config.weapon_names

__all__ = ["PlayerConfig", "max_weapons", "max_weapon_level", "weapon_names"]
