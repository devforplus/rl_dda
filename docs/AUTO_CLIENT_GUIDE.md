# RL DDA 자동 게임 데이터 업로드 클라이언트 🎉

클라이언트에서 **한 번만 설정**하면, 모든 게임 데이터가 자동으로 DB에 저장됩니다!

## 🚀 특징

- **완전 자동화**: 게임 세션 시작 후 모든 프레임이 자동으로 업로드
- **스마트 필터링**: 중요한 액션과 상황만 선별적으로 업로드
- **실시간 처리**: 게임 플레이 중 백그라운드에서 실시간 업로드
- **재시도 메커니즘**: 네트워크 오류 시 자동 재시도
- **플랫폼 호환**: 웹(Pyodide)과 데스크톱 환경 모두 지원
- **통계 제공**: 실시간 업로드 통계 및 성공률 추적

## 📦 설치 및 설정

```python
# 필요한 라이브러리가 이미 설치되어 있다면 바로 사용 가능
from src.auto_game_client import RLDDAAutoClient, create_auto_client_sync
```

## 🎮 기본 사용법

### 1. 간단한 시작 (원라이너)

```python
import asyncio
from src.auto_game_client import create_auto_client_sync

# 한 줄로 클라이언트 생성 및 세션 시작
client = create_auto_client_sync(
    server_url="http://localhost:3000",
    game_id="my_awesome_game",
    player_id="player_001"
)

# 게임 루프에서
screen_array = get_game_screen()  # 게임에서 화면 캡처
frame_data = client.capture_frame_from_array(screen_array, "JUMP")
asyncio.run(client.upload_frame_if_important(frame_data))

# 게임 종료 시
asyncio.run(client.end_game_session())
```

### 2. 완전 자동화 설정

```python
import asyncio
from src.auto_game_client import RLDDAAutoClient, GameSessionConfig

async def setup_auto_upload():
    # 클라이언트 초기화
    client = RLDDAAutoClient("http://localhost:3000")
    
    # 세션 설정
    config = GameSessionConfig(
        game_id="platformer_game",
        player_id="user123",
        auto_upload_interval=2.0,  # 2초마다 자동 업로드
        random_capture_rate=0.15   # 15% 확률로 일반 프레임도 업로드
    )
    
    # 세션 시작
    await client.start_game_session("platformer_game", "user123", config)
    
    # 프레임 캡처 함수 정의
    def capture_frame():
        screen = get_current_game_screen()  # 게임별 구현 필요
        return client.capture_frame_from_array(
            image_array=screen,
            player_action=game.current_action,
            game_score=game.score,
            game_level=game.level,
            player_position=game.get_player_position(),
            enemies=game.get_enemies(),
            items=game.get_items()
        )
    
    # 자동 업로드 시작 - 이제 모든 것이 자동!
    client.start_auto_upload(capture_frame)
    
    return client

# 사용
client = await setup_auto_upload()
# 이제 게임을 플레이하면 자동으로 데이터가 업로드됩니다!

# 게임 종료 시에만 호출
await client.end_game_session()
```

## 🎯 고급 사용법

### 커스텀 업로드 조건

```python
def custom_upload_condition(frame_data):
    """특별한 상황에서만 업로드"""
    # 보스전이거나 점수가 높을 때만
    return (frame_data.game_level >= 5 or 
            frame_data.game_score >= 1000 or
            len(frame_data.enemies) >= 3)

client.set_should_upload_callback(custom_upload_condition)
```

### 실시간 통계 모니터링

```python
# 게임 루프에서
stats = client.get_stats()
print(f"📊 캡처: {stats['total_frames_captured']}, "
      f"업로드: {stats['total_frames_uploaded']}, "
      f"성공률: {stats['upload_success_rate']:.1f}%")
```

### 즉시 업로드 (중요한 순간)

```python
# 특별한 액션이나 이벤트 시 즉시 업로드
if player_action == "BOSS_DEFEAT":
    frame_data = client.capture_frame_from_array(screen, "BOSS_DEFEAT")
    await client.upload_frame_if_important(frame_data)
```

## 🔧 게임별 연동 방법

### Pygame 게임

```python
import pygame
import numpy as np

def get_pygame_screen():
    """Pygame 화면을 NumPy 배열로 변환"""
    screen_surface = pygame.display.get_surface()
    screen_array = pygame.surfarray.array3d(screen_surface)
    return np.transpose(screen_array, (1, 0, 2))  # (width, height, 3) -> (height, width, 3)

# 게임 루프에서
screen = get_pygame_screen()
frame_data = client.capture_frame_from_array(screen, current_action)
```

### Unity 게임 (Python 스크립팅)

