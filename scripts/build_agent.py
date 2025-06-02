#!/usr/bin/env python3
"""
에이전트 게임을 빌드하는 스크립트
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


def copy_file(src, dst):
    """파일을 복사합니다."""
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"파일 복사: {src} -> {dst}")
    else:
        print(f"경고: 파일을 찾을 수 없습니다: {src}")


def copy_pyxel_web_lib(target_dir):
    """pyxel_web_lib의 파일들을 대상 디렉토리로 복사합니다."""
    run_command("python scripts/update_web_files.py", "pyxel_web_lib 파일 업데이트")


def create_html_from_template(
    template_path, output_path, title="VORTEXION - RL Agent Game"
):
    """템플릿에서 HTML 파일을 생성합니다."""
    if not os.path.exists(template_path):
        print(f"경고: 템플릿 파일을 찾을 수 없습니다: {template_path}")
        return

    # 템플릿 파일 읽기
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 제목 교체 (기본 제목을 에이전트 게임 제목으로 변경)
    content = content.replace("VORTEXION - Pyxel Web Game", title)

    # 출력 파일에 쓰기
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"HTML 파일 생성: {output_path} (템플릿: {template_path})")


def main():
    """에이전트 빌드 메인 함수"""
    try:
        # 1. 설정 파일 추출
        run_command("python scripts/extract_config.py", "설정 파일 추출")

        # 2. 웹 디렉토리 생성
        ensure_directory("web/agentic-game")

        # 3. pyxel_web_lib 파일들 복사
        copy_pyxel_web_lib("web/agentic-game")

        # 4. Pyxel 패키징 (에이전트용)
        run_command(
            "python -m pyxel package src src/run_agent_in_game.py",
            "에이전트 Pyxel 패키징",
        )

        # 5. 빌드된 파일 이동 (실제 생성되는 파일명 사용)
        move_file("src.pyxapp", "web/agentic-game/game.pyxapp")

        # 6. 템플릿에서 HTML 파일 생성
        create_html_from_template(
            "pyxel_web_lib/index_agent.html",
            "web/agentic-game/index.html",
            "VORTEXION - RL Agent Game",
        )

    finally:
        # 7. 설정 파일 정리 (항상 실행)
        try:
            run_command("python scripts/cleanup_config.py", "설정 파일 정리")
        except:
            pass  # 정리 실패는 무시


if __name__ == "__main__":
    main()
