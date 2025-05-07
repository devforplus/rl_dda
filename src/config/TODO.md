# 설정 파일 리팩토링 작업 진행 상황

## 리팩토링 목적 및 배경
이 작업은 기존의 모놀리식 `const.py` 파일을 기능별로 분리하여 모듈화된 설정 구조로 마이그레이션하는 것을 목표로 합니다. 이를 통해 다음과 같은 이점을 얻을 수 있습니다:
- **코드 가독성 향상**: 관련 설정을 논리적 그룹으로 구성
- **유지보수성 개선**: 특정 설정 변경 시 관련 모듈만 수정
- **확장성 강화**: 새로운 설정 카테고리 추가가 용이
- **테스트 용이성**: 개별 설정 모듈에 대한 독립적 테스트 가능

## 완료된 작업
- [x] 기존 const.py에서 모듈화된 설정 파일 구조로 마이그레이션 시작
- [x] 경로 및 색상 팔레트 설정을 config/paths 및 config/colors로 이동
  - `src/config/paths/paths.py`: 프로젝트 디렉토리 경로 설정
  - `src/config/colors/color_palette.py`: Pyxel 16색 팔레트 정의
- [x] 스테이지 관련 상수를 config/stage 모듈로 이동
  - `src/config/stage/stage_num.py`: 스테이지 열거형 및 관련 상수
- [x] 음악 관련 설정을 config/music 모듈로 이동
  - `src/config/music/music_config.py`: 스테이지별 음악 매핑
- [x] 사운드 관련 상수 및 열거형을 config/sound 모듈로 이동
  - `src/config/sound/sound_type.py`: 사운드 효과음 타입 열거형
  - `src/config/sound/sound_config.py`: 사운드 우선순위 및 채널 설정
- [x] 플레이어 관련 상수를 config/player 데이터클래스로 변환
  - `src/config/player/player_config.py`: 플레이어 관련 설정 데이터클래스

## 작업 중인 항목
- [ ] render 모듈 구현 중
  - 현재 `src/config/render/__init__.py`에 기본 구조와 TODO 주석 추가됨
  - 자세한 내용은 해당 파일의 주석 및 [render 모듈 구현 계획](#render-모듈-구현-계획) 섹션 참조
- [ ] const.py 파일의 나머지 상수 이전 작업 중
  - 현재 게임 메커니즘 관련 상수들 이전 필요
  - 적 캐릭터 관련 상수들 이전 필요

## 남은 작업
- [ ] 기존 코드에서 const.py 대신 새로운 설정 모듈 import하도록 수정
  - 우선순위: 높음
  - 시작 전략: 먼저 각 게임 객체 파일(enemy_*.py, player_shot.py 등)에서 사용 중인 상수를 분석하고 해당 import 문 변경
- [ ] const.py에서 완전히 마이그레이션 된 상수 제거
  - 우선순위: 중간
  - 진행 방법: 단계적으로 이전 완료된 상수들을 제거하며 회귀 테스트 수행
- [ ] 각 설정 모듈에 대한 추가 테스트 작성
  - 우선순위: 중간
  - 테스트 전략: 각 설정 값의 범위 및 유효성 검사, 설정 간 일관성 테스트
- [ ] render 모듈 완성 및 테스트 작성
  - 우선순위: 높음
  - 자세한 내용은 아래 [render 모듈 구현 계획](#render-모듈-구현-계획) 섹션 참조

## 참고사항
- **Python 버전 호환성 문제**: 일부 테스트에서 타입 힌팅 관련 오류 발생
  - 문제: Python 3.8에서 `list[str]` 구문 대신 `typing.List[str]` 사용 필요
  - 해결: `from typing import List` 추가 및 `List[str]` 사용으로 수정
- **경로 설정 업데이트**: config/paths 모듈에서 MUSIC_DIR 추가 필요
  - 경로: `MUSIC_DIR = ASSETS_DIR / "music"`
  - 영향받는 파일: `src/config/paths/paths.py`와 `src/config/paths/__init__.py`

## render 모듈 구현 계획 {#render-모듈-구현-계획}
`src/config/render` 모듈은 게임의 렌더링 관련 설정을 담당합니다. 다음 파일들을 구현할 예정입니다:

1. **screen_config.py**: 화면 크기, 해상도, 색상 설정
   ```python
   @dataclass
   class ScreenConfig:
       WIDTH: int = 240
       HEIGHT: int = 320
       # ... 기타 화면 관련 설정
   ```

2. **animation_config.py**: 애니메이션 프레임 관련 설정
   ```python
   @dataclass
   class AnimationConfig:
       DEFAULT_FRAME_RATE: int = 60
       # ... 기타 애니메이션 관련 설정
   ```

3. **sprite_config.py**: 스프라이트 렌더링 설정
   ```python
   @dataclass
   class SpriteConfig:
       DEFAULT_SCALE: float = 1.0
       # ... 기타 스프라이트 관련 설정
   ```

이 파일들에 대한 자세한 설명은 `src/config/render/__init__.py`의 주석을 참조하세요.

## 개발 표준
- **명명 규칙**: 상수는 `UPPER_CASE`, 클래스는 `PascalCase`, 함수/메서드는 `snake_case`
- **주석 방식**: 문서화 주석은 docstring 형식(`""" """`)으로 작성
- **테스트 파일**: 각 모듈 디렉토리에 `test_*.py` 이름으로 배치 