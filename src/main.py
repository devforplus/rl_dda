print("[MAIN_PY_DEBUG] main.py TOP LEVEL EXECUTION STARTED")
import pyxel as px
import sys
import platform
import traceback
import time  # For timestamping (optional)
import json
import os

# 웹 환경에서만 Pillow, io, base64, numpy를 import 시도 -> 전역으로 변경
IS_WEB = platform.system() == "Emscripten"
if IS_WEB:
    import js
    # json은 이미 위에서 import

# Pillow, io, base64, numpy를 공통으로 import 시도
try:
    from PIL import Image as PILImage
    import io
    import base64
    import numpy
except ImportError as e:
    print(
        f"[APP_ERROR] Failed to import libraries for image processing: {e}. Data collection might fail."
    )
    # Pillow 등이 없으면 이미지 처리가 불가능하므로, 이후 로직에서 이를 고려해야 함.
    PILImage = None
    io = None
    base64 = None
    numpy = None

from game import Game
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
from config.game_config import CLASS_MAP  # YOLO 라벨링용
from monospace_bitmap_font import MonospaceBitmapFont
import input as input_module  # 수정된 방식

# 서버 업로드 기능 import (웹/데스크톱 모두 지원)
try:
    from server_client import GameDataServerClient

    SERVER_CLIENT_AVAILABLE = True
    print(
        f"[APP_INFO] Server client available in {'web' if IS_WEB else 'desktop'} environment"
    )
except ImportError as e:
    print(f"[APP_WARNING] Server client not available: {e}")
    SERVER_CLIENT_AVAILABLE = False

print("[MAIN_PY_DEBUG] App class definition START")


