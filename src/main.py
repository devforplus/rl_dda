import pyxel as px
import sys
import platform
import traceback
import time  # For timestamping (optional)
import json
import os
from typing import Optional

# 환경 변수 설정 로드 (가장 먼저)
try:
    from config.env_config import (
        ENABLE_FAST_CAPTURE,
        CAPTURE_INTERVAL as ENV_CAPTURE_INTERVAL,
        ENABLE_PERFORMANCE_LOGGING,
        AUTO_COLLECT_DATA,
        MAX_COLLECTED_FRAMES,
        DEBUG_MODE,
        FORCE_WEB_MODE,
        ENABLE_AI_AGENT,
        GAME_WIDTH as ENV_GAME_WIDTH,
        GAME_HEIGHT as ENV_GAME_HEIGHT,
        GAME_FPS as ENV_GAME_FPS,
        DISPLAY_SCALE as ENV_DISPLAY_SCALE,
    )

    print("✅ 환경 변수 설정 로드됨")
except ImportError as e:
    if "DEBUG_MODE" not in locals():
        DEBUG_MODE = False
    if DEBUG_MODE:
        print(f"⚠️  환경 변수 설정 로드 실패, 기본값 사용: {e}")
    # 기본값 설정
    ENABLE_FAST_CAPTURE = True
    ENV_CAPTURE_INTERVAL = 5
    ENABLE_PERFORMANCE_LOGGING = True
    AUTO_COLLECT_DATA = False
    MAX_COLLECTED_FRAMES = 1000
    DEBUG_MODE = False
    FORCE_WEB_MODE = False
    ENABLE_AI_AGENT = False
    ENV_GAME_WIDTH = 256
    ENV_GAME_HEIGHT = 192
    ENV_GAME_FPS = 60
    ENV_DISPLAY_SCALE = 3

# 웹 환경 감지 (환경 변수로 강제 설정 가능)
IS_WEB = FORCE_WEB_MODE or platform.system() == "Emscripten"
if IS_WEB:
    try:
        import js
    except ImportError:
        if DEBUG_MODE:
            print("⚠️  js 모듈을 임포트할 수 없습니다 (웹 환경이 아닐 수 있음)")

# Pillow, io, base64, numpy를 공통으로 import 시도
try:
    from PIL import Image as PILImage
    import io
    import base64

    HAS_PERFORMANCE_LIBS = True
except ImportError as e:
    PILImage = None
    io = None
    base64 = None
    HAS_PERFORMANCE_LIBS = False

# numpy는 별도로 처리 (웹 환경에서 문제가 될 수 있음)
try:
    import numpy
    import numpy as np
except ImportError as e:
    numpy = None
except Exception as e:
    numpy = None

from game import Game
import input as input_module
from config.app.constants import (
    APP_WIDTH,
    APP_HEIGHT,
    APP_NAME,
    APP_DISPLAY_SCALE,
    APP_CAPTURE_SCALE,
    APP_FPS,
)
from config.paths import ASSETS_DIR
from config.colors import PALETTE
from monospace_bitmap_font import MonospaceBitmapFont

# 고성능 캡쳐를 위한 FastCapture import
try:
    from utils.fast_capture import FastCapture

    FAST_CAPTURE_AVAILABLE = True
    if DEBUG_MODE:
        print("✅ FastCapture 모듈 import 성공")
except ImportError as e:
    print(f"⚠️  FastCapture을 임포트할 수 없습니다: {e}")
    FAST_CAPTURE_AVAILABLE = False


