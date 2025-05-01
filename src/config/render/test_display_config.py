from config.render.display_config import (
    APP_WIDTH,
    APP_HEIGHT,
    APP_DISPLAY_SCALE,
    APP_CAPTURE_SCALE,
    APP_FPS,
    APP_GFX_FILE,
)


def test_display_config_values():
    """
    디스플레이 설정값 테스트

    목적: display_config.py의 모든 설정값이 올바른 값을 가지고 있는지 검증
    """
    # 애플리케이션 크기 설정 검증
    assert APP_WIDTH == 256, "애플리케이션 너비가 256이어야 합니다."
    assert APP_HEIGHT == 192, "애플리케이션 높이가 192이어야 합니다."

    # 스케일 설정 검증
    assert APP_DISPLAY_SCALE == 2, "디스플레이 스케일이 2이어야 합니다."
    assert APP_CAPTURE_SCALE == 2, "캡처 스케일이 2이어야 합니다."

    # FPS 설정 검증
    assert APP_FPS == 60, "FPS가 60이어야 합니다."

    # 그래픽스 파일 설정 검증
    assert APP_GFX_FILE == "gfx.png", "그래픽스 파일 이름이 'gfx.png'이어야 합니다."


def test_display_config_types():
    """
    디스플레이 설정 타입 테스트

    목적: display_config.py의 모든 설정값이 올바른 타입을 가지고 있는지 검증
    """
    # 정수형 설정값 검증
    assert isinstance(APP_WIDTH, int), "APP_WIDTH는 정수형이어야 합니다."
    assert isinstance(APP_HEIGHT, int), "APP_HEIGHT는 정수형이어야 합니다."
    assert isinstance(APP_DISPLAY_SCALE, int), "APP_DISPLAY_SCALE은 정수형이어야 합니다."
    assert isinstance(APP_CAPTURE_SCALE, int), "APP_CAPTURE_SCALE은 정수형이어야 합니다."
    assert isinstance(APP_FPS, int), "APP_FPS는 정수형이어야 합니다."

    # 문자열 설정값 검증
    assert isinstance(APP_GFX_FILE, str), "APP_GFX_FILE은 문자열이어야 합니다."


def test_display_config_positive_values():
    """
    디스플레이 설정 양수값 테스트

    목적: display_config.py의 수치 설정값이 양수인지 검증
    """
    # 양수값 검증
    assert APP_WIDTH > 0, "APP_WIDTH는 양수여야 합니다."
    assert APP_HEIGHT > 0, "APP_HEIGHT는 양수여야 합니다."
    assert APP_DISPLAY_SCALE > 0, "APP_DISPLAY_SCALE은 양수여야 합니다."
    assert APP_CAPTURE_SCALE > 0, "APP_CAPTURE_SCALE은 양수여야 합니다."
    assert APP_FPS > 0, "APP_FPS는 양수여야 합니다." 