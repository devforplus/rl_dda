"""
리플레이 녹화 스크립트

학습된 PPO 모델의 플레이를 JSON 형식으로 녹화하여 저장합니다.
웹 데모에서 재생 가능한 형태로 저장됩니다.

사용법:
    # 단일 모델 녹화
    rye run python replay_recorder.py --model-path "src/src/models/ppo/stages/고급-공격-중심-skill-1.0/master.pth" --skill-level 1.0 --output "replays/master_replay.json"

    # 모든 모델 자동 녹화
    rye run python replay_recorder.py --record-all
"""

import sys
import os
import argparse
import json
from datetime import datetime
from typing import List, Dict, Any

# Windows 콘솔 인코딩 설정
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except:
        pass

# 프로젝트 루트를 Python 경로에 추가
current_dir = os.path.dirname(__file__)
project_root = os.path.join(current_dir, "src")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"[INFO] 프로젝트 루트 경로: {project_root}")

try:
    import torch
    import pyxel as px
    from rl import PPOAgent, GameEnvironment
    from main import App

    print("[OK] 필수 모듈 임포트 성공")
except ImportError as e:
    print(f"[ERROR] 모듈 임포트 실패: {e}")
    print("pip install torch pyxel로 필요한 패키지를 설치해주세요.")
    sys.exit(1)


