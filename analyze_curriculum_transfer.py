#!/usr/bin/env python3
"""
커리큘럼 러닝과 전이학습 진행 상황 분석 스크립트

이 스크립트는:
1. 각 스테이지별 학습 곡선 분석
2. 스테이지 전환 시점의 성능 변화 확인
3. 전이학습 효과 정량화
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np


def analyze_stage_transition(
    prev_stage_data: List[float],
    next_stage_data: List[float],
    metric_name: str,
    window: int = 10
) -> Dict:
    """스테이지 전환 시점의 성능 변화 분석
    
    Args:
        prev_stage_data: 이전 스테이지의 마지막 부분 데이터
        next_stage_data: 다음 스테이지의 초반 데이터
        metric_name: 메트릭 이름
        window: 평균 계산 윈도우
        
    Returns:
        분석 결과 딕셔너리
    """
    # 이전 스테이지 마지막 성능
    prev_end = np.array(prev_stage_data[-window:])
    prev_avg = np.mean(prev_end)
    prev_std = np.std(prev_end)
    
    # 다음 스테이지 초반 성능
    next_start = np.array(next_stage_data[:window])
    next_avg = np.mean(next_start)
    next_std = np.std(next_start)
    
    # 성능 변화
    change = next_avg - prev_avg
    change_percent = (change / prev_avg * 100) if prev_avg != 0 else 0
    
    # 전이학습 효과 판단
    # 전이학습이 작동하면: 다음 스테이지 초반이 이전 스테이지 마지막보다 높거나 비슷해야 함
    transfer_working = change >= -prev_std  # 1 표준편차 이내로 떨어지는 것은 허용
    
    return {
        "metric": metric_name,
        "prev_stage_end_avg": float(prev_avg),
        "prev_stage_end_std": float(prev_std),
        "next_stage_start_avg": float(next_avg),
        "next_stage_start_std": float(next_std),
        "change": float(change),
        "change_percent": float(change_percent),
        "transfer_working": transfer_working,
    }


def analyze_stage_learning(
    data: List[float],
    metric_name: str,
    stage_name: str
) -> Dict:
    """단일 스테이지의 학습 진행 상황 분석
    
    Args:
        data: 스테이지 데이터
        metric_name: 메트릭 이름
        stage_name: 스테이지 이름
        
    Returns:
        분석 결과 딕셔너리
    """
    arr = np.array(data)
    
    # 초반과 후반 비교 (각 1/3)
    third = len(arr) // 3
    early = arr[:third]
    late = arr[-third:]
    
    early_avg = np.mean(early)
    late_avg = np.mean(late)
    
    improvement = late_avg - early_avg
    improvement_percent = (improvement / early_avg * 100) if early_avg != 0 else 0
    
    # 학습이 진행되는지 판단
    learning_happening = improvement > 0
    
    return {
        "stage": stage_name,
        "metric": metric_name,
        "initial_avg": float(early_avg),
        "final_avg": float(late_avg),
        "improvement": float(improvement),
        "improvement_percent": float(improvement_percent),
        "learning_happening": learning_happening,
        "data_points": len(data),
    }


def load_training_data(base_dir: Path) -> Dict:
    """학습 데이터 로드 (그래프 이미지의 메타데이터나 실제 데이터 파일에서)
    
    실제로는 학습 중 저장된 JSON 파일이나 로그를 파싱해야 하지만,
    여기서는 단계별 그래프 파일이 있다고 가정하고 분석 구조만 제시
    """
    # 실제 데이터 로드 로직은 학습 스크립트가 저장한 형식에 따라 다름
    # 여기서는 예제 구조만 제시
    
    stages = [
        {
            "name": "초급 (목표: 330스텝, 3킬)",
            "skill": 0.1,
            "episode_range": (1, 500),
            "file_pattern": "training_results_초급*20251027_213247.png"
        },
        {
            "name": "중하급 (목표: 590스텝, 9킬)",
            "skill": 0.3,
            "episode_range": (501, 1000),
            "file_pattern": "training_results_중하급*20251027_222831.png"
        },
        {
            "name": "중상급 (목표: 980스텝, 18킬)",
            "skill": 0.6,
            "episode_range": (1001, 1500),
            "file_pattern": "training_results_중상급*20251027_232640.png"
        },
        {
            "name": "고급 (목표: 1500스텝, 30킬)",
            "skill": 1.0,
            "episode_range": (1501, 2000),
            "file_pattern": "training_results_고급*20251028_002520.png"
        },
    ]
    
    return {"stages": stages}


def print_analysis_report(
    stage_analyses: List[Dict],
    transition_analyses: List[Dict]
):
    """분석 결과를 보기 좋게 출력"""
    
    print("=" * 80)
    print("🎓 커리큘럼 러닝 & 전이학습 분석 보고서")
    print("=" * 80)
    print()
    
    # 1. 각 스테이지별 학습 진행 상황
    print("📊 1. 스테이지별 학습 진행 상황")
    print("-" * 80)
    
    for stage_group in stage_analyses:
        stage_name = stage_group[0]["stage"]
        print(f"\n▶ {stage_name}")
        
        for analysis in stage_group:
            metric = analysis["metric"]
            initial = analysis["initial_avg"]
            final = analysis["final_avg"]
            improvement = analysis["improvement"]
            improvement_pct = analysis["improvement_percent"]
            learning = analysis["learning_happening"]
            
            status = "✅" if learning else "❌"
            print(f"  {status} {metric:15s}: {initial:7.1f} → {final:7.1f} "
                  f"(변화: {improvement:+7.1f}, {improvement_pct:+6.1f}%)")
    
    print()
    print("=" * 80)
    print()
    
    # 2. 스테이지 전환 시 전이학습 효과
    print("🔄 2. 스테이지 전환 시 전이학습 효과")
    print("-" * 80)
    
    if not transition_analyses:
        print("  ⚠️  전환 데이터 없음 (단일 스테이지 또는 데이터 부족)")
    else:
        for i, transition_group in enumerate(transition_analyses, 1):
            print(f"\n▶ 전환 {i}")
            
            for analysis in transition_group:
                metric = analysis["metric"]
                prev_end = analysis["prev_stage_end_avg"]
                next_start = analysis["next_stage_start_avg"]
                change = analysis["change"]
                change_pct = analysis["change_percent"]
                working = analysis["transfer_working"]
                
                status = "✅" if working else "❌"
                print(f"  {status} {metric:15s}: {prev_end:7.1f} → {next_start:7.1f} "
                      f"(변화: {change:+7.1f}, {change_pct:+6.1f}%)")
                
                if not working and change < 0:
                    print(f"      ⚠️  성능 하락! 전이학습이 제대로 작동하지 않을 수 있음")
    
    print()
    print("=" * 80)
    print()
    
    # 3. 종합 판단
    print("🎯 3. 종합 판단")
    print("-" * 80)
    
    # 학습 진행 상황
    total_stages = len(stage_analyses)
    learning_stages = sum(
        1 for group in stage_analyses 
        if any(a["learning_happening"] for a in group)
    )
    
    print(f"\n▶ 학습 진행: {learning_stages}/{total_stages} 스테이지에서 개선 관찰")
    
    if learning_stages == 0:
        print("  ❌ 심각: 어떤 스테이지에서도 학습이 진행되지 않음")
        print("  💡 권장: 하이퍼파라미터 조정 필요 (학습률, 엔트로피 증가)")
    elif learning_stages < total_stages / 2:
        print("  ⚠️  일부 스테이지에서만 학습 진행")
        print("  💡 권장: 목표값 조정 및 보상 구조 개선 필요")
    else:
        print("  ✅ 대부분의 스테이지에서 학습 진행 중")
    
    # 전이학습 효과
    if transition_analyses:
        total_transitions = len(transition_analyses)
        working_transitions = sum(
            1 for group in transition_analyses
            if all(a["transfer_working"] for a in group)
        )
        
        print(f"\n▶ 전이학습: {working_transitions}/{total_transitions} 전환에서 정상 작동")
        
        if working_transitions == 0:
            print("  ❌ 심각: 전이학습이 전혀 작동하지 않음")
            print("  💡 권장: 체크포인트 로드 로직 확인 필요")
            print("  💡 로그에서 '✅ 전이 학습 성공!' 메시지 확인")
        elif working_transitions < total_transitions:
            print("  ⚠️  일부 전환에서 전이학습 문제")
            print("  💡 권장: 체크포인트 저장/로드 타이밍 확인")
        else:
            print("  ✅ 모든 전환에서 전이학습 정상 작동")
    
    print()
    print("=" * 80)


def analyze_from_manual_data():
    """수동으로 관찰한 데이터를 기반으로 분석
    
    그래프에서 육안으로 확인한 값들을 기반으로 분석
    """
    
    # 그래프에서 관찰한 대략적인 값들 (이동평균 기준)
    stages_data = [
        {
            "name": "초급 (skill=0.1, Ep 1-500)",
            "skill": 0.1,
            "rewards": {"early": 200, "late": 250},
            "survival": {"early": 350, "late": 400},
            "kills": {"early": 3.0, "late": 3.5},
            "scores": {"early": 300, "late": 350},
        },
        {
            "name": "중하급 (skill=0.3, Ep 501-1000)",
            "skill": 0.3,
            "rewards": {"early": 150, "late": 200},
            "survival": {"early": 350, "late": 400},
            "kills": {"early": 3.0, "late": 4.0},
            "scores": {"early": 300, "late": 350},
        },
        {
            "name": "중상급 (skill=0.6, Ep 1001-1500)",
            "skill": 0.6,
            "rewards": {"early": 100, "late": 130},
            "survival": {"early": 400, "late": 450},
            "kills": {"early": 3.5, "late": 4.0},
            "scores": {"early": 320, "late": 360},
        },
        {
            "name": "고급 (skill=1.0, Ep 1501-2000)",
            "skill": 1.0,
            "rewards": {"early": 75, "late": 80},
            "survival": {"early": 430, "late": 450},
            "kills": {"early": 3.5, "late": 4.0},
            "scores": {"early": 350, "late": 380},
        },
    ]
    
    print("📈 수동 데이터 기반 분석")
    print("(그래프 이미지에서 육안으로 확인한 이동평균 값 기준)")
    print()
    
    # 스테이지별 분석
    stage_analyses = []
    for stage in stages_data:
        analyses = []
        for metric in ["rewards", "survival", "kills", "scores"]:
            early = stage[metric]["early"]
            late = stage[metric]["late"]
            improvement = late - early
            improvement_pct = (improvement / early * 100) if early != 0 else 0
            
            analyses.append({
                "stage": stage["name"],
                "metric": metric.capitalize(),
                "initial_avg": early,
                "final_avg": late,
                "improvement": improvement,
                "improvement_percent": improvement_pct,
                "learning_happening": improvement > 0,
                "data_points": 500,
            })
        stage_analyses.append(analyses)
    
    # 전환 분석
    transition_analyses = []
    for i in range(len(stages_data) - 1):
        prev_stage = stages_data[i]
        next_stage = stages_data[i + 1]
        
        analyses = []
        for metric in ["rewards", "survival", "kills", "scores"]:
            prev_end = prev_stage[metric]["late"]
            next_start = next_stage[metric]["early"]
            change = next_start - prev_end
            change_pct = (change / prev_end * 100) if prev_end != 0 else 0
            
            # 전이학습이 작동하면 성능이 유지되거나 약간만 떨어져야 함
            # 10% 이상 떨어지면 문제로 판단
            working = change >= -prev_end * 0.1
            
            analyses.append({
                "metric": metric.capitalize(),
                "prev_stage_end_avg": prev_end,
                "next_stage_start_avg": next_start,
                "change": change,
                "change_percent": change_pct,
                "transfer_working": working,
            })
        
        transition_analyses.append(analyses)
    
    print_analysis_report(stage_analyses, transition_analyses)
    
    # 추가 관찰 사항
    print("\n📝 4. 추가 관찰 사항")
    print("-" * 80)
    print()
    print("▶ 보상(Reward) 패턴:")
    print("  • 초급: MA ~250 수준으로 안정")
    print("  • 중하급: MA ~200으로 하락 (40% 감소) ❌")
    print("  • 중상급: MA ~130으로 추가 하락 (35% 감소) ❌")
    print("  • 고급: MA ~80으로 추가 하락 (38% 감소) ❌")
    print("  ⚠️  스킬 레벨이 올라갈수록 보상이 급격히 감소")
    print("  💡 이유: 목표값이 너무 높아서 달성률이 낮아짐")
    print()
    print("▶ 생존 시간(Survival) 패턴:")
    print("  • 모든 스테이지에서 MA ~400 수준으로 비슷함")
    print("  • 스킬 레벨과 무관하게 일정한 생존 시간 유지")
    print("  ✅ 생존 능력은 학습되었으나 더 이상 개선되지 않음")
    print()
    print("▶ 킬(Kills) 패턴:")
    print("  • 모든 스테이지에서 MA ~3.5 수준으로 비슷함")
    print("  • 목표값(초급 3킬 → 고급 30킬)과 실제 성능 간 큰 격차")
    print("  ❌ 공격 능력이 전혀 개선되지 않음")
    print()
    print("▶ 점수(Scores) 패턴:")
    print("  • 약간의 개선은 있으나 매우 느림")
    print("  • 변동폭이 매우 크고 불안정함")
    print()
    
    print("=" * 80)
    print()
    print("🎯 5. 최종 결론")
    print("-" * 80)
    print()
    print("✅ 긍정적인 점:")
    print("  1. 초급 스테이지에서 기본적인 학습은 진행됨")
    print("  2. 생존 시간이 ~400 스텝 수준으로 안정화")
    print("  3. 체크포인트가 각 스테이지별로 저장됨")
    print()
    print("❌ 문제점:")
    print("  1. 전이학습 효과가 명확하지 않음")
    print("     - 다음 스테이지 초반 성능이 이전보다 낮거나 비슷함")
    print("     - 보상이 스테이지마다 급격히 감소")
    print("  2. 고난이도 스테이지일수록 보상이 낮아짐")
    print("     - 목표값이 너무 높아서 달성 불가능")
    print("     - 학습 신호가 약해져서 개선이 느림")
    print("  3. 킬 수가 전혀 증가하지 않음")
    print("     - 초급 목표(3킬)는 달성")
    print("     - 고급 목표(30킬)는 현재 성능의 7.5배로 불가능")
    print()
    print("💡 권장 조치:")
    print("  1. 전이학습 로그 확인")
    print("     - 학습 중 '✅ 전이 학습 성공!' 메시지가 출력되었는지")
    print("     - 체크포인트가 실제로 로드되었는지")
    print("  2. 목표값 조정")
    print("     - 현재 성능(생존 ~400, 킬 ~4)을 기준으로 달성 가능한 목표")
    print("     - 점진적 증가: 초급 400/4 → 중급 500/6 → 고급 700/10")
    print("  3. 보상 구조 개선")
    print("     - 기본 생존 보상 추가")
    print("     - 목표 대비 달성률이 너무 낮으면 보상 스케일 조정")
    print("  4. 하이퍼파라미터 튜닝")
    print("     - 학습률 증가 (현재보다 2-3배)")
    print("     - 엔트로피 계수 증가 (더 많은 탐험)")
    print()
    print("=" * 80)


def main():
    """메인 함수"""
    print()
    analyze_from_manual_data()
    print()
    
    print("📌 다음 단계:")
    print("  1. 전이학습 로그 확인:")
    print("     rye run python -c \"import glob; files = glob.glob('src/logs/*.txt') + glob.glob('*.log'); print('\\n'.join(files) if files else '로그 파일 없음')\"")
    print()
    print("  2. 체크포인트 크기 확인 (실제로 학습되었는지):")
    print("     rye run python -c \"import os; [print(f'{p}: {os.path.getsize(p)/1024:.1f}KB') for p in [")
    print("         'src/src/models/ppo/stages/초급-목표-330스텝-3킬-skill-0.1/latest.pth',")
    print("         'src/src/models/ppo/stages/중하급-목표-590스텝-9킬-skill-0.3/latest.pth',")
    print("         'src/src/models/ppo/stages/중상급-목표-980스텝-18킬-skill-0.6/latest.pth',")
    print("         'src/src/models/ppo/stages/고급-목표-1500스텝-30킬-skill-1.0/latest.pth'") 
    print("     ] if os.path.exists(p)]\"")
    print()


if __name__ == "__main__":
    main()

