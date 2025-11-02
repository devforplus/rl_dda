"""
Skill-level based training targets - Continuous Function Version.

This module provides continuous (smooth) mapping from skill levels (0~1)
to survival step targets for curriculum learning and DDA (Dynamic Difficulty Adjustment).

Key Design:
- Single model learns with discrete skill values (0.1, 0.3, 0.6, 1.0)
- At inference, any continuous skill value (0~1) can be used
- Linear interpolation ensures smooth difficulty scaling
- Enables fine-grained DDA control in production
"""

from __future__ import annotations


def get_survival_target_steps(skill_level: float) -> int:
    """연속적인 skill_level에 대한 생존 목표 스텝 (선형 함수)
    
    커리큘럼 러닝:
    - 학습 시: skill=0.1, 0.3, 0.6, 1.0 네 단계로 학습
    - 추론 시: skill=0~1 사이 임의의 값 사용 가능
    
    선형 보간 공식 (사람 수준 목표):
    - target_steps = 200 + 1800 * skill_level
    
    주요 기준점:
    - skill=0.0: 200 스텝
    - skill=0.1: 380 스텝
    - skill=0.3: 740 스텝
    - skill=0.5: 1100 스텝
    - skill=0.6: 1280 스텝
    - skill=1.0: 2000 스텝 ← 사람 수준!
    
    중간 값 예시:
    - skill=0.2: 360 스텝
    - skill=0.7: 760 스텝
    
    DDA 활용:
    - 플레이어 실력 측정 후 적절한 skill 값으로 에이전트 호출
    - 부드러운 난이도 전환 가능
    
    Args:
        skill_level: 실력/난이도 레벨 (0.0 ~ 1.0)
    
    Returns:
        목표 생존 스텝 수 (연속 함수)
    """
    # 클램핑 (안전장치)
    skill_level = max(0.0, min(1.0, skill_level))
    
    # 선형 보간: y = 200 + 1800*x (사람 수준 목표)
    base_steps = 200
    skill_bonus = 1800 * skill_level
    
    return int(base_steps + skill_bonus)


def get_kill_target(skill_level: float) -> float:
    """연속적인 skill_level에 대한 킬 목표 (선형 함수)
    
    선형 보간 공식 (사람 수준 목표):
    - target_kills = 15 * skill_level
    
    주요 기준점:
    - skill=0.0: 0 킬
    - skill=0.1: 1.5 킬
    - skill=0.3: 4.5 킬
    - skill=0.5: 7.5 킬
    - skill=0.6: 9 킬
    - skill=1.0: 15 킬 ← 사람 수준!
    
    Args:
        skill_level: 실력/난이도 레벨 (0.0 ~ 1.0)
    
    Returns:
        목표 킬 수 (연속 함수)
    """
    skill_level = max(0.0, min(1.0, skill_level))
    return 15.0 * skill_level
