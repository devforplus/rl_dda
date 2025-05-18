"""
게임 상태를 감지하고 분석하는 도구
게임 디버깅 및 환경에 대한 이해를 위한 보조 도구
"""

import sys
import os
import time
import inspect
import pyxel as px

# 현재 디렉토리를 경로에 추가
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

from main import App

class GameStateDetector:
    """
    VORTEXION 게임의 상태를 감지하고 분석하는 도구
    게임 메모리 구조와 상태 변화를 이해하기 위한 디버깅 도구
    """
    
    def __init__(self, app=None):
        """
        게임 상태 감지기 초기화
        
        Args:
            app: 기존 게임 앱 인스턴스 (기본값: None - 새로 생성)
        """
        # 게임 앱 초기화 또는 설정
        self.app = app
        if self.app is None:
            print("새 게임 애플리케이션 생성 중...")
            
            # 원본 pyxel.run 메서드 백업
            original_run = px.run
            
            # pyxel.run 메서드 오버라이드 (무한 루프 방지)
            def custom_run(update_func, draw_func):
                print("게임 루프 오버라이드됨 - 상태 감지기가 게임을 제어합니다.")
            
            # 메서드 대체 후 게임 생성
            px.run = custom_run
            self.app = App()
            
            # 원본 메서드 복원
            px.run = original_run
        
        # 게임 객체 참조
        self.game = self.app.game
        
        # 입력 시스템 참조
        self.input = self.app.input
    
    def detect_game_state(self):
        """현재 게임 상태 정보 출력"""
        print("\n===== 게임 상태 감지 =====")
        
        # 게임 객체 구조 확인
        if hasattr(self.game, 'state'):
            state_obj = self.game.state
            state_class = state_obj.__class__.__name__
            
            print(f"현재 게임 상태: {state_class}")
            
            # 게임 상태별 특수 정보 출력
            if "GameStateTitles" in state_class:
                self._inspect_title_screen(state_obj)
            elif "GameStateStage" in state_class:
                self._inspect_game_stage(state_obj)
            elif "GameStateComplete" in state_class:
                self._inspect_game_complete(state_obj)
            else:
                print(f"알 수 없는 게임 상태: {state_class}")
        else:
            print("게임 상태 객체를 찾을 수 없습니다.")
        
        # 게임 변수 출력
        self._inspect_game_vars()
        
        print("===== 게임 상태 감지 완료 =====\n")
    
    def _inspect_title_screen(self, state_obj):
        """타이틀 화면 상태 검사"""
        print("타이틀 화면 정보:")
        
        # 메뉴 항목 및 선택된 항목 확인
        if hasattr(state_obj, 'menu_index'):
            print(f"  선택된 메뉴: {state_obj.menu_index}")
        
        # 기타 타이틀 화면 관련 속성 검사
        for name, value in inspect.getmembers(state_obj):
            if not name.startswith('_') and not inspect.ismethod(value) and not inspect.isfunction(value):
                if name not in ['game']:  # 게임 객체 제외 (너무 많은 정보)
                    print(f"  {name}: {value}")
    
    def _inspect_game_stage(self, state_obj):
        """게임 스테이지 정보 검사"""
        print("게임 스테이지 정보:")
        
        # 플레이어 정보 출력
        if hasattr(state_obj, 'player'):
            player = state_obj.player
            if player is not None:
                print(f"  플레이어 위치: ({player.x}, {player.y})")
                
                # 플레이어 속성 출력
                for name, value in inspect.getmembers(player):
                    if not name.startswith('_') and not inspect.ismethod(value) and not inspect.isfunction(value):
                        print(f"    {name}: {value}")
        
        # 적 정보 출력
        if hasattr(state_obj, 'enemies'):
            enemies = state_obj.enemies
            print(f"  적 수: {len(enemies)}")
            for i, enemy in enumerate(enemies[:3]):  # 처음 몇 개만 출력
                print(f"    적 {i+1}: 유형={enemy.__class__.__name__}, 위치=({enemy.x}, {enemy.y})")
        
        # 발사체 정보 출력
        if hasattr(state_obj, 'player_shots'):
            shots = state_obj.player_shots
            print(f"  플레이어 발사체 수: {len(shots)}")
        
        if hasattr(state_obj, 'enemy_shots'):
            shots = state_obj.enemy_shots
            print(f"  적 발사체 수: {len(shots)}")
    
    def _inspect_game_complete(self, state_obj):
        """게임 완료 화면 검사"""
        print("게임 완료 정보:")
        
        # 완료 화면 관련 속성 출력
        for name, value in inspect.getmembers(state_obj):
            if not name.startswith('_') and not inspect.ismethod(value) and not inspect.isfunction(value):
                if name not in ['game']:  # 게임 객체 제외
                    print(f"  {name}: {value}")
    
    def _inspect_game_vars(self):
        """게임 변수 검사"""
        if hasattr(self.game, 'game_vars'):
            vars_obj = self.game.game_vars
            print("게임 변수 정보:")
            
            # 중요 게임 변수 출력
            important_vars = ['score', 'lives', 'stage']
            for var in important_vars:
                if hasattr(vars_obj, var):
                    print(f"  {var}: {getattr(vars_obj, var)}")
            
            # 기타 게임 변수 출력
            for name, value in inspect.getmembers(vars_obj):
                if not name.startswith('_') and not inspect.ismethod(value) and not inspect.isfunction(value):
                    if name not in important_vars and name not in ['game']:
                        print(f"  {name}: {value}")
    
    def simulate_game_cycle(self, num_frames=1):
        """
        게임 프레임 시뮬레이션
        
        Args:
            num_frames: 시뮬레이션할 프레임 수
        """
        print(f"{num_frames}개 프레임 시뮬레이션 시작...")
        
        for i in range(num_frames):
            # 입력 업데이트
            self.app.input.update()
            
            # 게임 상태 업데이트
            self.game.update()
            
            # 프레임 정보 출력 (처음, 마지막, 10프레임마다)
            if i == 0 or i == num_frames - 1 or (i + 1) % 10 == 0:
                print(f"프레임 {i+1}/{num_frames} 처리됨")
            
            # 짧은 대기 (너무 빠른 실행 방지)
            time.sleep(0.05)
        
        print(f"{num_frames}개 프레임 시뮬레이션 완료")
    
    def press_button(self, button_name, duration_frames=5):
        """
        버튼 입력 시뮬레이션
        
        Args:
            button_name: 버튼 이름 ('up', 'down', 'left', 'right', 'z', 'x')
            duration_frames: 버튼을 누르는 프레임 수
        """
        print(f"{button_name} 버튼 {duration_frames}프레임 동안 누름")
        
        # 버튼 누르기
        if button_name == 'up':
            self.input.up_pressed = True
        elif button_name == 'down':
            self.input.down_pressed = True
        elif button_name == 'left':
            self.input.left_pressed = True
        elif button_name == 'right':
            self.input.right_pressed = True
        elif button_name == 'z':
            self.input.z_pressed = True
            self.input.fire_pressed = True
        elif button_name == 'x':
            pass  # 필요시 구현
        
        # 지정된 프레임 동안 업데이트
        self.simulate_game_cycle(duration_frames)
        
        # 버튼 떼기
        if button_name == 'up':
            self.input.up_pressed = False
        elif button_name == 'down':
            self.input.down_pressed = False
        elif button_name == 'left':
            self.input.left_pressed = False
        elif button_name == 'right':
            self.input.right_pressed = False
        elif button_name == 'z':
            self.input.z_pressed = False
            self.input.fire_pressed = False
        elif button_name == 'x':
            pass  # 필요시 구현
        
        # 추가 프레임 실행 (입력 해제 처리)
        self.simulate_game_cycle(2)
    
    def start_game_from_title(self):
        """타이틀 화면에서 게임 시작"""
        print("타이틀 화면에서 게임 시작 시도...")
        
        # 현재 게임 상태 확인
        if hasattr(self.game, 'state') and "GameStateTitles" in self.game.state.__class__.__name__:
            # 게임 시작 버튼 누르기
            self.press_button('z', 10)
            
            # 게임 로딩 대기
            self.simulate_game_cycle(20)
            
            # 상태 확인
            if hasattr(self.game, 'state') and "GameStateStage" in self.game.state.__class__.__name__:
                print("게임이 성공적으로 시작되었습니다!")
                return True
            else:
                print("게임 시작 실패 - 스테이지로 전환되지 않았습니다.")
                return False
        else:
            print("타이틀 화면이 아닙니다. 먼저 타이틀 화면으로 이동하세요.")
            return False
    
    def go_to_title_screen(self):
        """타이틀 화면으로 이동"""
        print("타이틀 화면으로 이동 중...")
        
        # 게임 변수 및 직접 호출
        self.game.go_to_titles()
        
        # 상태 전환 대기
        self.simulate_game_cycle(10)
        
        # 상태 확인
        if hasattr(self.game, 'state') and "GameStateTitles" in self.game.state.__class__.__name__:
            print("타이틀 화면으로 이동 성공!")
            return True
        else:
            print("타이틀 화면 전환 실패")
            return False
    
    def run_interactive_mode(self):
        """대화형 모드 실행"""
        print("\n===== 게임 상태 감지기 대화형 모드 =====")
        print("다음 명령어를 사용할 수 있습니다:")
        print("  state - 현재 게임 상태 출력")
        print("  update [n] - n개의 프레임 시뮬레이션 (기본: 1)")
        print("  press <button> [n] - 버튼 누르기 (버튼: up/down/left/right/z/x, 프레임 수: n)")
        print("  title - 타이틀 화면으로 이동")
        print("  start - 타이틀 화면에서 게임 시작")
        print("  quit - 종료")
        
        while True:
            cmd = input("\n명령어 입력: ").strip().lower()
            
            if cmd == 'quit' or cmd == 'exit':
                break
                
            elif cmd == 'state':
                self.detect_game_state()
                
            elif cmd.startswith('update'):
                parts = cmd.split()
                frames = 1
                if len(parts) > 1:
                    try:
                        frames = int(parts[1])
                    except:
                        pass
                self.simulate_game_cycle(frames)
                
            elif cmd.startswith('press'):
                parts = cmd.split()
                if len(parts) < 2:
                    print("버튼을 지정하세요: up, down, left, right, z, x")
                    continue
                
                button = parts[1]
                frames = 5
                if len(parts) > 2:
                    try:
                        frames = int(parts[2])
                    except:
                        pass
                
                if button in ['up', 'down', 'left', 'right', 'z', 'x']:
                    self.press_button(button, frames)
                else:
                    print(f"알 수 없는 버튼: {button}")
                    
            elif cmd == 'title':
                self.go_to_title_screen()
                
            elif cmd == 'start':
                self.start_game_from_title()
                
            else:
                print(f"알 수 없는 명령어: {cmd}")
        
        print("대화형 모드 종료")

def main():
    """메인 함수"""
    print("게임 상태 감지기 시작 중...")
    
    try:
        # 게임 상태 감지기 생성
        detector = GameStateDetector()
        
        # 초기 게임 상태 출력
        detector.detect_game_state()
        
        # 대화형 모드 실행
        detector.run_interactive_mode()
        
    except Exception as e:
        print(f"오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    print("게임 상태 감지기 종료")

if __name__ == "__main__":
    main() 