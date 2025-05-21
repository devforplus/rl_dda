import random
import torch # torchrl 사용을 가정하므로 torch 임포트 추가
# from torchrl.data import TensorSpec # 필요한 경우 특정 Spec 임포트

from .base_agent import BaseAgent

class RandomAgent(BaseAgent):
    """
    무작위로 행동을 선택하는 간단한 에이전트입니다.
    torchrl 환경과 호환되도록 고려되었습니다.
    """
    def __init__(self, action_space):
        """
        RandomAgent를 초기화합니다.

        Args:
            action_space: 에이전트가 선택할 수 있는 가능한 행동의 공간입니다.
                          torchrl의 TensorSpec 객체 (예: DiscreteTensorSpec) 또는
                          sample() 메소드를 가진 객체를 기대합니다.
                          간단한 리스트 형식도 지원합니다 (하위 호환성).
        """
        super().__init__(action_space)

    def select_action(self, state):
        """
        주어진 상태(state)와 관계없이 무작위로 행동을 선택합니다.
        action_space에 sample() 메소드가 있으면 사용하고, 없으면 리스트로 간주하여 random.choice를 사용합니다.

        Args:
            state: 현재 상태 (이 에이전트에서는 사용되지 않음).

        Returns:
            action_space에서 무작위로 선택된 행동입니다.
            torchrl.data.TensorSpec.sample()을 사용하면 보통 Tensor가 반환됩니다.
        """
        if hasattr(self.action_space, 'sample') and callable(getattr(self.action_space, 'sample')):
            # torchrl.data.TensorSpec (e.g., DiscreteTensorSpec, ContinuousTensorSpec)
            # 또는 gym.spaces.Space 와 같은 경우 .sample() 메소드를 사용합니다.
            return self.action_space.sample()
        elif isinstance(self.action_space, list):
            # action_space가 리스트인 경우 (기존 방식 지원)
            if not self.action_space:
                raise ValueError("Action space is an empty list. Cannot select an action.")
            action = random.choice(self.action_space)
            # torchrl 환경에서는 action도 Tensor 형태를 기대할 수 있으므로 변환을 고려할 수 있습니다.
            # 예를 들어, action_spec을 통해 dtype 등을 확인하고 Tensor로 변환:
            # if hasattr(self.action_space, 'dtype'): # action_space가 spec 객체일 때
            #    return torch.tensor(action, dtype=self.action_space.dtype)
            return action # 현재는 Python 기본 타입으로 반환
        else:
            raise TypeError(
                f"Unsupported action_space type: {type(self.action_space)}. "
                f"Expected a torchrl TensorSpec, a gym Space, or a list."
            )

# 사용 예시 (테스트 목적):
if __name__ == '__main__':
    # 예시 1: torchrl의 DiscreteTensorSpec 사용
    # from torchrl.data import DiscreteTensorSpec # 이 예시는 아직 주석 처리 유지
    # discrete_action_spec = DiscreteTensorSpec(n=4) # 4개의 이산적인 행동
    # agent1 = RandomAgent(action_space=discrete_action_spec)
    # random_action_tensor = agent1.select_action(None) # 상태는 무관
    # print(f"Selected action (from DiscreteTensorSpec): {random_action_tensor}, type: {type(random_action_tensor)}")

    # 예시 2: 구체적인 게임 액션(8방향 이동 + 공격)을 사용한 RandomAgent
    # 액션 정의:
    #   0: 좌상 (Up-Left),    1: 상 (Up),    2: 우상 (Up-Right)
    #   3: 좌 (Left),                     4: 우 (Right)
    #   5: 좌하 (Down-Left),  6: 하 (Down),  7: 우하 (Down-Right)
    #   8: 공격 (Attack)
    game_actions = list(range(9))  # 총 9개의 액션 (0부터 8까지)
    agent_game_specific = RandomAgent(action_space=game_actions)

    # 임의의 상태 (RandomAgent는 상태를 사용하지 않음)
    current_game_state = "some_game_state_representation"

    print("\n--- Game-Specific RandomAgent Test (8-directional move + attack) ---")
    action_names = [
        "Move Up-Left", "Move Up", "Move Up-Right",
        "Move Left", "Move Right",
        "Move Down-Left", "Move Down", "Move Down-Right",
        "Attack"
    ]
    for i in range(5): # 5번의 행동 선택 예시
        selected_action_id = agent_game_specific.select_action(current_game_state)
        print(f"Trial {i+1}: Selected action ID: {selected_action_id}, Meaning: {action_names[selected_action_id]}")

    # 예시 3: gym.spaces 사용 (만약 gym도 함께 사용한다면)
    # import gymnasium as gym # 이 예시는 아직 주석 처리 유지
    # from gymnasium.spaces import Discrete
    # gym_discrete_space = Discrete(4)
    # agent3 = RandomAgent(action_space=gym_discrete_space)
    # selected_action_gym = agent3.select_action(None)
    # print(f"Selected action (from gym.space): {selected_action_gym}, type: {type(selected_action_gym)}") 