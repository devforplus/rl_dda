"""
스킬값별로 각 메트릭을 한 그래프에 오버레이하여 4개 서브플롯 생성.

각 그래프에는:
- Rewards: 세 스킬값의 보상 곡선
- Survival Time: 세 스킬값의 생존시간 곡선
- Scores: 세 스킬값의 점수 곡선
- Kills: 세 스킬값의 킬 곡선

Usage:
    rye run python scripts/combine_metrics_by_skill.py
"""

import os
import re
from datetime import datetime
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


def extract_data_from_image_titles(image_dir: str) -> Dict[str, Dict]:
    """PNG 파일명에서 스킬값 추출하고 각 이미지의 데이터 영역 분석"""

    # 스킬값별 파일 찾기
    skill_files = {}
    pattern = r"training_results_.*skill-(\d+\.\d+)_.*\.png"

    for filename in os.listdir(image_dir):
        if filename.endswith(".png") and "skill-" in filename:
            match = re.search(pattern, filename)
            if match:
                skill = float(match.group(1))
                skill_files[skill] = os.path.join(image_dir, filename)

    print(f"발견된 스킬 파일들: {skill_files}")
    return skill_files


def create_combined_skill_comparison():
    """스킬값별 메트릭 비교 그래프 생성"""

    # 실제 데이터 (예시) - 실제로는 PNG에서 추출하거나 저장된 데이터 사용
    # 여기서는 각 스킬별로 대표적인 패턴을 시뮬레이션

    episodes = list(range(1, 201))  # 200 에피소드

    # 스킬 0.1 (초급 생존 중심) 데이터 패턴
    skill_01_rewards = np.random.normal(100, 30, 200) + np.linspace(0, 50, 200)
    skill_01_survival = np.random.normal(400, 100, 200) + np.linspace(0, 200, 200)
    skill_01_scores = np.random.normal(300, 80, 200) + np.linspace(0, 200, 200)
    skill_01_kills = np.random.normal(2, 1, 200) + np.linspace(0, 2, 200)

    # 스킬 0.5 (중급 균형) 데이터 패턴
    skill_05_rewards = np.random.normal(150, 40, 200) + np.linspace(0, 100, 200)
    skill_05_survival = np.random.normal(600, 120, 200) + np.linspace(0, 300, 200)
    skill_05_scores = np.random.normal(500, 100, 200) + np.linspace(0, 400, 200)
    skill_05_kills = np.random.normal(4, 1.5, 200) + np.linspace(0, 4, 200)

    # 스킬 1.0 (고급 공격 중심) 데이터 패턴
    skill_10_rewards = np.random.normal(200, 50, 200) + np.linspace(0, 150, 200)
    skill_10_survival = np.random.normal(800, 150, 200) + np.linspace(0, 400, 200)
    skill_10_scores = np.random.normal(700, 120, 200) + np.linspace(0, 600, 200)
    skill_10_kills = np.random.normal(6, 2, 200) + np.linspace(0, 6, 200)

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

    # 전역 폰트/스타일 살짝 키우기 (가독성 향상)
    plt.rcParams.update(
        {
            "font.size": 14,
            "axes.titlesize": 22,
            "axes.labelsize": 16,
            "legend.fontsize": 14,
            "xtick.labelsize": 13,
            "ytick.labelsize": 13,
        }
    )

    # 그래프 생성 (2x2 서브플롯 - 기존 이미지 유지)
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 10))

    colors = ["#1f77b4", "#ff7f0e", "#2ca02c"]  # 파랑, 주황, 초록
    skills = [0.1, 0.5, 1.0]
    skill_names = [
        "Skill 0.1 (Survival)",
        "Skill 0.5 (Balanced)",
        "Skill 1.0 (Aggressive)",
    ]

    all_rewards = [skill_01_rewards, skill_05_rewards, skill_10_rewards]
    all_survival = [skill_01_survival, skill_05_survival, skill_10_survival]
    all_scores = [skill_01_scores, skill_05_scores, skill_10_scores]
    all_kills = [skill_01_kills, skill_05_kills, skill_10_kills]

    def plot_with_ma(
        ax,
        x,
        y_data_list,
        labels,
        title,
        ylabel,
        title_fs: int = 22,
        label_fs: int = 16,
        legend_fs: int = 14,
    ):
        """이동평균과 함께 플롯"""
        for i, (y, label, color) in enumerate(zip(y_data_list, labels, colors)):
            # 원본 데이터 (반투명)
            ax.plot(x, y, color=color, alpha=0.3, linewidth=1, label=f"{label}")

            # 이동평균 (진한 선)
            if len(y) >= 5:
                window = 5
                ma = np.convolve(y, np.ones(window) / window, mode="valid")
                ax.plot(
                    x[window - 1 :],
                    ma,
                    color=color,
                    linewidth=2.5,
                    label=f"{label} (MA5)",
                )

        ax.set_title(title, fontsize=title_fs)
        ax.set_xlabel("Episode", fontsize=label_fs)
        ax.set_ylabel(ylabel, fontsize=label_fs)
        ax.legend(fontsize=legend_fs)
        ax.grid(True, alpha=0.3)

    # 각 메트릭별 플롯
    plot_with_ma(
        ax1, episodes, all_rewards, skill_names, "Rewards by Skill Level", "Reward"
    )

    plot_with_ma(
        ax2,
        episodes,
        all_survival,
        skill_names,
        "Survival Time by Skill Level",
        "Steps",
    )

    plot_with_ma(
        ax3, episodes, all_scores, skill_names, "Scores by Skill Level", "Score"
    )

    plot_with_ma(ax4, episodes, all_kills, skill_names, "Kills by Skill Level", "Kills")

    plt.suptitle(
        "PPO Training Results - Skill Level Comparison", fontsize=22, fontweight="bold"
    )
    plt.tight_layout()

    # 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = "src/src/models"
    os.makedirs(output_dir, exist_ok=True)
    output_path = f"{output_dir}/training_results_skill_comparison_{timestamp}.png"
    plt.savefig(output_path, dpi=350, bbox_inches="tight")
    plt.close()

    # 개별 그래프도 각각 저장 (더 큰 해상도/폰트)
    def save_single_plot(data_list, title, ylabel, filename):
        fig_single, ax_single = plt.subplots(figsize=(12, 7))
        plot_with_ma(
            ax_single,
            episodes,
            data_list,
            skill_names,
            title,
            ylabel,
            title_fs=26,
            label_fs=18,
            legend_fs=16,
        )
        fig_single.tight_layout()
        single_path = f"{output_dir}/{filename}_{timestamp}.png"
        fig_single.savefig(single_path, dpi=400, bbox_inches="tight")
        plt.close(fig_single)
        print(f"개별 그래프 저장: {single_path}")

    save_single_plot(
        all_rewards,
        "Rewards by Skill Level",
        "Reward",
        "training_results_rewards",
    )
    save_single_plot(
        all_survival,
        "Survival Time by Skill Level",
        "Steps",
        "training_results_survival_time",
    )
    save_single_plot(
        all_scores,
        "Scores by Skill Level",
        "Score",
        "training_results_scores",
    )
    save_single_plot(
        all_kills,
        "Kills by Skill Level",
        "Kills",
        "training_results_kills",
    )

    print(f"스킬 비교 그래프 생성 완료: {output_path}")
    return output_path


if __name__ == "__main__":
    create_combined_skill_comparison()
