#!/usr/bin/env python
"""
PPO 에이전트 ↔ 게임 데이터 흐름 분석기

실제로 주고받는 데이터를 실시간으로 분석하고 시각화합니다.
"""

import sys
import os
import time
import numpy as np
from typing import Dict, List, Any

# 프로젝트 루트의 'src' 디렉토리를 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
src_path = os.path.join(project_root, "src")
sys.path.insert(0, src_path)
sys.path.insert(0, project_root)

try:
    import pyxel as px
    from main import App
    from rl.environment import GameEnvironment
    from rl.game_adapter import GameStateAdapter
    from rl.agents.ppo_agent import PPOAgent
    from components.entity_types import EntityType
except ImportError as e:
    print(f"Error: {e}. Make sure you are in the correct environment.")
    sys.exit(1)


class DataFlowAnalyzer(App):
    """데이터 흐름을 분석하는 App 클래스"""

    def __init__(self):
        # 분석 도구들
        self.environment = GameEnvironment()
        self.adapter = GameStateAdapter()

        # PPO 에이전트 생성 (환경이 필요함)
        self.ppo_agent = PPOAgent(
            env=self.environment,
            device="cpu",
        )

        super().__init__(agent=self.ppo_agent, speed_multiplier=4)

        # 데이터 수집 변수
        self.frame_count = 0
        self.max_analysis_frames = 180  # 3초간 분석 (60fps * 3)
        self.data_samples = []

        # 플레이어 무적 모드
        if (
            self.game
            and hasattr(self.game, "state")
            and hasattr(self.game.state, "player")
        ):
            self.game.state.player.invincible = True

        print("🔍 PPO 에이전트 ↔ 게임 데이터 흐름 분석 시작")
        print("   3초간 실제 데이터를 수집하여 분석합니다...")

    def update(self):
        super().update()

        self.frame_count += 1

        # 매 30프레임마다 데이터 샘플링 (0.5초마다)
        if self.frame_count % 30 == 0:
            self._analyze_data_flow()

        # 분석 완료 후 종료
        if self.frame_count >= self.max_analysis_frames:
            self._show_analysis_results()
            px.quit()

    def _analyze_data_flow(self):
        """실제 데이터 흐름 분석"""
        try:
            # 1. 게임 → PPO: 상태 데이터 추출
            game_state = self.adapter.extract_game_state(self, 0.5, 0)
            state_tensor = self.environment.encode_state(game_state)

            # 2. PPO → 게임: 액션 생성
            action = self.ppo_agent.select_action(state_tensor)

            # 3. 데이터 분석 정보 수집
            sample = {
                "frame": self.frame_count,
                "timestamp": time.time(),
                "entities_count": len(game_state.entities),
                "state_vector_size": len(state_tensor),
                "state_vector_sample": state_tensor[:20].tolist(),  # 처음 20개 값
                "action": action,
                "game_meta": {
                    "player_hp": game_state.player_hp,
                    "player_lives": game_state.player_lives,
                    "score": game_state.score,
                    "survival_time": game_state.survival_time,
                    "kills": game_state.kills,
                    "current_stage": game_state.current_stage,
                    "game_cleared": game_state.game_cleared,
                },
                "entities_details": self._analyze_entities(
                    game_state.entities[:5]
                ),  # 처음 5개 엔티티만
            }

            self.data_samples.append(sample)

        except Exception as e:
            print(f"⚠️ 데이터 분석 오류: {e}")

    def _analyze_entities(self, entities):
        """엔티티 상세 분석"""
        details = []
        for entity in entities:
            details.append(
                {
                    "type": entity.entity_type.name,
                    "type_id": entity.entity_type.value,
                    "position": (round(entity.x, 1), round(entity.y, 1)),
                    "size": (round(entity.w, 1), round(entity.h, 1)),
                    "distance_to_player": round(entity.distance_to_player, 1),
                }
            )
        return details

    def _show_analysis_results(self):
        """분석 결과 출력"""
        print("\n" + "=" * 70)
        print("📊 **PPO 에이전트 ↔ 게임 데이터 흐름 분석 결과**")
        print("=" * 70)

        if not self.data_samples:
            print("❌ 수집된 데이터가 없습니다.")
            return

        # 전체 통계
        print(f"📈 **전체 통계** (샘플 {len(self.data_samples)}개)")
        avg_entities = np.mean([s["entities_count"] for s in self.data_samples])
        print(f"   - 평균 엔티티 수: {avg_entities:.1f}개")
        print(
            f"   - 상태 벡터 크기: {self.data_samples[0]['state_vector_size']} (고정)"
        )
        print(f"   - 액션 공간: 9개 (0~8)")

        # 최신 샘플 상세 분석
        latest = self.data_samples[-1]
        print(f"\n🔍 **최신 데이터 샘플** (프레임 {latest['frame']})")

        print(f"\n📤 **게임 → PPO 에이전트 (관찰 데이터)**")
        print(f"   🎮 게임 메타 정보:")
        for key, value in latest["game_meta"].items():
            print(f"      - {key}: {value}")

        print(f"   🎯 감지된 엔티티 ({latest['entities_count']}개):")
        if latest["entities_details"]:
            for i, entity in enumerate(
                latest["entities_details"][:3]
            ):  # 상위 3개만 표시
                print(
                    f"      [{i + 1}] {entity['type']}: 위치{entity['position']}, 크기{entity['size']}, 거리{entity['distance_to_player']}"
                )
            if len(latest["entities_details"]) > 3:
                print(f"      ... 외 {len(latest['entities_details']) - 3}개")
        else:
            print("      - 감지된 엔티티 없음")

        print(f"   📊 상태 벡터 (크기: {latest['state_vector_size']}):")
        print(
            f"      - 엔티티 데이터: {50 * 6} = 300개 값 (최대 50개 엔티티 × 6개 특성)"
        )
        print(f"      - 게임 메타 데이터: 9개 값")
        print(f"      - 샘플 값들: {latest['state_vector_sample'][:5]}... (처음 5개)")

        print(f"\n📥 **PPO 에이전트 → 게임 (액션 데이터)**")
        action_names = [
            "LEFT_UP",
            "UP",
            "RIGHT_UP",
            "LEFT",
            "RIGHT",
            "LEFT_DOWN",
            "DOWN",
            "RIGHT_DOWN",
            "FIRE",
        ]
        action_name = (
            action_names[latest["action"]] if 0 <= latest["action"] <= 8 else "UNKNOWN"
        )
        print(f"   🎯 선택된 액션: {latest['action']} ({action_name})")
        print(f"   🕹️  게임 입력 변환:")

        # 액션을 게임 입력으로 변환하여 표시
        input_map = self._action_to_input_description(latest["action"])
        for key, value in input_map.items():
            status = "ON" if value else "OFF"
            print(f"      - {key}: {status}")

        # 데이터 특성 분석
        print(f"\n📋 **데이터 특성 요약**")
        print(f"   🔄 데이터 흐름:")
        print(f"      게임 → PPO: 309개 실수 (상태 벡터)")
        print(f"      PPO → 게임: 1개 정수 (액션 ID)")
        print(f"   ⚡ 성능 특성:")
        print(f"      - 이미지 데이터: ❌ 사용 안 함 (성능 최적화)")
        print(f"      - 구조화된 데이터: ✅ 고속 처리")
        print(f"      - 메모리 효율성: ✅ 벡터 기반")
        print(f"   🎯 AI 학습 특성:")
        print(f"      - 입력 공간: 연속형 (실수 벡터)")
        print(f"      - 출력 공간: 이산형 (9개 액션)")
        print(f"      - 학습 타입: 강화학습 (PPO)")

        print("\n" + "=" * 70)
        print("✅ 데이터 흐름 분석 완료!")

    def _action_to_input_description(self, action_id: int) -> Dict[str, bool]:
        """액션 ID를 게임 입력 상태로 변환"""
        inputs = {
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "fire": False,
        }

        if action_id == 0:  # LEFT_UP
            inputs["left"] = True
            inputs["up"] = True
        elif action_id == 1:  # UP
            inputs["up"] = True
        elif action_id == 2:  # RIGHT_UP
            inputs["right"] = True
            inputs["up"] = True
        elif action_id == 3:  # LEFT
            inputs["left"] = True
        elif action_id == 4:  # RIGHT
            inputs["right"] = True
        elif action_id == 5:  # LEFT_DOWN
            inputs["left"] = True
            inputs["down"] = True
        elif action_id == 6:  # DOWN
            inputs["down"] = True
        elif action_id == 7:  # RIGHT_DOWN
            inputs["right"] = True
            inputs["down"] = True
        elif action_id == 8:  # FIRE
            inputs["fire"] = True

        return inputs


def main():
    print("🚀 PPO 에이전트 데이터 흐름 분석기 시작")
    print("   실제 학습 환경에서 주고받는 데이터를 분석합니다.")

    analyzer = DataFlowAnalyzer()
    analyzer.run()


if __name__ == "__main__":
    main()
