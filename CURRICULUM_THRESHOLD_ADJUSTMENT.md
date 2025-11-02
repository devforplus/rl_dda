# 커리큘럼 Threshold 조정 가이드

## 🎯 문제 상황

Skill 0.6에서 학습 붕괴 발생:
- 목표: 680 스텝, 7.2 킬
- 실제: 200-400 스텝, 3-4 킬
- 결과: 3995 에피소드 학습 후에도 목표 미달성

## 💡 해결 방법 1: success_threshold 낮추기

### 현재 설정 (train_ppo_real_game.py 1693-1705번 줄)

```python
ConvergenceStage(
    skill_level=0.6,
    name="중상급 (공격 중심)",
    target_steps=680,  # 목표
    target_kills=7.2,
    success_threshold=0.80,  # 80% 달성 필요 ← 문제!
)
```

### 권장 수정

```python
ConvergenceStage(
    skill_level=0.6,
    name="중상급 (공격 중심)",
    target_steps=680,
    target_kills=7.2,
    success_threshold=0.70,  # 70%로 완화 ← 해결!
)
```

### 효과

| 항목 | 기존 (80%) | 권장 (70%) | 차이 |
|------|----------|----------|------|
| **필요 생존** | 544 스텝 | **476 스텝** | -68 스텝 |
| **필요 킬** | 5.76 킬 | **5.04 킬** | -0.72 킬 |
| **달성 가능성** | ❌ 불가능 | ✅ **가능** |

## 💡 해결 방법 2: 모든 단계에 적용

모든 단계의 threshold를 70%로 낮추기:

```python
stages = [
    ConvergenceStage(
        skill_level=0.1,
        success_threshold=0.70,  # 80 → 70
        # ...
    ),
    ConvergenceStage(
        skill_level=0.3,
        success_threshold=0.70,  # 80 → 70
        # ...
    ),
    ConvergenceStage(
        skill_level=0.6,
        success_threshold=0.70,  # 80 → 70 (중요!)
        # ...
    ),
    ConvergenceStage(
        skill_level=1.0,
        success_threshold=0.70,  # 80 → 70
        # ...
    ),
]
```

## 📊 예상 학습 시간

| Threshold | 총 에피소드 | 학습 시간 (예상) | 성공률 |
|----------|-----------|--------------|--------|
| **80%** | ~6000 | 50시간 | ❌ 낮음 (붕괴 위험) |
| **70%** | ~3000 | **25시간** | ✅ **높음** |

## 🎯 즉시 적용 방법

```bash
# 1. train_ppo_real_game.py 수정
# 1693, 1697번 줄 수정:
success_threshold=0.70

# 2. 학습 재시작
rye run python train_ppo_real_game.py --use-curriculum --max-episodes 5000
```

## ⚠️ 주의사항

- 70%로 낮춰도 여전히 도전적인 목표입니다
- Skill 0.6: 476 스텝, 5.04 킬 달성 필요
- 절대 한계선(max_episodes * 1.5) 도달 시 자동 전환됩니다

