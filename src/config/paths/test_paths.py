from config.paths import SOURCE_DIR, ASSETS_DIR


def test_source_dir_exists():
    """SOURCE_DIR이 존재하는지 테스트"""
    assert SOURCE_DIR.exists()
    assert SOURCE_DIR.is_dir()


def test_assets_dir_exists():
    """ASSETS_DIR이 존재하는지 테스트"""
    assert ASSETS_DIR.exists()
    assert ASSETS_DIR.is_dir()


def test_assets_dir_is_subdir_of_source_dir():
    """ASSETS_DIR이 SOURCE_DIR의 하위 디렉토리인지 테스트"""
    assert ASSETS_DIR.parent == SOURCE_DIR
