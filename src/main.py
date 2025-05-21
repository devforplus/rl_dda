print("Pygbag: src/main.py parsing START")

import pyxel as px
import sys
import platform
import traceback # 예외 출력을 위해 추가

print("Pygbag: src/main.py basic imports DONE")

print("Pygbag: src/main.py - About to import Game from game.py")
from game import Game
print("Pygbag: src/main.py - Imported Game from game.py SUCCESSFULLY")

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
from input import Input

# 웹 환경에서 JavaScript와 상호작용하기 위한 js 모듈 임포트 시도
IS_WEB = platform.system() == "Emscripten" # IS_WEB 정의를 위로 이동
if IS_WEB:
    import js
    import json # JSON 문자열 생성을 위해

class App:
    def __init__(self, agent=None) -> None:
        try:
            self.agent = agent
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
            
            if IS_WEB:
                px.images[0].load(0, 0, "assets/gfx.png")
                px.load(
                    "assets/sounds.pyxres",
                    excl_images=True,
                    excl_tilemaps=True,
                    excl_musics=True,
                )
            else:
                px.images[0].load(0, 0, str(ASSETS_DIR / "gfx.png"))
                px.load(
                    str(ASSETS_DIR / "sounds.pyxres"),
                    excl_images=True,
                    excl_tilemaps=True,
                    excl_musics=True,
                )

            self.main_font = MonospaceBitmapFont()
            self.input = Input()
            self.game = Game(self)

            px.run(self.update, self.draw)
        except Exception as e:
            error_message = f"Error in App.__init__: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            if IS_WEB:
                js.console.error(error_message)
            print(error_message)
            raise # 초기화 실패 시 앱 실행 중단

    def apply_agent_action(self, action_id):
        """ 에이전트가 선택한 action_id를 게임 입력으로 변환합니다. """
        # 먼저 모든 입력을 False로 초기화
        self.input.left_pressed = False
        self.input.right_pressed = False
        self.input.up_pressed = False
        self.input.down_pressed = False
        self.input.fire_pressed = False

        if action_id == 0: # 좌상
            self.input.left_pressed = True
            self.input.up_pressed = True
        elif action_id == 1: # 상
            self.input.up_pressed = True
        elif action_id == 2: # 우상
            self.input.right_pressed = True
            self.input.up_pressed = True
        elif action_id == 3: # 좌
            self.input.left_pressed = True
        elif action_id == 4: # 우
            self.input.right_pressed = True
        elif action_id == 5: # 좌하
            self.input.left_pressed = True
            self.input.down_pressed = True
        elif action_id == 6: # 하
            self.input.down_pressed = True
        elif action_id == 7: # 우하
            self.input.right_pressed = True
            self.input.down_pressed = True
        elif action_id == 8: # 공격
            self.input.fire_pressed = True

    def update(self):
        try:
            if self.agent:
                agent_action = self.agent.select_action(state=None)
                self.apply_agent_action(agent_action)
            
            self.input.update()
            self.game.update()

            # 데이터 저장 키 확인 (예: S 키)
            if not IS_WEB and self.input.has_tapped(input.BUTTON_2): # X 키를 임시로 저장에 할당 (로컬 테스트용)
                # 로컬에서 저장하는 로직 (필요시 구현, 지금은 pass)
                # self.save_collected_data_locally()
                print("Local save triggered (not implemented).")
            elif IS_WEB and px.btnp(px.KEY_S): # 웹에서 S키로 저장
                self.download_collected_data_web()
        except Exception as e:
            error_message = f"Error in App.update: {type(e).__name__}: {e}\n{traceback.format_exc()}"
            if IS_WEB:
                js.console.error(error_message)
            print(error_message)
            # 업데이트 루프에서 오류 발생 시 게임을 중단할지 여부는 상황에 따라 결정
            # px.quit() # 필요시 게임 종료

    def draw(self):
        try:
            print("Pygbag: App.draw called - attempting basic draw")
            px.cls(1)  # Clear screen to dark blue (Pyxel color 1)
            px.rect(10, 10, 50, 50, 8)  # Draw a pink rectangle (Pyxel color 8)
            px.text(5, 5, "TESTING PYXEL WEB", 7) # Draw white text (Pyxel color 7)
            print("Pygbag: App.draw - basic drawing commands executed")
        except Exception as e:
            print(f"Pygbag: Error in App.draw: {e}")
            import traceback
            traceback.print_exc()

    def download_collected_data_web(self):
        """ 웹 환경에서 수집된 데이터를 JSON 파일로 다운로드합니다. """
        if not IS_WEB or not hasattr(self.game, 'collected_frames_data') or not self.game.collected_frames_data:
            print("다운로드할 데이터가 없거나 웹 환경이 아닙니다.")
            return

        try:
            # collected_frames_data를 JSON 문자열로 변환
            # numpy 배열이 있다면 tolist()로 변환된 상태여야 함 (이미 game.py에서 처리)
            json_data_string = json.dumps(self.game.collected_frames_data)
            
            # JavaScript를 사용하여 파일 다운로드 트리거
            file_name = "collected_dataset.json"
            mime_type = "application/json"
            
            # JavaScript 코드 생성
            js_code = f"""
            var blob = new Blob(['{json_data_string.replace("\'","\\\'")}'], {{type: '{mime_type}'}});
            var link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = '{file_name}';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);
            """
            js.eval(js_code)
            print(f"'{file_name}' 다운로드를 시작합니다...")
            # 데이터 다운로드 후 self.game.collected_frames_data.clear() 고려
        except Exception as e:
            print(f"웹 데이터 다운로드 중 오류 발생: {e}")

# if __name__ == "__main__":
#     App()
