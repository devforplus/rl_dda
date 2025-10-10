#!/usr/bin/env python3

"""
Update Web Files Script

This script copies all necessary files from pyxel_web_lib to web directories
ensuring that both game and agentic-game have the latest pyxel web resources.

---

웹 파일 업데이트 스크립트

pyxel_web_lib의 모든 필요한 파일들을 web 디렉토리로 복사하여
game과 agentic-game 모두 최신 pyxel 웹 리소스를 가지도록 합니다.
"""

import os
import shutil
import sys
from pathlib import Path


def copy_file_with_dirs(src: Path, dst: Path) -> None:
    """Copy file and create destination directories if needed

    ---

    필요시 대상 디렉토리를 생성하고 파일을 복사합니다.
    """
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"Copied: {src} -> {dst}")


def update_web_files() -> None:
    """Update all web files from pyxel_web_lib to web directories

    ---

    pyxel_web_lib의 모든 웹 파일들을 web 디렉토리로 업데이트합니다.
    """
    project_root = Path(__file__).parent.parent
    pyxel_web_lib = project_root / "pyxel_web_lib"
    web_dir = project_root / "web"
    src_dir = project_root / "src"

    if not pyxel_web_lib.exists():
        print(f"Error: {pyxel_web_lib} directory not found!")
        sys.exit(1)

    # Files to copy to each game directory
    # ---
    # 각 게임 디렉토리에 복사할 파일들
    files_to_copy = [
        "pyxel.js",
        "pyxel.css",
        "import_hook.py",
    ]

    # Find .whl files dynamically
    # ---
    # .whl 파일들을 동적으로 찾기
    whl_files = list(pyxel_web_lib.glob("*.whl"))
    files_to_copy.extend([f.name for f in whl_files])

    # Target directories
    # ---
    # 대상 디렉토리들
    target_dirs = [web_dir / "game", web_dir / "agentic-game"]

    for target_dir in target_dirs:
        print(f"\nUpdating {target_dir}...")

        # Copy individual files
        # ---
        # 개별 파일들 복사
        for file_name in files_to_copy:
            src_file = pyxel_web_lib / file_name
            if src_file.exists():
                dst_file = target_dir / file_name
                copy_file_with_dirs(src_file, dst_file)
            else:
                print(f"Warning: {src_file} not found, skipping...")

        # Copy images directory
        # ---
        # images 디렉토리 복사
        src_images = pyxel_web_lib / "images"
        dst_images = target_dir / "images"

        if src_images.exists():
            # Remove existing images directory and copy fresh
            # ---
            # 기존 images 디렉토리를 제거하고 새로 복사
            if dst_images.exists():
                shutil.rmtree(dst_images)
            shutil.copytree(src_images, dst_images)
            print(f"Copied directory: {src_images} -> {dst_images}")
        else:
            print(f"Warning: {src_images} directory not found!")

        # Copy src directory to agentic-game only (needed for agent script)
        # ---
        # agentic-game에만 src 디렉토리 복사 (에이전트 스크립트에 필요)
        if target_dir.name == "agentic-game" and src_dir.exists():
            dst_src = target_dir / "src"
            if dst_src.exists():
                shutil.rmtree(dst_src)
            shutil.copytree(src_dir, dst_src)
            print(f"Copied directory: {src_dir} -> {dst_src}")

    print(f"\n✅ Web files update completed!")


if __name__ == "__main__":
    update_web_files()
