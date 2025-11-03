# 학습 붕괴 원인 분석 및 해결방안

## 📊 증상 분석

5349 에피소드 학습 후 다음과 같은 심각한 성능 저하가 발생:

| 지표 | 초반 (0-500 에피소드) | 최종 (5000+ 에피소드) | 감소율 |
|------|---------------------|---------------------|--------|
| **Reward** | 300-500 | 100 이하 | **60-80% 감소** |
| **Survival Time** | 400-600 steps | 200-300 steps | **40-50% 감소** |
| **Score** | 400-500 | 200-300 | **40-50% 감소** |
| **Kills** | 3-5 | 1-3 | **40-60% 감소** |

### 그래프 패턴 특징

1. **초반 학습 (0-1000 에피소드)**: 빠른 성능 향상
2. **중반 (1000-2500 에피소드)**: 성능 유지 및 완만한 향상
3. **후반 (2500-5000+ 에피소드)**: **지속적인 성능 저하** ❌

이는 전형적인 **학습 붕괴(Training Collapse)** 패턴입니다.

---

## 🔍 근본 원인 분석

### 1. **Learning Rate 과다** (가장 치명적 ⚠️)

```python
# 기존 코드 (src/rl/ppo_agent.py:30)
learning_rate: float = 3e-4  # 7.67e-05 → 3e-4 (약 4배 증가)
```

#### 문제점:
- Optuna로 최적화된 값 `7.67e-05`를 **4배** 증가시켜 `3e-4`로 설정
- 초반에는 빠른 학습으로 좋은 성능을 보이지만...
- 시간이 지나면서 **과도한 그래디언트 업데이트**로 학습된 좋은 정책이 파괴됨
- 5000+ 에피소드에서는 학습이 완전히 **발산(divergence)**

#### 학습 과정:
```
에피소드 0-500:   빠른 학습 → 좋은 정책 발견 ✅
에피소드 500-2000: 계속 업데이트 → 조금씩 정책이 불안정해짐 ⚠️
에피소드 2000+:   과도한 업데이트 → 좋은 정책이 망가짐 ❌
```

#### 이론적 배경:
- PPO는 **on-policy** 알고리즘으로, 정책이 크게 변하면 수집된 데이터가 무효화됨
- `clip_epsilon`으로 변화량을 제한하지만, **learning rate가 높으면 소용없음**
- 높은 learning rate = 작은 배치에서도 큰 파라미터 변화
- 결과: 학습이 진행될수록 정책이 진동하고, 결국 붕괴

---

### 2. **Entropy Coefficient 과다**

```python
# 기존 코드 (src/rl/ppo_agent.py:35)
entropy_coef: float = 0.01  # 0.00166 → 0.01 (약 6배 증가)
```

#### 문제점:
- 최적화된 값 `0.00166`을 **6배** 증가시켜 `0.01`로 설정
- 엔트로피가 높으면 에이전트가 **계속 랜덤하게 행동**
- 탐험(exploration)은 초반에만 필요하고, 후반에는 **활용(exploitation)**이 중요
- 5000+ 에피소드에서도 계속 랜덤하게 행동 → 성능 저하

#### 학습 단계별 역할:
| 단계 | 필요한 것 | 적절한 Entropy |
|------|----------|---------------|
| **초반 (0-1000)** | 탐험 (다양한 전략 시도) | **높음** (0.01) |
| **중반 (1000-3000)** | 균형 (탐험 + 활용) | **중간** (0.005) |
| **후반 (3000+)** | 활용 (좋은 전략 활용) | **낮음** (0.001) |

현재 설정은 모든 단계에서 `0.01`로 높아서, 후반에도 계속 랜덤 행동!

---

### 3. **배치 크기와 Learning Rate 불균형**

```python
# src/rl/trainer.py:40
batch_size: int = 256  # 64 → 256 (4배 증가)
```

#### 문제점:
- 배치 크기를 4배 늘렸는데, learning rate는 오히려 4배 증가
- **이론**: 배치 크기가 커지면 그래디언트가 안정적 → learning rate를 **증가**시킬 수 있음
- **현실**: 하지만 PPO는 매우 민감 → learning rate를 증가시키면 불안정

#### 올바른 조정 방향:
```
배치 크기 증가 (64 → 256) ✅
→ Learning rate 약간 증가 또는 유지 (7.67e-05 → 1e-04)
→ 현재: 3e-4는 너무 높음! ❌
```

---

## 🛠️ 적용된 해결방안

### 1. Learning Rate 감소 (핵심 수정)

```python
# 수정 후 (src/rl/ppo_agent.py:30)
learning_rate: float = 5e-5  # 안정성 우선 (3e-4 → 5e-5, 6배 감소)
```

#### 효과:
- 학습 속도는 느려지지만, **안정적**이고 **지속 가능한** 학습
- 좋은 정책을 발견하면 유지하고 점진적으로 개선
- 5000+ 에피소드에서도 성능 유지 또는 향상

### 2. Entropy Coefficient 감소

```python
# 수정 후 (src/rl/ppo_agent.py:35)
entropy_coef: float = 0.0015  # 탐험 감소 (0.01 → 0.0015, 6.7배 감소)
```

#### 효과:
- 초반에도 적절한 탐험 유지
- 후반에는 학습된 좋은 전략을 더 많이 활용
- 랜덤 행동 감소 → 일관성 있는 플레이

---

## 📈 예상 학습 곡선 비교

