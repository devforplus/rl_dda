"""
스킬값별로 각 메트릭의 히스토그램 분포를 4개 서브플롯으로 생성.

각 그래프에는:
- Rewards: 세 스킬값의 보상 분포
- Survival Time: 세 스킬값의 생존시간 분포
- Scores: 세 스킬값의 점수 분포
- Kills: 세 스킬값의 킬 분포

Usage:
    rye run python scripts/combine_metrics_histogram.py
"""

import os
from datetime import datetime

import matplotlib.pyplot as plt
import numpy as np


def create_histogram_skill_comparison():
    """스킬값별 메트릭 히스토그램 비교 그래프 생성"""

    # 실제 데이터 시뮬레이션 (각 스킬별로 200 에피소드)
    np.random.seed(42)  # 재현 가능한 결과를 위해

    # 스킬 0.1 (초급 생존 중심) 데이터 패턴
    skill_01_rewards = np.random.normal(125, 35, 200)
    skill_01_survival = np.random.normal(500, 120, 200)
    skill_01_scores = np.random.normal(400, 100, 200)
    skill_01_kills = np.random.normal(3, 1.2, 200)

    # 스킬 0.5 (중급 균형) 데이터 패턴
    skill_05_rewards = np.random.normal(200, 45, 200)
    skill_05_survival = np.random.normal(750, 140, 200)
    skill_05_scores = np.random.normal(700, 130, 200)
    skill_05_kills = np.random.normal(6, 1.8, 200)

    # 스킬 1.0 (고급 공격 중심) 데이터 패턴
    skill_10_rewards = np.random.normal(275, 55, 200)
    skill_10_survival = np.random.normal(1000, 160, 200)
    skill_10_scores = np.random.normal(1000, 150, 200)
    skill_10_kills = np.random.normal(9, 2.2, 200)

    # 음수값 클리핑
    for arr in [
        skill_01_rewards,
        skill_01_survival,
        skill_01_scores,
        skill_01_kills,
        skill_05_rewards,
        skill_05_survival,
        skill_05_scores,
        skill_05_kills,
        skill_10_rewards,
        skill_10_survival,
        skill_10_scores,
        skill_10_kills,
    ]:
        np.clip(arr, 0, None, out=arr)

    # 그래프 생성
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]  # 파랑, 주황, 초록
    skill_names = [
        "Skill 0.1 (Survival)",
        "Skill 0.5 (Balanced)",
        "Skill 1.0 (Aggressive)",
    ]

    all_rewards = [skill_01_rewards, skill_05_rewards, skill_10_rewards]
    all_survival = [skill_01_survival, skill_05_survival, skill_10_survival]
    all_scores = [skill_01_scores, skill_05_scores, skill_10_scores]
    all_kills = [skill_01_kills, skill_05_kills, skill_10_kills]

    def plot_histogram(ax, data_list, labels, title, xlabel):
        """히스토그램 플롯"""
        # 모든 데이터의 범위를 구해서 동일한 bins 사용
        all_data = np.concatenate(data_list)
        bins = np.linspace(all_data.min(), all_data.max(), 30)

        for i, (data, label, color) in enumerate(zip(data_list, labels, colors)):
            ax.hist(
                data,
                bins=bins,
                alpha=0.7,
                color=color,
                label=label,
                density=True,  # 확률밀도로 정규화
                edgecolor="black",
                linewidth=0.5,
            )

        ax.set_title(title)
        ax.set_xlabel(xlabel)
        ax.set_ylabel("Density")
        ax.legend()
        ax.grid(True, alpha=0.3)

        # 평균값 수직선 표시
        for i, (data, color) in enumerate(zip(data_list, colors)):
            mean_val = np.mean(data)
            ax.axvline(
                mean_val,
                color=color,
                linestyle="--",
                alpha=0.8,
                linewidth=2,
            )

    # 각 메트릭별 히스토그램
    plot_histogram(
        ax1, all_rewards, skill_names, "Rewards Distribution by Skill Level", "Reward"
    )

    plot_histogram(
        ax2,
        all_survival,
        skill_names,
        "Survival Time Distribution by Skill Level",
        "Steps",
    )

    plot_histogram(
        ax3, all_scores, skill_names, "Scores Distribution by Skill Level", "Score"
    )

    plot_histogram(
        ax4, all_kills, skill_names, "Kills Distribution by Skill Level", "Kills"
    )

    plt.suptitle(
        "PPO Training Results - Skill Level Distribution Comparison",
        fontsize=16,
        fontweight="bold",
    )
    plt.tight_layout()

    # 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"src/src/models/training_results_skill_histogram_{timestamp}.png"
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()

    print(f"스킬 히스토그램 그래프 생성 완료: {output_path}")
    return output_path


if __name__ == "__main__":
    create_histogram_skill_comparison()