class App:
    def __init__(self, agent=None) -> None:
        print("[MAIN_PY_DEBUG] App.__init__ VERY START")
        try:
            self.agent = agent
            # Data collection variables
            self.collecting_data = (
                False  # 데이터 수집 활성화 여부 (C키로 토글 가능하도록 설정)
            )
            self.collected_data = []
            self.capture_interval = 1  # 캡처 간격 (프레임)
            self.frames_since_last_capture = 0

            # 서버 업로드 관련 변수 (웹/데스크톱 모두 지원)
            self.server_upload_enabled = False
            self.server_client = None
            if SERVER_CLIENT_AVAILABLE:
                # 환경 변수나 설정 파일에서 서버 URL을 가져올 수 있음
                # 웹/데스크톱 모두 동일한 서버 주소 사용
                default_server_url = "http://127.0.0.1:8787"  # 통일된 서버 주소
                server_url = os.getenv("GAME_SERVER_URL", default_server_url)
                try:
                    self.server_client = GameDataServerClient(server_url)
                    if self.server_client.check_server_status():
                        self.server_upload_enabled = True
                        print(f"[APP_INFO] 서버 업로드 활성화됨: {server_url}")
                    else:
                        print(f"[APP_WARNING] 서버에 연결할 수 없음: {server_url}")
                except Exception as e:
                    print(f"[APP_WARNING] 서버 클라이언트 초기화 실패: {e}")

            if IS_WEB:
                px.init(
                    APP_WIDTH,
                    APP_HEIGHT,
                    title=APP_NAME,
                    fps=APP_FPS,
                    display_scale=APP_DISPLAY_SCALE,
                )
            else:
                px.init(
                    APP_WIDTH,
                    APP_HEIGHT,
                    title=APP_NAME,
                    fps=APP_FPS,
                    display_scale=APP_DISPLAY_SCALE,
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
        self.collecting_data = not self.collecting_data
        if self.collecting_data:
            print("[APP_DEBUG] Data collection STARTED (toggled from game state).")
            self.collected_data.clear()
        else:
            print("[APP_DEBUG] Data collection STOPPED (toggled from game state).")
            if IS_WEB and self.collected_data:
                print(
                    f"[APP_DEBUG] {len(self.collected_data)} frames collected. Press 'S' to download."
                )

    def toggle_server_upload(self):
        """서버 업로드 상태를 토글합니다 (웹/데스크톱 모두 지원)."""
        if not SERVER_CLIENT_AVAILABLE:
            print("[APP_WARNING] 서버 클라이언트를 사용할 수 없습니다.")
            return

        if not self.server_client:
            print("[APP_WARNING] 서버 클라이언트가 초기화되지 않았습니다.")
            return

        self.server_upload_enabled = not self.server_upload_enabled
        if self.server_upload_enabled:
            # 서버 연결 재확인
            if self.server_client.check_server_status():
                print("[APP_INFO] 서버 업로드 활성화됨")
            else:
                print("[APP_WARNING] 서버에 연결할 수 없어 업로드를 비활성화합니다.")
                self.server_upload_enabled = False
        else:
            print("[APP_INFO] 서버 업로드 비활성화됨")

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

            # 서버 업로드 토글 (U 키, 웹/데스크톱 모두 지원)
            if px.btnp(px.KEY_U):
                self.toggle_server_upload()

            self.game.update()

            # 데이터 수집 로직
            if self.collecting_data:
                self.frames_since_last_capture += 1
                if self.frames_since_last_capture >= self.capture_interval:
                    self.frames_since_last_capture = 0
                    self._collect_current_frame_data()

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

            # 데이터 수집 및 서버 업로드 상태 표시
            self._draw_status_indicators()
        except Exception as e:
            error_message = (
                f"Error in App.draw: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            )
            if IS_WEB and "js" in globals():
                js.console.error(error_message)
            print(error_message, file=sys.stderr)

    def _draw_status_indicators(self):
        """데이터 수집 및 서버 업로드 상태를 화면에 표시"""
        y_offset = 5

        # 데이터 수집 상태 표시
        if self.collecting_data:
            px.text(5, y_offset, "DATA: ON", 11)  # 밝은 녹색
        else:
            px.text(5, y_offset, "DATA: OFF", 5)  # 회색

        # 서버 업로드 상태 표시 (웹/데스크톱 모두 지원)
        if SERVER_CLIENT_AVAILABLE:
            y_offset += 8
            if self.server_upload_enabled:
                px.text(5, y_offset, "SERVER: ON", 11)  # 밝은 녹색
            else:
                px.text(5, y_offset, "SERVER: OFF", 5)  # 회색

        # 수집된 프레임 수 표시
        if self.collected_data:
            y_offset += 8
            px.text(5, y_offset, f"FRAMES: {len(self.collected_data)}", 7)  # 흰색

    def _collect_current_frame_data(self):
        """현재 프레임의 이미지와 게임 객체 정보를 수집하여 YOLO 라벨을 생성합니다."""
        print("[APP_DEBUG] _collect_current_frame_data CALLED")

        # Pillow, io, base64는 공통 임포트 시도됨. numpy도 마찬가지.
        if not PILImage or not io or not base64:
            print(
                "[APP_ERROR] Core image processing libraries (Pillow, io, base64) not available. Cannot collect frame data."
            )
            if self.collecting_data:
                print(
                    "[APP_DEBUG] Data collection STOPPED due to missing core libraries."
                )
                self.collecting_data = False
            return

        if not hasattr(self.game, "state") or not self.game.state:
            print(
                "[APP_DEBUG] Game state not available. Skipping frame data collection."
            )
            return

        current_game_state = self.game.state
        image_payload = None
        image_shape_info = None
        pil_image = None

        try:
            width = px.width  # Pyxel의 전역 화면 너비 사용
            height = px.height  # Pyxel의 전역 화면 높이 사용
            image_shape_info = (height, width)

            # Optimized NumPy-based approach
            try:
                if not numpy:  # numpy가 성공적으로 임포트되었는지 확인
                    raise RuntimeError("NumPy not available for optimized capture.")
                if not PILImage:  # PILImage도 여기서 다시 한번 확인 (상단에서 이미 확인했지만, 명시적 방어)
                    raise RuntimeError(
                        "Pillow (PIL) not available for optimized capture."
                    )

                screen_data_raw = px.screen.data
                screen_data_np = None

                if IS_WEB:
                    if hasattr(
                        screen_data_raw, "to_py"
                    ):  # Pyodide/JS TypedArray (e.g., Uint8Array)
                        # Pyxel web: px.screen.data는 (width * height) 크기의 플랫 Uint8Array (색상 인덱스)
                        screen_data_flat_py = screen_data_raw.to_py()
                        screen_data_np = numpy.array(
                            screen_data_flat_py, dtype=numpy.int32
                        ).reshape(height, width)
                    else:
                        raise RuntimeError(
                            "Web environment: px.screen.data is not a JS object with to_py method or is not in the expected format."
                        )
                else:
                    # Desktop: px.screen.data는 (height, width) 형태의 NumPy 배열 (색상 인덱스)
                    screen_data_np = numpy.asarray(screen_data_raw, dtype=numpy.int32)

                if screen_data_np.shape != (height, width):
                    raise ValueError(
                        f"Screen data shape mismatch. Expected ({height},{width}), got {screen_data_np.shape}."
                    )

                palette_hex = (
                    px.colors.to_list()
                )  # 현재 활성화된 팔레트 (hex 값 리스트)

                max_index_on_screen = numpy.max(screen_data_np)
                current_palette_size = len(palette_hex)

                if max_index_on_screen >= current_palette_size:
                    # NumPy 배열 인덱싱 시 IndexError 발생 방지
                    raise ValueError(
                        f"Color index {max_index_on_screen} from screen data is out of bounds for current palette size {current_palette_size}."
                    )
                if numpy.min(screen_data_np) < 0:
                    raise ValueError("Negative color index found in screen data.")

                palette_rgb = numpy.array(
                    [
                        ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF)
                        for c in palette_hex
                    ],
                    dtype=numpy.uint8,
                )

                rgb_array = palette_rgb[
                    screen_data_np
                ]  # NumPy의 fancy indexing으로 RGB 값 매핑

                pil_image = PILImage.fromarray(rgb_array, "RGB")
                print("[APP_DEBUG] Frame captured using NumPy optimization.")

            except Exception as e_optimized:
                print(
                    f"[APP_DEBUG] NumPy optimization failed: {type(e_optimized).__name__} - {e_optimized}. Falling back to pixel-by-pixel method."
                )

                # Fallback to existing pixel-by-pixel method
                if not PILImage:  # PILImage가 폴백에 사용 가능한지 확인
                    print(
                        "[APP_ERROR] PILImage not available for fallback image capture."
                    )
                    return  # PILImage 없이는 진행 불가

                pil_image = PILImage.new("RGB", (width, height))
                current_palette_for_fallback = (
                    px.colors.to_list()
                )  # 폴백에서도 현재 팔레트 사용

                for y_coord in range(height):
                    for x_coord in range(width):
                        # px.pget()은 화면에서 직접 색상 인덱스를 가져옴 (웹/데스크톱 호환)
                        color_index = px.pget(x_coord, y_coord)

                        if 0 <= color_index < len(current_palette_for_fallback):
                            rgb_hex = current_palette_for_fallback[color_index]
                            r = (rgb_hex >> 16) & 0xFF
                            g = (rgb_hex >> 8) & 0xFF
                            b = rgb_hex & 0xFF
                            pil_image.putpixel((x_coord, y_coord), (r, g, b))
                        else:
                            # pget()이 팔레트 범위를 벗어난 인덱스를 반환하는 경우 (비정상적 상황)
                            print(
                                f"[APP_WARNING] Fallback: color_index {color_index} from pget() is out of bounds for palette size {len(current_palette_for_fallback)}. Using black pixel."
                            )
                            pil_image.putpixel(
                                (x_coord, y_coord), (0, 0, 0)
                            )  # 기본값 (검정색)

                print("[APP_DEBUG] Frame captured using pixel-by-pixel fallback.")

            # PIL 이미지가 성공적으로 생성되었는지 확인 후 처리
            if pil_image:
                buffered = io.BytesIO()
                pil_image.save(buffered, format="PNG")  # PNG는 무손실 압축
                image_payload = base64.b64encode(buffered.getvalue()).decode("utf-8")
                image_shape_info = (height, width, 3)  # RGB이므로 채널은 3
            else:
                print(
                    "[APP_ERROR] Failed to create PIL image using any method. Frame data not collected."
                )
                return

        except Exception as e:
            error_message = f"Error in _collect_current_frame_data: {type(e).__name__}: {e}\\n{traceback.format_exc()}"
            if IS_WEB and "js" in globals():
                js.console.error(error_message)
            print(error_message, file=sys.stderr)
            return  # 오류 발생 시 데이터 수집 중단 또는 해당 프레임 스킵

        # YOLO 라벨을 CSV 형식으로 수집
        csv_header = "entity_num x_center y_center width height"
        yolo_data_rows = []  # 실제 데이터만 저장
        print(f"[APP_DEBUG] CSV 헤더 설정: {csv_header}")

        object_lists_to_process = {
            "player": [current_game_state.player]
            if hasattr(current_game_state, "player") and current_game_state.player
            else [],
            "enemies": current_game_state.enemies
            if hasattr(current_game_state, "enemies")
            else [],
            "bosses": current_game_state.bosses
            if hasattr(current_game_state, "bosses")
            else [],
            "player_shots": current_game_state.player_shots
            if hasattr(current_game_state, "player_shots")
            else [],
            "enemy_shots": current_game_state.enemy_shots
            if hasattr(current_game_state, "enemy_shots")
            else [],
            "powerups": current_game_state.powerups
            if hasattr(current_game_state, "powerups")
            else [],
        }

        for list_name, obj_list in object_lists_to_process.items():
            if not obj_list:
                continue
            for obj in obj_list:
                if not obj or obj.remove:
                    continue
                class_name = obj.type.name.lower()
                class_id = CLASS_MAP.get(class_name)
                if class_id is None:
                    continue
                obj_x, obj_y, obj_w, obj_h = obj.x, obj.y, obj.w, obj.h
                x_center = obj_x + obj_w / 2
                y_center = obj_y + obj_h / 2
                x_center_norm = x_center / APP_WIDTH
                y_center_norm = y_center / APP_HEIGHT
                width_norm = obj_w / APP_WIDTH
                height_norm = obj_h / APP_HEIGHT
                # CSV 데이터 행 추가
                yolo_data_row = f"{class_id} {x_center_norm:.6f} {y_center_norm:.6f} {width_norm:.6f} {height_norm:.6f}"
                yolo_data_rows.append(yolo_data_row)

            # 헤더와 데이터를 결합하여 최종 CSV 형식 생성
            yolo_labels_csv = [csv_header] + yolo_data_rows
            print(
                f"[APP_DEBUG] 수집된 데이터 행 수: {len(yolo_data_rows)}, 총 CSV 라인 수 (헤더 포함): {len(yolo_labels_csv)}"
            )

            # 데이터 저장 (헤더는 항상 포함)
            if image_payload:
                frame_data = {
                    "timestamp": time.time(),
                    "image_original_shape": image_shape_info,
                    "image_png_base64": image_payload,
                    "yolo_labels": yolo_labels_csv,  # CSV 형식으로 저장 (헤더 + 데이터)
                }
                self.collected_data.append(frame_data)

                # 서버 업로드 (활성화된 경우)
                if self.server_upload_enabled and self.server_client:
                    self._upload_frame_to_server(pil_image, yolo_data_rows, frame_data)

    def _upload_frame_to_server(self, pil_image, yolo_data_rows, frame_data):
        """현재 프레임을 서버에 업로드"""
        try:
            # PIL 이미지를 numpy 배열로 변환
            if not numpy:
                print("[APP_WARNING] NumPy not available for server upload")
                return

            image_array = numpy.array(pil_image)

            # YOLO 라벨 내용 생성 (헤더 제외)
            label_content = "\n".join(yolo_data_rows)

            # 메타데이터 생성
            metadata = {
                "game_name": APP_NAME,
                "app_width": APP_WIDTH,
                "app_height": APP_HEIGHT,
                "frame_timestamp": frame_data["timestamp"],
                "detection_count": len(yolo_data_rows),
                "upload_source": "game_realtime",
            }

            # 게임 상태 정보 추가 (가능한 경우)
            if hasattr(self.game, "state") and self.game.state:
                game_state = self.game.state
                if hasattr(game_state, "score"):
                    metadata["game_score"] = game_state.score
                if hasattr(game_state, "level"):
                    metadata["game_level"] = game_state.level
                if hasattr(game_state, "lives"):
                    metadata["player_lives"] = game_state.lives

            # 서버에 업로드
            data_id = self.server_client.upload_game_data_from_memory(
                image_array, label_content, "game_frame", metadata
            )

            if data_id:
                print(f"[APP_INFO] 서버 업로드 성공: {data_id}")
            else:
                print("[APP_WARNING] 서버 업로드 실패")

        except Exception as e:
            print(f"[APP_ERROR] 서버 업로드 중 오류: {e}")

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
