from abc import ABC, abstractmethod
from itertools import filterfalse
from typing import List, TypeVar, TYPE_CHECKING

import pyxel as px

if TYPE_CHECKING:
    from .sprite import Sprite

T = TypeVar('T', bound='Sprite')

def rect_overlap(
    x1: int, y1: int, w1: int, h1: int, x2: int, y2: int, w2: int, h2: int
) -> bool:
    """
    두 사각형의 겹침 여부를 확인합니다.

    Args:
        x1 (int): 첫 번째 사각형의 x 좌표
        y1 (int): 첫 번째 사각형의 y 좌표
        w1 (int): 첫 번째 사각형의 너비
        h1 (int): 첫 번째 사각형의 높이
        x2 (int): 두 번째 사각형의 x 좌표
        y2 (int): 두 번째 사각형의 y 좌표
        w2 (int): 두 번째 사각형의 너비
        h2 (int): 두 번째 사각형의 높이

    Returns:
        bool: 두 사각형이 겹치면 True, 그렇지 않으면 False
    """
    return x1 < x2 + w2 and x1 + w1 > x2 and y1 < y2 + h2 and y1 + h1 > y2


class Sprite(ABC):
    """
    ## 게임 내 스프라이트 기본 클래스

    스프라이트의 위치, 크기, 그래픽 표현 및 상태 관리를 담당합니다.
    하위 클래스에서 구체적인 동작을 구현해야 합니다.

    ### 속성
    | 속성명 | 타입 | 설명 | 기본값 |
    |--------|------|------|--------|
    | `game_state` | `object` | 게임 상태 객체 | - |
    | `x` | `int` | 스프라이트 x좌표 | 0 |
    | `y` | `int` | 스프라이트 y좌표 | 0 |
    | `w` | `int` | 스프라이트 너비 | 16 |
    | `h` | `int` | 스프라이트 높이 | 16 |
    | `remove` | `bool` | 제거 여부 | `False` |
    | `colour` | `int` | 색상 | 15 |
    | `u` | `int` | 텍스처 u좌표 | 0 |
    | `v` | `int` | 텍스처 v좌표 | 0 |
    | `flip_x` | `bool` | x축 뒤집기 여부 | `False` |
    | `flip_y` | `bool` | y축 뒤집기 여부 | `False` |
    """

    game_state: object  # 게임 상태 객체
    x: int  # 스프라이트 x좌표
    y: int  # 스프라이트 y좌표
    w: int  # 스프라이트 너비
    h: int  # 스프라이트 높이
    remove: bool  # 제거 여부
    colour: int  # 색상
    u: int  # 텍스처 u좌표
    v: int  # 텍스처 v좌표
    flip_x: bool  # x축 뒤집기 여부
    flip_y: bool  # y축 뒤집기 여부

    def __init__(self, game_state: object) -> None:
        """
        스프라이트를 초기화합니다.

        ### 파라미터
        - `game_state` (`object`): 게임 상태 객체
        """
        self.game_state = game_state
        self.x = 0  # 초기 x좌표
        self.y = 0  # 초기 y좌표
        self.w = 16  # 기본 너비
        self.h = 16  # 기본 높이
        self.remove = False  # 초기 제거 여부

        # 그래픽 관련 속성
        self.colour = 15  # 기본 색상 (하양)
        self.u = 0  # 초기 u좌표
        self.v = 0  # 초기 v좌표

        # 뒤집기 관련 속성
        self.flip_x = False  # 초기 x축 뒤집기 여부
        self.flip_y = False  # 초기 y축 뒤집기 여부

    @abstractmethod
    def collided_with(self, other: "Sprite") -> None:
        """
        다른 스프라이트와의 충돌을 처리합니다.

        ### 파라미터
        - `other` (`Sprite`): 충돌한 다른 스프라이트
        """
        pass

    @abstractmethod
    def update(self) -> None:
        """
        스프라이트의 상태를 업데이트합니다.
        """
        pass

    def draw(self):
        """
        스프라이트를 그립니다.

        뒤집기 속성에 따라 적절히 스프라이트를 그립니다.
        """
        w = -self.w if self.flip_x else self.w
        h = -self.h if self.flip_y else self.h
        px.blt(self.x, self.y, 0, self.u, self.v, w, h, 0)

    def update_list(the_list: List[T]) -> None:
        """
        스프라이트 목록을 업데이트합니다.

        ### 파라미터
        - `the_list` (`List[Sprite]`): 스프라이트 목록
        """
        # 목록 내 모든 스프라이트의 상태를 업데이트
        for s in the_list:
            s.update()  # 각 스프라이트의 update 메서드 호출
        # 제거 표시된 스프라이트들을 목록에서 제거
        the_list[:] = filterfalse(
            lambda s: s.remove, the_list
        )  # remove가 True인 스프라이트 필터링

    def draw_list(the_list: List[T]) -> None:
        """
        스프라이트 목록을 그립니다.

        ### 파라미터
        - `the_list` (`List[Sprite]`): 스프라이트 목록
        """
        # 목록 내 모든 스프라이트를 화면에 그림
        for s in the_list:
            s.draw()  # 각 스프라이트의 draw 메서드 호출

    def lists_collide(list_a: List[T], list_b: List[T]) -> None:
        """
        두 스프라이트 목록 간의 충돌을 처리합니다.

        ### 파라미터
        - `list_a` (`List[Sprite]`): 첫 번째 스프라이트 목록
        - `list_b` (`List[Sprite]`): 두 번째 스프라이트 목록
        """
        # list_a의 각 스프라이트에 대해 반복
        for a in list_a:
            if a.remove:  # 제거 표시된 스프라이트는 건너뜀
                continue
            # list_b의 각 스프라이트에 대해 반복
            for b in list_b:
                if b.remove:  # 제거 표시된 스프라이트는 건너뜀
                    continue
                # 두 스프라이트 간의 충돌 여부 확인
                if Sprite.collide(a, b):
                    # 충돌 시 a의 collided_with 메서드 호출
                    a.collided_with(b)
                    # 충돌 시 b의 collided_with 메서드 호출
                    b.collided_with(a)

    def collide_list(spr: T, the_list: List[T]) -> None:
        """
        단일 스프라이트와 목록 간의 충돌을 처리합니다.

        ### 파라미터
        - `spr` (`Sprite`): 단일 스프라이트
        - `the_list` (`List[Sprite]`): 스프라이트 목록
        """
        # spr이 제거 표시된 경우 함수 종료
        if spr.remove:
            return
        # 목록 내 각 스프라이트에 대해 반복
        for a in the_list:
            if a.remove:  # 제거 표시된 스프라이트는 건너뜀
                continue
            # spr과 목록 내 스프라이트 간의 충돌 여부 확인
            if Sprite.collide(spr, a):
                # 충돌 시 spr의 collided_with 메서드 호출
                spr.collided_with(a)
                # 충돌 시 a의 collided_with 메서드 호출
                a.collided_with(spr)

    @staticmethod
    def collide(a: T, b: T) -> bool:
        """
        두 스프라이트 간의 충돌 여부를 확인합니다.

        ### 파라미터
        - `a` (`Sprite`): 첫 번째 스프라이트
        - `b` (`Sprite`): 두 번째 스프라이트

        ### 반환값
        - (`bool`): 충돌 여부
        """
        # 두 스프라이트의 바운딩 박스 겹침 여부를 확인하여 충돌 여부 반환
        return rect_overlap(a.x, a.y, a.w, a.h, b.x, b.y, b.w, b.h)

    def collides_with(self, other: T) -> bool:
        """
        다른 스프라이트와의 충돌 검사

        Args:
            other (Sprite): 충돌 검사할 다른 스프라이트

        Returns:
            bool: 충돌 여부
        """
        return (
            self.x < other.x + other.w
            and self.x + self.w > other.x
            and self.y < other.y + other.h
            and self.y + self.h > other.y
        )

    def on_collision(self, other: T) -> None:
        """
        충돌 시 호출되는 메서드

        Args:
            other (Sprite): 충돌한 다른 스프라이트
        """
        pass

def sprites_update(sprites: List[T]) -> None:
    """
    스프라이트 목록을 업데이트합니다.
    
    Args:
        sprites (List[Sprite]): 업데이트할 스프라이트 목록
    """
    Sprite.update_list(sprites)

def sprites_draw(sprites: List[T]) -> None:
    """
    스프라이트 목록을 그립니다.
    
    Args:
        sprites (List[Sprite]): 그릴 스프라이트 목록
    """
    Sprite.draw_list(sprites)

def sprite_lists_collide(list_a: List[T], list_b: List[T]) -> None:
    """
    두 스프라이트 목록 간의 충돌을 처리합니다.
    
    Args:
        list_a (List[Sprite]): 첫 번째 스프라이트 목록
        list_b (List[Sprite]): 두 번째 스프라이트 목록
    """
    Sprite.lists_collide(list_a, list_b)

def sprite_collide_list(spr: T, the_list: List[T]) -> None:
    """
    단일 스프라이트와 목록 간의 충돌을 처리합니다.
    
    Args:
        spr (Sprite): 단일 스프라이트
        the_list (List[Sprite]): 스프라이트 목록
    """
    Sprite.collide_list(spr, the_list)
