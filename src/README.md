# RL DDA Game

강화학습을 위한 게임 데이터 수집 및 서버 업로드 시스템

## 기능

- 게임 플레이 중 실시간 데이터 수집
- 서버에 게임 화면과 라벨 데이터 업로드
- YOLO 형식 라벨 자동 생성
- 강화학습 에이전트 통합

## 설치

```bash
rye sync
```

## 사용법

게임 실행:
```bash
python main.py
```

데이터 업로드:
```bash
rye run upload_data --help
```

자세한 사용법은 `GAME_DATA_UPLOAD_README.md`를 참조하세요. 