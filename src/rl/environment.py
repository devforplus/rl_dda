"""
게임 환경 구현

게임과 PPO 에이전트 사이의 브리지 역할을 하는 환경 클래스
"""

import numpy as np
from typing import Dict, List, Tuple, Any, Optional

from components.entity_types import EntityType
from .data_types import GameLogData, EntityPosition, PlayerState, ActionType


class GameEnvironment:
    """게임과 PPO 에이전트 사이의 브리지 환경

    게임 상태를 추출하고 PPO 모델의 입력으로 변환하며,
    에이전트의 액션에 따른 보상을 계산합니다.
    """

    def __init__(self):
        """환경 초기화"""
        # 이전 상태 추적 (보상 계산용)
        self.previous_score = 0
        self.previous_kills = 0
        self.previous_hp = 3
        self.previous_lives = 3

        # 액션 매핑 (ActionType -> 게임 입력)
        self.action_mapping = {
            ActionType.LEFT_UP: {"left": True, "up": True},
            ActionType.UP: {"up": True},
            ActionType.RIGHT_UP: {"right": True, "up": True},
            ActionType.LEFT: {"left": True},
            ActionType.RIGHT: {"right": True},
            ActionType.LEFT_DOWN: {"left": True, "down": True},
            ActionType.DOWN: {"down": True},
            ActionType.RIGHT_DOWN: {"right": True, "down": True},
            ActionType.FIRE: {"fire": True},
        }

    def extract_game_log_data(self, game_instance, skill_level: float) -> GameLogData:
        """게임 인스턴스에서 게임 로그 데이터 추출

        Args:
            game_instance: 게임 인스턴스 (main.py의 App 클래스)
            skill_level: 실력값 (0.0 ~ 1.0)

        Returns:
            PPO 모델용 게임 로그 데이터
        """
        entities = []
        player_state = PlayerState(hp=3, lives=3)  # 기본값

        # 게임 상태 확인
        if hasattr(game_instance, "game") and game_instance.game:
            game_state = getattr(game_instance.game, "state", None)
            game_vars = getattr(game_instance.game, "game_vars", None)

            if game_state:
                # 플레이어 정보 추출
                player = getattr(game_state, "player", None)
                if player and not getattr(player, "remove", False):
                    player_state.hp = getattr(
                        player, "current_hp", getattr(player, "hp", 3)
                    )

                    # 플레이어 엔티티 추가
                    entities.append(
                        EntityPosition(
                            x=float(getattr(player, "x", 0)),
                            y=float(getattr(player, "y", 0)),
                            entity_type=0,  # 플레이어
                        )
                    )

                # 적 엔티티 추출
                for enemy_list in [
                    "enemy_a",
                    "enemy_b",
                    "enemy_c",
                    "enemy_d",
                    "enemy_e",
                    "enemy_f",
                    "enemy_g",
                    "enemy_h",
                    "enemy_i",
                    "enemy_j",
                    "enemy_k",
                    "enemy_l",
                    "enemy_m",
                    "enemy_n",
                    "enemy_o",
                    "enemy_p",
                ]:
                    enemy_objects = getattr(game_state, enemy_list, [])
                    for enemy in enemy_objects:
                        if not getattr(enemy, "remove", False):
                            entities.append(
                                EntityPosition(
                                    x=float(getattr(enemy, "x", 0)),
                                    y=float(getattr(enemy, "y", 0)),
                                    entity_type=1,  # 적
                                )
                            )

                # 적 탄환 추출
                enemy_shots = getattr(game_state, "enemy_shot", [])
                for shot in enemy_shots:
                    if not getattr(shot, "remove", False):
                        entities.append(
                            EntityPosition(
                                x=float(getattr(shot, "x", 0)),
                                y=float(getattr(shot, "y", 0)),
                                entity_type=2,  # 적 탄환
                            )
                        )

            # 게임 변수에서 목숨 정보 추출
            if game_vars:
                player_state.lives = getattr(game_vars, "lives", 3)

        return GameLogData(
            entities=entities, player_state=player_state, skill_level=skill_level
        )

    def calculate_reward(self, game_instance, skill_level: float) -> float:
        """보상 계산

        Args:
            game_instance: 게임 인스턴스
            skill_level: 실력값

        Returns:
            계산된 보상값
        """
        reward = 0.0

        if hasattr(game_instance, "game") and game_instance.game:
            game_vars = getattr(game_instance.game, "game_vars", None)
            game_state = getattr(game_instance.game, "state", None)

            if game_vars:
                # 점수 증가 보상
                current_score = getattr(game_vars, "score", 0)
                score_delta = current_score - self.previous_score
                if score_delta > 0:
                    reward += score_delta * 0.01  # 점수 1점당 0.01 보상

                # 적 처치 보상
                current_kills = getattr(game_vars, "kills", 0)
                kills_delta = current_kills - self.previous_kills
                if kills_delta > 0:
                    # 실력값에 따른 적응적 보상
                    kill_reward = kills_delta * (1.0 + skill_level) * 10.0
                    reward += kill_reward

                # 상태 업데이트
                self.previous_score = current_score
                self.previous_kills = current_kills

            if game_state:
                player = getattr(game_state, "player", None)
                if player:
                    # 체력 감소 페널티
                    current_hp = getattr(player, "current_hp", getattr(player, "hp", 3))
                    hp_delta = current_hp - self.previous_hp
                    if hp_delta < 0:
                        reward += hp_delta * 5.0  # 체력 1 감소당 -5.0 페널티

                    # 생존 보상 (실력값에 따른 적응적 보상)
                    if current_hp > 0:
                        survival_reward = 0.1 * (1.0 + skill_level)
                        reward += survival_reward

                    self.previous_hp = current_hp

                # 목숨 감소 큰 페널티
                if game_vars:
                    current_lives = getattr(game_vars, "lives", 3)
                    lives_delta = current_lives - self.previous_lives
                    if lives_delta < 0:
                        reward += lives_delta * 50.0  # 목숨 1 감소당 -50.0 페널티

                    self.previous_lives = current_lives

        return reward

    def get_action_input(self, action_id: int) -> Dict[str, bool]:
        """액션 ID를 게임 입력으로 변환

        Args:
            action_id: PPO 에이전트가 선택한 액션 ID

        Returns:
            게임 입력 딕셔너리
        """
        if action_id in self.action_mapping:
            return self.action_mapping[action_id].copy()
        else:
            return {}  # 잘못된 액션 ID

    def is_episode_done(self, game_instance) -> bool:
        """에피소드 종료 여부 확인

        Args:
            game_instance: 게임 인스턴스

        Returns:
            에피소드 종료 여부
        """
        if hasattr(game_instance, "game") and game_instance.game:
            game_vars = getattr(game_instance.game, "game_vars", None)
            if game_vars:
                lives = getattr(game_vars, "lives", 3)
                return lives <= 0

        return False

    def reset(self):
        """환경 리셋 (새 에피소드 시작)"""
        self.previous_score = 0
        self.previous_kills = 0
        self.previous_hp = 3
        self.previous_lives = 3
