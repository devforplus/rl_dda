#!/usr/bin/env python3
"""
새로운 weighted sum 보상함수 로직 단독 테스트

의존성 없이 보상 계산 로직만 테스트합니다.
"""


def calculate_new_reward(
    current_step: int, current_kills: int, current_lives: int, skill_level: float
) -> float:
    """새로운 weighted sum 기반 보상 계산 로직"""

    # 실력값 기반 적응적 목표 설정
    target_survival_steps = 200 + (skill_level * 1200)  # 200 ~ 1400 스텝
    target_kill_rate = skill_level * 3.0  # 0 ~ 3 킬/100스텝

    # === 1. 생존 지표 (Survival Score) ===
    survival_score = min(1.0, current_step / target_survival_steps)

    # === 2. 공격 지표 (Attack Score) ===
    if current_step > 0 and target_kill_rate > 0:
        current_kill_rate = (current_kills / max(current_step, 1)) * 100.0  # 킬/100스텝
        attack_score = min(1.0, current_kill_rate / target_kill_rate)
    else:
        attack_score = 0.0

    # === 3. 일관성 지표 (Consistency Score) ===
    # 실력값에 맞는 성과를 얼마나 일관성 있게 유지하는지 측정
    if current_step > 0:
        # 생존 목표 달성률
        survival_achievement = min(1.0, current_step / target_survival_steps)

        # 공격 목표 달성률 (target_kill_rate가 0인 경우 처리)
        if target_kill_rate > 0:
            current_kill_rate = (current_kills / max(current_step, 1)) * 100.0
            attack_achievement = min(1.0, current_kill_rate / target_kill_rate)
        else:
            attack_achievement = 1.0  # 목표가 0이면 완벽 달성으로 간주

        # 일관성 = 두 달성률이 얼마나 균형잡혀 있는지 (편차가 작을수록 좋음)
        achievement_difference = abs(survival_achievement - attack_achievement)

        # 일관성 점수: 편차가 작을수록 높은 점수 (0.0 ~ 1.0)
        consistency_score = max(0.0, 1.0 - achievement_difference)

        # 추가 보정: 둘 다 목표를 달성한 경우 보너스
        if survival_achievement >= 0.8 and attack_achievement >= 0.8:
            consistency_score = min(1.0, consistency_score + 0.2)  # 보너스 추가
    else:
        consistency_score = 1.0  # 초기 상태는 완벽한 일관성

    # === Weighted Sum ===
    w_survival = 0.4  # 생존 중요도
    w_attack = 0.4  # 공격 중요도
    w_consistency = 0.2  # 일관성 중요도

    # 최종 보상 계산 (0.0 ~ 1.0 스케일)
    final_reward = (
        w_survival * survival_score
        + w_attack * attack_score
        + w_consistency * consistency_score
    )

    return final_reward, survival_score, attack_score, consistency_score


