"""
보상 분해 분석 모듈

PPO 학습 진단을 위한 보상 함수 분해 및 분석 도구
각 보상 요소의 기여도를 측정하고 학습 정체 원인을 파악합니다.
"""

from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, asdict
import numpy as np
import math
from collections import deque

from .targets import get_survival_target_steps, get_kill_target


@dataclass
class RewardBreakdown:
    """보상 분해 결과
    
    모든 보상 요소를 세분화하여 저장
    """
    # 기본 정보
    episode: int
    step: int
    skill_level: float
    
    # 게임 상태
    current_step: int
    current_kills: float
    current_hp: int
    current_lives: int
    
    # 목표 달성률
    target_survival_steps: int
    target_kills: float
    survival_achievement: float  # 0.0 ~ 1.0+
    kill_achievement: float      # 0.0 ~ 1.0+
    
    # 보상 요소
    survival_score: float        # 0.0 ~ 1.0
    attack_score: float          # 0.0 ~ 1.0
    multiplicative_reward: float # survival × attack
    bonus: float                 # exponential bonus
    dodge_reward: float          # 탄환 회피 보상
    kill_reward: float           # 킬 즉각 보상
    hp_damage_penalty: float     # HP 손실 페널티
    death_penalty: float         # 사망 페널티
    
    # 최종 보상
    final_reward: float
    
    # 보상 구성 비율
    base_reward_ratio: float     # (mult + bonus) / final
    immediate_reward_ratio: float # (dodge + kill) / final
    penalty_ratio: float         # (hp_dmg + death) / final


