"""
TorchRL과 통합되는 개선된 VORTEXION 게임 환경 래퍼
게임 인터페이스 문제를 해결
"""

import torch
import numpy as np
import time
from torchrl.envs import EnvBase
from tensordict import TensorDict
from torchrl.data import BoundedTensorSpec, CompositeSpec, UnboundedContinuousTensorSpec

class FixedVortexionEnv(EnvBase):
    """
    VORTEXION 게임을 위한 개선된 강화학습 환경 래퍼
    기존 문제점을 해결하기 위한 수정 버전
    """
    
    def __init__(self, game_instance):
        """
        환경 초기화
        
        Args:
            game_instance: 게임 인스턴스
        """
        super().__init__()
        self.game = game_instance
        self._setup_specs()
        
        # 게임 상태 추적
        self.is_game_started = False
        self.reset_count = 0
        self.total_reward = 0.0
        self.current_lives = 3  # 기본 생명 수
        self.current_score = 0
        
        # 디버깅
        self.debug_mode = True
        
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
        # 단순화된 관찰 공간으로 수정 - 사용 가능한 정보만 포함
        self.observation_spec = CompositeSpec(
            {
                "player_pos": BoundedTensorSpec(
                    shape=(2,),  # x, y 좌표
                    dtype=torch.float32,
                    low=torch.tensor([0, 0]),
                    high=torch.tensor([255, 191]),  # 게임 해상도 기준
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
        if self.debug_mode:
            print(f"\n===== 환경 리셋 (#{self.reset_count}) =====")
        
        self.reset_count += 1
        self.total_reward = 0.0
        
        # 게임이 이미 실행 중인 경우를 처리
        if hasattr(self.game, 'state'):
            state_name = self.game.state.__class__.__name__
            
            if "GameStateStage" in state_name:
                # 이미 게임 스테이지에 있으므로 타이틀로 돌아갔다가 다시 시작
                if self.debug_mode:
                    print("게임 스테이지에서 타이틀로 돌아갑니다...")
                self.game.go_to_titles()
                
                # 게임 상태 업데이트를 위해 몇 프레임 실행
                for _ in range(5):
                    self.game.update()
                    time.sleep(0.1)
        
        # 타이틀 화면으로 이동 확인
        if hasattr(self.game, 'state') and "GameStateTitles" in self.game.state.__class__.__name__:
            if self.debug_mode:
                print("타이틀 화면 감지됨, 게임 시작 중...")
            
            # 타이틀 화면에서 게임 시작 명령
            input_system = self.game.app.input
            
            # 입력 초기화
            input_system.up_pressed = False
            input_system.down_pressed = False
            input_system.left_pressed = False
            input_system.right_pressed = False
            input_system.fire_pressed = False
            input_system.z_pressed = False
            
            # 타이틀 화면 로딩 대기
            if self.debug_mode:
                print("타이틀 화면 로딩 대기...")
            
            for _ in range(8):
                self.game.update()
                time.sleep(0.1)
            
            # GAME START 선택 (기본적으로 이미 선택되어 있을 것)
            if self.debug_mode:
                print("GAME START 선택 중...")
            
            # Z키(버튼1) 누르기 - GAME START 선택
            input_system.z_pressed = True
            input_system.fire_pressed = True
            
            # 충분한 시간 동안 버튼 누름 유지
            for _ in range(5):
                self.game.update()
                time.sleep(0.1)
            
            # 버튼 해제
            input_system.z_pressed = False
            input_system.fire_pressed = False
            
            # 게임이 시작될 때까지 대기
            if self.debug_mode:
                print("게임 시작 대기 중...")
            
            max_wait = 30  # 최대 대기 프레임 수
            for i in range(max_wait):
                self.game.update()
                time.sleep(0.1)
                
                # 게임 스테이지로 전환 확인
                if hasattr(self.game, 'state') and "GameStateStage" in self.game.state.__class__.__name__:
                    self.is_game_started = True
                    if self.debug_mode:
                        print(f"게임 스테이지 감지됨 ({i+1}번째 프레임)")
                    break
                
                if i == max_wait - 1:
                    print("경고: 최대 대기 시간 초과, 게임 스테이지가 감지되지 않았습니다.")
        
        # 초기 상태 리셋
        self.current_lives = 3  # 기본 생명 수 
        self.current_score = 0
        
        # 초기 관찰값 반환
        initial_obs = self._get_observation()
        
        if self.debug_mode:
            print("환경 리셋 완료!\n")
            
        return initial_obs
    
    def _step(self, tensordict):
        """
        환경에서 한 스텝 진행
        
        Args:
            tensordict: 행동 정보를 포함한 TensorDict

        Returns:
            TensorDict: 관측, 보상, 종료 상태 등의 정보
        """
        # 실제 게임이 시작되지 않았다면 재시도
        if not self.is_game_started:
            if self.debug_mode:
                print("경고: 게임이 아직 시작되지 않았습니다. 리셋을 다시 시도합니다.")
            return self.reset()
        
        # 행동 추출 및 적용
        action = tensordict["action"]
        movement = action[0].item()  # 0: 왼쪽, 1: 정지, 2: 오른쪽
        shooting = action[1].item()  # 0: 발사 안함, 1: 발사
        
        if self.debug_mode:
            move_str = "왼쪽" if movement == 0 else ("정지" if movement == 1 else "오른쪽")
            shoot_str = "발사" if shooting == 1 else "대기"
            print(f"액션: {move_str} + {shoot_str}")
        
        # 입력 적용
        self._apply_action(movement, shooting)
        
        # 게임 상태 이전 정보 저장
        prev_lives = self.current_lives
        prev_score = self.current_score
        
        # 게임 프레임 업데이트
        self.game.update()
        
        # 게임 상태 변화 감지 및 정보 갱신
        if hasattr(self.game, 'game_vars'):
            current_score = self.game.game_vars.score
            current_lives = self.game.game_vars.lives
            
            # 점수와 생명력 변화 추적
            score_change = current_score - self.current_score
            lives_change = current_lives - prev_lives
            
            self.current_score = current_score
            self.current_lives = current_lives
            
            if self.debug_mode and score_change != 0:
                print(f"점수 변화: {score_change:+}")
                
            if self.debug_mode and lives_change != 0:
                print(f"생명력 변화: {lives_change:+}")
        
        # 관찰, 보상, 종료 여부 계산
        observation = self._get_observation()
        reward = self._compute_reward(score_change, lives_change)
        done = self._is_done()
        
        # 총 보상 누적
        self.total_reward += reward.item()
        
        # 결과 반환
        result = TensorDict(
            {
                **observation,
                "reward": reward,
                "done": torch.tensor([done], dtype=torch.bool),
            },
            batch_size=[],
        )
        
        if self.debug_mode and done:
            print(f"\n===== 에피소드 종료 - 총 보상: {self.total_reward:.2f} =====\n")
        
        return result
    
    def _apply_action(self, movement, shooting):
        """
        행동을 게임 입력으로 변환
        
        Args:
            movement: 이동 방향 (0: 왼쪽, 1: 정지, 2: 오른쪽)
            shooting: 발사 여부 (0: 발사 안함, 1: 발사)
        """
        # 게임 입력 시스템 접근
        input_system = self.game.app.input
        
        # 모든 입력 초기화
        input_system.left_pressed = False
        input_system.right_pressed = False
        input_system.up_pressed = False
        input_system.down_pressed = False
        input_system.fire_pressed = False
        input_system.z_pressed = False
        
        # 이동 설정
        if movement == 0:  # 왼쪽
            input_system.left_pressed = True
        elif movement == 2:  # 오른쪽
            input_system.right_pressed = True
            
        # 발사 설정
        if shooting == 1:
            input_system.fire_pressed = True
            input_system.z_pressed = True
    
    def _get_observation(self):
        """
        현재 게임 상태로부터 관찰값 생성
        
        Returns:
            TensorDict: 게임 상태 정보
        """
        # 플레이어 위치 (기본값)
        player_x, player_y = 128, 170
        
        # 실제 게임에서 플레이어 위치 추출 시도
        try:
            if hasattr(self.game, 'state') and hasattr(self.game.state, 'player'):
                player = self.game.state.player
                if player is not None:
                    player_x = float(player.x)
                    player_y = float(player.y)
        except:
            # 추출 실패시 기본값 사용
            pass
        
        # 플레이어 생명력 및 점수 설정
        player_lives = torch.tensor([self.current_lives], dtype=torch.int64)
        score = torch.tensor([float(self.current_score)], dtype=torch.float32)
        
        # 관측값 텐서딕트 구성
        observation = TensorDict(
            {
                "player_pos": torch.tensor([player_x, player_y], dtype=torch.float32),
                "player_lives": player_lives,
                "score": score,
            },
            batch_size=[],
        )
        
        return observation
    
    def _compute_reward(self, score_change=0, lives_change=0):
        """
        보상 계산
        
        Args:
            score_change: 점수 변화량
            lives_change: 생명력 변화량
            
        Returns:
            torch.Tensor: 계산된 보상
        """
        # 기본 보상
        reward = 0.0
        
        # 점수 증가에 따른 보상
        if score_change > 0:
            reward += score_change * 0.01  # 점수 증가에 비례한 보상
        
        # 생명력 감소에 따른 패널티
        if lives_change < 0:
            reward -= 1.0  # 생명력 감소 시 큰 패널티
        
        # 생존 보상 (작은 양의 보상)
        reward += 0.01
        
        return torch.tensor([reward], dtype=torch.float32)
    
    def _is_done(self):
        """
        에피소드 종료 여부 확인
        
        Returns:
            bool: 종료되었으면 True, 아니면 False
        """
        # 생명력이 0이하면 종료
        if self.current_lives <= 0:
            return True
        
        # 게임이 더 이상 스테이지 상태가 아니면 종료
        if hasattr(self.game, 'state') and "GameStateStage" not in self.game.state.__class__.__name__:
            return True
        
        return False
    
    def _set_seed(self, seed=None):
        """
        환경의 랜덤 시드 설정
        
        Args:
            seed: 설정할 시드 값
            
        Returns:
            int: 설정된 시드 값
        """
        if seed is not None:
            torch.manual_seed(seed)
            np.random.seed(seed)
            
        return seed 