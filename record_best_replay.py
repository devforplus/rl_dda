"""
베스트 플레이 녹화 시스템

목표 생존 시간을 달성한 최고의 리플레이를 자동으로 찾아 저장합니다.
"""

import os
import sys

# Windows 콘솔 UTF-8 인코딩 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
import json
import pyxel as px
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
import time
import threading

# 프로젝트 루트의 src를 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from main import App
from rl.ppo_agent import PPOAgent
from rl.data_types import GameLogData


class BestReplayRecorder:
    """베스트 플레이를 찾기 위한 녹화기"""

    def __init__(
        self, min_steps: int, max_steps: Optional[int] = None, max_attempts: int = 50
    ):
        """
        Args:
            min_steps: 최소 생존 목표 스텝
            max_steps: 최대 생존 목표 스텝 (None이면 무제한)
            max_attempts: 최대 시도 횟수
        """
        self.min_steps = min_steps
        self.max_steps = max_steps
        self.max_attempts = max_attempts

        # 현재 에피소드 데이터
        self.current_frames = []
        self.current_survival_steps = 0
        self.current_metadata = {}

        # 베스트 기록
        self.best_frames = []
        self.best_survival_steps = 0
        self.best_metadata = {}

        # 통계
        self.attempt_count = 0
        self.total_steps_played = 0
        self.survival_times = []

        # 제어 플래그
        self.recording = True
        self.episode_done = False

    def start_new_episode(self):
        """새 에피소드 시작"""
        self.current_frames = []
        self.current_survival_steps = 0
        self.current_metadata = {}
        self.episode_done = False

    def add_frame(self, game_log: GameLogData, action: int):
        """프레임 추가"""
        if not self.recording or self.episode_done:
            return

        # 플레이어 위치 찾기 (entities 리스트에서 entity_type == 0)
        player_entity = next((e for e in game_log.entities if e.entity_type == 0), None)

        frame_data = {
            "step": len(self.current_frames),
            "player": {
                "x": player_entity.x if player_entity else 0,
                "y": player_entity.y if player_entity else 0,
                "hp": game_log.player_state.hp,
                "lives": game_log.player_state.lives,
            },
            "enemies": [
                {"x": e.x, "y": e.y} for e in game_log.entities if e.entity_type == 1
            ],
            "bullets": [
                {"x": e.x, "y": e.y} for e in game_log.entities if e.entity_type == 2
            ],
            "score": game_log.current_score,
            "action": action,
        }
        self.current_frames.append(frame_data)
        self.current_survival_steps = len(self.current_frames)

    def finish_episode(self):
        """에피소드 종료 처리"""
        if self.episode_done:
            return

        self.episode_done = True
        self.attempt_count += 1
        self.total_steps_played += self.current_survival_steps
        self.survival_times.append(self.current_survival_steps)

        # 목표 달성 확인
        meets_min = self.current_survival_steps >= self.min_steps
        meets_max = (
            self.max_steps is None or self.current_survival_steps <= self.max_steps
        )

        if meets_min and meets_max:
            # 목표 달성!
            self.best_frames = self.current_frames.copy()
            self.best_survival_steps = self.current_survival_steps
            self.recording = False  # 녹화 완전 종료
            return True

        # 베스트 기록 갱신 (목표 미달성이지만 이전보다 좋은 경우)
        if self.current_survival_steps > self.best_survival_steps:
            self.best_frames = self.current_frames.copy()
            self.best_survival_steps = self.current_survival_steps

        # 최대 시도 횟수 도달
        if self.attempt_count >= self.max_attempts:
            print(f"\n[WARN] 최대 시도 횟수 도달 ({self.max_attempts}회)")
            print(
                f"[INFO] 베스트 기록으로 저장합니다 (생존: {self.best_survival_steps} 스텝)"
            )
            self.recording = False
            return True

        return False

    def get_stats_string(self) -> str:
        """현재 통계 문자열"""
        avg_survival = (
            sum(self.survival_times) / len(self.survival_times)
            if self.survival_times
            else 0
        )

        target_str = f"{self.min_steps}+"
        if self.max_steps:
            target_str = f"{self.min_steps}-{self.max_steps}"

        return (
            f"시도: {self.attempt_count}/{self.max_attempts} | "
            f"목표: {target_str} | "
            f"현재: {self.current_survival_steps} | "
            f"베스트: {self.best_survival_steps} | "
            f"평균: {avg_survival:.0f}"
        )

    def save(self, output_path: str, model_name: str, skill_level: float):
        """베스트 리플레이 저장"""
        if not self.best_frames:
            print("[ERROR] 저장할 리플레이가 없습니다")
            return

        # 출력 디렉토리 생성
        output_dir = os.path.dirname(output_path)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        # 메타데이터 구성
        replay_data = {
            "metadata": {
                "model_name": model_name,
                "skill_level": skill_level,
                "total_steps": self.best_survival_steps,
                "total_attempts": self.attempt_count,
                "average_survival": sum(self.survival_times) / len(self.survival_times)
                if self.survival_times
                else 0,
                "target_min_steps": self.min_steps,
                "target_max_steps": self.max_steps,
                "timestamp": time.strftime("%Y%m%d_%H%M%S"),
            },
            "frames": self.best_frames,
        }

        # JSON 저장
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(replay_data, f, indent=2, ensure_ascii=False)

        file_size = os.path.getsize(output_path) / 1024  # KB
        print(f"\n[OK] 리플레이 저장 완료: {output_path}")
        print(f"     - 생존 시간: {self.best_survival_steps} 스텝")
        print(f"     - 총 시도: {self.attempt_count}회")
        print(f"     - 파일 크기: {file_size:.1f} KB")


