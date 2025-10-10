#!/usr/bin/env python3
"""
pyproject.json 파일을 제거
description: 빌드/개발 완료 후 임시 설정 파일 정리
"""

import sys
from pathlib import Path


def cleanup_config():
    """pyproject.json 파일 제거"""
    # 프로젝트 루트 경로
    root_dir = Path(__file__).parent.parent
    json_file_path = root_dir / "src" / "pyproject.json"

    try:
        if json_file_path.exists():
            json_file_path.unlink()
            print(f"Removed {json_file_path}")
            return True
        else:
            print(f"File {json_file_path} does not exist")
            return True
    except Exception as e:
        print(f"Error removing config file: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    success = cleanup_config()
    sys.exit(0 if success else 1)
