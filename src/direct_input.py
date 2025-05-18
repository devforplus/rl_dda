"""
게임을 직접 제어하는 간단한 스크립트
"""

import time
import random
import sys
import os

# 현재 디렉토리를 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# 게임 키보드 입력 시뮬레이션
try:
    import pyautogui
    print("PyAutoGUI 임포트 성공")
    
    def press_key(key):
        """키보드 키를 누릅니다"""
        pyautogui.keyDown(key)
        time.sleep(0.05)
        pyautogui.keyUp(key)
        print(f"키 입력: {key}")
    
    def random_action():
        """무작위 행동 선택"""
        # 랜덤 이동 (좌우)
        movement = random.choice(['left', 'right', None])
        # 80% 확률로 발사
        shooting = random.random() < 0.8
        
        return movement, shooting
    
    def perform_action(movement, shooting):
        """선택된 행동 수행"""
        # 이동 키 입력
        if movement == 'left':
            pyautogui.keyDown('left')
            time.sleep(0.1)
            pyautogui.keyUp('left')
            print("왼쪽 이동")
        elif movement == 'right':
            pyautogui.keyDown('right')
            time.sleep(0.1)
            pyautogui.keyUp('right')
            print("오른쪽 이동")
            
        # 발사 키 입력
        if shooting:
            pyautogui.keyDown('z')
            time.sleep(0.05)
            pyautogui.keyUp('z')
            print("발사")
    
    def main():
        """메인 함수"""
        # 사용자에게 안내
        print("=== 직접 입력 에이전트 ===")
        print("1. 게임을 시작하세요.")
        print("2. Enter 키를 누르면 자동 조작이 시작됩니다.")
        print("3. 종료하려면 Ctrl+C를 누르세요.")
        
        # 사용자 입력 대기
        input("게임이 준비되면 Enter 키를 누르세요...")
        
        # 잠시 대기
        print("3초 후 에이전트가 시작됩니다...")
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)
            
        print("에이전트 시작!")
        
        # 메인 루프
        try:
            for step in range(500):  # 500 스텝 실행
                # 무작위 행동 선택
                movement, shooting = random_action()
                
                # 선택된 행동 로그
                move_str = "왼쪽" if movement == 'left' else "오른쪽" if movement == 'right' else "정지"
                shoot_str = "발사" if shooting else "대기"
                print(f"스텝 {step+1}: {move_str} + {shoot_str}")
                
                # 행동 수행
                perform_action(movement, shooting)
                
                # 짧은 지연
                time.sleep(0.1)
                
            print("에이전트 실행 완료!")
            
        except KeyboardInterrupt:
            print("\n사용자에 의해 중단되었습니다.")
        
        except Exception as e:
            print(f"오류 발생: {str(e)}")
            import traceback
            traceback.print_exc()
            
    if __name__ == "__main__":
        main()
        
except ImportError:
    print("PyAutoGUI를 설치해야 합니다. 다음 명령어로 설치하세요:")
    print("pip install pyautogui")
    
except Exception as e:
    print(f"초기화 중 오류 발생: {str(e)}")
    import traceback
    traceback.print_exc() 