class BestPlayAgent:
    """베스트 플레이를 찾기 위한 에이전트"""

    def __init__(
        self, model: PPOAgent, recorder: BestReplayRecorder, skill_level: float
    ):
        self.model = model
        self.recorder = recorder
        self.skill_level = skill_level
        self.connected_game: Optional[App] = None
        self.step_count = 0

        # Environment import (여기서 지연 import)
        from rl.environment import GameEnvironment

        self.environment = GameEnvironment()

    def select_action(self, state=None) -> int:
        """main.py에서 호출되는 액션 선택 메서드"""
        if self.connected_game is None:
            return 4  # 기본값: 정지

        try:
            # 게임 상태 추출
            game_log = self.environment.extract_game_log_data(
                self.connected_game, self.skill_level
            )

            # 플레이어 생존 확인 (lives가 0이면 게임 오버)
            if game_log.player_state.lives <= 0:
                # 이미 처리된 에피소드면 스킵
                if not self.recorder.episode_done:
                    # 게임 오버 - 에피소드 종료
                    should_stop = self.recorder.finish_episode()

                    if should_stop:
                        # 목표 달성 또는 최대 시도 도달 - 게임 종료
                        self.recorder.recording = False
                        try:
                            px.quit()
                        except:
                            pass
                    else:
                        # 다음 에피소드 시작 - 게임 재시작
                        print(f"[INFO] {self.recorder.get_stats_string()}")
                        self.recorder.start_new_episode()
                        self.step_count = 0

                        # 게임 재시작
                        if hasattr(self.connected_game, "game") and hasattr(
                            self.connected_game.game, "restart_game"
                        ):
                            self.connected_game.game.restart_game()

                return 4  # 정지

            # 상태 벡터 변환
            state_vector = game_log.to_state_vector()

            # PPO 모델로 액션 선택
            action = self.model.get_action(game_log)

            # 프레임 기록
            self.recorder.add_frame(game_log, action)
            self.step_count += 1

            return action

        except Exception as e:
            print(f"[ERROR] 액션 선택 중 오류: {e}")
            return 4  # 오류 시 정지


def record_best_replay(
    model_path: str,
    skill_level: float,
    output_path: str,
    min_steps: int,
    max_steps: Optional[int] = None,
    max_attempts: int = 50,
):
    """
    베스트 리플레이 녹화

    Args:
        model_path: PPO 모델 경로
        skill_level: 스킬 레벨 (0.1 ~ 1.0)
        output_path: 출력 JSON 경로
        min_steps: 최소 목표 생존 스텝
        max_steps: 최대 목표 생존 스텝 (None이면 무제한)
        max_attempts: 최대 시도 횟수
    """
    print("=" * 60)
    print(f"[INFO] 베스트 플레이 녹화 시작")
    print(f"       모델: {os.path.basename(model_path)}")
    print(f"       스킬: {skill_level}")

    target_str = f"{min_steps}+"
    if max_steps:
        target_str = f"{min_steps}-{max_steps}"
    print(f"       목표: {target_str} 스텝")
    print(f"       최대 시도: {max_attempts}회")
    print("=" * 60)

    # 1. PPO 모델 로드
    print(f"\n[LOAD] PPO 모델 로드 중...")
    if not os.path.exists(model_path):
        print(f"[ERROR] 모델 파일을 찾을 수 없습니다: {model_path}")
        return

    model = PPOAgent(
        state_size=161,  # GameLogData.to_state_vector() 크기
        action_size=10,  # 액션 공간 크기
        learning_rate=3e-4,
    )

    try:
        model.load_model(model_path)
        print(f"[OK] 모델 로드 완료")
    except Exception as e:
        print(f"[ERROR] 모델 로드 실패: {e}")
        return

    # 2. 녹화기 및 에이전트 생성
    recorder = BestReplayRecorder(
        min_steps=min_steps, max_steps=max_steps, max_attempts=max_attempts
    )
    agent = BestPlayAgent(model, recorder, skill_level)
    recorder.start_new_episode()

    # 3. 게임 실행 (별도 스레드)
    print(f"\n[START] 게임 시작 (목표 달성까지 자동 재시작)")
    print(f"        게임 창을 닫지 마세요!\n")

    game_app = App(agent=agent)
    agent.connected_game = game_app

    # 에이전트에 게임 연결 (connect_game 메서드가 있으면 호출)
    if hasattr(agent, "connect_game"):
        agent.connect_game(game_app)

    # 게임 스레드 시작
    game_thread = threading.Thread(
        target=lambda: px.run(game_app.update, game_app.draw)
    )
    game_thread.daemon = True
    game_thread.start()

    # 녹화 완료 대기
    last_attempt = 0
    while recorder.recording:
        time.sleep(0.5)

        # 진행 상황 업데이트 (새 시도마다)
        if recorder.attempt_count > last_attempt:
            last_attempt = recorder.attempt_count

    # 추가 대기 (게임 종료 처리)
    time.sleep(1)

    # 게임 종료
    try:
        px.quit()
    except:
        pass

    # 4. 저장
    print(f"\n[SAVE] 베스트 리플레이 저장 중...")
    model_name = os.path.basename(os.path.dirname(model_path))
    recorder.save(output_path, model_name, skill_level)


