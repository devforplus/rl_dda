# PPO 커리큘럼 러닝 진단 도구 사용 가이드

## 📋 개요

현재 학습이 정체되고 Catastrophic Forgetting이 발생하는 원인을 정확히 파악하기 위한 종합 진단 도구입니다.

## 🎯 진단 항목

### 1. 보상 분해 분석 (Reward Decomposition)
- **Multiplicative reward**: survival × attack 기본 보상
- **Bonus**: 80% 이상 달성 시 exponential 보너스
- **즉각 보상**: 킬 보상, 탄환 회피 보상
- **페널티**: HP 손실, 사망 페널티
- **분석 목적**: 어떤 보상 요소가 학습 신호를 제공하는지 파악

### 2. 목표 달성률 추이 분석
- 생존 목표 달성률 (current_steps / target_steps)
- 킬 목표 달성률 (current_kills / target_kills)
- 시간에 따른 추이 및 변동성(CV) 측정

### 3. Catastrophic Forgetting 감지
- 이전 단계에서의 성능 측정
- 현재 단계에서 이전 단계 목표를 달성할 수 있는지 테스트
- 성능 퇴화 정량화

### 4. PPO 학습 지표 분석
- **Policy loss, value loss, entropy**: 학습 손실 추이
- **Gradient norm**: Vanishing/Exploding gradient 확인
- **KL divergence**: 정책 변화 속도
- **Clip fraction**: PPO 제약 활성화 정도

### 5. 행동 패턴 분석
- 액션 분포 (특정 액션에 편향되었는지)
- Exploration vs Exploitation 비율

## 🚀 사용 방법

### 방법 1: 기존 체크포인트 진단 (추천)

```bash
# 최신 체크포인트 자동 탐색 및 진단
rye run python diagnose_training.py --skill 0.6

# 특정 체크포인트 진단
rye run python diagnose_training.py --checkpoint src/models/ppo/ppo_agent_episode_1000.pth --skill 0.6
```

### 방법 2: 학습 중 실시간 진단

`train_ppo_real_game.py`에 진단 기능을 통합하여 사용:

```python
from src.rl.reward_analyzer import RewardAnalyzer

# 학습 루프 내부에서
reward_analyzer = RewardAnalyzer()

for episode in range(num_episodes):
    # 에피소드 시작
    reward_analyzer.reset_episode()
    
    for step in range(max_steps):
        # ... 게임 스텝 실행 ...
        
        # 보상 분해 분석
        breakdown = reward_analyzer.analyze_reward(
            game_instance,
            skill_level,
            episode_step=step,
            previous_nearby_bullets=environment.previous_nearby_bullets,
            previous_player_pos=environment.previous_player_pos,
        )
    
    # 에피소드 종료 후 요약
    summary = reward_analyzer.get_episode_summary()
    
    # 50 에피소드마다 진단
    if episode % 50 == 0:
        diagnosis = reward_analyzer.diagnose_reward_sparsity(recent_episodes=50)
        print(f"\\n{'='*70}")
        print(f"보상 희소성 진단 (에피소드 {episode})")
        print(f"{'='*70}")
        print(f"평균 보상: {diagnosis['avg_final_reward']:.4f}")
        print(f"생존 달성률: {diagnosis['avg_survival_achievement']*100:.1f}%")
        print(f"킬 달성률: {diagnosis['avg_kill_achievement']*100:.1f}%")
        print(f"진단: {diagnosis['diagnosis']}")
```

## 📊 출력 결과

### 터미널 출력

