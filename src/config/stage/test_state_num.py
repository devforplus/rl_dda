from config.stage.stage_num import StageNum, FINAL_STAGE


def test_final_stage():
    """
    FINAL_STAGE 유효성 검증 테스트

    이 테스트는 FINAL_STAGE가 StageNum 열거형에 포함되어 있는지 확인합니다.
    이를 통해 FINAL_STAGE가 의도치 않게 다른 타입(예: 정수값)으로 변경되는 것을 방지하고,
    스테이지 번호의 일관성을 유지합니다.

    검증 내용:
    - FINAL_STAGE가 StageNum 멤버인지 확인
    """
    assert FINAL_STAGE in StageNum
