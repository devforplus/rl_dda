#!/usr/bin/env python3
"""
pyproject.toml에서 [tool.game] 설정을 추출하여 pyproject.json으로 저장
description: 빌드/개발 시 필요한 설정만 JSON으로 추출
"""

import json
import sys
from pathlib import Path


def extract_config():
    """pyproject.toml에서 [tool.game] 설정을 추출하여 JSON으로 저장"""
    try:
        import tomli
    except ImportError:
        print(
            "Error: tomli is required. Install with: pip install tomli", file=sys.stderr
        )
        return False

    # 프로젝트 루트 경로
    root_dir = Path(__file__).parent.parent
    pyproject_path = root_dir / "pyproject.toml"
    json_output_path = root_dir / "src" / "pyproject.json"

    try:
        # pyproject.toml 읽기
        with open(pyproject_path, "rb") as f:
            pyproject_data = tomli.load(f)

        # [tool.game] 섹션 추출
        game_config = pyproject_data.get("tool", {}).get("game", {})

        if not game_config:
            print(
                "Warning: [tool.game] section not found in pyproject.toml",
                file=sys.stderr,
            )
            game_config = {"app_name": "VORTEXION", "app_version": "1.0"}

        # JSON으로 저장
        json_output_path.parent.mkdir(exist_ok=True)
        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(game_config, f, indent=2, ensure_ascii=False)

        print(f"Config extracted to {json_output_path}")
        print(f"Extracted data: {game_config}")
        return True

    except FileNotFoundError:
        print(f"Error: {pyproject_path} not found", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error extracting config: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = extract_config()
    sys.exit(0 if success else 1)
