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


def copy_file(src, dst):
    """파일을 복사합니다."""
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f"파일 복사: {src} -> {dst}")
    else:
        print(f"경고: 파일을 찾을 수 없습니다: {src}")


def copy_pyxel_web_lib(target_dir):
    """pyxel_web_lib의 파일들을 대상 디렉토리로 복사합니다."""
    web_lib_dir = "pyxel_web_lib"
    if not os.path.exists(web_lib_dir):
        print(f"경고: {web_lib_dir} 디렉토리를 찾을 수 없습니다.")
        return

    # CSS, JS 파일 복사
    for file_name in ["pyxel.css", "pyxel.js"]:
        src_path = os.path.join(web_lib_dir, file_name)
        dst_path = os.path.join(target_dir, file_name)
        copy_file(src_path, dst_path)

    # images 디렉토리가 있다면 복사
    images_src = os.path.join(web_lib_dir, "images")
    if os.path.exists(images_src):
        images_dst = os.path.join(target_dir, "images")
        if os.path.exists(images_dst):
            shutil.rmtree(images_dst)
        shutil.copytree(images_src, images_dst)
        print(f"디렉토리 복사: {images_src} -> {images_dst}")


def create_html_from_template(
    template_path, output_path, title="VORTEXION - Pyxel Web Game"
):
    """템플릿에서 HTML 파일을 생성합니다."""
    if not os.path.exists(template_path):
        print(f"경고: 템플릿 파일을 찾을 수 없습니다: {template_path}")
        return

    # 템플릿 파일 읽기
    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 제목 교체
    content = content.replace("VORTEXION - Pyxel Web Game", title)

    # 출력 파일에 쓰기
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"HTML 파일 생성: {output_path} (템플릿: {template_path})")


def main():
    """빌드 메인 함수"""
    try:
        # 1. 설정 파일 추출
        run_command("python scripts/extract_config.py", "설정 파일 추출")

        # 2. 웹 디렉토리 생성
        ensure_directory("web/game")

        # 3. pyxel_web_lib 파일들 복사
        copy_pyxel_web_lib("web/game")

        # 4. Pyxel 패키징
        run_command("python -m pyxel package src src/main.py", "Pyxel 패키징")

        # 5. 빌드된 파일 이동 (실제 생성되는 파일명 사용)
        move_file("src.pyxapp", "web/game/game.pyxapp")

        # 6. 템플릿에서 HTML 파일 생성
        create_html_from_template(
            "pyxel_web_lib/index.html",
            "web/game/index.html",
            "VORTEXION - Pyxel Web Game",
        )

    finally:
        # 7. 설정 파일 정리 (항상 실행)
        try:
            run_command("python scripts/cleanup_config.py", "설정 파일 정리")
        except:
            pass  # 정리 실패는 무시


if __name__ == "__main__":
    main()
