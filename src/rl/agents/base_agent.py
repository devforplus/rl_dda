from abc import ABC, abstractmethod

class BaseAgent(ABC):
    """
    모든 에이전트 클래스를 위한 추상 기본 클래스입니다.
    """
    def __init__(self, action_space):
        """
        에이전트를 초기화합니다.

        Args:
            action_space: 에이전트가 선택할 수 있는 가능한 행동의 공간입니다.
                          (예: 리스트, gym.spaces.Space 객체, torchrl.data.TensorSpec 등)
        """
        self.action_space = action_space

    @abstractmethod
    def select_action(self, state):
        """
        주어진 상태(state)에 따라 행동(action)을 선택합니다.
        이 메소드는 하위 클래스에서 반드시 구현되어야 합니다.

        Args:
            state: 환경으로부터 관찰된 현재 상태입니다.
                   (예: numpy 배열, PyTorch Tensor 등)

        Returns:
            선택된 행동입니다.
        """
        pass

    # 향후 필요에 따라 다음 메소드들을 추가할 수 있습니다.
    # @abstractmethod
    # def train(self, experiences):
    #     """
    #     주어진 경험(experiences)을 사용하여 에이전트를 훈련합니다.
    #     """
    #     pass

    # @abstractmethod
    # def save_model(self, path):
    #     """
    #     에이전트의 모델을 지정된 경로에 저장합니다.
    #     """
    #     pass

    # @abstractmethod
    # def load_model(self, path):
    #     """
    #     지정된 경로에서 에이전트의 모델을 불러옵니다.
    #     """
    #     pass 