def record_all_best_replays():
    """모든 모델의 베스트 리플레이 녹화"""

    models = [
        {
            "name": "beginner",
            "path": "src/src/models/ppo/stages/초급-생존-중심-skill-0.1/beginner.pth",
            "skill": 0.1,
            "min_steps": 550,  # 그래프 분석: ~600 스텝 달성 가능
            "max_steps": 700,
            "max_attempts": 30,
            "output": "web/agentic-game/replays/best_beginner_skill_0.1.json",
        },
        {
            "name": "medium",
            "path": "src/src/models/ppo/stages/중급-균형-skill-0.5/medium.pth",
            "skill": 0.5,
            "min_steps": 850,  # 그래프 분석: ~900 스텝 달성 가능
            "max_steps": 1000,
            "max_attempts": 30,
            "output": "web/agentic-game/replays/best_medium_skill_0.5.json",
        },
        {
            "name": "master",
            "path": "src/src/models/ppo/stages/고급-공격-중심-skill-1.0/master.pth",
            "skill": 1.0,
            "min_steps": 1100,  # 그래프 분석: ~1100-1200 스텝 달성 가능
            "max_steps": None,  # 무제한
            "max_attempts": 50,
            "output": "web/agentic-game/replays/best_master_skill_1.0.json",
        },
    ]

    print("\n" + "=" * 60)
    print("베스트 플레이 녹화 - 전체 모델")
    print("=" * 60)

    for i, model_info in enumerate(models, 1):
        print(f"\n\n[{i}/{len(models)}] {model_info['name'].upper()} 모델")
        print("-" * 60)

        output_path = model_info["output"]

        record_best_replay(
            model_path=model_info["path"],
            skill_level=model_info["skill"],
            output_path=output_path,
            min_steps=model_info["min_steps"],
            max_steps=model_info.get("max_steps"),
            max_attempts=model_info["max_attempts"],
        )

        print(f"\n[OK] {model_info['name']} 완료!")

        # 다음 모델 전 대기
        if i < len(models):
            print("\n다음 모델 녹화까지 3초 대기...")
            time.sleep(3)

    print("\n" + "=" * 60)
    print("[COMPLETE] 모든 베스트 리플레이 녹화 완료!")
    print("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="베스트 플레이 녹화")
    parser.add_argument("--model-path", type=str, help="PPO 모델 경로")
    parser.add_argument("--skill-level", type=float, help="스킬 레벨 (0.1 ~ 1.0)")
    parser.add_argument("--output", type=str, help="출력 JSON 경로")
    parser.add_argument("--min-steps", type=int, help="최소 목표 생존 스텝")
    parser.add_argument(
        "--max-steps", type=int, default=None, help="최대 목표 생존 스텝"
    )
    parser.add_argument("--max-attempts", type=int, default=50, help="최대 시도 횟수")
    parser.add_argument(
        "--all", action="store_true", help="모든 모델의 베스트 리플레이 녹화"
    )

    args = parser.parse_args()

    if args.all:
        # 전체 모델 녹화
        record_all_best_replays()
    elif args.model_path and args.skill_level and args.output and args.min_steps:
        # 단일 모델 녹화
        record_best_replay(
            model_path=args.model_path,
            skill_level=args.skill_level,
            output_path=args.output,
            min_steps=args.min_steps,
            max_steps=args.max_steps,
            max_attempts=args.max_attempts,
        )
    else:
        print("사용법:")
        print("  # 모든 모델 자동 녹화")
        print("  rye run python record_best_replay.py --all")
        print()
        print("  # 단일 모델 녹화")
        print("  rye run python record_best_replay.py \\")
        print("    --model-path <모델경로> \\")
        print("    --skill-level <스킬> \\")
        print("    --output <출력경로> \\")
        print("    --min-steps <최소스텝> \\")
        print("    [--max-steps <최대스텝>] \\")
        print("    [--max-attempts <최대시도횟수>]")
