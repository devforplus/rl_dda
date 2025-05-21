print("Pygbag: src/run_agent_in_game.py parsing START")

import sys # sys 모듈 임포트
import os # os 모듈 임포트 (경로 확인용)

# --- Python 경로 문제 해결 시도 ---
# Pyxel 웹 환경에서 name="src/run_agent_in_game.py"로 실행되므로,
# 스크립트의 __file__ 속성은 'src/run_agent_in_game.py'와 유사한 값을 가질 수 있습니다.
# 프로젝트 루트를 sys.path에 추가해야 'from src.main ...' 같은 구문이 작동합니다.
# Pyodide 환경에서는 os.getcwd()가 가상 파일 시스템의 루트('/)를 반환하는 경우가 많습니다.
# 그리고 pyxel-run의 root="." 설정은 HTML 파일 위치를 기준으로 파일 시스템을 만듭니다.
# 따라서 현재 작업 디렉토리 (HTML 파일이 있는 프로젝트 루트)를 sys.path에 추가합니다.

current_working_directory = os.getcwd()
print(f"Pygbag: Current working directory: {current_working_directory}")
if current_working_directory not in sys.path:
    sys.path.insert(0, current_working_directory)
    print(f"Pygbag: Added '{current_working_directory}' to sys.path")

# 프로젝트의 'src' 폴더가 있는 루트를 sys.path에 추가했으므로,
# 'from src.x import y' 형태의 임포트가 가능해야 합니다.
# 혹시 모르니 스크립트의 실제 경로도 확인해봅니다.
try:
    script_path = os.path.dirname(os.path.abspath(__file__))
    project_root_from_script = os.path.dirname(script_path) # src 폴더의 부모
    print(f"Pygbag: Script path: {script_path}")
    print(f"Pygbag: Calculated project root from script: {project_root_from_script}")
    # if project_root_from_script != current_working_directory and project_root_from_script not in sys.path:
    # sys.path.insert(0, project_root_from_script)
    # print(f"Pygbag: Added (alt) '{project_root_from_script}' to sys.path")
except NameError:
    # __file__이 정의되지 않은 환경일 수 있음 (예: 인터랙티브 실행)
    print("Pygbag: __file__ is not defined. Relying on os.getcwd().")

print(f"Pygbag: sys.path after modification: {sys.path}")

# --- Pyodide 파일 시스템 확인 ---
print(f"Pygbag: Listing PWD (os.getcwd() - '{os.getcwd()}'): {os.listdir(os.getcwd())}")
# pyxel-run root="." 이므로, 현재 HTML 파일 위치(프로젝트 루트)를 기준으로 탐색
if os.path.exists('src'):
    print(f"Pygbag: Listing ./src from PWD: {os.listdir('src')}")
    if os.path.exists('src/main.py'):
        print("Pygbag: src/main.py EXISTS")
    else:
        print("Pygbag: src/main.py NOT FOUND")
else:
    print("Pygbag: ./src directory NOT FOUND in PWD")

print("Pygbag: Checking for specific config files...")
expected_config_path_1 = 'src/config/enemy/enemy_config.py'
expected_config_path_2 = '/pyxel_working_directory/src/config/enemy/enemy_config.py' # 절대 경로 시도

if os.path.exists(expected_config_path_1):
    print(f"Pygbag: Found: {expected_config_path_1}")
else:
    print(f"Pygbag: NOT Found: {expected_config_path_1}")

if os.path.exists(expected_config_path_2):
    print(f"Pygbag: Found: {expected_config_path_2}")
else:
    print(f"Pygbag: NOT Found: {expected_config_path_2}")

# src/config/__init__.py 존재 여부
expected_init_path = 'src/config/__init__.py'
if os.path.exists(expected_init_path):
    print(f"Pygbag: Found: {expected_init_path}")
else:
    print(f"Pygbag: NOT Found: {expected_init_path}")

# src/config/enemy/__init__.py 존재 여부
expected_enemy_init_path = 'src/config/enemy/__init__.py'
if os.path.exists(expected_enemy_init_path):
    print(f"Pygbag: Found: {expected_enemy_init_path}")
else:
    print(f"Pygbag: NOT Found: {expected_enemy_init_path}")

