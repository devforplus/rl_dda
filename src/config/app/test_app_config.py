from .app import load_app_config, APP_NAME, APP_VERSION
import tomli
import pytest
from pathlib import Path
from unittest.mock import mock_open, patch

# 테스트용 TOML 파일 내용
VALID_TOML = """
[tool.game]
app_name = "VORTEXION"
app_version = "1.0"
"""

MISSING_TOOL_SECTION_TOML = """
[project]
name = "test"
"""

INVALID_TOML = """
[tool.game
app_name = VORTEXION
"""

PARTIAL_TOML = """
[tool.game]
app_name = "CustomName"
"""

def test_load_app_config_with_valid_toml():
    """유효한 TOML 파일에서 앱 설정을 올바르게 로드하는지 테스트"""
    with patch("builtins.open", mock_open(read_data=VALID_TOML.encode())) as mock_file:
        mock_file.return_value.__enter__.return_value = mock_file.return_value
        config = load_app_config()
        assert config["APP_NAME"] == "VORTEXION"
        assert config["APP_VERSION"] == "1.0"

def test_load_app_config_with_missing_section():
    """tool.game 섹션이 없는 경우 기본값을 반환하는지 테스트"""
    with patch("builtins.open", mock_open(read_data=MISSING_TOOL_SECTION_TOML.encode())) as mock_file:
        mock_file.return_value.__enter__.return_value = mock_file.return_value
        config = load_app_config()
        assert config["APP_NAME"] == "VORTEXION"  # 기본값
        assert config["APP_VERSION"] == "1.0"  # 기본값

def test_load_app_config_file_not_found():
    """pyproject.toml 파일이 없는 경우 적절한 에러를 발생시키는지 테스트"""
    with patch("builtins.open", side_effect=FileNotFoundError("pyproject.toml not found")):
        with pytest.raises(FileNotFoundError):
            load_app_config()

def test_pyproject_path():
    """pyproject.toml 파일 경로가 올바른지 테스트"""
    with patch("builtins.open", mock_open(read_data=VALID_TOML.encode())) as mock_file:
        mock_file.return_value.__enter__.return_value = mock_file.return_value
        load_app_config()
        # 호출된 파일 경로 확인
        expected_path = Path(__file__).parent.parent.parent.parent / "pyproject.toml"
        mock_file.assert_called_once_with(expected_path, "rb")

def test_load_app_config_invalid_toml():
    """잘못된 TOML 형식일 때 적절한 에러가 발생하는지 테스트"""
    with patch("builtins.open", mock_open(read_data=INVALID_TOML.encode())):
        with pytest.raises(tomli.TOMLDecodeError):
            load_app_config()

def test_load_app_config_partial_settings():
    """일부 설정만 있는 경우 나머지는 기본값을 사용하는지 테스트"""
    with patch("builtins.open", mock_open(read_data=PARTIAL_TOML.encode())):
        config = load_app_config()
        assert config["APP_NAME"] == "CustomName"
        assert config["APP_VERSION"] == "1.0"  # 기본값

def test_load_app_config_permission_error():
    """파일 읽기 권한이 없는 경우 적절한 에러가 발생하는지 테스트"""
    with patch("builtins.open", side_effect=PermissionError("Permission denied")):
        with pytest.raises(PermissionError):
            load_app_config()

def test_global_config_variables():
    """전역 설정 변수가 올바르게 설정되는지 테스트"""
    assert APP_NAME == "VORTEXION"
    assert APP_VERSION == "1.0" 
