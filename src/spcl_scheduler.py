"""
Self-Paced Curriculum Learning (SPCL) 스케줄러 v2.1

탄막 슈팅 게임 강화학습을 위한 SPCL 구현
에이전트의 성능에 따라 동적으로 난이도를 조절합니다.

핵심 원리:
- Lambda (λ): 학습 진도를 조절하는 임계값 (허용 가능한 최대 Loss)
- Loss: 각 난이도별 에이전트의 실패율 (1 - 성공률)
- SPCL 조건: Loss(d) < Lambda인 난이도들이 학습 후보가 됨

v2.1 균형 조정:
1. 초기 Lambda: 0.35 (낮은 난이도부터 시작하되 v1보다 적극적)
2. 탐색 단계: 직접 성공률 계산 (정확한 Loss 파악)
3. 마스터리 기준: 80% (95%는 너무 높고 75%는 너무 낮음)
4. Lambda 증가: 0.03씩 (점진적이지만 v1보다 빠름)
5. 난이도별 점진적 Loss 초기화 (높은 난이도는 높은 Loss)
"""

import numpy as np
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass, field


@dataclass
class DifficultyStats:
    """난이도별 통계 추적"""
    difficulty: float
    loss: float = 0.5  # 중립적 초기화 (0.8 → 0.5)
    attempts: int = 0  # 전체 시도 횟수
    successes: int = 0  # 전체 성공 횟수
    recent_successes: int = 0  # 최근 성공 횟수
    recent_attempts: int = 0  # 최근 시도 횟수


