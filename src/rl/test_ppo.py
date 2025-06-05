"""
PPO 모델 테스트 스크립트

PPO 환경, 에이전트, 네트워크의 기본 동작을 테스트합니다.
실제 게임 없이도 PPO 구현이 올바른지 확인할 수 있습니다.

---

PPO 구현의 기능 검증을 위한 테스트 스크립트
"""

import torch
import numpy as np
from typing import List
import time

from rl.environment import GameEnvironment, GameState, EntityData
from rl.agents.ppo_agent import PPOAgent
from rl.networks import ActorCriticNetwork
from rl.game_adapter import GameStateAdapter, create_game_state_from_entities
from components.entity_types import EntityType


def test_environment():
    """게임 환경 테스트

    ---

    GameEnvironment 클래스의 기본 기능을 테스트
    """
    print("=== Testing GameEnvironment ===")

    # 환경 생성
    env = GameEnvironment(max_entities=10)

    # 상태 크기와 액션 크기 확인
    print(f"State size: {env.get_state_size()}")
    print(f"Action space size: {env.get_action_space_size()}")

    # 더미 게임 상태 생성
    entities = [
        EntityData(EntityType.PLAYER, 100, 100, 8, 8, 0),
        EntityData(EntityType.ENEMY, 150, 120, 8, 8, 50),
        EntityData(EntityType.ENEMY_SHOT, 130, 110, 4, 4, 30),
        EntityData(EntityType.POWERUP, 80, 80, 8, 8, 28),
    ]

    game_state = GameState(
        entities=entities,
        skill_level=0.5,
        personality=1,
        player_hp=8,
        score=1000,
        survival_time=500,
        kills=5,
    )

    # 상태 인코딩 테스트
    encoded_state = env.encode_state(game_state)
    print(f"Encoded state shape: {encoded_state.shape}")
    print(f"State sample: {encoded_state[:10]}")

    # 보상 계산 테스트
    reward = env.calculate_reward(game_state, 1)
    print(f"Calculated reward: {reward:.4f}")

    print("✅ Environment test passed!\n")


def test_networks():
    """신경망 테스트

    ---

    정책 네트워크와 가치 네트워크의 기본 동작을 테스트
    """
    print("=== Testing Neural Networks ===")

    state_size = 306  # 50 entities * 6 features + 6 meta features
    action_size = 9
    batch_size = 8

    # Actor-Critic 네트워크 생성
    network = ActorCriticNetwork(state_size, action_size)

    # 더미 상태 생성
    dummy_states = torch.randn(batch_size, state_size)
    dummy_actions = torch.randint(0, action_size, (batch_size,))

    # 순전파 테스트
    action_probs, values = network(dummy_states)
    print(f"Action probabilities shape: {action_probs.shape}")
    print(f"Values shape: {values.shape}")
    print(f"Action probs sum (should be ~1): {action_probs[0].sum():.4f}")

    # 액션 선택과 가치 추정
    action, log_prob, value = network.get_action_and_value(dummy_states[0:1])
    print(f"Selected action: {action.item()}")
    print(f"Log probability: {log_prob.item():.4f}")
    print(f"State value: {value.item():.4f}")

    # 액션 평가
    log_probs, values, entropy = network.evaluate_actions(dummy_states, dummy_actions)
    print(f"Batch log probs shape: {log_probs.shape}")
    print(f"Batch values shape: {values.shape}")
    print(f"Batch entropy shape: {entropy.shape}")

    print("✅ Networks test passed!\n")


def test_ppo_agent():
    """PPO 에이전트 테스트

    ---

    PPO 에이전트의 액션 선택과 학습 기능을 테스트
    """
    print("=== Testing PPO Agent ===")

    # 환경과 에이전트 생성
    env = GameEnvironment(max_entities=10)
    agent = PPOAgent(env)

    print(f"Agent device: {agent.device}")
    print(f"Network parameters: {sum(p.numel() for p in agent.network.parameters()):,}")

    # 더미 게임 상태 생성
    entities = [
        EntityData(EntityType.PLAYER, 100, 100, 8, 8, 0),
        EntityData(EntityType.ENEMY, 150, 120, 8, 8, 50),
    ]

    game_state = GameState(
        entities=entities,
        skill_level=0.7,
        personality=0,
        player_hp=10,
        score=500,
        survival_time=300,
        kills=2,
    )

    # 액션 선택 테스트
    action = agent.select_action(game_state)
    print(f"Selected action: {action}")

    # 탐험 포함 액션 선택 테스트
    action, log_prob, value = agent.select_action_with_exploration(game_state)
    print(f"Exploration action: {action}, log_prob: {log_prob:.4f}, value: {value:.4f}")

    # 경험 저장 테스트
    agent.store_experience(game_state, action, 0.5, log_prob, value, False)
    print(f"Buffer size after storing: {agent.buffer.size()}")

    # 여러 경험 저장
    for i in range(100):
        # 약간씩 다른 상태 생성
        test_entities = [
            EntityData(EntityType.PLAYER, 100 + i, 100, 8, 8, 0),
            EntityData(EntityType.ENEMY, 150, 120 + i, 8, 8, 50),
        ]

        test_state = GameState(
            entities=test_entities,
            skill_level=0.5,
            personality=0,
            player_hp=10,
            score=500 + i * 10,
            survival_time=300 + i,
            kills=2,
        )

        action, log_prob, value = agent.select_action_with_exploration(test_state)
        reward = np.random.random() * 2 - 1  # -1 ~ 1 사이의 보상
        done = i == 99  # 마지막에만 종료

        agent.store_experience(test_state, action, reward, log_prob, value, done)

    print(f"Buffer size after 100 experiences: {agent.buffer.size()}")

    # 학습 테스트
    training_stats = agent.train()
    if training_stats:
        print("Training stats:")
        for key, value in training_stats.items():
            print(f"  {key}: {value:.6f}")
    else:
        print("Not enough data for training")

    # 통계 확인
    stats = agent.get_stats()
    if stats:
        print("Agent stats:")
        for key, value in stats.items():
            print(f"  {key}: {value:.4f}")

    print("✅ PPO Agent test passed!\n")


