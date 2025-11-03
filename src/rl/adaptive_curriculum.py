"""
적응형 커리큘럼 러닝 - 성능 기반 단계 전환

기존 StepCurriculum의 문제점:
- 성능과 무관하게 정해진 에피소드 수만 지나면 다음 단계로 강제 전환
- 목표를 달성하지 못한 상태로 어려운 단계에 진입
- 학습 효율 저하 및 실패

개선점:
- 각 단계에서 목표 달성률이 일정 수준에 도달해야만 다음 단계로 전환
- 최소/최대 에피소드 제한으로 무한 대기 또는 조기 전환 방지
- 단계별 성능 추적 및 통계
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional
from collections import deque
import numpy as np


@dataclass
class AdaptiveStage:
    """적응형 커리큘럼의 단일 스테이지 정의
    
    Attributes:
        skill_level: 단계 스킬 레벨 (0.0 ~ 1.0)
        name: 단계 설명 이름
        target_steps: 목표 생존 스텝
        target_kills: 목표 킬 수
        min_episodes: 최소 에피소드 수 (조기 전환 방지)
        max_episodes: 최대 에피소드 수 (무한 대기 방지)
        success_threshold: 다음 단계 전환 기준 (목표 달성률)
        window_size: 성능 평가 윈도우 (최근 N개 에피소드)
    """
    skill_level: float
    name: str
    target_steps: int
    target_kills: float
    min_episodes: int = 100
    max_episodes: int = 500
    success_threshold: float = 0.75  # 75% 달성률
    window_size: int = 50  # 최근 50 에피소드로 평가


class AdaptiveCurriculum:
    """성능 기반 적응형 커리큘럼 스케줄러
    
    각 단계에서 목표 달성률이 threshold에 도달하면 다음 단계로 자동 전환
    """
    
    def __init__(self, stages: List[AdaptiveStage]):
        if not stages:
            raise ValueError("stages must not be empty")
        self.stages = stages
        self.current_stage_idx = 0
        self.stage_episode_count = 0  # 현재 단계 내 에피소드 카운터
        
        # 성능 추적
        self.recent_steps = deque(maxlen=stages[0].window_size)
        self.recent_kills = deque(maxlen=stages[0].window_size)
        self.stage_history = []  # 단계별 통계
        
    def get_current_stage(self) -> AdaptiveStage:
        """현재 스테이지 반환"""
        return self.stages[self.current_stage_idx]
    
    def report_episode_result(self, survival_steps: int, kills: float) -> bool:
        """에피소드 결과를 보고하고 단계 전환 여부 판단
        
        Args:
            survival_steps: 에피소드 생존 스텝
            kills: 에피소드 킬 수
            
        Returns:
            True if stage changed, False otherwise
        """
        current_stage = self.get_current_stage()
        
        # 성능 기록
        self.recent_steps.append(survival_steps)
        self.recent_kills.append(kills)
        self.stage_episode_count += 1
        
        # 최소 에피소드 미달 시 전환 불가
        if self.stage_episode_count < current_stage.min_episodes:
            return False
        
        # 최대 에피소드 도달 시 강제 전환 (무한 대기 방지)
        if self.stage_episode_count >= current_stage.max_episodes:
            return self._advance_stage()
        
        # 성능 평가 (충분한 데이터가 쌓였을 때만)
        if len(self.recent_steps) >= min(current_stage.window_size, current_stage.min_episodes):
            avg_steps = np.mean(self.recent_steps)
            avg_kills = np.mean(self.recent_kills)
            
            # 목표 달성률 계산
            step_achievement = avg_steps / current_stage.target_steps
            kill_achievement = avg_kills / current_stage.target_kills if current_stage.target_kills > 0 else 1.0
            
            # 두 지표 모두 threshold 이상이면 다음 단계로 전환
            if step_achievement >= current_stage.success_threshold and \
               kill_achievement >= current_stage.success_threshold:
                print(f"\n🎯 단계 목표 달성!")
                print(f"   생존: {avg_steps:.1f}/{current_stage.target_steps} ({step_achievement*100:.1f}%)")
                print(f"   킬: {avg_kills:.1f}/{current_stage.target_kills} ({kill_achievement*100:.1f}%)")
                return self._advance_stage()
        
        return False
    
    def _advance_stage(self) -> bool:
        """다음 단계로 전환"""
        current_stage = self.get_current_stage()
        
        # 현재 단계 통계 저장
        if len(self.recent_steps) > 0:
            self.stage_history.append({
                'stage_idx': self.current_stage_idx,
                'stage_name': current_stage.name,
                'episodes': self.stage_episode_count,
                'avg_steps': np.mean(self.recent_steps),
                'avg_kills': np.mean(self.recent_kills),
                'target_steps': current_stage.target_steps,
                'target_kills': current_stage.target_kills,
            })
        
        # 마지막 단계라면 전환 불가
        if self.current_stage_idx >= len(self.stages) - 1:
            return False
        
        # 다음 단계로 전환
        self.current_stage_idx += 1
        self.stage_episode_count = 0
        
        # 새 단계의 윈도우 크기로 버퍼 재설정
        next_stage = self.get_current_stage()
        self.recent_steps = deque(maxlen=next_stage.window_size)
        self.recent_kills = deque(maxlen=next_stage.window_size)
        
        return True
    
    def skill_for_episode(self, episode_index: int) -> Tuple[float, str]:
        """현재 스테이지의 skill_level과 이름 반환
        
        Note: 이 메서드는 호환성을 위해 제공되지만,
              실제 단계 전환은 report_episode_result()로 결정됨
        """
        current_stage = self.get_current_stage()
        return current_stage.skill_level, current_stage.name
    
    def get_progress_info(self) -> dict:
        """현재 진행 상황 정보 반환"""
        current_stage = self.get_current_stage()
        
        info = {
            'current_stage_idx': self.current_stage_idx,
            'total_stages': len(self.stages),
            'stage_name': current_stage.name,
            'skill_level': current_stage.skill_level,
            'stage_episodes': self.stage_episode_count,
            'min_episodes': current_stage.min_episodes,
            'max_episodes': current_stage.max_episodes,
        }
        
        if len(self.recent_steps) > 0:
            info.update({
                'recent_avg_steps': np.mean(self.recent_steps),
                'recent_avg_kills': np.mean(self.recent_kills),
                'target_steps': current_stage.target_steps,
                'target_kills': current_stage.target_kills,
                'step_achievement': np.mean(self.recent_steps) / current_stage.target_steps,
                'kill_achievement': np.mean(self.recent_kills) / current_stage.target_kills if current_stage.target_kills > 0 else 0,
            })
        
        return info
    
    def print_stage_summary(self):
        """현재까지의 단계별 통계 출력"""
        if not self.stage_history:
            return
        
        print("\n" + "="*70)
        print("📊 커리큘럼 단계별 학습 통계")
        print("="*70)
        
        for stat in self.stage_history:
            step_rate = (stat['avg_steps'] / stat['target_steps']) * 100
            kill_rate = (stat['avg_kills'] / stat['target_kills']) * 100 if stat['target_kills'] > 0 else 0
            
            print(f"\n🎓 {stat['stage_name']}")
            print(f"   에피소드: {stat['episodes']}")
            print(f"   평균 생존: {stat['avg_steps']:.1f} / {stat['target_steps']} ({step_rate:.1f}%)")
            print(f"   평균 킬: {stat['avg_kills']:.1f} / {stat['target_kills']:.1f} ({kill_rate:.1f}%)")
        
        print("="*70)