def test_reward_scenarios():
    """다양한 시나리오에서 새로운 보상함수 테스트"""

    print("🧪 새로운 Weighted Sum 보상함수 테스트")
    print("=" * 70)

    # 테스트 시나리오들
    scenarios = [
        # (skill_level, step, kills, lives, description)
        (0.0, 100, 0, 3, "초보자 - 100스텝 생존, 킬 없음"),
        (0.0, 200, 1, 3, "초보자 - 목표 달성, 킬 1개"),
        (0.5, 400, 2, 3, "중급자 - 50% 생존, 킬 2개"),
        (0.5, 800, 6, 3, "중급자 - 목표 달성, 킬 6개"),
        (1.0, 700, 10, 3, "고급자 - 50% 생존, 킬 10개"),
        (1.0, 1400, 42, 3, "고급자 - 완벽한 성과"),
        (0.5, 400, 3, 2, "중급자 - 생명 1개 손실"),
        (0.5, 400, 3, 1, "중급자 - 생명 2개 손실"),
        (0.5, 400, 3, 0, "중급자 - 모든 생명 손실"),
    ]

    for skill_level, step, kills, lives, description in scenarios:
        reward, survival, attack, consistency = calculate_new_reward(
            step, kills, lives, skill_level
        )

        # 목표값 계산 (참고용)
        target_survival = 200 + (skill_level * 1200)
        target_kill_rate = skill_level * 3.0
        current_kill_rate = (kills / max(step, 1)) * 100.0 if step > 0 else 0.0

        print(f"\n📊 {description}")
        print(
            f"   스킬값: {skill_level:.1f} | 스텝: {step} | 킬: {kills} | 생명: {lives}"
        )
        print(
            f"   목표: 생존 {target_survival:.0f}스텝, 킬레이트 {target_kill_rate:.1f}/100스텝"
        )
        print(f"   현재 킬레이트: {current_kill_rate:.2f}/100스텝")
        print(
            f"   🔹 생존점수: {survival:.3f} | 공격점수: {attack:.3f} | 일관성점수: {consistency:.3f}"
        )
        print(f"   🎯 최종보상: {reward:.3f}")


def test_skill_progression():
    """실력값에 따른 보상 변화 분석"""

    print("\n\n🎯 실력값별 보상 변화 분석")
    print("=" * 70)

    # 고정 성과로 실력값별 보상 비교
    fixed_step = 600
    fixed_kills = 8
    fixed_lives = 3

    print(f"고정 성과: {fixed_step}스텝, {fixed_kills}킬, {fixed_lives}생명")
    print("-" * 50)

    for skill_level in [0.0, 0.25, 0.5, 0.75, 1.0]:
        reward, survival, attack, consistency = calculate_new_reward(
            fixed_step, fixed_kills, fixed_lives, skill_level
        )

        target_survival = 200 + (skill_level * 1200)
        target_kill_rate = skill_level * 3.0

        print(f"스킬값 {skill_level:.2f}: 보상 {reward:.3f}")
        print(f"  목표: 생존{target_survival:.0f} 킬{target_kill_rate:.1f}/100")
        print(f"  점수: 생존{survival:.2f} 공격{attack:.2f} 일관성{consistency:.2f}")


def test_extreme_cases():
    """극단적 케이스 테스트"""

    print("\n\n🔥 극단적 케이스 테스트")
    print("=" * 70)

    extreme_cases = [
        (0.0, 0, 0, 3, "시작 직후"),
        (1.0, 2000, 100, 3, "초고성능 달성"),
        (0.5, 1000, 0, 3, "생존만 극대화 (킬 0)"),
        (0.5, 50, 50, 3, "킬만 극대화 (생존 짧음)"),
        (1.0, 1400, 42, 0, "완벽한 성과지만 모든 생명 손실"),
    ]

    for skill_level, step, kills, lives, description in extreme_cases:
        reward, survival, attack, consistency = calculate_new_reward(
            step, kills, lives, skill_level
        )

        print(f"\n🔥 {description}")
        print(f"   설정: 스킬{skill_level} 스텝{step} 킬{kills} 생명{lives}")
        print(f"   점수: 생존{survival:.3f} 공격{attack:.3f} 일관성{consistency:.3f}")
        print(f"   🎯 최종보상: {reward:.3f}")


if __name__ == "__main__":
    test_reward_scenarios()
    test_skill_progression()
    test_extreme_cases()

    print("\n\n✅ 새로운 보상함수 로직 테스트 완료!")
    print("\n🎯 주요 특징:")
    print("- 연속적 보상 신호 (조건부 임계값 없음)")
    print("- 실력값 기반 적응적 목표 설정")
    print("- 3지표 균형잡힌 평가 (생존 40% + 공격 40% + 일관성 20%)")
    print("- 0.0~1.0 정규화된 보상 범위")
    print("- 다양한 플레이 스타일 허용")
