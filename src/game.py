import platform
from enum import Enum, auto # GameState를 위해 필요
import sys # sys 모듈 임포트

from states.game_state.game_state_stage import GameStateStage
# from states.game_state.game_state_titles import GameStateTitles # 필요시 주석 해제
# from states.game_state.game_state_complete import GameStateComplete # 필요시 주석 해제
from game_vars import GameVars
# from utils.transform_utils import transform_game_to_image_coords # 데이터 수집 시 필요
# from data_collection.screen_capture import ScreenCapture # 데이터 수집 시 필요
# from data_collection.label_generator import LabelGenerator # 데이터 수집 시 필요
import os
import time
from config.game_config import CLASS_MAP # 데이터 수집 시 필요. CLASS_MAP이 정의되어 있어야 함.

IS_WEB = platform.system() == "Emscripten"

# GameState Enum 정의 (이전에 주석 처리됨)
class GameState(Enum):
    NONE = 0
    TITLES = auto()
    STAGE = auto()
    GAME_COMPLETE = auto()

class Game:
    def __init__(self, app):
        self.app = app
        self.next_state = None
        self.game_vars = GameVars(self)
        self.collected_frames_data = [] # 데이터 수집용

        # 게임 시작 시 바로 스테이지로 진입 (타이틀 생략)
        self.start_new_game() # GameVars 초기화 및 첫 스테이지 시작

    def start_new_game(self):
        """새 게임을 시작합니다 (스테이지 1부터)."""
        self.game_vars.new_game() # 점수, 목숨, 스테이지 등 초기화
        try:
            print("[GAME_PY_DEBUG] Starting new game, initializing GameStateStage.")
            self.state = GameStateStage(self)
        except Exception as e:
            print(f"Error initializing GameStateStage in start_new_game: {e}")
            if IS_WEB and 'js' in globals():
                js.console.error(f"Error initializing GameStateStage in start_new_game: {e}") # type: ignore
            self.state = None

    def restart_game(self):
        """현재 게임을 첫 스테이지부터 다시 시작합니다."""
        print("[GAME_PY_DEBUG] Restarting game.")
        self.start_new_game()

    def go_to_next_stage(self):
        """다음 스테이지로 진행합니다."""
        if self.game_vars.go_to_next_stage():
            try:
                print(f"[GAME_PY_DEBUG] Going to next stage: {self.game_vars.stage_num}")
                self.state = GameStateStage(self) # 새 스테이지 인스턴스 생성
            except Exception as e:
                print(f"Error initializing GameStateStage in go_to_next_stage: {e}")
                if IS_WEB and 'js' in globals():
                    js.console.error(f"Error initializing GameStateStage in go_to_next_stage: {e}") # type: ignore
                self.state = None
        else:
            # TODO: 게임 완료 처리 (예: GameStateComplete 상태로 전환)
            print("[GAME_PY_DEBUG] Final stage cleared. Game complete (Not implemented).")
            self.go_to_titles() # 임시로 타이틀로 이동 (또는 재시작)

    def go_to_titles(self):
        """타이틀 화면으로 돌아갑니다 (현재는 게임 재시작으로 대체)."""
        # 현재 타이틀 화면이 없으므로, 바로 게임을 재시작합니다.
        # 추후 GameStateTitles가 구현되면 해당 상태로 변경합니다.
        print("[GAME_PY_DEBUG] Going to titles (currently restarting game).")
        self.restart_game()
    
    def update(self):
        if self.state:
            try:
                self.state.update()
            except Exception as e:
                print(f"Error in Game state update ({type(self.state).__name__}): {e}")
                if IS_WEB and 'js' in globals():
                    js.console.error(f"Error in Game state update ({type(self.state).__name__}): {e}") # type: ignore
        
        if self.next_state:
            self.state = self.next_state
            self.next_state = None
    
    def draw(self):
        if self.state:
            try:
                self.state.draw()
            except Exception as e:
                print(f"Error in Game state draw ({type(self.state).__name__}): {e}")
                if IS_WEB and 'js' in globals():
                    js.console.error(f"Error in Game state draw ({type(self.state).__name__}): {e}") # type: ignore
        # Fallback drawing logic removed