def test_game_adapter():
    """게임 어댑터 테스트

    ---

    GameStateAdapter의 상태 변환과 액션 매핑을 테스트
    """
    print("=== Testing Game Adapter ===")

    adapter = GameStateAdapter()

    # 더미 엔티티 생성
    class DummyEntity:
        def __init__(self, x, y, entity_type, w=8, h=8):
            self.x = x
            self.y = y
            self.type = entity_type
            self.w = w
            self.h = h
            self.remove = False

    entities = [
        DummyEntity(100, 100, EntityType.PLAYER),
        DummyEntity(150, 120, EntityType.ENEMY),
        DummyEntity(130, 110, EntityType.ENEMY_SHOT, 4, 4),
    ]

    # 게임 상태 생성 테스트
    game_state = create_game_state_from_entities(
        entities, skill_level=0.8, personality=1
    )
    print(f"Created game state with {len(game_state.entities)} entities")
    print(
        f"Skill level: {game_state.skill_level}, Personality: {game_state.personality}"
    )

    # 액션 변환 테스트
    for action_id in range(9):
        game_inputs = adapter.convert_action_to_game_input(action_id)
        print(f"Action {action_id}: {game_inputs}")

    print("✅ Game Adapter test passed!\n")


def test_training_loop():
    """간단한 학습 루프 테스트

    ---

    실제 게임 없이 시뮬레이션된 환경에서 간단한 학습을 테스트
    """
    print("=== Testing Training Loop ===")

    # 환경과 에이전트 생성
    env = GameEnvironment(max_entities=5)
    agent = PPOAgent(env, buffer_size=128, batch_size=32, ppo_epochs=3)

    print("Starting mini training loop...")

    num_episodes = 5
    max_steps = 50

    for episode in range(num_episodes):
        episode_reward = 0
        episode_length = 0

        for step in range(max_steps):
            # 랜덤 게임 상태 생성
            entities = []
            if np.random.random() > 0.3:  # 70% 확률로 플레이어 생성
                entities.append(
                    EntityData(
                        EntityType.PLAYER,
                        np.random.randint(50, 200),
                        np.random.randint(50, 200),
                        8,
                        8,
                        0,
                    )
                )

            # 랜덤 적 생성
            num_enemies = np.random.randint(0, 3)
            for _ in range(num_enemies):
                entities.append(
                    EntityData(
                        EntityType.ENEMY,
                        np.random.randint(0, 256),
                        np.random.randint(0, 256),
                        8,
                        8,
                        np.random.random() * 200,
                    )
                )

            game_state = GameState(
                entities=entities,
                skill_level=0.5,
                personality=0,
                player_hp=max(1, 10 - step // 10),  # 체력 감소
                score=step * 10,
                survival_time=step,
                kills=step // 10,
            )

            # 액션 선택
            action, log_prob, value = agent.select_action_with_exploration(game_state)

            # 시뮬레이션된 보상 (간단한 규칙)
            reward = 0.1  # 기본 생존 보상
            if len(entities) > 1:  # 적이 있으면
                reward += 0.2 if action == 8 else -0.1  # 공격하면 보상, 아니면 페널티

            # 에피소드 종료 조건
            done = (game_state.player_hp <= 0) or (step >= max_steps - 1)

            # 경험 저장
            agent.store_experience(game_state, action, reward, log_prob, value, done)

            episode_reward += reward
            episode_length += 1

            if done:
                break

        # 학습
        training_stats = agent.train()

        print(
            f"Episode {episode + 1}: Reward = {episode_reward:.2f}, "
            f"Length = {episode_length}, "
            f"Buffer = {agent.buffer.size()}"
        )

        if training_stats and episode > 0:
            print(f"  Training loss: {training_stats.get('total_loss', 0):.6f}")

    print("✅ Training loop test passed!\n")


def run_all_tests():
    """모든 테스트 실행

    ---

    PPO 구현의 전체 기능을 순차적으로 테스트
    """
    print("🚀 Starting PPO Implementation Tests\n")

    try:
        test_environment()
        test_networks()
        test_ppo_agent()
        test_game_adapter()
        test_training_loop()

        print("🎉 All tests passed! PPO implementation is ready.")

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    run_all_tests()
