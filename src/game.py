from enum import Enum, auto
from typing import Optional
import platform

from states.game_state.game_state_titles import GameStateTitles
from states.game_state.game_state_stage import GameStateStage
from states.game_state.game_state_complete import GameStateComplete
from game_vars import GameVars
from data_collection.screen_capture import ScreenCapture
from data_collection.label_generator import LabelGenerator
import os
import cv2
import time

# 웹 환경 감지
IS_WEB = platform.system() == "Emscripten"

# 웹 환경이 아닐 때만 object_detection 모듈 가져오기
# if not IS_WEB:
#     from object_detection import GameDetector
# from input import COLLECT_DATA


class GameState(Enum):
    """
    게임 상태 열거형.

    게임의 다양한 상태를 정의하며, 각 상태는 게임의 진행 흐름을 결정한다.
    """

    NONE = 0  # 초기/정의되지 않은 상태
    TITLES = auto()  # 타이틀 화면
    STAGE = auto()  # 게임 스테이지 진행 중
    GAME_COMPLETE = auto()  # 게임 완료


class Game:
    """
    게임 메인 클래스.

    속성:
        app: 애플리케이션 객체
        next_state (Optional[GameState]): 다음 게임 상태
        game_vars (GameVars): 게임 변수 관리 객체
        state: 현재 게임 상태 객체
    """

    app: object
    next_state: Optional[GameState]
    game_vars: GameVars
    state: object

    def __init__(self, app) -> None:
        """
        게임 초기화.

        매개변수:
            app: 애플리케이션 객체
        """
        self.app = app
        self.next_state = None
        self.game_vars = GameVars(self)
        
        # 데이터 수집 관련 초기화
        self.is_collecting = False
        self.window_name = "VORTEXION"  # 게임 윈도우 이름
        self.screen_capture = ScreenCapture(self.window_name)
        self.label_generator = LabelGenerator("data/labels")
        self.frame_count = 0
        self.save_dir = "data"
        os.makedirs(os.path.join(self.save_dir, "images"), exist_ok=True)
        os.makedirs(os.path.join(self.save_dir, "labels"), exist_ok=True)
        
        # 초기 게임 상태 설정
        self.state = GameStateTitles(self)
        # self.state = GameStateStage(self)
        # self.state = GameStateComplete(self)

    def go_to_titles(self) -> None:
        """타이틀 화면으로 전환."""
        self.next_state = GameState.TITLES

    def go_to_new_game(self) -> None:
        """새 게임 시작."""
        self.game_vars.new_game()
        self.next_state = GameState.STAGE

    def go_to_continue(self) -> None:
        """게임 계속 진행."""
        self.game_vars.continue_game()
        self.next_state = GameState.STAGE

    def go_to_game_complete(self) -> None:
        """게임 완료 상태로 전환."""
        self.next_state = GameState.GAME_COMPLETE

    def go_to_next_stage(self) -> None:
        """
        다음 스테이지로 진행.

        스테이지가 더 없으면 게임 완료 상태로 전환.
        """
        if self.game_vars.go_to_next_stage():
            self.next_state = GameState.STAGE
        else:
            self.go_to_game_complete()

    def switch_state(self) -> None:
        """게임 상태 전환 처리."""
        new_state = None
        if self.next_state == GameState.TITLES:
            new_state = GameStateTitles
        elif self.next_state == GameState.STAGE:
            new_state = GameStateStage
        elif self.next_state == GameState.GAME_COMPLETE:
            new_state = GameStateComplete
        else:
            return

        # 현재 상태 종료 처리 후 새로운 상태로 전환
        self.state.on_exit()
        self.state = new_state(self)
        self.next_state = None

    def update(self) -> None:
        """게임 상태 업데이트."""
        if self.next_state is not None:
            self.switch_state()
        self.state.update()
        
        # 데이터 수집 중일 때 프레임 수집
        if self.is_collecting and isinstance(self.state, GameStateStage):
            self._collect_frame()

    def draw(self) -> None:
        """게임 상태 그리기."""
        self.state.draw()
        
        # 데이터 수집 상태 표시
        if self.is_collecting:
            import pyxel
            pyxel.text(10, 10, "데이터 수집 중...", 7)  # 7은 흰색

    def toggle_data_collection(self) -> None:
        """데이터 수집 시작/중지 토글"""
        self.is_collecting = not self.is_collecting
        if self.is_collecting:
            print("데이터 수집을 시작합니다.")
        else:
            print("데이터 수집을 중지했습니다.")
            
    def _collect_frame(self) -> None:
        try:
            # 화면 캡처
            frame = self.screen_capture.capture_window()
            image_filename = f"frame_{self.frame_count:06d}.png"
            image_path = os.path.join(self.save_dir, "images", image_filename)
            cv2.imwrite(image_path, frame)

            # 게임 좌표를 이미지 좌표로 변환하는 함수
            def transform_game_to_image_coords(game_x, game_y, game_w, game_h):
                """
                게임 내부 좌표를 이미지 좌표로 변환합니다.
                시각화 결과와 객체 분석을 바탕으로 정밀하게 조정된 변환식입니다.
                
                시각화에서 관찰된 좌표:
                - 플레이어: 게임 좌표계 중심에서 왼쪽, 이미지에서 (160~170, 280~290) 위치
                - 적: 게임 화면 오른쪽, 이미지에서 (560~590, 210~360) 위치
                """
                # 게임 해상도 (내부 좌표계)
                GAME_WIDTH, GAME_HEIGHT = 256, 192
                # 이미지 해상도
                IMG_WIDTH, IMG_HEIGHT = 768, 576
                
                # 객체 타입 인식 (플레이어와 적 구분)
                is_enemy = game_w > 5  # 적은 일반적으로 플레이어보다 큼
                
                if is_enemy:
                    # === 적 객체 (청록색) 좌표 변환 ===
                    # 관찰 결과: 적 객체는 이미지 오른쪽(560~590px)에 위치
                    # 적 객체의 x좌표를 왼쪽->오른쪽으로 변환 (특별 스케일 적용)
                    # 게임 상에서 적은 x좌표가 약 200 부근이고, 이미지에서는 580 부근
                    ENEMY_SCALE_X = 2.9
                    ENEMY_OFFSET_X = 22  # 10에서 22로 변경 (12픽셀 오른쪽으로 이동)
                    
                    # 적의 y좌표는 비교적 정확하게 매핑됨 (3배 스케일 유지)
                    ENEMY_SCALE_Y = 3.0
                    ENEMY_OFFSET_Y = 0
                    
                    # 적 객체 바운딩 박스 크기 조정 (약간 큰 값으로)
                    ENEMY_SIZE_FACTOR = 4.0
                    
                    # 적 좌표 변환 적용
                    img_x = game_x * ENEMY_SCALE_X + ENEMY_OFFSET_X
                    img_y = game_y * ENEMY_SCALE_Y + ENEMY_OFFSET_Y
                    img_w = game_w * ENEMY_SIZE_FACTOR
                    img_h = game_h * ENEMY_SIZE_FACTOR
                else:
                    # === 플레이어 (흰색) 좌표 변환 ===
                    # 관찰 결과: 플레이어는 이미지 왼쪽(160~170px)에 위치
                    # 정확한 위치 매핑을 위한 변환 식
                    PLAYER_SCALE_X = 2.6
                    PLAYER_OFFSET_X = -12  # 10에서 -1로 변경 (11픽셀 왼쪽으로 이동)
                    
                    PLAYER_SCALE_Y = 3.0
                    PLAYER_OFFSET_Y = 0
                    
                    # 플레이어 바운딩 박스 크기 (정확한 크기로)
                    PLAYER_SIZE_FACTOR = 2.5
                    
                    # 플레이어 좌표 변환 적용
                    img_x = game_x * PLAYER_SCALE_X + PLAYER_OFFSET_X
                    img_y = game_y * PLAYER_SCALE_Y + PLAYER_OFFSET_Y
                    img_w = game_w * PLAYER_SIZE_FACTOR
                    img_h = game_h * PLAYER_SIZE_FACTOR
                
                return img_x, img_y, img_w, img_h

            if isinstance(self.state, GameStateStage):
                player = self.state.player
                # 중심좌표로 변환
                player_center_x = player.x + player.w / 2
                player_center_y = player.y + player.h / 2
                player_pos = (player_center_x, player_center_y)
                player_bbox = (player.w, player.h)
                enemies = []
                for enemy in self.state.enemies:
                    enemy_type_str = enemy.type.name.lower()  # Enum → 소문자 문자열
                    # 중심좌표로 변환
                    enemy_center_x = enemy.x + enemy.w / 2
                    enemy_center_y = enemy.y + enemy.h / 2
                    enemies.append({
                        "type": enemy_type_str,
                        "position": (enemy_center_x, enemy_center_y),
                        "bbox": (enemy.w, enemy.h)
                    })
                # 보스도 포함
                if hasattr(self.state, "bosses"):
                    for boss in self.state.bosses:
                        boss_type_str = boss.type.name.lower()
                        boss_center_x = boss.x + boss.w / 2
                        boss_center_y = boss.y + boss.h / 2
                        enemies.append({
                            "type": boss_type_str,
                            "position": (boss_center_x, boss_center_y),
                            "bbox": (boss.w, boss.h)
                        })

                # === 고정 클래스 인덱스 ===
                CLASS_LIST = [
                    "player",
                    "enemy_a", "enemy_b", "enemy_c", "enemy_d", "enemy_e", "enemy_f", "enemy_g", "enemy_h",
                    "enemy_i", "enemy_j", "enemy_k", "enemy_l", "enemy_m", "enemy_n", "enemy_o", "enemy_p"
                ]
                CLASS_MAP = {cls: idx for idx, cls in enumerate(CLASS_LIST)}

                # 이미지 크기 (정규화 기준)
                w, h = 768, 576
                yolo_lines = []
                
                # 플레이어 (좌표 변환 추가)
                px, py = player_pos
                pw, ph = player_bbox
                # 게임 좌표를 이미지 좌표로 변환
                px_img, py_img, pw_img, ph_img = transform_game_to_image_coords(px, py, pw, ph)
                # 정규화
                x_center = px_img / w
                y_center = py_img / h
                width = pw_img / w
                height = ph_img / h
                yolo_lines.append(f"{CLASS_MAP['player']} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")
                
                # 적들 (좌표 변환 추가)
                for enemy in enemies:
                    ex, ey = enemy["position"]
                    ew, eh = enemy["bbox"]
                    class_name = enemy['type']
                    if class_name not in CLASS_MAP:
                        continue
                    # 게임 좌표를 이미지 좌표로 변환
                    ex_img, ey_img, ew_img, eh_img = transform_game_to_image_coords(ex, ey, ew, eh)
                    # 정규화
                    x_center = ex_img / w
                    y_center = ey_img / h
                    width = ew_img / w
                    height = eh_img / h
                    yolo_lines.append(f"{CLASS_MAP[class_name]} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

                # YOLO txt 저장
                yolo_label_dir = os.path.join(self.save_dir, "yolo_labels")
                os.makedirs(yolo_label_dir, exist_ok=True)
                yolo_label_path = os.path.join(yolo_label_dir, f"frame_{self.frame_count:06d}.txt")
                with open(yolo_label_path, "w") as f:
                    f.write("\n".join(yolo_lines))

                self.frame_count += 1

        except Exception as e:
            print(f"데이터 수집 중 오류 발생: {e}")
            self.is_collecting = False
