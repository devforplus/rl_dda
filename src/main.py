import pyxel as px
import sys
import platform
import traceback
import time  # For timestamping (optional)
import json
import os
import asyncio

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
except ImportError as e:
    PILImage = None
    io = None
    base64 = None

# numpy는 별도로 처리 (웹 환경에서 문제가 될 수 있음)
try:
    import numpy
except ImportError as e:
    numpy = None
except Exception as e:
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
SERVER_CLIENT_AVAILABLE = False
try:
    from server_client import (
        NewServerClient,
    )  # 변경: GameDataServerClient -> NewServerClient

    SERVER_CLIENT_AVAILABLE = True
except ImportError as e:
    pass
except Exception as e:
    pass

# 자동 업로드 관련 import 및 변수 삭제됨


class App:
    def __init__(self, agent=None) -> None:
        try:
            self.agent = agent
            # Data collection variables
            self.collecting_data = (
                False  # 데이터 수집 활성화 여부 (C키로 토글 가능하도록 설정)
            )
            self.collected_data = []
            self.capture_interval = (
                5  # 캡처 간격 (프레임) - 에이전트 학습용 고해상도 데이터 수집
            )
            self.frames_since_last_capture = 0

            # 에이전트가 있을 때는 데이터 수집 자동 활성화 (AI 학습용 데이터 수집)
            if self.agent is not None:
                self.collecting_data = True

            # 서버 업로드 관련 변수 (웹/데스크톱 모두 지원)
            self.server_upload_enabled = False
            self.server_client = None
            # self.auto_uploader = None 삭제됨

            # 서버 클라이언트 초기화 시도
            if SERVER_CLIENT_AVAILABLE:
                # 환경 변수나 설정 파일에서 서버 URL을 가져올 수 있음
                # 웹 환경에서는 현재 호스트를 기본으로 사용
                if IS_WEB:
                    default_server_url = os.getenv(
                        "PUBLIC_WORKER_URL",
                        "https://rl-dda-server.ijihyeon164.workers.dev",
                    )  # 웹 환경 기본값 - Cloudflare Workers 배포 주소
                else:
                    default_server_url = "https://rl-dda-server.ijihyeon164.workers.dev"  # 데스크톱 환경 기본값 - Cloudflare Workers 배포 주소
                server_url = os.getenv("GAME_SERVER_URL", default_server_url)
                api_key = os.getenv("GAME_API_KEY", None)  # API 키 추가
                try:
                    self.server_client = NewServerClient(
                        server_url, api_key
                    )  # 변경: NewServerClient 사용
                    self.server_upload_enabled = (
                        True  # 상태 확인 로직 제거하고 기본 활성화 (필요시 조정)
                    )

                    # 에이전트가 있을 때는 서버 업로드도 자동 활성화 (AI 학습 데이터 자동 업로드)
                    if self.agent is not None:
                        self.server_upload_enabled = True

                except Exception as e:  # NewServerClient 초기화 실패 시
                    self.server_client = None
                    self.server_upload_enabled = False
            else:
                # SERVER_CLIENT_AVAILABLE 자체가 False인 경우
                self.server_client = None
                self.server_upload_enabled = False

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
        # 에이전트 사용 중일 때는 데이터 수집 비활성화 방지 (AI 학습용 데이터 보호)
        if self.agent is not None and self.collecting_data:
            return

        self.collecting_data = not self.collecting_data
        if self.collecting_data:
            self.collected_data.clear()
        else:
            if IS_WEB and self.collected_data:
                pass

    def toggle_server_upload(self):
        """서버 업로드 상태를 토글합니다 (웹/데스크톱 모두 지원)."""
        if not SERVER_CLIENT_AVAILABLE:
            return

        if not self.server_client:
            return

        # 에이전트 사용 중일 때는 서버 업로드 비활성화 방지 (AI 학습 데이터 업로드 보호)
        if self.agent is not None and self.server_upload_enabled:
            return

        self.server_upload_enabled = not self.server_upload_enabled
        if self.server_upload_enabled:
            # 서버 연결 재확인
            # NewServerClient에는 check_server_status_sync가 없으므로, 단순 토글로 변경
            # 또는 비동기 상태 확인 후 콜백으로 UI 업데이트 등의 복잡한 처리 필요
            pass
            # if self.server_client.check_server_status_sync(): # 해당 메서드 없음
            #     print("[APP_INFO] 서버 업로드 활성화됨")
            # else:
            #     print("[APP_WARNING] 서버에 연결할 수 없어 업로드를 비활성화합니다.")
            #     self.server_upload_enabled = False
        else:
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

            # 서버 업로드 토글 (U 키, 웹/데스크톱 모두 지원)
            if px.btnp(px.KEY_U):
                self.toggle_server_upload()

            self.game.update()

            # 데이터 수집 로직
            if self.collecting_data:
                self.frames_since_last_capture += 1
                if self.frames_since_last_capture >= self.capture_interval:
                    self.frames_since_last_capture = 0
                    collected_info = self._collect_current_frame_data(for_upload=False)
                    if collected_info:
                        frame_data, pil_image, yolo_data_rows = collected_info
                        if frame_data and frame_data.get("image_png_base64"):
                            self.collected_data.append(frame_data)

                            # 데이터 수집 완료 로그 출력 (플레이어 정보는 참고용으로만 출력)
                            frame_data_log = {
                                "type": "event",
                                "event": "frame_collected",
                                "timestamp": time.time(),
                                "data": {
                                    "image_size_chars": len(
                                        frame_data.get("image_png_base64", "")
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
                        if (
                            self.server_upload_enabled
                            and self.server_client
                            and pil_image
                            and yolo_data_rows  # yolo_data_rows도 확인 (서버 업로드 시 필요)
                        ):
                            # 서버 업로드는 백그라운드에서 처리
                            if IS_WEB:
                                asyncio.ensure_future(
                                    self._upload_frame_to_server(
                                        pil_image, yolo_data_rows, frame_data
                                    )
                                )
                            else:
                                try:
                                    loop = asyncio.get_event_loop()
                                    if loop.is_running():
                                        loop.create_task(
                                            self._upload_frame_to_server(
                                                pil_image, yolo_data_rows, frame_data
                                            )
                                        )
                                except RuntimeError:
                                    pass
                        else:
                            pass

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

        # 서버 업로드 상태 표시 (웹/데스크톱 모두 지원)
        if SERVER_CLIENT_AVAILABLE:  # server_client 존재 여부도 확인 가능
            y_offset += 8
            if self.server_upload_enabled:
                status_text = "SERVER: AUTO" if self.agent is not None else "SERVER: ON"
                px.text(5, y_offset, status_text, 11)  # 밝은 녹색
            else:
                px.text(5, y_offset, "SERVER: OFF", 5)  # 회색

        # 수집된 프레임 수 표시
        if self.collected_data:
            y_offset += 8
            px.text(5, y_offset, f"FRAMES: {len(self.collected_data)}", 7)  # 흰색

        # 키 도움말 표시
        y_offset += 8
        if self.agent is not None:
            px.text(5, y_offset, "AUTO MODE", 6)  # 진한 회색
        else:
            px.text(5, y_offset, "C:Data U:Server", 6)  # 진한 회색

    def _collect_current_frame_data(self, for_upload=False):
        """현재 프레임의 이미지와 게임 객체 정보를 수집하여 YOLO 라벨을 생성합니다."""

        # Pillow, io, base64는 공통 임포트 시도됨. numpy도 마찬가지.
        if not PILImage or not io or not base64:
            if self.collecting_data:
                self.collecting_data = False
            return None

        if not hasattr(self.game, "state") or not self.game.state:
            return None

        current_game_state = self.game.state
        image_payload = None
        image_shape_info = None
        pil_image = None

        try:
            width = px.width  # Pyxel의 전역 화면 너비 사용
            height = px.height  # Pyxel의 전역 화면 높이 사용
            image_shape_info = (height, width)

            # NumPy를 사용한 빠른 화면 캡처 (가능한 경우)
            pil_image = None
            if numpy:
                try:
                    screen_data_raw = px.screen.data

                    if IS_WEB:
                        # 웹 환경에서 screen.data 안전하게 처리
                        if hasattr(screen_data_raw, "to_py"):
                            screen_data_flat_py = screen_data_raw.to_py()
                            screen_data_np = numpy.array(
                                screen_data_flat_py, dtype=numpy.int32
                            ).reshape(height, width)
                        elif hasattr(screen_data_raw, "__iter__"):
                            # 리스트나 배열인 경우
                            screen_data_np = numpy.array(
                                list(screen_data_raw), dtype=numpy.int32
                            ).reshape(height, width)
                        else:
                            # 직접 numpy 변환 시도
                            screen_data_np = numpy.asarray(
                                screen_data_raw, dtype=numpy.int32
                            ).reshape(height, width)
                    else:
                        # 데스크톱 환경
                        screen_data_np = numpy.asarray(
                            screen_data_raw, dtype=numpy.int32
                        )
                        # 필요시 reshape
                        if screen_data_np.shape != (height, width):
                            screen_data_np = screen_data_np.reshape(height, width)

                    # 팔레트를 사용하여 RGB로 변환
                    palette_hex = px.colors.to_list()
                    palette_rgb = numpy.array(
                        [
                            ((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF)
                            for c in palette_hex
                        ],
                        dtype=numpy.uint8,
                    )

                    rgb_array = palette_rgb[screen_data_np]
                    pil_image = PILImage.fromarray(rgb_array, "RGB")
                except Exception as e:
                    pil_image = None

            # NumPy 실패 시 픽셀별 캡처 (폴백)
            if pil_image is None:
                try:
                    pil_image = PILImage.new("RGB", (width, height))
                    palette_hex = px.colors.to_list()

                    for y in range(height):
                        for x in range(width):
                            color_index = px.pget(x, y)
                            if 0 <= color_index < len(palette_hex):
                                rgb_hex = palette_hex[color_index]
                                r = (rgb_hex >> 16) & 0xFF
                                g = (rgb_hex >> 8) & 0xFF
                                b = rgb_hex & 0xFF
                                pil_image.putpixel((x, y), (r, g, b))
                            else:
                                pil_image.putpixel((x, y), (0, 0, 0))
                except Exception as e:
                    return None

            # 게임 상태에서 YOLO 데이터 생성 (탄환 포함)
            yolo_data_rows = []
            if hasattr(self.game, "state") and self.game.state:
                game_state = self.game.state

                # 모든 게임 객체 수집
                all_objects = []

                # 플레이어 추가
                if (
                    hasattr(game_state, "player")
                    and game_state.player
                    and not getattr(game_state.player, "remove", False)
                ):
                    all_objects.append(("player", game_state.player))

                # 플레이어 탄환 추가
                if hasattr(game_state, "player_shots"):
                    for shot in game_state.player_shots:
                        if shot and not getattr(shot, "remove", False):
                            all_objects.append(("player_shot", shot))

                # 적 추가
                if hasattr(game_state, "enemies"):
                    for enemy in game_state.enemies:
                        if enemy and not getattr(enemy, "remove", False):
                            # EntityType을 사용하여 정확한 적 타입 식별
                            enemy_type = getattr(enemy, "type", None)
                            if enemy_type:
                                if hasattr(enemy_type, "name"):
                                    enemy_type_name = enemy_type.name.lower()
                                else:
                                    enemy_type_name = str(enemy_type).lower()
                            else:
                                enemy_type_name = "enemy_a"  # 기본값
                            all_objects.append((enemy_type_name, enemy))

                # 적 탄환 추가
                if hasattr(game_state, "enemy_shots"):
                    for shot in game_state.enemy_shots:
                        if shot and not getattr(shot, "remove", False):
                            all_objects.append(("enemy_shot", shot))

                # 보스 추가
                if hasattr(game_state, "bosses"):
                    for boss in game_state.bosses:
                        if boss and not getattr(boss, "remove", False):
                            # 보스도 적 타입 확인
                            boss_type = getattr(boss, "type", None)
                            if boss_type:
                                if hasattr(boss_type, "name"):
                                    boss_type_name = boss_type.name.lower()
                                else:
                                    boss_type_name = str(boss_type).lower()
                            else:
                                boss_type_name = "enemy_k"  # 기본 보스 타입
                            all_objects.append((boss_type_name, boss))

                # 파워업 추가
                if hasattr(game_state, "powerups"):
                    for powerup in game_state.powerups:
                        if powerup and not getattr(powerup, "remove", False):
                            all_objects.append(("powerup", powerup))

                # 폭발 추가 (선택적 - 짧은 지속시간)
                if hasattr(game_state, "explosions"):
                    for explosion in game_state.explosions:
                        if explosion and not getattr(explosion, "remove", False):
                            all_objects.append(("explosion", explosion))

                # 수집된 객체 통계
                object_counts = {}
                for obj_type, obj in all_objects:
                    object_counts[obj_type] = object_counts.get(obj_type, 0) + 1

                # YOLO 라벨 생성
                for obj_type, obj in all_objects:
                    # CLASS_MAP에서 클래스 ID 찾기
                    class_id = CLASS_MAP.get(obj_type, None)
                    if class_id is None:
                        continue

                    # 객체 좌표와 크기 가져오기
                    obj_x = getattr(obj, "x", 0)
                    obj_y = getattr(obj, "y", 0)
                    obj_w = getattr(obj, "w", 8)
                    obj_h = getattr(obj, "h", 8)

                    # 플레이어 탄환의 경우 YOLO 라벨 생성 시 X 좌표를 왼쪽으로 3px 이동
                    if obj_type == "player_shot":
                        obj_x -= 3

                    # YOLO 정규화 좌표 계산
                    x_center = obj_x + obj_w / 2
                    y_center = obj_y + obj_h / 2
                    x_center_norm = x_center / APP_WIDTH
                    y_center_norm = y_center / APP_HEIGHT
                    width_norm = obj_w / APP_WIDTH
                    height_norm = obj_h / APP_HEIGHT

                    # 좌표값이 유효한 범위 내에 있는지 확인 (0~1)
                    if 0 <= x_center_norm <= 1 and 0 <= y_center_norm <= 1:
                        yolo_data_row = f"{class_id} {x_center_norm:.6f} {y_center_norm:.6f} {width_norm:.6f} {height_norm:.6f}"
                        yolo_data_rows.append(yolo_data_row)

                print(
                    json.dumps(
                        {
                            "type": "event",
                            "event": "yolo_objects_collected",
                            "timestamp": time.time(),
                            "data": {
                                "objects_by_type": dict(object_counts),
                                "total_labels": len(yolo_data_rows),
                            },
                        }
                    )
                )

            # 이미지를 base64로 인코딩
            image_png_base64 = None
            image_original_shape = None

            if pil_image:
                try:
                    # image_original_shape 생성
                    image_original_shape = [
                        pil_image.height,
                        pil_image.width,
                        len(pil_image.getbands()),
                    ]

                    # image_png_base64 생성
                    buffered = io.BytesIO()
                    pil_image.save(buffered, format="PNG")
                    image_png_base64 = base64.b64encode(buffered.getvalue()).decode(
                        "utf-8"
                    )

                except Exception as e:
                    return None
            else:
                return None

            # yolo_labels 생성 (헤더 포함)
            header = CLASS_MAP.get(-1, "entity_num x_center y_center width height")
            yolo_labels = [header] + yolo_data_rows

            # 프레임 데이터 생성 (서버 API 형식에 맞춤)
            frame_data = {
                "timestamp": time.time(),
                "image_original_shape": image_original_shape,
                "image_png_base64": image_png_base64,
                "yolo_labels": yolo_labels,
            }

            if for_upload:
                return frame_data, pil_image, yolo_data_rows
            else:
                return frame_data, pil_image, yolo_data_rows

        except Exception as e:
            error_message = f"Error in _collect_current_frame_data: {type(e).__name__}: {e}\\n{traceback.format_exc()}"
            if IS_WEB and "js" in globals():
                js.console.error(error_message)
            print(error_message, file=sys.stderr)
            return None

    async def _upload_frame_to_server(self, pil_image, yolo_data_rows, frame_data):
        """서버로 프레임 데이터 업로드 (비동기 작업을 스케줄링하는 동기 래퍼)"""
        if not self.server_client or not self.server_upload_enabled:
            return False

        if not frame_data or not frame_data.get("image_png_base64"):
            return False

        try:
            # frame_data에 이미 필요한 모든 정보가 포함되어 있음
            dataset_entry = {
                "timestamp": frame_data.get("timestamp", time.time()),
                "image_original_shape": frame_data.get("image_original_shape"),
                "image_png_base64": frame_data.get("image_png_base64"),
                "yolo_labels": frame_data.get("yolo_labels", []),
            }

            # 필수 필드 검증
            if not all(
                [
                    dataset_entry["timestamp"],
                    dataset_entry["image_original_shape"],
                    dataset_entry["image_png_base64"],
                    isinstance(dataset_entry["yolo_labels"], list),
                ]
            ):
                return False

            # NewServerClient의 create_data는 list of dicts를 받음
            upload_id = await self.server_client.create_data([dataset_entry])

            if upload_id:
                return True
            else:
                return False
        except Exception as e:
            traceback.print_exc()
            return False

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
