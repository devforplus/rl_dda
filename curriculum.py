"""
커리큘럼 러닝 스케줄러

에피소드 번호와 최근 학습 통계를 기반으로 skill_level을 결정하여
환경 보상 함수의 목표(생존/공격)를 점진적으로 상향 조정할 수 있도록 합니다.
"""

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
