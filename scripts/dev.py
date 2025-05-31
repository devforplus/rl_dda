#!/usr/bin/env python3
"""
개발 환경에서 게임을 실행하는 스크립트
"""

import subprocess
import sys
import os


def run_command(cmd, description):
    """명령어를 실행하고 결과를 확인합니다."""
    print(f"실행 중: {description}")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"오류: {description} 실패")
        sys.exit(result.returncode)


def main():
    """개발 환경 실행 메인 함수"""
    try:
        # 1. 설정 파일 추출
        run_command("python scripts/extract_config.py", "설정 파일 추출")

        # 2. 메인 게임 실행
        run_command("python src/main.py", "게임 실행")

    finally:
        # 3. 설정 파일 정리 (항상 실행)
        try:
            run_command("python scripts/cleanup_config.py", "설정 파일 정리")
        except:
            pass  # 정리 실패는 무시


if __name__ == "__main__":
    main()
