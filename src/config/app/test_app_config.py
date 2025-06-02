import json
import tempfile
from pathlib import Path
from unittest.mock import patch
import pytest

from .config.app.app import (
    APP_NAME,
    APP_VERSION,
    load_app_config,
    DEFAULT_APP_NAME,
    DEFAULT_APP_VERSION,
)


def test_app_constants():
    """앱 상수들이 올바르게 정의되어 있는지 테스트"""
    assert APP_NAME == "VORTEXION"
    assert APP_VERSION == "1.0"


def test_load_app_config_with_valid_json():
    """유효한 JSON 파일에서 설정을 올바르게 로드하는지 테스트"""
    config_data = {"app_name": "TEST_GAME", "app_version": "2.0"}

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name

    try:
        with patch(".config.app.app.Path") as mock_path:
            mock_path.return_value = Path(temp_path)

            app_name, app_version = load_app_config()
            assert app_name == "TEST_GAME"
            assert app_version == "2.0"
    finally:
        Path(temp_path).unlink()


def test_load_app_config_file_not_found():
    """JSON 파일이 없을 때 기본값을 반환하는지 테스트"""
    with patch(".config.app.app.Path") as mock_path:
        mock_path.return_value = Path("/nonexistent/file.json")

        app_name, app_version = load_app_config()
        assert app_name == DEFAULT_APP_NAME
        assert app_version == DEFAULT_APP_VERSION


def test_load_app_config_partial_data():
    """일부 데이터만 있을 때 기본값으로 보완하는지 테스트"""
    config_data = {
        "app_name": "PARTIAL_GAME"
        # app_version 누락
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config_data, f)
        temp_path = f.name

    try:
        with patch(".config.app.app.Path") as mock_path:
            mock_path.return_value = Path(temp_path)

            app_name, app_version = load_app_config()
            assert app_name == "PARTIAL_GAME"
            assert app_version == DEFAULT_APP_VERSION
    finally:
        Path(temp_path).unlink()


def test_load_app_config_invalid_json():
    """잘못된 JSON 파일일 때 기본값을 반환하는지 테스트"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ invalid json")
        temp_path = f.name

    try:
        with patch(".config.app.app.Path") as mock_path:
            mock_path.return_value = Path(temp_path)

            app_name, app_version = load_app_config()
            assert app_name == DEFAULT_APP_NAME
            assert app_version == DEFAULT_APP_VERSION
    finally:
        Path(temp_path).unlink()
