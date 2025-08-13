"""
실제 게임에서 PPO 모델 학습 - 수정된 버전

주요 수정사항:
1. 에러 처리 강화
2. 게임 실행 문제 해결
3. 안전한 종료 처리
4. 디버깅 정보 추가
5. 최적화된 하이퍼파라미터 적용 (PPOAgent 기본값 사용)
"""

import sys
import os
import argparse
import threading
import time
import signal
from typing import Optional

# 프로젝트 루트를 Python 경로에 추가
current_dir = os.path.dirname(__file__)
project_root = os.path.join(current_dir, "src")
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print(f"🔍 프로젝트 루트 경로: {project_root}")
print(f"🔍 Python 경로에 추가됨: {project_root in sys.path}")

try:
    import torch
    import numpy as np

    print("✅ PyTorch와 NumPy 임포트 성공")
except ImportError as e:
    print(f"❌ 필수 라이브러리 임포트 실패: {e}")
    sys.exit(1)

# Pyxel 임포트 확인
try:
    import pyxel as px

    print("✅ Pyxel 임포트 성공")
except ImportError as e:
    print(f"❌ Pyxel 임포트 실패: {e}")
    print("pip install pyxel로 설치해주세요.")
    sys.exit(1)

# 프로젝트 모듈 임포트
try:
    from rl import (
        PPOAgent,
        GameEnvironment,
        PPOTrainer,
        CurriculumStage,
        StepCurriculum,
        LinearCurriculum,
    )
    from rl.data_types import GameLogData, EntityPosition, PlayerState

    print("✅ RL 모듈 임포트 성공")
except ImportError as e:
    print(f"❌ RL 모듈 임포트 실패: {e}")
    print("RL 모듈이 src/rl/ 디렉토리에 있는지 확인해주세요.")
    sys.exit(1)

try:
    from main import App

    print("✅ 메인 앱 클래스 임포트 성공")
except ImportError as e:
    print(f"❌ 메인 앱 클래스 임포트 실패: {e}")
    print("main.py 파일이 src/ 디렉토리에 있는지 확인해주세요.")
    sys.exit(1)

try:
    from config.player.player_config import STARTING_LIVES

    print("✅ 플레이어 설정 임포트 성공")
except ImportError as e:
    print(f"❌ 플레이어 설정 임포트 실패: {e}")
    print("기본값 3으로 설정합니다.")
    STARTING_LIVES = 3


