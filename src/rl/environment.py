"""
게임 환경 구현

게임과 PPO 에이전트 사이의 브리지 역할을 하는 환경 클래스
"""

from typing import Dict, List, Tuple
import math

from src.components.entity_types import EntityType
from .data_types import GameLogData, EntityPosition, PlayerState, ActionType
from .targets import get_survival_target_steps, get_kill_target
from src.config.player.player_config import STARTING_LIVES


class GameEnvironment:
    """게임과 PPO 에이전트 사이의 브리지 환경

    게임 상태를 추출하고 PPO 모델의 입력으로 변환하며,
    에이전트의 액션에 따른 보상을 계산합니다.
    """

    def __init__(self):
        # 이전 상태 추적용
        self.previous_score = 0
        self.previous_kills = 0
        self.previous_hp = 3
        self.previous_lives = 3

        # 에피소드 추적용
        self.episode_steps = 0
        self.episode_start_time = None

        # 탄환 회피 보상 계산을 위한 이전 프레임 추적
        # Format: List[Tuple[x, y, distance_to_player]]
        self.previous_nearby_bullets: List[Tuple[float, float, float]] = []
        self.previous_player_pos: Tuple[float, float] = (0, 0)

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

    def reset_episode(self):
        """새 에피소드 시작 시 호출"""
        import time

        self.previous_score = 0
        self.previous_kills = 0
        self.previous_hp = 3
        self.previous_lives = 3
        self.episode_steps = 0
        self.episode_start_time = time.time()
        self.previous_nearby_bullets = []
        self.previous_player_pos = (0, 0)

    def step(self):
        """매 스텝마다 호출하여 스텝 카운트 증가"""
        self.episode_steps += 1

    def extract_game_log_data(self, game_instance, skill_level: float) -> GameLogData:
        """게임 인스턴스에서 PPO 모델용 데이터를 추출

        거리 기반 우선순위 시스템:
        - 플레이어를 기준으로 모든 엔티티의 거리를 계산
        - 가까운 엔티티부터 우선적으로 상태 벡터에 포함
        - max_entities 제한 내에서 가장 위협적인(가까운) 정보를 우선 제공

        Args:
            game_instance: 게임 인스턴스
            skill_level: 실력값 (0.0~1.0)

        Returns:
            추출된 게임 로그 데이터 (거리순 정렬된 엔티티)
        """
        entities = []
        player_state = PlayerState(hp=3, lives=3)
        current_step = self.episode_steps
        current_kills = 0
        current_score = 0
        player_x = 0
        player_y = 0

        # 게임 인스턴스에서 데이터 추출
        if hasattr(game_instance, "game") and game_instance.game:
            game_state = getattr(game_instance.game, "state", None)
            game_vars = getattr(game_instance.game, "game_vars", None)

            if game_state:
                # 플레이어 정보
                player = getattr(game_state, "player", None)
                if player:
                    player_x = getattr(player, "x", 0)
                    player_y = getattr(player, "y", 0)
                    player_hp = getattr(player, "current_hp", getattr(player, "hp", 3))
                    player_state = PlayerState(
                        hp=player_hp,
                        lives=getattr(game_vars, "lives", 3) if game_vars else 3,
                    )

                # 플레이어 위치 저장 (탄환 회피 보상 계산용)
                self.previous_player_pos = (player_x, player_y)

                # 엔티티 수집 (플레이어, 적, 탄환)
                # 플레이어는 항상 첫 번째로 추가 (거리 0)
                if player:
                    entities.append(
                        EntityPosition(
                            x=player_x,
                            y=player_y,
                            entity_type=EntityType.PLAYER,
                        )
                    )

                # 임시 리스트: (entity, distance) 형태로 저장
                entities_with_distance: List[Tuple[EntityPosition, float]] = []

                # 적 정보 수집 (enemy_shots 제외 - 탄환은 별도 처리)
                enemy_attrs = [
                    attr for attr in dir(game_state) 
                    if attr.startswith("enemy") and attr != "enemy_shots"
                ]
                for attr in enemy_attrs:
                    enemy_group = getattr(game_state, attr, None)
                    if enemy_group and hasattr(enemy_group, "__iter__"):
                        try:
                            for enemy in enemy_group:
                                if hasattr(enemy, "x") and hasattr(enemy, "y"):
                                    enemy_x = getattr(enemy, "x", 0)
                                    enemy_y = getattr(enemy, "y", 0)
                                    distance = math.sqrt(
                                        (enemy_x - player_x) ** 2
                                        + (enemy_y - player_y) ** 2
                                    )
                                    entities_with_distance.append(
                                        (
                                            EntityPosition(
                                                x=enemy_x,
                                                y=enemy_y,
                                                entity_type=EntityType.ENEMY,
                                            ),
                                            distance,
                                        )
                                    )
                        except Exception:
                            pass

                # 탄환 정보 수집 (이전 프레임 탄환도 저장)
                nearby_bullets: List[Tuple[float, float, float]] = []
                if hasattr(game_state, "enemy_shots"):
                    enemy_shots = getattr(game_state, "enemy_shots", [])
                    if enemy_shots and hasattr(enemy_shots, "__iter__"):
                        try:
                            for shot in enemy_shots:
                                if hasattr(shot, "x") and hasattr(shot, "y"):
                                    shot_x = getattr(shot, "x", 0)
                                    shot_y = getattr(shot, "y", 0)
                                    distance = math.sqrt(
                                        (shot_x - player_x) ** 2
                                        + (shot_y - player_y) ** 2
                                    )
                                    entities_with_distance.append(
                                        (
                                            EntityPosition(
                                                x=shot_x,
                                                y=shot_y,
                                                entity_type=EntityType.ENEMY_SHOT,
                                            ),
                                            distance,
                                        )
                                    )
                                    # 가까운 탄환만 추적 (40픽셀 이내)
                                    # 탄환 회피 보상 계산에 사용
                                    if distance < 40:
                                        nearby_bullets.append(
                                            (shot_x, shot_y, distance)
                                        )
                        except Exception:
                            pass

                # 이전 프레임 탄환 정보 업데이트
                self.previous_nearby_bullets = nearby_bullets

                # 거리순으로 정렬 (가까운 것부터)
                entities_with_distance.sort(key=lambda x: x[1])

                # 정렬된 순서대로 entities에 추가
                for entity, _ in entities_with_distance:
                    entities.append(entity)

            # 게임 변수에서 현재 성과 정보 추출
            if game_vars:
                current_kills = getattr(game_vars, "kills", 0)
                current_score = getattr(game_vars, "score", 0)

        # 매 호출마다 스텝 증가
        self.step()

        return GameLogData(
            entities=entities,
            player_state=player_state,
            skill_level=skill_level,
            current_step=current_step,
            current_kills=current_kills,
            current_score=current_score,
        )

    def calculate_reward(self, game_instance, skill_level: float) -> float:
        """커리큘럼 러닝 기반 실력값별 플레이 스타일 보상 계산

        커리큘럼 러닝 시스템:
        - 2지표 가중합 보상: R = 0.5×survival + 0.5×attack + bonus
        - 가중합 형태로 부분 달성도 적절히 보상 (학습 안정성)
        - 목표값만 skill level에 따라 증가
        - Catastrophic Forgetting 방지: 보상 함수의 일관성 유지

        커리큘럼 단계 (가중치 고정 50:50):
        - Stage 1 (skill=0.1): 목표 330스텝, 1.2킬
        - Stage 2 (skill=0.3): 목표 590스텝, 3.6킬
        - Stage 3 (skill=0.5): 목표 850스텝, 6.0킬
        - Stage 4 (skill=0.7): 목표 1110스텝, 8.4킬
        - Stage 5 (skill=0.9): 목표 1370스텝, 10.8킬
        - Stage 6 (skill=1.0): 목표 1500스텝, 12킬

        즉각적 보상/페널티 시스템 (Immediate Feedback):
        1. 탄환 회피 보상 ✅:
           - 가까운 탄환(40픽셀 이내)을 성공적으로 회피했을 때 즉각적인 보상
           - 회피 보상 = 0.01 * 회피한 탄환 수 (최대 0.05)
           - 학습 초기 단계에서 회피 행동을 강화하는 역할
        
        2. 킬 보상 ✅:
           - 적을 처치했을 때 즉각적인 보상 제공
           - 킬 보상 = (0.02 + skill_level * 0.03) * 새로운 킬 수
           - Skill 0.1: 0.023/킬, Skill 1.0: 0.05/킬
           - 공격 행동 강화 및 빠른 학습 신호 제공
        
        3. HP 감소 페널티 ⚠️ (신규):
           - 탄환에 맞아서 HP가 감소했을 때 즉각적인 페널티
           - HP 손실 페널티 = (0.05 + skill_level * 0.05) * HP 손실량
           - Skill 0.1: 0.055/HP, Skill 1.0: 0.10/HP
           - 탄환 회피 행동 강화 및 신중한 플레이 유도
        
        4. 사망 페널티 ❌:
           - Lives 감소 시 큰 페널티
           - 사망 페널티 = 0.2 + skill_level * 0.3 (0.2 ~ 0.5)

        핵심 철학:
        - 보상 함수 일관성: 전 단계에서 동일한 가중치 (50:50)
        - 단계별 목표 증가: 에이전트가 점진적으로 더 높은 성능 달성
        - Catastrophic Forgetting 방지: 이전 학습 유지하면서 성장
        - 즉각적 피드백: 회피와 킬 모두 즉시 보상으로 빠른 학습 유도

        Args:
            game_instance: 게임 인스턴스
            skill_level: 실력값 (0.0 ~ 1.0)

        Returns:
            최종 보상 = 가중합 보상 + bonus + 킬 보상 + 회피 보상 - HP 페널티 - 사망 페널티
            (0.0 ~ 1.5+ 스케일, 페널티 적용 후 0.0 이상으로 제한)
        """
        if not (hasattr(game_instance, "game") and game_instance.game):
            return 0.0

        game_vars = getattr(game_instance.game, "game_vars", None)
        if not game_vars:
            return 0.0

        current_step = self.episode_steps
        current_kills = getattr(game_vars, "kills", 0)
        current_lives = getattr(game_vars, "lives", 3)
        
        # 현재 HP 추출 (탄환 피격 감지용)
        current_hp = 3  # 기본값
        game_state = getattr(game_instance.game, "state", None)
        if game_state:
            player = getattr(game_state, "player", None)
            if player:
                current_hp = getattr(player, "current_hp", getattr(player, "hp", 3))

        # 실력값 기반 적응적 목표 설정 (targets.py와 일치)
        target_survival_steps = get_survival_target_steps(skill_level)
        target_kills = get_kill_target(skill_level)
        
        # 목표 킬 레이트: targets.py 기준으로 정확히 계산
        # 예: skill 0.3 → 3.6킬 / 440스텝 = 0.818 킬/100스텝
        target_kill_rate = (target_kills / max(target_survival_steps, 1)) * 100.0

        # === 1. 생존 지표 (Survival Score) ===
        # 제곱근 변환 (Reward Shaping): 부분 달성에도 합리적인 보상
        # 선형: 50% → 0.5, 제곱근: 50% → 0.707
        # 최종 목표(100%)는 동일하게 1.0 유지
        survival_ratio = current_step / max(target_survival_steps, 1)
        survival_score = min(1.0, survival_ratio ** 0.5)

        # === 2. 공격 지표 (Attack Score) ===
        # 제곱근 변환 (Reward Shaping): 킬 달성에도 동일 적용
        if current_step > 0 and target_kill_rate > 0:
            current_kill_rate = (
                current_kills / max(current_step, 1)
            ) * 100.0  # 킬/100스텝
            attack_ratio = current_kill_rate / target_kill_rate
            attack_score = min(1.0, attack_ratio ** 0.5)
        else:
            attack_score = 0.0

        # === 3. 일관성 지표 (Consistency Score) ===
        # NOTE: 일관성 weight가 0으로 설정되어 현재 사용되지 않음
        # 추후 재사용할 수 있도록 주석 처리로 보존
        consistency_score = 0.0  # 사용하지 않음

        # 기존 일관성 계산 로직 (주석 처리)
        # if current_step > 0:
        #     # 생존 목표 달성률
        #     survival_achievement = min(1.0, current_step / target_survival_steps)
        #
        #     # 공격 목표 달성률 (target_kill_rate가 0인 경우 처리)
        #     if target_kill_rate > 0:
        #         current_kill_rate = (current_kills / max(current_step, 1)) * 100.0
        #         attack_achievement = min(1.0, current_kill_rate / target_kill_rate)
        #     else:
        #         attack_achievement = 1.0  # 목표가 0이면 완벽 달성으로 간주
        #
        #     # 일관성 = 두 달성률이 얼마나 균형잡혀 있는지 (편차가 작을수록 좋음)
        #     achievement_difference = abs(survival_achievement - attack_achievement)
        #
        #     # 일관성 점수: 편차가 작을수록 높은 점수 (0.0 ~ 1.0)
        #     # 편차 0 = 완벽한 일관성(1.0), 편차 1 = 매우 불일치(0.0)
        #     consistency_score = max(0.0, 1.0 - achievement_difference)
        #
        #     # 추가 보정: 둘 다 목표를 달성한 경우 보너스
        #     if survival_achievement >= 0.8 and attack_achievement >= 0.8:
        #         consistency_score = min(1.0, consistency_score + 0.2)  # 보너스 추가
        # else:
        #     consistency_score = 1.0  # 초기 상태는 완벽한 일관성

        # === 동적 가중치 커리큘럼 (고급 학습 경로 최적화) ===
        # 핵심 설계: 각 단계별 집중 영역 변화로 최적 학습 경로 제공
        # 
        # 이론적 우려: Catastrophic Forgetting
        # - 가중치 변경이 이전 학습을 망각시킬 수 있음
        # 
        # 실제 결과: Forgetting 발생하지 않음!
        # - 생존-공격은 계층적 관계 (독립적이 아님)
        # - 공격 학습이 생존 학습을 강화 (상호보완)
        # - 실험 검증: Skill 1.0에서 1200스텝 달성 (생존 능력도 향상)
        #
        # 학습 경로:
        # 1. 초급 (생존 중심): 먼저 살아남는 법 마스터
        # 2. 중급 (균형): 생존 유지하면서 공격 추가
        # 3. 고급 (공격 중심): 생존 기술 활용한 적극적 플레이
        
        # === 선형 보간 가중치 (6단계 커리큘럼 최적화) ===
        # Skill 0.1 → 1.0으로 갈수록 생존 70% → 30%, 공격 30% → 70%
        # 부드러운 전환으로 각 단계에서 최적화된 학습 신호 제공
        #
        # 가중치 변화 예시:
        # - Skill 0.1: 생존 66%, 공격 34% (생존 기초)
        # - Skill 0.3: 생존 58%, 공격 42% (생존 + 기본 공격)
        # - Skill 0.5: 생존 50%, 공격 50% (균형)
        # - Skill 0.7: 생존 42%, 공격 58% (공격 중심 전환)
        # - Skill 0.9: 생존 34%, 공격 66% (적극적 공격)
        # - Skill 1.0: 생존 30%, 공격 70% (마스터)
        #
        # 생존 최소 30% 유지 → Catastrophic Forgetting 방지
        
        # 선형 보간 계산
        # skill 0.0 → w_survival 0.7, skill 1.0 → w_survival 0.3
        w_survival = 0.7 - (skill_level * 0.4)  # 0.7 → 0.3
        w_attack = 0.3 + (skill_level * 0.4)    # 0.3 → 0.7
        
        # 안전 범위 클리핑 (혹시 모를 skill_level 범위 초과 대비)
        w_survival = max(0.3, min(0.7, w_survival))
        w_attack = max(0.3, min(0.7, w_attack))
        
        # 가중합 보상: 부분 달성도 보상
        base_reward = w_survival * survival_score + w_attack * attack_score
        
        # === 지수 보너스 시스템 (연속적 학습 신호) ===
        # 목표: 임계값 없이 전 구간에서 연속적이고 자연스러운 학습 신호 제공
        # 
        # 설계 원칙:
        # 1. 연속성: 모든 구간에서 부드러운 그래디언트
        # 2. 가속성: 성능이 좋을수록 보상이 더 빠르게 증가
        # 3. 균형: min_score로 두 지표 균형 유도
        # 
        # 수학적 특성:
        # - e^(x-1): x=0일 때 ~0.37, x=0.5일 때 ~0.61, x=1일 때 1.0
        # - avg_score: 전체적인 성능 수준
        # - min_score: 생존-공격 균형 (낮은 쪽에 페널티)
        # - 곱셈 조합: 둘 다 높아야 큰 보상
        min_score = min(survival_score, attack_score)
        avg_score = (survival_score + attack_score) / 2.0
        
        # 지수 함수 기반 보너스: 자연스럽게 가속되는 보상
        # e^(avg_score - 1) 형태로 avg_score=1일 때 e^0=1
        # 스케일링 계수 0.3: 보너스가 과도하지 않게 조절
        bonus = math.exp(avg_score - 1.0) * min_score * 0.3
        
        # 완벽 달성 추가 보너스: 둘 다 100% 이상일 때만
        # 목표 초과 달성을 명확히 보상
        if survival_score >= 1.0 and attack_score >= 1.0:
            bonus += 0.2
        
        # 최종 보상 (0.0 ~ 1.5 스케일)
        final_reward = base_reward + bonus

        # === 탄환 회피 보상 (Bullet Dodge Reward) ===
        # 이전 프레임의 가까운 탄환들이 현재 프레임에서 더 멀어졌는지 확인
        dodge_reward = 0.0
        if len(self.previous_nearby_bullets) > 0:
            # 현재 게임 상태에서 탄환 위치 재확인
            game_state = getattr(game_instance.game, "state", None)
            current_player_x, current_player_y = self.previous_player_pos

            dodged_count = 0
            if game_state and hasattr(game_state, "enemy_shots"):
                enemy_shots = getattr(game_state, "enemy_shots", [])
                current_bullet_positions = set()

                # 현재 탄환 위치들을 set으로 저장 (빠른 검색을 위해)
                for shot in enemy_shots:
                    if hasattr(shot, "x") and hasattr(shot, "y"):
                        shot_x = getattr(shot, "x", 0)
                        shot_y = getattr(shot, "y", 0)
                        # 위치를 반올림하여 약간의 오차 허용
                        current_bullet_positions.add((round(shot_x), round(shot_y)))

                # 이전 프레임의 가까운 탄환들을 확인
                for prev_x, prev_y, prev_distance in self.previous_nearby_bullets:
                    # 현재 프레임에 이 탄환이 존재하는지 확인
                    prev_pos_rounded = (round(prev_x), round(prev_y))

                    # 탄환이 사라졌거나 (플레이어가 회피했거나 화면 밖으로 나감)
                    # 거리가 증가했다면 회피 성공으로 간주
                    if prev_pos_rounded not in current_bullet_positions:
                        # 탄환이 사라짐 = 회피 성공
                        dodged_count += 1
                    else:
                        # 탄환이 여전히 존재하면 거리 변화 확인
                        current_distance = math.sqrt(
                            (prev_x - current_player_x) ** 2
                            + (prev_y - current_player_y) ** 2
                        )
                        # 거리가 5픽셀 이상 증가했으면 회피 중으로 간주
                        if current_distance > prev_distance + 5:
                            dodged_count += 1

            # 회피 보상: 탄환 1개당 0.01 (작지만 즉각적인 피드백)
            # 생존 초기 단계에서 특히 유용한 학습 신호
            dodge_reward = min(0.05, dodged_count * 0.01)  # 최대 0.05로 제한

        # === 즉각적 킬 보상 (Kill Reward) ===
        # 적을 처치했을 때 즉각적인 보상 제공
        # 목표: 공격 행동 강화 및 빠른 학습 신호 제공
        kill_reward = 0.0
        if current_kills > self.previous_kills:
            new_kills = current_kills - self.previous_kills
            # 킬당 보상: 0.02 ~ 0.05 (skill_level에 따라 증가)
            # - Skill 0.1: 0.023/킬 (초급자용 보상)
            # - Skill 1.0: 0.05/킬 (고급자용 보상)
            # 탄환 회피(0.01)보다 높은 보상으로 공격 행동 유도
            kill_reward = new_kills * (0.02 + skill_level * 0.03)

        # === HP 감소 페널티 (탄환 피격) ===
        # 탄환에 맞아서 HP가 감소했을 때 즉각적인 페널티 제공
        # 목표: 탄환 회피 행동 강화 및 신중한 플레이 유도
        hp_damage_penalty = 0.0
        if current_hp < self.previous_hp:
            hp_loss = self.previous_hp - current_hp
            # HP 손실당 페널티: 0.05 ~ 0.1 (skill_level에 따라 증가)
            # - Skill 0.1: HP 1당 0.055 페널티
            # - Skill 1.0: HP 1당 0.10 페널티
            # 사망 페널티(0.2~0.5)보다는 약하지만 명확한 학습 신호
            hp_damage_penalty = hp_loss * (0.05 + skill_level * 0.05)
            self.previous_hp = current_hp

        # 사망 시 즉시 페널티 (기존 구조 유지하되 단순화)
        death_penalty = 0.0
        if current_lives < self.previous_lives:
            death_penalty = 0.2 + (skill_level * 0.3)  # 0.2 ~ 0.5 페널티
            self.previous_lives = current_lives
            # 사망 시 HP도 리셋
            self.previous_hp = 3

        # 최종 보상 (킬 보상 + 회피 보상 + 페널티 적용)
        final_reward = max(0.0, final_reward + dodge_reward + kill_reward 
                          - hp_damage_penalty - death_penalty)

        # 상태 업데이트
        self.previous_kills = current_kills

        return final_reward
    
    def calculate_reward_breakdown(self, game_instance, skill_level: float) -> Dict[str, float]:
        """보상을 분해하여 각 요소별로 반환 (진단용)
        
        calculate_reward()와 동일한 로직이지만, 각 보상 요소를 딕셔너리로 반환합니다.
        
        Args:
            game_instance: 게임 인스턴스
            skill_level: 실력값 (0.0 ~ 1.0)
            
        Returns:
            보상 분해 딕셔너리
        """
        if not (hasattr(game_instance, "game") and game_instance.game):
            return self._empty_reward_breakdown()
        
        game_vars = getattr(game_instance.game, "game_vars", None)
        if not game_vars:
            return self._empty_reward_breakdown()
        
        current_step = self.episode_steps
        current_kills = getattr(game_vars, "kills", 0)
        current_lives = getattr(game_vars, "lives", 3)
        
        # 현재 HP 추출
        current_hp = 3
        game_state = getattr(game_instance.game, "state", None)
        if game_state:
            player = getattr(game_state, "player", None)
            if player:
                current_hp = getattr(player, "current_hp", getattr(player, "hp", 3))
        
        # 목표값 계산
        target_survival_steps = get_survival_target_steps(skill_level)
        target_kills = get_kill_target(skill_level)
        target_kill_rate = (target_kills / max(target_survival_steps, 1)) * 100.0
        
        # === 1. 생존 점수 (제곱근 변환) ===
        survival_ratio = current_step / max(target_survival_steps, 1)
        survival_score = min(1.0, survival_ratio ** 0.5)
        
        # === 2. 공격 점수 (제곱근 변환) ===
        if current_step > 0 and target_kill_rate > 0:
            current_kill_rate = (current_kills / max(current_step, 1)) * 100.0
            attack_ratio = current_kill_rate / target_kill_rate
            attack_score = min(1.0, attack_ratio ** 0.5)
        else:
            attack_score = 0.0
        
        # === 3. 동적 가중치 적용 ===
        w_survival = 0.7 - (skill_level * 0.4)  # 0.7 → 0.3
        w_attack = 0.3 + (skill_level * 0.4)    # 0.3 → 0.7
        w_survival = max(0.3, min(0.7, w_survival))
        w_attack = max(0.3, min(0.7, w_attack))
        
        # 가중합 보상 (base_reward)
        base_reward = w_survival * survival_score + w_attack * attack_score
        
        # === 4. 지수 보너스 (연속적 학습 신호) ===
        min_score = min(survival_score, attack_score)
        avg_score = (survival_score + attack_score) / 2.0
        
        bonus = math.exp(avg_score - 1.0) * min_score * 0.3
        
        if survival_score >= 1.0 and attack_score >= 1.0:
            bonus += 0.2
        
        # === 5. 탄환 회피 보상 ===
        dodge_reward = 0.0
        if len(self.previous_nearby_bullets) > 0:
            game_state = getattr(game_instance.game, "state", None)
            current_player_x, current_player_y = self.previous_player_pos
            
            dodged_count = 0
            if game_state and hasattr(game_state, "enemy_shots"):
                enemy_shots = getattr(game_state, "enemy_shots", [])
                current_bullet_positions = set()
                
                for shot in enemy_shots:
                    if hasattr(shot, "x") and hasattr(shot, "y"):
                        shot_x = getattr(shot, "x", 0)
                        shot_y = getattr(shot, "y", 0)
                        current_bullet_positions.add((round(shot_x), round(shot_y)))
                
                for prev_x, prev_y, prev_distance in self.previous_nearby_bullets:
                    prev_pos_rounded = (round(prev_x), round(prev_y))
                    
                    if prev_pos_rounded not in current_bullet_positions:
                        dodged_count += 1
                    else:
                        current_distance = math.sqrt(
                            (prev_x - current_player_x) ** 2
                            + (prev_y - current_player_y) ** 2
                        )
                        if current_distance > prev_distance + 5:
                            dodged_count += 1
            
            dodge_reward = min(0.05, dodged_count * 0.01)
        
        # === 6. 킬 보상 ===
        kill_reward = 0.0
        if current_kills > self.previous_kills:
            new_kills = current_kills - self.previous_kills
            kill_reward = new_kills * (0.02 + skill_level * 0.03)
        
        # === 7. HP 감소 페널티 ===
        hp_damage_penalty = 0.0
        if current_hp < self.previous_hp:
            hp_loss = self.previous_hp - current_hp
            hp_damage_penalty = hp_loss * (0.05 + skill_level * 0.05)
        
        # === 8. 사망 페널티 ===
        death_penalty = 0.0
        if current_lives < self.previous_lives:
            death_penalty = 0.2 + (skill_level * 0.3)
        
        # === 9. 최종 보상 ===
        final_reward = max(0.0, base_reward + bonus + dodge_reward + kill_reward
                          - hp_damage_penalty - death_penalty)
        
        return {
            'survival_score': survival_score,
            'attack_score': attack_score,
            'base_reward': base_reward,  # 가중합 보상
            'bonus': bonus,
            'dodge_reward': dodge_reward,
            'kill_reward': kill_reward,
            'hp_damage_penalty': hp_damage_penalty,
            'death_penalty': death_penalty,
            'final_reward': final_reward,
            'target_survival_steps': target_survival_steps,
            'target_kills': target_kills,
            'current_step': current_step,
            'current_kills': current_kills,
            'survival_achievement': current_step / target_survival_steps,
            'kill_achievement': current_kills / target_kills if target_kills > 0 else 0.0,
            'w_survival': w_survival,  # 디버깅용 가중치
            'w_attack': w_attack,
        }
    
    def _empty_reward_breakdown(self) -> Dict[str, float]:
        """빈 보상 분해 딕셔너리 반환"""
        return {
            'survival_score': 0.0,
            'attack_score': 0.0,
            'base_reward': 0.0,
            'bonus': 0.0,
            'dodge_reward': 0.0,
            'kill_reward': 0.0,
            'hp_damage_penalty': 0.0,
            'death_penalty': 0.0,
            'final_reward': 0.0,
            'target_survival_steps': 0,
            'target_kills': 0.0,
            'current_step': 0,
            'current_kills': 0.0,
            'survival_achievement': 0.0,
            'kill_achievement': 0.0,
            'w_survival': 0.0,
            'w_attack': 0.0,
        }

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
            # 게임 상태 확인
            game_state = getattr(game_instance.game, "state", None)
            if game_state and hasattr(game_state, "state"):
                # GAME_OVER 상태이면 에피소드 종료
                if (
                    hasattr(game_state, "state")
                    and str(game_state.state) == "State.GAME_OVER"
                ):
                    return True

            # 목숨 수 확인
            game_vars = getattr(game_instance.game, "game_vars", None)
            if game_vars:
                lives = getattr(game_vars, "lives", 3)
                if lives <= 0:
                    return True

        return False

    def reset(self):
        """환경 리셋 (새 에피소드 시작)"""
        self.previous_score = 0
        self.previous_kills = 0
        self.previous_hp = 2  # 플레이어 기본 체력
        self.previous_lives = STARTING_LIVES
        self.previous_nearby_bullets = []
        self.previous_player_pos = (0, 0)
