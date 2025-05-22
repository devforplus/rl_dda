import pyxel as px
import platform
import traceback
import sys # For stderr

from main import App
from rl.agents import RandomAgent

# from config.app.constants import APP_FPS # Example: if needed, ensure path is correct

IS_WEB = platform.system() == "Emscripten"

def run_with_agent():
    try:
        agent_action_space = list(range(9))
        random_agent = RandomAgent(action_space=agent_action_space)
        App(agent=random_agent)
    except Exception as e:
        error_message = f"Error in run_with_agent: {type(e).__name__}: {e}\n{traceback.format_exc()}"
        # Pyxel/Pyodide will typically print Python exceptions to the browser console.
        # Using sys.stderr for additional safety.
        print(error_message, file=sys.stderr)

if __name__ == "__main__":
    run_with_agent() 