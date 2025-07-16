import numpy as np
import torch
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import IntEnum
from collections import deque

from components.entity_types import EntityType


class ActionType(IntEnum):
    """PPO 에이전트가 사용할 액션 타입 정의

    8방향 이동 + 공격 = 총 9개 액션

    ---

    PPO 에이전트의 액션 공간을 정의하는 열거형
    """

    LEFT_UP = 0  # 좌상단
    UP = 1  # 상단
    RIGHT_UP = 2  # 우상단
    LEFT = 3  # 좌측
    RIGHT = 4  # 우측
    LEFT_DOWN = 5  # 좌하단
    DOWN = 6  # 하단
    RIGHT_DOWN = 7  # 우하단
    FIRE = 8  # 공격


@dataclass
class EntityData:
    """게임 엔티티의 데이터를 나타내는 클래스

    Attributes:
        entity_type: 엔티티 타입 (EntityType enum)
        x, y: 위치 좌표
        w, h: 크기
        distance_to_player: 플레이어와의 거리

    ---

    객체 탐지 모델에서 추출된 엔티티 정보를 저장
    """

    entity_type: EntityType
    x: float
    y: float
    w: float
    h: float
    distance_to_player: float = 0.0


@dataclass
class GameState:
    """게임 상태를 나타내는 클래스

    Attributes:
        entities: 화면 속 모든 엔티티 리스트
        skill_level: 실력 값 (0~1)
        personality: 성향 (0: 방어적, 1: 공격적)
        player_hp: 플레이어 체력
        player_lives: 플레이어 목숨 수
        score: 현재 점수
        survival_time: 생존 시간
        kills: 적 처치 수
        current_stage: 현재 스테이지 번호
        game_cleared: 게임 클리어 여부

    ---

    PPO 모델의 입력으로 사용될 게임 상태 정보
    """

    entities: List[EntityData]
    skill_level: float
    personality: int
    player_hp: int
    player_lives: int
    score: int
    survival_time: int
    kills: int
    current_stage: int  # 현재 스테이지 번호
    game_cleared: bool  # 게임 클리어 여부