### 이전 (문제 있는 설정)
```
성능
 │
500├─────╮
 │      ╲
400│       ╲
 │        ╲
300│         ╲___
 │             ╲___
200│                 ╲___
 │                      ╲___
100│                          ╲___
 │                               ╲___
 └──────────────────────────────────> 에피소드
   0    1000   2000   3000   4000   5000
```

### 이후 (안정화된 설정)
```
성능
 │
500├─────────╭────╮
 │        ╱      ╲
400│      ╱        ╲___________
 │    ╱                       ─────
300│  ╱
 │╱
200│
 │
100│
 │
 └──────────────────────────────────> 에피소드
   0    1000   2000   3000   4000   5000
```

---

## 💡 추가 권장사항

### 1. Learning Rate Scheduler 도입

현재는 고정된 learning rate를 사용하지만, 다음과 같이 개선 가능:

```python
class LearningRateScheduler:
    def __init__(self, initial_lr=5e-5, min_lr=1e-5, decay_rate=0.99):
        self.initial_lr = initial_lr
        self.min_lr = min_lr
        self.decay_rate = decay_rate
        self.current_lr = initial_lr
    
    def step(self, episode):
        """에피소드마다 learning rate 감소"""
        self.current_lr = max(
            self.min_lr,
            self.initial_lr * (self.decay_rate ** (episode / 100))
        )
        return self.current_lr
```

#### 효과:
- 초반: 높은 LR로 빠른 학습
- 후반: 낮은 LR로 안정적인 fine-tuning

### 2. Entropy Decay

```python
def get_entropy_coef(episode, max_episodes=5000):
    """에피소드가 진행될수록 엔트로피 감소"""
    progress = episode / max_episodes
    start_entropy = 0.01
    end_entropy = 0.0005
    return start_entropy * (1 - progress) + end_entropy * progress
```

#### 효과:
- 초반: 높은 엔트로피로 다양한 전략 탐험
- 후반: 낮은 엔트로피로 좋은 전략 활용

### 3. Early Stopping

```python
class EarlyStopping:
    def __init__(self, patience=500, min_delta=0.01):
        self.patience = patience
        self.min_delta = min_delta
        self.best_reward = float('-inf')
        self.counter = 0
    
    def check(self, current_reward):
        if current_reward > self.best_reward + self.min_delta:
            self.best_reward = current_reward
            self.counter = 0
            return False  # 계속 학습
        else:
            self.counter += 1
            if self.counter >= self.patience:
                return True  # 학습 중단
        return False
```

#### 효과:
- 성능이 더 이상 개선되지 않으면 학습 중단
- 과적합 및 학습 붕괴 방지

### 4. Gradient Monitoring

```python
def monitor_gradients(model):
    """그래디언트 크기 모니터링"""
    total_norm = 0
    for p in model.parameters():
        if p.grad is not None:
            param_norm = p.grad.data.norm(2)
            total_norm += param_norm.item() ** 2
    total_norm = total_norm ** 0.5
    
    if total_norm > 10.0:
        print(f"⚠️ 그래디언트 폭발 감지: {total_norm:.2f}")
    elif total_norm < 0.001:
        print(f"⚠️ 그래디언트 소실 감지: {total_norm:.6f}")
    
    return total_norm
```

#### 효과:
- 학습 중 그래디언트 문제 조기 감지
- 하이퍼파라미터 조정의 피드백

---

## 🎯 결론

### 문제의 핵심
- **Learning rate가 너무 높아서** 학습이 불안정하고, 시간이 지날수록 좋은 정책이 망가짐
- **Entropy coefficient가 너무 높아서** 계속 랜덤하게 행동

### 해결 방향
1. ✅ **Learning rate 감소** (3e-4 → 5e-5): 안정적인 학습
2. ✅ **Entropy coefficient 감소** (0.01 → 0.0015): 활용 중심
3. 🔜 **Learning rate scheduler**: 동적 조정
4. 🔜 **Early stopping**: 과적합 방지
5. 🔜 **Gradient monitoring**: 문제 조기 감지

### 예상 결과
- 학습 속도는 약간 느려지지만, **안정적**이고 **지속 가능한** 개선
- 5000+ 에피소드에서도 성능 유지 또는 향상
- 일관성 있는 플레이 패턴

---

## 📚 참고자료

### PPO 논문
- Schulman et al. (2017) "Proximal Policy Optimization Algorithms"
- Learning rate: "We use Adam optimizer with learning rate 2.5e-4"

### 실전 경험
- OpenAI Baselines: Learning rate 2.5e-4 ~ 1e-4
- Stable-Baselines3: Learning rate 3e-4 (기본값)
- 우리 프로젝트: 게임이 복잡하므로 더 낮은 LR 필요 (5e-5)

### 추천 읽기
- "Fine-Tuning Language Models from Human Preferences" (OpenAI)
- "Implementation Matters in Deep RL" (Henderson et al., 2018)
- "Deep Reinforcement Learning that Matters" (Henderson et al., 2017)

---

## 🚀 다음 단계

1. **재학습 시작**
   ```bash
   rye run python train_ppo_real_game.py --max-episodes 5000 --use-curriculum --curriculum-type step
   ```

2. **학습 모니터링**
   - 처음 500 에피소드: 빠른 학습 확인
   - 1000-2000 에피소드: 성능 유지 확인
   - 3000+ 에피소드: 성능 저하 없는지 확인

3. **결과 비교**
   - 이전 학습 그래프와 비교
   - 안정성 및 최종 성능 평가

4. **추가 최적화**
   - Learning rate scheduler 도입
   - Entropy decay 구현
   - Early stopping 추가

---

**작성일**: 2025-10-28  
**버전**: 1.0  
**상태**: 수정 완료 ✅



