"""
개선된 TorchRL 환경과 랜덤 에이전트를 실행하는 스크립트
"""

import sys
import os
import time
import pyxel as px

# 현재 디렉토리를 경로에 추가
script_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(script_dir)
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# 필요한 모듈 임포트
from fixed_environment import FixedVortexionEnv
from fixed_random_agent import FixedRandomAgent
from main import App

def main():
    """메인 함수"""
    print("=== VORTEXION TorchRL 랜덤 에이전트 실행 ===")
    print("1. 게임 애플리케이션 초기화 중...")
    
    # 게임 애플리케이션 생성
    try:
        # 원본 pyxel.run 메서드 백업
        original_run = px.run
        
        # pyxel.run 메서드 오버라이드 (무한 루프 방지)
        def custom_run(update_func, draw_func):
            print("게임이 RL 환경에 의해 제어됩니다.")
        
        # 메서드 대체
        px.run = custom_run
        
        # 게임 앱 생성
        app = App()
        
        # 원본 메서드 복원
        px.run = original_run
        
        # 게임 객체 접근
        game = app.game
        print("게임 애플리케이션 초기화 성공!")
        
    except Exception as e:
        print(f"게임 애플리케이션 초기화 실패: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n2. 강화학습 환경 초기화 중...")
    try:
        # 강화학습 환경 생성
        env = FixedVortexionEnv(game)
        print("강화학습 환경 초기화 성공!")
        
        # 랜덤 에이전트 생성
        agent = FixedRandomAgent(env)
        print("랜덤 에이전트 초기화 성공!")
        
        # 에피소드 실행 설정
        num_episodes = 3
        print(f"\n3. {num_episodes}개의 에피소드 실행 준비 완료.")
        input("Enter 키를 누르면 에이전트가 시작됩니다...")
        
        # 에이전트 평가 실행
        results = agent.evaluate(num_episodes=num_episodes)
        
        # 결과 출력
        print("\n===== 최종 결과 =====")
        print(f"평균 보상: {results['mean_reward']:.2f}")
        print(f"평균 에피소드 길이: {results['mean_episode_length']:.2f}")
        print(f"개별 에피소드 보상: {[f'{r:.2f}' for r in results['rewards']]}")
        print(f"개별 에피소드 길이: {results['lengths']}")
        
    except Exception as e:
        print(f"에이전트 실행 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
    
    finally:
        print("\n4. 종료 중...")
        try:
            # 게임 종료 처리
            if hasattr(px, 'quit'):
                px.quit()
        except:
            pass
        
        print("프로그램이 종료되었습니다.")

if __name__ == "__main__":
    main() 