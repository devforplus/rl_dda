import torch
import numpy as np
from torchrl.envs import EnvBase
from tensordict import TensorDict
from torchrl.data import BoundedTensorSpec, CompositeSpec, UnboundedContinuousTensorSpec
import time

class VortexionEnv(EnvBase):
    """
    VORTEXION 게임을 위한 강화학습 환경 래퍼
    """
    
    def __init__(self, game_instance):
        super().__init__()
        self.game = game_instance
        self._setup_specs()
        
    def _setup_specs(self):
        """액션 및 관찰 공간 설정"""
        # 액션 공간: 이동(좌, 우, 정지), 발사(발사, 정지)
        self.action_spec = BoundedTensorSpec(
            shape=(2,),
            dtype=torch.int64,
            low=torch.tensor([0, 0]),
            high=torch.tensor([2, 1]),
        )
        
        # 관찰 공간 (게임 상태 정보)
        self.observation_spec = CompositeSpec(
            {
                "player_pos": BoundedTensorSpec(
                    shape=(2,),  # x, y 좌표
                    dtype=torch.float32,
                    low=torch.tensor([0, 0]),
                    high=torch.tensor([255, 191]),  # 게임 해상도 기준
                ),
                "enemies": UnboundedContinuousTensorSpec(
                    shape=(10, 4),  # 최대 10개 적, 각 적마다 (x, y, 너비, 높이)
                    dtype=torch.float32,
                ),
                "enemy_shots": UnboundedContinuousTensorSpec(
                    shape=(20, 2),  # 최대 20개 적 발사체, 각각 (x, y)
                    dtype=torch.float32,
                ),
                "player_shots": UnboundedContinuousTensorSpec(
                    shape=(5, 2),  # 최대 5개 플레이어 발사체, 각각 (x, y)
                    dtype=torch.float32,
                ),
                "game_stage": BoundedTensorSpec(
                    shape=(1,),
                    dtype=torch.int64,
                    low=torch.tensor([0]),
                    high=torch.tensor([10]),  # 최대 10개 스테이지 가정
                ),
                "player_lives": BoundedTensorSpec(
                    shape=(1,),
                    dtype=torch.int64,
                    low=torch.tensor([0]),
                    high=torch.tensor([5]),  # 최대 생명력
                ),
                "score": UnboundedContinuousTensorSpec(
                    shape=(1,),
                    dtype=torch.float32,
                ),
            },
            shape=(),
        )
        
        # 리워드 스펙
        self.reward_spec = UnboundedContinuousTensorSpec(
            shape=(1,),
            dtype=torch.float32,
        )
        
    def _reset(self, tensordict=None):
        """환경 리셋"""
        print("환경 리셋 시작...")
        
        # 게임 재시작 로직
        try:
            print("타이틀 화면으로 이동...")
            self.game.go_to_titles()
            
            # 타이틀 화면에서 메뉴 처리를 위한 준비
            print("입력 시스템 접근...")
            input_system = self.game.app.input
            
            # 타이틀 화면에서 조금 대기 (화면이 완전히 로드되도록)
            print("타이틀 화면 로딩 대기...")
            for i in range(10):
                self.game.update()
                time.sleep(0.1)
            
            # 위쪽 화살표를 눌러 'GAME START' 메뉴 항목으로 이동 (이미 선택되어 있을 수도 있지만 확실히 하기 위해)
            print("위쪽 화살표키 누름 (GAME START 선택)...")
            input_system.up_pressed = True
            
            # 몇 프레임 실행하여 입력 처리
            for i in range(3):
                self.game.update()
                time.sleep(0.05)
            
            # 키 해제
            input_system.up_pressed = False
            
            # 조금 더 대기
            for i in range(2):
                self.game.update()
                time.sleep(0.05)
            
            # Z키(BUTTON_1) 누르기 - GAME START 선택
            print("Z키 누름 (GAME START 선택)...")
            input_system.z_pressed = True
            input_system.fire_pressed = True
            
            # 충분한 프레임 동안 키 입력 유지
            for i in range(5):
                print(f"프레임 {i+1}/5 업데이트...")
                self.game.update()
                time.sleep(0.1)
            
            # 버튼 해제
            print("버튼 해제...")
            input_system.z_pressed = False
            input_system.fire_pressed = False
            
            # 게임이 시작될 때까지 대기
            print("게임 시작 대기 중...")
            for i in range(20):  # 더 많은 프레임 동안 대기
                self.game.update()
                time.sleep(0.1)
                
                # 여기서 게임이 실제로 시작되었는지 확인할 수 있으면 좋음
                # 예: if hasattr(self.game, 'state') and self.game.state.__class__.__name__ == 'GameStateStage':
                #       break
            
            print("게임 환경 초기화 완료!")
            
            # 초기 관찰값 반환
            print("관찰값 생성...")
            obs = self._get_observation()
            print("환경 리셋 완료!")
            return obs
        except Exception as e:
            print(f"환경 리셋 중 오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            raise
    
    def _step(self, tensordict):
        """
        환경에서 한 스텝 진행
        
        Args:
            tensordict: 행동 정보를 포함한 TensorDict

        Returns:
            TensorDict: 관측, 보상, 종료 상태 등의 정보
        """
        action = tensordict["action"]
        
        # 행동 디코딩 및 적용
        movement = action[0].item()  # 0: 왼쪽, 1: 정지, 2: 오른쪽
        shooting = action[1].item()  # 0: 발사 안함, 1: 발사
        
        print(f"\n=== 스텝 시작: 액션 [이동={movement}, 발사={shooting}] ===")
        
        # 입력 적용 (실제 게임 코드와 연결 필요)
        self._apply_action(movement, shooting)
        
        # 게임 업데이트 (이전에는 3프레임이었으나 1프레임으로 축소)
        print("게임 프레임 업데이트 중...")
        self.game.update()
        
        # 결과 수집
        observation = self._get_observation()
        reward = self._compute_reward()
        done = self._is_done()
        
        # 결과 반환
        result = TensorDict(
            {
                **observation,
                "reward": reward,
                "done": torch.tensor([done], dtype=torch.bool),
            },
            batch_size=[],
        )
        
        print(f"=== 스텝 완료: 보상={reward.item():.2f}, 종료={done} ===\n")
        
        return result
    
    def _apply_action(self, movement, shooting):
        """
        행동을 게임 입력으로 변환
        
        Args:
            movement: 이동 방향 (0: 왼쪽, 1: 정지, 2: 오른쪽)
            shooting: 발사 여부 (0: 발사 안함, 1: 발사)
        """
        # 여기서 게임의 실제 입력 시스템과 연결 필요
        input_system = self.game.app.input
        
        # 모든 입력 초기화 (이전 액션의 잔류 상태를 방지)
        input_system.left_pressed = False
        input_system.right_pressed = False
        input_system.up_pressed = False
        input_system.down_pressed = False
        input_system.fire_pressed = False
        input_system.z_pressed = False
        
        # 이동 설정
        if movement == 0:  # 왼쪽
            input_system.left_pressed = True
            print("왼쪽 버튼 누름")
        elif movement == 2:  # 오른쪽
            input_system.right_pressed = True
            print("오른쪽 버튼 누름")
        else:  # 정지
            print("이동 버튼 모두 해제 (정지)")
            
        # 발사 설정
        if shooting == 1:
            input_system.fire_pressed = True
            input_system.z_pressed = True  # Z키도 함께 설정
            print("발사 버튼 누름")
        else:
            print("발사 버튼 해제")
            
        # 입력 상태 확인 출력
        print(f"현재 입력 상태 - 왼쪽: {input_system.left_pressed}, 오른쪽: {input_system.right_pressed}, 발사: {input_system.fire_pressed}")
    
    def _get_observation(self):
        """
        현재 게임 상태로부터 관찰값 생성
        
        Returns:
            TensorDict: 게임 상태 정보
        """
        # 실제 게임 데이터 추출 로직 구현 필요
        # 여기서는 단순화된 예시 제공
        
        # 게임 상태 객체 및 변수 참조
        game_vars = self.game.game_vars
        current_state = self.game.state
        
        # 플레이어 정보 (예시)
        player_x = 128  # 임시값
        player_y = 170  # 임시값
        
        if hasattr(current_state, "player"):
            player = current_state.player
            player_x = player.x
            player_y = player.y
        
        # 적 정보 (최대 10개까지)
        enemies_tensor = torch.zeros((10, 4), dtype=torch.float32)
        
        # 적 발사체 정보 (최대 20개)
        enemy_shots_tensor = torch.zeros((20, 2), dtype=torch.float32)
        
        # 플레이어 발사체 정보 (최대 5개)
        player_shots_tensor = torch.zeros((5, 2), dtype=torch.float32)
        
        # 기타 게임 상태 정보
        stage = game_vars.current_stage if hasattr(game_vars, "current_stage") else 0
        lives = game_vars.lives if hasattr(game_vars, "lives") else 3
        score = game_vars.score if hasattr(game_vars, "score") else 0
        
        # TensorDict로 변환하여 반환
        return TensorDict(
            {
                "player_pos": torch.tensor([player_x, player_y], dtype=torch.float32),
                "enemies": enemies_tensor,
                "enemy_shots": enemy_shots_tensor,
                "player_shots": player_shots_tensor,
                "game_stage": torch.tensor([stage], dtype=torch.int64),
                "player_lives": torch.tensor([lives], dtype=torch.int64),
                "score": torch.tensor([score], dtype=torch.float32),
            },
            batch_size=[],
        )
    
    def _compute_reward(self):
        """
        보상 계산
        
        Returns:
            torch.Tensor: 보상값
        """
        # 간단한 보상 체계 (예시)
        # 1. 적 격추: +10
        # 2. 생존 시간: +0.1/프레임
        # 3. 피격: -5
        # 4. 게임 종료: -20
        
        # 실제 게임 데이터 기반 보상 계산 필요
        # 현재는 임시 상수값 반환
        return torch.tensor([0.1], dtype=torch.float32)
    
    def _is_done(self):
        """
        게임 종료 조건 확인
        
        Returns:
            bool: 게임 종료 여부
        """
        # 게임 변수에서 종료 조건 확인
        # 1. 모든 생명 소진
        # 2. 게임 완료
        
        game_vars = self.game.game_vars
        lives = game_vars.lives if hasattr(game_vars, "lives") else 0
        
        # 생명이 0이면 게임 종료
        return lives <= 0
    
    def _set_seed(self, seed=None):
        """시드 설정 (랜덤성 제어)"""
        # 게임 내부 랜덤 시드 설정 (필요시)
        return seed 