import pyxel as px

from system.const import MAX_WEAPONS, MAX_WEAPON_LEVEL, WEAPON_NAMES


class Hud:
    """
    게임의 헤드업 디스플레이(HUD)를 담당하는 클래스.

    속성:
        game_vars: 게임 변수 관리 객체
        font: 텍스트 렌더링을 위한 폰트 객체
    """

    def __init__(self, game_vars, font) -> None:
        """
        HUD 초기화.

        매개변수:
            game_vars: 게임 변수 관리 객체
            font: 텍스트 렌더링을 위한 폰트 객체
        """
        self.game_vars = game_vars
        self.font = font

    def draw_weapon_level(self, i: int, x: int, y: int) -> None:
        """
        특정 무기의 레벨을 화면에 그린다.

        매개변수:
            i (int): 무기 인덱스
            x (int): 그리기 시작 x 좌표
            y (int): 그리기 시작 y 좌표
        """
        # 무기 이름 그리기
        self.font.draw_text(x + 16, y, WEAPON_NAMES[i])
        # 무기 아이콘 그리기
        px.blt(x + 24, y, 0, i * 16, 224, 16, 8)

        # 무기 레벨 표시 그리기
        j = 0
        while j <= self.game_vars.weapon_levels[i]:
            # 활성화된 레벨 표시
            px.blt(x + (j * 8), y + 8, 0, 32, 232, 8, 8)
            j += 1
        while j <= MAX_WEAPON_LEVEL:
            # 비활성화된 레벨 표시
            px.blt(x + (j * 8), y + 8, 0, 40, 232, 8, 8)
            j += 1

    def draw(self) -> None:
        """
        HUD를 화면에 그린다.
        """
        # 상단 및 하단 배경 그리기
        px.rect(0, 0, 256, 16, 1)
        px.rect(0, 176, 256, 16, 1)

        # 상단 정보 그리기
        # 1UP 점수
        self.font.draw_text(24, 0, "1UP")
        self.font.draw_text(16, 8, f"{self.game_vars.score:06}")

        # 최고 점수
        self.font.draw_text(96, 0, "HI-SCORE")
        self.font.draw_text(104, 8, f"{self.game_vars.hi_score:06}")

        # 현재 무기 정보
        self.font.draw_text(176, 0, "ARM")
        self.font.draw_text(176, 8, WEAPON_NAMES[self.game_vars.current_weapon])
        px.blt(184, 8, 0, self.game_vars.current_weapon * 16, 224, 16, 8)

        # 생명 수 표시
        px.blt(216, 0, 0, 0, 4, 16, 8, 0)
        self.font.draw_text(224, 8, f"{self.game_vars.lives}")

        # 하단 정보 그리기
        self.font.draw_text(16, 176, "ARM")
        self.font.draw_text(16, 184, "LVL")

        # 무기 레벨 정보
        for i in range(MAX_WEAPONS):
            self.draw_weapon_level(i, 56 + (64 * i), 176)
