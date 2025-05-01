from enum import Enum, IntEnum, auto

# 애플리케이션 기본 상수 정의
# APP_VERSION = "1.0"  # 애플리케이션 버전
# APP_WIDTH = 256  # 애플리케이션 너비
# APP_HEIGHT = 192  # 애플리케이션 높이
# APP_NAME = "VORTEXION"  # 애플리케이션 이름
# APP_FPS = 60  # 초당 프레임 수
# APP_DISPLAY_SCALE = 2  # 디스플레이 스케일
# APP_CAPTURE_SCALE = 2  # 캡처 스케일
# APP_GFX_FILE = "gfx.png"  # 그래픽스 파일 이름


# TODO: 아래는 점수, 데미지 관련 설정으로 각각 분리하자. 데미지 설정은 플레이어/적 설정에 편입할 수 있을 수도 있음.

# TODO: 점수 상한은 표기 가능한 숫자의 최대 크기에 맞춰진 것 같은데, DDA 작업하면서 변경이 필요할 지 생각해봐야 함.
MAX_SCORE = 999999  # 최대 점수

# 점수 관련 상수
ENEMY_SCORE_NORMAL = 100  # 일반 적 처치 점수
ENEMY_SCORE_BOSS = 5000  # 보스 처치 점수

# 데미지 관련 상수
# PLAYER_SHOT_DAMAGE = 1  # 플레이어 발사체 데미지 (player.py로 이동)
# BOMB_DAMAGE = 30  # 폭탄 데미지 (player_config.py로 이동)

# 사운드 리소스 파일 정의
# SOUNDS_RES_FILE = "sounds.pyxres"  # 사운드 리소스 파일 이름 (sound_config.py로 이동)
