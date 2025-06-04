#!/usr/bin/env python
"""
PPO 에이전트와 실제 게임 연동 스크립트

훈련된 PPO 에이전트가 실제 게임 환경에서 플레이하도록 합니다.
게임 상태를 실시간으로 추출하여 에이전트에 전달하고,
에이전트의 액션을 게임 입력으로 변환합니다.

---

실제 게임과 강화학습 에이전트를 연동하는 통합 스크립트
"""

import sys
import os
import time
import json
import traceback
from typing import Optional, Dict, Any

# src 디렉토리를 시스템 경로에 추가
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

try:
    import pyxel as px
    from main import App
    from rl.agents.ppo_agent import PPOAgent, create_ppo_agent
    from rl.environment import GameEnvironment
    from rl.game_adapter import GameStateAdapter
    from components.entity_types import EntityType
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    print(
        "Make sure all required modules are installed and paths are correct.",
        file=sys.stderr,
    )
    sys.exit(1)


class GamePPOAgent:
    """실제 게임과 연동되는 PPO 에이전트 래퍼

    게임 상태를 추출하고 PPO 에이전트의 액션을 적용하는 브리지 역할을 합니다.

    ---

    게임과 PPO 에이전트 사이의 인터페이스를 제공하는 어댑터 클래스
    """

    def __init__(
        self,
        ppo_agent: PPOAgent,
        skill_level: float = 0.5,
        personality: int = 0,
        enable_learning: bool = False,
    ):
        """게임 PPO 에이전트 초기화

        Args:
            ppo_agent: PPO 에이전트 인스턴스
            skill_level: 플레이어 실력 수준 (0~1)
            personality: 플레이어 성향 (0: 방어적, 1: 공격적)
            enable_learning: 학습 모드 여부

        ---

        PPO 에이전트와 게임 어댑터를 초기화
        """
        self.ppo_agent = ppo_agent
        self.skill_level = skill_level
        self.personality = personality
        self.enable_learning = enable_learning

        # 게임 상태 어댑터
        self.adapter = GameStateAdapter()

        # 게임 인스턴스 참조 (나중에 설정됨)
        self.game_instance = None

        # 성능 통계
        self.step_count = 0
        self.episode_count = 0
        self.total_reward = 0.0
        self.episode_start_time = time.time()
        self.last_game_state = None
        self.last_action = None
        self.last_action_time = time.time()

        # 통계 출력 간격
        self.stats_interval = 300  # 5초마다 (60 FPS 기준)

        print(f"🤖 GamePPOAgent initialized:")
        print(f"   Skill Level: {skill_level}")
        print(f"   Personality: {'Aggressive' if personality == 1 else 'Defensive'}")
        print(f"   Learning: {'Enabled' if enable_learning else 'Disabled'}")

    def set_game_instance(self, game_instance):
        """게임 인스턴스 설정

        Args:
            game_instance: App 인스턴스

        ---

        게임과의 연결을 설정하여 실제 게임 상태에 접근 가능하게 함
        """
        self.game_instance = game_instance
        print("🔗 Game instance connected to PPO agent")

    def select_action(self, state=None) -> int:
        """게임에서 호출되는 액션 선택 메서드

        Args:
            state: 게임 상태 (사용되지 않음, 직접 추출)

        Returns:
            선택된 액션 ID (0~8)

        ---

        게임 루프에서 매 프레임 호출되어 에이전트의 액션을 반환
        """
        try:
            # 현재 시간 기록
            current_time = time.time()

            # 게임 인스턴스에서 상태 추출
            game_state = self._extract_current_game_state()

            if game_state is None:
                # 상태를 추출할 수 없으면 기본 액션 (정지)
                return 4  # 우측 이동 (안전한 기본 액션)

            # PPO 에이전트로 액션 선택
            if self.enable_learning:
                # 학습 모드: 탐험 포함 액션 선택
                action, log_prob, value = self.ppo_agent.select_action_with_exploration(
                    game_state
                )

                # 이전 상태가 있으면 경험 저장
                if (
                    self.last_game_state is not None
                    and self.last_action is not None
                    and hasattr(self, "last_log_prob")
                    and hasattr(self, "last_value")
                ):
                    # 보상 계산
                    reward = self.ppo_agent.env.calculate_reward(
                        game_state, self.last_action
                    )

                    # 에피소드 종료 여부 확인
                    done = self._is_episode_done(game_state)

                    # 경험 저장
                    self.ppo_agent.store_experience(
                        self.last_game_state,
                        self.last_action,
                        reward,
                        self.last_log_prob,
                        self.last_value,
                        done,
                    )

                    self.total_reward += reward

                    # 에피소드 종료 처리
                    if done:
                        self._handle_episode_end()

                # 현재 상태 저장
                self.last_game_state = game_state
                self.last_action = action
                self.last_log_prob = log_prob
                self.last_value = value

            else:
                # 평가 모드: 탐험 없는 액션 선택
                action = self.ppo_agent.select_action(game_state)
                self.last_action = action

            self.step_count += 1
            self.last_action_time = current_time

            # 주기적 통계 출력
            if self.step_count % self.stats_interval == 0:
                self._print_performance_stats()

            return action

        except Exception as e:
            print(f"Error in select_action: {e}", file=sys.stderr)
            print(traceback.format_exc(), file=sys.stderr)
            return 4  # 안전한 기본 액션

    def _extract_current_game_state(self):
        """현재 게임 상태 추출

        Returns:
            GameState 인스턴스 또는 None

        ---

        실제 게임 인스턴스에서 상태를 추출하여 PPO 모델용으로 변환
        """
        try:
            if self.game_instance is None:
                # 게임 인스턴스가 없으면 더미 상태 생성
                return self._create_dummy_game_state()

            # 게임 어댑터를 사용하여 실제 게임 상태 추출
            return self.adapter.extract_game_state(
                self.game_instance,
                self.skill_level,
                self.personality,
            )

        except Exception as e:
            print(f"Error extracting game state: {e}", file=sys.stderr)
            # 오류 발생 시 더미 상태로 대체
            return self._create_dummy_game_state()

    def _create_dummy_game_state(self):
        """더미 게임 상태 생성

        Returns:
            기본 GameState 인스턴스

        ---

        게임 인스턴스에 접근할 수 없을 때 사용하는 대체 상태
        """
        from rl.environment import GameState, EntityData

        # 기본 게임 상태 생성
        entities = [
            EntityData(EntityType.PLAYER, 100, 100, 8, 8, 0),
        ]

        return GameState(
            entities=entities,
            skill_level=self.skill_level,
            personality=self.personality,
            player_hp=10,
            score=self.step_count * 10,  # 임시 점수
            survival_time=self.step_count,
            kills=self.step_count // 100,
        )

    def _is_episode_done(self, game_state) -> bool:
        """에피소드 종료 여부 확인

        Args:
            game_state: 현재 게임 상태

        Returns:
            에피소드 종료 여부

        ---

        플레이어 사망이나 게임 종료 조건을 확인
        """
        # 플레이어 체력이 0이면 에피소드 종료
        if game_state.player_hp <= 0:
            return True

        # 일정 시간 이상 플레이하면 에피소드 종료 (학습 안정성을 위해)
        if self.enable_learning and self.step_count - self.episode_count * 1000 > 1000:
            return True

        return False

    def _handle_episode_end(self):
        """에피소드 종료 처리

        ---

        에피소드 통계 출력 및 학습 수행
        """
        self.episode_count += 1
        episode_length = self.step_count % 1000  # 임시 계산

        print(f"🏁 Episode {self.episode_count} ended:")
        print(f"   Length: {episode_length} steps")
        print(f"   Total Reward: {self.total_reward:.2f}")
        print(f"   Average Reward: {self.total_reward / max(1, episode_length):.4f}")

        # 학습 수행
        if self.enable_learning:
            training_stats = self.ppo_agent.train()
            if training_stats:
                print(f"   Training Loss: {training_stats.get('total_loss', 0):.6f}")

        # 통계 리셋
        self.total_reward = 0.0
        self.episode_start_time = time.time()

    def _print_performance_stats(self):
        """성능 통계 출력

        ---

        주기적으로 에이전트 성능 통계를 출력
        """
        current_time = time.time()
        elapsed_time = current_time - self.episode_start_time

        stats = {
            "type": "performance",
            "timestamp": current_time,
            "data": {
                "steps": self.step_count,
                "episodes": self.episode_count,
                "elapsed_time": elapsed_time,
                "steps_per_second": self.step_count / max(1, elapsed_time),
                "total_reward": self.total_reward,
                "learning_enabled": self.enable_learning,
            },
        }

        # PPO 에이전트 통계 추가
        agent_stats = self.ppo_agent.get_stats()
        if agent_stats:
            stats["data"]["agent"] = agent_stats

        print(json.dumps(stats))


