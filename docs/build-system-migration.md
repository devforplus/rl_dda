# 빌드 시스템 마이그레이션 완료

## 개요

정적 HTML 파일과 Mustache 템플릿이 공존하던 이중 시스템을 **Mustache 템플릿 기반 단일 시스템**으로 통합했습니다.

## 변경사항

### 제거된 파일들
- `pyxel_web_lib/index.html` - 수동 게임용 정적 HTML
- `pyxel_web_lib/index_agent.html` - 에이전트 게임용 정적 HTML

### 새로 추가된 파일들
- `scripts/web_build_utils.py` - Mustache 템플릿 렌더링 공통 유틸리티

### 수정된 파일들
- `scripts/build.py` - `manual_game` 프리셋 사용하도록 변경
- `scripts/build_agent.py` - `agent_game` 프리셋 사용하도록 변경

## 새로운 빌드 프로세스

### 1. 수동 게임 빌드
```bash
python scripts/build.py
```
- `manual_game` 프리셋 사용
- `pyxel-run` 엘리먼트로 `src/main.py` 실행
- 로딩 화면 비활성화

### 2. 에이전트 게임 빌드
```bash
python scripts/build_agent.py
```
- `agent_game` 프리셋 사용
- `pyxel-play` 엘리먼트로 `game.pyxapp` 실행
- 로딩 화면 및 콘솔 에러 필터링 활성화

### 3. 직접 Mustache 빌드 (고급)
```bash
python scripts/build_web.py <preset_name> <output_dir>
```

## 장점

### ✅ **코드 중복 제거**
- 동일한 HTML 구조를 여러 파일에서 관리할 필요 없음
- 설정 변경 시 한 곳에서만 수정

### ✅ **유지보수성 향상**
- 중앙화된 템플릿 시스템
- 일관된 빌드 프로세스

### ✅ **설정 중앙화**
- `pyxel_web_lib/build_config.json`에서 모든 프리셋 관리
- 새로운 프리셋 추가 용이

### ✅ **확장성**
- 새로운 게임 타입 추가 시 프리셋만 추가하면 됨
- 템플릿 변경 시 모든 빌드에 자동 반영

## 프리셋 설정

### manual_game
```json
{
  "title": "RL DDA Pyxel Game",
  "pyxel_element": "pyxel-run",
  "name": "src/main.py",
  "loading_enabled": false
}
```

### agent_game
```json
{
  "title": "RL DDA Agent Game", 
  "pyxel_element": "pyxel-play",
  "name": "game.pyxapp",
  "loading_enabled": true,
  "loading_message": "Loading Pyxel Game..."
}
```

### development
```json
{
  "title": "RL DDA Development",
  "gamepad": "enabled",
  "packages": "toolz,numpy,Pillow,matplotlib",
  "filter_console_errors": false
}
```

## 마이그레이션 검증

### ✅ 빌드 테스트 통과
- `python scripts/build.py` - 정상 작동
- `python scripts/build_agent.py` - 정상 작동

### ✅ 생성된 HTML 검증
- `web/game/index.html` - manual_game 프리셋 적용됨
- `web/agentic-game/index.html` - agent_game 프리셋 적용됨

### ✅ 파일 복사 최적화
- 정적 HTML 파일들이 더 이상 복사되지 않음
- 필요한 에셋만 선택적 복사

## 향후 계획

1. **프리셋 확장**: 개발, 테스트, 프로덕션 환경별 프리셋 추가
2. **템플릿 개선**: 더 많은 커스터마이징 옵션 추가
3. **자동화**: CI/CD 파이프라인에 통합

## 롤백 방법

만약 문제가 발생할 경우:
```bash
git revert HEAD  # 이전 커밋으로 롤백
```

백업된 정적 HTML 파일들은 git 히스토리에서 복구 가능합니다. 