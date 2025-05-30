import json
import time
from typing import Optional

try:
    from torch.utils.tensorboard import SummaryWriter
    TENSORBOARD_AVAILABLE = True
except ImportError:
    TENSORBOARD_AVAILABLE = False

class SimpleTensorBoardLogger:
    def __init__(self, log_dir: str = "runs/game_logs", enabled: bool = True):
        self.enabled = enabled and TENSORBOARD_AVAILABLE
        self.step_counter = 0
        
        if self.enabled:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.writer = SummaryWriter(f"{log_dir}/session_{timestamp}")
            print(f"[TENSORBOARD] Logging enabled to: {log_dir}/session_{timestamp}")
        else:
            self.writer = None
            print("[TENSORBOARD] Disabled or TensorBoard not available")
    
    def log_json_event(self, json_str: str) -> None:
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
        if "player" in data:
            player = data["player"]
            self.writer.add_scalar("Player/Lives", player.get("lives", 0), self.step_counter)
            self.writer.add_scalar("Player/Score", player.get("score", 0), self.step_counter)
            
            if "hp" in player:
                hp = player["hp"]
                current_hp = hp.get("current", 0)
                max_hp = hp.get("max", 1)
                self.writer.add_scalar("Player/Current_HP", current_hp, self.step_counter)
                self.writer.add_scalar("Player/HP_Ratio", current_hp / max_hp if max_hp > 0 else 0, self.step_counter)
    
    def _log_entity_event(self, event_name, data):
        if event_name in ["enemy_created", "boss_created"]:
            self.writer.add_scalar("Entities/Created_Total", 1, self.step_counter)
        elif event_name == "enemy_destroyed":
            self.writer.add_scalar("Entities/Destroyed_Total", 1, self.step_counter)
            reason = data.get("reason", "unknown")
            if reason == "killed_by_player":
                self.writer.add_scalar("Entities/Killed_By_Player", 1, self.step_counter)
    
    def increment_step(self):
        self.step_counter += 1
    
    def close(self):
        if self.enabled and self.writer:
            self.writer.close()

# 전역 로거
_tb_logger: Optional[SimpleTensorBoardLogger] = None

def init_tensorboard(enabled: bool = True) -> SimpleTensorBoardLogger:
    global _tb_logger
    _tb_logger = SimpleTensorBoardLogger(enabled=enabled)
    return _tb_logger

def log_to_tensorboard(json_str: str):
    if _tb_logger:
        _tb_logger.log_json_event(json_str)
        _tb_logger.increment_step()