```python
# Unity에서 스크린샷을 NumPy 배열로 전달받는 경우
def capture_unity_frame(unity_screen_data, action):
    return client.capture_frame_from_array(
        image_array=unity_screen_data,
        player_action=action,
        game_score=Unity.GetScore(),
        player_position=Unity.GetPlayerPosition()
    )
```

### 웹 게임 (Pyodide)

```python
# 웹 환경에서 JavaScript와 연동
import js

def capture_web_frame():
    # JavaScript 게임에서 데이터 가져오기
    canvas_data = js.gameCanvas.getImageData()
    screen_array = np.array(canvas_data)
    
    return client.capture_frame_from_array(
        image_array=screen_array,
        player_action=js.game.currentAction,
        game_score=js.game.score
    )
```

## 📈 성능 최적화

### 업로드 조건 최적화

```python
# 효율적인 필터링으로 네트워크 사용량 최소화
config = GameSessionConfig(
    auto_upload_interval=3.0,      # 간격 늘리기
    random_capture_rate=0.05,      # 랜덤 캡처 줄이기
    max_queue_size=50,             # 큐 크기 제한
    max_retry_count=2              # 재시도 횟수 제한
)
```

### 이미지 품질 조정

```python
# 이미지 크기 줄이기 (게임별 구현)
def resize_screen(screen_array, scale=0.5):
    from PIL import Image
    h, w = screen_array.shape[:2]
    new_size = (int(w * scale), int(h * scale))
    img = Image.fromarray(screen_array)
    resized = img.resize(new_size)
    return np.array(resized)

# 사용
small_screen = resize_screen(screen_array)
frame_data = client.capture_frame_from_array(small_screen, action)
```

## 🔍 디버깅 및 모니터링

### 로그 레벨 설정

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# 상세한 업로드 로그가 출력됩니다
client = RLDDAAutoClient("http://localhost:3000")
```

### 네트워크 상태 확인

```python
# 서버 연결 상태 체크
if await client.server_client.check_server_status():
    print("✅ 서버 연결 정상")
else:
    print("❌ 서버 연결 실패")
```

### 업로드 실패 처리

```python
def handle_upload_failure(frame_data):
    """업로드 실패 시 로컬 저장"""
    import json
    import base64
    
    # 로컬 파일로 백업
    backup_data = {
        "timestamp": time.time(),
        "action": frame_data.player_action,
        "score": frame_data.game_score,
        "image_base64": frame_data.image_base64[:100] + "..."  # 일부만 저장
    }
    
    with open(f"backup_frame_{int(time.time())}.json", "w") as f:
        json.dump(backup_data, f)

# 클라이언트에 실패 핸들러 등록 (커스텀 구현 시)
```

## 🎭 예제 프로젝트

완전한 예제는 `examples/auto_upload_example.py`를 참조하세요:

```bash
python examples/auto_upload_example.py
```

## 🤝 기존 코드와의 호환성

기존 `server_client.py`를 사용하던 코드도 그대로 작동합니다:

```python
# 기존 방식
from src.server_client import GameDataServerClient
client = GameDataServerClient("http://localhost:3000")
client.upload_game_data_sync(image_path, label_path)

# 새로운 자동화 방식과 함께 사용 가능
from src.auto_game_client import RLDDAAutoClient
auto_client = RLDDAAutoClient("http://localhost:3000")
# 두 클라이언트 모두 같은 서버와 호환됩니다
```

## 🛠️ 문제 해결

### 자주 발생하는 문제

1. **서버 연결 실패**
   ```python
   # 서버 URL 확인
   print(client.server_url)
   # 서버 상태 확인
   status = await client.server_client.check_server_status()
   ```

2. **메모리 사용량 증가**
   ```python
   # 큐 크기 제한 설정
   config.max_queue_size = 20
   # 이미지 해상도 줄이기
   ```

3. **업로드 속도 느림**
   ```python
   # 업로드 간격 조정
   config.auto_upload_interval = 5.0
   # 업로드 조건 엄격하게 설정
   ```

### 로그 확인

모든 업로드 활동은 콘솔에 상세히 출력됩니다:
- ✅ 성공한 업로드
- ❌ 실패한 업로드  
- 🤖 자동 업로드 시작/중단
- 📊 실시간 통계

## 🎉 결론

이제 **단 몇 줄의 코드**로 게임 데이터 수집이 완전 자동화됩니다!

```python
# 이것만 있으면 끝!
client = create_auto_client_sync("http://localhost:3000", "my_game", "player1")
client.start_auto_upload(my_capture_function)
# 🎮 게임 플레이...
await client.end_game_session()
```

**모든 게임 데이터가 자동으로 DB에 저장되어 AI 학습에 활용됩니다!** 🚀 