class PPOGameApp(App):
    """PPO 에이전트와 통합된 게임 애플리케이션

    기본 App 클래스를 상속하여 PPO 에이전트와의 연동을 개선합니다.

    ---

    PPO 에이전트가 게임 상태에 접근할 수 있도록 하는 확장된 App 클래스
    """

    def __init__(self, game_ppo_agent: GamePPOAgent):
        """PPO 게임 앱 초기화

        Args:
            game_ppo_agent: 게임 PPO 에이전트 인스턴스

        ---

        게임과 PPO 에이전트 사이의 연결을 설정
        """
        self.game_ppo_agent = game_ppo_agent

        # 부모 클래스 초기화 (에이전트 전달)
        super().__init__(agent=game_ppo_agent)

        # 게임 PPO 에이전트에 게임 인스턴스 연결
        game_ppo_agent.set_game_instance(self)

        print("🎮 PPO Game App initialized successfully")


def create_trained_ppo_agent(model_path: Optional[str] = None) -> PPOAgent:
    """훈련된 PPO 에이전트 생성

    Args:
        model_path: 저장된 모델 파일 경로 (None이면 새 모델)

    Returns:
        PPO 에이전트 인스턴스

    ---

    기존 모델을 로드하거나 새 PPO 에이전트를 생성
    """
    # PPO 에이전트 생성
    agent = create_ppo_agent(
        skill_level=0.7,
        personality=1,  # 공격적 성향
        max_entities=50,
        learning_rate=3e-4,
        batch_size=64,
        buffer_size=2048,
        ppo_epochs=10,
    )

    # 저장된 모델 로드
    if model_path and os.path.exists(model_path):
        try:
            agent.load_model(model_path)
            print(f"✅ Model loaded from {model_path}")
        except Exception as e:
            print(f"⚠️  Failed to load model from {model_path}: {e}")
            print("Using newly initialized model instead.")
    else:
        print("🆕 Using newly initialized PPO agent")

    return agent


