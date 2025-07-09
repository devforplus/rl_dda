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
    """PPO 강화학습을 위한 게임 환경 클래스

    게임 상태를 관찰하고 에이전트의 액션에 따른 보상을 계산합니다.

    Attributes:
        max_entities: 최대 엔티티 수 (상태 벡터 크기 고정용)
        entity_feature_size: 엔티티당 특성 수
        state_size: 전체 상태 벡터 크기
        action_size: 액션 공간 크기
        max_lives: 플레이어의 최대 목숨 수 (정규화용)
        final_stage_num: 마지막 스테이지 번호 (정규화용)

    ---

    게임과 강화학습 환경을 연결하는 인터페이스 클래스
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

        self.reset()

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
        단순화된 보상 함수: 생존과 적 제거에 초점

        Args:
            game_state: 현재 게임 상태
            last_action: 에이전트가 마지막으로 취한 행동

        Returns:
            계산된 보상 값
        """
        reward = 0.0

        # 1. 생존 보상 (매 스텝마다 작은 보상)
        reward += 0.01

        # 2. 적 제거 보상
        if game_state.score > self.last_score:
            reward += (
                game_state.score - self.last_score
            ) * 0.1  # 점수 증가분을 보상에 반영

        # 3. 사망 시 큰 패널티
        if game_state.player_lives < self.last_lives:
            reward -= 100.0
            print(f"💀 DEATH PENALTY: -100.0 applied.")

        # 상태 업데이트
        self.last_score = game_state.score
        self.last_lives = game_state.player_lives

        return reward

    def _calculate_reward_original(
        self, game_state: GameState, last_action: int
    ) -> float:
        """보상 계산 (원본)

        에이전트의 행동에 대한 보상을 계산합니다.
        생존, 적 파괴, 위험 회피 등 다양한 요소를 고려합니다.

        Args:
            game_state: 현재 게임 상태
            last_action: 에이전트가 마지막으로 취한 행동

        Returns:
            계산된 보상 값
        """
        total_reward = 0.0

        # 커리큘럼 기반 보상 스케일링
        curriculum_multiplier = 0.6 + (
            self.curriculum_stage * 0.08
        )  # 0.6 ~ 1.0 (더 보수적)
        stability_multiplier = self.stability_factor  # 0.5 ~ 1.5

        # 기본 생존 보상 - 일관된 생존 중시
        base_survival_reward = 0.15 * curriculum_multiplier  # 0.12에서 0.15로 소폭 증가
        skill_multiplier = 1.0 + (
            game_state.skill_level * 0.7
        )  # 0.8에서 0.7로 감소 (안정화)
        survival_reward = base_survival_reward * skill_multiplier * stability_multiplier
        total_reward += survival_reward

        # 적극적인 플레이를 위한 전투 효율성 보상
        enemy_count = sum(
            1
            for entity in game_state.entities
            if entity.entity_type == EntityType.ENEMY
        )
        enemy_shot_count = sum(
            1
            for entity in game_state.entities
            if entity.entity_type == EntityType.ENEMY_SHOT
        )

        # 보스 감지 및 보스전 균형잡힌 보상
        boss_types = [
            EntityType.ENEMY_J,
            EntityType.ENEMY_K,
            EntityType.ENEMY_L,
            EntityType.ENEMY_M,
        ]
        boss_count = sum(
            1 for entity in game_state.entities if entity.entity_type in boss_types
        )

        # 스테이지 진행 감지 (보스 출현은 스테이지 후반부를 의미)
        stage_progress_bonus = 0.0
        if boss_count > 0:
            # 보스전 진입 보너스 (안정적으로 조정)
            stage_progress_bonus = (
                20.0 * skill_multiplier * stability_multiplier
            )  # 50.0에서 20.0으로 감소
            total_reward += stage_progress_bonus
            print(f"🏰 BOSS ENCOUNTER: +{stage_progress_bonus:.1f} (Boss appeared!)")

        # 1. 적 처치 보상 (보스 처치 보상 안정화)
        if self.previous_state is not None:
            kill_increase = game_state.kills - self.previous_state.kills
            if kill_increase > 0:
                # 보스전 중일 때 킬 보상 적절히 증가 (과도하지 않게)
                if boss_count > 0:
                    base_kill_reward = 80.0  # 150.0에서 80.0으로 감소 (안정화)
                    print(
                        f"🔥 BOSS BATTLE KILL: +{base_kill_reward:.1f} (Critical boss damage!)"
                    )
                else:
                    base_kill_reward = 25.0 + (self.curriculum_stage * 5.0)  # 소폭 감소

                enemy_density_bonus = min(
                    enemy_count * 2.0, 12.0
                )  # 3.0에서 2.0으로 감소
                kill_reward = (
                    (base_kill_reward + enemy_density_bonus)
                    * skill_multiplier
                    * stability_multiplier
                )
                total_reward += kill_reward
                print(
                    f"🎯 KILL REWARD: +{kill_reward:.1f} (stage {self.curriculum_stage}, enemies: {enemy_count})"
                )

        # 2. 공격 행동에 대한 즉시 보상 (보스전 중 적절한 가중치)
        if last_action == ActionType.FIRE:
            if boss_count > 0:
                # 보스전 중 공격 시 적절한 보상
                fire_reward = (
                    1.5 * skill_multiplier * stability_multiplier
                )  # 3.0에서 1.5로 감소
                print(f"⚔️ BOSS ATTACK: +{fire_reward:.1f} (Attacking boss!)")
            else:
                fire_reward = (
                    (0.5 + self.curriculum_stage * 0.1)
                    * skill_multiplier
                    * stability_multiplier
                )  # 소폭 감소

            if enemy_count > 0:
                enemy_target_bonus = (
                    min(enemy_count * 0.2, 1.5) * stability_multiplier
                )  # 0.3에서 0.2로 감소
                fire_reward += enemy_target_bonus * skill_multiplier
            total_reward += fire_reward

        # 3. 점수 증가 보상 (적절한 수준으로 조정)
        if self.previous_state is not None:
            score_increase = game_state.score - self.previous_state.score
            if score_increase > 0:
                score_reward = (
                    score_increase * 0.005 * skill_multiplier * stability_multiplier
                )  # 0.008에서 0.005로 감소
                total_reward += score_reward

        # 4. 생존 시간 보너스 (점진적이고 안정적)
        if game_state.survival_time > 0:
            # 보스전 중일 때도 과도하지 않게 조정
            if boss_count > 0:
                time_bonus_base = (
                    game_state.survival_time**0.6
                ) * 0.015  # 0.025에서 0.015로 감소
            else:
                time_bonus_base = (
                    game_state.survival_time**0.6
                ) * 0.012  # 0.02에서 0.012로 감소
            time_bonus = time_bonus_base * skill_multiplier * stability_multiplier
            total_reward += time_bonus

        # 5. 체력 유지 보상 및 피격 페널티
        if self.previous_state is not None:
            # 피격 페널티 (체력 감소 시)
            hp_decrease = self.previous_state.player_hp - game_state.player_hp
            if hp_decrease > 0:
                # 목숨을 잃은 경우는 제외 (사망 페널티와 중복 방지)
                if game_state.player_lives == self.previous_state.player_lives:
                    hit_penalty = 15.0 * hp_decrease  # 잃은 체력만큼 페널티
                    total_reward -= hit_penalty
                    print(f"💔 HIT PENALTY: -{hit_penalty:.1f} (HP decreased)")

        hp_ratio = game_state.player_hp / 2.0
        if hp_ratio == 1.0:
            hp_bonus = (
                0.8 * skill_multiplier * stability_multiplier
            )  # 1.0에서 0.8로 감소
            if boss_count > 0:
                hp_bonus *= 1.5  # 2.0에서 1.5로 감소
            total_reward += hp_bonus
        elif hp_ratio >= 0.5:
            hp_bonus = (
                0.3 * skill_multiplier * stability_multiplier
            )  # 0.4에서 0.3으로 감소
            total_reward += hp_bonus

        # 6. 위험 회피 보너스
        if self.previous_state is not None:
            # 플레이어 근처의 위험한 탄환 수 계산
            prev_dangerous_shots = sum(
                1
                for e in self.previous_state.entities
                if e.entity_type == EntityType.ENEMY_SHOT and e.distance_to_player < 50
            )
            current_dangerous_shots = sum(
                1
                for e in game_state.entities
                if e.entity_type == EntityType.ENEMY_SHOT and e.distance_to_player < 50
            )
            # 위험한 탄환이 줄어들었다면 (회피 성공) 보상
            if current_dangerous_shots < prev_dangerous_shots:
                dodged_bullets = prev_dangerous_shots - current_dangerous_shots
                dodge_reward = (
                    (5.0 * dodged_bullets) * skill_multiplier * stability_multiplier
                )
                total_reward += dodge_reward
                print(
                    f" dodging bullets reward: +{dodge_reward:.1f} (Dodged {dodged_bullets} bullets!)"
                )

        # 7. 스테이지 진행 보상 (핵심이지만 안정적으로)
        if self.previous_state is not None:
            stage_increase = (
                game_state.current_stage - self.previous_state.current_stage
            )
            if stage_increase > 0:
                # 스테이지 클리어 시 큰 보상이지만 과도하지 않게
                stage_clear_reward = (
                    500.0 * (game_state.current_stage) * skill_multiplier
                )  # 1000.0에서 500.0으로 감소
                total_reward += stage_clear_reward
                print(
                    f"🏆 STAGE CLEAR! +{stage_clear_reward:.1f} (Reached Stage {game_state.current_stage}!)"
                )

        # 8. 생존 마일스톤 보상 (점진적이고 균형잡힌)
        survival_milestones = [
            (300, 1.5),  # 5초 - 기본 생존
            (600, 3.0),  # 10초 - 안정적 생존
            (900, 5.0),  # 15초 - 중반 진행
            (1200, 8.0),  # 20초 - 보스 접근
            (1800, 15.0),  # 30초 - 보스전 가능성
            (2400, 25.0),  # 40초 - 보스전 중
            (3000, 40.0),  # 50초 - 스테이지 클리어 임박
            (3600, 60.0),  # 60초 - 확실한 스테이지 클리어
        ]

        if self.previous_state is not None:
            for milestone_time, milestone_reward in survival_milestones:
                if (
                    self.previous_state.survival_time
                    < milestone_time
                    <= game_state.survival_time
                ):
                    final_milestone_reward = (
                        milestone_reward * skill_multiplier * stability_multiplier
                    )
                    total_reward += final_milestone_reward
                    print(
                        f"🏆 SURVIVAL MILESTONE: +{final_milestone_reward:.1f} ({milestone_time / 60:.1f}s)"
                    )

        # 9. 연속 생존 보너스 (균형잡힌 수준)
        if game_state.survival_time > 1200:  # 20초 이상 생존 시
            consistency_bonus = (
                min((game_state.survival_time - 1200) * 0.01, 10.0)
                * stability_multiplier
            )  # 0.015에서 0.01로 감소
            if boss_count > 0:
                consistency_bonus *= 1.5  # 2.0에서 1.5로 감소
            total_reward += consistency_bonus

        # 10. 전투 회피 페널티 (보스전에서 적절한 강화)
        if self.previous_state is not None and len(self.action_history) >= 15:
            recent_fires = sum(
                1 for a in self.action_history[-20:] if a == ActionType.FIRE
            )
            fire_ratio = recent_fires / min(len(self.action_history), 20)

            # 보스전 중 공격하지 않으면 적절한 페널티
            if boss_count > 0 and fire_ratio < 0.15:  # 0.1에서 0.15로 완화
                boss_passivity_penalty = (
                    10.0 * skill_multiplier
                )  # 20.0에서 10.0으로 감소
                total_reward -= boss_passivity_penalty
                print(
                    f"⚠️ BOSS PASSIVITY PENALTY: -{boss_passivity_penalty:.1f} (Must attack boss!)"
                )
            elif enemy_count > 6 and fire_ratio < 0.02:  # 5에서 6으로 기준 상향
                passivity_penalty = (
                    (enemy_count - 6) * 0.3 * skill_multiplier
                )  # 0.4에서 0.3으로 감소
                total_reward -= passivity_penalty

        # 11. 위험 관리 보상/페널티 (균형 조정)
        danger_level = (
            (enemy_count * 0.15) + (enemy_shot_count * 0.08) + (boss_count * 1.5)
        )

        if danger_level > 2.0:
            if last_action == ActionType.FIRE:
                courage_bonus = (
                    danger_level * 0.3 * skill_multiplier * stability_multiplier
                )  # 0.4에서 0.3으로 감소
                if boss_count > 0:
                    courage_bonus *= 1.3  # 1.5에서 1.3으로 감소
                total_reward += courage_bonus
            else:
                danger_penalty = (
                    danger_level * 0.02 * skill_multiplier
                )  # 0.03에서 0.02로 감소
                total_reward -= danger_penalty
        elif danger_level < 0.3:
            safety_bonus = (
                0.08 * skill_multiplier * stability_multiplier
            )  # 0.1에서 0.08로 감소
            total_reward += safety_bonus

        # 12. 목숨 감소 시 페널티 (안정적 조정)
        if self.previous_state is not None:
            life_lost = self.previous_state.player_lives - game_state.player_lives
            if life_lost > 0:
                # 보스전 중 사망 시 적절한 페널티
                if boss_count > 0:
                    base_death_penalty = 80.0 + (
                        self.curriculum_stage * 15.0
                    )  # 50.0에서 80.0으로 증가 (적절한 수준)
                    print(
                        f"💀 BOSS BATTLE DEATH: -{base_death_penalty:.1f} (Boss fight death)"
                    )
                else:
                    base_death_penalty = 100.0 + (
                        self.curriculum_stage * 20.0
                    )  # 120.0에서 100.0으로 감소

                survival_time_penalty = min(
                    game_state.survival_time * 0.02, 15.0
                )  # 0.03에서 0.02로 감소
                skill_death_multiplier = 1.0 + (
                    game_state.skill_level * 0.1
                )  # 0.15에서 0.1로 감소

                total_death_penalty = (
                    base_death_penalty + survival_time_penalty
                ) * skill_death_multiplier
                # 안정성 계수로 페널티 완화
                total_death_penalty *= 2.0 - stability_multiplier
                total_reward -= total_death_penalty
                print(
                    f"💀 DEATH PENALTY: -{total_death_penalty:.1f} (stability: {stability_multiplier:.2f})"
                )

        # 13. 움직임 보상 (적절한 수준)
        if last_action in [
            ActionType.LEFT,
            ActionType.RIGHT,
            ActionType.UP,
            ActionType.DOWN,
        ]:
            movement_reward = (
                0.05 * skill_multiplier * stability_multiplier
            )  # 0.06에서 0.05로 감소
            if boss_count > 0:
                movement_reward *= 1.1  # 1.2에서 1.1로 감소
            total_reward += movement_reward

        # 14. 안정성 강화 메커니즘 (더 보수적인 제한)
        # 극단적인 보상 변화 방지
        if total_reward < -150:  # -200에서 -150으로 강화
            smoothed_penalty = (
                -150 + (total_reward + 150) * 0.4
            )  # 0.3에서 0.4로 증가 (덜 가혹하게)
            total_reward = smoothed_penalty

        # 과도한 양수 보상 제한 강화
        if total_reward > 150:  # 300에서 150으로 대폭 감소 (안정성 강화)
            smoothed_reward = (
                150 + (total_reward - 150) * 0.1
            )  # 0.2에서 0.1로 감소 (더 강한 제한)
            total_reward = smoothed_reward

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
