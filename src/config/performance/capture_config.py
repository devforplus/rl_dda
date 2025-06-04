# 캡쳐 성능 최적화 설정
"""
게임 이미지 캡쳐 성능 최적화 설정

성능 우선순위:
1. NumPy 벡터화 연산 최대 활용
2. 메모리 할당 최소화 (사전 할당된 버퍼 재사용)
3. 불필요한 변환 단계 제거
4. 프레임 건너뛰기를 통한 적응형 캡쳐
"""

# 캡쳐 간격 설정 (성능에 따른 동적 조정)
CAPTURE_INTERVAL_FAST = 3  # 고성능 모드: 20 FPS 캡쳐
CAPTURE_INTERVAL_NORMAL = 5  # 일반 모드: 12 FPS 캡쳐
CAPTURE_INTERVAL_SLOW = 10  # 저성능 모드: 6 FPS 캡쳐

# 성능 임계값 (밀리초)
CAPTURE_TIME_THRESHOLD_FAST = 5.0  # 5ms 이하면 고성능 모드
CAPTURE_TIME_THRESHOLD_NORMAL = 15.0  # 15ms 이하면 일반 모드

# 이미지 압축 최적화
PNG_COMPRESSION_LEVEL = 1  # 빠른 압축 (0-9, 낮을수록 빠름)
JPEG_QUALITY = 85  # JPEG 품질 (웹 환경에서 더 빠를 수 있음)

# 메모리 최적화
PREALLOCATE_BUFFERS = True  # 버퍼 사전 할당
BUFFER_POOL_SIZE = 3  # 순환 버퍼 풀 크기

# 웹 환경 최적화
WEB_USE_WORKER = True  # 웹 워커 사용 (가능한 경우)
WEB_BATCH_SIZE = 4  # 웹에서 배치 처리 크기

# 캡쳐 품질 최적화
SKIP_IDENTICAL_FRAMES = True  # 동일한 프레임 건너뛰기
FRAME_SIMILARITY_THRESHOLD = 0.95  # 프레임 유사성 임계값

# 디버그 설정
ENABLE_PERFORMANCE_LOGGING = True  # 성능 로깅 활성화
LOG_SLOW_CAPTURES = True  # 느린 캡쳐 로깅
PERFORMANCE_SAMPLE_RATE = 0.1  # 성능 로깅 샘플링 비율 (10%)
