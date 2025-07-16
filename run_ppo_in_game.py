#!/usr/bin/env python
"""
PPO 에이전트와 실제 게임 연동 스크립트 (개선된 보상 시스템 통합)

훈련된 PPO 에이전트가 실제 게임 환경에서 플레이하도록 합니다.
게임 상태를 실시간으로 추출하여 에이전트에 전달하고,
에이전트의 액션을 게임 입력으로 변환합니다.

개선사항:
- 향상된 보상 시스템 (10배 생존 보상, 세분화된 마일스톤)
- 감소된 사망 페널티 (50% 감소)
- 공격 행동 장려 시스템
- 완전한 시각화 및 로깅

---

실제 게임과 강화학습 에이전트를 연동하는 통합 스크립트
"""

import sys
import os
import time
import traceback
import csv
import json
from datetime import datetime
from typing import Optional, Dict, Any

# src 디렉토리를 시스템 경로에 추가
src_path = os.path.join(os.path.dirname(__file__), "src")
sys.path.insert(0, src_path)

try:
    import pyxel as px
    from main import App
    from rl.agents.ppo_agent import PPOAgent, create_ppo_agent
    from rl.environment import GameEnvironment
    from rl.game_adapter import GameStateAdapter
    from components.entity_types import EntityType
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    print(
        "Make sure all required modules are installed and paths are correct.",
        file=sys.stderr,
    )
    sys.exit(1)


