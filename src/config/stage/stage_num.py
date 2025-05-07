from enum import IntEnum, auto


# 스테이지 번호 열거형 정의
class StageNum(IntEnum):
    """게임 스테이지 번호 정의"""

    STAGE_1 = auto()  # 스테이지 1
    STAGE_2 = auto()  # 소용돌이 스테이지
    STAGE_3 = auto()  # 스테이지 3
    STAGE_4 = auto()  # 소용돌이 스테이지
    STAGE_5 = auto()  # 스테이지 5


# 최종 스테이지 정의
FINAL_STAGE = StageNum.STAGE_5
