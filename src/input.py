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
YOLO_DEBUG = 8  # YOLO 디버그 그리기 토글 (D 키)

# 매핑: 키 코드 -> 입력 상수
KEY_MAPPINGS = {
    px.KEY_Z: BUTTON_1,
    px.KEY_X: BUTTON_2,
    px.KEY_UP: UP,
    px.KEY_DOWN: DOWN,
    px.KEY_LEFT: LEFT,
    px.KEY_RIGHT: RIGHT,
    px.KEY_W: UP,
    px.KEY_S: DOWN,
    px.KEY_A: LEFT,
    px.KEY_D: YOLO_DEBUG,
    px.KEY_I: INVINCIBLE,
    px.KEY_C: COLLECT_DATA,
    px.GAMEPAD1_BUTTON_DPAD_UP: UP,
    px.GAMEPAD1_BUTTON_DPAD_DOWN: DOWN,
    px.GAMEPAD1_BUTTON_DPAD_LEFT: LEFT,
    px.GAMEPAD1_BUTTON_DPAD_RIGHT: RIGHT,
    px.GAMEPAD1_BUTTON_A: BUTTON_1,
    px.GAMEPAD1_BUTTON_B: BUTTON_2,
}


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

        # 직접 설정할 수 있는 입력 상태 (RL 에이전트용)
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.fire_pressed = False  # Z키에 해당
        self.z_pressed = False  # Z키 직접 제어용

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
        for key, value in KEY_MAPPINGS.items():
            if (
                px.btn(key)
                or (key == px.KEY_S and self.down_pressed)
                or (key == px.KEY_W and self.up_pressed)
            ):
                self.pressing.append(value)

        if (
            px.btn(px.KEY_Z)
            or px.btn(px.KEY_U)
            or px.btn(px.GAMEPAD1_BUTTON_A)
            or self.fire_pressed
            or self.z_pressed
        ):
            self.pressing.append(BUTTON_1)
        if px.btn(px.KEY_X) or px.btn(px.GAMEPAD1_BUTTON_B):
            self.pressing.append(BUTTON_2)

        # 무적 모드 토글 입력
        if px.btn(px.KEY_I):
            self.pressing.append(INVINCIBLE)

        # 데이터 수집 토글 입력
        if px.btn(px.KEY_C):
            self.pressing.append(COLLECT_DATA)

        # 무적 모드 토글 입력
        if px.btn(px.KEY_D):
            self.pressing.append(YOLO_DEBUG)

        # 현재 프레임에서 눌린 입력 처리
        for key, value in KEY_MAPPINGS.items():
            if px.btnp(key):
                self.tapped.append(value)

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

        # 무적 모드 토글 입력
        if px.btnp(px.KEY_D):
            self.tapped.append(YOLO_DEBUG)