def run_ppo_in_game(
    model_path: Optional[str] = None,
    skill_level: float = 0.7,
    personality: int = 1,
    enable_learning: bool = False,
    save_interval: int = 1000,
):
    """PPO 에이전트를 게임에서 실행

    Args:
        model_path: 모델 파일 경로
        skill_level: 실력 수준
        personality: 성향
        enable_learning: 학습 모드 여부
        save_interval: 모델 저장 간격

    ---

    PPO 에이전트가 실제 게임을 플레이하도록 설정
    """
    try:
        print("🚀 Starting PPO Agent in Game Environment")
        print(f"📦 Model Path: {model_path if model_path else 'None (new model)'}")
        print(f"🧠 Learning Mode: {'Enabled' if enable_learning else 'Disabled'}")

        # PPO 에이전트 생성
        ppo_agent = create_trained_ppo_agent(model_path)

        # 게임 PPO 에이전트 래퍼 생성
        game_agent = GamePPOAgent(
            ppo_agent=ppo_agent,
            skill_level=skill_level,
            personality=personality,
            enable_learning=enable_learning,
        )

        # PPO 통합 게임 애플리케이션 시작
        print("🎮 Starting game with PPO agent...")
        app = PPOGameApp(game_agent)

        # 게임 종료 후 모델 저장
        if enable_learning and model_path:
            save_path = model_path or "models/ppo_game_trained.pth"
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            ppo_agent.save_model(save_path)
            print(f"💾 Model saved to {save_path}")

    except Exception as e:
        print(f"❌ Error running PPO in game: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)


def main():
    """메인 실행 함수

    ---

    명령행 인자를 파싱하고 PPO 에이전트를 게임에서 실행
    """
    import argparse

    parser = argparse.ArgumentParser(description="Run PPO agent in game environment")
    parser.add_argument("--model", type=str, help="Path to saved PPO model")
    parser.add_argument("--skill", type=float, default=0.7, help="Skill level (0-1)")
    parser.add_argument(
        "--personality",
        type=int,
        default=1,
        choices=[0, 1],
        help="Personality (0: defensive, 1: aggressive)",
    )
    parser.add_argument("--learn", action="store_true", help="Enable learning mode")
    parser.add_argument(
        "--save-interval", type=int, default=1000, help="Model save interval (steps)"
    )

    args = parser.parse_args()

    run_ppo_in_game(
        model_path=args.model,
        skill_level=args.skill,
        personality=args.personality,
        enable_learning=args.learn,
        save_interval=args.save_interval,
    )


if __name__ == "__main__":
    main()
