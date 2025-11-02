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
    
    선형 보간 공식 (학습 가능한 목표로 재조정):
    - target_steps = 200 + 600 * skill_level
    
    주요 기준점:
    - skill=0.0: 200 스텝
    - skill=0.1: 260 스텝 (기존 280)
    - skill=0.3: 380 스텝 (기존 440)
    - skill=0.5: 500 스텝 (기존 600)
    - skill=0.6: 560 스텝 (기존 680) ← 달성 가능!
    - skill=1.0: 800 스텝 (기존 1000) ← 현실적!
    
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
    
    # 선형 보간: y = 200 + 600*x (학습 가능한 목표)
    base_steps = 200
    skill_bonus = 600 * skill_level
    
    return int(base_steps + skill_bonus)


def get_kill_target(skill_level: float) -> float:
    """연속적인 skill_level에 대한 킬 목표 (선형 함수)
    
    선형 보간 공식 (학습 가능한 목표로 재조정):
    - target_kills = 8 * skill_level
    
    주요 기준점:
    - skill=0.0: 0 킬
    - skill=0.1: 0.8 킬 (기존 1.2)
    - skill=0.3: 2.4 킬 (기존 3.6)
    - skill=0.5: 4 킬 (기존 6)
    - skill=0.6: 4.8 킬 (기존 7.2) ← 달성 가능!
    - skill=1.0: 8 킬 (기존 12) ← 현실적!
    
    Args:
        skill_level: 실력/난이도 레벨 (0.0 ~ 1.0)
    
    Returns:
        목표 킬 수 (연속 함수)
    """
    skill_level = max(0.0, min(1.0, skill_level))
    return 8.0 * skill_level
