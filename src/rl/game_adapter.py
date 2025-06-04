import math
import numpy as np
from typing import List, Dict, Any, Optional, Tuple

from components.entity_types import EntityType
from rl.environment import GameState, EntityData, ActionType


class GameStateAdapter:
    """게임 상태를 PPO 모델 입력으로 변환하는 어댑터

    실제 게임의 상태를 강화학습 환경에서 사용할 수 있는 형태로 변환합니다.

    ---

    게임과 강화학습 환경 사이의 데이터 변환을 담당하는 어댑터 클래스
    """

    def __init__(self):
        """어댑터 초기화

        ---

        게임 상태 변환에 필요한 설정을 초기화
        """
        # 이전 상태 추적 (델타 계산용)
        self.previous_score = 0
        self.previous_kills = 0
        self.previous_survival_time = 0

        # 거리 계산 캐시
        self.distance_cache = {}

    def extract_game_state(
        self, game_instance, skill_level: float, personality: int
    ) -> GameState:
        """게임 인스턴스에서 상태 정보 추출

        Args:
            game_instance: 게임 인스턴스 (main.py의 App 클래스)
            skill_level: 플레이어 실력 수준 (0~1)
            personality: 플레이어 성향 (0: 방어적, 1: 공격적)

        Returns:
            PPO 모델용 게임 상태

        ---

        실제 게임 상태에서 강화학습에 필요한 정보를 추출하여 변환
        """
        entities = []
        player_hp = 0
        score = 0
        survival_time = 0
        kills = 0
        lives = 3  # 기본값

        # 게임 상태 확인
        if hasattr(game_instance, "game") and game_instance.game:
            game_state = getattr(game_instance.game, "state", None)
            game_vars = getattr(game_instance.game, "game_vars", None)

            if game_state:
                # 플레이어 정보 추출
                player = getattr(game_state, "player", None)
                player_pos = None

                if player and not getattr(player, "remove", False):
                    player_hp = getattr(player, "current_hp", getattr(player, "hp", 0))
                    player_pos = (getattr(player, "x", 0), getattr(player, "y", 0))

                    # 플레이어 엔티티 추가
                    entities.append(
                        EntityData(
                            entity_type=EntityType.PLAYER,
                            x=player.x,
                            y=player.y,
                            w=getattr(player, "w", 8),
                            h=getattr(player, "h", 8),
                            distance_to_player=0.0,
                        )
                    )

                # 모든 게임 객체에서 엔티티 추출
                entities.extend(
                    self._extract_entities_from_objects(game_state, player_pos)
                )

            # 게임 변수에서 점수, 생존 시간, 목숨 추출
            if game_vars:
                score = getattr(game_vars, "score", 0)
                lives = getattr(game_vars, "lives", 3)  # 목숨 정보 추출

                # 디버깅: 목숨 정보 확인
                print(f"🔍 Adapter Debug: Extracted lives = {lives} from game_vars")

                # 생존 시간은 스테이지 상태에서 추출
                if game_state and hasattr(game_state, "state_time"):
                    survival_time = game_state.state_time

                # 처치 수는 점수 변화량으로 추정 (임시)
                score_increase = max(0, score - self.previous_score)
                if score_increase > 0:
                    # 점수 증가량을 기반으로 처치 수 추정
                    estimated_kills = score_increase // 100  # 적당한 점수 단위
                    kills = self.previous_kills + estimated_kills
                else:
                    kills = self.previous_kills
            else:
                print(
                    f"🔍 Adapter Debug: No game_vars found, using default lives = {lives}"
                )

        # 상태 정보 업데이트
        self.previous_score = score
        self.previous_kills = kills
        self.previous_survival_time = survival_time

        return GameState(
            entities=entities,
            skill_level=skill_level,
            personality=personality,
            player_hp=player_hp,
            score=score,
            survival_time=survival_time,
            kills=kills,
            lives=lives,
        )

    def _extract_entities_from_objects(
        self, game_state, player_pos: Optional[Tuple[float, float]]
    ) -> List[EntityData]:
        """게임 객체들로부터 엔티티 리스트 추출

        Args:
            game_state: 게임 상태 객체
            player_pos: 플레이어 위치 (x, y)

        Returns:
            추출된 엔티티 리스트

        ---

        게임의 모든 객체를 순회하며 엔티티 데이터로 변환
        """
        entities = []

        if not player_pos:
            player_pos = (128, 128)  # 기본 위치

        # 적 객체들 추출
        enemies = getattr(game_state, "enemies", [])
        for enemy in enemies:
            if enemy and not getattr(enemy, "remove", False):
                entity_data = self._create_entity_data(enemy, player_pos)
                if entity_data:
                    entities.append(entity_data)

        # 보스 객체들 추출
        bosses = getattr(game_state, "bosses", [])
        for boss in bosses:
            if boss and not getattr(boss, "remove", False):
                entity_data = self._create_entity_data(boss, player_pos)
                if entity_data:
                    entities.append(entity_data)

        # 플레이어 탄환 추출
        player_shots = getattr(game_state, "player_shots", [])
        for shot in player_shots:
            if shot and not getattr(shot, "remove", False):
                entities.append(
                    EntityData(
                        entity_type=EntityType.PLAYER_SHOT,
                        x=getattr(shot, "x", 0),
                        y=getattr(shot, "y", 0),
                        w=getattr(shot, "w", 4),
                        h=getattr(shot, "h", 4),
                        distance_to_player=self._calculate_distance(
                            (getattr(shot, "x", 0), getattr(shot, "y", 0)), player_pos
                        ),
                    )
                )

        # 적 탄환 추출
        enemy_shots = getattr(game_state, "enemy_shots", [])
        for shot in enemy_shots:
            if shot and not getattr(shot, "remove", False):
                entities.append(
                    EntityData(
                        entity_type=EntityType.ENEMY_SHOT,
                        x=getattr(shot, "x", 0),
                        y=getattr(shot, "y", 0),
                        w=getattr(shot, "w", 4),
                        h=getattr(shot, "h", 4),
                        distance_to_player=self._calculate_distance(
                            (getattr(shot, "x", 0), getattr(shot, "y", 0)), player_pos
                        ),
                    )
                )

        # 파워업 추출
        powerups = getattr(game_state, "powerups", [])
        for powerup in powerups:
            if powerup and not getattr(powerup, "remove", False):
                entities.append(
                    EntityData(
                        entity_type=EntityType.POWERUP,
                        x=getattr(powerup, "x", 0),
                        y=getattr(powerup, "y", 0),
                        w=getattr(powerup, "w", 8),
                        h=getattr(powerup, "h", 8),
                        distance_to_player=self._calculate_distance(
                            (getattr(powerup, "x", 0), getattr(powerup, "y", 0)),
                            player_pos,
                        ),
                    )
                )

        return entities

    def _create_entity_data(
        self, game_object, player_pos: Tuple[float, float]
    ) -> Optional[EntityData]:
        """게임 객체를 엔티티 데이터로 변환

        Args:
            game_object: 게임 객체 (적, 보스 등)
            player_pos: 플레이어 위치

        Returns:
            변환된 엔티티 데이터 또는 None

        ---

        개별 게임 객체의 정보를 추출하여 엔티티 데이터로 변환
        """
        if not game_object:
            return None

        # 엔티티 타입 결정
        entity_type = getattr(game_object, "type", None)
        if not entity_type:
            # 타입이 없으면 기본 적으로 설정
            entity_type = EntityType.ENEMY

        # 위치와 크기 정보 추출
        x = getattr(game_object, "x", 0)
        y = getattr(game_object, "y", 0)
        w = getattr(game_object, "w", 8)
        h = getattr(game_object, "h", 8)

        # 플레이어와의 거리 계산
        distance = self._calculate_distance((x, y), player_pos)

        return EntityData(
            entity_type=entity_type, x=x, y=y, w=w, h=h, distance_to_player=distance
        )

    def _calculate_distance(
        self, pos1: Tuple[float, float], pos2: Tuple[float, float]
    ) -> float:
        """두 점 사이의 유클리디안 거리 계산

        Args:
            pos1: 첫 번째 점 (x, y)
            pos2: 두 번째 점 (x, y)

        Returns:
            두 점 사이의 거리

        ---

        효율적인 거리 계산을 위해 캐시를 활용
        """
        # 거리 계산 캐시 키 생성
        cache_key = (round(pos1[0]), round(pos1[1]), round(pos2[0]), round(pos2[1]))

        if cache_key in self.distance_cache:
            return self.distance_cache[cache_key]

        # 유클리디안 거리 계산
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        distance = math.sqrt(dx * dx + dy * dy)

        # 캐시에 저장 (캐시 크기 제한)
        if len(self.distance_cache) < 1000:
            self.distance_cache[cache_key] = distance

        return distance

    def convert_action_to_game_input(self, action_id: int) -> Dict[str, bool]:
        """PPO 액션을 게임 입력으로 변환

        Args:
            action_id: PPO 액션 ID (0~8)

        Returns:
            게임 입력 딕셔너리

        ---

        PPO 에이전트의 액션을 실제 게임 입력 형태로 변환
        """
        # 모든 입력을 초기화
        inputs = {
            "left": False,
            "right": False,
            "up": False,
            "down": False,
            "fire": False,
        }

        # 액션 타입에 따른 입력 설정
        if action_id == ActionType.LEFT_UP:
            inputs["left"] = True
            inputs["up"] = True
        elif action_id == ActionType.UP:
            inputs["up"] = True
        elif action_id == ActionType.RIGHT_UP:
            inputs["right"] = True
            inputs["up"] = True
        elif action_id == ActionType.LEFT:
            inputs["left"] = True
        elif action_id == ActionType.RIGHT:
            inputs["right"] = True
        elif action_id == ActionType.LEFT_DOWN:
            inputs["left"] = True
            inputs["down"] = True
        elif action_id == ActionType.DOWN:
            inputs["down"] = True
        elif action_id == ActionType.RIGHT_DOWN:
            inputs["right"] = True
            inputs["down"] = True
        elif action_id == ActionType.FIRE:
            inputs["fire"] = True

        return inputs

    def apply_action_to_game(self, game_instance, action_id: int):
        """게임 인스턴스에 액션 적용

        Args:
            game_instance: 게임 인스턴스
            action_id: 적용할 액션 ID

        ---

        PPO 에이전트의 액션을 실제 게임에 적용
        """
        if hasattr(game_instance, "apply_agent_action"):
            # 기존 apply_agent_action 메서드 사용
            game_instance.apply_agent_action(action_id)
        else:
            # 직접 입력 시스템에 적용
            inputs = self.convert_action_to_game_input(action_id)

            if hasattr(game_instance, "input"):
                input_system = game_instance.input

                # 입력 상태 설정
                input_system.left_pressed = inputs["left"]
                input_system.right_pressed = inputs["right"]
                input_system.up_pressed = inputs["up"]
                input_system.down_pressed = inputs["down"]
                input_system.fire_pressed = inputs["fire"]

    def reset_tracking(self):
        """추적 상태 리셋

        새로운 에피소드 시작 시 호출하여 이전 상태 추적을 초기화합니다.

        ---

        에피소드 간 상태 추적 정보를 초기화
        """
        self.previous_score = 0
        self.previous_kills = 0
        self.previous_survival_time = 0
        self.distance_cache.clear()


