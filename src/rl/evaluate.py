import argparse
import os
import time
import json
from typing import Dict, Any
import matplotlib.pyplot as plt

import torch
import numpy as np
import pyxel as px

from .fixed_environment import FixedVortexionEnv
from .fixed_random_agent import FixedRandomAgent

# 게임 임포트
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main import App

def parse_args():
    """커맨드 라인 인자 파싱"""
    parser = argparse.ArgumentParser(description='TorchRL을 사용한 랜덤 에이전트 평가')
    
    parser.add_argument('--episodes', type=int, default=3,
                        help='평가할 에피소드 수')
    parser.add_argument('--log-dir', type=str, default='eval_logs',
                        help='평가 로그 디렉토리 경로')
    parser.add_argument('--render', action='store_true',
                        help='환경 렌더링 여부')
    parser.add_argument('--record', action='store_true',
                        help='비디오 녹화 여부')
    parser.add_argument('--seed', type=int, default=12345,
                        help='랜덤 시드')
    
    return parser.parse_args()

def set_seeds(seed: int) -> None:
    """시드 설정"""
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False

def save_evaluation_results(results: Dict[str, Any], log_dir: str) -> None:
    """평가 결과 저장"""
    os.makedirs(log_dir, exist_ok=True)
    
    # JSON 파일로 결과 저장
    with open(os.path.join(log_dir, 'evaluation.json'), 'w') as f:
        json.dump(results, f, indent=2)
    
    # 보상 그래프 생성
    plt.figure(figsize=(10, 5))
    plt.bar(range(len(results['rewards'])), results['rewards'])
    plt.title('Evaluation Rewards')
    plt.xlabel('Episode')
    plt.ylabel('Total Reward')
    plt.savefig(os.path.join(log_dir, 'eval_rewards.png'))
    plt.close()
    
    # 에피소드 길이 그래프 생성
    plt.figure(figsize=(10, 5))
    plt.bar(range(len(results['lengths'])), results['lengths'])
    plt.title('Evaluation Episode Lengths')
    plt.xlabel('Episode')
    plt.ylabel('Steps')
    plt.savefig(os.path.join(log_dir, 'eval_lengths.png'))
    plt.close()

def evaluate_agent(args):
    """랜덤 에이전트 평가"""
    print("=== 개선된 TorchRL 기반 랜덤 에이전트 평가 시작 ===")
    
    try:
        # 시드 설정
        print("시드 설정 중...")
        set_seeds(args.seed)
        
        # 게임 앱 초기화
        print("1. 게임 애플리케이션 초기화 중...")
        
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
        
        # 강화학습 환경 및 에이전트 초기화
        print("\n2. 강화학습 환경 초기화 중...")
        env = FixedVortexionEnv(game)
        print("강화학습 환경 초기화 성공!")
        
        print("3. 랜덤 에이전트 초기화 중...")
        agent = FixedRandomAgent(env)
        print("랜덤 에이전트 초기화 성공!")
        
        # 에이전트 실행
        print(f"\n4. {args.episodes}개의 에피소드 실행 준비 완료.")
        input("Enter 키를 누르면 에이전트가 시작됩니다...")
        
        # 평가 실행
        evaluation_results = agent.evaluate(num_episodes=args.episodes)
        
        # 추가 정보 저장
        evaluation_results['timestamp'] = time.strftime("%Y-%m-%d %H:%M:%S")
        evaluation_results['seed'] = args.seed
        evaluation_results['args'] = vars(args)
        
        # 결과 출력
        print("\n===== 평가 결과 =====")
        print(f"평가 에피소드: {args.episodes}")
        print(f"평균 보상: {evaluation_results['mean_reward']:.2f}")
        print(f"평균 에피소드 길이: {evaluation_results['mean_episode_length']:.2f}")
        print("개별 에피소드 보상:", [f"{r:.2f}" for r in evaluation_results['rewards']])
        print("개별 에피소드 길이:", evaluation_results['lengths'])
        
        # 결과 저장
        save_evaluation_results(evaluation_results, args.log_dir)
        
    except Exception as e:
        print(f"에이전트 평가 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return None
    
    finally:
        print("\n5. 종료 중...")
        try:
            # 게임 종료 처리
            if hasattr(px, 'quit'):
                px.quit()
        except:
            pass
        
        print("평가가 종료되었습니다.")
    
    return evaluation_results

def main():
    """메인 함수"""
    args = parse_args()
    evaluate_agent(args)

if __name__ == "__main__":
    main() 