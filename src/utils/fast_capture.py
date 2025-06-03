"""
고성능 게임 이미지 캡쳐 최적화 유틸리티

주요 최적화 기법:
1. 메모리 사전 할당 및 재사용
2. NumPy 벡터화 연산 최대 활용
3. 불필요한 변환 단계 제거
4. 적응형 성능 조정
5. 프레임 중복 검사
"""

import time
import io
import base64
import numpy as np
from typing import Optional, Tuple, List
from collections import deque
import hashlib

try:
    from PIL import Image as PILImage

    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    import cv2

    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False

from src.config.performance.capture_config import (
    CAPTURE_INTERVAL_FAST,
    CAPTURE_INTERVAL_NORMAL,
    CAPTURE_INTERVAL_SLOW,
    CAPTURE_TIME_THRESHOLD_FAST,
    CAPTURE_TIME_THRESHOLD_NORMAL,
    PNG_COMPRESSION_LEVEL,
    JPEG_QUALITY,
    PREALLOCATE_BUFFERS,
    BUFFER_POOL_SIZE,
    SKIP_IDENTICAL_FRAMES,
    FRAME_SIMILARITY_THRESHOLD,
    ENABLE_PERFORMANCE_LOGGING,
    LOG_SLOW_CAPTURES,
    PERFORMANCE_SAMPLE_RATE,
)