```
======================================================================
🔬 PPO 커리큘럼 러닝 종합 진단
======================================================================

======================================================================
📂 체크포인트 로드: src/models/ppo/ppo_agent_episode_3000.pth
======================================================================

✅ 체크포인트 로드 완료
   - 에피소드: 3000
   - 스킬 레벨: 0.6

======================================================================
🎯 Stage 성능 진단: Skill 0.6
======================================================================

목표: 680 스텝, 7.2 킬
테스트 에피소드: 10회

📊 Stage 성능 요약:
   - 평균 생존: 450.2 ± 82.3 스텝
   - 평균 킬: 4.1 ± 1.2
   - 생존 달성률: 66.2%
   - 킬 달성률: 56.9%

======================================================================
🧠 Catastrophic Forgetting 진단
======================================================================

현재 스킬: 0.6
테스트할 이전 단계들: 0.1, 0.3

🔍 이전 Stage (Skill 0.1) 테스트 중...
   ✅ 정상 유지 (달성률: 92.3%)

🔍 이전 Stage (Skill 0.3) 테스트 중...
   ⚠️  성능 퇴화 감지! (달성률: 58.1%)

🚨 Catastrophic Forgetting 감지: 1/2 단계

======================================================================
💰 보상 희소성 진단: Skill 0.6
======================================================================

분석 에피소드: 50개
분석 스텝: 23500개

📊 보상 요소별 기여도:
   - Multiplicative Reward: 0.3521
   - Bonus: 0.0012
   - 즉각 보상 (킬/회피): 0.0834
   - 최종 보상: 0.4367

🎯 목표 달성률:
   - 생존: 66.2%
   - 킬: 56.9%

⚡ 학습 신호 강도:
   - 보상 분산: 0.0523
   - Signal-to-Noise: 1.87

🔬 Sparsity 지표:
   - Zero Multiplicative: 0.0%
   - Zero Bonus: 99.8%
   - Zero Immediate: 23.4%

💬 진단:
   🚨 Multiplicative reward가 매우 낮음 (목표 달성률 부족) |
   ⚠️ Bonus가 거의 발생하지 않음 (80% 달성 필요) |
   🚨 생존 목표 달성률이 매우 낮음: 66.2% |
   🚨 킬 목표 달성률이 매우 낮음: 56.9%
```

### 시각화 파일

진단 결과는 `diagnosis_results/` 디렉토리에 저장됩니다:

1. **`stage_performance_YYYYMMDD_HHMMSS.png`**
   - Stage별 생존/킬 달성률 막대 그래프
   - 평균 생존 스텝 및 킬 수 추이

2. **`catastrophic_forgetting_YYYYMMDD_HHMMSS.png`**
   - 이전 단계별 성능 유지 현황
   - Forgetting 여부 색상 표시 (녹색: 유지, 빨강: 퇴화)

3. **`reward_breakdown_YYYYMMDD_HHMMSS.png`**
   - 보상 요소별 기여도
   - Sparsity 지표 (Zero 비율)

4. **`diagnosis_report_YYYYMMDD_HHMMSS.json`**
   - 모든 진단 결과를 JSON 형식으로 저장
   - 추가 분석 및 비교에 활용

## 🔍 진단 결과 해석

### 현재 문제 (Stage 2 - Skill 0.3 기준)

#### 1. 보상 희소성 문제 ⚠️

```
목표: 740 스텝, 4.5 킬
현재 달성률: ~53%

→ Multiplicative Reward = 0.53 × 0.53 = 0.28 (매우 낮음!)
→ Bonus = 0 (80% 이상 필요)
→ 학습 신호가 너무 약함
```

**원인**:
- 목표가 과도하게 높음 (원래 설계: 440스텝, 3.6킬 → 현재: 740스텝, 4.5킬)
- Multiplicative reward의 곱셈 특성 때문에 53% 달성 시 보상이 제곱으로 감소
- Bonus가 80% 이상에서만 발생하므로 중간 단계에서 보상 부족

#### 2. Catastrophic Forgetting 발생 🚨

```
Stage 1 (Skill 0.1) → Stage 2 (Skill 0.3) 전환 후
→ Stage 1 목표 달성 불가
→ 기초 기술 퇴화
```

**원인**:
- 너무 이른 시기에 다음 단계로 전환
- Stage 1에서 충분히 수렴하지 않음
- 급격한 난이도 상승으로 인한 정책 붕괴

#### 3. PPO 고유 한계

```
Entropy: 0.00167 (매우 낮음)
→ Exploration 거의 없음
→ Local optimum 탈출 어려움
```

## 💡 해결 방안

### 즉시 적용 가능한 개선

#### 1. 목표 재설정 (Critical)

