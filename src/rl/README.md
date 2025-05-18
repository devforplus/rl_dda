# VORTEXION 게임 - TorchRL 랜덤 에이전트

이 디렉토리에는 TorchRL을 사용하여 VORTEXION 게임을 위한 랜덤 에이전트 구현이 포함되어 있습니다.

## 파일 구조

- `fixed_environment.py`: 게임을 위한 개선된 강화학습 환경 래퍼 (`FixedVortexionEnv` 클래스)
- `fixed_random_agent.py`: 지속성 있는 움직임을 생성하는 개선된 랜덤 에이전트
- `game_state_detector.py`: 게임 상태 분석 및 디버깅 도구
- `run_agent.py`: 개선된 에이전트를 실행하는 스크립트
- `train.py`: 랜덤 에이전트 학습 스크립트
- `evaluate.py`: 랜덤 에이전트 평가 스크립트
- `utils.py`: 유틸리티 함수 모음
- `__init__.py`: 패키지 초기화 파일

## 환경 설정

프로젝트 종속성을 설치하려면:

```bash
# Windows
pip install -e .

# macOS/Linux
pip install -e .
```

## 사용 방법

### 에이전트 실행

개선된 랜덤 에이전트를 실행하려면:

```bash
python -m src.rl.run_agent
```

### 게임 상태 분석

게임 상태 분석 도구를 실행하려면:

```bash
python -m src.rl.game_state_detector
```

### 훈련

랜덤 에이전트를 훈련하려면:

```bash
python -m src.rl.train --episodes 10 --log-dir logs
```

옵션:
- `--episodes`: 훈련할 에피소드 수
- `--log-dir`: 로그를 저장할 디렉토리
- `--render`: 환경 렌더링 활성화 (시각화)
- `--seed`: 랜덤 시드 설정

### 평가

랜덤 에이전트를 평가하려면:

```bash
python -m src.rl.evaluate --episodes 5 --log-dir eval_logs
```

옵션:
- `--episodes`: 평가할 에피소드 수
- `--log-dir`: 평가 로그를 저장할 디렉토리
- `--render`: 환경 렌더링 활성화 (시각화)
- `--record`: 비디오 녹화 활성화
- `--seed`: 랜덤 시드 설정

## 환경 구성

`FixedVortexionEnv` 클래스는 게임을 위한 개선된 강화학습 환경을 제공합니다:

- **행동 공간**: 이동(왼쪽, 정지, 오른쪽)과 발사(발사, 대기) 조합
- **관측 공간**: 플레이어 위치, 생명력, 점수 정보
- **보상**: 점수 증가 및 생명력 감소에 기반한 보상 신호

## 랜덤 에이전트

`FixedRandomAgent` 클래스는 지속성 있는 움직임을 생성하는 개선된 랜덤 에이전트입니다. 이동 행동을 일정 시간 동안 유지함으로써 더 자연스러운 게임플레이를 제공합니다.

## 다음 단계

1. DQN, PPO 등의 강화학습 알고리즘 구현
2. 보상 함수 개선
3. 관측 공간 최적화
4. 모델 저장 및 로드 기능 추가 