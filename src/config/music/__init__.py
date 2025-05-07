"""Music configuration package."""

from .music_config import MusicConfig

# MusicConfig 인스턴스 생성
music_config = MusicConfig()

# 음악 파일 매핑 노출
stage_music_mapping = music_config.stage_music_mapping
special_music_files = music_config.special_music_files

__all__ = ["MusicConfig", "special_music_files"]
