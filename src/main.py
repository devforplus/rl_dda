import pyxel as px
import sys
import platform
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
from monospace_bitmap_font import MonospaceBitmapFont
from input import Input

# 웹 환경 감지
IS_WEB = platform.system() == "Emscripten"

class App:
    def __init__(self) -> None:
        # 웹 환경에서는 일부 기능 제한
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
        
        # 웹 환경에서 파일 경로 처리 방식 변경
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

    def update(self):
        self.input.update()
        self.game.update()

    def draw(self):
        px.cls(0)
        self.game.draw()


if __name__ == "__main__":
    App()