class ActionMapper:
    """액션 매핑 유틸리티 클래스

    PPO 액션과 게임 액션 간의 변환을 담당합니다.

    ---

    액션 변환과 관련된 유틸리티 기능을 제공
    """

    @staticmethod
    def ppo_to_game_action(action_id: int) -> int:
        """PPO 액션 ID를 게임 액션 ID로 변환

        Args:
            action_id: PPO 액션 ID (0~8)

        Returns:
            게임 액션 ID (main.py의 apply_agent_action에서 사용)

        ---

        PPO 액션 공간을 게임의 기존 액션 공간으로 매핑
        """
        # PPO ActionType을 게임의 액션 ID로 직접 매핑
        # (main.py의 apply_agent_action 메서드 참고)
        return action_id

    @staticmethod
    def get_action_description(action_id: int) -> str:
        """액션 ID에 대한 설명 반환

        Args:
            action_id: 액션 ID

        Returns:
            액션 설명 문자열

        ---

        디버깅과 로깅을 위한 액션 설명 제공
        """
        action_descriptions = {
            ActionType.LEFT_UP: "Move Left-Up",
            ActionType.UP: "Move Up",
            ActionType.RIGHT_UP: "Move Right-Up",
            ActionType.LEFT: "Move Left",
            ActionType.RIGHT: "Move Right",
            ActionType.LEFT_DOWN: "Move Left-Down",
            ActionType.DOWN: "Move Down",
            ActionType.RIGHT_DOWN: "Move Right-Down",
            ActionType.FIRE: "Fire",
        }

        return action_descriptions.get(action_id, f"Unknown Action {action_id}")


