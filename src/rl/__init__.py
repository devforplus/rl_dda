"""
새로운 PPO 강화학습 모듈

게임 로그 데이터와 실력값을 입력으로 받는 PPO 모델을 구현합니다.
"""

from .data_types import GameLogData, PlayerState, ActionType
from .environment import GameEnvironment
from .ppo_agent import PPOAgent
from .trainer import PPOTrainer
from .curriculum import (
    CurriculumStage,
    StepCurriculum,
    LinearCurriculum,
    ExponentialCurriculum,
    SigmoidCurriculum,
    PolynomialCurriculum,
)
from .adaptive_curriculum import AdaptiveCurriculum, AdaptiveStage
from .goal_based_curriculum import GoalBasedCurriculum, GoalBasedStage
from .convergence_based_curriculum import ConvergenceBasedCurriculum, ConvergenceStage

__all__ = [
    "GameLogData",
    "PlayerState",
    "ActionType",
    "GameEnvironment",
    "PPOAgent",
    "PPOTrainer",
    "CurriculumStage",
    "StepCurriculum",
    "LinearCurriculum",
    "ExponentialCurriculum",
    "SigmoidCurriculum",
    "PolynomialCurriculum",
    "AdaptiveCurriculum",
    "AdaptiveStage",
    "GoalBasedCurriculum",
    "GoalBasedStage",
    "ConvergenceBasedCurriculum",
    "ConvergenceStage",
]
