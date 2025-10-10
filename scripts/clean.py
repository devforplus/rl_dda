#!/usr/bin/env python3
"""
빌드 파일들을 정리하는 스크립트
"""

import os
import shutil
import glob


def remove_file(path):
    """파일을 안전하게 삭제합니다."""
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"파일 삭제: {path}")
    except Exception as e:
        print(f"파일 삭제 실패: {path} - {e}")


def remove_directory(path):
    """디렉토리를 안전하게 삭제합니다."""
    try:
        if os.path.exists(path):
            shutil.rmtree(path)
            print(f"디렉토리 삭제: {path}")
    except Exception as e:
        print(f"디렉토리 삭제 실패: {path} - {e}")


def remove_pattern(pattern):
    """패턴에 맞는 파일들을 삭제합니다."""
    files = glob.glob(pattern)
    for file in files:
        remove_file(file)


def main():
    """정리 메인 함수"""
    print("빌드 파일 정리 시작...")

    # 웹 디렉토리 삭제 (HTML 파일 포함)
    remove_directory("web/game")
    remove_directory("web/agentic-game")

    # pyxapp 파일들 삭제 (실제 생성되는 파일명들)
    remove_file(".pyxapp")  # 메인 게임용
    remove_pattern("*.pyxapp")  # 모든 pyxapp 파일

    print("빌드 파일 정리 완료!")


if __name__ == "__main__":
    main()
