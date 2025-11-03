
# 최적 하이퍼파라미터로 PPO 에이전트 생성하기
# 생성 시간: 2025-08-07 12:00:10

from src.rl.ppo_agent import PPOAgent

# 최적화된 하이퍼파라미터
best_params = {
    "state_size": 153,
    "action_size": 9,
    "learning_rate": 0.0006278482659955976,
    "gamma": 0.9797015348175233,
    "gae_lambda": 0.8311813563951888,
    "clip_epsilon": 0.21111982063074786,
    "value_coef": 0.8771599556595219,
    "entropy_coef": 0.010654903044552189,
    "batch_size": 32,
    "num_epochs": 4,
    "hidden_size": 512,
    "num_layers": 4,
    "grad_clip_norm": 0.6973918906870632
}

# PPO 에이전트 생성
agent = PPOAgent(**best_params)

print("✅ 최적화된 PPO 에이전트가 생성되었습니다!")
print(f"📊 예상 성능 향상: 35.9점")
