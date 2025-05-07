from config.colors.color_palette import COLOR_PALETTE, MAX_COLORS


def test_color_palette_length():
    """MAX_COLORS가 COLOR_PALETTE의 실제 길이를 정확히 반영하는지 테스트"""
    assert MAX_COLORS == len(COLOR_PALETTE)


def test_color_values_are_valid():
    """모든 색상 값이 유효한 24비트 색상 코드인지 테스트"""
    for color in COLOR_PALETTE:
        assert isinstance(color, int)
        assert 0 <= color <= 0xFFFFFF


def test_no_duplicate_colors():
    """COLOR_PALETTE에 중복된 색상 값이 없는지 테스트"""
    assert len(COLOR_PALETTE) == len(set(COLOR_PALETTE))


def test_color_palette_structure():
    """COLOR_PALETTE의 구조적 일관성 테스트"""
    # COLOR_PALETTE의 길이 검증
    # MAX_COLORS는 COLOR_PALETTE의 길이를 나타내는 상수
    assert len(COLOR_PALETTE) == MAX_COLORS, (
        "COLOR_PALETTE의 길이가 MAX_COLORS와 일치하지 않습니다."
    )

    # COLOR_PALETTE 내 모든 색상 값 검증
    # 각 색상 값은 24비트 정수(0x000000 ~ 0xFFFFFF)여야 함
    assert all(
        isinstance(color, int) and 0 <= color <= 0xFFFFFF for color in COLOR_PALETTE
    ), "COLOR_PALETTE에 유효하지 않은 색상 값이 포함되어 있습니다."
