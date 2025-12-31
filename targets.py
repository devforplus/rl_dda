"""
Skill-level based training targets.

This module centralizes the mapping from skill levels to survival step targets
so the same logic is used consistently across reward calculation and state
vector construction.

선형 커리큘럼 러닝을 위해 연속 수식을 사용합니다:
- T_target(skill) = 300 + (skill - 0.1) * 1333.33
- K_target_rate(skill) = skill * 3.0
"""

from __future__ import annotations


def get_survival_target_steps(skill_level: float) -> float:
    """실력값에 따른 생존 목표 스텝 계산 (연속 선형 함수)
    
    수식: T_target(skill) = 300 + (skill - 0.1) * (1500 - 300) / (1.0 - 0.1)
    
    결과:
    - skill 0.1 → 300 스텝
    - skill 0.5 → 833 스텝
    - skill 1.0 → 1500 스텝
    
    Args:
        skill_level: 실력값 (0.0 ~ 1.0)
        
    Returns:
        목표 생존 스텝 수
    """
    # 선형 보간: 0.1(300) ~ 1.0(1500)
    return 300.0 + (skill_level - 0.1) * (1500.0 - 300.0) / (1.0 - 0.1)


def get_kill_target_rate(skill_level: float) -> float:
    """실력값에 따른 목표 킬 효율 계산
    
    수식: K_target_rate(skill) = skill * 3.0
    
    결과:
    - skill 0.1 → 0.3 kills/100steps
    - skill 0.5 → 1.5 kills/100steps
    - skill 1.0 → 3.0 kills/100steps
    
    Args:
        skill_level: 실력값 (0.0 ~ 1.0)
        
    Returns:
        목표 킬 효율 (kills per 100 steps)
    """
    return skill_level * 3.0

