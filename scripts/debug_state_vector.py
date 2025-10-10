#!/usr/bin/env python3
"""
상태 벡터 디버깅 스크립트

실제 게임 플레이 중 상태 벡터의 값들을 분석하여
Value Loss가 높은 원인을 파악합니다.

Usage:
    python scripts/debug_state_vector.py
"""

import numpy as np
import torch
import matplotlib.pyplot as plt
from typing import List, Dict, Any
import json
from pathlib import Path
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from rl.environment import GameEnvironment, GameState, EntityData
from components.entity_types import EntityType


class StateVectorAnalyzer:
    """상태 벡터 분석 클래스"""

    def __init__(self):
        self.env = GameEnvironment()
        self.state_samples = []
        self.analysis_results = {}

    def create_dummy_game_states(self) -> List[GameState]:
        """다양한 게임 상황을 시뮬레이션하는 더미 상태들 생성"""
        dummy_states = []

        # 1. 초기 상태 (적 없음)
        empty_state = GameState(
            entities=[],
            skill_level=0.5,
            personality=0,
            player_hp=2,
            player_lives=3,
            score=0,
            survival_time=60,  # 1초
            kills=0,
            current_stage=1,
            game_cleared=False,
        )
        dummy_states.append(("초기_상태", empty_state))

        # 2. 적이 많은 위험한 상태
        dangerous_entities = []
        for i in range(10):
            enemy = EntityData(
                entity_type=EntityType.ENEMY,
                x=50 + i * 20,
                y=50 + i * 15,
                w=16,
                h=16,
                distance_to_player=50 + i * 10,
            )
            dangerous_entities.append(enemy)

        dangerous_state = GameState(
            entities=dangerous_entities,
            skill_level=0.3,
            personality=1,
            player_hp=1,  # 낮은 체력
            player_lives=2,
            score=1500,
            survival_time=300,  # 5초
            kills=3,
            current_stage=2,
            game_cleared=False,
        )
        dummy_states.append(("위험한_상태", dangerous_state))

        # 3. 안전한 높은 점수 상태
        safe_entities = [
            EntityData(
                entity_type=EntityType.POWERUP,
                x=128,
                y=128,
                w=8,
                h=8,
                distance_to_player=20,
            )
        ]

        safe_state = GameState(
            entities=safe_entities,
            skill_level=0.8,
            personality=0,
            player_hp=2,
            player_lives=3,
            score=5000,
            survival_time=900,  # 15초
            kills=10,
            current_stage=3,
            game_cleared=False,
        )
        dummy_states.append(("안전한_상태", safe_state))

        # 4. 극한 상황 (많은 엔티티)
        extreme_entities = []
        for i in range(50):  # 최대치
            entity_type = EntityType.ENEMY if i % 3 == 0 else EntityType.ENEMY_SHOT
            extreme_entities.append(
                EntityData(
                    entity_type=entity_type,
                    x=np.random.uniform(0, 256),
                    y=np.random.uniform(0, 256),
                    w=np.random.uniform(8, 32),
                    h=np.random.uniform(8, 32),
                    distance_to_player=np.random.uniform(10, 300),
                )
            )

        extreme_state = GameState(
            entities=extreme_entities,
            skill_level=1.0,
            personality=1,
            player_hp=1,
            player_lives=1,
            score=10000,
            survival_time=1800,  # 30초
            kills=25,
            current_stage=5,
            game_cleared=False,
        )
        dummy_states.append(("극한_상황", extreme_state))

        return dummy_states

    def analyze_state_vector(self, state_name: str, game_state: GameState):
        """개별 상태 벡터 분석"""
        print(f"\n{'=' * 50}")
        print(f"🔍 상태 분석: {state_name}")
        print(f"{'=' * 50}")

        # 상태 벡터 생성
        state_vector = self.env.encode_state(game_state)

        # 기본 통계
        print(f"📊 기본 통계:")
        print(f"  - 벡터 크기: {len(state_vector)}")
        print(f"  - 최소값: {state_vector.min().item():.6f}")
        print(f"  - 최대값: {state_vector.max().item():.6f}")
        print(f"  - 평균: {state_vector.mean().item():.6f}")
        print(f"  - 표준편차: {state_vector.std().item():.6f}")

        # NaN, inf 체크
        nan_count = torch.isnan(state_vector).sum().item()
        inf_count = torch.isinf(state_vector).sum().item()
        print(f"  - NaN 개수: {nan_count}")
        print(f"  - Inf 개수: {inf_count}")

        if nan_count > 0 or inf_count > 0:
            print(f"⚠️ 경고: 비정상적인 값 발견!")

        # 엔티티 데이터 분석 (처음 300개 값)
        entity_data = state_vector[:300].reshape(50, 6)
        print(f"\n🎯 엔티티 데이터 분석:")

        # 비어있지 않은 엔티티 개수
        non_zero_entities = (entity_data.sum(dim=1) != 0).sum().item()
        print(f"  - 활성 엔티티 수: {non_zero_entities}/50")

        if non_zero_entities > 0:
            active_entities = entity_data[entity_data.sum(dim=1) != 0]
            print(
                f"  - 엔티티 타입 범위: {active_entities[:, 0].min().item():.1f} ~ {active_entities[:, 0].max().item():.1f}"
            )
            print(
                f"  - X 좌표 범위: {active_entities[:, 1].min().item():.3f} ~ {active_entities[:, 1].max().item():.3f}"
            )
            print(
                f"  - Y 좌표 범위: {active_entities[:, 2].min().item():.3f} ~ {active_entities[:, 2].max().item():.3f}"
            )
            print(
                f"  - 거리 범위: {active_entities[:, 5].min().item():.3f} ~ {active_entities[:, 5].max().item():.3f}"
            )

        # 메타 데이터 분석 (마지막 9개 값)
        meta_data = state_vector[300:]
        meta_labels = [
            "skill_level",
            "personality",
            "player_hp",
            "player_lives",
            "score",
            "survival_time",
            "kills",
            "current_stage",
            "game_cleared",
        ]

        print(f"\n🎮 메타 데이터 분석:")
        for i, (label, value) in enumerate(zip(meta_labels, meta_data)):
            print(f"  - {label}: {value.item():.6f}")

            # 이상한 값 체크
            if label in ["skill_level", "personality", "game_cleared"] and not (
                0 <= value <= 1
            ):
                print(f"    ⚠️ 범위 이상: {label}은 0-1 범위여야 함")
            elif label == "player_hp" and value < 0:
                print(f"    ⚠️ 음수 체력: {value.item()}")
            elif label in ["score", "survival_time", "kills"] and value < 0:
                print(f"    ⚠️ 음수 값: {label}이 음수임")

        # 분석 결과 저장
        self.analysis_results[state_name] = {
            "vector_size": len(state_vector),
            "min_value": state_vector.min().item(),
            "max_value": state_vector.max().item(),
            "mean": state_vector.mean().item(),
            "std": state_vector.std().item(),
            "nan_count": nan_count,
            "inf_count": inf_count,
            "active_entities": non_zero_entities,
            "meta_data": {
                label: value.item() for label, value in zip(meta_labels, meta_data)
            },
            "raw_vector": state_vector.numpy().tolist(),
        }

        return state_vector

    def compare_states(self):
        """여러 상태 간 비교 분석"""
        print(f"\n{'=' * 50}")
        print(f"📈 상태 벡터 비교 분석")
        print(f"{'=' * 50}")

        # 상태별 주요 지표 비교
        for state_name, results in self.analysis_results.items():
            print(f"\n{state_name}:")
            print(
                f"  값 범위: [{results['min_value']:.3f}, {results['max_value']:.3f}]"
            )
            print(f"  평균/표준편차: {results['mean']:.3f} ± {results['std']:.3f}")
            print(f"  활성 엔티티: {results['active_entities']}")
            print(f"  점수: {results['meta_data']['score']:.3f}")
            print(f"  생존시간: {results['meta_data']['survival_time']:.3f}")

    def detect_potential_issues(self):
        """잠재적 문제점 감지"""
        print(f"\n{'=' * 50}")
        print(f"🚨 잠재적 문제점 감지")
        print(f"{'=' * 50}")

        issues_found = []

        for state_name, results in self.analysis_results.items():
            # 1. 값 범위 문제
            if results["max_value"] > 10 or results["min_value"] < -10:
                issues_found.append(
                    f"{state_name}: 값 범위가 너무 큼 ({results['min_value']:.3f} ~ {results['max_value']:.3f})"
                )

            # 2. 표준편차 문제 (값들이 너무 다름)
            if results["std"] > 5:
                issues_found.append(
                    f"{state_name}: 표준편차가 너무 큼 ({results['std']:.3f})"
                )

            # 3. NaN/Inf 문제
            if results["nan_count"] > 0 or results["inf_count"] > 0:
                issues_found.append(
                    f"{state_name}: 비정상 값 존재 (NaN: {results['nan_count']}, Inf: {results['inf_count']})"
                )

            # 4. 메타 데이터 문제
            meta = results["meta_data"]
            if meta["score"] > 1:  # 정규화 후 1을 초과
                issues_found.append(
                    f"{state_name}: 점수 정규화 문제 ({meta['score']:.3f})"
                )

            if meta["survival_time"] > 1:  # 정규화 후 1을 초과
                issues_found.append(
                    f"{state_name}: 생존시간 정규화 문제 ({meta['survival_time']:.3f})"
                )

        if issues_found:
            print("🔴 발견된 문제들:")
            for issue in issues_found:
                print(f"  - {issue}")
        else:
            print("✅ 명백한 문제는 발견되지 않았습니다.")

        return issues_found

    def visualize_state_distributions(self):
        """상태 벡터 분포 시각화"""
        print(f"\n📊 상태 벡터 분포 시각화 중...")

        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle("상태 벡터 분포 분석", fontsize=16)

        state_names = list(self.analysis_results.keys())

        # 1. 값 범위 비교
        ax = axes[0, 0]
        min_vals = [self.analysis_results[name]["min_value"] for name in state_names]
        max_vals = [self.analysis_results[name]["max_value"] for name in state_names]

        x = range(len(state_names))
        ax.bar([i - 0.2 for i in x], min_vals, 0.4, label="최소값", alpha=0.7)
        ax.bar([i + 0.2 for i in x], max_vals, 0.4, label="최대값", alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(state_names, rotation=45)
        ax.set_title("상태별 값 범위")
        ax.legend()

        # 2. 평균/표준편차 비교
        ax = axes[0, 1]
        means = [self.analysis_results[name]["mean"] for name in state_names]
        stds = [self.analysis_results[name]["std"] for name in state_names]

        ax.bar([i - 0.2 for i in x], means, 0.4, label="평균", alpha=0.7)
        ax.bar([i + 0.2 for i in x], stds, 0.4, label="표준편차", alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(state_names, rotation=45)
        ax.set_title("평균 및 표준편차")
        ax.legend()

        # 3. 활성 엔티티 수
        ax = axes[1, 0]
        active_entities = [
            self.analysis_results[name]["active_entities"] for name in state_names
        ]
        ax.bar(x, active_entities, alpha=0.7)
        ax.set_xticks(x)
        ax.set_xticklabels(state_names, rotation=45)
        ax.set_title("활성 엔티티 수")

        # 4. 첫 번째 상태의 히스토그램
        ax = axes[1, 1]
        first_state_vector = self.analysis_results[state_names[0]]["raw_vector"]
        ax.hist(first_state_vector, bins=50, alpha=0.7)
        ax.set_title(f"{state_names[0]} 값 분포")
        ax.set_xlabel("값")
        ax.set_ylabel("빈도")

        plt.tight_layout()

        # 저장
        output_path = project_root / "scripts" / "state_vector_analysis.png"
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"📈 시각화 결과 저장: {output_path}")

        plt.show()

    def save_results(self):
        """분석 결과 저장"""
        output_path = project_root / "scripts" / "state_vector_analysis.json"

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(self.analysis_results, f, indent=2, ensure_ascii=False)

        print(f"💾 분석 결과 저장: {output_path}")

    def run_full_analysis(self):
        """전체 분석 실행"""
        print("🔍 상태 벡터 분석 시작...")

        # 더미 상태들 생성
        dummy_states = self.create_dummy_game_states()

        # 각 상태 분석
        for state_name, game_state in dummy_states:
            state_vector = self.analyze_state_vector(state_name, game_state)
            self.state_samples.append((state_name, state_vector))

        # 비교 분석
        self.compare_states()

        # 문제점 감지
        issues = self.detect_potential_issues()

        # 시각화
        self.visualize_state_distributions()

        # 결과 저장
        self.save_results()

        print(f"\n{'=' * 50}")
        print(f"✅ 분석 완료!")
        print(f"{'=' * 50}")

        return issues


def main():
    """메인 함수"""
    analyzer = StateVectorAnalyzer()
    issues = analyzer.run_full_analysis()

    print(f"\n🎯 분석 요약:")
    print(f"  - 총 {len(analyzer.analysis_results)}개 상태 분석 완료")
    print(f"  - 발견된 문제점: {len(issues)}개")

    if issues:
        print(f"\n🔧 권장 조치사항:")
        print(f"  1. 정규화 스케일 조정 검토")
        print(f"  2. 상태 벡터 전처리 개선")
        print(f"  3. Value Function 입력 범위 확인")

    return issues


if __name__ == "__main__":
    main()