class SPCLScheduler:
    """Self-Paced Curriculum Learning 스케줄러 v2
    
    에이전트의 현재 성능에 맞는 난이도를 동적으로 선택합니다.
    
    v2 개선사항:
    1. 탐색 단계: 직접 성공률로 Loss 계산 (EMA 제거)
    2. 학습 단계: 높은 EMA alpha로 빠른 적응
    3. 주기적 전체 평가로 모든 난이도 Loss 갱신
    4. 마스터리 기준 완화 (75%)
    5. Lambda 증가 가속
    
    Args:
        difficulties: 난이도 리스트 (기본: [0.0, 0.1, ..., 1.0])
        initial_lambda: 초기 Lambda 값
        lambda_step: Lambda 증가량
        lambda_decay: Lambda 감소량 (실패 시)
        lambda_max: Lambda 최대값
        lambda_min: Lambda 최소값
        ema_alpha: EMA(지수이동평균) 알파값 (학습 단계용)
        lambda_update_interval: Lambda 업데이트 주기 (에피소드 단위)
        mastery_threshold: 마스터리 판정 성공률
        struggle_threshold: 고전 판정 성공률
        min_attempts_per_difficulty: 탐색 단계에서 각 난이도당 최소 시도 횟수
        min_mastery_attempts: 마스터리 판정에 필요한 최소 시도 횟수
        hard_weight_bonus: 어려운 난이도 샘플링 가중치 보너스
        periodic_eval_interval: 주기적 전체 평가 간격 (에피소드 단위)
    """
    
    def __init__(
        self,
        difficulties: Optional[List[float]] = None,
        initial_lambda: float = 0.35,  # 중간값 (v1:0.15, v2:0.55 → 0.35)
        lambda_step: float = 0.03,  # 중간값 (v1:0.01, v2:0.05 → 0.03)
        lambda_decay: float = 0.02,  # 실패 시 감소량
        lambda_max: float = 1.1,
        lambda_min: float = 0.2,  # 중간값 (v1:0.1, v2:0.3 → 0.2)
        ema_alpha: float = 0.20,  # 학습 단계용 EMA (빠른 적응)
        lambda_update_interval: int = 150,  # 자주 업데이트 (확인 빈도 높임)
        mastery_threshold: float = 0.90,  # 중간값 (v1:0.95, v2:0.75 → 0.80)
        struggle_threshold: float = 0.35,  # 고전 기준
        min_attempts_per_difficulty: int = 100,  # 탐색 시 충분히 (15 → 25)
        min_mastery_attempts: int = 15,  # 마스터리 판정 최소 시도
        hard_weight_bonus: float = 0.4,  # 어려운 난이도 보너스
        periodic_eval_interval: int = 800,  # 주기적 전체 평가 간격
    ):
        # 난이도 리스트 설정 (기본: 0.0 ~ 1.0, 11단계)
        if difficulties is None:
            self.difficulties = [round(i * 0.1, 1) for i in range(11)]
        else:
            self.difficulties = sorted(difficulties)
        
        # Lambda 관련 파라미터
        self.lambda_value = initial_lambda
        self.initial_lambda = initial_lambda
        self.lambda_step = lambda_step
        self.lambda_decay = lambda_decay
        self.lambda_max = lambda_max
        self.lambda_min = lambda_min
        self.lambda_update_interval = lambda_update_interval
        
        # 마스터리 판정 임계값
        self.mastery_threshold = mastery_threshold
        self.struggle_threshold = struggle_threshold
        self.min_mastery_attempts = min_mastery_attempts
        
        # EMA 파라미터
        self.ema_alpha = ema_alpha
        
        # 탐색 단계 설정
        self.min_attempts_per_difficulty = min_attempts_per_difficulty
        self.exploration_phase = True
        
        # 샘플링 가중치 보너스
        self.hard_weight_bonus = hard_weight_bonus
        
        # 주기적 평가 설정
        self.periodic_eval_interval = periodic_eval_interval
        self.last_periodic_eval = 0
        
        # 난이도별 통계 초기화 (난이도에 비례한 점진적 Loss)
        # 핵심: 높은 난이도는 높은 Loss로 시작 → Lambda가 증가해야 학습 가능
        # Loss 최대치 1.0 감안: skill 1.0일 때 Loss = 1.0이 되도록 설정
        self.stats: Dict[float, DifficultyStats] = {}
        for d in self.difficulties:
            # Loss = 0.2 + (난이도 * 0.8)
            # 예: skill 0.0 → Loss 0.2, skill 0.5 → Loss 0.6, skill 1.0 → Loss 1.0
            initial_loss = 0.2 + (d * 0.8)
            self.stats[d] = DifficultyStats(difficulty=d, loss=initial_loss)
        
        # 학습 이력 추적
        self.episode_count = 0
        self.lambda_history: List[float] = [initial_lambda]
        self.selected_difficulties: List[float] = []
        
        # 최근 결과 추적
        self.recent_results: List[Tuple[float, bool]] = []
        self.recent_window: int = 100
        
        # 각 난이도별 최근 결과 추적
        self.difficulty_recent_results: Dict[float, List[bool]] = {
            d: [] for d in self.difficulties
        }
        self.difficulty_recent_window: int = 50  # 더 긴 윈도우 (30 → 50)
        
        # 난이도별 연속 선택 방지 (Coverage 개념)
        self.last_selected_difficulty: float = 0.0
        self.consecutive_same_count: int = 0
        self.max_consecutive_same: int = 10  # 같은 난이도 최대 연속 선택 횟수
    
    def update_performance(self, difficulty: float, success: bool) -> None:
        """에피소드 결과를 반영하여 해당 난이도의 Loss 업데이트
        
        탐색 단계: 직접 성공률로 Loss 계산 (더 정확한 추정)
        학습 단계: EMA로 점진적 업데이트 (안정성)
        
        Args:
            difficulty: 에피소드에서 사용한 난이도 (skill level)
            success: 에피소드 성공 여부
        """
        if difficulty not in self.stats:
            self.stats[difficulty] = DifficultyStats(difficulty=difficulty, loss=0.5)
            self.difficulty_recent_results[difficulty] = []
        
        stats = self.stats[difficulty]
        stats.attempts += 1
        
        if success:
            stats.successes += 1
        
        # 난이도별 최근 결과 추적
        if difficulty not in self.difficulty_recent_results:
            self.difficulty_recent_results[difficulty] = []
        self.difficulty_recent_results[difficulty].append(success)
        if len(self.difficulty_recent_results[difficulty]) > self.difficulty_recent_window:
            self.difficulty_recent_results[difficulty].pop(0)
        
        # Loss 업데이트 방식 선택
        if self.exploration_phase:
            # 탐색 단계: 직접 성공률로 Loss 계산 (더 빠른 수렴)
            if stats.attempts >= 5:  # 최소 5회 이상 시도 후
                success_rate = stats.successes / stats.attempts
                stats.loss = 1.0 - success_rate
        else:
            # 학습 단계: EMA로 점진적 업데이트
            current_loss = 0.0 if success else 1.0
            stats.loss = self.ema_alpha * current_loss + (1 - self.ema_alpha) * stats.loss
        
        # 전역 최근 결과 추적
        self.recent_results.append((difficulty, success))
        if len(self.recent_results) > self.recent_window:
            self.recent_results.pop(0)
        
        self.episode_count += 1
    
    def step_lambda(self) -> Tuple[float, str, Dict]:
        """Lambda 값을 적응적으로 조정
        
        v2.1 수정: 
        - 전체 최근 성공률도 Lambda 증가 조건에 포함
        - 탐색 단계에서는 Lambda 조정 비활성화
        - 평가된 난이도 수가 충분해야 Lambda 증가
        
        Returns:
            (new_lambda, action, details): Lambda, 조정 방향, 상세 정보
        """
        details = {
            "overall_sr": 0.0,
            "mastery_ratio": 0.0,
            "struggling_ratio": 0.0,
            "evaluated_count": 0,
            "mastered_count": 0,
            "struggling_count": 0,
            "reason": "",
        }
        
        # 탐색 단계에서는 Lambda 조정 안 함
        if self.exploration_phase:
            self.lambda_history.append(self.lambda_value)
            details["reason"] = "탐색 단계 (Lambda 고정)"
            return self.lambda_value, "hold", details
        
        if len(self.recent_results) < 30:
            details["reason"] = "데이터 부족 (< 30 에피소드)"
            return self.lambda_value, "hold", details
        
        old_lambda = self.lambda_value
        action = "hold"
        
        # 전체 최근 성공률 확인
        overall_success_rate = self.get_recent_success_rate()
        details["overall_sr"] = overall_success_rate
        
        # 현재 학습 가능한 난이도들
        candidates = self.get_candidate_difficulties()
        
        if not candidates:
            self.lambda_history.append(self.lambda_value)
            details["reason"] = "학습 가능 난이도 없음"
            return self.lambda_value, "hold", details
        
        # 각 후보 난이도의 마스터리 상태 확인
        mastered_count = 0
        struggling_count = 0
        evaluated_count = 0
        
        for difficulty in candidates:
            recent = self.difficulty_recent_results.get(difficulty, [])
            
            # 충분한 데이터가 있는 경우만 평가
            if len(recent) >= self.min_mastery_attempts // 2:
                evaluated_count += 1
                recent_success_rate = sum(recent) / len(recent)
                
                if recent_success_rate >= self.mastery_threshold:
                    mastered_count += 1
                elif recent_success_rate < self.struggle_threshold:
                    struggling_count += 1
        
        details["evaluated_count"] = evaluated_count
        details["mastered_count"] = mastered_count
        details["struggling_count"] = struggling_count
        
        # Lambda 조정 결정
        if evaluated_count > 0:
            mastery_ratio = mastered_count / evaluated_count
            struggling_ratio = struggling_count / evaluated_count
            details["mastery_ratio"] = mastery_ratio
            details["struggling_ratio"] = struggling_ratio
            
            if struggling_ratio > 0.3:
                # 30% 이상이 고전 중 → Lambda 감소
                self.lambda_value = max(self.lambda_value - self.lambda_decay, self.lambda_min)
                action = "down"
                details["reason"] = f"고전 비율 {struggling_ratio*100:.0f}% > 30%"
            elif overall_success_rate < 0.50:
                # 전체 성공률 50% 미만 → Lambda 감소 (완화: 70% → 50%)
                # 높은 난이도가 포함되면 자연스럽게 성공률이 떨어지므로 관대하게 설정
                self.lambda_value = max(self.lambda_value - self.lambda_decay, self.lambda_min)
                action = "down"
                details["reason"] = f"전체SR {overall_success_rate*100:.0f}% < 50%"
            elif mastery_ratio >= 0.7 and overall_success_rate >= 0.70:
                # 70% 이상 마스터 + 전체 성공률 70% 이상 → Lambda 증가
                if evaluated_count >= 3:
                    self.lambda_value = min(self.lambda_value + self.lambda_step, self.lambda_max)
                    action = "up"
                    details["reason"] = f"마스터 {mastery_ratio*100:.0f}%≥70% & 전체SR {overall_success_rate*100:.0f}%≥70%"
                else:
                    details["reason"] = f"평가 난이도 부족 ({evaluated_count}<3)"
            elif mastery_ratio >= 0.5 and overall_success_rate >= 0.60 and struggling_ratio < 0.1:
                # 50% 이상 마스터 + 전체 성공률 60% 이상 + 고전 10% 미만 → 소폭 증가
                if evaluated_count >= 2:
                    self.lambda_value = min(self.lambda_value + self.lambda_step * 0.5, self.lambda_max)
                    action = "up_slow"
                    details["reason"] = f"마스터 {mastery_ratio*100:.0f}%≥50% & 전체SR {overall_success_rate*100:.0f}%≥60%"
                else:
                    details["reason"] = f"평가 난이도 부족 ({evaluated_count}<2)"
            else:
                # Lambda 유지 이유
                reasons = []
                if mastery_ratio < 0.5:
                    reasons.append(f"마스터 {mastery_ratio*100:.0f}%<50%")
                if overall_success_rate < 0.60:
                    reasons.append(f"전체SR {overall_success_rate*100:.0f}%<60%")
                details["reason"] = " & ".join(reasons) if reasons else "조건 미충족"
        else:
            details["reason"] = "평가 가능 난이도 없음"
        
        self.lambda_history.append(self.lambda_value)
        return self.lambda_value, action, details
    
    def get_recent_success_rate(self) -> float:
        """최근 전체 성공률 반환"""
        if not self.recent_results:
            return 0.0
        successes = sum(1 for _, success in self.recent_results if success)
        return successes / len(self.recent_results)
    
    def get_difficulty_mastery_status(self) -> Dict[float, Tuple[float, bool]]:
        """각 난이도의 마스터리 상태 반환"""
        status = {}
        for difficulty in self.difficulties:
            recent = self.difficulty_recent_results.get(difficulty, [])
            if len(recent) >= self.min_mastery_attempts // 2:
                success_rate = sum(recent) / len(recent)
                is_mastered = success_rate >= self.mastery_threshold
            else:
                success_rate = 0.0
                is_mastered = False
            status[difficulty] = (success_rate, is_mastered)
        return status
    
    def select_difficulty(self) -> float:
        """난이도 선택 (탐색 단계 vs 학습 단계)
        
        v2 개선:
        - 학습 단계에서도 주기적으로 미탐색 난이도 선택
        - Coverage 개념 추가 (연속 같은 난이도 방지)
        """
        if self.exploration_phase:
            return self._select_exploration()
        else:
            return self._select_learning()
    
    def _select_exploration(self) -> float:
        """탐색 단계: 시도 횟수가 적은 난이도 우선 선택"""
        under_explored = []
        for difficulty in self.difficulties:
            if self.stats[difficulty].attempts < self.min_attempts_per_difficulty:
                under_explored.append(difficulty)
        
        if not under_explored:
            # 모든 난이도 탐색 완료 → 학습 단계로 전환
            self.exploration_phase = False
            
            # 탐색 결과 요약 출력
            print(f"\n{'='*60}")
            print(f"🎓 SPCL 탐색 단계 완료! 학습 단계로 전환")
            print(f"   각 난이도당 {self.min_attempts_per_difficulty}회 이상 시도 완료")
            print(f"   탐색 결과:")
            for d in self.difficulties:
                stats = self.stats[d]
                sr = stats.successes / max(stats.attempts, 1)
                status = "✓" if stats.loss < self.lambda_value else "✗"
                print(f"     {status} Skill {d:.1f}: Loss={stats.loss:.3f}, 성공률={sr*100:.1f}%")
            print(f"   현재 Lambda: {self.lambda_value:.3f}")
            candidates = self.get_candidate_difficulties()
            print(f"   학습 가능 난이도: {[f'{d:.1f}' for d in candidates]}")
            print(f"{'='*60}\n")
            
            return self._select_learning()
        
        # 시도 횟수가 가장 적은 난이도 선택
        min_attempts = min(self.stats[d].attempts for d in under_explored)
        least_tried = [d for d in under_explored if self.stats[d].attempts == min_attempts]
        
        selected = np.random.choice(least_tried)
        self.selected_difficulties.append(selected)
        return selected
    
    def _select_learning(self) -> float:
        """학습 단계: Loss < Lambda인 난이도만 선택
        
        v2.1 수정:
        - undersampled 선택도 candidates 내에서만 수행
        - SPCL 원칙 준수: Loss < Lambda인 난이도만 학습
        """
        # Loss < Lambda 조건으로 학습 후보 필터링 (먼저 수행)
        candidates = []
        candidate_weights = []
        
        for difficulty in self.difficulties:
            stats = self.stats[difficulty]
            
            if stats.loss < self.lambda_value:
                candidates.append(difficulty)
                
                # 가중치 계산
                weight = 1.0 + (difficulty * self.hard_weight_bonus)
                
                # Loss가 Lambda에 가까울수록 추가 보너스
                loss_proximity = stats.loss / max(self.lambda_value, 0.01)
                weight += loss_proximity * 0.5
                
                # Coverage penalty: 최근에 많이 선택된 난이도 가중치 감소
                recent_count = self.selected_difficulties[-100:].count(difficulty)
                if recent_count > 20:
                    weight *= 0.5  # 20회 이상 선택 시 가중치 절반
                
                candidate_weights.append(weight)
        
        # 후보가 없으면 가장 쉬운 난이도 반환
        if not candidates:
            selected = self.difficulties[0]
            self.selected_difficulties.append(selected)
            self._update_consecutive_count(selected)
            return selected
        
        # 가중치 기반 확률적 샘플링
        weights = np.array(candidate_weights)
        probabilities = weights / weights.sum()
        
        selected = np.random.choice(candidates, p=probabilities)
        self.selected_difficulties.append(selected)
        self._update_consecutive_count(selected)
        
        return selected
    
    def _update_consecutive_count(self, difficulty: float) -> None:
        """연속 선택 카운트 업데이트"""
        if difficulty == self.last_selected_difficulty:
            self.consecutive_same_count += 1
        else:
            self.consecutive_same_count = 1
            self.last_selected_difficulty = difficulty
    
    def force_exploration_for_all(self, num_episodes_per_difficulty: int = 10) -> List[float]:
        """모든 난이도에 대해 강제 탐색 수행
        
        주기적 전체 평가 시 사용. 각 난이도별로 N 에피소드씩 수행.
        
        Returns:
            탐색할 난이도 리스트 (셔플됨)
        """
        difficulties_to_explore = []
        for d in self.difficulties:
            difficulties_to_explore.extend([d] * num_episodes_per_difficulty)
        
        np.random.shuffle(difficulties_to_explore)
        return difficulties_to_explore
    
    def should_do_periodic_eval(self) -> bool:
        """주기적 전체 평가 시점인지 확인"""
        if self.episode_count - self.last_periodic_eval >= self.periodic_eval_interval:
            return True
        return False
    
    def mark_periodic_eval_done(self) -> None:
        """주기적 평가 완료 표시"""
        self.last_periodic_eval = self.episode_count
    
    def is_exploration_phase(self) -> bool:
        """현재 탐색 단계인지 확인"""
        return self.exploration_phase
    
    def should_evaluate_all(self, eval_interval: int = 500) -> bool:
        """전체 난이도 평가 주기인지 확인"""
        return self.episode_count > 0 and self.episode_count % eval_interval == 0
    
    def get_all_difficulties(self) -> List[float]:
        """모든 난이도 리스트 반환"""
        return self.difficulties.copy()
    
    def update_loss_from_evaluation(self, difficulty: float, success_rate: float) -> None:
        """평가 결과로 Loss 직접 업데이트
        
        Args:
            difficulty: 평가한 난이도
            success_rate: 성공률 (0.0 ~ 1.0)
        """
        if difficulty in self.stats:
            stats = self.stats[difficulty]
            # 직접 성공률로 Loss 계산 (가장 정확)
            new_loss = 1.0 - success_rate
            # 기존 Loss와 블렌딩 (급격한 변화 방지)
            stats.loss = 0.7 * new_loss + 0.3 * stats.loss
    
    def update_loss_batch(self, eval_results: Dict[float, Tuple[int, int]]) -> None:
        """배치 평가 결과로 Loss 일괄 업데이트
        
        Args:
            eval_results: {난이도: (성공 횟수, 전체 시도 횟수)}
        """
        for difficulty, (successes, attempts) in eval_results.items():
            if attempts > 0 and difficulty in self.stats:
                success_rate = successes / attempts
                self.update_loss_from_evaluation(difficulty, success_rate)
    
    def get_stats_summary(self) -> str:
        """현재 상태 요약 문자열 반환"""
        recent_sr = self.get_recent_success_rate()
        phase = "탐색" if self.exploration_phase else "학습"
        
        lines = [
            f"SPCL Status | Phase: {phase} | Lambda: {self.lambda_value:.3f} | Episodes: {self.episode_count}",
            f"Recent Success Rate: {recent_sr*100:.1f}% (last {len(self.recent_results)} eps)",
            "-" * 60
        ]
        
        for difficulty in self.difficulties:
            stats = self.stats[difficulty]
            success_rate = stats.successes / max(stats.attempts, 1) * 100
            
            # 최근 성공률도 표시
            recent = self.difficulty_recent_results.get(difficulty, [])
            recent_sr = sum(recent) / len(recent) * 100 if recent else 0
            
            if self.exploration_phase:
                remaining = max(0, self.min_attempts_per_difficulty - stats.attempts)
                status = f"({remaining:2d})" if remaining > 0 else " ✓ "
            else:
                status = " ✓ " if stats.loss < self.lambda_value else " ✗ "
            
            lines.append(
                f"  {status} Skill {difficulty:.1f}: "
                f"Loss={stats.loss:.3f}, "
                f"Attempts={stats.attempts:4d}, "
                f"전체={success_rate:5.1f}%, "
                f"최근={recent_sr:5.1f}%"
            )
        
        return "\n".join(lines)
    
    def get_candidate_difficulties(self) -> List[float]:
        """현재 학습 가능한 후보 난이도 리스트 반환"""
        return [d for d in self.difficulties if self.stats[d].loss < self.lambda_value]
    
    def reset(self) -> None:
        """스케줄러 상태 초기화"""
        self.lambda_value = self.initial_lambda
        self.episode_count = 0
        self.lambda_history = [self.initial_lambda]
        self.selected_difficulties = []
        self.recent_results = []
        self.exploration_phase = True
        self.last_periodic_eval = 0
        
        # 난이도에 비례한 점진적 Loss로 초기화 (Loss 최대치 1.0 감안)
        for d in self.difficulties:
            initial_loss = 0.2 + (d * 0.8)  # skill 1.0 → Loss 1.0
            self.stats[d] = DifficultyStats(difficulty=d, loss=initial_loss)
            self.difficulty_recent_results[d] = []
        
        # 연속 선택 추적 리셋
        self.last_selected_difficulty = 0.0
        self.consecutive_same_count = 0
    
    def should_step_lambda(self) -> bool:
        """Lambda 업데이트 주기인지 확인"""
        return self.episode_count > 0 and self.episode_count % self.lambda_update_interval == 0


# 편의 함수: 학습 모드별 기본 설정
def create_spcl_scheduler_for_mode(training_mode: str = "balanced") -> SPCLScheduler:
    """학습 모드에 맞는 SPCL 스케줄러 생성 (v2.1 통일 버전)
    
    Args:
        training_mode: "survival", "balanced", "attack" 중 하나 (현재 미사용)
    
    Returns:
        SPCLScheduler 인스턴스 (모든 모드 동일 설정)
    
    v2.1 통일 원칙:
    - 모든 모드에서 동일한 파라미터 사용
    - SPCL 자체가 에이전트 성능에 적응하므로 모드별 차이 불필요
    - 유지보수 간소화
    
    초기 학습 가능 난이도 (Lambda=0.35):
    - skill 0.0: Loss 0.20 < 0.35 ✓
    - skill 0.1: Loss 0.25 < 0.35 ✓
    - skill 0.2: Loss 0.30 < 0.35 ✓
    - skill 0.3: Loss 0.35 = 0.35 (경계)
    - skill 0.4+: Lambda 증가 필요
    """
    # 모든 모드에서 동일한 기본 설정 사용
    return SPCLScheduler()