```python
# targets.py 수정
def get_survival_target_steps(skill_level: float) -> int:
    # 기존: 280 + 1800 * skill (너무 높음)
    # 수정: 200 + 800 * skill (더 현실적)
    base_steps = 200
    skill_bonus = 800 * skill_level
    return int(base_steps + skill_bonus)

def get_kill_target(skill_level: float) -> float:
    # 기존: 1.2 + 10.8 * skill (너무 높음)
    # 수정: 1.0 + 9.0 * skill (더 현실적)
    base_kills = 1.0
    skill_bonus = 9.0 * skill_level
    return base_kills + skill_bonus

# 결과:
# Stage 1 (0.1): 280 스텝, 1.9 킬 (기존: 280, 2.3)
# Stage 2 (0.3): 440 스텝, 3.7 킬 (기존: 740, 4.5)  ← 훨씬 현실적!
# Stage 3 (0.6): 680 스텝, 6.4 킬 (기존: 1280, 7.7)
# Stage 4 (1.0): 1000 스텝, 10 킬 (기존: 2000, 12)
```

#### 2. 보상 함수 개선

```python
# environment.py - calculate_reward() 수정

# A. Bonus 발동 임계값 낮추기
if survival_score >= 0.6 and attack_score >= 0.6:  # 80% → 60%
    bonus = calculate_bonus(...)

# B. Intermediate reward 추가 (60-80% 구간)
if 0.5 <= survival_score < 0.8 or 0.5 <= attack_score < 0.8:
    intermediate_bonus = (survival_score + attack_score) / 2 * 0.1

# C. 즉각 보상 강화
kill_reward = new_kills * (0.03 + skill_level * 0.05)  # 증가
dodge_reward = min(0.08, dodged_count * 0.02)  # 증가
```

#### 3. 커리큘럼 전환 기준 강화

```python
# convergence_based_curriculum.py

# 수렴 기준 강화
stage.success_threshold = 0.90  # 80% → 90%
stage.min_episodes = 200  # 150 → 200
stage.consecutive_success_rate = 0.85  # 80% → 85%

# Warm Start 크기 증가
warmup_size = 50  # 20 → 50
```

## 📚 추가 도구

### 1. 보상 분해 CSV 저장

```python
reward_analyzer.save_to_csv('reward_breakdown.csv')
```

CSV 파일을 Excel이나 pandas로 열어서 더 상세한 분석 가능

### 2. PPO 학습 지표 로깅

`train_ppo_real_game.py`에서 자동으로 로깅됩니다:

```python
update_info = agent.update(num_epochs=4, batch_size=64)

# 반환되는 지표:
# - policy_loss
# - value_loss
# - entropy_loss
# - entropy (실제 엔트로피)
# - kl_divergence (정책 변화 속도)
# - clip_fraction (PPO 제약 활성화 비율)
# - grad_norm (그래디언트 크기)
```

## 🎓 진단 결과 기반 액션 플랜

### Priority 1: 목표 재설정 (즉시)
- [ ] `src/rl/targets.py` 수정
- [ ] 새로운 목표로 학습 재시작
- [ ] 100 에피소드 후 진단 재실행

### Priority 2: 보상 함수 개선 (단기)
- [ ] Bonus 임계값 60%로 낮추기
- [ ] Intermediate bonus 추가
- [ ] 즉각 보상 강화

### Priority 3: 커리큘럼 강화 (중기)
- [ ] 수렴 기준 강화
- [ ] Warm Start 크기 증가
- [ ] Stage별 최소 에피소드 증가

### Priority 4: PPO 하이퍼파라미터 (장기)
- [ ] Entropy coefficient 증가 (exploration 강화)
- [ ] Learning rate 조정
- [ ] Batch size 최적화

## 🐛 트러블슈팅

### 문제: 진단 도구가 체크포인트를 찾지 못함

```bash
# 체크포인트 경로 확인
ls src/models/ppo/*.pth

# 직접 경로 지정
rye run python diagnose_training.py --checkpoint <경로>
```

### 문제: 시각화 생성 실패

```bash
# matplotlib 백엔드 확인
python -c "import matplotlib; print(matplotlib.get_backend())"

# 'Agg' 백엔드로 설정 (GUI 없음)
export MPLBACKEND=Agg  # Linux/Mac
set MPLBACKEND=Agg     # Windows
```

### 문제: 실시간 진단 시 게임 느려짐

```python
# 진단 빈도 줄이기
if episode % 100 == 0:  # 50 → 100
    diagnosis = reward_analyzer.diagnose_reward_sparsity()
```

## 📞 추가 지원

진단 결과가 명확하지 않거나 추가 분석이 필요한 경우:
1. `diagnosis_report_YYYYMMDD_HHMMSS.json` 파일 확인
2. 보상 분해 CSV 데이터 분석
3. 여러 시점의 체크포인트 비교 진단


