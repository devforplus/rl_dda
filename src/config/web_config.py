"""
Web Environment Configuration

For web builds where .env files are not available.
Web environment configuration with hardcoded values that mirror .env settings.

---

웹 환경용 설정 파일
.env 파일을 사용할 수 없는 웹 빌드 환경에서 사용됩니다.
"""

# ===== Performance Optimization Settings =====
# 성능 최적화 설정
ENABLE_FAST_CAPTURE = True
CAPTURE_INTERVAL = 5
ENABLE_PERFORMANCE_LOGGING = True

# ===== Data Collection Settings =====
# 데이터 수집 설정
AUTO_COLLECT_DATA = True
MAX_COLLECTED_FRAMES = 1000

# ===== Developer Settings =====
# 개발자 설정
DEBUG_MODE = False  # Web builds should have debug off by default
FORCE_WEB_MODE = True  # Always true for web config
ENABLE_AI_AGENT = False

# ===== Game Settings =====
# 게임 설정
GAME_WIDTH = 256
GAME_HEIGHT = 192
GAME_FPS = 60
DISPLAY_SCALE = 3

# ===== Web-Specific Settings =====
# 웹 전용 설정
WEB_ENABLE_LOCAL_STORAGE = True
WEB_AUTO_DOWNLOAD_DATA = False
WEB_COMPRESSION_FORMAT = "png"  # png, jpeg, webp


def get_web_config():
    """
    Returns web configuration as a dictionary

    ---

    웹 설정을 딕셔너리로 반환합니다.
    """
    return {
        "ENABLE_FAST_CAPTURE": ENABLE_FAST_CAPTURE,
        "CAPTURE_INTERVAL": CAPTURE_INTERVAL,
        "ENABLE_PERFORMANCE_LOGGING": ENABLE_PERFORMANCE_LOGGING,
        "AUTO_COLLECT_DATA": AUTO_COLLECT_DATA,
        "MAX_COLLECTED_FRAMES": MAX_COLLECTED_FRAMES,
        "DEBUG_MODE": DEBUG_MODE,
        "FORCE_WEB_MODE": FORCE_WEB_MODE,
        "ENABLE_AI_AGENT": ENABLE_AI_AGENT,
        "GAME_WIDTH": GAME_WIDTH,
        "GAME_HEIGHT": GAME_HEIGHT,
        "GAME_FPS": GAME_FPS,
        "DISPLAY_SCALE": DISPLAY_SCALE,
        "WEB_ENABLE_LOCAL_STORAGE": WEB_ENABLE_LOCAL_STORAGE,
        "WEB_AUTO_DOWNLOAD_DATA": WEB_AUTO_DOWNLOAD_DATA,
        "WEB_COMPRESSION_FORMAT": WEB_COMPRESSION_FORMAT,
    }


def print_web_config():
    """
    Print web configuration summary

    ---

    웹 설정 요약을 출력합니다.
    """
    print("🌐 웹 환경 설정:")
    print(f"  🚀 고성능 캡쳐: {ENABLE_FAST_CAPTURE}")
    print(f"  📊 성능 로깅: {ENABLE_PERFORMANCE_LOGGING}")
    print(f"  🎮 게임 크기: {GAME_WIDTH}x{GAME_HEIGHT}")
    print(f"  🔧 디버그 모드: {DEBUG_MODE}")
    print(f"  📁 데이터 수집: {AUTO_COLLECT_DATA}")
    print(f"  🖼️  압축 형식: {WEB_COMPRESSION_FORMAT}")
