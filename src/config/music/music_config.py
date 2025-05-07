from ..stage import StageNum


class MusicConfig:
    """
    음악 관련 설정 클래스

    Attributes:
        stage_music_mapping (dict): 스테이지별 음악 파일 매핑
        special_music_files (dict): 특수 상황 음악 파일 정의
    """

    # 스테이지별 음악 파일 매핑
    stage_music_mapping = {
        StageNum.STAGE_1: "music_stage_1.json",
        StageNum.STAGE_2: "music_vortex.json",
        StageNum.STAGE_3: "music_stage_3.json",
        StageNum.STAGE_4: "music_vortex.json",
        StageNum.STAGE_5: "music_stage_5.json",
    }

    # 특수 상황 음악 파일 정의
    special_music_files = {
        "game_complete": "music_game_complete.json",
        "game_over": "music_game_over.json",
        "boss": "music_boss.json",
        "stage_clear": "music_stage_clear.json",
    }
