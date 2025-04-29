import pyxel as px

# Pyxel: A Python-based game engine for creating retro-style games.
# It provides an easy-to-use API for graphics, sound, and input.

import input as input
from hud import Hud
from system.const import APP_VERSION
from audio import load_music, play_music

# 화면 너비 (픽셀 단위)
VIEW_WIDTH = 256
# 맵 높이 (픽셀 단위)
MAP_HEIGHT = 160
# 배경 스크롤 속도 (픽셀 단위 per frame)
BG_SCROLL_SPD = 8
# 타이틀 화면 타일맵 파일명
TILEMAP_FILE = "title.tmx"
# 타이틀 배경 음악 파일명
MUSIC_FILE = "music_title.json"
# 배경 타일맵 인덱스 (내부 식별자)
BG_TM_INDEX = 0
# 전경 타일맵 인덱스 (내부 식별자)
FG_TM_INDEX = 1


class GameStateTitles:
    """
    타이틀 화면 상태를 나타내는 클래스.

    속성:
        game: 게임 객체
        input: 사용자 입력 처리 객체
        font: 폰트 객체
        hud: HUD 객체
        scroll_x: 배경 스크롤 x 좌표
        selections: 메뉴 항목 리스트
        selected_index: 현재 선택된 메뉴 항목 인덱스
        music: 음악 객체
    """

    def __init__(self, game) -> None:
        """
        타이틀 화면 상태 초기화.

        타이틀 화면의 배경, 메뉴 항목 등을 초기화합니다.
        """
        self.game = game
        self.input = self.game.app.input
        self.font = game.app.main_font

        # HUD 초기화 (점수 표시 등)
        self.hud = Hud(game.game_vars, self.font)

        # 배경 및 전경 타일맵 로딩
        # Tiled로 작성한 타일맵을 로드하여 pyxel에서 사용
        px.tilemaps[BG_TM_INDEX] = px.Tilemap.from_tmx(
            "assets/" + TILEMAP_FILE, BG_TM_INDEX
        )
        px.tilemaps[FG_TM_INDEX] = px.Tilemap.from_tmx(
            "assets/" + TILEMAP_FILE, FG_TM_INDEX
        )

        # 배경 스크롤 초기 위치 설정
        self.scroll_x = 0  # 스크롤 시작 위치 (왼쪽)

        # 메뉴 항목 정의
        # 각 항목은 위치, 레이블, 실행 액션으로 구성
        self.selections = {
            0: {
                "loc": [96, 112],  # 화면 상 위치
                "label": "GAME START",  # 표시되는 텍스트
                "action": self.game.go_to_new_game,  # 선택 시 실행할 함수
            },
            1: {
                "loc": [96, 128],
                "label": "CONTINUE",
                "action": self.game.go_to_continue,
            },
        }

        # 현재 선택된 메뉴 항목
        self.selected_index = 0

        # 음악 로딩 및 재생 시작
        self.music = load_music(MUSIC_FILE)
        play_music(self.music)

    def on_exit(self):
        """타이틀 화면 종료 시 처리

        pyxel의 사운드 재생을 중지합니다.
        """
        px.stop()

    def update(self):
        """
        타이틀 화면 업데이트 로직

        1. 배경 스크롤 업데이트
            - 배경을 왼쪽으로 스크롤하여 움직이는 효과 생성
            - 스크롤 속도는 BG_SCROLL_SPD 픽셀/프레임
        2. 사용자 입력 처리 (메뉴 선택)
        """
        # 배경 스크롤
        # 스크롤링: 화면에 그래픽스를 연속적으로 그려 움직이는 효과 생성
        self.scroll_x -= BG_SCROLL_SPD  # 왼쪽으로 스크롤
        if self.scroll_x <= -VIEW_WIDTH:
            # 스크롤이 화면 너비만큼 왼쪽으로 이동하면
            self.scroll_x += VIEW_WIDTH  # 다시 오른쪽으로 시작 위치로 이동

        # 메뉴 선택 변경
        if self.input.has_tapped(input.UP) or self.input.has_tapped(input.DOWN):
            # 현재 선택된 항목 toggle
            self.selected_index = 0 if self.selected_index == 1 else 1

        # 메뉴 실행
        if self.input.has_tapped(input.BUTTON_1) or self.input.has_tapped(
            input.BUTTON_2
        ):
            self.selections[self.selected_index]["action"]()

    def draw(self):
        """
        타이틀 화면 그리기 로직

        1. 배경 렌더링 (스크롤링)
        2. 메뉴 항목 렌더링
        3. HUD 렌더링
        """
        # 배경 그리기
        # pyxel.bltm: 블록 단위로 그래픽을 전송하는 함수
        # (x, y, tm_index, tx, ty, width, height)
        px.bltm(self.scroll_x, 16, BG_TM_INDEX, 0, 0, VIEW_WIDTH, MAP_HEIGHT)
        px.bltm(
            self.scroll_x + VIEW_WIDTH, 16, BG_TM_INDEX, 0, 0, VIEW_WIDTH, MAP_HEIGHT
        )

        # 전경 그리기
        px.bltm(0, 16, FG_TM_INDEX, 0, 0, VIEW_WIDTH, MAP_HEIGHT, 0)

        # 메뉴 항목 그리기
        for k, v in self.selections.items():
            loc = v["loc"]
            if k == self.selected_index:
                # 선택된 항목 표시
                px.blt(loc[0] - 16, loc[1] - 4, 0, 0, 0, 16, 16, 0)
            # 텍스트 그리기
            self.font.draw_text(loc[0], loc[1], v["label"])

        # HUD 그리기
        self.hud.draw()

        # 버전 정보 표시
        px.text(8, 152, f"v{APP_VERSION}", 4)
