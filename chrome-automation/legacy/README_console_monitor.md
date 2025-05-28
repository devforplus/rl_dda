# 🔍 Chrome DevTools Console Monitor

Chrome DevTools Protocol을 사용하여 브라우저의 Console 메시지를 실시간으로 모니터링하는 도구입니다.

## 📋 기능

- **실시간 Console 모니터링**: `console.log`, `console.info`, `console.warn`, `console.error` 등 모든 Console API 호출 감지
- **Exception 추적**: JavaScript 예외 및 스택 트레이스 표시
- **색상 구분**: 로그 레벨별 색상으로 구분하여 가독성 향상
- **타임스탬프**: 각 메시지에 시간 정보 포함
- **소스 정보**: 메시지가 발생한 파일과 라인 번호 표시
- **자동 재연결**: 연결이 끊어지면 자동으로 재연결 시도

## 🚀 사용법

### 1. 기본 실행
```bash
./monitor_console.sh
```

### 2. 커스텀 포트 및 URL 패턴 지정
```bash
./monitor_console.sh [DEBUG_PORT] [URL_PATTERN]
```

**예시:**
```bash
# 기본값 (포트 9222, localhost:5175)
./monitor_console.sh

# 다른 포트 사용
./monitor_console.sh 9223

# 다른 URL 패턴 모니터링
./monitor_console.sh 9222 "example.com"
```

### 3. Node.js로 직접 실행
```bash
node console_monitor.js [DEBUG_PORT] [URL_PATTERN]
```

## 📦 의존성

- **Node.js**: JavaScript 런타임
- **ws**: WebSocket 클라이언트 라이브러리
- **node-fetch**: HTTP 요청 라이브러리 (Node.js 18 미만)

의존성은 스크립트 실행 시 자동으로 설치됩니다.

## 🎯 전제 조건

Chrome/Chromium이 다음 옵션으로 실행되어야 합니다:
```bash
--remote-debugging-port=9222
```

또는 `start_chromium.sh` 스크립트를 사용하여 Chrome을 실행하세요.

## 📺 출력 예시

```
🔍 Chrome DevTools Console Monitor
📍 디버그 포트: 9222
🎯 대상 URL 패턴: localhost:5175

🔗 연결 중: RL DDA Pyxel Game (Local Lib)
📄 URL: http://localhost:5175/
🆔 Tab ID: AB89639C9D29B70CDB27C05E8F5DB4C4

✅ WebSocket 연결 성공
📺 Console 메시지 모니터링 시작...

[21:36:15] [LOG] 🎮 Game Console Test - LOG
[21:36:16] [INFO] 📘 Game is running - INFO
[21:36:17] [WARN] ⚠️ Low performance detected - WARN
[21:36:18] [ERROR] ❌ Connection failed - ERROR
[21:36:19] [DEBUG] 🔍 Debug information - DEBUG
[21:36:20] [EXCEPTION] ReferenceError: undefined variable
    at gameLoop (game.js:45)
    at update (main.js:12)
    at <anonymous> (main.js:1)
```

## 🎨 색상 구분

- **LOG**: 회색 - 일반 로그 메시지
- **INFO**: 파란색 - 정보성 메시지
- **WARN**: 노란색 - 경고 메시지
- **ERROR**: 빨간색 - 오류 메시지
- **DEBUG**: 자홍색 - 디버그 메시지
- **EXCEPTION**: 빨간색 - JavaScript 예외

## 🛑 종료

`Ctrl+C`를 눌러 모니터링을 종료할 수 있습니다.

## 🔧 고급 사용법

### 특정 탭 모니터링
URL 패턴을 더 구체적으로 지정하여 특정 탭만 모니터링할 수 있습니다:

```bash
./monitor_console.sh 9222 "game.html"
./monitor_console.sh 9222 "localhost:3000"
./monitor_console.sh 9222 "example.com/app"
```

### 여러 탭 동시 모니터링
여러 터미널에서 각각 다른 URL 패턴으로 실행하여 여러 탭을 동시에 모니터링할 수 있습니다.

## 🐛 문제 해결

### Chrome DevTools에 연결할 수 없는 경우
1. Chrome이 `--remote-debugging-port=9222` 옵션으로 실행되었는지 확인
2. 포트가 이미 사용 중인지 확인: `netstat -tuln | grep 9222`
3. 방화벽이 포트를 차단하지 않는지 확인

### 대상 탭을 찾을 수 없는 경우
1. URL 패턴이 정확한지 확인
2. 탭이 실제로 열려있는지 확인
3. `curl -s "http://localhost:9222/json" | jq .` 명령으로 사용 가능한 탭 목록 확인

### 의존성 설치 실패
1. Node.js가 설치되어 있는지 확인: `node --version`
2. npm이 정상 작동하는지 확인: `npm --version`
3. 네트워크 연결 상태 확인

## 📁 파일 구조

- `console_monitor.js`: 메인 모니터링 스크립트
- `monitor_console.sh`: 실행용 셸 스크립트
- `test_console.js`: 테스트용 스크립트
- `README_console_monitor.md`: 이 문서

## 🔗 관련 스크립트

- `start_chromium.sh`: Chrome 헤드리스 모드 실행 (자동 클릭 포함)
- `stop_chromium.sh`: Chrome 프로세스 종료 (있다면)
- `debug_chromium.sh`: Chrome 디버그 정보 확인 (있다면) 