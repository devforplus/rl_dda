import json
import time
import csv
import os
from typing import Optional


# TensorBoard 대체용 CSV 로거
class SimpleCSVLogger:
    """게임 메트릭을 CSV 파일로 로깅하는 클래스"""

    def __init__(self, log_dir: str = "runs/game_logs", enabled: bool = True):
        self.enabled = enabled
        self.step_counter = 0

        if self.enabled:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            os.makedirs(log_dir, exist_ok=True)
            self.log_file = f"{log_dir}/csv_session_{timestamp}.csv"

            # CSV 헤더 작성
            with open(self.log_file, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["step", "timestamp", "metric", "value"])

            print(f"[CSV_LOGGER] Logging enabled to: {self.log_file}")
        else:
            self.log_file = None
            print("[CSV_LOGGER] Disabled")

    def add_scalar(self, tag: str, value: float, step: int):
        """메트릭 값을 CSV 파일에 추가"""
        if not self.enabled or not self.log_file:
            return

        timestamp = time.time()
        with open(self.log_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([step, timestamp, tag, value])


# TensorFlow + TensorBoard 사용 시도
try:
    import tensorflow as tf

    # TensorBoard가 함께 설치되었는지 확인
    try:
        tf.summary.create_file_writer
        TENSORBOARD_AVAILABLE = True
        print(f"[TENSORBOARD] TensorFlow {tf.__version__} with TensorBoard available")
    except AttributeError:
        TENSORBOARD_AVAILABLE = False
        print(
            f"[TENSORBOARD] TensorFlow {tf.__version__} found but TensorBoard unavailable"
        )
except ImportError:
    TENSORBOARD_AVAILABLE = False
    print("[TENSORBOARD] TensorFlow not available, using CSV fallback")


class TensorBoardLogger:
    """TensorFlow + TensorBoard를 사용한 게임 메트릭 로거"""

    def __init__(self, log_dir: str = "runs/game_logs", enabled: bool = True):
        self.enabled = enabled
        self.step_counter = 0

        if self.enabled and TENSORBOARD_AVAILABLE:
            # TensorBoard 사용
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.log_dir = f"{log_dir}/tb_session_{timestamp}"

            try:
                # TensorBoard summary writer 초기화
                self.writer = tf.summary.create_file_writer(self.log_dir)
                self.csv_logger = None
                print(f"[TENSORBOARD] Logging enabled to: {self.log_dir}")
                print(f"[TENSORBOARD] View with: tensorboard --logdir {log_dir}")
            except Exception as e:
                print(f"[TENSORBOARD] Failed to initialize: {e}")
                print("[TENSORBOARD] Falling back to CSV logging")
                self.writer = None
                self.csv_logger = SimpleCSVLogger(log_dir, enabled)
        elif self.enabled:
            # CSV 로거 사용
            self.writer = None
            self.csv_logger = SimpleCSVLogger(log_dir, enabled)
        else:
            self.writer = None
            self.csv_logger = None
            print("[LOGGER] Disabled")

    def log_json_event(self, json_str: str) -> None:
        """JSON 형태의 게임 이벤트를 파싱하여 메트릭으로 변환"""
        if not self.enabled:
            return

        try:
            data = json.loads(json_str)
            event_type = data.get("type")
            event_name = data.get("event")
            event_data = data.get("data", {})

            if event_type == "event" and event_name == "frame_collected":
                self._log_player_metrics(event_data)
            elif event_type == "entity":
                self._log_entity_event(event_name, event_data)

        except Exception as e:
            pass  # Silent fail

    def _log_player_metrics(self, data):
        """플레이어 메트릭 로깅"""
        if "player" in data:
            player = data["player"]
            self._add_scalar("Player/Lives", player.get("lives", 0))
            self._add_scalar("Player/Score", player.get("score", 0))

            if "hp" in player:
                hp = player["hp"]
                current_hp = hp.get("current", 0)
                max_hp = hp.get("max", 1)
                self._add_scalar("Player/Current_HP", current_hp)
                self._add_scalar(
                    "Player/HP_Ratio", current_hp / max_hp if max_hp > 0 else 0
                )

    def _log_entity_event(self, event_name, data):
        """엔티티 이벤트 로깅"""
        if event_name in ["enemy_created", "boss_created"]:
            self._add_scalar("Entities/Created_Total", 1)
        elif event_name == "enemy_destroyed":
            self._add_scalar("Entities/Destroyed_Total", 1)
            reason = data.get("reason", "unknown")
            if reason == "killed_by_player":
                self._add_scalar("Entities/Killed_By_Player", 1)

    def _add_scalar(self, tag: str, value: float):
        """메트릭을 TensorBoard 또는 CSV에 로깅"""
        if self.writer and TENSORBOARD_AVAILABLE:
            with self.writer.as_default():
                tf.summary.scalar(tag, value, step=self.step_counter)
                self.writer.flush()
        elif self.csv_logger:
            self.csv_logger.add_scalar(tag, value, self.step_counter)

    def increment_step(self):
        """스텝 카운터 증가"""
        self.step_counter += 1

    def close(self):
        """로거 종료"""
        if self.writer and TENSORBOARD_AVAILABLE:
            self.writer.close()
            print(
                f"[TENSORBOARD] Session completed. View with: tensorboard --logdir {os.path.dirname(self.log_dir)}"
            )
        elif self.csv_logger:
            print(
                f"[CSV_LOGGER] Session completed. Log saved to: {self.csv_logger.log_file}"
            )


# 전역 로거 인스턴스
_logger: Optional[TensorBoardLogger] = None


def init_tensorboard(enabled: bool = True) -> TensorBoardLogger:
    """TensorBoard/CSV 로거 초기화"""
    global _logger
    _logger = TensorBoardLogger(enabled=enabled)
    return _logger


def log_to_tensorboard(json_str: str):
    """JSON 이벤트를 로거에 전송"""
    if _logger:
        _logger.log_json_event(json_str)
        _logger.increment_step()
