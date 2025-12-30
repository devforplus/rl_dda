import sys
import os
import time
import argparse
import threading
from collections import deque

# 에셋 로드를 위해 작업 디렉토리를 src로 설정 (현재 파일 위치)
current_file_path = os.path.dirname(os.path.abspath(__file__))
os.chdir(current_file_path)

# 모듈 임포트를 위해 현재 디렉토리를 sys.path에 추가
if current_file_path not in sys.path:
    sys.path.insert(0, current_file_path)

import pyxel as px
import numpy as np

# 프로젝트 내 모듈 임포트
try:
    import train_ppo_real_game
    from train_ppo_real_game import RealGamePPOAgent, create_random_ppo_agent
except ImportError as e:
    print(f"❌ train_ppo_real_game import 실패: {e}")
    sys.exit(1)

from rl import PPOAgent, GameEnvironment
from main import App
from const import APP_WIDTH, APP_HEIGHT, APP_NAME, APP_FPS, APP_DISPLAY_SCALE, APP_CAPTURE_SCALE, APP_GFX_FILE, PALETTE, SOUNDS_RES_FILE
from monospace_bitmap_font import MonospaceBitmapFont
from input import Input
from game import Game

class BenchmarkApp:
    def __init__(self, agent, start_speed=1, max_speed=50, duration_per_step=3.0, run_training=True):
        self.agent = agent
        self.run_training = run_training
        
        # 자동 벤치마크 설정
        self.current_speed = start_speed
        self.max_test_speed = max_speed
        self.duration_per_step = duration_per_step 
        
        # 상태 관리
        self.step_start_time = time.time()
        self.is_benchmarking = True
        self.results = []
        
        px.init(
            APP_WIDTH, APP_HEIGHT, 
            title=f"{APP_NAME} - Auto Benchmark",
            fps=APP_FPS,
            display_scale=APP_DISPLAY_SCALE,
            capture_scale=APP_CAPTURE_SCALE
        )

        px.colors.from_list(PALETTE)
        
        # 에셋 로드
        try:
            px.images[0].load(0, 0, "assets/" + APP_GFX_FILE)
            px.load("assets/" + SOUNDS_RES_FILE, exclude_images=True, 
                    exclude_tilemaps=True, exclude_musics=True)
        except Exception as e:
            print(f"❌ 에셋 로드 실패: {e}")
            px.quit()
            sys.exit(1)

        self.main_font = MonospaceBitmapFont()
        self.input = Input()

        self.game = Game(self)
        self.game.go_to_new_game()
        self.game.game_vars.god_mode = True
        self.agent.connect_game(self)
        
        # 측정용 버퍼
        self.frame_times = deque(maxlen=60)
        self.ppo_inference_times = deque(maxlen=100)
        self.step_fps_records = []
        self.step_inf_records = []
        
        if self.run_training:
            self.stop_training = False
            self.training_thread = threading.Thread(target=self._training_loop)
            self.training_thread.daemon = True
            self.training_thread.start()

        print(f"\n🚀 자동 벤치마크 시작 (1배속 ~ {max_speed}배속)")
        print(f"   각 단계당 {duration_per_step}초 측정\n")
        print(f"{'Speed':<6} | {'Target FPS':<10} | {'Actual FPS':<10} | {'Ratio':<8} | {'PPO(ms)':<8}")
        print("-" * 55)

        px.run(self.update, self.draw)

    def update(self):
        if not self.is_benchmarking:
            if px.btnp(px.KEY_Q) or px.btnp(px.KEY_ESCAPE):
                px.quit()
            return

        target_fps = APP_FPS * self.current_speed
        
        # 프레임 시작 시간
        frame_start = time.time()
        
        # 배속만큼 루프 실행
        for _ in range(self.current_speed):
            self.input.update()
            self.game.update()
            self.agent.select_action()
        
        # 프레임 종료 시간 및 기록
        frame_end = time.time()
        frame_duration = frame_end - frame_start
        self.frame_times.append(frame_duration)
        
        # Logic FPS 계산: (1초 / 프레임당 소요시간) * 배속
        # 하지만 프레임당 소요시간에는 배속 루프가 이미 포함되어 있으므로
        # actual_logic_fps = self.current_speed / frame_duration 이 더 정확함
        if frame_duration > 0:
            actual_logic_fps = self.current_speed / frame_duration
        else:
            actual_logic_fps = target_fps

        self.step_fps_records.append(actual_logic_fps)
        
        if hasattr(self.agent.ppo_agent, 'last_inference_time') and self.agent.ppo_agent.last_inference_time > 0:
            self.step_inf_records.append(self.agent.ppo_agent.last_inference_time * 1000)

        # 다음 단계 체크
        elapsed = time.time() - self.step_start_time
        if elapsed >= self.duration_per_step:
            avg_fps = sum(self.step_fps_records) / len(self.step_fps_records) if self.step_fps_records else 0
            avg_inf = sum(self.step_inf_records) / len(self.step_inf_records) if self.step_inf_records else 0
            fps_ratio = (avg_fps / target_fps * 100) if target_fps > 0 else 0
            
            self.results.append((self.current_speed, avg_fps, target_fps, fps_ratio, avg_inf))
            
            print(f"{self.current_speed:<6} | {target_fps:<10} | {avg_fps:<10.1f} | {fps_ratio:<7.1f}% | {avg_inf:<8.2f}")
            
            self.current_speed += 1
            self.step_start_time = time.time()
            self.step_fps_records = []
            self.step_inf_records = []
            
            if (fps_ratio < 90 and self.current_speed > 2) or self.current_speed > self.max_test_speed:
                self.is_benchmarking = False
                self.stop_training = True
                print("-" * 55)
                print(f"🏁 벤치마크 종료! 한계 속도: {self.current_speed-1}배속")
                print(f"결과 요약:")
                for res in self.results:
                    print(f"  {res[0]}배속: FPS {res[1]:.1f}/{res[2]} ({res[3]:.1f}%), PPO {res[4]:.2f}ms")

    def draw(self):
        px.cls(0)
        self.game.draw()
        
        y = 20
        self.main_font.draw_text(APP_WIDTH - 120, y, f"BENCHMARKING...")
        y += 10
        self.main_font.draw_text(APP_WIDTH - 120, y, f"SPEED: x{self.current_speed}")
        
        if self.is_benchmarking:
            y += 10
            elapsed = time.time() - self.step_start_time
            progress = elapsed / self.duration_per_step
            bar_width = 80
            px.rect(APP_WIDTH - 90, y, bar_width, 4, 1)
            px.rect(APP_WIDTH - 90, y, int(bar_width * progress), 4, 8)
            
            y += 10
            fps = self.step_fps_records[-1] if self.step_fps_records else 0
            self.main_font.draw_text(APP_WIDTH - 100, y, f"Logic FPS: {fps:.0f}")
        else:
            self.main_font.draw_text(APP_WIDTH - 120, y, "BENCHMARK COMPLETE")
            y += 10
            self.main_font.draw_text(APP_WIDTH - 120, y, "Check Console for Results")

    def _training_loop(self):
        while not getattr(self, 'stop_training', False):
            try:
                if len(self.agent.ppo_agent.states) >= 64:
                    self.agent.ppo_agent.update()
                time.sleep(0.01)
            except Exception:
                pass

def main():
    parser = argparse.ArgumentParser(description="PPO 랜덤 에이전트 배속 한계 테스트")
    parser.add_argument("--start", type=int, default=1, help="시작 배속 (기본: 1)")
    parser.add_argument("--max", type=int, default=50, help="최대 테스트 배속 (기본: 50)")
    parser.add_argument("--duration", type=float, default=2.0, help="단계별 측정 시간(초) (기본: 2.0)")
    parser.add_argument("--random-mode", action="store_true", help="완전 랜덤 액션 모드 사용")
    parser.add_argument("--no-training", action="store_true", help="학습 루프 비활성화")
    args = parser.parse_args()

    real_agent = create_random_ppo_agent(
        state_size=161,
        action_size=10,
        random_mode=args.random_mode
    )
    
    agent_type = "완전 랜덤" if args.random_mode else "초기화된 가중치 PPO"
    print(f"🤖 에이전트 타입: {agent_type}")
    
    BenchmarkApp(
        real_agent, 
        start_speed=args.start, 
        max_speed=args.max,
        duration_per_step=args.duration,
        run_training=not args.no_training
    )

if __name__ == "__main__":
    main()