class RealGamePPOAgent:
    """실제 게임에서 동작하는 PPO 에이전트"""

    def __init__(
        self, ppo_agent: PPOAgent, environment: GameEnvironment, skill_level: float
    ):
        self.ppo_agent = ppo_agent
        self.environment = environment
        self.skill_level = skill_level
        self.connected_game = None

        # 학습 통계
        self.step_count = 0
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.previous_action_taken = False

        # 에피소드 관리
        self.episode_done = False
        self.previous_lives = STARTING_LIVES
        self.trainer_callback = None
        self.reset_requested = False
        self.reset_timer = 0  # 리셋 타이머 추가

        print(f"✅ PPO 에이전트 초기화 완료 (실력값: {skill_level})")

    def connect_game(self, game_instance):
        """게임 인스턴스 연결"""
        self.connected_game = game_instance
        self.previous_lives = self._get_current_lives()
        print(
            f"✅ PPO 에이전트가 게임에 연결되었습니다. 초기 목숨: {self.previous_lives}"
        )

    def select_action(self, state=None) -> int:
        """게임에서 호출되는 액션 선택 메서드"""
        if self.connected_game is None:
            return 4  # 기본값: 정지

        try:
            # 리셋이 요청된 경우 처리
            if self.reset_requested:
                self._handle_reset()
                return 4

            # 에피소드가 종료된 경우
            if self.episode_done:
                # 강제 리셋 타이머 증가
                self.reset_timer += 1

                # 100 프레임 후에도 리셋되지 않으면 강제 리셋
                if self.reset_timer > 100:
                    print("⏰ 타이머 만료 - 강제 에피소드 리셋 실행")
                    self._force_episode_reset()
                    return 4

                return self._handle_episode_done()

            # 현재 목숨 수 확인 및 에피소드 종료 체크
            if self._check_episode_end():
                return 4

            # 게임 상태 추출
            try:
                game_log_data = self.environment.extract_game_log_data(
                    self.connected_game, self.skill_level
                )
            except Exception as e:
                print(f"❌ 게임 상태 추출 실패: {e}")
                return 4

            # 이전 액션의 보상 계산 및 저장
            if self.previous_action_taken:
                try:
                    reward = self.environment.calculate_reward(
                        self.connected_game, self.skill_level
                    )
                    self.ppo_agent.store_reward_and_done(reward, False)
                    self.episode_reward += reward
                    self.episode_steps += 1

                    # 주기적 디버깅 정보
                    if self.step_count % 100 == 0:
                        self._print_debug_info()

                except Exception as e:
                    print(f"❌ 보상 계산 실패: {e}")

            # PPO 에이전트로 액션 선택
            try:
                action_id = self.ppo_agent.get_action(game_log_data)
                self.previous_action_taken = True
                self.step_count += 1
                return action_id

            except Exception as e:
                print(f"❌ 액션 선택 실패: {e}")

                # 상태 크기 불일치 오류인지 확인
                if "shapes cannot be multiplied" in str(e):
                    print("🔍 상태 크기 불일치 감지 - 상태 벡터 분석 중...")
                    try:
                        state_vector = self.environment._extract_state_vector(
                            game_log_data
                        )
                        print(f"   - 실제 상태 벡터 크기: {len(state_vector)}")
                        print(
                            f"   - 예상 상태 크기: {self.ppo_agent.network.state_size}"
                        )
                        print(
                            f"   - 차이: {len(state_vector) - self.ppo_agent.network.state_size}"
                        )
                    except Exception as analysis_error:
                        print(f"   - 상태 분석 실패: {analysis_error}")

                return 4

        except Exception as e:
            print(f"❌ select_action 메서드에서 예외 발생: {e}")
            import traceback

            traceback.print_exc()
            return 4

    def _check_episode_end(self) -> bool:
        """에피소드 종료 조건 확인"""
        current_lives = self._get_current_lives()

        if current_lives != self.previous_lives:
            print(f"🔔 목숨 변화: {self.previous_lives} → {current_lives}")

            if current_lives < self.previous_lives:
                print(f"💀 플레이어 사망!")

                if current_lives <= 0:
                    print(f"🏁 에피소드 종료 (목숨 0)")
                    self._finalize_episode()
                    self.episode_done = True

                    # 일정 시간 후 강제 리셋을 위한 타이머 설정
                    self.reset_timer = 0
                    return True

        self.previous_lives = current_lives
        return False

    def _finalize_episode(self):
        """에피소드 종료 처리"""
        if self.previous_action_taken:
            try:
                reward = self.environment.calculate_reward(
                    self.connected_game, self.skill_level
                )
                self.ppo_agent.store_reward_and_done(reward, True)  # 에피소드 종료
                self.episode_reward += reward
                self.episode_steps += 1
                print(f"💾 최종 보상 저장: {reward:.3f}")
            except Exception as e:
                print(f"❌ 최종 보상 저장 실패: {e}")

        self._print_episode_summary()

        if self.trainer_callback:
            try:
                self.trainer_callback()
            except Exception as e:
                print(f"❌ 트레이너 콜백 실행 실패: {e}")

    def _handle_episode_done(self) -> int:
        """에피소드 완료 후 리셋 대기"""
        # 게임이 자동으로 리셋될 때까지 대기
        if self._is_game_reset():
            self._reset_for_new_episode()
            self.episode_done = False
            print("✅ 새로운 에피소드 시작!")
        else:
            # 게임 리셋을 강제로 요청
            self._request_game_reset()

        return 4  # 대기

    def _is_game_reset(self) -> bool:
        """게임이 리셋되었는지 확인"""
        try:
            current_lives = self._get_current_lives()
            # 목숨이 시작 값으로 돌아왔는지 확인
            reset_detected = current_lives >= STARTING_LIVES

            # 추가: 게임 상태가 실제로 리셋되었는지 확인
            if self.connected_game and hasattr(self.connected_game, "game"):
                game = self.connected_game.game
                if hasattr(game, "game_vars"):
                    # 점수나 다른 상태가 초기화되었는지도 확인
                    score = getattr(game.game_vars, "score", 0)
                    if (
                        reset_detected and score <= 50
                    ):  # 점수가 낮으면 리셋된 것으로 판단
                        return True

            return reset_detected

        except Exception as e:
            print(f"❌ 게임 리셋 확인 실패: {e}")
            return False

    def _request_game_reset(self):
        """게임 리셋 강제 요청"""
        try:
            if self.connected_game and hasattr(self.connected_game, "game"):
                game = self.connected_game.game

                # 게임에 리셋 메서드가 있다면 호출
                if hasattr(game, "reset_game"):
                    print("🔄 게임 강제 리셋 요청...")
                    game.reset_game()
                elif hasattr(game, "restart_game"):
                    print("🔄 게임 재시작 요청...")
                    game.restart_game()
                elif hasattr(game, "game_vars"):
                    # 게임 변수 직접 초기화
                    print("🔄 게임 상태 직접 초기화...")
                    game_vars = game.game_vars
                    game_vars.lives = STARTING_LIVES
                    game_vars.score = 0
                    game_vars.kills = 0

                    # 게임 상태 초기화
                    if hasattr(game_vars, "game_over"):
                        game_vars.game_over = False
                    if hasattr(game_vars, "game_started"):
                        game_vars.game_started = True

                    print("✅ 게임 상태 초기화 완료")

                    # 강제로 에피소드 종료 해제
                    self.episode_done = False
                    self._reset_for_new_episode()

        except Exception as e:
            print(f"❌ 게임 리셋 요청 실패: {e}")
            # 최후의 수단: 강제 리셋
            self._force_episode_reset()

    def _handle_reset(self):
        """리셋 처리"""
        self._reset_for_new_episode()
        self.reset_requested = False

    def _reset_for_new_episode(self):
        """새로운 에피소드를 위한 상태 리셋"""
        print("🔄 에피소드 리셋 중...")

        self.environment.reset_episode()
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.previous_action_taken = False
        self.previous_lives = self._get_current_lives()
        self.reset_requested = False

        print(f"✅ 에피소드 리셋 완료 (목숨: {self.previous_lives})")

    def _force_episode_reset(self):
        """강제 에피소드 리셋 (최후의 수단)"""
        print("⚠️  강제 에피소드 리셋 실행...")

        # 에피소드 상태 강제 초기화
        self.episode_done = False
        self.reset_requested = False

        # 게임 상태 무시하고 에이전트 상태만 리셋
        self.environment.reset_episode()
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.previous_action_taken = False
        self.previous_lives = STARTING_LIVES  # 기본값으로 설정

        print("🔧 강제 리셋 완료 - 새로운 에피소드 시작")

    def _get_current_lives(self) -> int:
        """현재 목숨 수 반환"""
        try:
            if (
                self.connected_game
                and hasattr(self.connected_game, "game")
                and self.connected_game.game
                and hasattr(self.connected_game.game, "game_vars")
            ):
                return getattr(
                    self.connected_game.game.game_vars, "lives", STARTING_LIVES
                )
        except Exception as e:
            print(f"❌ 목숨 수 조회 실패: {e}")

        return STARTING_LIVES

    def _print_debug_info(self):
        """디버깅 정보 출력"""
        buffer_sizes = {
            "states": len(self.ppo_agent.states),
            "actions": len(self.ppo_agent.actions),
            "rewards": len(self.ppo_agent.rewards),
            "dones": len(self.ppo_agent.dones),
        }
        print(f"🔍 Step {self.step_count} - 버퍼: {buffer_sizes}")

    def _print_episode_summary(self):
        """에피소드 요약 출력"""
        print(f"\n🏁 에피소드 종료")
        print(f"   - 보상: {self.episode_reward:.2f}")
        print(f"   - 스텝: {self.episode_steps}")
        print(f"   - 총 스텝: {self.step_count}")


