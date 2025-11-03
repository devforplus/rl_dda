"""
학습된 PPO 모델이 게임을 플레이하는 것을 시각적으로 확인하는 스크립트

사용법:
    python watch_trained_model.py --model-path "src/src/models/ppo/stages/고급-공격-중심-skill-1.0/master.pth"

선택적 인자:
    --skill-level: 모델이 사용할 실력값 (0.0-1.0, 기본값: 1.0)
    --model-path: 로드할 모델 파일 경로 (기본값: 위 경로)
"""

import sys
import os
import argparse

# Windows 콘솔 인코딩 설정 (이모지 출력 지원)
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


class ModelPlayerAgent:
    """학습된 모델을 사용하여 게임을 플레이하는 에이전트"""

    def __init__(
        self, ppo_agent: PPOAgent, environment: GameEnvironment, skill_level: float
    ):
        self.ppo_agent = ppo_agent
        self.environment = environment
        self.skill_level = skill_level
        self.connected_game = None

        # 통계 (선택적)
        self.step_count = 0
        self.total_score = 0

        print(f"[OK] 모델 플레이어 에이전트 초기화 완료 (실력값: {skill_level})")

    def connect_game(self, game_instance):
        """게임 인스턴스 연결"""
        self.connected_game = game_instance
        print(f"[OK] 에이전트가 게임에 연결되었습니다.")

    def select_action(self, state=None) -> int:
        """게임에서 호출되는 액션 선택 메서드"""
        if self.connected_game is None:
            return 4  # 기본값: 정지

        try:
            # 게임 상태 추출
            game_log_data = self.environment.extract_game_log_data(
                self.connected_game, self.skill_level
            )

            # 학습된 모델로 액션 선택 (학습 모드가 아니므로 버퍼에 저장하지 않음)
            state_vector = game_log_data.to_state_vector()
            state_tensor = (
                torch.FloatTensor(state_vector).unsqueeze(0).to(self.ppo_agent.device)
            )

            with torch.no_grad():
                action, _, _, _ = self.ppo_agent.network.get_action_and_value(
                    state_tensor
                )

            action_id = action.cpu().item()
            self.step_count += 1

            # 주기적으로 통계 출력
            if self.step_count % 300 == 0:
                try:
                    if (
                        self.connected_game
                        and hasattr(self.connected_game, "game")
                        and self.connected_game.game
                        and hasattr(self.connected_game.game, "game_vars")
                    ):
                        game_vars = self.connected_game.game.game_vars
                        score = getattr(game_vars, "score", 0)
                        lives = getattr(game_vars, "lives", 0)
                        kills = getattr(game_vars, "kills", 0)
                        print(
                            f"[STATS] Step {self.step_count} | 점수: {score} | 목숨: {lives} | 킬: {kills}"
                        )
                except:
                    pass

            return action_id

        except Exception as e:
            print(f"[ERROR] 액션 선택 실패: {e}")
            return 4  # 정지


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="학습된 PPO 모델이 게임을 플레이하는 것을 시각적으로 확인"
    )
    parser.add_argument(
        "--model-path",
        type=str,
        default="src/src/models/ppo/stages/고급-공격-중심-skill-1.0/master.pth",
        help="로드할 모델 파일 경로",
    )
    parser.add_argument(
        "--skill-level",
        type=float,
        default=1.0,
        help="모델이 사용할 실력값 (0.0-1.0, 기본값: 1.0)",
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("[GAME] 학습된 PPO 모델 플레이 시청")
    print("=" * 60)
    print(f"[CONFIG] 설정:")
    print(f"   - 모델 경로: {args.model_path}")
    print(f"   - 실력값: {args.skill_level}")
    print()

    try:
        # 모델 파일 존재 확인
        if not os.path.exists(args.model_path):
            print(f"[ERROR] 오류: 모델 파일을 찾을 수 없습니다: {args.model_path}")
            print("올바른 경로를 지정해주세요.")
            sys.exit(1)

        print(f"[INIT] PPO 에이전트 초기화 중...")

        # 환경 초기화 (상태 크기 확인용)
        environment = GameEnvironment()

        # PPO 에이전트 생성 (학습된 모델의 구조와 동일해야 함)
        ppo_agent = PPOAgent(
            state_size=161,  # 프로젝트 표준 상태 크기
            action_size=10,  # 9개 액션 + 1
        )

        print(f"[LOAD] 모델 로드 중: {args.model_path}")
        ppo_agent.load_model(args.model_path)
        print(f"[OK] 모델 로드 완료!")

        # 게임 플레이 에이전트 생성
        print(f"[INIT] 게임 플레이 에이전트 초기화 중...")
        game_agent = ModelPlayerAgent(ppo_agent, environment, args.skill_level)

        # 게임 앱 생성 및 실행
        print(f"[START] 게임 시작...")
        print()
        print("[TIP] 팁:")
        print("   - 게임을 종료하려면 창을 닫거나 Ctrl+C를 누르세요")
        print("   - 모델이 자동으로 플레이하는 것을 지켜보세요!")
        print()

        game_app = App(agent=game_agent)

        # Pyxel 게임 실행 (메인 스레드)
        px.run(game_app.update, game_app.draw)

    except KeyboardInterrupt:
        print("\n[EXIT] 사용자에 의해 종료되었습니다.")
    except Exception as e:
        print(f"[ERROR] 오류 발생: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