class ReplayRecorder:
    """리플레이 녹화 클래스"""

    def __init__(self, max_steps: int = 2000):
        self.frames: List[Dict[str, Any]] = []
        self.max_steps = max_steps
        self.metadata: Dict[str, Any] = {}
        self.recording = True

    def add_frame(self, game_instance, action_id: int, step: int):
        """프레임 데이터 추가"""
        if not self.recording or step >= self.max_steps:
            return

        try:
            frame_data = {
                "step": step,
                "action": action_id,
            }

            # 게임 상태 추출
            if game_instance and hasattr(game_instance, "game") and game_instance.game:
                game = game_instance.game

                # 플레이어 정보
                if hasattr(game, "state") and game.state:
                    player = getattr(game.state, "player", None)
                    if player:
                        frame_data["player"] = {
                            "x": round(getattr(player, "x", 0), 2),
                            "y": round(getattr(player, "y", 0), 2),
                            "hp": getattr(player, "current_hp", 0),
                            "invincible": getattr(player, "invincible", False),
                        }

                    # 적 정보
                    enemies = getattr(game.state, "enemies", [])
                    frame_data["enemies"] = [
                        {
                            "x": round(getattr(enemy, "x", 0), 2),
                            "y": round(getattr(enemy, "y", 0), 2),
                            "type": type(enemy).__name__,
                        }
                        for enemy in enemies[:20]  # 최대 20개만
                    ]

                    # 적 총알 정보
                    enemy_shots = []
                    for enemy in enemies:
                        if hasattr(enemy, "shots"):
                            for shot in enemy.shots[:5]:  # 적당 최대 5개
                                enemy_shots.append(
                                    {
                                        "x": round(getattr(shot, "x", 0), 2),
                                        "y": round(getattr(shot, "y", 0), 2),
                                    }
                                )
                    frame_data["enemy_bullets"] = enemy_shots[:50]  # 전체 최대 50개

                    # 플레이어 총알 정보
                    player_shots = getattr(game.state, "player_shots", [])
                    frame_data["player_bullets"] = [
                        {
                            "x": round(getattr(shot, "x", 0), 2),
                            "y": round(getattr(shot, "y", 0), 2),
                        }
                        for shot in player_shots[:30]  # 최대 30개
                    ]

                    # 파워업 정보
                    powerups = getattr(game.state, "powerups", [])
                    frame_data["powerups"] = [
                        {
                            "x": round(getattr(pu, "x", 0), 2),
                            "y": round(getattr(pu, "y", 0), 2),
                            "type": getattr(pu, "type", "unknown"),
                        }
                        for pu in powerups[:10]  # 최대 10개
                    ]

                # 게임 변수
                if hasattr(game, "game_vars"):
                    game_vars = game.game_vars
                    frame_data["score"] = getattr(game_vars, "score", 0)
                    frame_data["kills"] = getattr(game_vars, "kills", 0)
                    frame_data["lives"] = getattr(game_vars, "lives", 0)

            self.frames.append(frame_data)

        except Exception as e:
            print(f"[WARN] 프레임 {step} 기록 실패: {e}")

    def finalize_metadata(self, model_name: str, skill_level: float, game_instance):
        """메타데이터 완성"""
        final_score = 0
        final_kills = 0
        final_lives = 0

        try:
            if (
                game_instance
                and hasattr(game_instance, "game")
                and game_instance.game
                and hasattr(game_instance.game, "game_vars")
            ):
                game_vars = game_instance.game.game_vars
                final_score = getattr(game_vars, "score", 0)
                final_kills = getattr(game_vars, "kills", 0)
                final_lives = getattr(game_vars, "lives", 0)
        except:
            pass

        self.metadata = {
            "model": model_name,
            "skill_level": skill_level,
            "total_steps": len(self.frames),
            "final_score": final_score,
            "total_kills": final_kills,
            "final_lives": final_lives,
            "recorded_at": datetime.now().isoformat(),
            "game_fps": 60,
            "game_width": 256,
            "game_height": 192,
        }

    def save(self, output_path: str):
        """JSON으로 저장"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        replay_data = {"metadata": self.metadata, "frames": self.frames}

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(replay_data, f, indent=2, ensure_ascii=False)

        file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
        print(f"[SAVE] 리플레이 저장 완료: {output_path}")
        print(f"       프레임 수: {len(self.frames)}")
        print(f"       파일 크기: {file_size_mb:.2f} MB")


class RecordingAgent:
    """녹화 기능이 있는 에이전트"""

    def __init__(
        self,
        ppo_agent: PPOAgent,
        environment: GameEnvironment,
        skill_level: float,
        recorder: ReplayRecorder,
    ):
        self.ppo_agent = ppo_agent
        self.environment = environment
        self.skill_level = skill_level
        self.recorder = recorder
        self.connected_game = None
        self.step_count = 0
        self.save_callback = None  # 저장 콜백

    def connect_game(self, game_instance):
        """게임 인스턴스 연결"""
        self.connected_game = game_instance
        print(f"[OK] 녹화 에이전트가 게임에 연결되었습니다.")

    def select_action(self, state=None) -> int:
        """액션 선택 및 녹화"""
        if self.connected_game is None:
            return 4

        try:
            # 게임 상태 추출
            game_log_data = self.environment.extract_game_log_data(
                self.connected_game, self.skill_level
            )

            # 모델로 액션 선택
            state_vector = game_log_data.to_state_vector()
            state_tensor = (
                torch.FloatTensor(state_vector).unsqueeze(0).to(self.ppo_agent.device)
            )

            with torch.no_grad():
                action, _, _, _ = self.ppo_agent.network.get_action_and_value(
                    state_tensor
                )

            action_id = action.cpu().item()

            # 프레임 녹화
            self.recorder.add_frame(self.connected_game, action_id, self.step_count)
            self.step_count += 1

            # 진행 상황 표시
            if self.step_count % 100 == 0:
                try:
                    if (
                        self.connected_game
                        and hasattr(self.connected_game, "game")
                        and self.connected_game.game
                        and hasattr(self.connected_game.game, "game_vars")
                    ):
                        game_vars = self.connected_game.game.game_vars
                        score = getattr(game_vars, "score", 0)
                        kills = getattr(game_vars, "kills", 0)
                        lives = getattr(game_vars, "lives", 0)
                        print(
                            f"[REC] Step {self.step_count} | 점수: {score} | 킬: {kills} | 목숨: {lives}"
                        )
                except:
                    pass

            # 최대 스텝 도달 또는 게임 오버 시 녹화 종료
            if self.step_count >= self.recorder.max_steps or self._is_game_over():
                if self.recorder.recording:  # 한 번만 실행
                    self.recorder.recording = False
                    print(f"[STOP] 녹화 완료 (총 {self.step_count} 스텝)")

                    # 저장 콜백 호출
                    if self.save_callback:
                        self.save_callback()

                    # 게임 종료
                    px.quit()

            return action_id

        except Exception as e:
            print(f"[ERROR] 액션 선택 실패: {e}")
            return 4

    def _is_game_over(self) -> bool:
        """게임 오버 확인"""
        try:
            if (
                self.connected_game
                and hasattr(self.connected_game, "game")
                and self.connected_game.game
                and hasattr(self.connected_game.game, "game_vars")
            ):
                lives = getattr(self.connected_game.game.game_vars, "lives", 1)
                return lives <= 0
        except:
            pass
        return False


def record_replay(
    model_path: str,
    skill_level: float,
    output_path: str,
    max_steps: int = 2000,
    model_name: str = None,
):
    """리플레이 녹화 실행"""
    print("\n" + "=" * 60)
    print("[RECORD] 리플레이 녹화 시작")
    print("=" * 60)
    print(f"[CONFIG] 설정:")
    print(f"   - 모델 경로: {model_path}")
    print(f"   - 스킬 레벨: {skill_level}")
    print(f"   - 출력 경로: {output_path}")
    print(f"   - 최대 스텝: {max_steps}")
    print()

    try:
        # 모델 파일 존재 확인
        if not os.path.exists(model_path):
            print(f"[ERROR] 모델 파일을 찾을 수 없습니다: {model_path}")
            return False

        # 모델 이름 추출
        if model_name is None:
            model_name = os.path.basename(os.path.dirname(model_path))

        print(f"[INIT] PPO 에이전트 초기화 중...")

        # 환경 및 에이전트 초기화
        environment = GameEnvironment()
        ppo_agent = PPOAgent(state_size=161, action_size=10)

        print(f"[LOAD] 모델 로드 중: {model_path}")
        ppo_agent.load_model(model_path)
        print(f"[OK] 모델 로드 완료!")

        # 녹화기 생성
        recorder = ReplayRecorder(max_steps=max_steps)

        # 녹화 에이전트 생성
        print(f"[INIT] 녹화 에이전트 초기화 중...")
        recording_agent = RecordingAgent(ppo_agent, environment, skill_level, recorder)

        # 게임 앱 생성 및 실행
        print(f"[START] 게임 녹화 시작...")
        print()

        game_app = App(agent=recording_agent)

        # 저장을 위한 콜백 설정
        saved = False

        def save_on_quit():
            nonlocal saved
            if not saved:
                print(f"\n[SAVE] 리플레이 저장 중...")
                recorder.finalize_metadata(
                    model_name, skill_level, recording_agent.connected_game
                )
                recorder.save(output_path)
                saved = True

        # 녹화 에이전트에 저장 콜백 설정
        recording_agent.save_callback = save_on_quit

        # Pyxel 게임 실행
        try:
            px.run(game_app.update, game_app.draw)
        except SystemExit:
            pass  # px.quit() 호출로 인한 정상 종료
        finally:
            # 저장되지 않았다면 여기서 저장
            save_on_quit()

        print(f"[OK] 녹화 완료!")
        return True

    except KeyboardInterrupt:
        print("\n[EXIT] 사용자에 의해 중단되었습니다.")
        return False
    except Exception as e:
        print(f"[ERROR] 녹화 중 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        return False


def record_all_models():
    """모든 모델 자동 녹화"""
    models = [
        {
            "name": "beginner",
            "path": "src/src/models/ppo/stages/초급-생존-중심-skill-0.1/beginner.pth",
            "skill": 0.1,
            "output": "replays/beginner_skill_0.1.json",
        },
        {
            "name": "medium",
            "path": "src/src/models/ppo/stages/중급-균형-skill-0.5/medium.pth",
            "skill": 0.5,
            "output": "replays/medium_skill_0.5.json",
        },
        {
            "name": "master",
            "path": "src/src/models/ppo/stages/고급-공격-중심-skill-1.0/master.pth",
            "skill": 1.0,
            "output": "replays/master_skill_1.0.json",
        },
    ]

    print("\n" + "=" * 60)
    print("[AUTO] 모든 모델 자동 녹화")
    print("=" * 60)
    print(f"총 {len(models)}개 모델을 녹화합니다.")
    print()

    results = []
    for i, model in enumerate(models, 1):
        print(f"\n[{i}/{len(models)}] {model['name']} 모델 녹화 중...")
        success = record_replay(
            model_path=model["path"],
            skill_level=model["skill"],
            output_path=model["output"],
            model_name=model["name"],
        )
        results.append((model["name"], success))

    # 결과 요약
    print("\n" + "=" * 60)
    print("[SUMMARY] 녹화 결과 요약")
    print("=" * 60)
    for name, success in results:
        status = "[OK]" if success else "[FAIL]"
        print(f"{status} {name}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="PPO 모델 리플레이 녹화")
    parser.add_argument(
        "--model-path",
        type=str,
        help="모델 파일 경로",
    )
    parser.add_argument(
        "--skill-level",
        type=float,
        help="스킬 레벨 (0.0-1.0)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="출력 JSON 파일 경로",
    )
    parser.add_argument(
        "--max-steps",
        type=int,
        default=2000,
        help="최대 녹화 스텝 수 (기본: 2000)",
    )
    parser.add_argument(
        "--record-all",
        action="store_true",
        help="모든 모델 자동 녹화",
    )

    args = parser.parse_args()

    if args.record_all:
        record_all_models()
    elif args.model_path and args.skill_level is not None and args.output:
        record_replay(
            model_path=args.model_path,
            skill_level=args.skill_level,
            output_path=args.output,
            max_steps=args.max_steps,
        )
    else:
        parser.print_help()
        print(
            "\n[ERROR] --record-all 또는 --model-path, --skill-level, --output을 지정해주세요."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