class GameEnvironment:
    """게임과 PPO 에이전트 간의 브리지 역할을 하는 환경 클래스

    게임 상태를 추출하고 PPO 모델의 입력으로 변환하며,
    에이전트의 액션에 따른 보상을 계산합니다.

    ---

    Reinforcement Learning 환경의 표준 인터페이스를 제공
    """

    def __init__(
        self, max_entities: int = 50, max_lives: int = 1, final_stage_num: int = 5
    ):
        """환경 초기화

        Args:
            max_entities: 한 번에 처리할 최대 엔티티 수
            max_lives: 플레이어의 최대 목숨 수 (정규화용) - 1로 변경
            final_stage_num: 마지막 스테이지 번호 (정규화용)

        ---

        게임 환경을 초기화하고 상태/액션 공간을 설정
        """
        self.max_entities = max_entities
        self.max_lives = max_lives  # 최대 목숨 수 저장 (1로 변경)
        self.final_stage_num = final_stage_num  # 마지막 스테이지 번호 저장

        # 엔티티당 특성: [type_id, x, y, w, h, distance_to_player] = 6개
        self.entity_feature_size = 6

        # 전체 상태 크기: 엔티티 특성 + 게임 메타 정보
        # 엔티티: max_entities * entity_feature_size
        # 메타: [skill_level, personality, player_hp, player_lives, score, survival_time, kills, current_stage, game_cleared] = 9개
        self.state_size = (
            self.max_entities * self.entity_feature_size + 9
        )  # current_stage, game_cleared 추가로 +2

        # 액션 공간: 8방향 이동 + 공격 = 9개
        self.action_size = 9

        # 이전 상태 추적 (보상 계산용)
        self.previous_state = None
        self.action_history = []
        self.max_action_history = 10

        # Catastrophic Forgetting 방지를 위한 안정화 시스템
        self.episode_count = 0
        self.reward_history: List[float] = []  # 최근 보상 기록
        self.performance_baseline = 0.0  # 성능 기준선
        self.stability_factor = 1.0  # 안정성 계수
        self.max_reward_history = 50  # 최근 50 에피소드 기록

        # 점진적 학습을 위한 커리큘럼 시스템
        self.curriculum_stage = 1  # 현재 커리큘럼 단계
        self.success_threshold = 0.7  # 성공 기준 (70% 이상 성능 유지)
        self.consecutive_successes = 0  # 연속 성공 횟수

        # 보상 계산을 위한 상태 변수 초기화
        self.last_score = 0
        self.last_lives = 3  # 초기 목숨 값으로 가정

        # 성능 추적
        self.performance_tracker = deque(maxlen=100)
        self.stability_factor = 1.0

        # 개선된 생존 마일스톤 (훨씬 더 세분화)
        self.early_survival_milestones = [
            (60, 10.0),  # 1초 - 첫 생존
            (120, 15.0),  # 2초 - 기본 생존
            (180, 25.0),  # 3초 - 안정적 생존
            (240, 40.0),  # 4초 - 좋은 생존
            (300, 60.0),  # 5초 - 우수한 생존
            (420, 80.0),  # 7초 - 뛰어난 생존
            (600, 120.0),  # 10초 - 탁월한 생존
            (900, 200.0),  # 15초 - 마스터 레벨
            (1200, 300.0),  # 20초 - 전문가 레벨
        ]

        # 배속 모드 지원 (기본값 1 = 정상 속도)
        self.speed_multiplier = 1

        self.reset()

    def _convert_survival_time_to_seconds(self, survival_time_frames: int) -> float:
        """배속 모드를 고려하여 survival_time을 실제 초 단위로 변환

        Args:
            survival_time_frames: 프레임 단위 생존 시간

        Returns:
            실제 생존 시간 (초)

        ---

        배속 모드에서는 게임이 빠르게 진행되므로,
        실제 생존 시간은 프레임 수를 (60 * speed_multiplier)로 나눈 값입니다.
        """
        return survival_time_frames / (60.0 * self.speed_multiplier)

    def encode_state(self, game_state: GameState) -> torch.Tensor:
        """게임 상태를 신경망 입력용 벡터로 인코딩

        Args:
            game_state: 현재 게임 상태

        Returns:
            인코딩된 상태 벡터 (torch.Tensor)

        ---

        게임 상태를 고정 크기의 벡터로 변환하여 신경망에 입력
        """
        # 엔티티 데이터 인코딩
        entity_features = np.zeros((self.max_entities, self.entity_feature_size))

        for i, entity in enumerate(game_state.entities[: self.max_entities]):
            entity_features[i] = [
                float(entity.entity_type.value),  # 엔티티 타입 ID
                entity.x / 256.0,  # 정규화된 x 좌표 (0~1)
                entity.y / 256.0,  # 정규화된 y 좌표 (0~1)
                entity.w / 32.0,  # 정규화된 너비
                entity.h / 32.0,  # 정규화된 높이
                entity.distance_to_player / 300.0,  # 정규화된 플레이어 거리
            ]

        # 플랫한 엔티티 벡터로 변환
        entity_vector = entity_features.flatten()

        # 게임 메타 정보 인코딩
        meta_features = np.array(
            [
                game_state.skill_level,  # 실력 값 (0~1)
                float(game_state.personality),  # 성향 (0 or 1)
                game_state.player_hp / 2.0,  # 정규화된 플레이어 체력 (최대 2로 변경)
                game_state.player_lives
                / float(self.max_lives),  # 정규화된 플레이어 목숨
                game_state.score / 100000.0,  # 정규화된 점수
                game_state.survival_time / 10000.0,  # 정규화된 생존 시간
                game_state.kills / 100.0,  # 정규화된 처치 수
                game_state.current_stage
                / float(self.final_stage_num),  # 정규화된 현재 스테이지
                float(game_state.game_cleared),  # 게임 클리어 여부 (0.0 또는 1.0)
            ]
        )

        # 전체 상태 벡터 결합
        state_vector = np.concatenate([entity_vector, meta_features])

        return torch.FloatTensor(state_vector)

    def update_performance_tracking(self, episode_reward: float, survival_time: int):
        """성능 추적 및 안정성 계수 업데이트

        Args:
            episode_reward: 에피소드 총 보상
            survival_time: 생존 시간

        ---

        Catastrophic Forgetting 방지를 위한 성능 모니터링
        """
        self.episode_count += 1
        self.reward_history.append(episode_reward)

        # 기록 크기 제한
        if len(self.reward_history) > self.max_reward_history:
            self.reward_history.pop(0)

        # 성능 기준선 업데이트 (최근 20 에피소드 평균)
        if len(self.reward_history) >= 20:
            recent_avg = np.mean(self.reward_history[-20:])
            self.performance_baseline = recent_avg

            # 안정성 계수 계산 (성능 변동성 기반)
            recent_std = np.std(self.reward_history[-20:])
            if recent_std > 0:
                stability_ratio = abs(recent_avg) / (recent_std + 1e-6)
                self.stability_factor = min(1.5, max(0.5, stability_ratio / 10.0))

            # 연속 성공 여부 판단 (최근 5 에피소드가 기준선 이상)
            if len(self.reward_history) >= 5:
                recent_performance = np.mean(self.reward_history[-5:])
                if (
                    recent_performance
                    >= self.performance_baseline * self.success_threshold
                ):
                    self.consecutive_successes += 1
                else:
                    self.consecutive_successes = 0

            # 커리큘럼 진행 (10회 연속 성공 시 다음 단계)
            if self.consecutive_successes >= 10 and self.curriculum_stage < 5:
                self.curriculum_stage += 1
                self.consecutive_successes = 0
                print(f"🎓 Curriculum advanced to stage {self.curriculum_stage}")

    def calculate_reward(self, game_state: GameState, last_action: int) -> float:
        """
        대폭 개선된 보상 시스템 - 초기 학습 효율성 극대화

        핵심 개선사항:
        1. 생존 보상 10배 증가 (0.01 → 0.1)
        2. 초기 마일스톤 대폭 세분화 (1초부터 시작)
        3. 사망 페널티 50% 감소 (-100 → -50)
        4. 단순하고 직관적인 구조

        Args:
            game_state: 현재 게임 상태
            last_action: 에이전트가 마지막으로 취한 행동

        Returns:
            계산된 보상 값
        """
        total_reward = 0.0

        # 1. 기본 생존 보상 (10배 증가)
        survival_reward = 0.1  # 0.01 → 0.1 (1000% 증가)
        total_reward += survival_reward

        # 2. 초기 생존 마일스톤 보상 (세분화)
        if self.previous_state is not None:
            for milestone_time, milestone_reward in self.early_survival_milestones:
                if (
                    self.previous_state.survival_time
                    < milestone_time
                    <= game_state.survival_time
                ):
                    total_reward += milestone_reward
                    print(
                        f"🎉 SURVIVAL MILESTONE: +{milestone_reward:.1f} ({milestone_time / 60:.1f}s)"
                    )

        # 3. 점수 증가 보상 (2배 증가)
        if game_state.score > self.last_score:
            score_reward = (
                game_state.score - self.last_score
            ) * 0.2  # 0.1 → 0.2 (2배 증가)
            total_reward += score_reward
            print(f"📈 SCORE: +{score_reward:.1f}")

        # 4. 감소된 사망 페널티 (50% 감소)
        if game_state.player_lives < self.last_lives:
            death_penalty = -50.0  # -100.0 → -50.0 (50% 감소)
            total_reward += death_penalty
            print(f"💀 DEATH PENALTY: {death_penalty:.1f}")

        # 5. 공격 행동 보상 (적극적 플레이 장려)
        if last_action == ActionType.FIRE:
            fire_reward = 0.5
            total_reward += fire_reward

        # 상태 업데이트
        self.last_score = game_state.score
        self.last_lives = game_state.player_lives
        self.previous_state = game_state

        return total_reward

    def _calculate_reward_complex(
        self, game_state: GameState, last_action: int
    ) -> float:
        """복잡한 보상 시스템 (백업용)

        기존의 복잡한 보상 계산 로직을 백업으로 보관합니다.
        필요시 다시 사용할 수 있도록 유지합니다.

        Args:
            game_state: 현재 게임 상태
            last_action: 에이전트가 마지막으로 취한 행동

        Returns:
            계산된 보상 값
        """
        skill = game_state.skill_level
        total_reward = 0.0

        # 실력별 기대 성과 기준치 설정
        if skill < 0.3:  # 초보자
            expected_survival = 300  # 5분 (300초)
            expected_kills_per_min = 0.5
            survival_multiplier = 2.0  # 생존 자체가 큰 성취
            kill_base_reward = 50.0
        elif skill < 0.7:  # 중급자
            expected_survival = 600  # 10분 (600초)
            expected_kills_per_min = 1.0
            survival_multiplier = 1.5
            kill_base_reward = 30.0
        else:  # 고급자
            expected_survival = 1200  # 20분 이상 (1200초)
            expected_kills_per_min = 2.0
            survival_multiplier = 1.0
            kill_base_reward = 20.0

        # 1. 생존 시간 기반 리워드
        survival_ratio = min(game_state.survival_time / expected_survival, 2.0)
        survival_reward = (1.0 + survival_ratio) * survival_multiplier
        total_reward += survival_reward

        # 2. 킬 효율성 리워드 (이전 상태와 비교)
        if self.previous_state:
            kill_increase = game_state.kills - self.previous_state.kills
            if kill_increase > 0:
                # 현재 킬 레이트가 기대치 대비 얼마나 좋은지 평가 (배속 모드 고려)
                time_minutes = max(
                    self._convert_survival_time_to_seconds(game_state.survival_time)
                    / 60.0,
                    0.1,
                )
                current_kill_rate = game_state.kills / time_minutes
                kill_efficiency = current_kill_rate / expected_kills_per_min

                # 효율성이 높을수록 큰 리워드
                kill_reward = kill_base_reward * kill_increase * (1.0 + kill_efficiency)
                total_reward += kill_reward

                print(
                    f"📈 Skill {skill:.1f}: Kill reward {kill_reward:.1f} (rate: {current_kill_rate:.1f}, efficiency: {kill_efficiency:.1f})"
                )

        # 3. 실력별 차등 피격 페널티
        if self.previous_state and game_state.player_hp < self.previous_state.player_hp:
            # 고실력자일수록 더 엄격한 페널티
            base_penalty = 15.0
            skill_penalty_multiplier = 0.5 + skill * 1.5  # 0.5~2.0
            hit_penalty = base_penalty * skill_penalty_multiplier
            total_reward -= hit_penalty

            print(f"💔 Skill {skill:.1f}: Hit penalty -{hit_penalty:.1f}")

        # 4. 스테이지 진행 보너스 (실력별 차등)
        if self.previous_state:
            stage_increase = (
                game_state.current_stage - self.previous_state.current_stage
            )
            if stage_increase > 0:
                # 고실력자는 스테이지 클리어가 당연하므로 상대적으로 낮은 보너스
                stage_bonus_base = 200.0
                skill_stage_multiplier = 2.0 - skill  # 고실력자: 1.0, 저실력자: 2.0
                stage_reward = (
                    stage_bonus_base * stage_increase * skill_stage_multiplier
                )
                total_reward += stage_reward

                print(f"🏆 Skill {skill:.1f}: Stage clear +{stage_reward:.1f}")

        # 5. 목숨 감소 시 페널티 (실력별 차등)
        if self.previous_state:
            life_lost = self.previous_state.player_lives - game_state.player_lives
            if life_lost > 0:
                # 실력이 높을수록 더 큰 페널티
                base_death_penalty = 50.0
                skill_death_multiplier = 1.0 + skill * 2.0  # 1.0~3.0
                death_penalty = base_death_penalty * skill_death_multiplier
                total_reward -= death_penalty

                print(f"💀 Skill {skill:.1f}: Death penalty -{death_penalty:.1f}")

        # 6. 공격 행동 보상 (간단화)
        if last_action == ActionType.FIRE:
            # 기본 공격 보상
            fire_reward = 0.5 + skill * 0.5  # 실력에 따라 0.5~1.0
            total_reward += fire_reward

        # 상태 업데이트
        self.previous_state = game_state
        self.action_history.append(last_action)
        if len(self.action_history) > self.max_action_history:
            self.action_history.pop(0)

        return total_reward

    def reset(self) -> None:
        """환경 상태 초기화"""
        self.previous_state = None
        self.action_history = []
        self.last_score = 0
        self.last_lives = 3  # 초기 목숨 값으로 설정 (게임 사양에 맞게 조정 필요)

    def get_action_space_size(self) -> int:
        """액션 공간의 크기를 반환"""
        return len(ActionType)

    def get_state_size(self) -> int:
        """상태 공간 크기 반환

        Returns:
            상태 벡터의 크기
        """
        return self.state_size
