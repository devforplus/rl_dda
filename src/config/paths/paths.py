from os.path import dirname
from pathlib import Path
from toolz.functoolz import pipe

# 프로젝트 루트 디렉토리 경로 생성
__PROJECT_DIR = pipe(
    __file__,
    dirname,
    Path,
    lambda path: path.parent.parent.parent,
)

# 주요 디렉토리 경로 정의
SOURCE_DIR = __PROJECT_DIR / "src"  # 소스 코드 디렉토리 경로
ASSETS_DIR = SOURCE_DIR / "assets"  # 에셋 디렉토리 경로

# 공개 인터페이스 정의
__all__ = [
    "ASSETS_DIR",
    "SOURCE_DIR",
]
