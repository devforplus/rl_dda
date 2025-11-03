"""
커리큘럼 러닝 스케줄러

에피소드 번호와 최근 학습 통계를 기반으로 skill_level을 결정하여
환경 보상 함수의 목표(생존/공격)를 점진적으로 상향 조정할 수 있도록 합니다.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class CurriculumStage:
    """단계형 커리큘럼의 단일 스테이지 정의.

    Attributes:
        num_episodes: 이 단계에 머무를 에피소드 수
        skill_level: 단계 동안 사용할 skill level (0.0 ~ 1.0)
        name: 단계의 설명 이름 (로그용)
    """

    num_episodes: int
    skill_level: float
    name: str


class StepCurriculum:
    """에피소드 구간별로 고정 skill_level을 적용하는 단계형 스케줄러."""

    def __init__(self, stages: List[CurriculumStage]):
        if not stages:
            raise ValueError("stages must not be empty")
        self.stages = stages

        # 누적 에피소드 경계 계산
        self._boundaries: List[int] = []
        cumulative = 0
        for stage in stages:
            cumulative += stage.num_episodes
            self._boundaries.append(cumulative)

    def skill_for_episode(self, episode_index: int) -> Tuple[float, str]:
        """주어진 0-based episode index에 대한 (skill_level, stage_name)을 반환."""
        if episode_index < 0:
            episode_index = 0
        for idx, boundary in enumerate(self._boundaries):
            if episode_index < boundary:
                stage = self.stages[idx]
                return stage.skill_level, stage.name
        # 범위를 넘어가면 마지막 단계 유지
        last = self.stages[-1]
        return last.skill_level, last.name


class LinearCurriculum:
    """전체 에피소드에 걸쳐 skill_level을 선형으로 증가시키는 스케줄러."""

    def __init__(
        self,
        start_skill: float,
        end_skill: float,
        total_episodes: int,
        name: str = "Linear",
    ):
        if total_episodes <= 0:
            raise ValueError("total_episodes must be > 0")
        self.start_skill = max(0.0, min(1.0, start_skill))
        self.end_skill = max(0.0, min(1.0, end_skill))
        self.total_episodes = total_episodes
        self.name = name

    def skill_for_episode(self, episode_index: int) -> Tuple[float, str]:
        if episode_index <= 0:
            return self.start_skill, self.name
        if episode_index >= self.total_episodes:
            return self.end_skill, self.name
        t = episode_index / float(self.total_episodes)
        skill = self.start_skill + (self.end_skill - self.start_skill) * t
        return max(0.0, min(1.0, skill)), self.name


class ExponentialCurriculum:
    """지수 함수로 skill_level을 증가시키는 스케줄러.
    
    초반에는 빠르게 증가하고, 후반에는 천천히 증가합니다.
    기초를 빠르게 학습하고 고급 단계에 더 많은 시간을 할애하는 전략입니다.
    """

    def __init__(
        self,
        start_skill: float = 0.1,
        end_skill: float = 1.0,
        total_episodes: int = 2000,
        rate: float = 3.0,
        name: str = "Exponential",
    ):
        """
        Args:
            start_skill: 시작 스킬 레벨
            end_skill: 종료 스킬 레벨
            total_episodes: 전체 에피소드 수
            rate: 증가 속도 (1.0-5.0 권장, 3.0이 적당)
            name: 커리큘럼 이름
        """
        if total_episodes <= 0:
            raise ValueError("total_episodes must be > 0")
        self.start_skill = max(0.0, min(1.0, start_skill))
        self.end_skill = max(0.0, min(1.0, end_skill))
        self.total_episodes = total_episodes
        self.rate = max(0.1, rate)
        self.name = name

    def skill_for_episode(self, episode_index: int) -> Tuple[float, str]:
        if episode_index <= 0:
            return self.start_skill, self.name
        if episode_index >= self.total_episodes:
            return self.end_skill, self.name

        t = episode_index / float(self.total_episodes)
        # 지수 함수: 1 - exp(-rate * t)
        # rate=3.0일 때, t=0.5에서 ~0.78까지 도달
        progress = 1.0 - math.exp(-self.rate * t)
        skill = self.start_skill + (self.end_skill - self.start_skill) * progress
        return max(0.0, min(1.0, skill)), self.name


class SigmoidCurriculum:
    """시그모이드(S자) 곡선으로 skill_level을 증가시키는 스케줄러.
    
    처음과 끝은 천천히, 중간은 빠르게 증가합니다.
    가장 부드러운 전환을 제공합니다.
    """

    def __init__(
        self,
        start_skill: float = 0.1,
        end_skill: float = 1.0,
        total_episodes: int = 2000,
        steepness: float = 12.0,
        name: str = "Sigmoid",
    ):
        """
        Args:
            start_skill: 시작 스킬 레벨
            end_skill: 종료 스킬 레벨
            total_episodes: 전체 에피소드 수
            steepness: 기울기 (6.0-15.0 권장, 12.0이 적당)
            name: 커리큘럼 이름
        """
        if total_episodes <= 0:
            raise ValueError("total_episodes must be > 0")
        self.start_skill = max(0.0, min(1.0, start_skill))
        self.end_skill = max(0.0, min(1.0, end_skill))
        self.total_episodes = total_episodes
        self.steepness = max(1.0, steepness)
        self.name = name

    def skill_for_episode(self, episode_index: int) -> Tuple[float, str]:
        if episode_index <= 0:
            return self.start_skill, self.name
        if episode_index >= self.total_episodes:
            return self.end_skill, self.name

        t = episode_index / float(self.total_episodes)
        # Sigmoid: 1 / (1 + exp(-steepness * (t - 0.5)))
        # 중심을 0.5로 하여 대칭적인 S자 곡선
        progress = 1.0 / (1.0 + math.exp(-self.steepness * (t - 0.5)))
        skill = self.start_skill + (self.end_skill - self.start_skill) * progress
        return max(0.0, min(1.0, skill)), self.name


class PolynomialCurriculum:
    """다항 함수로 skill_level을 증가시키는 스케줄러.
    
    degree=2: 점진적으로 가속 (처음 느리게, 후반 빠르게)
    degree=3: S자와 유사하지만 더 부드러움
    """

    def __init__(
        self,
        start_skill: float = 0.1,
        end_skill: float = 1.0,
        total_episodes: int = 2000,
        degree: float = 2.0,
        name: str = "Polynomial",
    ):
        """
        Args:
            start_skill: 시작 스킬 레벨
            end_skill: 종료 스킬 레벨
            total_episodes: 전체 에피소드 수
            degree: 다항식 차수 (1.0=선형, 2.0=이차, 3.0=삼차)
            name: 커리큘럼 이름
        """
        if total_episodes <= 0:
            raise ValueError("total_episodes must be > 0")
        self.start_skill = max(0.0, min(1.0, start_skill))
        self.end_skill = max(0.0, min(1.0, end_skill))
        self.total_episodes = total_episodes
        self.degree = max(0.5, degree)
        self.name = name

    def skill_for_episode(self, episode_index: int) -> Tuple[float, str]:
        if episode_index <= 0:
            return self.start_skill, self.name
        if episode_index >= self.total_episodes:
            return self.end_skill, self.name

        t = episode_index / float(self.total_episodes)
        progress = math.pow(t, self.degree)
        skill = self.start_skill + (self.end_skill - self.start_skill) * progress
        return max(0.0, min(1.0, skill)), self.name
