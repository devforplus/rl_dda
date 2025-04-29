# 작업 진행 중인 리팩토링 안내

이 브랜치에서는 기존 게임 코드를 모듈화하고 구조를 개선하는 리팩토링을 진행하고 있습니다.
현재 작업은 크게 두 부분으로 나뉩니다:

1. `const.py` 파일을 기능별로 분리하여 `src/config/` 디렉토리 내 모듈화된 설정 파일로 이전
2. 게임 객체들을 컴포넌트 기반 아키텍처로 전환 (`src/components/` 디렉토리)

## 작업 진행 상황

- `src/config/`: 설정 모듈화 작업 진행 중
  - 자세한 내용은 `src/config/TODO.md` 참조
  - render 모듈 작업 중 (`src/config/render/__init__.py` 참조)

- `src/components/`: 컴포넌트 기반 구조 구현 중
  - 자세한 내용은 `src/components/TODO.md` 참조
  - 기본 컴포넌트 구조 설계 완료 및 일부 구현

## 주요 변경 사항

1. 기존 `src/const.py` 파일이 다음과 같이 분리됨:
   - `src/config/colors/color_palette.py`: 색상 관련 설정
   - `src/config/paths/paths.py`: 디렉토리 경로 설정
   - `src/config/stage/stage_num.py`: 스테이지 관련 설정
   - `src/config/music/music_config.py`: 음악 관련 설정
   - `src/config/sound/sound_config.py`, `sound_type.py`: 사운드 관련 설정
   - `src/config/player/player_config.py`: 플레이어 관련 설정

2. 기존 게임 객체 구현이 컴포넌트 기반으로 재설계됨:
   - `src/components/entity_types.py`: 엔티티 타입 열거형
   - `src/components/sprite.py`: 기본 스프라이트 구현
   - `src/components/player.py`: 플레이어 관련 컴포넌트
   - `src/components/enemy.py`: 적 관련 컴포넌트

## 다음 작업자를 위한 가이드라인

1. 현재 변경 중인 파일들은 중간 작업 상태로, 일부 import 오류나 미완성 코드가 있을 수 있습니다.
2. 각 모듈의 TODO.md 파일을 참조하여 남은 작업을 이어서 진행해주세요.
3. 기존 코드에서 const.py를 import하는 부분을 새로운 설정 모듈로 교체해야 합니다.
4. 'render' 관련 모듈은 특히 설계 단계이므로 구현을 계속 진행해야 합니다.

## 알려진 이슈

1. Python 3.8 타입 힌팅 문제: `list[str]` 대신 `typing.List[str]` 사용 필요
2. config/paths 모듈에 `MUSIC_DIR`을 추가해야 함 (import 관련 오류 발생 중)
3. src/config/const.py는 임시 파일로, 최종적으로는 제거될 예정입니다.

## 테스트 방법

1. 각 설정 모듈에 대한 테스트 코드가 해당 디렉토리에 있습니다.
2. pytest를 사용하여 테스트를 실행할 수 있습니다:
   ```
   pytest src/config/colors/test_color_palette.py
   ``` 