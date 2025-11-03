"""
목표 기반 커리큘럼 러닝 - 목표 달성 시 자동 종료

핵심 아이디어:
- 에피소드 수를 미리 정하지 않음
- 각 단계의 목표를 달성하면 다음 단계로
- 최종 단계(Skill 1.0)의 목표를 달성하면 훈련 자동 종료
- 효율적이고 명확한 훈련 프로세스

기존 방식의 문제:
- "5000 에피소드 훈련" → 충분한지 부족한지 모름
- 목표 달성 후에도 계속 훈련 (낭비)
- 목표 미달성 상태에서 종료 (품질 저하)

개선된 방식:
- "Skill 1.0 목표 달성까지 훈련" → 명확한 종료 조건
- 달성하면 즉시 종료 (효율성)
- 미달성이면 계속 훈련 (품질 보장)
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from collections import deque
import numpy as np


@dataclass
class GoalBasedStage:
    """목표 기반 커리큘럼의 단일 스테이지
    
    Attributes:
        skill_level: 단계 스킬 레벨 (0.0 ~ 1.0)
        name: 단계 설명 이름
        target_steps: 목표 생존 스텝
        target_kills: 목표 킬 수
        min_episodes: 최소 에피소드 수 (조기 전환 방지)
        max_episodes: 최대 에피소드 수 (안전장치, 무한 대기 방지)
        success_threshold: 목표 달성 기준 (0.0 ~ 1.0)
        window_size: 성능 평가 윈도우 (최근 N개 에피소드)
        is_final: 최종 단계 여부 (True면 달성 시 훈련 종료)
    """
    skill_level: float
    name: str
    target_steps: int
    target_kills: float
    min_episodes: int = 100
    max_episodes: int = 2000  # 안전장치
    success_threshold: float = 0.80  # 80% 달성 기준 (엄격하게)
    window_size: int = 50
    is_final: bool = False  # 최종 단계 표시


class GoalBasedCurriculum:
    """목표 달성 기반 커리큘럼 - 목표 달성 시 자동 종료
    
    핵심 기능:
    1. 각 단계에서 목표의 80%를 달성해야 다음 단계로
    2. 최종 단계에서 목표 달성 시 훈련 자동 종료
    3. max_episodes는 안전장치로만 사용 (무한 루프 방지)
    """
    
    def __init__(self, stages: List[GoalBasedStage]):
        if not stages:
            raise ValueError("stages must not be empty")
        
        # 마지막 단계는 자동으로 final로 설정
        stages[-1].is_final = True
        
        self.stages = stages
        self.current_stage_idx = 0
        self.stage_episode_count = 0
        self.total_episode_count = 0
        
        # 성능 추적
        current_stage = self.get_current_stage()
        self.recent_steps = deque(maxlen=current_stage.window_size)
        self.recent_kills = deque(maxlen=current_stage.window_size)
        self.stage_history = []
        
        # 훈련 종료 플래그
        self.training_complete = False
        self.completion_reason = None
        
    def get_current_stage(self) -> GoalBasedStage:
        """현재 스테이지 반환"""
        return self.stages[self.current_stage_idx]
    
    def is_training_complete(self) -> bool:
        """훈련 완료 여부 확인"""
        return self.training_complete
    
    def get_completion_info(self) -> Optional[Dict]:
        """훈련 완료 정보 반환"""
        if not self.training_complete:
            return None
        
        return {
            'reason': self.completion_reason,
            'total_episodes': self.total_episode_count,
            'final_stage': self.get_current_stage().name,
            'final_skill': self.get_current_stage().skill_level,
        }
    
    def report_episode_result(self, survival_steps: int, kills: float) -> Dict[str, any]:
        """에피소드 결과를 보고하고 단계 전환 또는 훈련 종료 판단
        
        Args:
            survival_steps: 에피소드 생존 스텝
            kills: 에피소드 킬 수
            
        Returns:
            {
                'stage_changed': bool,  # 단계 전환 여부
                'training_complete': bool,  # 훈련 종료 여부
                'reason': str,  # 전환/종료 이유
                'achievement': dict,  # 달성률 정보
            }
        """
        if self.training_complete:
            return {
                'stage_changed': False,
                'training_complete': True,
                'reason': self.completion_reason,
            }
        
        current_stage = self.get_current_stage()
        
        # 성능 기록
        self.recent_steps.append(survival_steps)
        self.recent_kills.append(kills)
        self.stage_episode_count += 1
        self.total_episode_count += 1
        
        # 현재 달성률 계산
        achievement_info = self._calculate_achievement()
        
        # 경고: 최대 에피소드 근처
        if self.stage_episode_count >= current_stage.max_episodes:
            if not achievement_info['goal_achieved']:
                # 목표 미달성 - 경고만 하고 계속 학습
                if self.stage_episode_count % 100 == 0:  # 100 에피소드마다 경고
                    print(f"\n{'='*70}")
                    print(f"⚠️  경고: 권장 최대 에피소드({current_stage.max_episodes}) 초과")
                    print(f"{'='*70}")
                    print(f"단계: {current_stage.name} (Skill {current_stage.skill_level:.1f})")
                    print(f"현재 에피소드: {self.stage_episode_count}회")
                    print(f"생존 달성률: {achievement_info['step_achievement']:.1%} (목표: {current_stage.success_threshold:.1%})")
                    print(f"킬 달성률: {achievement_info['kill_achievement']:.1%} (목표: {current_stage.success_threshold:.1%})")
                    print(f"\n💡 목표 달성까지 계속 학습합니다...")
                    print(f"   학습이 정체되었다면 Ctrl+C로 중단 후 조정하세요")
                    print(f"{'='*70}")
                
                # 계속 학습
                return {
                    'stage_changed': False,
                    'training_complete': False,  # 계속!
                    'achievement': achievement_info,
                }
            
            # 목표 달성한 경우
            if current_stage.is_final:
                # 최종 단계: 목표 달성했으므로 성공
                self.training_complete = True
                self.completion_reason = f"최종 목표 달성: {achievement_info['overall_achievement']:.1%}"
                self._save_stage_history(achievement_info)
                
                print(f"\n🎉 훈련 완료! (목표 달성)")
                
                return {
                    'stage_changed': False,
                    'training_complete': True,
                    'reason': self.completion_reason,
                    'achievement': achievement_info,
                }
            else:
                # 중간 단계: 목표 달성했으므로 다음 단계로
                print(f"\n✅ 목표 달성, 다음 단계로 전환")
                return self._advance_stage(achievement_info, forced=True)
        
        # 최소 에피소드 확인 (단, 목표 과달성 시 조기 전환 허용)
        if self.stage_episode_count < current_stage.min_episodes:
            # 목표를 크게 초과 달성하면 조기 전환 허용 (120% 이상)
            if achievement_info['step_achievement'] >= 1.2 and achievement_info['kill_achievement'] >= 1.2:
                print(f"\n💡 조기 목표 과달성! (min_episodes 미달이지만 목표 120% 이상 달성)")
                # 과달성했으므로 전환 허용 (아래 코드로 계속)
            else:
                # 아직 충분하지 않음, 최소 에피소드 대기
                return {
                    'stage_changed': False,
                    'training_complete': False,
                    'achievement': achievement_info,
                }
        
        # 충분한 데이터가 쌓였을 때만 평가
        if len(self.recent_steps) < min(current_stage.window_size, current_stage.min_episodes):
            return {
                'stage_changed': False,
                'training_complete': False,
                'achievement': achievement_info,
            }
        
        # 목표 달성 확인
        if achievement_info['goal_achieved']:
            if current_stage.is_final:
                # 🎉 최종 단계 목표 달성 → 훈련 완료!
                self.training_complete = True
                self.completion_reason = f"최종 목표 달성! (생존: {achievement_info['step_achievement']:.1%}, 킬: {achievement_info['kill_achievement']:.1%})"
                self._save_stage_history(achievement_info)
                
                print(f"\n🎉🎉🎉 훈련 완료! 🎉🎉🎉")
                print(f"최종 단계 목표 달성!")
                print(f"  총 에피소드: {self.total_episode_count}")
                print(f"  생존 달성률: {achievement_info['step_achievement']:.1%}")
                print(f"  킬 달성률: {achievement_info['kill_achievement']:.1%}")
                
                return {
                    'stage_changed': False,
                    'training_complete': True,
                    'reason': self.completion_reason,
                    'achievement': achievement_info,
                }
            else:
                # 중간 단계 목표 달성 → 다음 단계로
                return self._advance_stage(achievement_info, forced=False)
        
        # 아직 목표 미달성
        return {
            'stage_changed': False,
            'training_complete': False,
            'achievement': achievement_info,
        }
    
    def _calculate_achievement(self) -> Dict:
        """현재 달성률 계산"""
        if len(self.recent_steps) == 0:
            return {
                'goal_achieved': False,
                'step_achievement': 0.0,
                'kill_achievement': 0.0,
                'overall_achievement': 0.0,
                'avg_steps': 0,
                'avg_kills': 0.0,
            }
        
        current_stage = self.get_current_stage()
        avg_steps = np.mean(self.recent_steps)
        avg_kills = np.mean(self.recent_kills)
        
        step_achievement = avg_steps / current_stage.target_steps
        kill_achievement = avg_kills / current_stage.target_kills if current_stage.target_kills > 0 else 1.0
        
        # 전체 달성률: 두 지표의 평균
        overall_achievement = (step_achievement + kill_achievement) / 2.0
        
        # 목표 달성: 둘 다 threshold 이상
        goal_achieved = (
            step_achievement >= current_stage.success_threshold and
            kill_achievement >= current_stage.success_threshold
        )
        
        return {
            'goal_achieved': goal_achieved,
            'step_achievement': step_achievement,
            'kill_achievement': kill_achievement,
            'overall_achievement': overall_achievement,
            'avg_steps': avg_steps,
            'avg_kills': avg_kills,
        }
    
    def _advance_stage(self, achievement_info: Dict, forced: bool) -> Dict:
        """다음 단계로 전환"""
        current_stage = self.get_current_stage()
        
        # 현재 단계 통계 저장
        self._save_stage_history(achievement_info)
        
        # 마지막 단계라면 전환 불가 (이미 is_final 체크했으므로 여기 오면 안 됨)
        if self.current_stage_idx >= len(self.stages) - 1:
            return {
                'stage_changed': False,
                'training_complete': False,
                'achievement': achievement_info,
            }
        
        # 다음 단계 정보
        next_stage_idx = self.current_stage_idx + 1
        next_stage = self.stages[next_stage_idx]
        
        # 전환 로그
        print(f"\n{'⚠️' if forced else '🎯'} 단계 전환!")
        if forced:
            print(f"   사유: 최대 에피소드 도달 (강제 전환)")
        else:
            print(f"   사유: 목표 달성")
        print(f"   {current_stage.name} (skill {current_stage.skill_level:.1f}) → {next_stage.name} (skill {next_stage.skill_level:.1f})")
        print(f"   에피소드: {self.stage_episode_count}회")
        print(f"   생존: {achievement_info['avg_steps']:.1f}/{current_stage.target_steps} ({achievement_info['step_achievement']:.1%})")
        print(f"   킬: {achievement_info['avg_kills']:.1f}/{current_stage.target_kills:.1f} ({achievement_info['kill_achievement']:.1%})")
        
        # 단계 전환
        self.current_stage_idx = next_stage_idx
        self.stage_episode_count = 0
        
        # 새 단계의 윈도우 크기로 버퍼 재설정
        self.recent_steps = deque(maxlen=next_stage.window_size)
        self.recent_kills = deque(maxlen=next_stage.window_size)
        
        return {
            'stage_changed': True,
            'training_complete': False,
            'achievement': achievement_info,
            'new_stage': next_stage.name,
            'new_skill': next_stage.skill_level,
        }
    
    def _save_stage_history(self, achievement_info: Dict):
        """현재 단계 통계 저장"""
        current_stage = self.get_current_stage()
        
        self.stage_history.append({
            'stage_idx': self.current_stage_idx,
            'stage_name': current_stage.name,
            'skill_level': current_stage.skill_level,
            'episodes': self.stage_episode_count,
            'avg_steps': achievement_info['avg_steps'],
            'avg_kills': achievement_info['avg_kills'],
            'target_steps': current_stage.target_steps,
            'target_kills': current_stage.target_kills,
            'step_achievement': achievement_info['step_achievement'],
            'kill_achievement': achievement_info['kill_achievement'],
            'overall_achievement': achievement_info['overall_achievement'],
        })
    
    def skill_for_episode(self, episode_index: int) -> Tuple[float, str]:
        """현재 스테이지의 skill_level과 이름 반환 (호환성)"""
        current_stage = self.get_current_stage()
        return current_stage.skill_level, current_stage.name
    
    def get_progress_info(self) -> Dict:
        """현재 진행 상황 정보 반환"""
        current_stage = self.get_current_stage()
        achievement = self._calculate_achievement()
        
        info = {
            'current_stage_idx': self.current_stage_idx,
            'total_stages': len(self.stages),
            'stage_name': current_stage.name,
            'skill_level': current_stage.skill_level,
            'is_final_stage': current_stage.is_final,
            'stage_episodes': self.stage_episode_count,
            'total_episodes': self.total_episode_count,
            'min_episodes': current_stage.min_episodes,
            'max_episodes': current_stage.max_episodes,
            'training_complete': self.training_complete,
        }
        
        if achievement['avg_steps'] > 0:
            info.update({
                'recent_avg_steps': achievement['avg_steps'],
                'recent_avg_kills': achievement['avg_kills'],
                'target_steps': current_stage.target_steps,
                'target_kills': current_stage.target_kills,
                'step_achievement': achievement['step_achievement'],
                'kill_achievement': achievement['kill_achievement'],
                'overall_achievement': achievement['overall_achievement'],
                'goal_achieved': achievement['goal_achieved'],
            })
        
        return info
    
    def print_stage_summary(self):
        """전체 단계별 통계 출력"""
        if not self.stage_history:
            return
        
        print("\n" + "="*80)
        print("📊 커리큘럼 단계별 학습 통계")
        print("="*80)
        
        for stat in self.stage_history:
            step_pct = stat['step_achievement'] * 100
            kill_pct = stat['kill_achievement'] * 100
            overall_pct = stat['overall_achievement'] * 100
            
            status = "✅ 달성" if stat['overall_achievement'] >= 0.8 else "⚠️ 미달"
            
            print(f"\n🎓 {stat['stage_name']} (Skill {stat['skill_level']:.1f}) {status}")
            print(f"   에피소드: {stat['episodes']}회")
            print(f"   생존: {stat['avg_steps']:.1f} / {stat['target_steps']} ({step_pct:.1f}%)")
            print(f"   킬: {stat['avg_kills']:.1f} / {stat['target_kills']:.1f} ({kill_pct:.1f}%)")
            print(f"   종합 달성률: {overall_pct:.1f}%")
        
        print("\n" + "="*80)
        print(f"총 에피소드: {self.total_episode_count}회")
        
        if self.training_complete:
            print(f"훈련 상태: ✅ 완료")
            print(f"완료 사유: {self.completion_reason}")
        else:
            print(f"훈련 상태: 🔄 진행 중")
        
        print("="*80)
    
    def should_continue_training(self) -> bool:
        """훈련을 계속해야 하는지 확인 (외부에서 호출)"""
        return not self.training_complete