class RealGameTrainer:
    """실제 게임에서의 PPO 학습 관리자 - 최적화된 하이퍼파라미터 사용"""

    def __init__(self, skill_level: float = 0.5, curriculum=None):
        print(f"🚀 PPO 트레이너 초기화 시작...")

        self.curriculum = curriculum
        self.skill_level = skill_level
        self.is_training = False
        self.episode_count = 0
        self.max_episodes = 100
        self.update_interval = 50
        self.cleaned_up = False  # 중복 정리 방지 플래그

        # 통계 수집용
        self.episode_rewards = []
        self.episode_survival_times = []
        self.episode_scores = []
        self.episode_kills = []
        self.training_start_time = None

        try:
            # 먼저 환경을 초기화하여 실제 상태 크기를 확인
            print("🌍 게임 환경 초기화 중...")
            self.environment = GameEnvironment()

            # 실제 상태 크기 확인
            try:
                # 더미 게임 상태로 상태 크기 측정
                print("📏 실제 상태 크기 측정 중...")
                dummy_game_log = self._create_dummy_game_log()
                actual_state_size = len(
                    self.environment._extract_state_vector(dummy_game_log)
                )
                print(f"🔍 실제 상태 크기: {actual_state_size}")
            except Exception as e:
                print(f"⚠️  상태 크기 자동 측정 실패: {e}")
                actual_state_size = 161  # 오류 메시지에서 확인된 크기
                print(f"🔧 기본 상태 크기 사용: {actual_state_size}")

            # PPO 컴포넌트 초기화 (최적화된 하이퍼파라미터 사용)
            print("🧠 PPO 에이전트 초기화 중...")
            print("📊 최적화된 하이퍼파라미터를 기본값으로 사용합니다:")
            print("   - Learning Rate: 7.67e-05")
            print("   - Gamma: 0.9659")
            print("   - GAE Lambda: 0.9592")
            print("   - Clip Epsilon: 0.2371")
            print("   - Value Coef: 0.1658")
            print("   - Entropy Coef: 0.00167")
            print("   - Hidden Size: 128")
            print("   - Num Layers: 2")
            print("   - Grad Clip Norm: 1.5008")

            # 최적화된 하이퍼파라미터는 PPOAgent의 기본값을 사용
            self.ppo_agent = PPOAgent(
                state_size=actual_state_size,
                action_size=10,  # 9 → 10으로 변경 (액션 매핑 0~9)
                # 나머지 하이퍼파라미터들은 PPOAgent의 최적화된 기본값 사용
            )

            # 커리큘럼이 있을 경우, 0번째 에피소드 스킬/스테이지 설정
            if self.curriculum is not None:
                init_skill, init_stage = self.curriculum.skill_for_episode(0)
                self.skill_level = init_skill
                self.current_stage_name = init_stage
                self.stage_start_episode = 1
                print(
                    f"🎓 커리큘럼 활성화 - 초기 Stage: {init_stage}, skill={self.skill_level:.2f}"
                )

            print("🌍 게임 환경 재초기화 중...")
            self.environment = GameEnvironment()

            print("🤖 게임 에이전트 래퍼 초기화 중...")
            self.game_agent = RealGamePPOAgent(
                self.ppo_agent, self.environment, self.skill_level
            )

            # 커리큘럼 초기 스킬 반영
            if self.curriculum is not None:
                self.game_agent.skill_level = self.skill_level

            # 콜백 설정
            self.game_agent.trainer_callback = self._on_episode_end

            self.game_app = None

            print(f"✅ PPO 트레이너 초기화 완료")
            print(f"   - 실력값: {skill_level}")
            print(f"   - 상태 크기: {actual_state_size}")
            print(f"   - 액션 크기: 10 (0~9)")
            print(f"   - 디바이스: {self.ppo_agent.device}")
            print(f"   - 최적화된 하이퍼파라미터 적용됨")

        except Exception as e:
            print(f"❌ 트레이너 초기화 실패: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

    def _create_dummy_game_log(self):
        """상태 크기 측정을 위한 더미 게임 로그 생성"""
        try:
            # 더미 GameLogData 생성
            dummy_game_log = GameLogData()

            # 기본 플레이어 상태
            dummy_game_log.player = PlayerState(
                position=EntityPosition(x=100.0, y=100.0),
                lives=3,
                score=0,
                kills=0,
                health=100,
                speed=1.0,
                direction=0.0,
                weapon_cooldown=0,
            )

            # 빈 엔티티 리스트들
            dummy_game_log.enemies = []
            dummy_game_log.bullets = []
            dummy_game_log.power_ups = []
            dummy_game_log.obstacles = []

            # 게임 메타 정보
            dummy_game_log.frame_count = 0
            dummy_game_log.elapsed_time = 0.0
            dummy_game_log.skill_level = self.skill_level

            return dummy_game_log

        except Exception as e:
            print(f"❌ 더미 게임 로그 생성 실패: {e}")

            # 최소한의 더미 객체 반환
            class DummyLog:
                def __init__(self):
                    self.player = None
                    self.enemies = []
                    self.bullets = []
                    self.power_ups = []
                    self.obstacles = []
                    self.frame_count = 0
                    self.elapsed_time = 0.0
                    self.skill_level = 0.5

            return DummyLog()

    def start_training(self, max_episodes: int = 100):
        """학습 시작"""
        self.max_episodes = max_episodes
        self.is_training = True
        self.training_start_time = time.time()

        print(f"\n🎮 실제 게임에서 PPO 학습 시작!")
        print(f"   - 최대 에피소드: {max_episodes}")
        print(f"   - 업데이트 간격: {self.update_interval} 스텝")
        print(f"   - 최적화된 하이퍼파라미터 사용")

        # 신호 핸들러 설정 (Ctrl+C 처리)
        signal.signal(signal.SIGINT, self._signal_handler)

        try:
            # 백그라운드 학습 스레드 시작
            print("🧵 백그라운드 학습 스레드 시작...")
            self.training_thread = threading.Thread(target=self._training_loop)
            self.training_thread.daemon = True
            self.training_thread.start()

            # 게임 앱 생성 및 실행
            print("🎮 게임 앱 생성 중...")
            self.game_app = App(agent=self.game_agent)

            print("🎮 Pyxel 게임 실행...")
            # Pyxel 실행 (메인 스레드에서 실행)
            px.run(self.game_app.update, self.game_app.draw)

        except KeyboardInterrupt:
            print("\n⏹️  사용자에 의해 학습이 중단되었습니다.")
        except Exception as e:
            print(f"❌ 게임 실행 중 오류: {e}")
            import traceback

            traceback.print_exc()
        finally:
            self._cleanup()

    def _signal_handler(self, signum, frame):
        """시그널 핸들러 (Ctrl+C 처리)"""
        print("\n🛑 종료 신호를 받았습니다. 안전하게 종료하는 중...")
        self.stop_training()

    def _training_loop(self):
        """백그라운드 학습 루프"""
        print("🔄 학습 루프 시작...")
        last_update_step = 0
        min_samples_for_update = 512  # 최소 샘플 수 감소

        while self.is_training and self.episode_count < self.max_episodes:
            try:
                current_step = self.game_agent.step_count

                # PPO 업데이트 조건 확인
                if current_step - last_update_step >= self.update_interval:
                    num_samples = len(self.ppo_agent.states)

                    if num_samples >= min_samples_for_update:
                        self._perform_ppo_update(current_step, num_samples)
                        last_update_step = current_step
                    else:
                        if current_step % 200 == 0:  # 덜 빈번한 메시지
                            print(
                                f"⏳ 학습 데이터 부족 ({num_samples}/{min_samples_for_update})"
                            )

                time.sleep(0.2)  # CPU 사용량 감소

            except Exception as e:
                print(f"❌ 학습 루프 오류: {e}")
                import traceback

                traceback.print_exc()
                time.sleep(1)

        print("🔄 학습 루프 종료")

    def _perform_ppo_update(self, current_step: int, num_samples: int):
        """PPO 업데이트 수행"""
        print(f"📈 PPO 업데이트 시작 (스텝 {current_step}, 샘플 {num_samples}개)")

        try:
            update_info = self.ppo_agent.update()

            if update_info:
                print(f"✅ PPO 업데이트 완료 (최적화된 하이퍼파라미터 사용)")
                print(f"   - Policy Loss: {update_info.get('policy_loss', 0):.4f}")
                print(f"   - Value Loss: {update_info.get('value_loss', 0):.4f}")
                print(f"   - 에피소드 보상: {self.game_agent.episode_reward:.2f}")

                # 주기적 모델 저장
                if (current_step // self.update_interval) % 10 == 0:
                    self.save_model()
            else:
                print("⚠️  PPO 업데이트 건너뜀 (데이터 부족)")

        except Exception as e:
            print(f"❌ PPO 업데이트 실패: {e}")
            import traceback

            traceback.print_exc()
            # 오류 시 버퍼 리셋
            self.ppo_agent.reset_buffer()
            print("🔄 버퍼 리셋 완료")

    def stop_training(self):
        """학습 중단"""
        print("🛑 학습 중단 중...")
        self.is_training = False

        # 학습 스레드 종료 대기
        if hasattr(self, "training_thread") and self.training_thread.is_alive():
            print("⏳ 학습 스레드 종료 대기...")
            self.training_thread.join(timeout=3.0)

        # 정리 작업을 먼저 수행 (그래프 생성 포함)
        self._cleanup()

        # 게임 루프 종료 (Pyxel) - 정리 후에 호출
        try:
            import pyxel as px

            print("🪟 Pyxel 루프 종료 요청 (px.quit)")
            px.quit()
        except Exception as e:
            print(f"⚠️  Pyxel 종료 요청 실패 또는 불필요: {e}")

    def _cleanup(self):
        """정리 작업"""
        if self.cleaned_up:
            return
        self.cleaned_up = True
        print("🧹 정리 작업 시작...")

        # 최종 모델 저장
        self.save_model()

        # 통계 출력
        self._print_final_stats()

        # 그래프 생성
        print(
            f"🔍 그래프 생성 조건 확인: episode_rewards 길이 = {len(self.episode_rewards)}"
        )
        if len(self.episode_rewards) > 0:
            print("📊 그래프 생성 시작...")
            self._generate_training_plots()
        else:
            print("⚠️  에피소드 데이터가 없어 그래프를 생성할 수 없습니다.")

        print("✅ 정리 작업 완료")

    def save_model(self):
        """모델 저장"""
        try:
            save_path = self.ppo_agent.save_model()
            print(f"💾 모델 저장 완료: {save_path}")
        except Exception as e:
            print(f"❌ 모델 저장 실패: {e}")

    def _on_episode_end(self):
        """에피소드 완료 콜백"""
        self.episode_count += 1

        # 통계 수집
        episode_reward = self.game_agent.episode_reward
        episode_steps = self.game_agent.episode_steps

        # 게임 통계 수집
        episode_score = 0
        episode_kills = 0
        try:
            if (
                self.game_agent.connected_game
                and hasattr(self.game_agent.connected_game, "game")
                and self.game_agent.connected_game.game
                and hasattr(self.game_agent.connected_game.game, "game_vars")
            ):
                game_vars = self.game_agent.connected_game.game.game_vars
                episode_score = getattr(game_vars, "score", 0)
                episode_kills = getattr(game_vars, "kills", 0)
        except Exception as e:
            print(f"❌ 게임 통계 수집 실패: {e}")

        # 통계 저장
        self.episode_rewards.append(episode_reward)
        self.episode_survival_times.append(episode_steps)
        self.episode_scores.append(episode_score)
        self.episode_kills.append(episode_kills)

        # 에피소드 요약 출력
        print(f"\n📊 에피소드 {self.episode_count}/{self.max_episodes} 완료")
        print(f"   - 보상: {episode_reward:.2f}")
        print(f"   - 생존시간: {episode_steps} 스텝")
        print(f"   - 점수: {episode_score}")
        print(f"   - 킬 수: {episode_kills}")

        # 최근 평균 출력
        if len(self.episode_rewards) >= 5:
            recent_avg_reward = np.mean(self.episode_rewards[-5:])
            recent_avg_survival = np.mean(self.episode_survival_times[-5:])
            print(f"   - 최근 5개 평균 보상: {recent_avg_reward:.2f}")
            print(f"   - 최근 5개 평균 생존시간: {recent_avg_survival:.1f}")

        # 커리큘럼 단계 종료 감지 및 단계별 아티팩트 저장/그래프 생성
        if self.curriculum is not None:
            # 다음 에피소드 기준 스테이지 조회 (0-based index = self.episode_count)
            next_skill, next_stage = self.curriculum.skill_for_episode(
                self.episode_count
            )

            # 현재 스테이지 이름이 없으면 초기화 (안전장치)
            if not hasattr(self, "current_stage_name"):
                self.current_stage_name = next_stage
                self.stage_start_episode = 1

            stage_changed = next_stage != self.current_stage_name
            final_episode_reached = self.episode_count >= self.max_episodes

            if stage_changed or final_episode_reached:
                # 방금 끝난 스테이지 기준으로 저장/그래프 생성
                stage_name = self.current_stage_name
                try:
                    self._save_model_for_stage(stage_name, self.skill_level)
                    self._generate_stage_plots(
                        stage_name, self.stage_start_episode, self.episode_count
                    )
                except Exception as e:
                    print(f"⚠️  스테이지 아티팩트 생성 중 오류: {e}")

                # 다음 스테이지로 전환 준비
                self.current_stage_name = next_stage
                self.stage_start_episode = self.episode_count + 1

            # 다음 에피소드용 스킬 레벨 반영 (학습 계속 시)
            if self.episode_count < self.max_episodes:
                prev_skill = self.skill_level
                self.skill_level = next_skill
                self.game_agent.skill_level = next_skill
                print(
                    f"🎓 커리큘럼 전환 → 다음 Ep {self.episode_count + 1}: Stage='{next_stage}', "
                    f"skill {prev_skill:.2f} → {next_skill:.2f}"
                )

        # 목표 달성 확인
        if self.episode_count >= self.max_episodes:
            print(f"🎯 목표 에피소드 달성! 학습을 종료합니다.")
            self.stop_training()

    def _print_final_stats(self):
        """최종 통계 출력"""
        if not self.episode_rewards:
            print("📊 학습 통계가 없습니다.")
            return

        training_time = 0
        if self.training_start_time:
            training_time = time.time() - self.training_start_time

        print("\n" + "=" * 60)
        print("🏆 PPO 학습 완료! (최적화된 하이퍼파라미터 사용)")
        print("=" * 60)
        print(f"📈 학습 통계:")
        print(f"   - 총 학습 시간: {training_time:.1f}초 ({training_time / 60:.1f}분)")
        print(f"   - 총 에피소드: {self.episode_count}")
        print(f"   - 총 스텝: {self.game_agent.step_count}")
        print(f"   - 실력값: {self.skill_level}")

        print(f"\n📊 성과 통계:")
        print(f"   - 평균 보상: {np.mean(self.episode_rewards):.2f}")
        print(f"   - 최고 보상: {np.max(self.episode_rewards):.2f}")
        print(f"   - 평균 생존시간: {np.mean(self.episode_survival_times):.1f} 스텝")
        print(f"   - 최장 생존시간: {np.max(self.episode_survival_times)} 스텝")
        if self.episode_scores:
            print(f"   - 평균 점수: {np.mean(self.episode_scores):.0f}")
            print(f"   - 최고 점수: {np.max(self.episode_scores)}")
        if self.episode_kills:
            print(f"   - 총 킬 수: {np.sum(self.episode_kills)}")
            print(f"   - 평균 킬/에피소드: {np.mean(self.episode_kills):.1f}")

        print(f"\n🧠 사용된 최적화 하이퍼파라미터:")
        print(f"   - Learning Rate: 7.67e-05")
        print(f"   - Gamma: 0.9659")
        print(f"   - GAE Lambda: 0.9592")
        print(f"   - Clip Epsilon: 0.2371")
        print(f"   - Value Coef: 0.1658")
        print(f"   - Entropy Coef: 0.00167")

    def _generate_training_plots(self):
        """학습 결과 그래프 생성"""
        try:
            print("🔍 matplotlib 임포트 중...")
            import matplotlib

            matplotlib.use("Agg")  # GUI 없는 백엔드 사용
            import matplotlib.pyplot as plt
            from datetime import datetime

            print("✅ matplotlib 임포트 성공")

            # 폰트 설정
            plt.rcParams["font.family"] = ["DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False

            # 저장 디렉토리
            save_dir = "models"
            print(f"🔍 저장 디렉토리 생성: {save_dir}")
            os.makedirs(save_dir, exist_ok=True)

            # 데이터 상태 확인
            print(f"🔍 데이터 상태:")
            print(f"   - episode_rewards: {len(self.episode_rewards)}개")
            print(f"   - episode_survival_times: {len(self.episode_survival_times)}개")
            print(f"   - episode_scores: {len(self.episode_scores)}개")
            print(f"   - episode_kills: {len(self.episode_kills)}개")

            # 그래프 생성
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
            episodes = list(range(1, len(self.episode_rewards) + 1))

            # 1. 보상 그래프
            ax1.plot(
                episodes, self.episode_rewards, alpha=0.6, color="blue", label="Reward"
            )
            if len(episodes) >= 5:
                window = min(5, len(self.episode_rewards))
                moving_avg = np.convolve(
                    self.episode_rewards, np.ones(window) / window, mode="valid"
                )
                ax1.plot(
                    episodes[window - 1 :],
                    moving_avg,
                    "r-",
                    linewidth=2,
                    label=f"MA({window})",
                )
            ax1.set_title("Episode Rewards")
            ax1.set_xlabel("Episode")
            ax1.set_ylabel("Reward")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 2. 생존시간 그래프
            ax2.plot(
                episodes,
                self.episode_survival_times,
                alpha=0.6,
                color="green",
                label="Survival Time",
            )
            if len(episodes) >= 5:
                moving_avg = np.convolve(
                    self.episode_survival_times, np.ones(window) / window, mode="valid"
                )
                ax2.plot(
                    episodes[window - 1 :],
                    moving_avg,
                    "r-",
                    linewidth=2,
                    label=f"MA({window})",
                )
            ax2.set_title("Episode Survival Time")
            ax2.set_xlabel("Episode")
            ax2.set_ylabel("Steps")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # 3. 점수 그래프
            if self.episode_scores:
                ax3.plot(
                    episodes,
                    self.episode_scores,
                    alpha=0.6,
                    color="orange",
                    label="Score",
                )
                if len(episodes) >= 5:
                    moving_avg = np.convolve(
                        self.episode_scores, np.ones(window) / window, mode="valid"
                    )
                    ax3.plot(
                        episodes[window - 1 :],
                        moving_avg,
                        "r-",
                        linewidth=2,
                        label=f"MA({window})",
                    )
            ax3.set_title("Episode Scores")
            ax3.set_xlabel("Episode")
            ax3.set_ylabel("Score")
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            # 4. 킬 수 그래프
            if self.episode_kills:
                ax4.plot(
                    episodes,
                    self.episode_kills,
                    alpha=0.6,
                    color="purple",
                    label="Kills",
                )
                if len(episodes) >= 5:
                    moving_avg = np.convolve(
                        self.episode_kills, np.ones(window) / window, mode="valid"
                    )
                    ax4.plot(
                        episodes[window - 1 :],
                        moving_avg,
                        "r-",
                        linewidth=2,
                        label=f"MA({window})",
                    )
            ax4.set_title("Episode Kills")
            ax4.set_xlabel("Episode")
            ax4.set_ylabel("Kills")
            ax4.legend()
            ax4.grid(True, alpha=0.3)

            plt.suptitle(
                f"PPO Training Results - Optimized Hyperparameters\n"
                f"(Skill: {self.skill_level}, Episodes: {len(episodes)})",
                fontsize=16,
                fontweight="bold",
            )
            plt.tight_layout()

            # 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            graph_file = os.path.join(
                save_dir, f"training_results_optimized_{timestamp}.png"
            )
            plt.savefig(graph_file, dpi=300, bbox_inches="tight")
            plt.close()

            print(f"📊 학습 결과 그래프 저장: {graph_file}")

        except Exception as e:
            print(f"❌ 그래프 생성 실패: {e}")
            import traceback

            traceback.print_exc()

    def _generate_combined_skill_plots(self):
        """스킬 단계별 데이터를 한 그림에 오버레이하여 비교 그래프 생성.

        - 커리큘럼이 단계형(StepCurriculum)일 때만 동작
        - 각 단계 구간을 에피소드 상대 인덱스(1부터)로 정규화하여 동일 축에 겹쳐 그림
        - 보상/생존시간/점수/킬 4개 서브플롯에 스킬값별 곡선을 표시
        """
        try:
            if self.curriculum is None:
                return
            # StepCurriculum에서만 지원
            from rl import StepCurriculum  # 이미 상단에서 임포트되지만, 안전하게 참조

            if not isinstance(self.curriculum, StepCurriculum):
                return

            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from datetime import datetime
            import numpy as np
            import os

            if not self.episode_rewards:
                return

            # 단계별 구간 계산 (훈련이 조기 종료되어도 안전하게 슬라이스)
            stages = getattr(self.curriculum, "stages", [])
            if not stages:
                return

            cumulative = 0
            stage_segments = []
            total_eps = len(self.episode_rewards)
            for stage in stages:
                start = cumulative  # 0-based inclusive
                end = min(cumulative + max(0, stage.num_episodes), total_eps)  # 0-based exclusive
                cumulative += stage.num_episodes
                if start >= end:
                    # 이 단계에 수집된 데이터가 없음
                    continue
                # 상대 에피소드 인덱스 (1..N)
                rel_eps = list(range(1, (end - start) + 1))
                stage_segments.append(
                    {
                        "name": stage.name,
                        "skill": stage.skill_level,
                        "episodes": rel_eps,
                        "rewards": self.episode_rewards[start:end],
                        "survival": self.episode_survival_times[start:end],
                        "scores": self.episode_scores[start:end] if self.episode_scores else [],
                        "kills": self.episode_kills[start:end] if self.episode_kills else [],
                    }
                )

            if not stage_segments:
                return

            # 색상 맵 (스킬값 구분)
            base_colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
            # 스킬값 정렬(가독성)
            stage_segments.sort(key=lambda x: x["skill"])  # 0.1 → 0.5 → 1.0 순

            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

            def plot_series(ax, x_vals, y_vals, color, label):
                ax.plot(x_vals, y_vals, color=color, alpha=0.35, linewidth=1.0, label=label)
                if len(y_vals) >= 5:
                    window = min(5, len(y_vals))
                    ma = np.convolve(y_vals, np.ones(window) / window, mode="valid")
                    ax.plot(x_vals[window - 1 :], ma, color=color, linewidth=2.0)

            # 보상
            for idx, seg in enumerate(stage_segments):
                color = base_colors[idx % len(base_colors)]
                plot_series(
                    ax1,
                    seg["episodes"],
                    seg["rewards"],
                    color,
                    f"skill {seg['skill']:.1f}",
                )
            ax1.set_title("Rewards - (Overlaid by Skill)")
            ax1.set_xlabel("Episode (relative in stage)")
            ax1.set_ylabel("Reward")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 생존시간
            for idx, seg in enumerate(stage_segments):
                color = base_colors[idx % len(base_colors)]
                plot_series(ax2, seg["episodes"], seg["survival"], color, f"skill {seg['skill']:.1f}")
            ax2.set_title("Survival Time - (Overlaid by Skill)")
            ax2.set_xlabel("Episode (relative in stage)")
            ax2.set_ylabel("Steps")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # 점수
            has_scores = any(len(seg["scores"]) > 0 for seg in stage_segments)
            if has_scores:
                for idx, seg in enumerate(stage_segments):
                    if not seg["scores"]:
                        continue
                    color = base_colors[idx % len(base_colors)]
                    plot_series(ax3, seg["episodes"], seg["scores"], color, f"skill {seg['skill']:.1f}")
            ax3.set_title("Scores - (Overlaid by Skill)")
            ax3.set_xlabel("Episode (relative in stage)")
            ax3.set_ylabel("Score")
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            # 킬
            has_kills = any(len(seg["kills"]) > 0 for seg in stage_segments)
            if has_kills:
                for idx, seg in enumerate(stage_segments):
                    if not seg["kills"]:
                        continue
                    color = base_colors[idx % len(base_colors)]
                    plot_series(ax4, seg["episodes"], seg["kills"], color, f"skill {seg['skill']:.1f}")
            ax4.set_title("Kills - (Overlaid by Skill)")
            ax4.set_xlabel("Episode (relative in stage)")
            ax4.set_ylabel("Kills")
            ax4.legend()
            ax4.grid(True, alpha=0.3)

            # 제목 및 저장
            stage_desc = ", ".join([f"{s['name']} (skill {s['skill']:.1f})" for s in stage_segments])
            plt.suptitle(
                f"PPO Training - Combined by Skill\n({stage_desc})",
                fontsize=16,
                fontweight="bold",
            )
            plt.tight_layout()

            os.makedirs("src/models", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join("src/models", f"training_results_combined_by_skill_{timestamp}.png")
            plt.savefig(out_path, dpi=300, bbox_inches="tight")
            plt.close()

            print(f"📊 스킬 비교 그래프 저장: {out_path}")

        except Exception as e:
            print(f"❌ 스킬 비교 그래프 생성 실패: {e}")

    def _sanitize_stage_slug(self, stage_name: str, skill: float | None = None) -> str:
        """Create a filesystem-friendly slug for a stage name and optional skill."""
        base = stage_name.strip().lower().replace(" ", "-")
        base = "".join(c for c in base if c.isalnum() or c in ("-", "_"))
        if skill is not None:
            return f"{base}-skill-{skill:.1f}"
        return base

    def _generate_stage_plots(self, stage_name: str, start_ep: int, end_ep: int):
        """단계별 부분 학습 그래프 생성 (에피소드 구간 슬라이스).

        Args:
            stage_name: 스테이지 이름
            start_ep: 시작 에피소드 (1-based, inclusive)
            end_ep: 종료 에피소드 (1-based, inclusive)
        """
        try:
            import matplotlib

            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            from datetime import datetime
            import numpy as np
            import os

            # 경계 보정
            n = len(self.episode_rewards)
            start_idx = max(1, start_ep)
            end_idx = min(end_ep, n)
            if start_idx > end_idx:
                print("⚠️  스테이지 그래프 생성 스킵: 유효한 에피소드 범위가 아닙니다.")
                return

            # 0-based 슬라이스 인덱스
            s = start_idx - 1
            e = end_idx

            episodes = list(range(start_idx, end_idx + 1))
            rewards = self.episode_rewards[s:e]
            survival = self.episode_survival_times[s:e]
            scores = self.episode_scores[s:e] if self.episode_scores else []
            kills = self.episode_kills[s:e] if self.episode_kills else []

            # 저장 디렉토리
            save_dir = "src/models"
            os.makedirs(save_dir, exist_ok=True)

            # 그래프 생성
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))

            # 보상
            ax1.plot(episodes, rewards, alpha=0.6, color="blue", label="Reward")
            if len(rewards) >= 5:
                window = min(5, len(rewards))
                moving_avg = np.convolve(
                    rewards, np.ones(window) / window, mode="valid"
                )
                ax1.plot(
                    episodes[window - 1 :],
                    moving_avg,
                    "r-",
                    linewidth=2,
                    label=f"MA({window})",
                )
            ax1.set_title(f"Rewards - {stage_name}")
            ax1.set_xlabel("Episode")
            ax1.set_ylabel("Reward")
            ax1.legend()
            ax1.grid(True, alpha=0.3)

            # 생존시간
            ax2.plot(
                episodes, survival, alpha=0.6, color="green", label="Survival Time"
            )
            if len(survival) >= 5:
                window = min(5, len(survival))
                moving_avg = np.convolve(
                    survival, np.ones(window) / window, mode="valid"
                )
                ax2.plot(
                    episodes[window - 1 :],
                    moving_avg,
                    "r-",
                    linewidth=2,
                    label=f"MA({window})",
                )
            ax2.set_title(f"Survival Time - {stage_name}")
            ax2.set_xlabel("Episode")
            ax2.set_ylabel("Steps")
            ax2.legend()
            ax2.grid(True, alpha=0.3)

            # 점수
            if scores:
                ax3.plot(episodes, scores, alpha=0.6, color="orange", label="Score")
                if len(scores) >= 5:
                    window = min(5, len(scores))
                    moving_avg = np.convolve(
                        scores, np.ones(window) / window, mode="valid"
                    )
                    ax3.plot(
                        episodes[window - 1 :],
                        moving_avg,
                        "r-",
                        linewidth=2,
                        label=f"MA({window})",
                    )
            ax3.set_title(f"Scores - {stage_name}")
            ax3.set_xlabel("Episode")
            ax3.set_ylabel("Score")
            ax3.legend()
            ax3.grid(True, alpha=0.3)

            # 킬
            if kills:
                ax4.plot(episodes, kills, alpha=0.6, color="purple", label="Kills")
                if len(kills) >= 5:
                    window = min(5, len(kills))
                    moving_avg = np.convolve(
                        kills, np.ones(window) / window, mode="valid"
                    )
                    ax4.plot(
                        episodes[window - 1 :],
                        moving_avg,
                        "r-",
                        linewidth=2,
                        label=f"MA({window})",
                    )
            ax4.set_title(f"Kills - {stage_name}")
            ax4.set_xlabel("Episode")
            ax4.set_ylabel("Kills")
            ax4.legend()
            ax4.grid(True, alpha=0.3)

            plt.suptitle(
                f"PPO Training - Stage Results\n(Stage: {stage_name}, Episodes: {start_idx}-{end_idx})",
                fontsize=16,
                fontweight="bold",
            )
            plt.tight_layout()

            # 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            slug = self._sanitize_stage_slug(stage_name, self.skill_level)
            graph_file = os.path.join(
                save_dir, f"training_results_{slug}_{timestamp}.png"
            )
            plt.savefig(graph_file, dpi=300, bbox_inches="tight")
            plt.close()

            print(f"📊 스테이지 그래프 저장: {graph_file}")

        except Exception as e:
            print(f"❌ 스테이지 그래프 생성 실패: {e}")

    def _save_model_for_stage(self, stage_name: str, skill: float):
        """단계 종료 시 모델 저장 (스테이지별 디렉토리)."""
        try:
            import os

            slug = self._sanitize_stage_slug(stage_name, skill)
            save_dir = os.path.join("src/models/ppo/stages", slug)
            path = self.ppo_agent.save_model(save_dir=save_dir)
            print(f"💾 스테이지 모델 저장 완료: {path}")
        except Exception as e:
            print(f"❌ 스테이지 모델 저장 실패: {e}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="PPO를 사용한 실제 게임 학습 (최적화된 하이퍼파라미터)"
    )
    parser.add_argument(
        "--skill-level",
        type=float,
        default=0.5,
        help="에이전트 실력값 (0.0-1.0, 기본값: 0.5)",
    )
    parser.add_argument(
        "--max-episodes", type=int, default=100, help="최대 에피소드 수 (기본값: 100)"
    )
    parser.add_argument(
        "--update-interval",
        type=int,
        default=50,
        help="PPO 업데이트 간격 (기본값: 50 스텝)",
    )
    parser.add_argument(
        "--use-curriculum",
        action="store_true",
        help="커리큘럼 러닝을 사용하여 에피소드별 skill_level을 자동 스케줄링",
    )
    parser.add_argument(
        "--curriculum-type",
        choices=["step", "linear"],
        default="step",
        help="커리큘럼 유형 선택 (기본: step)",
    )
    parser.add_argument(
        "--linear-start",
        type=float,
        default=0.2,
        help="선형 커리큘럼 시작 skill (기본: 0.2)",
    )
    parser.add_argument(
        "--linear-end",
        type=float,
        default=1.0,
        help="선형 커리큘럼 종료 skill (기본: 1.0)",
    )

    args = parser.parse_args()

    print("🚀 실제 게임 PPO 학습 시작 - 최적화된 하이퍼파라미터 버전")
    print(f"📋 설정:")
    print(f"   - 실력값: {args.skill_level}")
    print(f"   - 최대 에피소드: {args.max_episodes}")
    print(f"   - 업데이트 간격: {args.update_interval}")
    print(f"   - 최적화된 하이퍼파라미터 자동 적용")

    try:
        # 커리큘럼 구성 (옵션)
        curriculum = None
        if args.use_curriculum:
            if args.curriculum_type == "step":
                # Use only discrete skill levels: 0.1, 0.5, 1.0
                # Distribute episodes evenly across the three stages
                total = max(1, args.max_episodes)
                base = total // 3
                remainder = total - (base * 3)
                stage_episodes = [base, base, base]
                # Assign any remainder to the last stage to ensure sum == total
                stage_episodes[-1] += remainder

                stages = [
                    CurriculumStage(stage_episodes[0], 0.1, "초급 생존 중심"),
                    CurriculumStage(stage_episodes[1], 0.5, "중급 균형"),
                    CurriculumStage(stage_episodes[2], 1.0, "고급 공격 중심"),
                ]
                curriculum = StepCurriculum(stages)
            else:
                curriculum = LinearCurriculum(
                    start_skill=args.linear_start,
                    end_skill=args.linear_end,
                    total_episodes=args.max_episodes,
                )

        # 트레이너 생성 (최적화된 하이퍼파라미터는 PPOAgent에서 자동 적용)
        trainer = RealGameTrainer(skill_level=args.skill_level, curriculum=curriculum)

        # 업데이트 간격 설정
        trainer.update_interval = args.update_interval

        # 학습 시작
        trainer.start_training(max_episodes=args.max_episodes)

    except Exception as e:
        print(f"❌ 학습 시작 실패: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