class App:
    def __init__(self, agent=None) -> None:
        try:
            self.agent = agent
            # Data collection variables
            self.collecting_data = AUTO_COLLECT_DATA  # 환경 변수로 설정
            self.collected_data = []
            self.capture_interval = ENV_CAPTURE_INTERVAL  # 환경 변수로 설정
            self.frames_since_last_capture = 0

            # FastCapture 초기화 전 조건 확인
            if DEBUG_MODE:
                print(f"🔍 FastCapture 조건 확인:")
                print(f"  - FAST_CAPTURE_AVAILABLE: {FAST_CAPTURE_AVAILABLE}")
                print(f"  - HAS_PERFORMANCE_LIBS: {HAS_PERFORMANCE_LIBS}")
                print(f"  - ENABLE_FAST_CAPTURE: {ENABLE_FAST_CAPTURE}")
                print(f"  - numpy 가용성: {numpy is not None}")

            # 성능 최적화 - FastCapture 초기화
            self.fast_capture: Optional[FastCapture] = None
            if (
                FAST_CAPTURE_AVAILABLE
                and HAS_PERFORMANCE_LIBS
                and ENABLE_FAST_CAPTURE
                and numpy is not None
            ):
                try:
                    self.fast_capture = FastCapture(ENV_GAME_WIDTH, ENV_GAME_HEIGHT)
                    self.use_fast_capture = True
                    if ENABLE_PERFORMANCE_LOGGING:
                        print("🚀 고성능 캡쳐 모드 활성화")
                except Exception as e:
                    print(f"❌ FastCapture 초기화 실패: {e}")
                    self.use_fast_capture = False
                    if ENABLE_PERFORMANCE_LOGGING:
                        print("📸 일반 캡쳐 모드로 fallback")
            else:
                self.use_fast_capture = False
                if ENABLE_PERFORMANCE_LOGGING:
                    reasons = []
                    if not FAST_CAPTURE_AVAILABLE:
                        reasons.append("FastCapture 모듈 없음")
                    if not HAS_PERFORMANCE_LIBS:
                        reasons.append("PIL/io/base64 라이브러리 없음")
                    if not ENABLE_FAST_CAPTURE:
                        reasons.append("환경 변수로 비활성화")
                    if numpy is None:
                        reasons.append("NumPy 없음")
                    print(f"📸 일반 캡쳐 모드 사용 (이유: {', '.join(reasons)})")

            # 에이전트가 있거나 환경 변수로 설정된 경우 데이터 수집 자동 활성화
            if self.agent is not None or ENABLE_AI_AGENT:
                self.collecting_data = True

            if IS_WEB:
                px.init(
                    ENV_GAME_WIDTH,
                    ENV_GAME_HEIGHT,
                    title=APP_NAME,
                    fps=ENV_GAME_FPS,
                    display_scale=ENV_DISPLAY_SCALE,
                )
            else:
                px.init(
                    ENV_GAME_WIDTH,
                    ENV_GAME_HEIGHT,
                    title=APP_NAME,
                    fps=ENV_GAME_FPS,
                    display_scale=ENV_DISPLAY_SCALE,
                    capture_scale=APP_CAPTURE_SCALE,
                )

            px.colors.from_list(PALETTE)

            asset_path_gfx = "assets/gfx.png"
            asset_path_sounds = "assets/sounds.pyxres"

            if IS_WEB:
                asset_path_gfx = "assets/gfx.png"
                asset_path_sounds = "assets/sounds.pyxres"
            elif ASSETS_DIR:
                asset_path_gfx = str(ASSETS_DIR / "gfx.png")
                asset_path_sounds = str(ASSETS_DIR / "sounds.pyxres")

            px.images[0].load(0, 0, asset_path_gfx)
            px.load(
                asset_path_sounds,
                excl_images=True,
                excl_tilemaps=True,
                excl_musics=True,
            )

            self.main_font = MonospaceBitmapFont()
            self.input = input_module.Input()
            self.game = Game(self)

            px.run(self.update, self.draw)
        except Exception as e:
            error_message = f"Error in App.__init__: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            if IS_WEB and "js" in globals():
                js.console.error(error_message)
            print(error_message, file=sys.stderr)
            raise

    def toggle_data_collection(self):
        """데이터 수집 상태를 토글합니다."""
        # 에이전트 사용 중일 때는 데이터 수집 비활성화 방지 (AI 학습용 데이터 보호)
        if self.agent is not None and self.collecting_data:
            return

        self.collecting_data = not self.collecting_data
        if self.collecting_data:
            self.collected_data.clear()
        else:
            if IS_WEB and self.collected_data:
                pass

    def apply_agent_action(self, action_id):
        self.input.left_pressed = False
        self.input.right_pressed = False
        self.input.up_pressed = False
        self.input.down_pressed = False
        self.input.fire_pressed = False

        if action_id == 0:
            self.input.left_pressed = True
            self.input.up_pressed = True
        elif action_id == 1:
            self.input.up_pressed = True
        elif action_id == 2:
            self.input.right_pressed = True
            self.input.up_pressed = True
        elif action_id == 3:
            self.input.left_pressed = True
        elif action_id == 4:
            self.input.right_pressed = True
        elif action_id == 5:
            self.input.left_pressed = True
            self.input.down_pressed = True
        elif action_id == 6:
            self.input.down_pressed = True
        elif action_id == 7:
            self.input.right_pressed = True
            self.input.down_pressed = True
        elif action_id == 8:
            self.input.fire_pressed = True

    def update(self):
        try:
            if self.agent:
                agent_action = self.agent.select_action(state=None)
                self.apply_agent_action(agent_action)

            self.input.update()

            # 데이터 수집 토글 (C 키)
            if self.input.has_tapped(input_module.COLLECT_DATA):
                self.toggle_data_collection()  # App의 토글 메소드 호출

            self.game.update()

            # 데이터 수집 로직
            if self.collecting_data:
                self.frames_since_last_capture += 1
                if self.frames_since_last_capture >= self.capture_interval:
                    self.frames_since_last_capture = 0
                    collected_info = self._collect_current_frame_data()
                    if collected_info:
                        frame_data, pil_image, yolo_data_rows = collected_info
                        if (
                            frame_data
                            and isinstance(frame_data, dict)
                            and frame_data.get("image_png_base64")
                        ):
                            self.collected_data.append(frame_data)

                            # 데이터 수집 완료 로그 출력 (플레이어 정보는 참고용으로만 출력)
                            frame_data_log = {
                                "type": "event",
                                "event": "frame_collected",
                                "timestamp": time.time(),
                                "data": {
                                    "image_size_chars": len(
                                        str(frame_data.get("image_png_base64", ""))
                                    ),
                                    "yolo_objects_count": len(
                                        frame_data.get("yolo_labels", [])
                                    )
                                    - 1,  # -1 for header
                                },
                            }

                            # 플레이어 정보 추가 (콘솔 출력 전용)
                            if hasattr(self.game, "game_vars") and self.game.game_vars:
                                lives = getattr(self.game.game_vars, "lives", "N/A")
                                score = getattr(self.game.game_vars, "score", "N/A")
                                stage = getattr(self.game.game_vars, "stage_num", "N/A")

                                # frame_data_log["data"]["player"]가 dict인지 확인
                                if isinstance(frame_data_log["data"], dict):
                                    frame_data_log["data"]["player"] = {
                                        "lives": lives,
                                        "score": score,
                                        "stage": str(stage),
                                    }

                                    # 플레이어 체력 정보 추가 (콘솔 출력 전용)
                                    if (
                                        hasattr(self.game, "state")
                                        and self.game.state
                                        and hasattr(self.game.state, "player")
                                        and self.game.state.player
                                    ):
                                        current_hp = getattr(
                                            self.game.state.player, "current_hp", "N/A"
                                        )
                                        max_hp = getattr(
                                            self.game.state.player, "max_hp", "N/A"
                                        )
                                        frame_data_log["data"]["player"]["hp"] = {
                                            "current": current_hp,
                                            "max": max_hp,
                                        }

                            print(json.dumps(frame_data_log))

            if not IS_WEB and self.input.has_tapped(input_module.BUTTON_2):
                print("Local save triggered (not implemented).")
            elif IS_WEB and px.btnp(px.KEY_S):
                self.download_collected_data_web()
        except Exception as e:
            error_message = f"Error in App.update: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            if IS_WEB and "js" in globals():
                js.console.error(error_message)
            print(error_message, file=sys.stderr)

    def draw(self):
        try:
            self.game.draw()

            # 데이터 수집 상태 표시
            self._draw_status_indicators()
        except Exception as e:
            error_message = (
                f"Error in App.draw: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            )
            if IS_WEB and "js" in globals():
                js.console.error(error_message)
            print(error_message, file=sys.stderr)

    def _draw_status_indicators(self):
        """데이터 수집 상태를 화면에 표시"""
        y_offset = 5

        # 에이전트 상태 표시 (우선순위 최고)
        if self.agent is not None:
            px.text(5, y_offset, "AGENT: ACTIVE", 12)  # 파란색
            y_offset += 8

        # 데이터 수집 상태 표시
        if self.collecting_data:
            status_text = "DATA: AUTO" if self.agent is not None else "DATA: ON"
            px.text(5, y_offset, status_text, 11)  # 밝은 녹색
        else:
            px.text(5, y_offset, "DATA: OFF", 5)  # 회색

        # 수집된 프레임 수 표시
        if self.collected_data:
            y_offset += 8
            px.text(5, y_offset, f"FRAMES: {len(self.collected_data)}", 7)  # 흰색

        # 키 도움말 표시
        y_offset += 8
        if self.agent is not None:
            px.text(5, y_offset, "AUTO MODE", 6)  # 진한 회색
        else:
            px.text(5, y_offset, "C:Data", 6)  # 진한 회색

    def _collect_current_frame_data(self):
        """
        현재 프레임의 이미지 및 게임 오브젝트 정보를 수집합니다.
        YOLO 라벨 생성을 위한 데이터를 생성합니다.

        Returns:
            tuple: (frame_data, pil_image, yolo_data_rows) 또는 None
        """
        try:
            start_time = time.time()

            # 성능 최적화된 캡쳐 사용
            if self.use_fast_capture and self.fast_capture:
                try:
                    # FastCapture 사용 - palette_hex 정의
                    palette_hex = [
                        0x000000,
                        0x2D1B69,
                        0xC53031,
                        0x9B59B6,
                        0x2E8B57,
                        0x8B4513,
                        0xFF7F00,
                        0xD3D3D3,
                        0x696969,
                        0x6495ED,
                        0x4169E1,
                        0x00FF00,
                        0xFF00FF,
                        0xA52A2A,
                        0xFFFF00,
                        0xFFFFFF,
                    ]
                    result = self.fast_capture.capture_optimized(px, palette_hex)
                    if result is None:
                        raise Exception("FastCapture 실패")
                    image_data_b64, stats = result
                    capture_method = "FastCapture"
                except Exception as e:
                    print(f"⚠️  FastCapture 실패, 기본 방법 사용: {e}")
                    image_data_b64 = self._capture_frame_legacy()
                    capture_method = "Legacy"
            else:
                image_data_b64 = self._capture_frame_legacy()
                capture_method = "Legacy"

            # 이미지가 성공적으로 캡쳐되었는지 확인
            if image_data_b64 is None:
                print("❌ 이미지 캡쳐 실패")
                return None

            # YOLO 데이터 생성 (기존 로직 유지)
            yolo_data = self._generate_yolo_data()

            # 프레임 데이터 생성 (로컬 수집용)
            frame_data = {
                "timestamp": time.time(),
                "image_png_base64": image_data_b64,
                "yolo_labels": ["header"]
                + [f"{obj[0]} {obj[1].x} {obj[1].y}" for obj in yolo_data],
                "game_state": {
                    "score": getattr(self.game.game_vars, "score", 0)
                    if hasattr(self.game, "game_vars")
                    else 0,
                    "stage": getattr(self.game.game_vars, "stage_num", 1)
                    if hasattr(self.game, "game_vars")
                    else 1,
                },
            }

            # PIL 이미지 생성 (호환성을 위해)
            pil_image = None
            if PILImage and image_data_b64 and io and base64:
                try:
                    img_data = base64.b64decode(image_data_b64)
                    pil_image = PILImage.open(io.BytesIO(img_data))
                except Exception as e:
                    print(f"⚠️  PIL 이미지 생성 실패: {e}")

            # YOLO 데이터 행 형태로 변환
            yolo_data_rows = frame_data["yolo_labels"]

            # 성능 통계 출력 (FastCapture의 performance stats 제거)
            capture_time = time.time() - start_time
            if (
                ENABLE_PERFORMANCE_LOGGING and capture_time > 0.1
            ):  # 100ms 이상일 때만 출력
                print(f"📊 캡쳐 성능: {capture_time:.3f}s, 메서드: {capture_method}")

            return (frame_data, pil_image, yolo_data_rows)

        except Exception as e:
            print(f"❌ 프레임 데이터 수집 중 오류: {e}")
            traceback.print_exc()
            return None

    def _capture_frame_legacy(self):
        """기존 캡쳐 방법 (fallback) - 픽셀별 읽기만 사용"""
        try:
            if not PILImage or not io or not base64:
                print("❌ 필요한 라이브러리가 없습니다 (PIL, io, base64)")
                return None

            # RGB 이미지 생성
            image = PILImage.new("RGB", (APP_WIDTH, APP_HEIGHT))

            # 팔레트 정의
            palette = [
                (0, 0, 0),
                (45, 27, 105),
                (197, 48, 49),
                (155, 89, 182),
                (46, 139, 87),
                (139, 69, 19),
                (255, 127, 0),
                (211, 211, 211),
                (105, 105, 105),
                (100, 149, 237),
                (65, 105, 225),
                (0, 255, 0),
                (255, 0, 255),
                (165, 42, 42),
                (255, 255, 0),
                (255, 255, 255),
            ]

            # 픽셀별로 읽기 (pyxel pget 사용)
            for y in range(APP_HEIGHT):
                for x in range(APP_WIDTH):
                    color_index = px.pget(x, y)
                    if 0 <= color_index < len(palette):
                        image.putpixel((x, y), palette[color_index])

            # base64 인코딩
            img_buffer = io.BytesIO()
            image.save(img_buffer, format="PNG")
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            return img_str

        except Exception as e:
            print(f"❌ Legacy 캡쳐 실패: {e}")
            return None

    def _capture_frame_pixel_by_pixel(self):
        """픽셀별 캡쳐 방법 - legacy와 동일"""
        return self._capture_frame_legacy()

    def _generate_yolo_data(self):
        """YOLO 라벨 데이터 생성"""
        yolo_objects = []

        # 게임 상태에서 오브젝트들 가져오기
        if hasattr(self.game, "state") and self.game.state:
            # 플레이어 (클래스 0)
            if hasattr(self.game.state, "player") and self.game.state.player:
                player = self.game.state.player
                yolo_objects.append(("player", player))

            # 적들 (클래스 1)
            if hasattr(self.game.state, "enemies"):
                for enemy in self.game.state.enemies:
                    yolo_objects.append(("enemy", enemy))

            # 파워업들 (클래스 2)
            if hasattr(self.game.state, "powerups"):
                for powerup in self.game.state.powerups:
                    yolo_objects.append(("powerup", powerup))

            # 폭발들 (클래스 3)
            if hasattr(self.game.state, "explosions"):
                for explosion in self.game.state.explosions:
                    yolo_objects.append(("explosion", explosion))

        return yolo_objects

    def download_collected_data_web(self):
        if not IS_WEB or not self.collected_data:
            print("No data to download or not in web environment.", file=sys.stderr)
            return

        try:
            file_name = "collected_rl_dataset.json"
            mime_type = "application/json"

            # self.collected_data는 이미 JSON으로 직렬화 가능한 형태임
            # (image_data가 tolist()로 변환되었음)
            json_data_string = json.dumps(self.collected_data)

            # JavaScript에서 백슬래시와 따옴표 문제를 피하기 위해
            # JSON 문자열을 안전하게 이스케이프 처리합니다.
            # 여기서는 Python의 json.dumps가 생성한 문자열을 그대로 사용하고,
            # JavaScript 템플릿 리터럴 내에 직접 삽입하는 대신 변수로 전달하는 방식을 고려할 수 있으나,
            # Pyodide의 js.eval 한계상 직접 문자열 구성이 일반적입니다.
            # 가장 큰 문제는 json_data_string 내의 따옴표입니다.
            # 간단한 방법은 json_data_string 자체를 JavaScript 변수로 할당하는 것입니다.

            # JSON 문자열 내의 백슬래시와 작은따옴표를 이스케이프 처리합니다.
            escaped_json_data = json_data_string.replace("\\", "\\\\").replace(
                "'", "\\'"
            )

            js_code = f"""
            const jsonData = JSON.parse('{escaped_json_data}');
            const blob = new Blob([JSON.stringify(jsonData, null, 2)], {{type: '{mime_type}'}});
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = '{file_name}';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);
            """
            js.eval(js_code)
            print(f"Starting download of '{file_name}'...")
            # 다운로드 후 데이터 클리어 여부는 정책에 따라 결정 (현재는 유지)
            # self.collected_data.clear()
        except Exception as e:
            print(f"Error during web data download: {e}", file=sys.stderr)
            traceback.print_exc()
