from typing import ClassVar
import pyxel as px


class MonospaceBitmapFont:
    """
    고정폭 비트맵 폰트를 처리하는 클래스입니다.

    이 클래스는 고정폭 비트맵 폰트의 그리기 기능을 제공합니다.
    """

    width: ClassVar[int] = 8
    height: ClassVar[int] = 8
    uv_chars_wide: ClassVar[int] = 32  # 이미지 너비당 문자 수
    u_offset: ClassVar[int] = 0
    v_offset: ClassVar[int] = 240

    def __init__(self) -> None:
        """
        MonospaceBitmapFont 클래스의 인스턴스를 초기화합니다.
        """

    def draw_text(self, x: int, y: int, text: str) -> None:
        """
        지정된 위치에 텍스트를 그립니다.

        Args:
            x (int): 텍스트를 그릴 x 좌표
            y (int): 텍스트를 그릴 y 좌표
            text (str): 그릴 텍스트 문자열
        """
        for char in text:
            code = ord(char)
            if code < 32 or code > 95:
                x += self.width
                continue
            code -= 32
            px.blt(
                x,
                y,
                0,
                self.u_offset + (px.floor(code % self.uv_chars_wide) * self.width),
                self.v_offset + (px.floor(code / self.uv_chars_wide) * self.height),
                self.width,
                self.height,
            )
            x += self.width
