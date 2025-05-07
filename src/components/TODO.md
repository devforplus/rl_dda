# 컴포넌트 기반 구조 리팩토링 작업 진행 상황

## 리팩토링 목적 및 배경
이 작업은 기존의 절차적/객체 지향적 코드를 컴포넌트 기반 구조로 전환하는 것을 목표로 합니다. 컴포넌트 기반 아키텍처는 다음과 같은 이점을 제공합니다:
- **모듈성 향상**: 각 기능을 독립적인 컴포넌트로 분리하여 코드 복잡성 감소
- **재사용성 증가**: 범용적인 컴포넌트를 여러 객체에서 활용 가능
- **확장성 개선**: 새로운 기능 추가 시 기존 코드 변경 최소화
- **테스트 용이성**: 각 컴포넌트를 독립적으로 테스트 가능

## 컴포넌트 구조 설계
현재 구현 중인 컴포넌트 아키텍처는 다음과 같은 계층 구조를 따릅니다:
```
components/
├── entity_types.py  # 기본 엔티티 유형 정의
├── sprite.py        # 기본 스프라이트 구현
├── enemy.py         # 적 관련 컴포넌트
├── player.py        # 플레이어 관련 컴포넌트
└── render/          # 렌더링 관련 컴포넌트 (예정)
```

## 완료된 작업
- [x] 기본 컴포넌트 구조 설계
  - 엔티티 유형, 스프라이트 기반 클래스, 특수 객체 컴포넌트 구조 수립
- [x] entity_types.py 열거형 정의
  - `EntityType` 열거형: 게임 내 모든 엔티티 유형 정의
  - `CollisionType` 열거형: 충돌 처리 유형 정의
- [x] sprite.py 기본 클래스 구현
  - `Sprite` 기본 클래스: 위치, 크기, 애니메이션 속성 정의
  - `MovableSprite` 클래스: 이동 관련 기능 추가
- [x] enemy.py 기본 인터페이스 구현
  - `Enemy` 기본 클래스: 적 객체의 공통 속성 및 행동 정의
  - `EnemyBehavior` 추상 클래스: 적 행동 패턴 인터페이스 정의
- [x] player.py 기본 구현
  - `Player` 클래스: 플레이어 속성 및 동작 정의
  - `PlayerState` 열거형: 플레이어 상태 정의

## 작업 중인 항목
- [ ] render 관련 컴포넌트 구현 중
  - 현재 스프라이트 렌더링 컴포넌트 설계 중
  - 렌더링 계층 관리 기능 구현 중
  - 자세한 내용은 [Render 컴포넌트 구현 계획](#render-컴포넌트-구현-계획) 섹션 참조
- [ ] 각 컴포넌트 간 상호작용 로직 구현 중
  - 충돌 감지 시스템 설계 진행 중
  - 이벤트 기반 통신 메커니즘 설계 중

## 남은 작업
- [ ] 기존 코드에서 새로운 컴포넌트 구조 사용하도록 변경
  - 우선순위: 높음
  - 적용 전략: 게임 루프 및 메인 모듈부터 순차적으로 변경
  - 필수 단계: 1) 컴포넌트 인스턴스 생성 2) 기존 객체 대체 3) 테스트
- [ ] 슛(shot) 관련 컴포넌트 구현
  - 우선순위: 높음
  - 필요 컴포넌트: `PlayerShot`, `EnemyShot` 클래스
  - 주요 고려사항: 탄막 패턴, 충돌 감지, 공격력 계산
- [ ] 파워업 관련 컴포넌트 구현
  - 우선순위: 중간
  - 필요 컴포넌트: `PowerUp` 클래스, `PowerUpEffect` 인터페이스
- [ ] 폭발 효과 관련 컴포넌트 구현
  - 우선순위: 낮음
  - 필요 컴포넌트: `Explosion` 클래스, `ParticleSystem` 클래스
- [ ] 각 컴포넌트에 대한 테스트 작성
  - 우선순위: 중간
  - 테스트 전략: 단위 테스트 중심, 모의 객체 활용
- [ ] 컴포넌트 간 의존성 최소화 및 인터페이스 정리
  - 우선순위: 높음
  - 방법: 인터페이스 추상화, 의존성 주입 패턴 적용

## Render 컴포넌트 구현 계획 {#render-컴포넌트-구현-계획}
`components/render` 모듈은 게임 객체의 시각적 표현을 담당합니다. 다음 컴포넌트들을 구현할 예정입니다:

1. **RenderComponent**: 기본 렌더링 컴포넌트
   ```python
   class RenderComponent:
       def __init__(self, sprite, layer=0):
           self.sprite = sprite
           self.layer = layer
           self.visible = True
       
       def render(self, screen):
           # 스프라이트 렌더링 로직
   ```

2. **AnimationComponent**: 애니메이션 처리 컴포넌트
   ```python
   class AnimationComponent:
       def __init__(self, sprite_sheet, frame_duration=5):
           self.sprite_sheet = sprite_sheet
           self.current_frame = 0
           self.frame_duration = frame_duration
       
       def update(self):
           # 애니메이션 프레임 업데이트 로직
   ```

3. **LayerManager**: 렌더링 레이어 관리 시스템
   ```python
   class LayerManager:
       def __init__(self):
           self.layers = defaultdict(list)
       
       def add(self, component, layer):
           # 렌더링 컴포넌트 추가 로직
       
       def render_all(self, screen):
           # 모든 레이어 렌더링 로직
   ```

## 컴포넌트 간 관계 및 상호작용
현재 설계 중인 컴포넌트 시스템의 주요 상호작용은 다음과 같습니다:

1. **기본 계층 구조**:
   - `Sprite` → `MovableSprite` → 특수 객체(`Enemy`, `Player` 등)

2. **충돌 시스템**:
   - 충돌 감지는 `CollisionComponent`가 담당
   - 충돌 처리는 `EntityType`과 `CollisionType`에 기반하여 결정
   - 충돌 이벤트는 이벤트 시스템을 통해 관련 컴포넌트에 전파

3. **렌더링 파이프라인**:
   - 각 게임 객체는 `RenderComponent` 보유
   - `LayerManager`가 모든 렌더링 컴포넌트를 레이어별로 관리
   - 게임 루프에서 `LayerManager.render_all()` 호출하여 전체 화면 렌더링

## 참고사항
- **설계 패턴**: 컴포넌트 기반 아키텍처는 Entity-Component-System(ECS) 패턴의 간소화된 버전
- **성능 고려사항**: 렌더링 최적화를 위해 화면 밖 객체는 렌더링 생략
- **확장성**: 향후 스크립팅 시스템이나 행동 트리 등 고급 기능 추가 가능

## 개발 표준
- **명명 규칙**: 컴포넌트 클래스는 `PascalCase`로 작성하고 `Component` 접미사 사용
- **주석 방식**: 모든 퍼블릭 메서드에 docstring 추가
- **의존성 관리**: 순환 의존성 방지, 상위 모듈이 하위 모듈에 의존하지 않도록 주의
- **테스트**: 각 컴포넌트는 단위 테스트 작성 필수 