class ImprovedGameEnvironment(GameEnvironment):
    """개선된 보상 시스템을 가진 게임 환경 (동일한 환경에서 에이전트 능력 차별화)"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 개선된 생존 마일스톤 (더 세분화된 보상)
        self.improved_survival_milestones = [
            (60, 15.0),  # 1초 - 첫 생존
            (120, 25.0),  # 2초 - 기본 생존
            (180, 40.0),  # 3초 - 안정적 생존
            (240, 60.0),  # 4초 - 좋은 생존
            (300, 100.0),  # 5초 - 우수한 생존
            (420, 150.0),  # 7초 - 뛰어난 생존
            (600, 250.0),  # 10초 - 탁월한 생존
            (900, 400.0),  # 15초 - 마스터 레벨
            (1200, 600.0),  # 20초 - 전문가 레벨
        ]

        # 커리큘럼 학습 설정 추가
        self.curriculum_phase = (
            0  # 0: 기본 조작 학습, 1: 생존 학습, 2: 공격 학습, 3: 고급 전략
        )
        # 🎯 개선된 에피소드 분배: 더 빨리 실제 게임에 노출
        self.phase_episode_counts = [100, 150, 250, 500]  # 총 1000 에피소드
        self.total_episodes = 0
        # 🛡️ 개선된 무적 시간: 대폭 감소
        self.invulnerability_frames = 60  # 초기 무적 시간 1초 (기존 3초에서 대폭 감소)

        print("🚀 Improved reward system with BALANCED Curriculum Learning activated!")
        print(
            "🎯 Same environment for all skill levels - Agent ability differentiation enabled!"
        )

    def set_skill_level(self, skill_level: float):
        """스킬 레벨 설정 및 환경 난이도 조정

        Args:
            skill_level: 스킬 레벨 (0.0-1.0)
        """
        self.skill_level = skill_level
        self.update_environment_difficulty()

    def update_environment_difficulty(self):
        """스킬 레벨에 따른 환경 난이도 조정"""
        skill = self.skill_level

        if skill < 0.3:  # 🔰 초보자: 매우 쉬운 환경
            self.environment_modifications = {
                "enemy_speed_multiplier": 0.6,  # 적 속도 40% 감소
                "enemy_spawn_rate": 0.7,  # 적 생성 30% 감소
                "enemy_shot_speed": 0.5,  # 적 탄환 속도 50% 감소
                "player_invulnerability_bonus": 1.5,  # 무적 시간 50% 증가
                "player_speed_bonus": 1.2,  # 플레이어 속도 20% 증가
                "enemy_damage_multiplier": 0.7,  # 적 데미지 30% 감소
                "environment_name": "EASY",
                "target_survival_time": 15.0,  # 목표 생존 시간
                "recommended_episodes": 300,  # 권장 에피소드 수
            }
            print(
                f"🔰 EASY Environment: Slower enemies, reduced damage, extended invulnerability"
            )

        elif skill < 0.7:  # ⚖️ 중급자: 표준 환경
            self.environment_modifications = {
                "enemy_speed_multiplier": 0.85,  # 적 속도 15% 감소
                "enemy_spawn_rate": 0.9,  # 적 생성 10% 감소
                "enemy_shot_speed": 0.8,  # 적 탄환 속도 20% 감소
                "player_invulnerability_bonus": 1.0,  # 무적 시간 변화 없음
                "player_speed_bonus": 1.0,  # 플레이어 속도 변화 없음
                "enemy_damage_multiplier": 0.9,  # 적 데미지 10% 감소
                "environment_name": "NORMAL",
                "target_survival_time": 20.0,
                "recommended_episodes": 500,
            }
            print(f"⚖️ NORMAL Environment: Slightly reduced difficulty")

        else:  # 🔥 고급자: 어려운 환경
            self.environment_modifications = {
                "enemy_speed_multiplier": 1.3,  # 적 속도 30% 증가
                "enemy_spawn_rate": 1.4,  # 적 생성 40% 증가
                "enemy_shot_speed": 1.5,  # 적 탄환 속도 50% 증가
                "player_invulnerability_bonus": 0.7,  # 무적 시간 30% 감소
                "player_speed_bonus": 1.0,  # 플레이어 속도 변화 없음
                "enemy_damage_multiplier": 1.3,  # 적 데미지 30% 증가
                "environment_name": "HARD",
                "target_survival_time": 30.0,
                "recommended_episodes": 800,
            }
            print(
                f"🔥 HARD Environment: Faster enemies, increased damage, reduced invulnerability"
            )

        # 환경 정보 출력
        print(
            f"   🎮 Environment: {self.environment_modifications['environment_name']}"
        )
        print(
            f"   🎯 Target Survival: {self.environment_modifications['target_survival_time']:.1f}s"
        )
        print(
            f"   📊 Enemy Speed: {self.environment_modifications['enemy_speed_multiplier']:.1f}x"
        )
        print(
            f"   🔫 Enemy Spawn: {self.environment_modifications['enemy_spawn_rate']:.1f}x"
        )
        print(
            f"   💥 Enemy Damage: {self.environment_modifications['enemy_damage_multiplier']:.1f}x"
        )

    def get_environment_info(self) -> dict:
        """현재 환경 정보 반환"""
        return self.environment_modifications.copy()

    def get_current_phase_info(self):
        """현재 커리큘럼 단계 정보 반환"""
        phase_names = [
            "Quick Control",  # 기존: Basic Control
            "Survival Focus",  # 기존: Survival Training
            "Combat Training",  # 동일
            "Master Strategy",  # 기존: Advanced Strategy
        ]

        base_info = {
            "phase": self.curriculum_phase,
            "name": phase_names[self.curriculum_phase],
            "episode_in_phase": self.total_episodes
            - sum(self.phase_episode_counts[: self.curriculum_phase]),
            "total_in_phase": self.phase_episode_counts[self.curriculum_phase],
            "invulnerability": self.invulnerability_frames > 0,
        }

        return base_info

    def update_curriculum_phase(self, episode_count: int):
        """에피소드 수에 따라 커리큘럼 단계 업데이트"""
        self.total_episodes = episode_count

        cumulative = 0
        for i, count in enumerate(self.phase_episode_counts):
            cumulative += count
            if episode_count <= cumulative:
                old_phase = self.curriculum_phase
                self.curriculum_phase = i

                # 단계 변경 시 알림
                if old_phase != self.curriculum_phase:
                    phase_info = self.get_current_phase_info()
                    print(f"\n🎓 Curriculum Phase Changed: {phase_info['name']}")
                    print(
                        f"   Phase {self.curriculum_phase + 1}/4: Episodes {episode_count}/{cumulative}"
                    )

                # 🛡️ 개선된 단계별 무적 시간: 더 빠른 난이도 증가
                if self.curriculum_phase == 0:  # 빠른 조작 학습 (100 에피소드)
                    self.invulnerability_frames = 60  # 1초 (기존 3초에서 감소)
                elif self.curriculum_phase == 1:  # 생존 집중 (150 에피소드)
                    self.invulnerability_frames = 30  # 0.5초 (기존 2초에서 대폭 감소)
                elif self.curriculum_phase == 2:  # 전투 훈련 (250 에피소드)
                    self.invulnerability_frames = 15  # 0.25초 (기존 1초에서 감소)
                else:  # 마스터 전략 (500 에피소드)
                    self.invulnerability_frames = 0  # 무적 없음

                return

        # 모든 단계 완료
        self.curriculum_phase = 3
        self.invulnerability_frames = 0

    def calculate_reward_improved(self, game_state, last_action: int) -> float:
        """개선된 보상 계산 시스템 (커리큘럼 학습 + 스킬 차별화 포함)

        기존 보상 시스템을 기반으로 하되, 커리큘럼 학습을 통한 단계적 난이도 조절과
        스킬 레벨에 따른 차별화된 보상 체계를 적용:

        커리큘럼 단계:
        1. 1단계: 기본 조작 학습 (무적 시간 1초, 움직임 보상 강화)
        2. 2단계: 생존 학습 (무적 시간 0.5초, 생존 보상 강화)
        3. 3단계: 전투 학습 (무적 시간 0.25초, 공격 보상 강화)
        4. 4단계: 고급 전략 (무적 없음, 종합 평가)

        스킬 차별화:
        - 고실력자: 더 엄격한 기준, 높은 페널티, 낮은 기본 보상 (더 어려운 목표)
        - 저실력자: 관대한 기준, 낮은 페널티, 높은 격려 보상 (달성 가능한 목표)
        """
        total_reward = 0.0
        phase_info = self.get_current_phase_info()

        # 🎯 스킬 기반 보상 차별화 설정 (동일한 환경에서 다른 기준)
        skill = game_state.skill_level

        # 스킬별 기대 성과 기준치 설정 (동일한 환경에서 다른 목표)
        if skill < 0.3:  # 초보자 (skill 0-0.3) - 기본 목표
            survival_skill_multiplier = 2.0  # 생존 자체가 큰 성취
            fire_skill_multiplier = 1.5  # 공격 행동 큰 격려
            death_skill_multiplier = 0.5  # 관대한 사망 페널티
            stage_skill_multiplier = 2.0  # 높은 스테이지 클리어 보상
            hit_skill_multiplier = 0.5  # 낮은 피격 페널티
            skill_target_survival = 10.0  # 초보자 목표: 10초 생존
        elif skill < 0.7:  # 중급자 (skill 0.3-0.7) - 중간 목표
            survival_skill_multiplier = 1.5
            fire_skill_multiplier = 1.2
            death_skill_multiplier = 0.8
            stage_skill_multiplier = 1.5
            hit_skill_multiplier = 0.8
            skill_target_survival = 20.0  # 중급자 목표: 20초 생존
        else:  # 고급자 (skill 0.7-1.0) - 고급 목표
            survival_skill_multiplier = 1.0  # 기본 생존 보상
            fire_skill_multiplier = 1.0  # 기본 공격 보상
            death_skill_multiplier = 1.5  # 엄격한 사망 페널티
            stage_skill_multiplier = 1.0  # 낮은 스테이지 클리어 보상
            hit_skill_multiplier = 1.2  # 높은 피격 페널티
            skill_target_survival = 30.0  # 고급자 목표: 30초 생존

        # 단계별 보상 가중치 조정
        if self.curriculum_phase == 0:  # 기본 조작 학습
            base_survival_multiplier = 2.0  # 생존 보상 2배
            movement_multiplier = 3.0  # 움직임 보상 3배
            milestone_multiplier = 0.5  # 마일스톤 보상 절반
            death_penalty_multiplier = 0.3  # 사망 페널티 30%
        elif self.curriculum_phase == 1:  # 생존 훈련
            base_survival_multiplier = 1.5
            movement_multiplier = 1.5
            milestone_multiplier = 1.0
            death_penalty_multiplier = 0.5
        elif self.curriculum_phase == 2:  # 전투 훈련
            base_survival_multiplier = 1.0
            movement_multiplier = 1.0
            milestone_multiplier = 1.2
            death_penalty_multiplier = 0.7
        else:  # 고급 전략
            base_survival_multiplier = 1.0
            movement_multiplier = 1.0
            milestone_multiplier = 1.0
            death_penalty_multiplier = 1.0

        # 1. 스킬 차별화된 기본 생존 보상
        base_survival_reward = (
            0.1 * base_survival_multiplier * survival_skill_multiplier
        )
        total_reward += base_survival_reward

        # 2. 개선된 생존 마일스톤 보상 (스킬 차별화)
        if self.previous_state is not None:
            for milestone_time, milestone_reward in self.improved_survival_milestones:
                if (
                    self.previous_state.survival_time
                    < milestone_time
                    <= game_state.survival_time
                ):
                    # 스킬과 커리큘럼 단계에 따른 조정
                    adjusted_reward = (
                        milestone_reward
                        * milestone_multiplier
                        * survival_skill_multiplier
                    )
                    total_reward += adjusted_reward

                    # 스킬 목표 정보 포함한 출력
                    skill_info = f" (Skill {skill:.1f})" if skill != 0.5 else ""
                    target_info = (
                        f" [Target: {skill_target_survival:.1f}s]"
                        if skill_target_survival != 20.0
                        else ""
                    )
                    if milestone_multiplier != 1.0 or survival_skill_multiplier != 1.0:
                        print(
                            f"MILESTONE{skill_info}{target_info}: +{adjusted_reward:.1f} ({milestone_time / 60:.1f}s)"
                        )
                    else:
                        print(
                            f"MILESTONE: +{adjusted_reward:.1f} ({milestone_time / 60:.1f}s)"
                        )

        # 3. 스킬 차별화된 점수 증가 보상
        if game_state.score > self.last_score:
            score_reward = (
                (game_state.score - self.last_score) * 0.2 * survival_skill_multiplier
            )
            total_reward += score_reward

        # 4. 스킬과 단계별 조정된 사망 페널티
        if game_state.player_lives < self.last_lives:
            base_death_penalty = -50.0
            total_death_penalty = (
                base_death_penalty * death_penalty_multiplier * death_skill_multiplier
            )
            total_reward += total_death_penalty

            skill_info = f" (Skill {skill:.1f})" if skill != 0.5 else ""
            if death_penalty_multiplier != 1.0 or death_skill_multiplier != 1.0:
                print(f"DEATH PENALTY{skill_info}: {total_death_penalty:.1f}")
            else:
                print(f"DEATH PENALTY: {total_death_penalty:.1f}")

        # 5. 스킬 차별화된 공격 행동 장려 보상
        if last_action == 8:  # FIRE 액션
            base_fire_reward = 1.0 if self.curriculum_phase < 2 else 2.0
            fire_reward = base_fire_reward * fire_skill_multiplier
            total_reward += fire_reward

        # 6. 스킬 차별화된 적극적 움직임 보상
        if last_action != 4:  # 정지 액션이 아닐 때
            movement_reward = 0.1 * movement_multiplier * survival_skill_multiplier
            total_reward += movement_reward

        # 7. 스킬 차별화된 피격 페널티 (새로 추가)
        if (
            self.previous_state is not None
            and game_state.player_hp < self.previous_state.player_hp
        ):
            # 목숨을 잃지 않은 경우에만 피격 페널티 적용 (사망 페널티와 중복 방지)
            if game_state.player_lives == self.previous_state.player_lives:
                hp_decrease = self.previous_state.player_hp - game_state.player_hp
                base_hit_penalty = 10.0 * hp_decrease
                hit_penalty = base_hit_penalty * hit_skill_multiplier
                total_reward -= hit_penalty

                skill_info = f" (Skill {skill:.1f})" if skill != 0.5 else ""
                print(f"HIT PENALTY{skill_info}: -{hit_penalty:.1f}")

        # 8. 스킬 차별화된 스테이지 진행 보상 (새로 추가)
        if self.previous_state is not None:
            stage_increase = (
                game_state.current_stage - self.previous_state.current_stage
            )
            if stage_increase > 0:
                base_stage_reward = 200.0 * stage_increase
                stage_reward = base_stage_reward * stage_skill_multiplier
                total_reward += stage_reward

                skill_info = f" (Skill {skill:.1f})" if skill != 0.5 else ""
                print(f"STAGE CLEAR{skill_info}: +{stage_reward:.1f}")

        # 9. 🎯 스킬별 목표 달성도 평가 (새로 추가)
        if self.previous_state is not None and skill_target_survival > 0:
            # 🔧 배속 모드 고려한 실제 생존 시간 계산
            survival_seconds = self._convert_survival_time_to_seconds(
                game_state.survival_time
            )
            previous_survival_seconds = self._convert_survival_time_to_seconds(
                self.previous_state.survival_time
            )

            # 스킬별 목표 생존 시간 달성 보상
            target_thresholds = [
                (skill_target_survival * 0.5, 50.0),  # 목표의 50% 달성
                (skill_target_survival * 0.75, 100.0),  # 목표의 75% 달성
                (skill_target_survival, 200.0),  # 목표 100% 달성
                (skill_target_survival * 1.5, 350.0),  # 목표 초과 달성
            ]

            for threshold_time, threshold_reward in target_thresholds:
                if previous_survival_seconds < threshold_time <= survival_seconds:
                    # 스킬별 기본 보상 (목표 달성 자체가 보상)
                    skill_achievement_reward = threshold_reward
                    total_reward += skill_achievement_reward

                    percentage = int((threshold_time / skill_target_survival) * 100)
                    print(
                        f"🎯 SKILL TARGET: +{skill_achievement_reward:.1f} ({percentage}% of {skill_target_survival:.1f}s goal)"
                    )

                    # 고급자가 어려운 목표를 달성했을 때 추가 보상
                    if skill >= 0.7 and threshold_time >= skill_target_survival:
                        expert_bonus = threshold_reward * 0.5  # 50% 보너스
                        total_reward += expert_bonus
                        print(
                            f"🏆 EXPERT BONUS: +{expert_bonus:.1f} (High skill achievement!)"
                        )

        # 10. 커리큘럼 단계별 추가 보상 (기존 유지)
        if self.curriculum_phase == 0:  # 기본 조작: 다양한 액션 시도 보상
            if hasattr(self, "recent_actions"):
                self.recent_actions.append(last_action)
                if len(self.recent_actions) > 10:
                    self.recent_actions.pop(0)
                # 다양성 보상 (스킬 차별화)
                if len(set(self.recent_actions)) >= 5:
                    diversity_reward = 1.0 * survival_skill_multiplier
                    total_reward += diversity_reward
            else:
                self.recent_actions = [last_action]

        # 상태 업데이트
        self.last_score = game_state.score
        self.last_lives = game_state.player_lives
        self.previous_state = game_state

        return total_reward


class GamePPOAgent:
    """실제 게임과 연동되는 PPO 에이전트 래퍼 (개선된 보상 시스템 통합)

    게임 상태를 추출하고 PPO 에이전트의 액션을 적용하는 브리지 역할을 합니다.

    ---

    게임과 PPO 에이전트 사이의 인터페이스를 제공하는 어댑터 클래스
    """

    def __init__(
        self,
        ppo_agent: PPOAgent,
        skill_level: float = 0.5,
        personality: int = 0,
        enable_learning: bool = False,
        model_path: Optional[str] = None,
        save_interval: int = 1000,
        speed_multiplier: int = 1,
        use_improved_rewards: bool = True,  # 개선된 보상 시스템 사용 여부
    ):
        """게임 PPO 에이전트 초기화

        Args:
            ppo_agent: PPO 에이전트 인스턴스
            skill_level: 플레이어 실력 수준 (0~1)
            personality: 플레이어 성향 (0: 방어적, 1: 공격적)
            enable_learning: 학습 모드 여부
            model_path: 모델 저장 경로 (학습 시에만 사용)
            save_interval: 모델 저장 간격 (스텝 단위)
            use_improved_rewards: 개선된 보상 시스템 사용 여부

        ---

        PPO 에이전트와 게임 어댑터를 초기화
        """
        self.ppo_agent = ppo_agent
        self.skill_level = skill_level
        self.personality = personality
        self.enable_learning = enable_learning
        self.model_path = model_path
        self.save_interval = save_interval
        self.speed_multiplier = speed_multiplier
        self.use_improved_rewards = use_improved_rewards

        # 개선된 환경으로 교체 (활성화된 경우)
        if use_improved_rewards:
            original_env = self.ppo_agent.env
            improved_env = ImprovedGameEnvironment(
                max_entities=original_env.max_entities,
                max_lives=original_env.max_lives,
                final_stage_num=original_env.final_stage_num,
            )
            # 🔧 배속 정보를 환경에 전달
            improved_env.speed_multiplier = speed_multiplier
            self.ppo_agent.env = improved_env

        # 게임 상태 어댑터
        self.adapter = GameStateAdapter()

        # 게임 인스턴스 참조 (나중에 설정됨)
        self.game_instance = None

        # 성능 통계
        self.step_count = 0
        self.episode_count = 0
        self.total_reward = 0.0
        self.episode_start_time = time.time()
        self.episode_start_step = 0  # 에피소드 시작 스텝 추가
        self.last_game_state = None
        self.last_action = None
        self.last_action_time = time.time()

        # PPO 관련 속성 초기화
        self.last_log_prob = None
        self.last_value = None

        # 에피소드별 상세 통계
        self.episode_rewards = []  # 각 스텝별 보상 기록
        self.episode_actions = []  # 각 스텝별 액션 기록
        self.max_score_in_episode = 0  # 에피소드 내 최고 스코어
        self.max_lives_in_episode = 0  # 에피소드 내 최대 생명 수
        self.final_stage = 1  # 에피소드 종료 시 스테이지

        # 통계 출력 간격
        self.stats_interval = 600  # 10초마다 (60 FPS 기준) - 기존 300에서 증가

        # 로깅 시스템 초기화
        self.log_dir = "logs"
        self.training_log_file = None
        self.episode_log_file = None
        self.plot_interval = 0  # 주기적 그래프 생성 비활성화 (0으로 설정)
        self.target_episodes = None  # 목표 에피소드 수 (외부에서 설정)
        self.training_complete = False  # 훈련 완료 플래그 추가
        self.setup_logging()

        # 안정적인 학습을 위한 최적화 설정
        self.fast_mode = enable_learning  # 학습 모드에서만 빠른 모드 활성화
        if self.fast_mode:
            self.stats_interval = 900  # 더 긴 간격 (15초마다) - 기존 150에서 증가

        # 실시간 메트릭 추적
        self.best_score = 0
        self.best_reward = float("-inf")
        self.best_survival_time = 0.0  # 최고 생존 시간 추가
        self.last_survival_time = 0.0  # 이전 에피소드 생존 시간 추가
        self.episode_final_survival_time = (
            0  # 🔧 에피소드 종료 직전 survival_time 저장용
        )
        self.training_start_time = time.time()

        # 시각화를 위한 통계 히스토리
        self.training_stats_history = []
        self.episode_survival_times = []
        self.episode_total_rewards = []

        # 커리큘럼 학습 하이퍼파라미터 관리
        self.base_learning_rate = None
        self.current_learning_rate = None
        if enable_learning and hasattr(ppo_agent, "optimizer"):
            # 현재 학습률 저장
            for param_group in ppo_agent.optimizer.param_groups:
                if self.base_learning_rate is None:
                    self.base_learning_rate = param_group["lr"]
                    self.current_learning_rate = param_group["lr"]
                    break

        if enable_learning:
            print(
                f"🤖 Learning Agent: {'Improved' if use_improved_rewards else 'Standard'} rewards"
            )
            if model_path:
                print(f"💾 Model saves to: {model_path}")
            if self.base_learning_rate:
                print(f"📚 Base learning rate: {self.base_learning_rate:.6f}")

    def update_learning_parameters(self):
        """커리큘럼 단계에 따른 학습 파라미터 동적 조정"""
        if not self.enable_learning or not self.use_improved_rewards:
            return

        if not hasattr(self.ppo_agent.env, "get_current_phase_info"):
            return

        phase_info = self.ppo_agent.env.get_current_phase_info()

        # 단계별 학습률 조정 (기본 조작 단계에서 높은 학습률)
        lr_multipliers = [1.5, 1.2, 1.0, 0.8]  # 기본 조작에서 더 빠른 학습
        new_lr = self.base_learning_rate * lr_multipliers[phase_info["phase"]]

        # PPO 에이전트의 학습률 업데이트
        if (
            hasattr(self.ppo_agent, "optimizer")
            and self.current_learning_rate != new_lr
        ):
            for param_group in self.ppo_agent.optimizer.param_groups:
                param_group["lr"] = new_lr

            print(
                f"📚 Learning rate updated: {self.current_learning_rate:.6f} → {new_lr:.6f} ({phase_info['name']})"
            )
            self.current_learning_rate = new_lr

    def setup_logging(self):
        """로깅 시스템 설정

        ---

        훈련 메트릭과 에피소드 데이터를 CSV 파일로 저장하는 시스템 초기화
        """
        if not self.enable_learning:
            return

        # 로그 디렉토리 생성
        os.makedirs(self.log_dir, exist_ok=True)

        # 타임스탬프로 고유한 로그 파일명 생성
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 훈련 메트릭 로그 파일
        self.training_log_file = os.path.join(
            self.log_dir, f"training_metrics_{timestamp}.csv"
        )
        with open(self.training_log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "step",
                    "episode",
                    "total_loss",
                    "policy_loss",
                    "value_loss",
                    "entropy_loss",
                    "current_reward",
                    "steps_per_sec",
                ]
            )

        # 에피소드 로그 파일
        self.episode_log_file = os.path.join(self.log_dir, f"episodes_{timestamp}.csv")
        with open(self.episode_log_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "timestamp",
                    "episode",
                    "duration_sec",
                    "steps",
                    "total_reward",
                    "avg_reward_per_step",
                    "final_score",
                    "max_score",
                    "final_stage",
                    "final_lives",
                    "positive_rewards",
                    "negative_rewards",
                    "end_reason",
                ]
            )

        print(f"Logging initialized:")
        print(f"   Training metrics: {self.training_log_file}")
        print(f"   Episode data: {self.episode_log_file}")

    def log_training_metrics(self, training_stats: Dict[str, float]):
        """훈련 메트릭을 로그 파일에 기록

        Args:
            training_stats: 훈련 통계 딕셔너리

        ---

        실시간 그래프 생성을 위한 훈련 메트릭 저장
        """
        if not self.enable_learning or not self.training_log_file:
            return

        # 통계 히스토리에 추가 (시각화용)
        self.training_stats_history.append(training_stats)

        try:
            # 파일이 존재하는지 확인하고 없으면 헤더 다시 생성
            if not os.path.exists(self.training_log_file):
                print(
                    f"⚠️ Training log file missing, recreating: {self.training_log_file}"
                )
                os.makedirs(os.path.dirname(self.training_log_file), exist_ok=True)
                with open(
                    self.training_log_file, "w", newline="", encoding="utf-8"
                ) as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            "timestamp",
                            "step",
                            "episode",
                            "total_loss",
                            "policy_loss",
                            "value_loss",
                            "entropy_loss",
                            "current_reward",
                            "steps_per_sec",
                        ]
                    )

            current_time = time.time()
            elapsed_time = current_time - self.episode_start_time
            steps_per_second = self.step_count / max(1, elapsed_time)

            with open(self.training_log_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        datetime.now().isoformat(),
                        self.step_count,
                        self.episode_count,
                        training_stats.get("total_loss", 0),
                        training_stats.get("policy_loss", 0),
                        training_stats.get("value_loss", 0),
                        training_stats.get("entropy_loss", 0),
                        self.total_reward,
                        steps_per_second,
                    ]
                )
        except Exception as e:
            print(f"⚠️ Failed to log training metrics: {e}")

    def log_episode_data(self, episode_data: Dict[str, Any]):
        """에피소드 데이터를 로그 파일에 기록

        Args:
            episode_data: 에피소드 통계 딕셔너리

        ---

        에피소드별 성과 데이터를 CSV 파일에 저장
        """
        if not self.enable_learning or not self.episode_log_file:
            return

        try:
            # 파일이 존재하는지 확인하고 없으면 헤더 다시 생성
            if not os.path.exists(self.episode_log_file):
                print(
                    f"⚠️ Episode log file missing, recreating: {self.episode_log_file}"
                )
                os.makedirs(os.path.dirname(self.episode_log_file), exist_ok=True)
                with open(
                    self.episode_log_file, "w", newline="", encoding="utf-8"
                ) as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            "timestamp",
                            "episode",
                            "duration_sec",
                            "steps",
                            "total_reward",
                            "avg_reward_per_step",
                            "final_score",
                            "max_score",
                            "final_stage",
                            "final_lives",
                            "positive_rewards",
                            "negative_rewards",
                            "end_reason",
                        ]
                    )

            with open(self.episode_log_file, "a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        datetime.now().isoformat(),
                        episode_data["episode"],
                        episode_data["duration"],
                        episode_data["steps"],
                        episode_data["total_reward"],
                        episode_data["avg_reward_per_step"],
                        episode_data["final_score"],
                        episode_data["max_score"],
                        episode_data["final_stage"],
                        episode_data["final_lives"],
                        episode_data["positive_rewards"],
                        episode_data["negative_rewards"],
                        episode_data["end_reason"],
                    ]
                )
        except Exception as e:
            print(f"⚠️ Failed to log episode data: {e}")

    def generate_training_plots(self):
        """훈련 진행도 그래프 생성 (matplotlib 기반)

        ---

        에피소드 종료 시점에 현재까지의 훈련 진행도를 시각화
        """
        if not self.enable_learning:
            return

        try:
            import matplotlib.pyplot as plt
            import matplotlib
            import numpy as np

            # 폰트 경고 억제
            matplotlib.rcParams["font.family"] = ["DejaVu Sans", "sans-serif"]
            import warnings

            warnings.filterwarnings("ignore", category=UserWarning, module="matplotlib")

            if len(self.episode_total_rewards) < 2:
                print("Not enough data for plotting (need at least 2 episodes)")
                return

            # 플롯 디렉토리 생성
            plot_dir = "src/plots"
            os.makedirs(plot_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 그래프 생성
            plt.figure(figsize=(15, 10))

            # 1. 에피소드 보상 그래프
            plt.subplot(2, 3, 1)
            episodes = range(1, len(self.episode_total_rewards) + 1)
            plt.plot(
                episodes,
                self.episode_total_rewards,
                alpha=0.7,
                color="blue",
                linewidth=1,
            )
            if len(self.episode_total_rewards) >= 10:
                # 이동 평균
                window = min(10, len(self.episode_total_rewards))
                moving_avg = []
                for i in range(len(self.episode_total_rewards)):
                    start_idx = max(0, i - window + 1)
                    moving_avg.append(
                        np.mean(self.episode_total_rewards[start_idx : i + 1])
                    )
                plt.plot(
                    episodes,
                    moving_avg,
                    color="red",
                    linewidth=2,
                    label=f"Moving Avg ({window})",
                )
                plt.legend()
            plt.title("Episode Total Rewards")
            plt.xlabel("Episode")
            plt.ylabel("Total Reward")
            plt.grid(True, alpha=0.3)

            # 2. 생존 시간 그래프
            plt.subplot(2, 3, 2)
            if self.episode_survival_times:
                plt.plot(
                    episodes,
                    self.episode_survival_times,
                    alpha=0.7,
                    color="green",
                    linewidth=1,
                )
                if len(self.episode_survival_times) >= 10:
                    window = min(10, len(self.episode_survival_times))
                    moving_avg = []
                    for i in range(len(self.episode_survival_times)):
                        start_idx = max(0, i - window + 1)
                        moving_avg.append(
                            np.mean(self.episode_survival_times[start_idx : i + 1])
                        )
                    plt.plot(
                        episodes,
                        moving_avg,
                        color="orange",
                        linewidth=2,
                        label=f"Moving Avg ({window})",
                    )
                    plt.legend()
                plt.title("Survival Time per Episode")
                plt.xlabel("Episode")
                plt.ylabel("Survival Time (seconds)")
                plt.grid(True, alpha=0.3)

            # 3. 학습 손실 (훈련 통계가 있는 경우)
            if self.training_stats_history:
                plt.subplot(2, 3, 3)
                policy_losses = [
                    stats.get("policy_loss", 0) for stats in self.training_stats_history
                ]
                value_losses = [
                    stats.get("value_loss", 0) for stats in self.training_stats_history
                ]
                training_steps = range(1, len(policy_losses) + 1)

                plt.plot(
                    training_steps,
                    policy_losses,
                    label="Policy Loss",
                    alpha=0.7,
                    linewidth=1,
                )
                plt.plot(
                    training_steps,
                    value_losses,
                    label="Value Loss",
                    alpha=0.7,
                    linewidth=1,
                )
                plt.title("Training Losses")
                plt.xlabel("Training Update")
                plt.ylabel("Loss")
                plt.legend()
                plt.grid(True, alpha=0.3)

            # 4. 보상 분포 히스토그램
            plt.subplot(2, 3, 4)
            if self.episode_total_rewards:
                plt.hist(
                    self.episode_total_rewards,
                    bins=min(20, len(self.episode_total_rewards)),
                    alpha=0.7,
                    color="skyblue",
                )
                plt.title("Reward Distribution")
                plt.xlabel("Total Reward")
                plt.ylabel("Frequency")
                plt.grid(True, alpha=0.3)

            # 5. 성능 트렌드 (최근 성과)
            plt.subplot(2, 3, 5)
            if len(self.episode_total_rewards) >= 20:
                recent_rewards = self.episode_total_rewards[-20:]
                recent_episodes = range(
                    len(self.episode_total_rewards) - 19,
                    len(self.episode_total_rewards) + 1,
                )
                plt.plot(
                    recent_episodes,
                    recent_rewards,
                    "o-",
                    alpha=0.8,
                    color="purple",
                    linewidth=2,
                )
                plt.title("Recent Performance (Last 20 Episodes)")
                plt.xlabel("Episode")
                plt.ylabel("Total Reward")
                plt.grid(True, alpha=0.3)

            # 6. 성능 요약 텍스트
            plt.subplot(2, 3, 6)
            plt.text(
                0.1,
                0.9,
                f"Training Summary",
                fontsize=14,
                fontweight="bold",
                transform=plt.gca().transAxes,
            )
            plt.text(
                0.1,
                0.8,
                f"Episodes: {len(self.episode_total_rewards)}",
                fontsize=12,
                transform=plt.gca().transAxes,
            )
            plt.text(
                0.1,
                0.7,
                f"Best Survival: {self.best_survival_time:.1f}s",
                fontsize=12,
                transform=plt.gca().transAxes,
            )

            if self.episode_total_rewards:
                plt.text(
                    0.1,
                    0.6,
                    f"Best Reward: {max(self.episode_total_rewards):+.1f}",
                    fontsize=12,
                    transform=plt.gca().transAxes,
                )
                plt.text(
                    0.1,
                    0.5,
                    f"Avg Reward: {np.mean(self.episode_total_rewards):+.1f}",
                    fontsize=12,
                    transform=plt.gca().transAxes,
                )

                recent_10 = (
                    self.episode_total_rewards[-10:]
                    if len(self.episode_total_rewards) >= 10
                    else self.episode_total_rewards
                )
                plt.text(
                    0.1,
                    0.4,
                    f"Recent 10 Avg: {np.mean(recent_10):+.1f}",
                    fontsize=12,
                    transform=plt.gca().transAxes,
                )

            plt.text(
                0.1,
                0.3,
                f"Best Score: {self.best_score:,}",
                fontsize=12,
                transform=plt.gca().transAxes,
            )

            # 커리큘럼 학습 정보 추가
            curriculum_info = "Standard"
            learning_rate_info = ""
            skill_info = ""

            if self.use_improved_rewards and hasattr(
                self.ppo_agent.env, "get_current_phase_info"
            ):
                phase_info = self.ppo_agent.env.get_current_phase_info()
                curriculum_info = f"Curriculum: {phase_info['name']}"
                if self.current_learning_rate:
                    learning_rate_info = f"LR: {self.current_learning_rate:.6f}"

                # 스킬 정보 추가
                skill_level = self.skill_level
                if skill_level < 0.3:
                    skill_info = (
                        f"Agent: BEGINNER (Skill {skill_level:.1f}) - Target: 10s"
                    )
                elif skill_level < 0.7:
                    skill_info = (
                        f"Agent: INTERMEDIATE (Skill {skill_level:.1f}) - Target: 20s"
                    )
                else:
                    skill_info = (
                        f"Agent: EXPERT (Skill {skill_level:.1f}) - Target: 30s"
                    )

            plt.text(
                0.1,
                0.2,
                f"Reward System: {'Improved' if self.use_improved_rewards else 'Standard'}",
                fontsize=12,
                transform=plt.gca().transAxes,
            )
            plt.text(
                0.1,
                0.15,
                curriculum_info,
                fontsize=10,
                transform=plt.gca().transAxes,
            )
            if learning_rate_info:
                plt.text(
                    0.1,
                    0.1,
                    learning_rate_info,
                    fontsize=10,
                    transform=plt.gca().transAxes,
                )
            if skill_info:
                plt.text(
                    0.1,
                    0.05,
                    skill_info,
                    fontsize=9,
                    transform=plt.gca().transAxes,
                )
                plt.text(
                    0.1,
                    0.0,
                    f"Training Steps: {self.step_count:,}",
                    fontsize=10,
                    transform=plt.gca().transAxes,
                )
            else:
                plt.text(
                    0.1,
                    0.05,
                    f"Training Steps: {self.step_count:,}",
                    fontsize=10,
                    transform=plt.gca().transAxes,
                )

            plt.axis("off")

            plt.tight_layout()

            # 저장
            plot_path = os.path.join(plot_dir, f"training_progress_{timestamp}.png")
            plt.savefig(plot_path, dpi=150, bbox_inches="tight")

            # 최신 버전으로도 저장
            latest_path = os.path.join(plot_dir, "latest_training_progress.png")
            plt.savefig(latest_path, dpi=150, bbox_inches="tight")

            print(f"Training plots saved: {plot_path}")
            plt.close()

        except ImportError:
            print("⚠️ matplotlib not available - using fallback plot generator")
            try:
                # plot_training_progress 모듈 사용 (기존 방식)
                from plot_training_progress import TrainingPlotter

                plotter = TrainingPlotter(log_dir=self.log_dir, output_dir="plots")
                success = plotter.generate_all_plots()
                if success:
                    print(f"Training plots generated in plots/ directory")
            except ImportError:
                print("⚠️ plot_training_progress.py not found - plots not generated")
        except Exception as e:
            print(f"⚠️ Failed to generate plots: {e}")
            print(f"Error details: {traceback.format_exc()}")

    def set_game_instance(self, game_instance):
        """게임 인스턴스 설정

        Args:
            game_instance: App 인스턴스

        ---

        게임과의 연결을 설정하여 실제 게임 상태에 접근 가능하게 함
        """
        self.game_instance = game_instance

    def connect_game(self, game_instance):
        """게임과 연결 설정 (App.py에서 호출되는 메서드)

        Args:
            game_instance: 게임 인스턴스

        ---

        App 클래스에서 에이전트 초기화 시 호출되는 메서드
        """
        self.set_game_instance(game_instance)

        # 게임 종료 시그널 처리를 위한 핸들러 등록 (가능한 경우)
        if hasattr(game_instance, "on_exit"):
            original_exit = game_instance.on_exit

            def exit_with_plots():
                print("🔚 Game is closing - generating final plots...")
                self.generate_final_plots("Game closed by user")
                if original_exit:
                    original_exit()

            game_instance.on_exit = exit_with_plots

    def select_action(self) -> int:
        """게임에서 호출되는 액션 선택 메서드 (스킬 기반 성능 차별화)

        Returns:
            선택된 액션 ID (0~8)

        ---

        스킬 레벨에 따라 실제 플레이 성능을 차별화:
        - 고실력자 (0.7-1.0): 정확한 액션, 낮은 실수율, 빠른 반응
        - 중급자 (0.3-0.7): 보통 정확도, 보통 실수율
        - 초보자 (0.0-0.3): 부정확한 액션, 높은 실수율, 느린 반응
        """
        if self.training_complete:
            return 4  # Return a neutral action if training is done

        try:
            game_state = self._extract_current_game_state()
            if game_state is None:
                return 4  # Return a neutral action if game state is not available

            # 목표 에피소드 달성 체크 (더 자주 확인)
            if self.target_episodes and self.episode_count >= self.target_episodes:
                if not self.training_complete:
                    print(f"\n🎯 Target episodes ({self.target_episodes}) reached!")
                    self.training_complete = True
                    self.generate_final_plots(
                        f"Target episodes ({self.target_episodes}) completed"
                    )

                    # 게임 종료 시도
                    print(f"🔚 Automatically terminating game...")
                    if self.game_instance and hasattr(self.game_instance, "quit"):
                        self.game_instance.quit()
                    elif hasattr(self.game_instance, "running"):
                        self.game_instance.running = False

                    try:
                        px.quit()
                    except:
                        pass

                    import sys

                    print("✅ Training completed and game terminated!")
                    sys.exit(0)
                return 4

            # 에피소드 종료 감지 (학습/비학습 모드 공통)
            done = self._is_episode_done(game_state)

            # 🎯 스킬 기반 성능 차별화 구현
            skill = game_state.skill_level

            # 1. 기본 액션 선택 (PPO 에이전트)
            if self.enable_learning:
                # 커리큘럼 학습에 따른 탐험 전략 조정
                exploration_bonus = 0.0
                if self.use_improved_rewards and hasattr(
                    self.ppo_agent.env, "get_current_phase_info"
                ):
                    phase_info = self.ppo_agent.env.get_current_phase_info()

                    # 단계별 탐험 확률 조정
                    exploration_rates = [
                        0.3,
                        0.2,
                        0.15,
                        0.1,
                    ]  # 기본 조작 단계에서 높은 탐험
                    exploration_bonus = exploration_rates[phase_info["phase"]]

                    # 기본 조작 단계에서 랜덤 액션 확률 증가
                    if phase_info["phase"] == 0:
                        import random

                        if random.random() < 0.15:  # 15% 확률로 랜덤 액션
                            action = random.randint(0, 8)
                            self.last_game_state = game_state
                            self.last_action = action
                            self.step_count += 1
                            return action

                action, log_prob, value = self.ppo_agent.select_action_with_exploration(
                    game_state
                )

                # 추가 탐험 보너스 적용
                if exploration_bonus > 0.0:
                    import random

                    if random.random() < exploration_bonus:
                        # 현재 액션과 다른 액션 선택
                        available_actions = [i for i in range(9) if i != action]
                        if available_actions:
                            action = random.choice(available_actions)

                if self.last_game_state is not None and self.last_action is not None:
                    # 개선된 보상 시스템 사용
                    if self.use_improved_rewards and hasattr(
                        self.ppo_agent.env, "calculate_reward_improved"
                    ):
                        reward = self.ppo_agent.env.calculate_reward_improved(
                            game_state, self.last_action
                        )
                    else:
                        reward = self.ppo_agent.env.calculate_reward(
                            game_state, self.last_action
                        )

                    self.ppo_agent.store_experience(
                        self.last_game_state,
                        self.last_action,
                        reward,
                        self.last_log_prob,
                        self.last_value,
                        done,
                    )
                    self.total_reward += reward
                    self.episode_rewards.append(reward)
                    self.episode_actions.append(self.last_action)

                    if done:
                        self._handle_episode_end()

                        # 목표 달성 즉시 체크
                        if (
                            self.target_episodes
                            and self.episode_count >= self.target_episodes
                        ):
                            self.training_complete = True
                            return 4  # 즉시 중립 액션 반환

                self.last_log_prob = log_prob
                self.last_value = value

                # 버퍼가 가득 차면 학습을 수행합니다.
                if self.ppo_agent.is_buffer_full():
                    print("🧠 Buffer is full, starting training...")
                    training_stats = self.ppo_agent.train()
                    if training_stats:
                        self.log_training_metrics(training_stats)
            else:
                # 비학습 모드에서도 에피소드 관리
                action = self.ppo_agent.select_action(game_state)

                # 비학습 모드에서도 에피소드 종료 처리
                if self.last_game_state is not None and done:
                    self._handle_episode_end()

                    # 목표 달성 즉시 체크
                    if (
                        self.target_episodes
                        and self.episode_count >= self.target_episodes
                    ):
                        self.training_complete = True
                        return 4

            # 🚀 스킬 기반 실제 성능 차별화
            final_action = self._apply_skill_based_performance(
                action, skill, game_state
            )

            self.last_game_state = game_state
            self.last_action = final_action  # 실제 적용된 액션 저장
            self.step_count += 1

            # 모델 저장 로직 추가
            if (
                self.enable_learning
                and self.model_path
                and self.step_count % self.save_interval == 0
            ):
                self.ppo_agent.save_model(self.model_path)
                print(f"💾 Model saved to {self.model_path} at step {self.step_count}")

            return final_action
        except Exception as e:
            import sys

            print(
                f"Error in select_action: {e}\n{traceback.format_exc()}",
                file=sys.stderr,
            )
            return 4  # Return a neutral action in case of error

    def _apply_skill_based_performance(
        self, base_action: int, skill: float, game_state
    ) -> int:
        """스킬 레벨에 따른 실제 성능 차별화 적용 (강화된 버전)

        Args:
            base_action: PPO 에이전트가 선택한 기본 액션
            skill: 스킬 레벨 (0.0-1.0)
            game_state: 현재 게임 상태

        Returns:
            스킬에 따라 조정된 최종 액션

        ---

        스킬 레벨에 따른 종합적인 능력 차별화:
        - 고실력자: 정확한 판단, 빠른 반응, 전략적 사고
        - 저실력자: 부정확한 판단, 느린 반응, 단순한 사고
        """
        import random
        import time

        # 🎯 스킬별 성능 파라미터 설정 (강화된 버전)
        if skill < 0.3:  # 초보자 (0.0-0.3)
            accuracy_rate = 0.5  # 50% 정확도 (더 낮춤)
            mistake_rate = 0.35  # 35% 실수율 (더 높임)
            reaction_delay = 0.4  # 40% 반응 지연 (더 높임)
            random_action_rate = 0.2  # 20% 완전 랜덤 액션 (더 높임)
            panic_threshold = 2  # 적 2마리만 있어도 패닉
            strategic_thinking = 0.1  # 10% 전략적 사고
        elif skill < 0.7:  # 중급자 (0.3-0.7)
            accuracy_rate = 0.75
            mistake_rate = 0.15
            reaction_delay = 0.2
            random_action_rate = 0.1
            panic_threshold = 4
            strategic_thinking = 0.3
        else:  # 고급자 (0.7-1.0)
            accuracy_rate = 0.95  # 95% 정확도 (더 높임)
            mistake_rate = 0.02  # 2% 실수율 (더 낮춤)
            reaction_delay = 0.03  # 3% 반응 지연 (더 낮춤)
            random_action_rate = 0.01  # 1% 완전 랜덤 액션 (더 낮춤)
            panic_threshold = 8  # 적 8마리까지 침착
            strategic_thinking = 0.8  # 80% 전략적 사고

        # 🎲 1. 완전 랜덤 액션 (혼란 상태)
        if random.random() < random_action_rate:
            return random.randint(0, 8)

        # ⏰ 2. 반응 지연 시뮬레이션
        if random.random() < reaction_delay:
            if hasattr(self, "_delayed_action_cache"):
                return self._delayed_action_cache
            else:
                self._delayed_action_cache = base_action
                return base_action
        else:
            self._delayed_action_cache = base_action

        # 😰 3. 패닉 상태 시뮬레이션 (저숙련자)
        if skill < 0.7:
            nearby_enemies = sum(
                1
                for entity in game_state.entities
                if entity.entity_type.name.startswith("ENEMY")
                and entity.distance_to_player < 40
            )

            if nearby_enemies >= panic_threshold:
                # 패닉 상태에서는 더 많은 실수
                if random.random() < 0.6:  # 60% 확률로 패닉 액션
                    panic_actions = [
                        4,
                        4,
                        4,
                        0,
                        1,
                        2,
                        3,
                        5,
                        6,
                        7,
                    ]  # 정지 액션 많이 포함
                    return random.choice(panic_actions)

        # 🎯 4. 액션 정확도 적용
        if random.random() > accuracy_rate:
            # 실수 유형 결정
            mistake_type = random.random()

            if mistake_type < 0.4:  # 40%: 잘못된 방향키
                if base_action in [0, 1, 2, 3, 5, 6, 7]:  # 이동 액션인 경우
                    movement_actions = [0, 1, 2, 3, 5, 6, 7]
                    return random.choice(movement_actions)

            elif mistake_type < 0.7:  # 30%: 입력 누락 (정지)
                return 4  # STAY 액션

            else:  # 30%: 의도하지 않은 공격
                if base_action != 8:
                    return 8  # FIRE 액션

        # 💫 5. 전략적 사고 능력 (고급자 전용)
        if skill >= 0.7 and random.random() < strategic_thinking:
            # 고급 상황 분석
            nearby_enemies = sum(
                1
                for entity in game_state.entities
                if entity.entity_type.name.startswith("ENEMY")
                and entity.distance_to_player < 30
            )

            nearby_shots = sum(
                1
                for entity in game_state.entities
                if entity.entity_type.name == "ENEMY_SHOT"
                and entity.distance_to_player < 20
            )

            # 전략적 액션 선택
            danger_level = nearby_enemies + nearby_shots * 2

            if danger_level > 5:  # 위험 상황
                # 고급자는 회피 우선
                if base_action == 8 and random.random() < 0.4:
                    evasive_actions = [0, 1, 2, 3, 5, 6, 7]
                    return random.choice(evasive_actions)

                # 정지 금지 (위험할 때)
                if base_action == 4:
                    evasive_actions = [0, 1, 2, 3, 5, 6, 7]
                    return random.choice(evasive_actions)

            elif danger_level < 2:  # 안전 상황
                # 고급자는 공격적 플레이
                if base_action in [0, 1, 2, 3, 5, 6, 7] and random.random() < 0.3:
                    return 8  # 공격 액션으로 변경

        # 🧠 6. 신경망 출력 노이즈 추가 (스킬 기반)
        if skill < 0.5:  # 저숙련자는 더 불안정한 출력
            noise_level = (0.5 - skill) * 0.8  # 스킬이 낮을수록 높은 노이즈
            if random.random() < noise_level:
                # 인접한 액션으로 변경 (신경망 출력이 불안정한 것처럼)
                adjacent_actions = {
                    0: [1, 3, 4],  # 좌상 -> 상, 좌, 중앙
                    1: [0, 2, 4],  # 상 -> 좌상, 우상, 중앙
                    2: [1, 5, 4],  # 우상 -> 상, 우, 중앙
                    3: [0, 6, 4],  # 좌 -> 좌상, 좌하, 중앙
                    4: [0, 1, 2, 3, 5, 6, 7],  # 중앙 -> 모든 방향
                    5: [2, 8, 4],  # 우 -> 우상, 우하, 중앙
                    6: [3, 7, 4],  # 좌하 -> 좌, 하, 중앙
                    7: [6, 8, 4],  # 하 -> 좌하, 우하, 중앙
                    8: [5, 7, 4],  # 우하 -> 우, 하, 중앙
                }

                if base_action in adjacent_actions:
                    return random.choice(adjacent_actions[base_action])

        # 기본 액션 반환 (모든 필터를 통과한 경우)
        return base_action

    def _extract_current_game_state(self):
        """현재 게임 상태를 추출하여 GameState 객체로 변환

        Returns:
            GameState: 현재 게임 상태

        ---

        게임 인스턴스에서 필요한 정보를 추출하여 강화학습에 사용할 수 있는 형태로 변환
        """
        if not self.game_instance:
            return self._create_dummy_game_state()

        try:
            # game_adapter를 통해 게임 상태 추출
            from rl.game_adapter import GameStateAdapter

            adapter = GameStateAdapter()
            game_state = adapter.extract_game_state(
                self.game_instance, self.skill_level, self.personality
            )

            # 🔍 디버깅: 게임 상태 변화 추적 (에피소드 종료 관련)
            if self.game_instance and hasattr(self.game_instance, "game"):
                game = self.game_instance.game
                if hasattr(game, "state") and hasattr(game.state, "state"):
                    current_state = game.state.state
                    if hasattr(current_state, "name"):
                        state_name = current_state.name

                        # 게임 상태가 변경되었을 때만 로그 출력
                        if (
                            not hasattr(self, "_last_game_state_name")
                            or self._last_game_state_name != state_name
                        ):
                            if state_name in [
                                "PLAYER_DEAD",
                                "GAME_OVER",
                                "PLAY",
                                "PLAYER_SPAWNED",
                            ]:
                                lives = (
                                    getattr(game.game_vars, "lives", "N/A")
                                    if hasattr(game, "game_vars")
                                    else "N/A"
                                )
                                print(
                                    f"🎮 Game State Change: {self._last_game_state_name if hasattr(self, '_last_game_state_name') else 'UNKNOWN'} → {state_name} (Lives: {lives})"
                                )
                            self._last_game_state_name = state_name

            return game_state
        except Exception as e:
            print(f"⚠️ Error extracting game state: {e}")
            return self._create_dummy_game_state()

    def _create_dummy_game_state(self):
        """더미 게임 상태 생성

        Returns:
            기본 GameState 인스턴스

        ---

        게임 인스턴스에 접근할 수 없을 때 사용하는 대체 상태
        """
        from rl.environment import GameState, EntityData

        # 기본 게임 상태 생성
        entities = [
            EntityData(EntityType.PLAYER, 100, 100, 8, 8, 0),
        ]

        # 실제 게임 시간 계산 (속도 배수 모드 고려)
        actual_game_time = self.step_count
        if self.game_instance and hasattr(self.game_instance, "game"):
            game = self.game_instance.game
            if hasattr(game, "state") and hasattr(game.state, "state_time"):
                actual_game_time = game.state.state_time
                # 🔍 디버깅: 생존 시간 계산 확인
                if self.episode_count % 50 == 0:  # 50 에피소드마다 출력
                    print(
                        f"🔍 Survival time debug: step_count={self.step_count}, game.state.state_time={game.state.state_time}, actual_game_time={actual_game_time}"
                    )
                    print(
                        f"   survival_seconds = {self._convert_survival_time_to_seconds(actual_game_time):.2f}s (speed: {self.speed_multiplier}x)"
                    )

        return GameState(
            entities=entities,
            skill_level=self.skill_level,
            personality=self.personality,
            player_hp=2,  # 체력 (10에서 2로 변경)
            player_lives=1,  # 기본 목숨 수 (3에서 1로 변경)
            score=self.step_count * 10,  # 임시 점수
            survival_time=actual_game_time,  # 🔧 수정: 실제 게임 시간 사용
            kills=self.step_count // 100,
            current_stage=1,  # 기본 스테이지
            game_cleared=False,  # 기본값
        )

    def _is_episode_done(self, game_state) -> bool:
        """에피소드 종료 여부 확인

        Args:
            game_state: 현재 게임 상태

        Returns:
            에피소드 종료 여부

        ---

        플레이어 사망이나 게임 종료 조건을 확인
        """
        episode_length = self.step_count - self.episode_start_step
        # 🔧 수정: 실제 게임 시간 사용 (배속 모드 고려)
        survival_seconds = self._convert_survival_time_to_seconds(
            game_state.survival_time
        )

        # 🔧 에피소드 종료 직전에 survival_time 저장 (게임 리셋 전에)
        self.episode_final_survival_time = game_state.survival_time

        # 🚨 최우선: 게임 인스턴스에서 직접 게임 상태 확인 (플레이어 사망 즉시 감지)
        if self.game_instance and hasattr(self.game_instance, "game"):
            game = self.game_instance.game

            # 게임 상태 우선 확인 - 플레이어 사망 또는 게임 오버 즉시 종료
            if hasattr(game, "state") and hasattr(game.state, "state"):
                current_state = game.state.state
                if hasattr(current_state, "name"):
                    state_name = current_state.name
                    if state_name in [
                        "PLAYER_DEAD",
                        "GAME_OVER",
                        "GAMEOVER",
                        "GAME_END",
                    ]:
                        # 🔧 게임 상태에서 survival_time 직접 저장
                        if hasattr(game.state, "state_time"):
                            self.episode_final_survival_time = game.state.state_time

                        print(
                            f"🏁 Episode done: Game state is {state_name} (immediate termination)"
                        )
                        return True

            # 게임 변수에서 목숨 확인 (2차 확인)
            if hasattr(game, "game_vars"):
                game_vars = game.game_vars
                lives_count = getattr(game_vars, "lives", None)
                if lives_count is not None and lives_count <= 0:
                    print(f"🏁 Episode done: Game vars lives = {lives_count}")
                    return True

                # 스테이지 완주 확인 (최종 스테이지 도달)
                if hasattr(game_vars, "stage_num"):
                    current_stage = getattr(game_vars, "stage_num", 1)
                    if current_stage >= 8:  # 최종 스테이지 (게임에 따라 조정)
                        print(f"🏁 Episode done: Final stage {current_stage} reached")
                        return True

        # GameState 객체를 통한 종료 조건 확인 (3차 확인)
        if game_state.player_lives <= 0:
            print(
                f"🏁 Episode done: Player lives exhausted ({game_state.player_lives})"
            )
            return True

        # 게임 클리어 시 에피소드 종료 (모든 스테이지 완주)
        if game_state.game_cleared:
            print(f"🏁 Episode done: Game cleared!")
            return True

        # 🎯 커리큘럼 학습 최소 생존 시간 조건 (대폭 완화 - 학습 방해 최소화)
        if self.use_improved_rewards and hasattr(
            self.ppo_agent.env, "get_current_phase_info"
        ):
            phase_info = self.ppo_agent.env.get_current_phase_info()

            # 🛡️ 매우 제한적인 최소 생존 시간 (초급 단계에서만 적용)
            min_survival_times = [0.2, 0.0, 0.0, 0.0]  # 첫 번째 단계에서만 0.2초 보장
            min_survival = min_survival_times[phase_info["phase"]]

            # 최소 생존 시간 조건을 매우 완화하여 플레이어 사망 시 즉시 종료 우선
            if (
                survival_seconds < min_survival
                and episode_length > 12  # 12프레임 (0.2초) 이상만 체크
                and phase_info["phase"] == 0  # 첫 번째 단계에서만 적용
            ):
                # 매우 짧은 경우에만 강제 연장 (거의 사용하지 않음)
                return False

        # 매우 긴 에피소드 강제 종료 (무한 루프 방지)
        max_episode_length = 8000 if not self.fast_mode else 5000

        if episode_length > max_episode_length:
            print(
                f"🏁 Episode done: Maximum episode length reached ({episode_length} steps)"
            )
            return True

        # 기존 조건: 매우 짧은 생존 시간 연속 발생 (커리큘럼 학습 시 비활성화)
        if not (
            self.use_improved_rewards
            and hasattr(self.ppo_agent.env, "get_current_phase_info")
        ):
            # 일반 학습 모드에서만 적용
            if (
                survival_seconds < 0.5 and episode_length > 30
            ):  # 0.5초 미만이고 30스텝 이상
                print(
                    f"🏁 Episode done: Very short survival detected ({survival_seconds:.2f}s)"
                )
                return True

        return False

    def _handle_episode_end(self):
        """에피소드 종료 처리

        ---

        에피소드 통계 출력 및 학습 수행
        """
        self.episode_count += 1
        episode_length = self.step_count - self.episode_start_step
        episode_duration = time.time() - self.episode_start_time

        # 커리큘럼 학습 단계 업데이트 (개선된 보상 시스템 사용 시)
        if self.use_improved_rewards and hasattr(
            self.ppo_agent.env, "update_curriculum_phase"
        ):
            self.ppo_agent.env.update_curriculum_phase(self.episode_count)

            # 학습 파라미터 동적 조정
            self.update_learning_parameters()

            # 현재 단계 정보 출력
            if hasattr(self.ppo_agent.env, "get_current_phase_info"):
                phase_info = self.ppo_agent.env.get_current_phase_info()
                if self.episode_count % 20 == 0:  # 20 에피소드마다 출력
                    print(
                        f"\n🎓 Curriculum Status: {phase_info['name']} ({phase_info['episode_in_phase']}/{phase_info['total_in_phase']})"
                    )
                    if phase_info["invulnerability"]:
                        print(f"   🛡️ Training wheels: Reduced damage penalty active")
                    if self.current_learning_rate:
                        print(
                            f"   📚 Current learning rate: {self.current_learning_rate:.6f}"
                        )

        # 현재 게임 상태에서 최종 정보 추출
        final_score = 0
        final_lives = 0
        final_stage = 1
        episode_end_reason = "Unknown"

        if self.game_instance and hasattr(self.game_instance, "game"):
            game = self.game_instance.game

            # 게임 변수에서 정보 추출
            if hasattr(game, "game_vars"):
                final_score = getattr(game.game_vars, "score", 0)
                final_lives = getattr(game.game_vars, "lives", 0)
                final_stage = getattr(game.game_vars, "stage_num", 1)

            # 게임 상태에서 종료 이유 판단
            if hasattr(game, "state") and hasattr(game.state, "state"):
                from states.game_state.game_state_stage import State

                if hasattr(game.state, "state"):
                    game_state = game.state.state
                    if game_state.name == "GAME_OVER":
                        episode_end_reason = "Game Over - All Lives Lost"
                    elif game_state.name == "STAGE_CLEAR":
                        if (
                            final_stage >= 8
                        ):  # 최종 스테이지 클리어 (게임에 따라 조정 필요)
                            episode_end_reason = "Game Complete - All Stages Cleared!"
                        else:
                            episode_end_reason = f"Stage {final_stage} Cleared"
                    elif game_state.name == "PLAYER_DEAD":
                        if final_lives <= 0:
                            episode_end_reason = "Player Death - Last Life Lost"
                        else:
                            episode_end_reason = (
                                f"Player Death - {final_lives} Lives Remaining"
                            )
                    else:
                        episode_end_reason = f"Game State: {game_state.name}"

        # 최종 게임 상태 기반으로도 종료 이유 판단
        if episode_end_reason == "Unknown":
            current_game_state = self._extract_current_game_state()
            if current_game_state:
                if current_game_state.player_lives <= 0:
                    episode_end_reason = "No Lives Remaining"
                elif current_game_state.game_cleared:
                    episode_end_reason = "All Stages Completed"
                else:
                    episode_end_reason = "Episode Terminated"

        # 보상 통계 계산
        total_positive_reward = sum(r for r in self.episode_rewards if r > 0)
        total_negative_reward = sum(r for r in self.episode_rewards if r < 0)
        avg_reward_per_step = self.total_reward / max(1, episode_length)

        # 액션 분포 계산
        action_distribution = {}
        fire_actions = 0
        movement_actions = 0
        for action in self.episode_actions:
            action_distribution[action] = action_distribution.get(action, 0) + 1
            if action == 8:  # FIRE action
                fire_actions += 1
            elif action in [0, 1, 2, 3, 5, 6, 7]:  # Movement actions
                movement_actions += 1

        # 전투 및 플레이 스타일 분석
        total_actions = len(self.episode_actions)
        fire_ratio = (fire_actions / max(1, total_actions)) * 100
        movement_ratio = (movement_actions / max(1, total_actions)) * 100

        # 액션 분포 출력 (간소화) - 커리큘럼 단계에 따라 조정
        show_detailed_actions = False
        if self.use_improved_rewards and hasattr(
            self.ppo_agent.env, "get_current_phase_info"
        ):
            phase_info = self.ppo_agent.env.get_current_phase_info()
            # 기본 조작 단계에서는 더 자주 출력
            show_detailed_actions = (
                phase_info["phase"] == 0 and self.episode_count % 3 == 0
            ) or (self.episode_count % 5 == 0)
        else:
            show_detailed_actions = self.episode_count % 5 == 0

        if show_detailed_actions:
            print(f"Action Distribution:")
            action_names = [
                "UL",
                "UP",
                "UR",
                "LEFT",
                "STAY",
                "RIGHT",
                "DL",
                "DOWN",
                "DR",
                "FIRE",
            ]
            for action_id in sorted(action_distribution.keys()):
                if action_id < len(action_names):
                    action_name = action_names[action_id]
                    count = action_distribution[action_id]
                    percentage = (count / max(1, episode_length)) * 100
                    if action_id == 8:  # Fire action - highlight
                        print(
                            f"   {action_name} (#{action_id}): {count} times ({percentage:.1f}%) *"
                        )
                    else:
                        print(
                            f"   {action_name} (#{action_id}): {count} times ({percentage:.1f}%)"
                        )

        # 최고 기록 업데이트
        if self.total_reward > self.best_reward:
            self.best_reward = self.total_reward
        if final_score > self.best_score:
            self.best_score = final_score

        # 생존 시간 계산 및 기록 업데이트 (실제 플레이 시간)
        # 🔧 우선: 에피소드 종료 직전에 저장된 survival_time 사용
        if (
            hasattr(self, "episode_final_survival_time")
            and self.episode_final_survival_time > 0
        ):
            survival_seconds = self._convert_survival_time_to_seconds(
                self.episode_final_survival_time
            )
            print(
                f"🔧 Using saved survival time: {self.episode_final_survival_time} frames = {survival_seconds:.2f}s"
            )
        elif self.game_instance and hasattr(self.game_instance, "game"):
            try:
                # game_adapter를 통해 실제 게임 상태 추출
                from rl.game_adapter import GameStateAdapter

                adapter = GameStateAdapter()
                real_game_state = adapter.extract_game_state(
                    self.game_instance, self.skill_level, self.personality
                )
                if real_game_state:
                    survival_seconds = self._convert_survival_time_to_seconds(
                        real_game_state.survival_time
                    )
                    # 🔍 디버깅: 실제 생존 시간 확인
                    if self.episode_count % 50 == 0:  # 50 에피소드마다 출력
                        print(
                            f"🔍 Real survival time: {real_game_state.survival_time} frames = {survival_seconds:.2f}s (speed: {self.speed_multiplier}x)"
                        )
                else:
                    # 🚨 GameStateAdapter가 None을 반환한 경우
                    print(
                        f"⚠️ GameStateAdapter returned None - using current game state"
                    )
                    current_game_state = self._extract_current_game_state()
                    survival_seconds = self._convert_survival_time_to_seconds(
                        current_game_state.survival_time
                    )
            except Exception as e:
                # 🚨 자세한 오류 정보 출력
                print(f"⚠️ Error extracting real game state: {e}")
                print(f"   Using current game state as fallback")
                current_game_state = self._extract_current_game_state()
                survival_seconds = self._convert_survival_time_to_seconds(
                    current_game_state.survival_time
                )
        else:
            # 🚨 게임 인스턴스가 없는 경우
            print(f"⚠️ No game instance available - using current game state")
            current_game_state = self._extract_current_game_state()
            survival_seconds = self._convert_survival_time_to_seconds(
                current_game_state.survival_time
            )

        if survival_seconds > self.best_survival_time:
            self.best_survival_time = survival_seconds

        # 시각화용 데이터 저장
        self.episode_survival_times.append(survival_seconds)
        self.episode_total_rewards.append(self.total_reward)

        # 상세한 에피소드 요약 출력
        episode_header = f"\n🏁 ===== Episode {self.episode_count} Summary ====="

        # 커리큘럼 정보 추가
        if self.use_improved_rewards and hasattr(
            self.ppo_agent.env, "get_current_phase_info"
        ):
            phase_info = self.ppo_agent.env.get_current_phase_info()
            episode_header += f" [{phase_info['name']}] "

        print(episode_header)
        print(f"Episode Stats:")
        print(f"   Duration: {episode_duration:.1f}s ({episode_length} steps)")
        print(f"   Steps/sec: {episode_length / max(0.1, episode_duration):.1f}")
        print(f"   End Reason: {episode_end_reason}")

        print(f"🎯 Game Performance:")
        print(f"   Final Score: {final_score:,}")
        print(f"   Max Score: {self.max_score_in_episode:,}")
        print(f"   Final Stage: {final_stage}")
        print(f"   Final Lives: {final_lives}")

        print(f"💰 Reward Analysis:")
        print(f"   Total Reward: {self.total_reward:.3f}")
        print(f"   Average Reward/Step: {avg_reward_per_step:.6f}")
        print(f"   Positive Rewards: {total_positive_reward:.3f}")
        print(f"   Negative Rewards: {total_negative_reward:.3f}")
        print(f"   Reward Steps: {len(self.episode_rewards)}")

        # 생존 분석 추가
        print(f"⏱️  Survival Analysis:")
        print(f"   Survival Time: {survival_seconds:.1f} seconds")
        print(f"   Survival Steps: {episode_length}")
        print(f"   Best Survival: {self.best_survival_time:.1f} seconds")

        if self.last_survival_time > 0:
            improvement = survival_seconds - self.last_survival_time
            if improvement > 0:
                print(f"   📈 Improvement: +{improvement:.1f}s from last episode!")
            elif improvement < 0:
                print(f"   📉 Decline: {improvement:.1f}s from last episode")
            else:
                print(f"   ➡️ Same as last episode")

        # 🎯 개선된 커리큘럼 단계별 생존 시간 평가
        if self.use_improved_rewards and hasattr(
            self.ppo_agent.env, "get_current_phase_info"
        ):
            phase_info = self.ppo_agent.env.get_current_phase_info()

            # 🎯 현실적인 단계별 목표 생존 시간 (대폭 하향 조정)
            target_survival = [1.0, 2.5, 5.0, 10.0][phase_info["phase"]]

            if survival_seconds < target_survival * 0.3:
                print(
                    f"   ⚠️ SHORT: {phase_info['name']} ({survival_seconds:.1f}s < {target_survival * 0.3:.1f}s)"
                )
                print(f"   💡 Target: {target_survival}s")
            elif survival_seconds >= target_survival:
                print(
                    f"   ✅ EXCELLENT! Target exceeded ({survival_seconds:.1f}s >= {target_survival}s)"
                )
            elif survival_seconds >= target_survival * 0.7:
                print(
                    f"   👍 GOOD: Approaching target ({survival_seconds:.1f}s / {target_survival}s)"
                )
        else:
            # 기존 평가
            if survival_seconds < 5.0:
                print(
                    f"   ⚠️ WARNING: Very short survival time ({survival_seconds:.1f}s)"
                )
                print(f"   💡 Agent needs to learn better survival strategies!")
            elif survival_seconds > 10.0:
                print(f"   ✅ Good survival time!")

        self.last_survival_time = survival_seconds

        print(f"📈 Overall Progress:")
        print(f"   Total Steps: {self.step_count}")
        print(f"   Episodes Completed: {self.episode_count}")
        print("=" * 50 + "\n")

        # 게임을 먼저 재시작하여 환경을 초기화합니다.
        if (
            self.game_instance
            and hasattr(self.game_instance, "game")
            and hasattr(self.game_instance.game, "restart_game")
        ):
            self.game_instance.game.restart_game()
            print("🔄 Game restarted for new episode.")

        # 에피소드 데이터 로깅 (리셋하기 전에 수행!)
        episode_total_reward = self.total_reward  # 현재 에피소드의 총 보상 저장
        self.log_episode_data(
            {
                "episode": self.episode_count,
                "duration": episode_duration,
                "steps": episode_length,
                "total_reward": episode_total_reward,  # 리셋 전 값 사용
                "avg_reward_per_step": avg_reward_per_step,
                "final_score": final_score,
                "max_score": self.max_score_in_episode,
                "final_stage": final_stage,
                "final_lives": final_lives,
                "positive_rewards": total_positive_reward,
                "negative_rewards": total_negative_reward,
                "end_reason": episode_end_reason,
            }
        )

        # 통계 리셋 (에피소드 데이터 로깅 후에 수행)
        self.total_reward = 0.0
        self.episode_start_time = time.time()
        self.episode_start_step = self.step_count
        self.episode_rewards.clear()
        self.episode_actions.clear()
        self.max_score_in_episode = 0
        self.max_lives_in_episode = 0
        self.final_stage = 1

        # 이전 상태 정보 초기화 (새 에피소드 시작)
        self.last_game_state = None
        self.last_action = None
        self.last_log_prob = None
        self.last_value = None

        # 환경 리셋 (PPO 환경의 이전 상태 초기화)
        self.ppo_agent.env.reset()

        # 목표 에피소드 수 달성 시에만 그래프 생성
        should_generate_plots = False
        should_terminate_game = False  # 게임 종료 플래그 추가

        if self.target_episodes and self.episode_count >= self.target_episodes:
            should_generate_plots = True
            should_terminate_game = True  # 목표 달성 시 게임 종료
            self.training_complete = True  # 훈련 완료 표시
            print(f"\n🎯 Target episodes ({self.target_episodes}) reached!")
            print(f"Episodes: {self.episode_count}, Steps: {self.step_count}")

            # 그래프 생성
            try:
                self.generate_final_plots(
                    f"Target episodes ({self.target_episodes}) completed"
                )
                print("Final plots generated.")
            except Exception as e:
                print(f"⚠️ Failed to generate plots: {e}")

            # 게임 종료
            print(f"🔚 Terminating game...")
            try:
                if self.game_instance and hasattr(self.game_instance, "quit"):
                    self.game_instance.quit()
                elif hasattr(self.game_instance, "running"):
                    self.game_instance.running = False

                px.quit()
                import sys

                sys.exit(0)

            except Exception as e:
                print(f"⚠️ Error during termination: {e}")
                import os

                os._exit(0)

        # 주기적 그래프 생성 제거 - 학습 종료 시에만 생성

        # 주기적 그래프 생성만 처리 (목표 달성 시는 위에서 이미 처리됨)
        if should_generate_plots and not should_terminate_game:
            self.generate_final_plots(
                f"Target episodes ({self.target_episodes}) completed"
            )

    def _print_performance_stats(self):
        """성능 통계 출력

        ---

        주기적으로 에이전트 성능 통계를 출력
        """
        current_time = time.time()
        elapsed_time = current_time - self.episode_start_time

        steps_per_second = self.step_count / max(1, elapsed_time)

        # PPO 에이전트 통계
        agent_stats = self.ppo_agent.get_stats()

        print(f"Stats @ Step {self.step_count} (Episode {self.episode_count}):")
        print(f"   Current Reward: {self.total_reward:.2f}")
        print(f"   Steps/sec: {steps_per_second:.1f}")

    def set_target_episodes(self, target: int):
        """목표 에피소드 수 설정

        Args:
            target: 목표 에피소드 수

        ---

        지정된 에피소드 수에 도달하면 그래프를 생성
        """
        self.target_episodes = target
        print(f"🎯 Target episodes set to: {target}")

    def is_training_complete(self) -> bool:
        """훈련 완료 여부 확인

        Returns:
            훈련 완료 여부

        ---

        외부에서 훈련 상태를 확인할 수 있는 메서드
        """
        return self.training_complete

    def generate_final_plots(self, reason: str = "Training completed"):
        """최종 그래프 생성

        Args:
            reason: 그래프 생성 이유

        ---

        훈련 완료 시 최종 결과 그래프를 생성
        """
        print(f"Generating final training plots - {reason}")
        self.generate_training_plots()

        # 최종 통계 출력
        print("\n" + "=" * 80)
        print("🎯 Training Summary")
        print(f"Total Episodes: {self.episode_count}")
        print(f"📈 Total Steps: {self.step_count}")
        print(f"🏆 Best Score: {self.best_score:,}")
        print(f"💰 Best Reward: {self.best_reward:.3f}")
        print(f"⏱️ Best Survival: {self.best_survival_time:.1f} seconds")
        print(f"⚡ Training Time: {time.time() - self.training_start_time:.1f}s")
        print("=" * 80)

    def _convert_survival_time_to_seconds(self, survival_time_frames: int) -> float:
        """배속 모드를 고려하여 survival_time을 실제 초 단위로 변환

        Args:
            survival_time_frames: 프레임 단위 생존 시간

        Returns:
            게임 내 생존 시간 (초)

        ---

        🧪 실험 결과: survival_time_frames는 이미 배속을 반영한 게임 시간
        따라서 단순히 60으로 나누면 올바른 게임 내 생존 시간이 됨
        """
        # 🎯 실험 결과: Method 1 (frames/60)이 정답
        # survival_time_frames는 이미 배속 모드를 반영한 게임 시간
        survival_seconds = survival_time_frames / 60.0

        # 🔍 디버깅: 가끔 중요한 정보 출력
        if self.episode_count % 20 == 0:
            print(
                f"🧪 Survival Time: {survival_time_frames} frames = {survival_seconds:.3f}s (Speed: {self.speed_multiplier}x)"
            )

        return survival_seconds


class PPOGameApp(App):
    """PPO 에이전트와 연동되는 게임 앱"""

    def __init__(self, game_ppo_agent: "GamePPOAgent", speed_multiplier: int = 1):
        """앱 초기화

        Args:
            game_ppo_agent: PPO 에이전트 래퍼
            speed_multiplier: 게임 배속 (1=정상속도, 2=2배속, 등...)
        """
        self.game_agent = game_ppo_agent
        # game_agent에 self(App 인스턴스)를 연결합니다.
        self.game_agent.set_game_instance(self)
        # App의 생성자를 호출합니다. 이 안에서 px.run()이 호출되어 게임이 시작됩니다.
        super().__init__(agent=game_ppo_agent, speed_multiplier=speed_multiplier)

    def update(self):
        """게임 업데이트 (에이전트 연동 + 속도 모드 적용)"""
        # 에이전트로부터 액션 받아오기 (입력 처리는 프레임당 한 번만)
        action = self.game_agent.select_action()

        # 액션을 게임 입력으로 변환하여 적용
        self.apply_agent_action(action)

        # 입력 처리는 프레임당 한 번만 (배속 영향 없음)
        self.input.update()

        # 게임 로직을 speed_multiplier만큼 반복 실행 (배속 적용!)
        for _ in range(self.speed_multiplier):
            self.game.update()


def find_latest_model() -> Optional[str]:
    """가장 최근 PPO 모델 찾기"""
    model_dir = "src/models/ppo"
    if not os.path.exists(model_dir):
        return None

    models = [f for f in os.listdir(model_dir) if f.endswith(".pth")]
    if not models:
        return None

    # 파일명의 타임스탬프로 정렬
    models.sort(reverse=True)
    latest_model = os.path.join(model_dir, models[0])
    return latest_model


def create_trained_ppo_agent(
    model_path: Optional[str] = None, enable_learning: bool = False
) -> PPOAgent:
    """훈련된 PPO 에이전트를 생성하거나 새로 초기화합니다."""
    from rl.environment import GameEnvironment
    from rl.agents.ppo_agent import create_ppo_agent

    env = GameEnvironment()
    agent = create_ppo_agent(env=env)

    if model_path and os.path.exists(model_path):
        try:
            agent.load_model(model_path)
            print(f"✅ Model loaded from {model_path}")
        except Exception as e:
            print(f"⚠️ Failed to load model, starting fresh.")
    else:
        print("🆕 Starting with new model.")

    if enable_learning:
        agent.set_train_mode()
    else:
        agent.set_eval_mode()

    return agent


def run_ppo_in_game(
    model_path: Optional[str] = None,
    skill_level: float = 0.7,
    personality: int = 1,
    enable_learning: bool = False,
    save_interval: int = 1000,
    target_episodes: Optional[int] = None,
    speed_multiplier: int = 1,
    use_improved_rewards: bool = True,
):
    """
    PPO 에이전트를 실제 게임에 연동하여 실행합니다.

    Args:
        model_path: 불러올 PPO 모델 파일 경로 (없으면 새로 생성)
        skill_level: 플레이어 실력 수준
        personality: 플레이어 성향 (0: 방어적, 1: 공격적)
        enable_learning: 학습 모드 활성화 여부
        save_interval: 모델 저장 간격 (스텝 단위)
        target_episodes: 목표 에피소드 수 (도달 시 학습 종료)
        speed_multiplier: 게임 배속 (1=정상속도, 2=2배속, 등...)
        use_improved_rewards: 개선된 보상 시스템 사용 여부
    """
    try:
        # 학습 모드이고 모델 경로가 지정되지 않은 경우, 자동 경로 생성
        if enable_learning and not model_path:
            model_dir = os.path.join("models", "ppo")
            os.makedirs(model_dir, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            model_path = os.path.join(model_dir, f"ppo_agent_{timestamp}.pth")

        # 에이전트 생성
        ppo_agent = create_trained_ppo_agent(
            model_path=model_path, enable_learning=enable_learning
        )

        # 게임-PPO 에이전트 래퍼 생성
        game_agent = GamePPOAgent(
            ppo_agent=ppo_agent,
            skill_level=skill_level,
            personality=personality,
            enable_learning=enable_learning,
            model_path=model_path,
            save_interval=save_interval,
            speed_multiplier=speed_multiplier,
            use_improved_rewards=use_improved_rewards,
        )

        # 목표 에피소드 설정
        if target_episodes is not None:
            game_agent.set_target_episodes(target_episodes)

        if speed_multiplier > 1:
            print(f"🚀 Speed: {speed_multiplier}x")
        print("🎮 Starting game...")
        app = PPOGameApp(game_agent, speed_multiplier=speed_multiplier)
        app.run()

    except KeyboardInterrupt:
        print("\n⚠️ Training interrupted by user (Ctrl+C).")
        if "game_agent" in locals() and enable_learning:
            game_agent.generate_final_plots("Training interrupted by user")
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}", file=sys.stderr)
        print(traceback.format_exc(), file=sys.stderr)
        sys.exit(1)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Run PPO agent in the game environment with improved reward system and curriculum learning."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Path to the saved PPO model (default: auto-detect latest)",
    )
    parser.add_argument(
        "--skill", type=float, default=0.7, help="Player skill level (0 to 1)"
    )
    parser.add_argument(
        "--personality",
        type=int,
        default=1,
        help="Player personality (0: Defensive, 1: Aggressive)",
    )
    parser.add_argument(
        "--learn", action="store_true", help="Enable learning mode for the agent"
    )
    parser.add_argument(
        "--save-interval",
        type=int,
        default=500,
        help="Model save interval (steps) - reduced for curriculum learning",
    )
    parser.add_argument(
        "--target-episodes",
        type=int,
        default=1000,  # 커리큘럼 학습 전체 에피소드에 맞게 조정
        help="Target number of episodes to run before auto-terminating (default: 1000 for full curriculum).",
    )
    parser.add_argument(
        "--speed",
        type=int,
        default=2,  # 학습 시간 단축을 위해 기본 2배속
        help="Game speed multiplier (1=normal, 2=2x speed, etc.). Higher values reduce training time.",
    )
    parser.add_argument(
        "--no-improved-rewards",
        action="store_true",
        help="Disable improved reward system and curriculum learning (use standard rewards)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start with fresh model (ignore existing models)",
    )
    args = parser.parse_args()

    # 모델 경로 결정
    model_path = None
    if not args.fresh:
        if args.model:
            if os.path.exists(args.model):
                model_path = args.model
            else:
                print(f"❌ 지정된 모델을 찾을 수 없습니다: {args.model}")
                return
        else:
            model_path = find_latest_model()
            if model_path:
                print(f"🔍 자동 감지된 최신 모델: {model_path}")

    use_improved_rewards = not args.no_improved_rewards

    print(f"🎮 PPO Agent Launch")
    print(
        f"📋 Config: Learning={args.learn}, Speed={args.speed}x, Episodes={args.target_episodes or 'unlimited'}"
    )
    print(
        f"🎓 Curriculum Learning: {'Enabled' if use_improved_rewards else 'Disabled'}"
    )
    if use_improved_rewards:
        print(
            f"   📚 Phase 1: Quick Control (Episodes 1-100) - Basic movement (1s invulnerability)"
        )
        print(
            f"   🛡️ Phase 2: Survival Focus (Episodes 101-250) - Survival skills (0.5s invulnerability)"
        )
        print(
            f"   ⚔️ Phase 3: Combat Training (Episodes 251-500) - Attack patterns (0.25s invulnerability)"
        )
        print(
            f"   🏆 Phase 4: Master Strategy (Episodes 501-1000) - Full difficulty (no invulnerability)"
        )

        # 🎯 스킬별 에이전트 능력 차별화 정보
        print(f"\n🎯 Agent Skill Differentiation (Same Environment):")
        if args.skill < 0.3:
            print(
                f"   🔰 BEGINNER Agent (Skill {args.skill:.1f}): 50% accuracy, 20% random actions, frequent mistakes"
            )
            print(
                f"      • Target: 10s survival • Panic threshold: 2 enemies • Strategic thinking: 10%"
            )
        elif args.skill < 0.7:
            print(
                f"   ⚖️ INTERMEDIATE Agent (Skill {args.skill:.1f}): 75% accuracy, 10% random actions, moderate mistakes"
            )
            print(
                f"      • Target: 20s survival • Panic threshold: 4 enemies • Strategic thinking: 30%"
            )
        else:
            print(
                f"   🔥 EXPERT Agent (Skill {args.skill:.1f}): 95% accuracy, 1% random actions, minimal mistakes"
            )
            print(
                f"      • Target: 30s survival • Panic threshold: 8 enemies • Strategic thinking: 80%"
            )

    if model_path:
        print(f"📁 Model: {model_path}")
    else:
        print(f"📁 Starting with new model")

    run_ppo_in_game(
        model_path=model_path,
        skill_level=args.skill,
        personality=args.personality,
        enable_learning=args.learn,
        save_interval=args.save_interval,
        target_episodes=args.target_episodes,
        speed_multiplier=args.speed,
        use_improved_rewards=use_improved_rewards,
    )


if __name__ == "__main__":
    main()
