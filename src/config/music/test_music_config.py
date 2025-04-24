from config.music.music_config import MusicConfig
from config.stage import StageNum


def test_stage_music_mapping_structure():
    """
    스테이지별 음악 파일 매핑 구조 테스트

    목적: 스테이지 음악 매핑이 올바른 데이터 구조와 형식으로 정의되었는지 검증
    """
    config = MusicConfig()  # MusicConfig 인스턴스 생성
    assert isinstance(config.stage_music_mapping, dict)  # 매핑이 dict 타입인지 확인
    # 모든 키가 StageNum enum 값인지 확인
    assert all(
        isinstance(stage, StageNum) for stage in config.stage_music_mapping.keys()
    )
    # 모든 값이 문자열이며 .json 확장자를 가지는지 확인
    assert all(
        isinstance(filename, str) and filename.endswith(".json")
        for filename in config.stage_music_mapping.values()
    )


def test_special_music_files_structure():
    """
    특수 상황 음악 파일 구조 테스트

    목적: 특수 상황 음악 파일들이 올바른 데이터 구조와 형식으로 정의되었는지 검증
    """
    config = MusicConfig()  # MusicConfig 인스턴스 생성
    assert isinstance(
        config.special_music_files, dict
    )  # 특수 상황 음악 파일 매핑이 dict 타입인지 확인
    # 모든 키가 문자열인지 확인
    assert all(isinstance(key, str) for key in config.special_music_files.keys())
    # 모든 값이 문자열이며 .json 확장자를 가지는지 확인
    assert all(
        isinstance(filename, str) and filename.endswith(".json")
        for filename in config.special_music_files.values()
    )


def test_music_file_names_are_valid():
    """
    모든 음악 파일 이름 유효성 및 중복 검사 테스트

    목적: 스테이지 음악과 특수 상황 음악 파일 이름이 올바른 형식이며 중복되지 않는지 검증
    """
    config = MusicConfig()
    all_music_files = {
        **config.stage_music_mapping,
        **config.special_music_files,
    }.values()
    assert all(
        isinstance(filename, str) and filename.endswith(".json")
        for filename in all_music_files
    )


def test_stage_music_mapping_coverage():
    """
    스테이지 음악 매핑 커버리지 테스트

    목적: 정의된 모든 스테이지에 대해 음악 파일이 매핑되어 있는지 검증
    """
    config = MusicConfig()  # MusicConfig 인스턴스 생성
    # 정의된 스테이지 집합 생성
    defined_stages = set(config.stage_music_mapping.keys())
    # 모든 StageNum 값들의 집합 생성
    all_stages = set(StageNum)
    # 정의된 스테이지가 모든 스테이지의 부분집합인지 확인
    assert defined_stages.issubset(all_stages)