def create_game_state_from_entities(
    entities: List[Any], skill_level: float = 0.5, personality: int = 0
) -> GameState:
    """엔티티 리스트로부터 간단한 게임 상태 생성

    테스트나 시뮬레이션을 위한 헬퍼 함수입니다.

    Args:
        entities: 엔티티 객체 리스트
        skill_level: 실력 수준
        personality: 성향

    Returns:
        생성된 게임 상태

    ---

    테스트 목적으로 엔티티 리스트에서 게임 상태를 생성
    """
    entity_data_list = []
    player_pos = (128, 128)  # 기본 플레이어 위치

    for entity in entities:
        if not entity:
            continue

        x = getattr(entity, "x", 0)
        y = getattr(entity, "y", 0)
        entity_type = getattr(entity, "type", EntityType.ENEMY)

        # 플레이어 위치 업데이트
        if entity_type == EntityType.PLAYER:
            player_pos = (x, y)

    # 두 번째 패스: 거리 계산
    for entity in entities:
        if not entity:
            continue

        x = getattr(entity, "x", 0)
        y = getattr(entity, "y", 0)
        entity_type = getattr(entity, "type", EntityType.ENEMY)

        # 거리 계산
        dx = x - player_pos[0]
        dy = y - player_pos[1]
        distance = math.sqrt(dx * dx + dy * dy)

        entity_data_list.append(
            EntityData(
                entity_type=entity_type,
                x=x,
                y=y,
                w=getattr(entity, "w", 8),
                h=getattr(entity, "h", 8),
                distance_to_player=distance,
            )
        )

    return GameState(
        entities=entity_data_list,
        skill_level=skill_level,
        personality=personality,
        player_hp=10,  # 기본값
        score=0,
        survival_time=0,
        kills=0,
        lives=3,  # 기본 목숨 수
    )
