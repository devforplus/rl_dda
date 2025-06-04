import numpy as np
import torch
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass
from enum import IntEnum

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
        score: 현재 점수
        survival_time: 생존 시간
        kills: 적 처치 수

    ---

    PPO 모델의 입력으로 사용될 게임 상태 정보
    """

    entities: List[EntityData]
    skill_level: float
    personality: int
    player_hp: int
    score: int
    survival_time: int
    kills: int


class GameEnvironment:
    """PPO 강화학습을 위한 게임 환경 클래스

    게임 상태를 관찰하고 에이전트의 액션에 따른 보상을 계산합니다.

    Attributes:
        max_entities: 최대 엔티티 수 (상태 벡터 크기 고정용)
        entity_feature_size: 엔티티당 특성 수
        state_size: 전체 상태 벡터 크기
        action_size: 액션 공간 크기

    ---

    게임과 강화학습 환경을 연결하는 인터페이스 클래스
    """

    def __init__(self, max_entities: int = 50):
        """환경 초기화

        Args:
            max_entities: 한 번에 처리할 최대 엔티티 수

        ---

        게임 환경을 초기화하고 상태/액션 공간을 설정
        """
        self.max_entities = max_entities

        # 엔티티당 특성: [type_id, x, y, w, h, distance_to_player] = 6개
        self.entity_feature_size = 6

        # 전체 상태 크기: 엔티티 특성 + 게임 메타 정보
        # 엔티티: max_entities * entity_feature_size
        # 메타: [skill_level, personality, player_hp, score, survival_time, kills] = 6개
        self.state_size = self.max_entities * self.entity_feature_size + 6

        # 액션 공간: 8방향 이동 + 공격 = 9개
        self.action_size = 9

        # 보상 가중치 설정
        self.reward_weights = {
            "survival": 0.4,  # 생존 지표 가중치
            "combat": 0.4,  # 공격 지표 가중치
            "consistency": 0.2,  # 일관성 지표 가중치
        }

        # 이전 상태 추적 (일관성 지표 계산용)
        self.previous_state: Optional[GameState] = None
        self.action_history: List[int] = []
        self.max_action_history = 10

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
                game_state.player_hp / 10.0,  # 정규화된 플레이어 체력
                game_state.score / 100000.0,  # 정규화된 점수
                game_state.survival_time / 10000.0,  # 정규화된 생존 시간
                game_state.kills / 100.0,  # 정규화된 처치 수
            ]
        )

        # 전체 상태 벡터 결합
        state_vector = np.concatenate([entity_vector, meta_features])

        return torch.FloatTensor(state_vector)

    def calculate_reward(self, current_state: GameState, action: int) -> float:
        """현재 상태와 액션에 대한 보상 계산

        Args:
            current_state: 현재 게임 상태
            action: 수행한 액션

        Returns:
            계산된 보상 값

        ---

        생존, 공격, 일관성 지표를 종합하여 총 보상을 계산
        """
        total_reward = 0.0

        # 1. 생존 지표 (Survival Metric)
        survival_reward = self._calculate_survival_reward(current_state)
        total_reward += self.reward_weights["survival"] * survival_reward

        # 2. 공격 지표 (Combat Metric)
        combat_reward = self._calculate_combat_reward(current_state)
        total_reward += self.reward_weights["combat"] * combat_reward

        # 3. 일관성 지표 (Consistency Metric)
        consistency_reward = self._calculate_consistency_reward(current_state, action)
        total_reward += self.reward_weights["consistency"] * consistency_reward

        # 상태 업데이트
        self.previous_state = current_state
        self.action_history.append(action)
        if len(self.action_history) > self.max_action_history:
            self.action_history.pop(0)

        return total_reward

    def _calculate_survival_reward(self, current_state: GameState) -> float:
        """생존 지표 보상 계산

        생존 시간과 위험 상황 회피를 기준으로 보상을 계산합니다.

        Args:
            current_state: 현재 게임 상태

        Returns:
            생존 관련 보상 값

        ---

        플레이어의 생존 능력을 평가하는 보상 함수
        """
        reward = 0.0

        # 기본 생존 보상 (시간당 보상)
        # reward += 0.1

        # 체력 기반 보상/페널티
        hp_ratio = current_state.player_hp / 10.0  # 최대 체력 10 가정
        if hp_ratio > 0.7:
            reward += 0.2  # 체력이 높을 때 보너스
        elif hp_ratio < 0.3:
            reward -= 0.3  # 체력이 낮을 때 페널티

        # 적과의 거리 기반 위험도 평가 (가장 가까운 적을 기반으로 해야할듯(Todo))
        danger_score = self._calculate_danger_score(current_state)
        if danger_score > 0.8:
            reward -= 0.5  # 매우 위험한 상황
        elif danger_score < 0.3:
            reward += 0.1  # 안전한 상황

        return reward

    def _calculate_combat_reward(self, current_state: GameState) -> float:
        """공격 지표 보상 계산

        적 처치 수와 공격 효율성을 기준으로 보상을 계산합니다.

        Args:
            current_state: 현재 게임 상태

        Returns:
            공격 관련 보상 값

        ---

        플레이어의 공격 능력을 평가하는 보상 함수
        """
        reward = 0.0

        # 적 처치 수 증가 보상
        if self.previous_state is not None:
            kill_increase = current_state.kills - self.previous_state.kills
            if kill_increase > 0:
                reward += kill_increase * 10.0  # 적 처치당 높은 보상

        # 성향에 따른 보상 조정
        if current_state.personality == 1:  # 공격적 성향
            # 적과 가까운 거리에서 싸우는 것을 선호
            close_enemies = self._count_close_enemies(
                current_state, distance_threshold=50.0
            )
            reward += close_enemies * 0.5
        else:  # 방어적 성향
            # 안전한 거리에서 적을 처치하는 것을 선호
            safe_distance_reward = self._calculate_safe_distance_combat_reward(
                current_state
            )
            reward += safe_distance_reward

        return reward

    def _calculate_consistency_reward(
        self, current_state: GameState, action: int
    ) -> float:
        """일관성 지표 보상 계산

        실력 수준에 맞는 일관된 행동을 보상합니다.

        Args:
            current_state: 현재 게임 상태
            action: 현재 액션

        Returns:
            일관성 관련 보상 값

        ---

        플레이어의 실력에 맞는 일관된 플레이를 장려하는 보상 함수
        """
        reward = 0.0

        if len(self.action_history) < 3:  # 충분한 히스토리가 없으면 0 반환
            return 0.0

        # 액션 패턴의 일관성 평가
        action_variance = np.var(self.action_history[-5:])  # 최근 5개 액션의 분산

        if current_state.skill_level > 0.7:  # 고숙련자
            # 복잡하고 다양한 패턴을 보상
            if action_variance > 2.0:
                reward += 0.3
        else:  # 초보자
            # 단순하고 일관된 패턴을 보상
            if action_variance < 1.0:
                reward += 0.3

        # 실력에 맞지 않는 행동 페널티
        danger_score = self._calculate_danger_score(current_state)

        if current_state.skill_level < 0.3 and danger_score > 0.8:
            # 초보자가 너무 위험한 상황에 자주 노출되면 페널티
            reward -= 0.4

        return reward

    def _calculate_danger_score(self, current_state: GameState) -> float:
        """현재 상황의 위험도를 0~1로 계산

        Args:
            current_state: 현재 게임 상태

        Returns:
            위험도 점수 (0: 안전, 1: 매우 위험)

        ---

        플레이어 주변의 적과 총알 밀도를 기반으로 위험도 평가
        """
        danger = 0.0
        player_entity = None

        # 플레이어 위치 찾기
        for entity in current_state.entities:
            if entity.entity_type == EntityType.PLAYER:
                player_entity = entity
                break

        if player_entity is None:
            return 1.0  # 플레이어가 없으면 최대 위험

        # 주변 적과 적 총알 개수 계산
        close_enemies = 0
        close_bullets = 0

        for entity in current_state.entities:
            if entity.distance_to_player < 50.0:  # 가까운 거리
                if entity.entity_type == EntityType.ENEMY:
                    close_enemies += 1
                elif entity.entity_type == EntityType.ENEMY_SHOT:
                    close_bullets += 1

        # 위험도 계산
        danger += min(close_enemies * 0.2, 0.6)  # 적 최대 0.6
        danger += min(close_bullets * 0.1, 0.4)  # 총알 최대 0.4

        return min(danger, 1.0)

    def _count_close_enemies(
        self, current_state: GameState, distance_threshold: float
    ) -> int:
        """주어진 거리 내의 적 개수 계산

        Args:
            current_state: 현재 게임 상태
            distance_threshold: 거리 임계값

        Returns:
            가까운 적의 개수
        """
        count = 0
        for entity in current_state.entities:
            if (
                entity.entity_type == EntityType.ENEMY
                and entity.distance_to_player <= distance_threshold
            ):
                count += 1
        return count

    def _calculate_safe_distance_combat_reward(self, current_state: GameState) -> float:
        """안전한 거리에서의 전투 보상 계산

        방어적 성향의 플레이어가 안전한 거리를 유지하면서
        적을 처치하는 것을 보상합니다.

        Args:
            current_state: 현재 게임 상태

        Returns:
            안전 거리 전투 보상
        """
        if self.previous_state is None:
            return 0.0

        kill_increase = current_state.kills - self.previous_state.kills
        if kill_increase <= 0:
            return 0.0

        # 적을 처치했을 때의 위험도가 낮으면 보상
        danger_score = self._calculate_danger_score(current_state)
        if danger_score < 0.5:
            return kill_increase * 5.0  # 안전한 상황에서 처치 시 보너스

        return 0.0

    def reset(self):
        """환경 리셋

        새로운 에피소드 시작 시 호출하여 상태를 초기화합니다.

        ---

        강화학습 에피소드 시작 시 환경을 초기 상태로 리셋
        """
        self.previous_state = None
        self.action_history.clear()

    def get_action_space_size(self) -> int:
        """액션 공간 크기 반환

        Returns:
            액션 공간의 크기 (9)
        """
        return self.action_size

    def get_state_size(self) -> int:
        """상태 공간 크기 반환

        Returns:
            상태 벡터의 크기
        """
        return self.state_size
