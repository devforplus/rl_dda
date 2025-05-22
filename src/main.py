print("[MAIN_PY_DEBUG] main.py TOP LEVEL EXECUTION STARTED")
import pyxel as px
import sys
import platform
import traceback
import time # For timestamping (optional)
import json

# 웹 환경에서만 Pillow, io, base64, numpy를 import 시도
IS_WEB = platform.system() == "Emscripten"
if IS_WEB:
    import js
    # json은 이미 위에서 import
    try:
        from PIL import Image as PILImage
        import io
        import base64
        import numpy # numpy는 Pillow 내부 또는 다른 곳에서 필요할 수 있음
    except ImportError as e:
        print(f"[APP_ERROR] Failed to import libraries for image processing: {e}. Data collection might fail.")
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
from config.game_config import CLASS_MAP # YOLO 라벨링용
from monospace_bitmap_font import MonospaceBitmapFont
import input as input_module # 수정된 방식

print("[MAIN_PY_DEBUG] App class definition START")
class App:
    def __init__(self, agent=None) -> None:
        print("[MAIN_PY_DEBUG] App.__init__ VERY START")
        try:
            self.agent = agent
            # Data collection variables
            self.collecting_data = False # 데이터 수집 활성화 여부 (C키로 토글 가능하도록 설정)
            self.collected_data = []
            self.capture_interval = 10 # 캡처 간격 (프레임)
            self.frames_since_last_capture = 0
            
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
            if IS_WEB and 'js' in globals():
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
                print(f"[APP_DEBUG] {len(self.collected_data)} frames collected. Press 'S' to download.")

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
                self.toggle_data_collection() # App의 토글 메소드 호출

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
            if IS_WEB and 'js' in globals():
                js.console.error(error_message)
            print(error_message, file=sys.stderr)

    def draw(self):
        try:
            self.game.draw()
        except Exception as e:
            error_message = f"Error in App.draw: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            if IS_WEB and 'js' in globals():
                js.console.error(error_message)
            print(error_message, file=sys.stderr)

    def _collect_current_frame_data(self):
        """현재 프레임의 이미지와 게임 객체 정보를 수집하여 YOLO 라벨을 생성합니다."""
        print("[APP_DEBUG] _collect_current_frame_data CALLED")
        if IS_WEB:
            print(f"[WEB_PYXEL_DEBUG] Type of px.images[0]: {type(px.images[0])}")
            print(f"[WEB_PYXEL_DEBUG] Attributes of px.images[0]: {dir(px.images[0])}")
            try:
                print(f"[WEB_PYXEL_DEBUG] px.images[0].width: {px.images[0].width}")
                print(f"[WEB_PYXEL_DEBUG] px.images[0].height: {px.images[0].height}")
            except Exception as e_dim:
                print(f"[WEB_PYXEL_DEBUG] Error accessing width/height: {e_dim}")

            # Try to access a single pixel using get(), if available
            if hasattr(px.images[0], 'get'):
                try:
                    print(f"[WEB_PYXEL_DEBUG] px.images[0].get(0,0) result: {px.images[0].get(0,0)}")
                except Exception as e_get:
                    print(f"[WEB_PYXEL_DEBUG] Error calling .get(0,0): {e_get}")
            else:
                print(f"[WEB_PYXEL_DEBUG] px.images[0] does not have 'get' method.")

            # Check for .data attribute
            if hasattr(px.images[0], 'data'):
                print(f"[WEB_PYXEL_DEBUG] px.images[0] has 'data' attribute. Type: {type(px.images[0].data)}")
            else:
                print(f"[WEB_PYXEL_DEBUG] px.images[0] does NOT have 'data' attribute.")

        if not IS_WEB or not PILImage or not io or not base64: # Pillow 등 라이브러리 없으면 실행 중단
            print("[APP_ERROR] Image processing libraries not available. Cannot collect frame data.")
            # 데이터 수집 중단 (선택적)
            if self.collecting_data:
                print("[APP_DEBUG] Data collection STOPPED due to missing libraries.")
                self.collecting_data = False
            return

        if not hasattr(self.game, 'state') or not self.game.state:
            return

        current_game_state = self.game.state
        image_payload = None
        image_shape_info = None

        try:
            active_image_bank = px.screen # 변경: px.images[0] 대신 px.screen 사용
            width = active_image_bank.width
            height = active_image_bank.height
            image_shape_info = (height, width)

            pil_image = PILImage.new("RGB", (width, height))
            
            for y_coord in range(height):
                for x_coord in range(width):
                    if IS_WEB: # If in web environment
                        color_value = active_image_bank.pget(x_coord, y_coord) # Use pget directly
                        # Assuming pget returns a color index for now, like bget was expected to.
                        # If pget returns an RGB tuple or a direct hex value, this part will need adjustment.
                        color_index = color_value 
                    else: # Otherwise (e.g., desktop)
                        color_index = active_image_bank.get(x_coord, y_coord) # Use get
                    
                    rgb_hex = px.colors[color_index]
                    r = (rgb_hex >> 16) & 0xFF
                    g = (rgb_hex >> 8) & 0xFF
                    b = rgb_hex & 0xFF
                    pil_image.putpixel((x_coord, y_coord), (r, g, b))

            png_buffer = io.BytesIO()
            pil_image.save(png_buffer, format="PNG")
            png_bytes = png_buffer.getvalue()
            image_payload = base64.b64encode(png_bytes).decode('utf-8')
            
        except Exception as e_img:
            print(f"[APP_ERROR] Failed to get and process image data: {e_img}")
            traceback.print_exc()
            return 

        yolo_labels = []
        object_lists_to_process = {
            "player": [current_game_state.player] if hasattr(current_game_state, 'player') and current_game_state.player else [],
            "enemies": current_game_state.enemies if hasattr(current_game_state, 'enemies') else [],
            "bosses": current_game_state.bosses if hasattr(current_game_state, 'bosses') else [],
            "player_shots": current_game_state.player_shots if hasattr(current_game_state, 'player_shots') else [],
            "enemy_shots": current_game_state.enemy_shots if hasattr(current_game_state, 'enemy_shots') else [],
            "powerups": current_game_state.powerups if hasattr(current_game_state, 'powerups') else []
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
                yolo_label = f"{class_id} {x_center_norm:.6f} {y_center_norm:.6f} {width_norm:.6f} {height_norm:.6f}"
                yolo_labels.append(yolo_label)

        if image_payload and yolo_labels:
            self.collected_data.append({
                "timestamp": time.time(),
                "image_original_shape": image_shape_info, 
                "image_png_base64": image_payload,
                "yolo_labels": yolo_labels
            })
        elif image_payload:
             self.collected_data.append({
                "timestamp": time.time(),
                "image_original_shape": image_shape_info, 
                "image_png_base64": image_payload,
                "yolo_labels": [] # 라벨 없는 이미지도 저장 (선택적)
            })

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
            escaped_json_data = json_data_string.replace("\\", "\\\\").replace("'", "\\'")

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
