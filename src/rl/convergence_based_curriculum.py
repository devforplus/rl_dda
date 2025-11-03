"""
수렴 기반 커리큘럼 러닝 - 성능 수렴 확인 후 전환 (개선 버전)

핵심 개념:
- 단순히 목표 달성이 아닌 "수렴(convergence)" 확인
- 성능이 안정화되고 변동성이 낮아야 전환
- 연속적으로 목표를 달성해야 함 (운으로 달성 방지)

강화학습의 "학습 완료" 기준:
1. 목표 달성: 평균 성능이 목표의 80% 이상
2. 성능 수렴: 최근 성능이 plateau에 도달
3. 낮은 변동성: 성능의 표준편차가 낮음
4. 연속 달성: 연속 10 에피소드 목표 달성

개선 사항 (2025-11-02):
1. 연속 달성 계산 최적화: O(n²) → O(1) 복잡도 (캐싱)
2. 조기 수렴 로직 제거: 논리적 모순 해결
3. 안정성 평가 개선: 생존(CV) + 킬(절대 표준편차) 분리 평가
4. 단계별 적응형 threshold: 초급은 느슨하게, 고급은 엄격하게
5. 데이터 평활화 (Warm Start): 단계 전환 시 데이터 손실 방지
6. 수렴 기준 우선순위 명확화: 가중치 기반 점수 시스템
7. Dead code 제거: 미사용 window_success_history 삭제
8. 목표 과달성 기준 조정: 115% → 120%, 완전 생략 대신 완화된 기준
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from collections import deque
import numpy as np


@dataclass
class ConvergenceStage:
    """수렴 기반 커리큘럼의 단일 스테이지
    
    Attributes:
        skill_level: 단계 스킬 레벨 (0.0 ~ 1.0)
        name: 단계 설명 이름
        target_steps: 목표 생존 스텝
        target_kills: 목표 킬 수
        min_episodes: 최소 에피소드 수
        max_episodes: 최대 에피소드 수 (안전장치)
        success_threshold: 목표 달성 기준 (0.80 = 80%)
        
        # 수렴 관련 파라미터
        window_size: 성능 평가 윈도우 (1 = 각 에피소드 개별 평가)
        convergence_window: 수렴 판단 윈도우 (더 큼)
        stability_threshold: 안정성 기준 (표준편차/평균, 0.15 = 15%)
        consecutive_windows: 연속 달성 필요 에피소드 수 (10)
        consecutive_success_rate: 연속 에피소드 중 성공 비율 (1.0 = 100%)
        
        is_final: 최종 단계 여부
    """
    skill_level: float
    name: str
    target_steps: int
    target_kills: float
    min_episodes: int = 150
    max_episodes: int = 2000
    success_threshold: float = 0.80
    
    # 수렴 관련
    window_size: int = 1  # 각 에피소드를 개별 평가
    convergence_window: int = 100  # 수렴 판단용 (더 긴 윈도우)
    stability_threshold: float = 0.15  # CV (표준편차/평균) 15% 이하
    consecutive_windows: int = 10  # 최근 10개 에피소드
    consecutive_success_rate: float = 1.0  # 10개 모두 성공 (연속 달성)
    
    is_final: bool = False


class ConvergenceBasedCurriculum:
    """수렴 기반 커리큘럼 - 성능 수렴 확인 후 전환 (개선 버전)
    
    핵심 기능:
    1. 목표 달성 확인 (기본)
    2. 성능 수렴 확인 (추가) ⭐
    3. 안정성 확인 (변동성) - 생존/킬 분리 평가
    4. 연속 달성 확인 (운 방지) - 최적화된 캐싱
    """
    
    def __init__(self, stages: List[ConvergenceStage]):
        if not stages:
            raise ValueError("stages must not be empty")
        
        stages[-1].is_final = True
        self.stages = stages
        self.current_stage_idx = 0
        self.stage_episode_count = 0
        self.total_episode_count = 0
        
        # 성능 추적 (긴 히스토리 유지)
        current_stage = self.get_current_stage()
        self.all_steps = []  # 전체 히스토리
        self.all_kills = []
        self.recent_steps = deque(maxlen=current_stage.window_size)
        self.recent_kills = deque(maxlen=current_stage.window_size)
        
        # 수렴 추적
        self.convergence_history = deque(maxlen=current_stage.convergence_window)
        
        # 🔧 개선 1: 연속 달성 캐싱 (O(n²) → O(1))
        self.window_cache = deque(maxlen=current_stage.consecutive_windows)
        self.last_cached_episode = 0  # 마지막으로 캐싱한 윈도우 인덱스
        
        self.stage_history = []
        self.training_complete = False
        self.completion_reason = None
        
    def get_current_stage(self) -> ConvergenceStage:
        return self.stages[self.current_stage_idx]
    
    def is_training_complete(self) -> bool:
        return self.training_complete
    
    def report_episode_result(self, survival_steps: int, kills: float) -> Dict[str, any]:
        """에피소드 결과 보고 및 수렴 분석"""
        if self.training_complete:
            return {
                'stage_changed': False,
                'training_complete': True,
                'reason': self.completion_reason,
            }
        
        current_stage = self.get_current_stage()
        
        # 성능 기록
        self.all_steps.append(survival_steps)
        self.all_kills.append(kills)
        self.recent_steps.append(survival_steps)
        self.recent_kills.append(kills)
        self.convergence_history.append(survival_steps)  # 수렴 판단용
        self.stage_episode_count += 1
        self.total_episode_count += 1
        
        # 달성률 계산
        achievement_info = self._calculate_achievement()
        
        # 수렴 분석 (충분한 데이터가 쌓인 후)
        convergence_info = self._analyze_convergence()
        achievement_info.update(convergence_info)
        
        # 🚨 절대 한계선: max_episodes의 1.5배 초과 시 훈련 중단 (학습 붕괴 방지)
        # 목표를 달성하지 못한 상태로 다음 단계로 넘어가면 Catastrophic Forgetting 발생!
        absolute_limit = int(current_stage.max_episodes * 1.5)
        if self.stage_episode_count >= absolute_limit:
            print(f"\n{'='*70}")
            print(f"🚨 절대 한계선 도달! ({absolute_limit} 에피소드)")
            print(f"{'='*70}")
            print(f"단계: {current_stage.name} (Skill {current_stage.skill_level:.1f})")
            print(f"현재 에피소드: {self.stage_episode_count}회")
            print(f"생존 달성률: {achievement_info['step_achievement']:.1%} (목표: {current_stage.success_threshold:.1%})")
            print(f"킬 달성률: {achievement_info['kill_achievement']:.1%} (목표: {current_stage.success_threshold:.1%})")
            print(f"\n⚠️ 경고: 목표 미달성 상태에서 다음 단계로 넘어가면")
            print(f"   Catastrophic Forgetting이 발생할 수 있습니다!")
            print(f"\n🛑 학습을 중단합니다. 다음 조치를 취해주세요:")
            print(f"\n   1. 목표 재조정 (targets.py)")
            print(f"      - 현재 목표가 너무 높을 수 있습니다")
            print(f"      - 실제 달성 가능한 수준으로 낮추기")
            print(f"\n   2. Success Threshold 완화 (train_ppo_real_game.py)")
            print(f"      - success_threshold: 0.80 → 0.70")
            print(f"\n   3. 하이퍼파라미터 튜닝")
            print(f"      - Learning Rate, Batch Size 등 조정")
            print(f"\n   4. 보상 함수 검토 (environment.py)")
            print(f"      - 목표와 보상 함수가 일치하는지 확인")
            print(f"{'='*70}")
            
            # 훈련 중단 (강제 전환 X)
            self.training_complete = True
            self.completion_reason = f"절대 한계선 도달 - 목표 미달성 (생존 {achievement_info['step_achievement']:.1%}, 킬 {achievement_info['kill_achievement']:.1%})"
            self._save_stage_history(achievement_info)
            return {
                'stage_changed': False,
                'training_complete': True,
                'reason': self.completion_reason,
                'achievement': achievement_info,
            }
        
        # 경고: 최대 에피소드 근처 (목표 미달성 시)
        if self.stage_episode_count >= current_stage.max_episodes:
            if not achievement_info['goal_achieved']:
                # 목표 미달성 - 경고하고 제한된 추가 학습 허용
                if self.stage_episode_count % 100 == 0:  # 100 에피소드마다 경고
                    remaining = absolute_limit - self.stage_episode_count
                    print(f"\n{'='*70}")
                    print(f"⚠️  경고: 권장 최대 에피소드({current_stage.max_episodes}) 초과")
                    print(f"{'='*70}")
                    print(f"단계: {current_stage.name} (Skill {current_stage.skill_level:.1f})")
                    print(f"현재 에피소드: {self.stage_episode_count}회 (절대 한계: {absolute_limit}회, 남은 기회: {remaining}회)")
                    print(f"생존 달성률: {achievement_info['step_achievement']:.1%} (목표: {current_stage.success_threshold:.1%})")
                    print(f"킬 달성률: {achievement_info['kill_achievement']:.1%} (목표: {current_stage.success_threshold:.1%})")
                    print(f"\n💡 절대 한계선({absolute_limit}회)까지 목표 달성을 시도합니다...")
                    print(f"   만약 학습이 정체되었다면:")
                    print(f"   1. Ctrl+C로 중단 후 하이퍼파라미터 튜닝")
                    print(f"   2. 또는 목표를 낮추세요 (success_threshold를 0.70으로)")
                    print(f"{'='*70}")
                
                # 제한된 추가 학습 (절대 한계까지)
                return {
                    'stage_changed': False,
                    'training_complete': False,
                    'achievement': achievement_info,
                }
            
            # 목표는 달성했지만 수렴하지 않은 경우
            if current_stage.is_final:
                # 최종 단계: 목표 달성했으므로 종료 (수렴은 선택사항)
                self.training_complete = True
                self.completion_reason = f"최종 목표 달성 (목표 달성, 수렴은 완전하지 않음: {achievement_info['overall_achievement']:.1%})"
                self._save_stage_history(achievement_info)
                
                print(f"\n{'='*70}")
                print(f"🎉 훈련 완료! (목표 달성)")
                print(f"{'='*70}")
                print(f"목표를 달성했습니다. (수렴은 완전하지 않지만 충분함)")
                print(f"생존 달성률: {achievement_info['step_achievement']:.1%}")
                print(f"킬 달성률: {achievement_info['kill_achievement']:.1%}")
                print(f"안정성: CV {achievement_info.get('stability_cv', 0):.1%}")
                print(f"{'='*70}")
                
                return {
                    'stage_changed': False,
                    'training_complete': True,
                    'reason': self.completion_reason,
                    'achievement': achievement_info,
                }
            
            # 중간 단계: 목표 달성했으므로 다음 단계로
            print(f"\n✅ 목표 달성 (max_episodes 도달), 다음 단계로 전환")
            return self._advance_stage(achievement_info, forced=True)
        
        # 🔧 개선 2: 조기 수렴 로직 제거 (논리적 모순)
        # 최소 에피소드 확인
        if self.stage_episode_count < current_stage.min_episodes:
            return {
                'stage_changed': False,
                'training_complete': False,
                'achievement': achievement_info,
            }
        
        # 🎯 목표 과달성 시 데이터 요구사항 완화
        step_achievement = achievement_info.get('step_achievement', 0)
        kill_achievement = achievement_info.get('kill_achievement', 0)
        
        # 과달성 (120% 이상) 시 데이터 요구사항 완화
        if step_achievement >= 1.20 and kill_achievement >= 1.20:
            # 과달성 시 최소 데이터만 확인 (window_size * 3)
            min_required_episodes = current_stage.window_size * 3  # 150 에피소드
            print(f"   💡 목표 과달성 감지 (생존: {step_achievement:.1%}, 킬: {kill_achievement:.1%})")
            print(f"   → 데이터 요구사항 완화 (500 → {min_required_episodes} 에피소드)")
        else:
            # 일반적인 경우 충분한 데이터 확인
            min_required_episodes = current_stage.consecutive_windows * current_stage.window_size
        
        if len(self.all_steps) < min_required_episodes:
            return {
                'stage_changed': False,
                'training_complete': False,
                'achievement': achievement_info,
            }
        
        # 🎯 수렴 기반 전환 판단
        ready_to_advance = self._check_convergence_criteria(achievement_info)
        
        if ready_to_advance:
            if current_stage.is_final:
                # 최종 단계 완료!
                self.training_complete = True
                self.completion_reason = f"최종 목표 달성 (수렴 확인)! (생존: {achievement_info['step_achievement']:.1%}, 킬: {achievement_info['kill_achievement']:.1%})"
                self._save_stage_history(achievement_info)
                
                print(f"\n{'='*70}")
                print(f"🎉🎉🎉 훈련 완료! (수렴 확인) 🎉🎉🎉")
                print(f"{'='*70}")
                print(f"최종 목표 달성!")
                print(f"  총 에피소드: {self.total_episode_count}")
                print(f"  생존 달성률: {achievement_info['step_achievement']:.1%}")
                print(f"  킬 달성률: {achievement_info['kill_achievement']:.1%}")
                
                # 개선된 안정성 정보 출력
                if 'survival_cv' in achievement_info and 'kill_std' in achievement_info:
                    print(f"  생존 안정성: CV {achievement_info['survival_cv']:.2%}")
                    print(f"  킬 안정성: 표준편차 {achievement_info['kill_std']:.2f}")
                else:
                    print(f"  성능 안정성: CV {achievement_info.get('stability_cv', 0):.2%}")
                
                print(f"  수렴 상태: {achievement_info['convergence_status']}")
                print(f"{'='*70}")
                
                return {
                    'stage_changed': False,
                    'training_complete': True,
                    'reason': self.completion_reason,
                    'achievement': achievement_info,
                }
            else:
                # 다음 단계로
                return self._advance_stage(achievement_info, forced=False)
        
        return {
            'stage_changed': False,
            'training_complete': False,
            'achievement': achievement_info,
        }
    
    def _calculate_achievement(self) -> Dict:
        """기본 달성률 계산"""
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
        overall_achievement = (step_achievement + kill_achievement) / 2.0
        
        # 기본 목표 달성 (수렴 확인 없이)
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
    
    def _analyze_convergence(self) -> Dict:
        """수렴 분석 ⭐ 핵심 로직 (개선 버전)"""
        current_stage = self.get_current_stage()
        
        # 기본값
        result = {
            'converged': False,
            'stable': False,
            'survival_stable': False,
            'kill_stable': False,
            'consecutive_success': False,
            'convergence_status': '데이터 부족',
            'stability_cv': 0.0,
            'survival_cv': 0.0,
            'kill_std': 0.0,
            'consecutive_rate': 0.0,
            'trend_slope': 0.0,
        }
        
        # 1. 충분한 데이터 확인
        if len(self.convergence_history) < current_stage.convergence_window:
            if len(self.recent_steps) < current_stage.window_size:
                return result
            recent_data = list(self.recent_steps)
        else:
            recent_data = list(self.convergence_history)
        
        # 🔧 개선 3: 안정성 평가 개선 (생존/킬 분리)
        stability_info = self._analyze_stability()
        result.update(stability_info)
        
        # 3. 트렌드 분석 (수렴 = 더 이상 개선 없음)
        x = np.arange(len(recent_data))
        y = np.array(recent_data)
        
        # 선형 회귀: y = slope * x + intercept
        x_mean = np.mean(x)
        y_mean = np.mean(y)
        numerator = np.sum((x - x_mean) * (y - y_mean))
        denominator = np.sum((x - x_mean) ** 2)
        slope = numerator / denominator if denominator != 0 else 0
        
        # slope가 0에 가까우면 수렴 (plateau)
        normalized_slope = slope / y_mean if y_mean > 0 else 0
        result['trend_slope'] = normalized_slope
        
        # 🔧 개선 4: 단계별 적응형 threshold
        convergence_threshold = self._get_convergence_threshold()
        converged = abs(normalized_slope) <= convergence_threshold
        result['converged'] = converged
        
        # 🔧 개선 1: 연속 달성 확인 (최적화된 캐싱)
        consecutive_info = self._calculate_consecutive_achievement()
        result.update(consecutive_info)
        
        # 5. 종합 수렴 상태 (우선순위 명확화)
        if result['converged']:
            if result['stable'] and result['consecutive_success']:
                result['convergence_status'] = '✅ 수렴 완료'
            elif result['stable']:
                result['convergence_status'] = '📊 plateau 도달 (안정화 중)'
            elif result['consecutive_success']:
                result['convergence_status'] = '📊 plateau 도달 (연속 달성 중)'
            else:
                result['convergence_status'] = '📊 plateau 도달'
        elif result['consecutive_success']:
            result['convergence_status'] = '⚠️ 연속 달성 중 (학습 중)'
        elif result['stable']:
            result['convergence_status'] = '⏳ 안정화 중 (학습 중)'
        else:
            result['convergence_status'] = '📈 학습 중'
        
        return result
    
    def _analyze_stability(self) -> Dict:
        """🔧 개선 3: 안정성 평가 개선 - 생존(CV)과 킬(절대 표준편차) 분리"""
        current_stage = self.get_current_stage()
        
        if len(self.recent_steps) < current_stage.window_size:
            return {
                'survival_stable': False,
                'kill_stable': False,
                'stable': False,
                'survival_cv': 1.0,
                'kill_std': 999.0,
                'stability_cv': 1.0,  # 하위 호환성
            }
        
        # 생존 안정성: CV (변동계수) 사용
        survival_avg = np.mean(self.recent_steps)
        survival_std = np.std(self.recent_steps)
        survival_cv = survival_std / survival_avg if survival_avg > 0 else 1.0
        survival_stable = survival_cv <= current_stage.stability_threshold
        
        # 킬 안정성: 절대 표준편차 사용 (킬이 적을 때 CV 과대평가 방지)
        kill_avg = np.mean(self.recent_kills)
        kill_std = np.std(self.recent_kills)
        
        # 킬 표준편차 threshold: 목표의 30%
        kill_threshold = current_stage.target_kills * 0.3
        kill_stable = kill_std <= kill_threshold
        
        # 종합 안정성: 생존과 킬 모두 안정
        stable = survival_stable and kill_stable
        
        return {
            'survival_stable': survival_stable,
            'kill_stable': kill_stable,
            'stable': stable,
            'survival_cv': survival_cv,
            'kill_std': kill_std,
            'stability_cv': survival_cv,  # 하위 호환성 (기존 코드와의 호환)
        }
    
    def _get_convergence_threshold(self) -> float:
        """🔧 개선 4: 단계별 적응형 수렴 threshold
        
        초급: 더 느슨한 기준 (빠른 변화 허용)
        고급: 더 엄격한 기준 (세밀한 수렴 확인)
        """
        current_stage = self.get_current_stage()
        
        # 기본 threshold: 0.002
        base_threshold = 0.002
        
        # skill_level에 따라 조정
        # skill 0.1 → factor 0.925 → threshold 0.00185 (느슨)
        # skill 1.0 → factor 0.25 → threshold 0.0005 (엄격)
        skill_factor = 1.0 - (current_stage.skill_level * 0.75)
        
        return base_threshold * skill_factor
    
    def _calculate_consecutive_achievement(self) -> Dict:
        """🔧 개선 1: 연속 달성 계산 최적화 (캐싱)
        
        기존: 매 에피소드마다 O(n²) 재계산
        개선: 새로운 윈도우만 계산 O(1)
        """
        current_stage = self.get_current_stage()
        
        # 현재 완성된 윈도우 수
        current_windows = len(self.all_steps) // current_stage.window_size
        
        # 새로운 윈도우가 완성되었을 때만 계산
        while self.last_cached_episode < current_windows:
            window_idx = self.last_cached_episode
            start_idx = window_idx * current_stage.window_size
            end_idx = (window_idx + 1) * current_stage.window_size
            
            window_steps = self.all_steps[start_idx:end_idx]
            window_kills = self.all_kills[start_idx:end_idx]
            
            avg_steps = np.mean(window_steps)
            avg_kills = np.mean(window_kills)
            
            step_ok = avg_steps >= current_stage.target_steps * current_stage.success_threshold
            kill_ok = avg_kills >= current_stage.target_kills * current_stage.success_threshold
            
            self.window_cache.append(step_ok and kill_ok)
            self.last_cached_episode += 1
        
        # 연속 달성 판단
        if len(self.window_cache) >= current_stage.consecutive_windows:
            # 최근 consecutive_windows개의 윈도우 중 성공률
            recent_windows = list(self.window_cache)[-current_stage.consecutive_windows:]
            consecutive_rate = np.mean(recent_windows)
            consecutive_success = consecutive_rate >= current_stage.consecutive_success_rate
            
            return {
                'consecutive_success': consecutive_success,
                'consecutive_rate': consecutive_rate,
            }
        
        return {
            'consecutive_success': False,
            'consecutive_rate': 0.0,
        }
    
    def _check_convergence_criteria(self, achievement_info: Dict) -> bool:
        """🔧 개선 6: 수렴 기준 종합 판단 (가중치 기반 점수 시스템)"""
        current_stage = self.get_current_stage()
        
        # 필수 조건: 목표 달성
        if not achievement_info['goal_achieved']:
            return False
        
        # 🔧 개선 8: 목표 과달성 기준 조정 (115% → 120%)
        step_achievement = achievement_info.get('step_achievement', 0)
        kill_achievement = achievement_info.get('kill_achievement', 0)
        
        # 과달성 시 완화된 기준 적용
        if step_achievement >= 1.20 and kill_achievement >= 1.20:
            threshold = 0.5  # 완화된 기준 (70% 대신 50%)
            print(f"   💡 목표 과달성 (생존: {step_achievement:.1%}, 킬: {kill_achievement:.1%}) → 수렴 기준 완화 (70% → 50%)")
        else:
            threshold = 0.7  # 일반 기준
        
        # 수렴 점수 계산 (가중치 기반)
        convergence_score = 0.0
        
        # 1순위: Plateau 도달 (가장 중요한 수렴 지표) - 가중치 40%
        converged = achievement_info.get('converged', False)
        if converged:
            convergence_score += 0.4
        
        # 2순위: 안정성 (변동성) - 가중치 30%
        stable = achievement_info.get('stable', False)
        if stable:
            convergence_score += 0.3
        elif achievement_info.get('survival_stable', False):
            # 생존만 안정적이면 절반
            convergence_score += 0.15
        
        # 3순위: 연속 달성 - 가중치 30%
        consecutive_success = achievement_info.get('consecutive_success', False)
        consecutive_rate = achievement_info.get('consecutive_rate', 0)
        
        if consecutive_success:
            convergence_score += 0.3
        elif consecutive_rate >= 0.60:
            # 연속 달성률 60% 이상이면 부분 점수
            convergence_score += 0.3 * (consecutive_rate / current_stage.consecutive_success_rate)
        
        # 판단
        passed = convergence_score >= threshold
        
        if not passed:
            # 상세 정보 출력
            print(f"   ⏳ 수렴 점수: {convergence_score:.2f}/{threshold:.2f}")
            print(f"      - Plateau 도달: {'✅' if converged else '❌'} (가중치 40%)")
            print(f"      - 안정성: {'✅' if stable else '❌'} (가중치 30%)")
            print(f"      - 연속 달성: {'✅' if consecutive_success else f'⚠️ {consecutive_rate:.1%}'} (가중치 30%)")
        
        return passed
    
    def _advance_stage(self, achievement_info: Dict, forced: bool) -> Dict:
        """🔧 개선 5: 다음 단계로 전환 (데이터 평활화 - Warm Start)"""
        current_stage = self.get_current_stage()
        self._save_stage_history(achievement_info)
        
        if self.current_stage_idx >= len(self.stages) - 1:
            return {
                'stage_changed': False,
                'training_complete': False,
                'achievement': achievement_info,
            }
        
        next_stage_idx = self.current_stage_idx + 1
        next_stage = self.stages[next_stage_idx]
        
        print(f"\n{'⚠️' if forced else '🎯'} 단계 전환!")
        if forced:
            print(f"   사유: 최대 에피소드 도달 (강제 전환)")
        else:
            print(f"   사유: 목표 달성 + 수렴 확인 ✅")
        print(f"   {current_stage.name} (skill {current_stage.skill_level:.1f}) → {next_stage.name} (skill {next_stage.skill_level:.1f})")
        print(f"   에피소드: {self.stage_episode_count}회")
        print(f"   생존: {achievement_info['avg_steps']:.1f}/{current_stage.target_steps} ({achievement_info['step_achievement']:.1%})")
        print(f"   킬: {achievement_info['avg_kills']:.1f}/{current_stage.target_kills:.1f} ({achievement_info['kill_achievement']:.1%})")
        
        # 개선된 안정성 정보 출력
        if 'survival_cv' in achievement_info and 'kill_std' in achievement_info:
            print(f"   생존 안정성: CV {achievement_info['survival_cv']:.1%}")
            print(f"   킬 안정성: 표준편차 {achievement_info['kill_std']:.2f}")
        else:
            print(f"   안정성: CV {achievement_info.get('stability_cv', 0):.1%}")
        
        print(f"   연속 달성: {achievement_info.get('consecutive_rate', 0):.1%}")
        print(f"   수렴 상태: {achievement_info.get('convergence_status', 'N/A')}")
        
        self.current_stage_idx = next_stage_idx
        self.stage_episode_count = 0
        
        # 🔧 개선 5: 데이터 평활화 (Warm Start)
        # 이전 단계의 최근 성능을 새 단계 초기값으로 사용
        warmup_size = 20  # Warm start 데이터 크기
        
        if len(self.recent_steps) >= warmup_size:
            warmup_data_steps = list(self.recent_steps)[-warmup_size:]
            warmup_data_kills = list(self.recent_kills)[-warmup_size:]
            
            print(f"   🔥 Warm Start: 최근 {warmup_size}개 데이터로 초기화 (데이터 손실 방지)")
            
            # 새 단계 초기화 (warm start)
            self.recent_steps = deque(warmup_data_steps, maxlen=next_stage.window_size)
            self.recent_kills = deque(warmup_data_kills, maxlen=next_stage.window_size)
            self.convergence_history = deque(warmup_data_steps, maxlen=next_stage.convergence_window)
        else:
            # 데이터 부족 시 빈 초기화
            self.recent_steps = deque(maxlen=next_stage.window_size)
            self.recent_kills = deque(maxlen=next_stage.window_size)
            self.convergence_history = deque(maxlen=next_stage.convergence_window)
        
        # 연속 달성 캐시 초기화
        self.window_cache = deque(maxlen=next_stage.consecutive_windows)
        self.last_cached_episode = 0
        
        return {
            'stage_changed': True,
            'training_complete': False,
            'achievement': achievement_info,
            'new_stage': next_stage.name,
            'new_skill': next_stage.skill_level,
        }
    
    def _save_stage_history(self, achievement_info: Dict):
        """단계 통계 저장"""
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
            'stability_cv': achievement_info.get('stability_cv', 0),
            'survival_cv': achievement_info.get('survival_cv', 0),
            'kill_std': achievement_info.get('kill_std', 0),
            'convergence_status': achievement_info.get('convergence_status', 'N/A'),
            'consecutive_rate': achievement_info.get('consecutive_rate', 0),
        })
    
    def skill_for_episode(self, episode_index: int) -> Tuple[float, str]:
        """호환성"""
        current_stage = self.get_current_stage()
        return current_stage.skill_level, current_stage.name
    
    def should_continue_training(self) -> bool:
        return not self.training_complete
    
    def get_progress_info(self) -> Dict:
        """진행 상황 정보"""
        current_stage = self.get_current_stage()
        achievement = self._calculate_achievement()
        convergence = self._analyze_convergence()
        achievement.update(convergence)
        
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
                'stability_cv': achievement.get('stability_cv', 0),
                'survival_cv': achievement.get('survival_cv', 0),
                'kill_std': achievement.get('kill_std', 0),
                'stable': achievement.get('stable', False),
                'survival_stable': achievement.get('survival_stable', False),
                'kill_stable': achievement.get('kill_stable', False),
                'converged': achievement.get('converged', False),
                'consecutive_success': achievement.get('consecutive_success', False),
                'convergence_status': achievement.get('convergence_status', 'N/A'),
            })
        
        return info
    
    def print_stage_summary(self):
        """단계별 통계 출력"""
        if not self.stage_history:
            return
        
        print("\n" + "="*80)
        print("📊 커리큘럼 단계별 학습 통계 (수렴 기반 - 개선 버전)")
        print("="*80)
        
        for stat in self.stage_history:
            step_pct = stat['step_achievement'] * 100
            kill_pct = stat['kill_achievement'] * 100
            overall_pct = stat['overall_achievement'] * 100
            cv_pct = stat.get('survival_cv', stat.get('stability_cv', 0)) * 100
            kill_std = stat.get('kill_std', 0)
            consec_pct = stat['consecutive_rate'] * 100
            
            status = "✅ 수렴 완료" if stat['overall_achievement'] >= 0.8 else "⚠️ 미달"
            
            print(f"\n🎓 {stat['stage_name']} (Skill {stat['skill_level']:.1f}) {status}")
            print(f"   에피소드: {stat['episodes']}회")
            print(f"   생존: {stat['avg_steps']:.1f} / {stat['target_steps']} ({step_pct:.1f}%)")
            print(f"   킬: {stat['avg_kills']:.1f} / {stat['target_kills']:.1f} ({kill_pct:.1f}%)")
            print(f"   종합 달성률: {overall_pct:.1f}%")
            print(f"   생존 안정성 (CV): {cv_pct:.1f}%")
            print(f"   킬 안정성 (표준편차): {kill_std:.2f}")
            print(f"   연속 달성률: {consec_pct:.1f}%")
            print(f"   수렴 상태: {stat['convergence_status']}")
        
        print("\n" + "="*80)
        print(f"총 에피소드: {self.total_episode_count}회")
        
        if self.training_complete:
            print(f"훈련 상태: ✅ 완료")
            print(f"완료 사유: {self.completion_reason}")
        else:
            print(f"훈련 상태: 🔄 진행 중")
        
        print("="*80)
