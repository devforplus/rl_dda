from enum import Enum, auto
from typing import Optional

from states.game_state.game_state_titles import GameStateTitles
from states.game_state.game_state_stage import GameStateStage
from states.game_state.game_state_complete import GameStateComplete
from game_vars import GameVars
from object_detection import GameDetector
from input import COLLECT_DATA


class GameState(Enum):
    """
    게임 상태 열거형.

    게임의 다양한 상태를 정의하며, 각 상태는 게임의 진행 흐름을 결정한다.
    """

    NONE = 0  # 초기/정의되지 않은 상태
    TITLES = auto()  # 타이틀 화면
    STAGE = auto()  # 게임 스테이지 진행 중
    GAME_COMPLETE = auto()  # 게임 완료


class Game:
    """
    게임 메인 클래스.

    속성:
        app: 애플리케이션 객체
        next_state (Optional[GameState]): 다음 게임 상태
        game_vars (GameVars): 게임 변수 관리 객체
        state: 현재 게임 상태 객체
    """

    app: object
    next_state: Optional[GameState]
    game_vars: GameVars
    state: object

    def __init__(self, app) -> None:
        """
        게임 초기화.

        매개변수:
            app: 애플리케이션 객체
        """
        self.app = app
        self.next_state = None
        self.game_vars = GameVars(self)
        # 객체 탐지기 초기화
        self.object_detector = GameDetector()
        # 데이터 수집기 제거
        # self.dataset_collector = DatasetCollector()
        # 초기 게임 상태 설정
        self.state = GameStateTitles(self)
        # self.state = GameStateStage(self)
        # self.state = GameStateComplete(self)

    def go_to_titles(self) -> None:
        """타이틀 화면으로 전환."""
        self.next_state = GameState.TITLES

    def go_to_new_game(self) -> None:
        """새 게임 시작."""
        self.game_vars.new_game()
        self.next_state = GameState.STAGE

    def go_to_continue(self) -> None:
        """게임 계속 진행."""
        self.game_vars.continue_game()
        self.next_state = GameState.STAGE

    def go_to_game_complete(self) -> None:
        """게임 완료 상태로 전환."""
        self.next_state = GameState.GAME_COMPLETE

    def go_to_next_stage(self) -> None:
        """
        다음 스테이지로 진행.

        스테이지가 더 없으면 게임 완료 상태로 전환.
        """
        if self.game_vars.go_to_next_stage():
            self.next_state = GameState.STAGE
        else:
            self.go_to_game_complete()

    def switch_state(self) -> None:
        """게임 상태 전환 처리."""
        new_state = None
        if self.next_state == GameState.TITLES:
            new_state = GameStateTitles
        elif self.next_state == GameState.STAGE:
            new_state = GameStateStage
        elif self.next_state == GameState.GAME_COMPLETE:
            new_state = GameStateComplete
        else:
            return

        # 현재 상태 종료 처리 후 새로운 상태로 전환
        self.state.on_exit()
        self.state = new_state(self)
        self.next_state = None

    def update(self) -> None:
        """게임 상태 업데이트."""
        if self.next_state is not None:
            self.switch_state()
        self.state.update()
        # C 키 데이터 수집 토글 제거
        # if COLLECT_DATA in self.app.input.tapped:
        #     self.toggle_data_collection()
        # 객체 탐지 수행 (스테이지 상태일 때만)
        if isinstance(self.state, GameStateStage):
            # frame = self.dataset_collector.capture_screen()
            frame = None
            detections, frame = self.object_detector.detect_objects(frame, self.state)
            self.object_detector.draw_detections(frame, detections)
            # 데이터 수집 업데이트 제거
            # self.dataset_collector.update(detections)

    def draw(self) -> None:
        """게임 상태 그리기."""
        self.state.draw()

    def toggle_data_collection(self) -> None:
        """데이터 수집 시작/중지 토글"""
        pass
