#!/usr/bin/env python
"""
테스트 실행 스크립트
이 스크립트는 Python 모듈 경로 문제를 해결하여 테스트를 실행합니다.
"""

import os
import sys
import asyncio

# 프로젝트 루트 디렉토리를 PYTHONPATH에 추가
sys.path.insert(0, os.path.abspath("."))

# 테스트 모듈 임포트
from src.tests.test_db import main

if __name__ == "__main__":
    print("🚀 Vortextion Server 데이터베이스 테스트 시작...")
    asyncio.run(main())
