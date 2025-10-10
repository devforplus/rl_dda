"""
게임 환경 구현

게임과 PPO 에이전트 사이의 브리지 역할을 하는 환경 클래스
"""

from typing import Dict

from src.components.entity_types import EntityType
from .data_types import GameLogData, EntityPosition, PlayerState, ActionType
from .targets import get_survival_target_steps
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

        # 에피소드 추적용 (새로 추가)
        self.episode_steps = 0
        self.episode_start_time = None

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
        print("🔄 환경 리셋 완료 - 새로운 에피소드 시작")

    def step(self):
        """매 스텝마다 호출하여 스텝 카운트 증가"""
        self.episode_steps += 1

    def extract_game_log_data(self, game_instance, skill_level: float) -> GameLogData:
        """게임 인스턴스에서 PPO 모델용 데이터를 추출

        Args:
            game_instance: 게임 인스턴스
            skill_level: 실력값 (0.0~1.0)

        Returns:
            추출된 게임 로그 데이터
        """
        entities = []
        player_state = PlayerState(hp=3, lives=3)
        current_step = self.episode_steps
        current_kills = 0
        current_score = 0

        # 게임 인스턴스에서 데이터 추출
        if hasattr(game_instance, "game") and game_instance.game:
            game_state = getattr(game_instance.game, "state", None)
            game_vars = getattr(game_instance.game, "game_vars", None)

            if game_state:
                # 플레이어 정보
                player = getattr(game_state, "player", None)
                if player:
                    player_hp = getattr(player, "current_hp", getattr(player, "hp", 3))
                    player_state = PlayerState(
                        hp=player_hp,
                        lives=getattr(game_vars, "lives", 3) if game_vars else 3,
                    )

                # 엔티티 수집 (플레이어, 적, 탄환)
                # 플레이어 위치 추가
                if player:
                    entities.append(
                        EntityPosition(
                            x=getattr(player, "x", 0),
                            y=getattr(player, "y", 0),
                            entity_type=EntityType.PLAYER,
                        )
                    )

                # 적 정보 추가 (game_state의 모든 적 객체)
                enemy_attrs = [
                    attr for attr in dir(game_state) if attr.startswith("enemy")
                ]
                for attr in enemy_attrs:
                    enemy_group = getattr(game_state, attr, None)
                    if enemy_group and hasattr(enemy_group, "__iter__"):
                        try:
                            for enemy in enemy_group:
                                if hasattr(enemy, "x") and hasattr(enemy, "y"):
                                    entities.append(
                                        EntityPosition(
                                            x=getattr(enemy, "x", 0),
                                            y=getattr(enemy, "y", 0),
                                            entity_type=EntityType.ENEMY,
                                        )
                                    )
                        except Exception:
                            pass

                # 탄환 정보 추가
                if hasattr(game_state, "enemy_shots"):
                    enemy_shots = getattr(game_state, "enemy_shots", [])
                    if enemy_shots and hasattr(enemy_shots, "__iter__"):
                        try:
                            for shot in enemy_shots:
                                if hasattr(shot, "x") and hasattr(shot, "y"):
                                    entities.append(
                                        EntityPosition(
                                            x=getattr(shot, "x", 0),
                                            y=getattr(shot, "y", 0),
                                            entity_type=EntityType.ENEMY_BULLET,
                                        )
                                    )
                        except Exception:
                            pass

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
        - 2지표 dynamic weighted sum: R = w1*survival + w2*attack (consistency는 0)
        - skill level에 따른 4단계 커리큘럼으로 점진적 성장
        - 생존 마스터 → 안전한 공격 → 균형 전투 → 공격적 플레이

        커리큘럼 단계:
        - 0.0~0.3: 생존 마스터 (80%→65% 생존, 20%→35% 공격)
        - 0.3~0.6: 안전한 공격 (65%→50% 생존, 35%→50% 공격)
        - 0.6~0.8: 균형잡힌 전투 (50%→40% 생존, 50%→60% 공격)
        - 0.8~1.0: 공격적 플레이 (40%→35% 생존, 60%→65% 공격)

        핵심 철학:
        - 실력값 입력 → 해당 수준의 플레이 스타일로 동작
        - 단계별 학습으로 안정적이고 자연스러운 성장 곡선
        - 초보자는 생존 중심, 고수는 공격 중심

        Args:
            game_instance: 게임 인스턴스
            skill_level: 실력값 (0.0 ~ 1.0)

        Returns:
            커리큘럼 단계별 weighted sum 보상값 (0.0 ~ 1.0 스케일)
        """
        if not (hasattr(game_instance, "game") and game_instance.game):
            return 0.0

        game_vars = getattr(game_instance.game, "game_vars", None)
        if not game_vars:
            return 0.0

        current_step = self.episode_steps
        current_kills = getattr(game_vars, "kills", 0)
        current_lives = getattr(game_vars, "lives", 3)

        # 실력값 기반 적응적 목표 설정 (공유 타겟 맵 사용)
        target_survival_steps = get_survival_target_steps(skill_level)
        target_kill_rate = skill_level * 3.0  # 0 ~ 3 킬/100스텝

        # === 1. 생존 지표 (Survival Score) ===
        # 단순한 비율 기반, 연속적 점수 (0.0 ~ 1.0)
        survival_score = min(1.0, current_step / target_survival_steps)

        # === 2. 공격 지표 (Attack Score) ===
        # 현재 킬 레이트와 목표 킬 레이트 비교
        if current_step > 0 and target_kill_rate > 0:
            current_kill_rate = (
                current_kills / max(current_step, 1)
            ) * 100.0  # 킬/100스텝
            attack_score = min(1.0, current_kill_rate / target_kill_rate)
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

        # === Balanced Weight System for All-Round Agent ===
        # 일관성 weight는 0으로 고정 (사용자 요청)
        w_consistency = 0.0

        # 커리큘럼 러닝 기반 실력값별 플레이 스타일 시뮬레이션
        # skill level에 따라 생존 중심 → 공격 중심으로 점진적 전환
        if skill_level <= 0.3:
            # 초보자: 생존 마스터 단계 (80% → 65% 생존)
            progress = skill_level / 0.3  # 0.0 ~ 1.0
            w_survival = 0.8 - (progress * 0.15)  # 0.8 → 0.65
            w_attack = 0.2 + (progress * 0.15)  # 0.2 → 0.35
        elif skill_level <= 0.6:
            # 중급자: 안전한 공격 단계 (65% → 50% 생존)
            progress = (skill_level - 0.3) / 0.3  # 0.0 ~ 1.0
            w_survival = 0.65 - (progress * 0.15)  # 0.65 → 0.5
            w_attack = 0.35 + (progress * 0.15)  # 0.35 → 0.5
        elif skill_level <= 0.8:
            # 중고급자: 균형잡힌 전투 단계 (50% → 40% 생존)
            progress = (skill_level - 0.6) / 0.2  # 0.0 ~ 1.0
            w_survival = 0.5 - (progress * 0.1)  # 0.5 → 0.4
            w_attack = 0.5 + (progress * 0.1)  # 0.5 → 0.6
        else:
            # 고수: 공격적 플레이 단계 (40% → 35% 생존)
            progress = (skill_level - 0.8) / 0.2  # 0.0 ~ 1.0
            w_survival = 0.4 - (progress * 0.05)  # 0.4 → 0.35
            w_attack = 0.6 + (progress * 0.05)  # 0.6 → 0.65

        # 최종 보상 계산 (0.0 ~ 1.0 스케일)
        final_reward = (
            w_survival * survival_score
            + w_attack * attack_score
            + w_consistency * consistency_score
        )

        # 사망 시 즉시 페널티 (기존 구조 유지하되 단순화)
        death_penalty = 0.0
        if current_lives < self.previous_lives:
            death_penalty = 0.2 + (skill_level * 0.3)  # 0.2 ~ 0.5 페널티
            self.previous_lives = current_lives

        # 최종 보상 (페널티 적용 후 클리핑)
        final_reward = max(0.0, final_reward - death_penalty)

        # 상태 업데이트
        self.previous_kills = current_kills

        return final_reward

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