class RewardAnalyzer:
    """보상 분석기
    
    게임 환경과 연동하여 보상을 분해 분석합니다.
    """
    
    def __init__(self):
        self.episode_breakdowns: List[RewardBreakdown] = []
        self.current_episode = 0
        
        # 에피소드 통계
        self.episode_stats: Dict[int, Dict] = {}
        
        # 이전 상태 추적 (environment와 동일)
        self.previous_kills = 0
        self.previous_hp = 3
        self.previous_lives = 3
        self.previous_nearby_bullets: List[Tuple[float, float, float]] = []
        
    def reset_episode(self):
        """새 에피소드 시작"""
        self.current_episode += 1
        self.previous_kills = 0
        self.previous_hp = 3
        self.previous_lives = 3
        self.previous_nearby_bullets = []
        
    def analyze_reward(
        self,
        game_instance,
        skill_level: float,
        episode_step: int,
        previous_nearby_bullets: Optional[List[Tuple[float, float, float]]] = None,
        previous_player_pos: Optional[Tuple[float, float]] = None,
    ) -> RewardBreakdown:
        """보상을 분해하여 분석
        
        Environment.calculate_reward()의 로직을 그대로 재현하되,
        각 요소를 세분화하여 반환합니다.
        
        Args:
            game_instance: 게임 인스턴스
            skill_level: 스킬 레벨
            episode_step: 현재 에피소드 내 스텝
            previous_nearby_bullets: 이전 프레임의 가까운 탄환들
            previous_player_pos: 이전 플레이어 위치
            
        Returns:
            RewardBreakdown 객체
        """
        if not (hasattr(game_instance, "game") and game_instance.game):
            return self._empty_breakdown(skill_level, episode_step)
        
        game_vars = getattr(game_instance.game, "game_vars", None)
        if not game_vars:
            return self._empty_breakdown(skill_level, episode_step)
        
        # 현재 게임 상태 추출
        current_step = episode_step
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
        
        # === 1. 생존 점수 (Survival Score) ===
        survival_score = min(1.0, current_step / target_survival_steps)
        survival_achievement = current_step / target_survival_steps
        
        # === 2. 공격 점수 (Attack Score) ===
        if current_step > 0 and target_kill_rate > 0:
            current_kill_rate = (current_kills / max(current_step, 1)) * 100.0
            attack_score = min(1.0, current_kill_rate / target_kill_rate)
            kill_achievement = current_kills / target_kills if target_kills > 0 else 1.0
        else:
            attack_score = 0.0
            kill_achievement = 0.0
        
        # === 3. Multiplicative Reward ===
        multiplicative_reward = survival_score * attack_score
        
        # === 4. Bonus ===
        bonus = 0.0
        if survival_score >= 0.8 and attack_score >= 0.8:
            avg_score = (survival_score + attack_score) / 2.0
            min_score = min(survival_score, attack_score)
            
            if avg_score >= 0.9:
                bonus = (avg_score ** 3) * min_score * 0.5
            else:
                bonus = (avg_score ** 2) * min_score * 0.2
            
            if survival_score >= 1.0 and attack_score >= 1.0:
                bonus += 0.3
        
        # === 5. 탄환 회피 보상 ===
        dodge_reward = 0.0
        if previous_nearby_bullets and len(previous_nearby_bullets) > 0:
            # 간단화: 실제 계산은 복잡하므로 근사치 사용
            # 실제 게임 환경에서는 더 정밀한 계산 필요
            dodged_count = len(previous_nearby_bullets)  # 단순화
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
            self.previous_hp = current_hp
        
        # === 8. 사망 페널티 ===
        death_penalty = 0.0
        if current_lives < self.previous_lives:
            death_penalty = 0.2 + (skill_level * 0.3)
            self.previous_lives = current_lives
            self.previous_hp = 3
        
        # === 9. 최종 보상 ===
        final_reward = max(0.0, multiplicative_reward + bonus + dodge_reward + kill_reward
                          - hp_damage_penalty - death_penalty)
        
        # 상태 업데이트
        self.previous_kills = current_kills
        
        # 보상 구성 비율 계산
        if final_reward > 0:
            base_reward_ratio = (multiplicative_reward + bonus) / final_reward
            immediate_reward_ratio = (dodge_reward + kill_reward) / final_reward
            penalty_ratio = (hp_damage_penalty + death_penalty) / final_reward
        else:
            base_reward_ratio = 0.0
            immediate_reward_ratio = 0.0
            penalty_ratio = 0.0
        
        breakdown = RewardBreakdown(
            episode=self.current_episode,
            step=episode_step,
            skill_level=skill_level,
            current_step=current_step,
            current_kills=current_kills,
            current_hp=current_hp,
            current_lives=current_lives,
            target_survival_steps=target_survival_steps,
            target_kills=target_kills,
            survival_achievement=survival_achievement,
            kill_achievement=kill_achievement,
            survival_score=survival_score,
            attack_score=attack_score,
            multiplicative_reward=multiplicative_reward,
            bonus=bonus,
            dodge_reward=dodge_reward,
            kill_reward=kill_reward,
            hp_damage_penalty=hp_damage_penalty,
            death_penalty=death_penalty,
            final_reward=final_reward,
            base_reward_ratio=base_reward_ratio,
            immediate_reward_ratio=immediate_reward_ratio,
            penalty_ratio=penalty_ratio,
        )
        
        self.episode_breakdowns.append(breakdown)
        return breakdown
    
    def _empty_breakdown(self, skill_level: float, episode_step: int) -> RewardBreakdown:
        """빈 breakdown 반환 (에러 케이스)"""
        target_survival_steps = get_survival_target_steps(skill_level)
        target_kills = get_kill_target(skill_level)
        
        return RewardBreakdown(
            episode=self.current_episode,
            step=episode_step,
            skill_level=skill_level,
            current_step=0,
            current_kills=0.0,
            current_hp=3,
            current_lives=3,
            target_survival_steps=target_survival_steps,
            target_kills=target_kills,
            survival_achievement=0.0,
            kill_achievement=0.0,
            survival_score=0.0,
            attack_score=0.0,
            multiplicative_reward=0.0,
            bonus=0.0,
            dodge_reward=0.0,
            kill_reward=0.0,
            hp_damage_penalty=0.0,
            death_penalty=0.0,
            final_reward=0.0,
            base_reward_ratio=0.0,
            immediate_reward_ratio=0.0,
            penalty_ratio=0.0,
        )
    
    def get_episode_summary(self, episode: Optional[int] = None) -> Dict:
        """에피소드 요약 통계
        
        Args:
            episode: 에피소드 번호 (None이면 현재 에피소드)
            
        Returns:
            에피소드 요약 딕셔너리
        """
        if episode is None:
            episode = self.current_episode
        
        # 해당 에피소드의 breakdown들 필터링
        episode_data = [b for b in self.episode_breakdowns if b.episode == episode]
        
        if not episode_data:
            return {}
        
        # 통계 계산
        final_breakdown = episode_data[-1]  # 마지막 breakdown
        
        # 각 보상 요소의 누적 기여도
        total_multiplicative = sum(b.multiplicative_reward for b in episode_data)
        total_bonus = sum(b.bonus for b in episode_data)
        total_dodge = sum(b.dodge_reward for b in episode_data)
        total_kill = sum(b.kill_reward for b in episode_data)
        total_hp_penalty = sum(b.hp_damage_penalty for b in episode_data)
        total_death_penalty = sum(b.death_penalty for b in episode_data)
        total_reward = sum(b.final_reward for b in episode_data)
        
        summary = {
            'episode': episode,
            'skill_level': final_breakdown.skill_level,
            'final_step': final_breakdown.current_step,
            'final_kills': final_breakdown.current_kills,
            'survival_achievement': final_breakdown.survival_achievement,
            'kill_achievement': final_breakdown.kill_achievement,
            
            # 누적 보상 요소
            'total_reward': total_reward,
            'total_multiplicative': total_multiplicative,
            'total_bonus': total_bonus,
            'total_dodge': total_dodge,
            'total_kill': total_kill,
            'total_hp_penalty': total_hp_penalty,
            'total_death_penalty': total_death_penalty,
            
            # 보상 구성 비율
            'multiplicative_ratio': total_multiplicative / total_reward if total_reward > 0 else 0,
            'bonus_ratio': total_bonus / total_reward if total_reward > 0 else 0,
            'dodge_ratio': total_dodge / total_reward if total_reward > 0 else 0,
            'kill_ratio': total_kill / total_reward if total_reward > 0 else 0,
            'hp_penalty_ratio': total_hp_penalty / total_reward if total_reward > 0 else 0,
            'death_penalty_ratio': total_death_penalty / total_reward if total_reward > 0 else 0,
            
            # 평균 점수
            'avg_survival_score': np.mean([b.survival_score for b in episode_data]),
            'avg_attack_score': np.mean([b.attack_score for b in episode_data]),
            
            # 학습 신호 강도 (보상의 변동성)
            'reward_std': np.std([b.final_reward for b in episode_data]),
            'reward_mean': np.mean([b.final_reward for b in episode_data]),
        }
        
        return summary
    
    def get_all_summaries(self) -> List[Dict]:
        """모든 에피소드의 요약 통계"""
        episodes = sorted(set(b.episode for b in self.episode_breakdowns))
        return [self.get_episode_summary(ep) for ep in episodes]
    
    def diagnose_reward_sparsity(self, recent_episodes: int = 50) -> Dict:
        """보상 희소성 진단
        
        Args:
            recent_episodes: 분석할 최근 에피소드 수
            
        Returns:
            진단 결과
        """
        if not self.episode_breakdowns:
            return {'error': 'No data available'}
        
        # 최근 에피소드들 필터
        max_episode = max(b.episode for b in self.episode_breakdowns)
        min_episode = max(1, max_episode - recent_episodes + 1)
        recent_data = [b for b in self.episode_breakdowns 
                       if min_episode <= b.episode <= max_episode]
        
        if not recent_data:
            return {'error': 'No recent data'}
        
        # 보상 요소별 통계
        multiplicative_rewards = [b.multiplicative_reward for b in recent_data]
        bonuses = [b.bonus for b in recent_data]
        immediate_rewards = [b.dodge_reward + b.kill_reward for b in recent_data]
        final_rewards = [b.final_reward for b in recent_data]
        
        # Sparsity 지표
        # 1. Zero reward 비율
        zero_mult_ratio = sum(1 for r in multiplicative_rewards if r == 0) / len(multiplicative_rewards)
        zero_bonus_ratio = sum(1 for r in bonuses if r == 0) / len(bonuses)
        zero_immediate_ratio = sum(1 for r in immediate_rewards if r == 0) / len(immediate_rewards)
        
        # 2. 보상 크기
        avg_mult = np.mean(multiplicative_rewards)
        avg_bonus = np.mean(bonuses)
        avg_immediate = np.mean(immediate_rewards)
        avg_final = np.mean(final_rewards)
        
        # 3. 학습 신호 강도
        reward_variance = np.var(final_rewards)
        signal_to_noise = avg_final / np.std(final_rewards) if np.std(final_rewards) > 0 else 0
        
        # 4. 달성률
        survival_achievements = [b.survival_achievement for b in recent_data]
        kill_achievements = [b.kill_achievement for b in recent_data]
        avg_survival_achievement = np.mean(survival_achievements)
        avg_kill_achievement = np.mean(kill_achievements)
        
        diagnosis = {
            'recent_episodes': recent_episodes,
            'total_steps_analyzed': len(recent_data),
            
            # Sparsity 지표
            'zero_multiplicative_ratio': zero_mult_ratio,
            'zero_bonus_ratio': zero_bonus_ratio,
            'zero_immediate_ratio': zero_immediate_ratio,
            
            # 평균 보상
            'avg_multiplicative_reward': avg_mult,
            'avg_bonus': avg_bonus,
            'avg_immediate_reward': avg_immediate,
            'avg_final_reward': avg_final,
            
            # 학습 신호
            'reward_variance': reward_variance,
            'signal_to_noise_ratio': signal_to_noise,
            
            # 달성률
            'avg_survival_achievement': avg_survival_achievement,
            'avg_kill_achievement': avg_kill_achievement,
            
            # 진단 메시지
            'diagnosis': self._generate_diagnosis_message(
                avg_mult, avg_bonus, avg_immediate, 
                avg_survival_achievement, avg_kill_achievement,
                zero_bonus_ratio
            ),
        }
        
        return diagnosis
    
    def _generate_diagnosis_message(
        self, 
        avg_mult: float,
        avg_bonus: float, 
        avg_immediate: float,
        survival_achievement: float,
        kill_achievement: float,
        zero_bonus_ratio: float,
    ) -> str:
        """진단 메시지 생성"""
        messages = []
        
        # 보상 희소성 체크
        if avg_mult < 0.1:
            messages.append("🚨 Multiplicative reward가 매우 낮음 (목표 달성률 부족)")
        
        if zero_bonus_ratio > 0.95:
            messages.append("⚠️ Bonus가 거의 발생하지 않음 (80% 달성 필요)")
        
        if avg_immediate < 0.05:
            messages.append("⚠️ 즉각 보상(킬/회피)이 매우 적음")
        
        # 달성률 체크
        if survival_achievement < 0.5:
            messages.append(f"🚨 생존 목표 달성률이 매우 낮음: {survival_achievement*100:.1f}%")
        
        if kill_achievement < 0.5:
            messages.append(f"🚨 킬 목표 달성률이 매우 낮음: {kill_achievement*100:.1f}%")
        
        # 불균형 체크
        achievement_diff = abs(survival_achievement - kill_achievement)
        if achievement_diff > 0.3:
            if survival_achievement > kill_achievement:
                messages.append(f"⚠️ 생존 편향 (생존 {survival_achievement*100:.1f}% vs 킬 {kill_achievement*100:.1f}%)")
            else:
                messages.append(f"⚠️ 공격 편향 (킬 {kill_achievement*100:.1f}% vs 생존 {survival_achievement*100:.1f}%)")
        
        if not messages:
            messages.append("✅ 보상 체계가 정상적으로 작동 중")
        
        return " | ".join(messages)
    
    def save_to_csv(self, filepath: str):
        """분석 결과를 CSV로 저장"""
        import csv
        
        if not self.episode_breakdowns:
            print("저장할 데이터가 없습니다.")
            return
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=asdict(self.episode_breakdowns[0]).keys())
            writer.writeheader()
            for breakdown in self.episode_breakdowns:
                writer.writerow(asdict(breakdown))
        
        print(f"✅ 보상 분해 데이터 저장 완료: {filepath}")


