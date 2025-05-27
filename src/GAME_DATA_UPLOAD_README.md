# 게임 데이터 서버 업로드 기능

이 문서는 게임 화면과 라벨 데이터를 서버에 업로드하는 기능의 사용법을 설명합니다.

## 기능 개요

- **실시간 데이터 수집**: 게임 플레이 중 화면과 객체 정보를 실시간으로 서버에 업로드
- **일괄 업로드**: 로컬에 저장된 기존 데이터를 서버에 일괄 업로드
- **서버 관리**: 서버에 저장된 데이터 조회, 다운로드, 삭제

## 서버 API 엔드포인트

- `GET /` - 서버 상태 확인
- `POST /api/upload` - 게임 데이터 업로드
- `GET /api/download/:id` - 게임 데이터 다운로드
- `GET /api/list` - 데이터 목록 조회
- `DELETE /api/delete/:id` - 데이터 삭제

## 설치 및 설정

### 1. 의존성 설치

```bash
# rye를 사용하여 의존성 설치
rye sync
```

### 2. 서버 URL 설정

환경 변수로 서버 URL을 설정할 수 있습니다:

```bash
export GAME_SERVER_URL="http://localhost:3000"
```

기본값은 `http://localhost:3000`입니다.

## 사용법

### 1. 게임 내 실시간 업로드

게임을 실행하고 다음 키를 사용하여 제어합니다:

- **C 키**: 데이터 수집 토글 (ON/OFF)
- **U 키**: 서버 업로드 토글 (ON/OFF, 데스크톱 환경에서만)

게임 화면 좌상단에 상태가 표시됩니다:
- `DATA: ON/OFF` - 데이터 수집 상태
- `SERVER: ON/OFF` - 서버 업로드 상태
- `FRAMES: N` - 수집된 프레임 수

### 2. 명령줄 도구 사용

#### 실시간 데이터 수집

```bash
# 60초 동안 실시간 데이터 수집 및 서버 업로드
rye run upload_data realtime --duration 60

# 사용자 정의 서버 URL 사용
rye run upload_data realtime --server-url http://your-server.com:3000 --duration 30
```

#### 기존 데이터 일괄 업로드

```bash
# 기본 디렉토리의 데이터 업로드
rye run upload_data batch

# 사용자 정의 디렉토리 지정
rye run upload_data batch --images-dir path/to/images --labels-dir path/to/labels

# 사용자 정의 서버 URL 사용
rye run upload_data batch --server-url http://your-server.com:3000
```

#### 서버 데이터 목록 조회

```bash
# 서버에 저장된 데이터 목록 조회
rye run upload_data list

# 사용자 정의 서버 URL 사용
rye run upload_data list --server-url http://your-server.com:3000
```

### 3. Python 코드에서 직접 사용

```python
from src.server_client import GameDataServerClient
from src.dataset_collector import DatasetCollector

# 서버 클라이언트 생성
client = GameDataServerClient("http://localhost:3000")

# 서버 상태 확인
if client.check_server_status():
    print("서버 연결 성공")

# 파일에서 업로드
data_id = client.upload_game_data("image.png", "label.txt", {"game": "test"})

# 메모리에서 업로드
import cv2
import numpy as np

image = cv2.imread("image.png")
label_content = "0 0.5 0.5 0.1 0.1"
data_id = client.upload_game_data_from_memory(image, label_content, "frame", {"test": True})

# 데이터 수집기 사용 (서버 업로드 포함)
collector = DatasetCollector(
    server_url="http://localhost:3000",
    enable_server_upload=True
)

collector.start_collection()
# 게임 객체 정보를 detections 형태로 전달
detections = [(0, 100, 100, 120, 120)]  # (class_id, x_min, y_min, x_max, y_max)
collector.update(detections, {"level": 1, "score": 1000})
```

## 데이터 형식

### 업로드 데이터 구조

```json
{
  "timestamp": "2024-01-01T12:00:00.000Z",
  "image": {
    "filename": "frame_20240101_120000_123456.png",
    "data": "base64_encoded_image_data",
    "format": "png"
  },
  "label": {
    "filename": "frame_20240101_120000_123456.txt",
    "data": "0 0.5 0.5 0.1 0.1\n1 0.3 0.3 0.05 0.05",
    "format": "yolo"
  },
  "metadata": {
    "game_name": "VORTEXION",
    "app_width": 256,
    "app_height": 192,
    "detection_count": 2,
    "game_score": 1000,
    "game_level": 1
  }
}
```

### YOLO 라벨 형식

```
class_id x_center y_center width height
```

모든 좌표는 0-1 사이로 정규화됩니다.

## 클래스 매핑

게임 객체는 다음과 같이 클래스 ID로 매핑됩니다:

```python
CLASS_MAP = {
    "player": 0,
    "enemy": 1,
    "boss": 2,
    "player_shot": 3,
    "enemy_shot": 4,
    "powerup": 5
}
```

## 문제 해결

### 서버 연결 실패

1. 서버가 실행 중인지 확인
2. 서버 URL이 올바른지 확인
3. 방화벽 설정 확인

### 업로드 실패

1. 네트워크 연결 상태 확인
2. 서버 로그 확인
3. 이미지/라벨 데이터 형식 확인

### 의존성 오류

```bash
# 의존성 재설치
rye sync --force
```

## 개발자 정보

- 서버 클라이언트: `src/server_client.py`
- 데이터 수집기: `src/dataset_collector.py`
- 업로드 스크립트: `src/upload_game_data.py`
- 게임 통합: `src/main.py` 