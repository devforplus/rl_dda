#!/usr/bin/env python3
"""
게임을 빌드하는 스크립트
"""

import subprocess
import sys
import os
import shutil


def run_command(cmd, description):
    """명령어를 실행하고 결과를 확인합니다."""
    print(f"실행 중: {description}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"오류: {description} 실패")
        sys.exit(result.returncode)


def ensure_directory(path):
    """디렉토리가 없으면 생성합니다."""
    os.makedirs(path, exist_ok=True)
    print(f"디렉토리 확인: {path}")


def move_file(src, dst):
    """파일을 이동합니다."""
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"파일 이동: {src} -> {dst}")
    else:
        print(f"경고: 파일을 찾을 수 없습니다: {src}")


def main():
    """빌드 메인 함수"""
    try:
        # 1. 설정 파일 추출
        run_command("python scripts/extract_config.py", "설정 파일 추출")

        # 2. 웹 디렉토리 생성
        ensure_directory("web/game")

        # 3. Pyxel 패키징
        run_command("python -m pyxel package src src/main.py", "Pyxel 패키징")

        # 4. 빌드된 파일 이동
        move_file("src.pyxapp", "web/game/game.pyxapp")

    finally:
        # 5. 설정 파일 정리 (항상 실행)
        try:
            run_command("python scripts/cleanup_config.py", "설정 파일 정리")
        except:
            pass  # 정리 실패는 무시


if __name__ == "__main__":
    main()
