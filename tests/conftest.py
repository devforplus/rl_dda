import pytest
import os
from pathlib import Path
from unittest.mock import MagicMock


@pytest.fixture(scope="session")
def weights_path():
    """Create a dummy weights file for testing and return the path."""
    dummy_weights_content = b"This is a dummy model file."
    weights_dir = Path("tests/models")
    weights_dir.mkdir(exist_ok=True)
    weights_file = weights_dir / "dummy_model.pt"
    if not weights_file.exists():
        weights_file.write_bytes(dummy_weights_content)

    return str(weights_file.resolve())


# YOLO detector fixture removed - no longer using YOLO models
