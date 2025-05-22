import random
import platform # platform 모듈 임포트

IS_WEB = platform.system() == "Emscripten"

if not IS_WEB:
    try:
        import torch # torchrl 사용을 가정하므로 torch 임포트 추가
        # from torchrl.data import TensorSpec # 필요한 경우 특정 Spec 임포트
    except ImportError:
        # print("Warning: PyTorch (torch) not found. Some features might be unavailable if torchrl is intended.")
        pass # 웹 환경이 아니지만 torch가 없는 경우, 일단 진행

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
            return self.action_space.sample()
        elif isinstance(self.action_space, list):
            if not self.action_space:
                raise ValueError("Action space is an empty list. Cannot select an action.")
            action = random.choice(self.action_space)
            # 웹 환경이 아니고 torch가 로드되었다면 텐서 변환을 고려할 수 있습니다.
            # if not IS_WEB and 'torch' in globals() and hasattr(self.action_space, 'dtype'):
            #    return torch.tensor(action, dtype=self.action_space.dtype)
            return action
        else:
            raise TypeError(
                f"Unsupported action_space type: {type(self.action_space)}. "
                f"Expected a torchrl TensorSpec, a gym Space, or a list."
            )

# 사용 예시 (테스트 목적):
if __name__ == '__main__':
    # 예시 코드는 torchrl 또는 gymnasium을 직접 임포트하므로,
    # 이 스크립트를 직접 실행할 때는 해당 라이브러리가 설치되어 있어야 합니다.
    # 웹 환경에서는 이 __main__ 블록이 직접 실행되지 않을 것입니다.

    # 예시 1: torchrl의 DiscreteTensorSpec 사용 (로컬에서 torchrl 설치 시 테스트 가능)
    # if not IS_WEB:
    #     try:
    #         from torchrl.data import DiscreteTensorSpec
    #         discrete_action_spec = DiscreteTensorSpec(n=4)
    #         agent1 = RandomAgent(action_space=discrete_action_spec)
    #         random_action_tensor = agent1.select_action(None)
    #         print(f"Selected action (from DiscreteTensorSpec): {random_action_tensor}, type: {type(random_action_tensor)}")
    #     except ImportError:
    #         print("torchrl not installed, skipping DiscreteTensorSpec example.")

    # 예시 2: 구체적인 게임 액션(8방향 이동 + 공격)을 사용한 RandomAgent
    game_actions = list(range(9))
    agent_game_specific = RandomAgent(action_space=game_actions)
    current_game_state = "some_game_state_representation"
    print("\n--- Game-Specific RandomAgent Test (8-directional move + attack) ---")
    action_names = [
        "Move Up-Left", "Move Up", "Move Up-Right",
        "Move Left", "Move Right",
        "Move Down-Left", "Move Down", "Move Down-Right",
        "Attack"
    ]
    for i in range(5):
        selected_action_id = agent_game_specific.select_action(current_game_state)
        print(f"Trial {i+1}: Selected action ID: {selected_action_id}, Meaning: {action_names[selected_action_id]}")

    # 예시 3: gym.spaces 사용 (로컬에서 gymnasium 설치 시 테스트 가능)
    # if not IS_WEB:
    #     try:
    #         import gymnasium as gym
    #         from gymnasium.spaces import Discrete
    #         gym_discrete_space = Discrete(4)
    #         agent3 = RandomAgent(action_space=gym_discrete_space)
    #         selected_action_gym = agent3.select_action(None)
    #         print(f"Selected action (from gym.space): {selected_action_gym}, type: {type(selected_action_gym)}")
    #     except ImportError:
    #         print("gymnasium not installed, skipping gym.spaces example.") 