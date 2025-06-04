#!/usr/bin/env python
"""
PPO 테스트 실행 스크립트

시스템 경로에 src 디렉토리를 추가하여 import 문제를 해결합니다.
"""

import sys
import os

# src 디렉토리를 시스템 경로에 추가
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

# PPO 테스트 실행
if __name__ == "__main__":
    from rl.test_ppo import run_all_tests

    run_all_tests()
