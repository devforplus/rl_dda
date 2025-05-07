import pyxel as px

# 입력 인덱스 상수
UP = 0  # 위쪽 방향 입력
DOWN = 1  # 아래쪽 방향 입력
LEFT = 2  # 왼쪽 방향 입력
RIGHT = 3  # 오른쪽 방향 입력
BUTTON_1 = 4  # 버튼 1 입력 (Z, U, 게임패드 A 버튼)
BUTTON_2 = 5  # 버튼 2 입력 (X, 게임패드 B 버튼)
INVINCIBLE = 6  # 무적 모드 토글 입력 (I 키)
COLLECT_DATA = 7  # 데이터 수집 토글 입력 (C 키)


class Input:
    """
    사용자 입력을 처리하는 클래스.

    속성:
        pressing (list): 현재 눌려진 입력 목록
        tapped (list): 현재 프레임에서 눌린 입력 목록
    """

    def __init__(self) -> None:
        """
        입력 처리 초기화.
        """
        self.pressing = []
        self.tapped = []

    def is_pressing(self, i: int) -> bool:
        """
        특정 입력이 현재 눌려져 있는지 확인.

        매개변수:
            i (int): 입력 인덱스

        반환값:
            bool: 입력이 눌려져 있으면 True, 아니면 False
        """
        return i in self.pressing

    def has_tapped(self, i: int) -> bool:
        """
        특정 입력이 현재 프레임에서 눌렸는지 확인.

        매개변수:
            i (int): 입력 인덱스

        반환값:
            bool: 입력이 눌렸으면 True, 아니면 False
        """
        return i in self.tapped

    def update(self) -> None:
        """
        사용자 입력을 업데이트.
        """
        self.pressing.clear()
        self.tapped.clear()

        # 현재 눌려진 입력 처리
        if px.btn(px.KEY_UP) or px.btn(px.KEY_W) or px.btn(px.GAMEPAD1_BUTTON_DPAD_UP):
            self.pressing.append(UP)
        if (
            px.btn(px.KEY_DOWN)
            or px.btn(px.KEY_S)
            or px.btn(px.GAMEPAD1_BUTTON_DPAD_DOWN)
        ):
            self.pressing.append(DOWN)
        if (
            px.btn(px.KEY_LEFT)
            or px.btn(px.KEY_A)
            or px.btn(px.GAMEPAD1_BUTTON_DPAD_LEFT)
        ):
            self.pressing.append(LEFT)
        if (
            px.btn(px.KEY_RIGHT)
            or px.btn(px.KEY_D)
            or px.btn(px.GAMEPAD1_BUTTON_DPAD_RIGHT)
        ):
            self.pressing.append(RIGHT)

        if px.btn(px.KEY_Z) or px.btn(px.KEY_U) or px.btn(px.GAMEPAD1_BUTTON_A):
            self.pressing.append(BUTTON_1)
        if px.btn(px.KEY_X) or px.btn(px.GAMEPAD1_BUTTON_B):
            self.pressing.append(BUTTON_2)

        # 무적 모드 토글 입력
        if px.btn(px.KEY_I):
            self.pressing.append(INVINCIBLE)
            
        # 데이터 수집 토글 입력
        if px.btn(px.KEY_C):
            self.pressing.append(COLLECT_DATA)

        # 현재 프레임에서 눌린 입력 처리
        if (
            px.btnp(px.KEY_UP)
            or px.btnp(px.KEY_W)
            or px.btnp(px.GAMEPAD1_BUTTON_DPAD_UP)
        ):
            self.tapped.append(UP)
        if (
            px.btnp(px.KEY_DOWN)
            or px.btnp(px.KEY_S)
            or px.btnp(px.GAMEPAD1_BUTTON_DPAD_DOWN)
        ):
            self.tapped.append(DOWN)
        if (
            px.btnp(px.KEY_LEFT)
            or px.btnp(px.KEY_A)
            or px.btnp(px.GAMEPAD1_BUTTON_DPAD_LEFT)
        ):
            self.tapped.append(LEFT)
        if (
            px.btnp(px.KEY_RIGHT)
            or px.btnp(px.KEY_D)
            or px.btnp(px.GAMEPAD1_BUTTON_DPAD_RIGHT)
        ):
            self.tapped.append(RIGHT)

        if px.btnp(px.KEY_Z) or px.btnp(px.KEY_U) or px.btnp(px.GAMEPAD1_BUTTON_A):
            self.tapped.append(BUTTON_1)
        if px.btnp(px.KEY_X) or px.btnp(px.GAMEPAD1_BUTTON_B):
            self.tapped.append(BUTTON_2)

        # 무적 모드 토글 입력
        if px.btnp(px.KEY_I):
            self.tapped.append(INVINCIBLE)
            
        # 데이터 수집 토글 입력
        if px.btnp(px.KEY_C, 0, 0):
            self.tapped.append(COLLECT_DATA)
