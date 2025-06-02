# Vortexion

## Introduction
Vortexion is a MSX/SG-1000 inspired shoot-em-up written in Python and uses the Pyxel game engine.

You can play the game on itch.io [here](https://badcomputer0.itch.io/vortexion).

![](/images/prev00.png?raw=true "")![](/images/prev01.gif?raw=true "")

## Dependencies
- [Python](https://www.python.org/) 3.7 or higher.
- [Pyxel](https://github.com/kitao/pyxel) 2.0.13 or higher.

## Build & Run
- Inside the "src" directory, run "python main.py"

## CLI Tools

이 프로젝트에는 웹 스크래핑 및 Pyxel 게임 데이터 수집을 위한 CLI 도구가 포함되어 있습니다.

### 설치

필요한 종속성을 설치합니다:

```bash
pip install aiohttp websockets playwright
playwright install firefox
```

### 사용법

#### 1. 브라우저 설치
```bash
python -m scripts.cli install [--force]
```

#### 2. 콘솔 캡처
웹페이지의 콘솔 메시지를 캡처합니다:
```bash
python -m scripts.cli capture --url https://example.com [--duration 30] [--output console.log]
```

#### 3. 일반 데이터 수집
웹사이트에서 데이터를 수집합니다:
```bash
python -m scripts.cli collect --url https://example.com [--config config.json] [--output-dir ./data] [--headless]
```

#### 4. Pyxel 게임 데이터 수집 ⭐ 
Pyxel 게임에서 console.info로 출력되는 데이터를 자동으로 수집합니다:

```bash
# 무한 수집 (Ctrl+C로 중단)
python -m scripts.cli pyxel --url https://example.com/game.html --output ./game_data.txt

# 시간 제한 수집 (60초)
python -m scripts.cli pyxel --url https://example.com/game.html --output ./game_data.txt --duration 60

# 헤드리스 모드
python -m scripts.cli pyxel --url https://example.com/game.html --output ./game_data.txt --headless
```

**Pyxel 데이터 수집 동작 과정:**
1. 크로미움 브라우저를 시작하고 지정된 URL로 이동
2. "Loaded pyxel" 메시지가 콘솔에 출력될 때까지 대기
3. 메시지가 확인되면 자동으로 화면을 클릭하여 게임 시작
4. 게임 시작 후 `console.info()` 메시지만 필터링하여 파일에 저장
5. 실시간으로 수집된 데이터 개수를 표시 (`\r` 사용)
6. 지정된 시간이 지나거나 사용자가 중단할 때까지 계속 수집

**출력 파일 형식:**
```
# Pyxel 게임 데이터 수집 시작 - 2024-01-01 12:00:00
[2024-01-01 12:00:15] Game data point 1
[2024-01-01 12:00:16] Game data point 2
...
```

### 옵션 설명

- `--url`: 대상 웹페이지 또는 게임 URL (필수)
- `--port`: 크로미움 디버그 포트 (기본값: 9222)
- `--duration`: 수집 지속 시간 (초, Pyxel 명령어에서는 미지정시 무한 수집)
- `--output`: 출력 파일 경로
- `--headless`: 헤드리스 모드로 실행 (GUI 없음)
- `--config`: 데이터 수집 설정 파일 경로 (collect 명령어)
- `--output-dir`: 수집 데이터 저장 디렉토리 (collect 명령어)

## EventLogger 모듈 📊

이 프로젝트에는 강력한 이벤트 로깅 시스템이 포함되어 있습니다. 게임 및 애플리케이션의 다양한 이벤트를 구조화된 형태로 기록하고 분석할 수 있습니다.

### 주요 기능

- **구조화된 로깅**: JSON 형태의 구조화된 로그 이벤트
- **다양한 이벤트 타입**: 시스템, 게임, 사용자, 네트워크, 데이터, 성능 이벤트 지원
- **실시간 콘솔 출력**: 컬러풀하고 읽기 쉬운 실시간 로그 출력
- **파일 저장**: 자동 로그 파일 관리 및 로테이션
- **이벤트 필터링**: 로그 레벨 및 이벤트 타입별 필터링
- **콜백 시스템**: 특정 이벤트 발생 시 커스텀 콜백 실행
- **통계 및 분석**: 실시간 로그 통계 및 분석 기능
- **데이터 내보내기**: 필터링된 이벤트를 JSON 형태로 내보내기

### 빠른 시작

```python
from src.utils.event_logger import setup_logger, LogLevel, EventType

# 로거 설정
logger = setup_logger(
    namespace="my_game",
    log_level=LogLevel.INFO,
    enable_console=True,
    enable_file=True,
)

# 기본 로깅
logger.info("게임 시작", source="game_engine")
logger.warning("메모리 사용량 높음", source="memory_monitor")
logger.error("파일 로드 실패", source="asset_loader")

# 데이터와 함께 로깅
logger.game_event("플레이어 점수 갱신", source="score_system", data={
    "player_id": "player_001",
    "score": 15000,
    "level": 3
})

# 사용자 이벤트
logger.user_event("키 입력", source="input_handler", data={
    "key": "SPACE",
    "action": "shoot"
})

# 성능 모니터링
logger.performance_event("프레임 성능", source="renderer", data={
    "fps": 60.0,
    "frame_time_ms": 16.7
})
```

### 전역 로거 사용

```python
from src.utils.event_logger import log_info, log_warning, log_error, log_game_event

# 전역 로거 설정 후 편의 함수 사용
log_info("애플리케이션 시작", source="main")
log_game_event("새 레벨 진입", source="level_manager", data={"level": 2})
log_error("네트워크 연결 실패", source="network_client")
```

### 컨텍스트 매니저 사용

```python
from src.utils.event_logger import LoggerContext, LogLevel

with LoggerContext(
    namespace="temp_session",
    log_level=LogLevel.DEBUG,
    enable_console=True,
    enable_file=True,
) as logger:
    logger.info("임시 세션 시작", source="session_manager")
    # 컨텍스트 종료 시 자동으로 정리됨
```

### 이벤트 필터링 및 내보내기

```python
# 게임 이벤트만 필터링하여 내보내기
game_events_file = logger.export_events(
    output_file="data/game_events.json",
    event_types=[EventType.GAME],
)

# 에러와 경고만 필터링
error_log_file = logger.export_events(
    output_file="data/errors.json",
    log_levels=[LogLevel.WARNING, LogLevel.ERROR],
)
```

### 사용 예제 실행

전체 기능을 확인하려면 포함된 예제를 실행해보세요:

```bash
python examples/event_logger_example.py
```

### 이벤트 타입

- `SYSTEM`: 시스템 관련 이벤트 (시작, 종료, 설정 변경 등)
- `GAME`: 게임 로직 관련 이벤트 (점수, 레벨, 플레이어 액션 등)
- `USER`: 사용자 입력 이벤트 (키보드, 마우스, 터치 등)
- `NETWORK`: 네트워크 통신 이벤트 (연결, 데이터 전송 등)
- `DATA`: 데이터 처리 이벤트 (저장, 로드, 변환 등)
- `PERFORMANCE`: 성능 관련 이벤트 (FPS, 메모리 사용량 등)

### 로그 레벨

- `DEBUG`: 디버깅 정보
- `INFO`: 일반 정보
- `WARNING`: 경고
- `ERROR`: 에러
- `CRITICAL`: 치명적 오류

## Controls
- WASD keys, Arrow keys, or gamepad D-pad to move.
- Z/U key or gamepad Button 1 to fire weapon.
- X/I key or gamepad Button 2 to pause.
- ESC key to exit.

## Credits
- Game design and art by [badcomputer](https://twitter.com/badcomputer0)
- Music generator [frenchbread1222](https://github.com/shiromofufactory/8bit-bgm-generator)
- Font by [Damien Guard](https://damieng.com/)

## License
[MIT license](http://en.wikipedia.org/wiki/MIT_License)

# Reinforcement Learning DDA (Dynamic Difficulty Adjustment)

A reinforcement learning project that dynamically adjusts game difficulty based on player performance.

---

강화학습을 사용하여 플레이어 성능에 따라 게임 난이도를 동적으로 조정하는 프로젝트입니다.

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- A modern web browser

### Web Game Setup

1. **Update Web Files** (Required after any changes to `pyxel_web_lib`)
   ```bash
   python scripts/update_web_files.py
   ```

2. **Start Web Server**
   ```bash
   cd web
   python -m http.server 8000
   ```

3. **Access Games**
   - General Game: `http://localhost:8000/game/`
   - RL Agent Game: `http://localhost:8000/agentic-game/`

## 📁 Project Structure

```
├── pyxel_web_lib/              # Pyxel web resources (source)
│   ├── pyxel.js               # Main Pyxel web library
│   ├── pyxel.css              # Pyxel styling
│   ├── import_hook.py         # Python import hook
│   ├── pyxel-1.7.2-py3-none-any.whl  # Pyxel WASM package
│   └── images/                # UI images
├── web/                       # Web deployment directory
│   ├── game/                  # General game
│   └── agentic-game/          # RL agent game
├── scripts/                   # Build and utility scripts
│   └── update_web_files.py    # Web files synchronization
└── game.py                    # Main game logic
```

## 🔧 Development Workflow

### Web Files Update Process

When you modify files in `pyxel_web_lib/`, you must run the update script:

```bash
python scripts/update_web_files.py
```

This script:
- Copies all Pyxel web resources from `pyxel_web_lib/` to `web/game/` and `web/agentic-game/`
- Ensures both game versions have the latest resources
- Maintains proper file structure and dependencies

### Build Process

1. **Modify** files in `pyxel_web_lib/` (source directory)
2. **Update** web files using the script
3. **Test** in browser at `http://localhost:8000`
4. **Commit** changes to git

## 🎮 Game Features

- **Dynamic Difficulty**: AI-powered difficulty adjustment
- **Web-based**: Play directly in browser
- **Mobile Support**: Touch controls and responsive design  
- **Virtual Gamepad**: Mobile-friendly controls

## 📝 Technical Details

### Pyxel Web Integration

- **Pyxel Version**: 1.7.2
- **Pyodide Version**: 0.26.2
- **Image Format**: PNG (optimized for web)
- **Mobile Support**: Touch events and virtual gamepad

### File Management

The project uses a two-directory approach:
- `pyxel_web_lib/`: Source files for development
- `web/`: Deployment files for serving

This separation ensures clean development workflow and proper version control.

## 🐛 Troubleshooting

### Common Issues

1. **404 Errors for Resources**
   - Run `python scripts/update_web_files.py`
   - Restart web server

2. **Version Mismatches** 
   - Check `pyxel.js` constants match actual files
   - Verify `.whl` file exists in both game directories

3. **Mobile Controls Not Working**
   - Ensure images are properly copied
   - Check browser console for loading errors

## 🤝 Contributing

When contributing:
1. Make changes in `pyxel_web_lib/` directory
2. Run update script before testing
3. Follow commit conventions in `docs/developer/git-commit-rule.md`
4. Document any new build requirements
