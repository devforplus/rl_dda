"""
PPO 모델을 위한 데이터 타입 정의

사용자 요구사항:
- 게임 로그 데이터: 적/플레이어 좌표, 적 탄환 좌표, 플레이어 체력/목숨
- 실력값: 0~1 사이 값 (높을수록 더 오래 생존 + 더 많은 적 처치)
"""

from dataclasses import dataclass
from typing import List, Tuple
from enum import IntEnum
import numpy as np


class ActionType(IntEnum):
    """PPO 에이전트 액션 정의 (8방향 이동 + 공격)"""

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
class EntityPosition:
    """게임 엔티티의 위치 정보

    Args:
        x: X 좌표
        y: Y 좌표
        entity_type: 엔티티 타입 (0: 플레이어, 1: 적, 2: 적 탄환)
    """

    x: float
    y: float
    entity_type: int  # 0: 플레이어, 1: 적, 2: 적 탄환


@dataclass
class PlayerState:
    """플레이어 상태 정보

    Args:
        hp: 현재 체력
        lives: 남은 목숨 수
    """

    hp: int
    lives: int


@dataclass
class GameLogData:
    """게임 로그 데이터 (PPO 모델의 핵심 입력)

    사용자 요구사항에 따른 핵심 데이터:
    - 적/플레이어 좌표
    - 적 탄환 좌표
    - 플레이어 체력 및 목숨 데이터
    - 실력값 (0~1)

    Args:
        entities: 모든 엔티티 위치 리스트
        player_state: 플레이어 상태
        skill_level: 실력값 (0.0 ~ 1.0)
    """

    entities: List[EntityPosition]
    player_state: PlayerState
    skill_level: float  # 0.0 ~ 1.0 사이 값

    def to_state_vector(self, max_entities: int = 50) -> np.ndarray:
        """게임 로그 데이터를 PPO 모델용 상태 벡터로 변환

        Args:
            max_entities: 최대 엔티티 수 (패딩용)

        Returns:
            1차원 상태 벡터 [entities(max_entities*3) + player_state(2) + skill_level(1)]
        """
        # 엔티티 데이터를 고정 크기 배열로 변환 (entity당 3개 값: x, y, type)
        entity_data = np.zeros(max_entities * 3)

        for i, entity in enumerate(self.entities[:max_entities]):
            base_idx = i * 3
            entity_data[base_idx] = entity.x / 256.0  # X 좌표 정규화 (0~1)
            entity_data[base_idx + 1] = entity.y / 256.0  # Y 좌표 정규화 (0~1)
            entity_data[base_idx + 2] = entity.entity_type / 2.0  # 타입 정규화 (0~1)

        # 플레이어 상태 정규화
        player_data = np.array(
            [
                self.player_state.hp / 3.0,  # 체력 정규화 (최대 3으로 가정)
                self.player_state.lives / 3.0,  # 목숨 정규화 (최대 3으로 가정)
            ]
        )

        # 실력값 (이미 0~1 사이)
        skill_data = np.array([self.skill_level])

        # 전체 상태 벡터 결합
        state_vector = np.concatenate([entity_data, player_data, skill_data])

        return state_vector.astype(np.float32)