print("Pygbag: Checking for score_config files...")
expected_score_config_path = 'src/config/score/score_config.py'
if os.path.exists(expected_score_config_path):
    print(f"Pygbag: Found: {expected_score_config_path}")
else:
    print(f"Pygbag: NOT Found: {expected_score_config_path}")

expected_score_init_path = 'src/config/score/__init__.py'
if os.path.exists(expected_score_init_path):
    print(f"Pygbag: Found: {expected_score_init_path}")
else:
    print(f"Pygbag: NOT Found: {expected_score_init_path}")

print("Pygbag: Checking for player_config files...")
expected_player_config_path = 'src/config/player/player_config.py'
if os.path.exists(expected_player_config_path):
    print(f"Pygbag: Found: {expected_player_config_path}")
else:
    print(f"Pygbag: NOT Found: {expected_player_config_path}")

expected_player_init_path = 'src/config/player/__init__.py'
if os.path.exists(expected_player_init_path):
    print(f"Pygbag: Found: {expected_player_init_path}")
else:
    print(f"Pygbag: NOT Found: {expected_player_init_path}")

# --- Pyodide 파일 시스템 확인 끝 ---

print("Pygbag: Checking for src/game.py BEFORE importing src.main")
if os.path.exists('src/game.py'):
    print("Pygbag: src/game.py FOUND in PWD before src.main import")
else:
    print("Pygbag: src/game.py NOT FOUND in PWD before src.main import")

# --- Python 경로 문제 해결 시도 끝 ---

import pyxel as px
import platform
import traceback # 예외 출력을 위해 추가

print("Pygbag: Basic imports DONE")

# main.py와 동일한 경로 설정을 위해 sys.path 조작 (필요한 경우)
# import sys
# import os
# current_dir = os.path.dirname(os.path.abspath(__file__))
# project_root = os.path.dirname(current_dir) # src 폴더의 부모, 즉 RL_DDA
# sys.path.insert(0, project_root)
# sys.path.insert(0, os.path.join(project_root, 'src'))

print("Pygbag: About to import App and RandomAgent")
from src.main import App  # src.main에서 App 클래스 임포트
from src.rl.agents import RandomAgent # src.rl.agents에서 RandomAgent 임포트
print("Pygbag: App and RandomAgent IMPORTED")

# from src.config.app.constants import APP_FPS # FPS 정보를 가져오기 위함 (선택적)

if platform.system() == "Emscripten":
    print("Pygbag: Detected Emscripten platform")
    import js # 웹 환경에서 콘솔 출력을 위해
    print("Pygbag: js module IMPORTED")
else:
    print(f"Pygbag: Detected platform: {platform.system()}")


# 웹 환경 감지 (main.py와 동일)
IS_WEB = platform.system() == "Emscripten"
print(f"Pygbag: IS_WEB = {IS_WEB}")

def run_with_agent():
    print("Pygbag: run_with_agent() CALLED")
    try:
        print("Pygbag: run_with_agent() TRY block started")
        # RandomAgent 액션 정의 (0-8)
        #   0: 좌상, 1: 상, 2: 우상
        #   3: 좌,             4: 우
        #   5: 좌하, 6: 하, 7: 우하
        #   8: 공격
        agent_action_space = list(range(9))
        random_agent = RandomAgent(action_space=agent_action_space)
        print("Pygbag: RandomAgent INSTANTIATED")

        # App 인스턴스 생성 시 에이전트 전달
        # App 내부에서 px.init() 및 px.run()이 호출됨
        App(agent=random_agent)
        print("Pygbag: App INSTANTIATED and run (blocking)")
    except Exception as e:
        error_message = f"Pygbag: Error in run_with_agent: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        if IS_WEB and 'js' in globals(): # Check if js was successfully imported
            js.console.error(error_message)
        print(error_message)

if __name__ == "__main__":
    print("Pygbag: __name__ == '__main__' is TRUE")
    # Pyxel 초기화는 App 클래스 내부에서 처리됨
    # 웹 환경에서는 특히 run_with_agent() 전에 px.init()을 호출하면 안 됨.
    run_with_agent()
else:
    print(f"Pygbag: __name__ is {__name__}, NOT '__main__'")

print("Pygbag: src/run_agent_in_game.py parsing END") 