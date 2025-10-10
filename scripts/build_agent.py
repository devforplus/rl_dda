#!/usr/bin/env python3
"""
Pyxel 에이전트 게임 빌드 스크립트

Mustache 템플릿을 사용하여 agent_game 프리셋으로 HTML을 생성합니다.
"""

import os
import shutil
import subprocess
from pathlib import Path

# 웹 빌드 유틸리티 import
from scripts.web_build_utils import build_html_with_preset, copy_assets


def run_command(cmd, description):
    """명령어 실행"""
    print(f"실행 중: {description}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"오류: {description} 실패")
        print(f"stderr: {result.stderr}")
        raise Exception(f"{description} 실패")
    print(f"완료: {description}")


def ensure_directory(path):
    """디렉토리 생성"""
    os.makedirs(path, exist_ok=True)
    print(f"디렉토리 생성: {path}")


def move_file(src, dst):
    """파일 이동"""
    if os.path.exists(src):
        shutil.move(src, dst)
        print(f"파일 이동: {src} -> {dst}")
    else:
        print(f"경고: 이동할 파일이 없습니다: {src}")


def copy_file(src, dst):
    """파일 복사"""
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"파일 복사: {src} -> {dst}")
    else:
        print(f"경고: 복사할 파일이 없습니다: {src}")


def copy_pyxel_web_lib(target_dir):
    """pyxel_web_lib 파일들을 대상 디렉토리로 복사"""
    src_dir = Path("pyxel_web_lib")
    dest_dir = Path(target_dir)

    # 에셋 복사 (mustache, json, html 파일 제외)
    copy_assets(
        src_dir,
        dest_dir,
        exclude_patterns=["*.mustache", "*.json", "*.html", "__pycache__"],
    )


def main():
    """에이전트 게임 빌드 메인 함수"""
    try:
        # 1. 설정 파일 추출
        run_command("python scripts/extract_config.py", "설정 파일 추출")

        # 2. 웹 디렉토리 생성
        ensure_directory("web/agentic-game")

        # 3. pyxel_web_lib 파일들 복사
        copy_pyxel_web_lib("web/agentic-game")

        # 4. 에이전트 Pyxel 패키징
        run_command(
            "python -m pyxel package src src/run_agent_in_game.py",
            "에이전트 Pyxel 패키징",
        )

        # 5. 빌드된 파일 이동 (실제 생성되는 파일명 사용)
        move_file("src.pyxapp", "web/agentic-game/game.pyxapp")

        # 6. Mustache 템플릿으로 HTML 파일 생성
        build_html_with_preset(
            preset_name="agent_game", output_path=Path("web/agentic-game/index.html")
        )

    finally:
        # 7. 설정 파일 정리 (항상 실행)
        try:
            run_command("python scripts/cleanup_config.py", "설정 파일 정리")
        except:
            pass  # 정리 실패는 무시


if __name__ == "__main__":
    main()
