import pyxel as px

import input as input
from hud import Hud
from system.const import MUSIC_GAME_COMPLETE
from audio import load_music, play_music, stop_music

# 화면 너비
VIEW_WIDTH = 256
# 맵 높이
MAP_HEIGHT = 192
# 배경 스크롤 속도
BG_SCROLL_SPD = 8
# 타이틀 화면 맵 파일
TITLE_SCREEN_MAP_FILE = "complete.tmx"
# 배경 타일맵 인덱스
BG_TM_INDEX = 0


class GameStateComplete:
    """
    게임 완료 상태를 나타내는 클래스.

    속성:
        game: 게임 객체
        input: 사용자 입력 처리 객체
        font: 폰트 객체
        hud: HUD 객체
        scroll_x: 배경 스크롤 x 좌표
        music: 음악 객체
    """

    def __init__(self, game) -> None:
        """
        게임 완료 상태 초기화.

        음악 재생을 시작합니다.
        """
        self.game = game
        self.input = self.game.app.input
        self.font = game.app.main_font

        # HUD 객체 초기화
        self.hud = Hud(game.game_vars, self.font)

        # 배경 타일맵 로드
        px.tilemaps[BG_TM_INDEX] = px.Tilemap.from_tmx(
            "assets/" + TITLE_SCREEN_MAP_FILE, BG_TM_INDEX
        )

        # 배경 스크롤 초기값 설정
        self.scroll_x = 0

        # 음악 로드 및 재생
        self.music = load_music(MUSIC_GAME_COMPLETE)
        play_music(self.music, True, num_channels=3)

    def on_exit(self):
        """게임 완료 상태 종료 시 처리."""
        # 음악 정지
        stop_music(3)

    def update(self):
        """게임 완료 상태 업데이트."""
        # 배경 스크롤 업데이트
        self.scroll_x -= BG_SCROLL_SPD
        if self.scroll_x <= -VIEW_WIDTH:
            self.scroll_x += VIEW_WIDTH

        # 사용자 입력 처리 (타이틀 화면으로 이동)
        if self.input.has_tapped(input.BUTTON_1) or self.input.has_tapped(
            input.BUTTON_2
        ):
            self.game.go_to_titles()

    def draw(self):
        """게임 완료 상태 그리기."""
        # 배경 그리기 (스크롤링 적용)
        px.bltm(self.scroll_x, 0, BG_TM_INDEX, 0, 0, VIEW_WIDTH, MAP_HEIGHT)
        px.bltm(
            self.scroll_x + VIEW_WIDTH, 0, BG_TM_INDEX, 0, 0, VIEW_WIDTH, MAP_HEIGHT
        )

        # 텍스트 그리기
        self.font.draw_text(56, 72, "THANKS FOR PLAYING")
        self.font.draw_text(88, 96, "FINAL SCORE")
        self.font.draw_text(104, 112, f"{self.game.game_vars.score}")