class FastCapture:
    """고성능 이미지 캡쳐 클래스"""

    def __init__(self, width: int = 256, height: int = 192):
        self.width = width
        self.height = height

        # 성능 모니터링
        self.capture_times = deque(maxlen=100)
        self.current_mode = "normal"
        self.total_captures = 0
        self.skipped_frames = 0

        # 버퍼 속성 초기화
        self.screen_data_buffer: Optional[np.ndarray] = None
        self.rgb_buffer: Optional[np.ndarray] = None
        self.palette_rgb_cache: Optional[np.ndarray] = None

        # 메모리 최적화 - 사전 할당된 버퍼들
        if PREALLOCATE_BUFFERS:
            self._initialize_buffers()

        # 프레임 중복 검사용
        self.last_frame_hash: Optional[str] = None
        self.identical_frame_count = 0

        # 압축 버퍼 (재사용)
        self.compression_buffer = io.BytesIO()

    def _initialize_buffers(self):
        """성능 향상을 위한 버퍼 사전 할당"""
        # NumPy 배열 풀
        self.screen_data_buffer = np.zeros((self.height, self.width), dtype=np.int32)
        self.rgb_buffer = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # 팔레트 변환 테이블 (한 번만 계산)
        self.palette_rgb_cache = None

    def update_palette_cache(self, palette_hex: List[int]):
        """팔레트 RGB 변환 테이블 캐시 업데이트"""
        if self.palette_rgb_cache is None or len(palette_hex) != len(
            self.palette_rgb_cache
        ):
            self.palette_rgb_cache = np.array(
                [((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF) for c in palette_hex],
                dtype=np.uint8,
            )

    def capture_optimized(
        self, px, palette_hex: List[int], use_compression: str = "png"
    ) -> Optional[Tuple[str, dict]]:
        """
        최적화된 화면 캡쳐

        Args:
            px: Pyxel 모듈
            palette_hex: 색상 팔레트
            use_compression: 압축 형식 ("png", "jpeg", "webp")

        Returns:
            (base64_image, performance_stats) 또는 None
        """
        start_time = time.perf_counter()

        try:
            # 1. 화면 데이터 획득 (최적화된 방식)
            screen_data = self._get_screen_data_fast(px)
            if screen_data is None:
                return None

            # 2. 프레임 중복 검사 (옵션)
            if SKIP_IDENTICAL_FRAMES and self._is_duplicate_frame(screen_data):
                self.skipped_frames += 1
                return None

            # 3. 팔레트 캐시 업데이트
            self.update_palette_cache(palette_hex)

            # 4. RGB 변환 (벡터화)
            rgb_array = self._convert_to_rgb_vectorized(screen_data)

            # 5. 이미지 압축
            base64_image = self._compress_image_fast(rgb_array, use_compression)

            # 6. 성능 통계 업데이트
            capture_time = (time.perf_counter() - start_time) * 1000  # ms
            self._update_performance_stats(capture_time)

            stats = {
                "capture_time_ms": capture_time,
                "mode": self.current_mode,
                "skipped_frames": self.skipped_frames,
                "total_captures": self.total_captures,
            }

            return base64_image, stats

        except Exception as e:
            if ENABLE_PERFORMANCE_LOGGING:
                print(f"⚠️ 캡쳐 오류: {e}")
            return None

    def _get_screen_data_fast(self, px) -> Optional[np.ndarray]:
        """최적화된 화면 데이터 획득"""
        try:
            screen_data_raw = px.screen.data

            # 웹 환경 처리
            if hasattr(screen_data_raw, "to_py"):
                # PyScript/Pyodide 환경
                screen_data_flat = screen_data_raw.to_py()
                if PREALLOCATE_BUFFERS:
                    # 사전 할당된 버퍼 재사용
                    flat_array = np.array(screen_data_flat, dtype=np.int32)
                    return flat_array.reshape(self.height, self.width)
                else:
                    return np.array(screen_data_flat, dtype=np.int32).reshape(
                        self.height, self.width
                    )

            elif hasattr(screen_data_raw, "__iter__"):
                # 리스트/배열인 경우
                return np.array(list(screen_data_raw), dtype=np.int32).reshape(
                    self.height, self.width
                )
            else:
                # 직접 변환
                screen_data = np.asarray(screen_data_raw, dtype=np.int32)
                if screen_data.shape != (self.height, self.width):
                    screen_data = screen_data.reshape(self.height, self.width)
                return screen_data

        except Exception as e:
            if ENABLE_PERFORMANCE_LOGGING:
                print(f"⚠️ 화면 데이터 획득 실패: {e}")
            return None

    def _convert_to_rgb_vectorized(self, screen_data: np.ndarray) -> np.ndarray:
        """벡터화된 RGB 변환"""
        if (
            PREALLOCATE_BUFFERS
            and hasattr(self, "rgb_buffer")
            and self.rgb_buffer is not None
            and self.palette_rgb_cache is not None
        ):
            # 사전 할당된 버퍼 재사용
            np.take(self.palette_rgb_cache, screen_data, axis=0, out=self.rgb_buffer)
            return self.rgb_buffer.copy()
        else:
            # 일반 변환
            if self.palette_rgb_cache is not None:
                return self.palette_rgb_cache[screen_data]
            else:
                return np.zeros((self.height, self.width, 3), dtype=np.uint8)

    def _compress_image_fast(self, rgb_array: np.ndarray, format: str = "png") -> str:
        """고속 이미지 압축"""
        if not HAS_PIL:
            return ""

        try:
            # PIL 이미지 생성
            pil_image = PILImage.fromarray(rgb_array, "RGB")

            # 압축 버퍼 재사용
            self.compression_buffer.seek(0)
            self.compression_buffer.truncate(0)

            if format.lower() == "jpeg":
                pil_image.save(
                    self.compression_buffer,
                    format="JPEG",
                    quality=JPEG_QUALITY,
                    optimize=False,
                )
            elif format.lower() == "webp" and HAS_CV2:
                # WebP는 더 빠른 압축 제공
                pil_image.save(
                    self.compression_buffer,
                    format="WEBP",
                    quality=JPEG_QUALITY,
                    method=0,
                )  # 빠른 압축
            else:
                # PNG (기본값)
                pil_image.save(
                    self.compression_buffer,
                    format="PNG",
                    compress_level=PNG_COMPRESSION_LEVEL,
                    optimize=False,
                )

            # Base64 인코딩
            image_bytes = self.compression_buffer.getvalue()
            return base64.b64encode(image_bytes).decode("utf-8")

        except Exception as e:
            if ENABLE_PERFORMANCE_LOGGING:
                print(f"⚠️ 이미지 압축 실패: {e}")
            return ""

    def _is_duplicate_frame(self, screen_data: np.ndarray) -> bool:
        """프레임 중복 검사"""
        # 빠른 해시 기반 중복 검사
        frame_hash = hashlib.md5(screen_data.tobytes()).hexdigest()

        if self.last_frame_hash == frame_hash:
            self.identical_frame_count += 1
            return True

        self.last_frame_hash = frame_hash
        self.identical_frame_count = 0
        return False

    def _update_performance_stats(self, capture_time_ms: float):
        """성능 통계 업데이트 및 적응형 모드 조정"""
        self.capture_times.append(capture_time_ms)
        self.total_captures += 1

        # 로깅 (샘플링)
        if ENABLE_PERFORMANCE_LOGGING and np.random.random() < PERFORMANCE_SAMPLE_RATE:
            print(f"📸 캡쳐 시간: {capture_time_ms:.2f}ms (모드: {self.current_mode})")

        # 느린 캡쳐 경고
        if LOG_SLOW_CAPTURES and capture_time_ms > 20.0:
            print(f"⚠️ 느린 캡쳐 감지: {capture_time_ms:.2f}ms")

        # 적응형 모드 조정 (최근 10회 평균 기준)
        if len(self.capture_times) >= 10:
            avg_time = np.mean(list(self.capture_times)[-10:])

            if avg_time <= CAPTURE_TIME_THRESHOLD_FAST:
                self.current_mode = "fast"
            elif avg_time <= CAPTURE_TIME_THRESHOLD_NORMAL:
                self.current_mode = "normal"
            else:
                self.current_mode = "slow"

    def get_optimal_capture_interval(self) -> int:
        """현재 성능에 최적화된 캡쳐 간격 반환"""
        if self.current_mode == "fast":
            return CAPTURE_INTERVAL_FAST
        elif self.current_mode == "normal":
            return CAPTURE_INTERVAL_NORMAL
        else:
            return CAPTURE_INTERVAL_SLOW

    def get_performance_report(self) -> dict:
        """성능 리포트 생성"""
        if not self.capture_times:
            return {}

        times = list(self.capture_times)
        return {
            "total_captures": self.total_captures,
            "skipped_frames": self.skipped_frames,
            "current_mode": self.current_mode,
            "avg_capture_time_ms": np.mean(times),
            "min_capture_time_ms": np.min(times),
            "max_capture_time_ms": np.max(times),
            "capture_efficiency": (
                1 - self.skipped_frames / max(self.total_captures, 1)
            )
            * 100,
        }


# 전역 인스턴스 (선택적 사용)
_global_fast_capture = None


def get_fast_capture(width: int = 256, height: int = 192) -> FastCapture:
    """전역 FastCapture 인스턴스 획득"""
    global _global_fast_capture
    if _global_fast_capture is None:
        _global_fast_capture = FastCapture(width, height)
    return _global_fast_capture


def capture_frame_optimized(
    px, palette_hex: List[int], format: str = "png"
) -> Optional[Tuple[str, dict]]:
    """빠른 프레임 캡쳐 (전역 함수)"""
    fast_capture = get_fast_capture()
    return fast_capture.capture_optimized(px, palette_hex, format)
