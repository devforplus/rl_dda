"""
렌더링 관련 설정 및 유틸리티 모듈 (WIP)

이 모듈은 게임의 시각적 표현과 관련된 모든 설정, 상수 및 유틸리티 클래스를 제공합니다.
기존의 const.py에 산재되어 있던 렌더링 관련 상수들을 체계적으로 구조화합니다.

## 모듈 구성
이 모듈은 다음과 같은 파일들로 구성될 예정입니다:

1. screen_config.py:
   - 화면 크기, 해상도, FPS 등 기본 화면 설정
   - 화면 경계값, 경계 처리 방식 등 정의

2. animation_config.py:
   - 애니메이션 프레임 속도, 기본 지속 시간 등 설정
   - 애니메이션 타입 열거형 (LOOP, ONCE, PING_PONG 등)

3. sprite_config.py:
   - 스프라이트 기본 설정 (크기, 스케일, 블렌딩 모드 등)
   - 스프라이트 시트 레이아웃 관련 설정

4. layer_config.py:
   - 렌더링 레이어 정의 및 우선순위 설정
   - 레이어별 가시성, 투명도 등 설정

## 사용 방법
설정 모듈 사용 예시:

```python
from config.render.screen_config import ScreenConfig
from config.render.animation_config import AnimationConfig

# 화면 설정 사용
screen_width = ScreenConfig.WIDTH
screen_height = ScreenConfig.HEIGHT

# 애니메이션 설정 사용
default_frame_duration = AnimationConfig.DEFAULT_FRAME_DURATION
```

## 의존성 관계
- src/config/colors/color_palette.py: 색상 팔레트 정의 참조
- src/components/render/: 렌더링 컴포넌트에서 이 설정 모듈 참조

## 구현 일정
1. 기본 설정 클래스 구조 정의: 진행 중
2. 기존 const.py에서 상수 이전: 예정
3. 스프라이트 관련 설정 구현: 예정
4. 레이어 시스템 설정 구현: 예정

## 주요 TODO 항목
- [ ] screen_config.py 구현하기
- [ ] animation_config.py 구현하기
- [ ] sprite_config.py 구현하기
- [ ] layer_config.py 구현하기
- [ ] 관련 테스트 코드 작성하기

## 참고 사항
- Pyxel 그래픽 시스템의 제약을 고려하여 설계됨
- 확장성을 위해 설정 값들은 데이터클래스로 구현
- 향후 UI 요소의 렌더링 설정도 포함할 예정
"""
