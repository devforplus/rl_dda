# 🚀 Chrome Automation

Chrome DevTools Protocol을 사용한 TypeScript 기반 브라우저 자동화 도구입니다.

## ✨ 주요 기능

- **🎯 자동 Chrome 실행**: 헤드리스 모드로 Chrome 실행 및 관리
- **🔍 Console 메시지 감지**: 특정 Console 메시지를 감지하여 자동 액션 수행
- **🖱️ 자동 클릭**: 메시지 감지 후 자동으로 화면 클릭
- **📺 실시간 모니터링**: Console 메시지 및 Exception 실시간 모니터링
- **🎨 컬러 로깅**: 로그 레벨별 색상 구분으로 가독성 향상
- **⚡ TypeScript**: 완전한 타입 안전성과 IntelliSense 지원

## 🛠️ 기술 스택

- **TypeScript**: 타입 안전성과 개발 경험 향상
- **pnpm**: 빠르고 효율적인 패키지 관리
- **Chrome DevTools Protocol**: 브라우저 제어 및 모니터링
- **WebSocket**: 실시간 통신
- **ESM**: 최신 JavaScript 모듈 시스템

## 📦 설치

```bash
# 의존성 설치
pnpm install

# TypeScript 빌드
pnpm build
```

## 🚀 사용법

### Chrome 자동 실행 + 클릭

```bash
# 기본 설정으로 실행 (Pyxel 로딩 감지 후 클릭)
pnpm start
```

### Console 모니터링만

```bash
# Console 메시지만 모니터링
pnpm start monitor
```

### 커스텀 설정

```bash
# 다른 URL과 설정으로 실행
pnpm start start --url http://localhost:3000 --width 1280 --height 720

# 다른 메시지 패턴으로 대기
pnpm start start --wait-message "App ready" --click-delay 2000

# 다른 디버그 포트 사용
pnpm start monitor --debug-port 9223
```

## ⚙️ 설정 옵션

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--url` | `http://localhost:5175` | 대상 URL |
| `--width` | `1920` | 브라우저 창 너비 |
| `--height` | `1080` | 브라우저 창 높이 |
| `--debug-port` | `9222` | Chrome DevTools 디버그 포트 |
| `--wait-message` | `"Loaded pyxel"` | 대기할 Console 메시지 |
| `--click-delay` | `1000` | 메시지 감지 후 클릭까지의 딜레이 (ms) |

## 📋 스크립트 명령어

```bash
# 개발 모드 (TypeScript 직접 실행)
pnpm dev

# 빌드
pnpm build

# 빌드된 파일 실행
pnpm start

# 타입 체크
pnpm run type-check

# 빌드 파일 정리
pnpm clean
```

## 🏗️ 프로젝트 구조

```
chrome-automation/
├── src/
│   ├── types.ts              # 타입 정의
│   ├── utils.ts              # 유틸리티 함수
│   ├── chrome-client.ts      # Chrome DevTools 클라이언트
│   ├── chrome-launcher.ts    # Chrome 프로세스 관리
│   ├── console-monitor.ts    # Console 모니터링
│   └── index.ts              # 메인 진입점
├── dist/                     # 빌드 결과물
├── package.json
├── tsconfig.json
└── README.md
```

## 🔧 API 문서

### ChromeLauncher

Chrome 프로세스를 관리하고 자동화 작업을 수행하는 클래스입니다.

```typescript
const launcher = new ChromeLauncher({
  url: 'http://localhost:5175',
  width: 1920,
  height: 1080,
  debugPort: 9222,
  headless: true,
  waitForMessage: 'Loaded pyxel',
  clickAfterMessage: true,
  clickDelay: 1000
});

await launcher.start();
```

### ConsoleMonitor

Console 메시지를 실시간으로 모니터링하는 클래스입니다.

```typescript
const monitor = new ConsoleMonitor({
  debugPort: 9222,
  targetUrlPattern: 'localhost:5175',
  timeout: 30000
});

await monitor.start();
```

### ChromeDevToolsClient

Chrome DevTools Protocol과 통신하는 저수준 클라이언트입니다.

```typescript
const client = new ChromeDevToolsClient(9222);
await client.connectToTab(tab);
await client.enableDomain('Runtime');
await client.click({ x: 960, y: 540 });
```

## 🎯 사용 사례

### Pyxel 게임 자동 시작

```bash
# Pyxel 게임이 로딩된 후 자동으로 클릭하여 게임 시작
pnpm start start --wait-message "Loaded pyxel"
```

### 웹 앱 개발 모니터링

```bash
# 개발 중인 웹 앱의 Console 메시지 모니터링
pnpm start monitor --debug-port 9222
```

### 자동화 테스트

```bash
# 특정 메시지 감지 후 자동 액션 수행
pnpm start start --url http://localhost:3000 --wait-message "Test ready" --click-delay 500
```

## 🐛 문제 해결

### Chrome 연결 실패

```bash
# Chrome이 실행 중인지 확인
ps -ef | grep chromium-browser

# 포트 사용 확인
netstat -tuln | grep 9222
```

### 모듈 오류

```bash
# 의존성 재설치
rm -rf node_modules pnpm-lock.yaml
pnpm install
```

### 빌드 오류

```bash
# TypeScript 설정 확인
pnpm run type-check

# 빌드 파일 정리 후 재빌드
pnpm clean && pnpm build
```

## 📄 라이선스

ISC

## 🤝 기여

이슈나 PR을 통해 기여해주세요!

---

**이전 bash 스크립트에서 TypeScript 기반 도구로 완전히 마이그레이션되었습니다! 🎉** 