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

try:
    import torch
    import numpy as np
except ImportError as e:
    print(f"❌ 필수 라이브러리 임포트 실패: {e}")
    sys.exit(1)

# Pyxel 임포트 확인
try:
    import pyxel as px
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
        GoalBasedCurriculum,
        GoalBasedStage,
        ConvergenceBasedCurriculum,
        ConvergenceStage,
    )
    from rl.data_types import GameLogData, EntityPosition, PlayerState
    from rl.targets import get_survival_target_steps, get_kill_target
    from rl.reward_analyzer import RewardAnalyzer
except ImportError as e:
    print(f"❌ RL 모듈 임포트 실패: {e}")
    print("RL 모듈이 src/rl/ 디렉토리에 있는지 확인해주세요.")
    sys.exit(1)

try:
    from main import App
except ImportError as e:
    print(f"❌ 메인 앱 클래스 임포트 실패: {e}")
    print("main.py 파일이 src/ 디렉토리에 있는지 확인해주세요.")
    sys.exit(1)

try:
    from config.player.player_config import STARTING_LIVES
except ImportError as e:
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

        # 리플레이 녹화
        self.current_replay_frames = []
        self.replay_save_callback = None  # 트레이너가 설정할 콜백

    def connect_game(self, game_instance):
        """게임 인스턴스 연결"""
        self.connected_game = game_instance
        self.previous_lives = self._get_current_lives()

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

                # 리플레이 프레임 기록
                self._record_frame(game_log_data, action_id)

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
            if current_lives < self.previous_lives:
                if current_lives <= 0:
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
            except Exception as e:
                pass

        self._print_episode_summary()

        # 좋은 플레이 리플레이 저장 시도
        if self.replay_save_callback:
            try:
                self.replay_save_callback(
                    self.current_replay_frames, self.episode_steps, self.skill_level
                )
            except Exception as e:
                print(f"❌ 리플레이 저장 실패: {e}")

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
                    game.reset_game()
                elif hasattr(game, "restart_game"):
                    game.restart_game()
                elif hasattr(game, "game_vars"):
                    # 게임 변수 직접 초기화
                    game_vars = game.game_vars
                    game_vars.lives = STARTING_LIVES
                    game_vars.score = 0
                    game_vars.kills = 0

                    # 게임 상태 초기화
                    if hasattr(game_vars, "game_over"):
                        game_vars.game_over = False
                    if hasattr(game_vars, "game_started"):
                        game_vars.game_started = True

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
        self.environment.reset_episode()
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.previous_action_taken = False
        self.previous_lives = self._get_current_lives()
        self.reset_requested = False

        # 리플레이 버퍼 초기화
        self.current_replay_frames = []

    def _force_episode_reset(self):
        """강제 에피소드 리셋 (최후의 수단)"""
        # 에피소드 상태 강제 초기화
        self.episode_done = False
        self.reset_requested = False

        # 게임 상태 무시하고 에이전트 상태만 리셋
        self.environment.reset_episode()
        self.episode_reward = 0.0
        self.episode_steps = 0
        self.previous_action_taken = False
        self.previous_lives = STARTING_LIVES  # 기본값으로 설정

        # 리플레이 버퍼 초기화
        self.current_replay_frames = []

    def _record_frame(self, game_log: GameLogData, action: int):
        """현재 프레임을 리플레이에 기록"""
        try:
            # 플레이어 위치 찾기
            player_entity = next(
                (e for e in game_log.entities if e.entity_type == 0), None
            )

            frame_data = {
                "step": len(self.current_replay_frames),
                "player": {
                    "x": player_entity.x if player_entity else 0,
                    "y": player_entity.y if player_entity else 0,
                    "hp": game_log.player_state.hp,
                    "lives": game_log.player_state.lives,
                },
                "enemies": [
                    {"x": e.x, "y": e.y}
                    for e in game_log.entities
                    if e.entity_type == 1
                ],
                "bullets": [
                    {"x": e.x, "y": e.y}
                    for e in game_log.entities
                    if e.entity_type == 2
                ],
                "score": game_log.current_score,
                "action": action,
            }
            self.current_replay_frames.append(frame_data)
        except Exception as e:
            # 프레임 기록 실패는 조용히 무시 (학습에 영향 없음)
            pass

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
        """디버깅 정보 출력 (비활성화)"""
        # 학습 중 불필요한 로그 제거
        pass

    def _print_episode_summary(self):
        """에피소드 요약 출력 (비활성화)"""
        # 학습 중 불필요한 로그 제거 (상위 레벨에서 출력)
        pass


class RealGameTrainer:
    """실제 게임에서의 PPO 학습 관리자 - 최적화된 하이퍼파라미터 사용"""

    def __init__(self, skill_level: float = 0.5, curriculum=None):
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
        
        # 🔬 실시간 진단 도구
        self.reward_analyzer = RewardAnalyzer()
        self.diagnosis_interval = 50  # 50 에피소드마다 진단
        self.last_diagnosis_episode = 0

        # 리플레이 수집 관리
        self.replay_save_dir = "web/agentic-game/replays"
        os.makedirs(self.replay_save_dir, exist_ok=True)

        # 각 스킬 레벨별 베스트 리플레이 추적 (각 1개씩, 계속 갱신)
        self.collected_replays = {
            0.1: {
                "best_steps": 0,
                "min_steps": 550,
                "name": "beginner",
                "saved": False,
            },
            0.5: {"best_steps": 0, "min_steps": 850, "name": "medium", "saved": False},
            1.0: {"best_steps": 0, "min_steps": 1100, "name": "master", "saved": False},
        }

        try:
            # 환경 초기화
            self.environment = GameEnvironment()

            # 상태 크기 확인
            try:
                dummy_game_log = self._create_dummy_game_log()
                actual_state_size = len(
                    self.environment._extract_state_vector(dummy_game_log)
                )
            except Exception as e:
                actual_state_size = 161  # 기본값

            # PPO 에이전트 초기화
            self.ppo_agent = PPOAgent(
                state_size=actual_state_size,
                action_size=10,
            )

            # 커리큘럼이 있을 경우, 0번째 에피소드 스킬/스테이지 설정
            if self.curriculum is not None:
                init_skill, init_stage = self.curriculum.skill_for_episode(0)
                self.skill_level = init_skill
                self.current_stage_name = init_stage
                self.stage_start_episode = 1

            self.environment = GameEnvironment()

            self.game_agent = RealGamePPOAgent(
                self.ppo_agent, self.environment, self.skill_level
            )

            # 커리큘럼 초기 스킬 반영
            if self.curriculum is not None:
                self.game_agent.skill_level = self.skill_level

            # 콜백 설정
            self.game_agent.trainer_callback = self._on_episode_end
            self.game_agent.replay_save_callback = self._try_save_replay

            self.game_app = None

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

        print(f"\n🎮 PPO 학습 시작 (에피소드: {max_episodes}, LR: 7.67e-05, Batch: 64)")

        # 신호 핸들러 설정 (Ctrl+C 처리)
        signal.signal(signal.SIGINT, self._signal_handler)

        try:
            # 백그라운드 학습 스레드 시작
            self.training_thread = threading.Thread(target=self._training_loop)
            self.training_thread.daemon = True
            self.training_thread.start()

            # 게임 앱 생성 및 실행
            self.game_app = App(agent=self.game_agent)

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

                time.sleep(0.2)  # CPU 사용량 감소

            except Exception as e:
                print(f"❌ 학습 루프 오류: {e}")
                import traceback

                traceback.print_exc()
                time.sleep(1)

    def _perform_ppo_update(self, current_step: int, num_samples: int):
        """PPO 업데이트 수행 (로그 간소화)"""
        try:
            update_info = self.ppo_agent.update()

            if update_info:
                # 주기적 모델 저장만 수행 (로그 제거)
                if (current_step // self.update_interval) % 10 == 0:
                    self.save_model()

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

        # 최종 모델 저장
        self.save_model()

        # 통계 출력
        self._print_final_stats()

        # 그래프 생성
        if len(self.episode_rewards) > 0:
            self._generate_training_plots()

    def save_model(self):
        """모델 저장 (로그 간소화)"""
        try:
            self.ppo_agent.save_model()
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
        
        # 🔬 실시간 진단: 에피소드 결과를 reward_analyzer에 기록
        # 참고: 실제 보상 분해는 스텝 단위로 해야 하지만, 여기서는 에피소드 요약만 기록
        # 향후 스텝 단위 통합을 위해 에피소드 요약 저장
        try:
            # RewardAnalyzer의 에피소드 카운터 업데이트
            if self.reward_analyzer.current_episode == 0:
                self.reward_analyzer.current_episode = 1
            else:
                self.reward_analyzer.reset_episode()
            
            # 에피소드 통계 저장 (간소화 버전)
            if not hasattr(self.reward_analyzer, 'episode_stats'):
                self.reward_analyzer.episode_stats = {}
            
            self.reward_analyzer.episode_stats[self.episode_count] = {
                'episode': self.episode_count,
                'skill_level': self.skill_level,
                'final_step': episode_steps,
                'final_kills': episode_kills,
                'total_reward': episode_reward,
                'target_survival_steps': get_survival_target_steps(self.skill_level),
                'target_kills': get_kill_target(self.skill_level),
                'survival_achievement': episode_steps / get_survival_target_steps(self.skill_level),
                'kill_achievement': episode_kills / get_kill_target(self.skill_level) if get_kill_target(self.skill_level) > 0 else 0.0,
            }
        except Exception as e:
            # 진단 실패해도 학습은 계속 진행
            pass

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
        
        # 🔬 실시간 진단: N 에피소드마다 보상 희소성 진단
        if self.episode_count > 0 and (self.episode_count - self.last_diagnosis_episode) >= self.diagnosis_interval:
            try:
                self._run_realtime_diagnosis()
                self.last_diagnosis_episode = self.episode_count
            except Exception as e:
                print(f"⚠️ 실시간 진단 실패 (무시됨): {e}")

        # 커리큘럼 단계 관리
        if self.curriculum is not None:
            # GoalBasedCurriculum 또는 ConvergenceBasedCurriculum인 경우 특별 처리
            if isinstance(self.curriculum, (GoalBasedCurriculum, ConvergenceBasedCurriculum)):
                # 에피소드 결과를 커리큘럼에 보고
                result = self.curriculum.report_episode_result(episode_steps, episode_kills)
                
                # 진행 상황 출력
                progress = self.curriculum.get_progress_info()
                print(f"\n📈 커리큘럼 진행 상황:")
                print(f"   단계: {progress['stage_name']} (Skill {progress['skill_level']:.1f})")
                print(f"   단계 에피소드: {progress['stage_episodes']}/{progress['max_episodes']}")
                print(f"   총 에피소드: {progress['total_episodes']}")
                
                if 'recent_avg_steps' in progress:
                    print(f"   평균 생존: {progress['recent_avg_steps']:.1f}/{progress['target_steps']} ({progress['step_achievement']:.1%})")
                    print(f"   평균 킬: {progress['recent_avg_kills']:.1f}/{progress['target_kills']:.1f} ({progress['kill_achievement']:.1%})")
                    if progress['goal_achieved']:
                        print(f"   ✅ 목표 달성! (다음 단계 전환 준비)")
                
                # 단계 전환 처리
                if result.get('stage_changed'):
                    prev_stage_name = self.current_stage_name if hasattr(self, 'current_stage_name') else "초기"
                    prev_stage_skill = self.skill_level
                    
                    # 이전 단계 아티팩트 저장
                    try:
                        self._save_model_for_stage(prev_stage_name, prev_stage_skill)
                        if hasattr(self, 'stage_start_episode'):
                            self._generate_stage_plots(
                                prev_stage_name, self.stage_start_episode, self.episode_count
                            )
                    except Exception as e:
                        print(f"⚠️  스테이지 아티팩트 생성 중 오류: {e}")
                    
                    # 전이 학습
                    transfer_success = self._load_previous_stage_checkpoint(
                        prev_stage_name, prev_stage_skill
                    )
                    if transfer_success:
                        print("   ✅ 전이 학습 성공")
                    else:
                        print("   ⚠️ 전이 학습 실패 - 랜덤 초기화")
                    
                    # 새 단계 설정
                    self.current_stage_name = result['new_stage']
                    self.skill_level = result['new_skill']
                    self.game_agent.skill_level = result['new_skill']
                    self.stage_start_episode = self.episode_count + 1
                
                # 훈련 종료 확인
                if result.get('training_complete'):
                    print(f"\n{'='*70}")
                    print(f"🎉🎉🎉 훈련 완료! 🎉🎉🎉")
                    print(f"{'='*70}")
                    print(f"완료 사유: {result.get('reason', '목표 달성')}")
                    
                    # 최종 통계 출력
                    self.curriculum.print_stage_summary()
                    
                    # 최종 모델 저장
                    try:
                        self._save_model_for_stage("최종", self.skill_level)
                        if hasattr(self, 'stage_start_episode'):
                            self._generate_stage_plots(
                                "최종", self.stage_start_episode, self.episode_count
                            )
                    except Exception as e:
                        print(f"⚠️  최종 아티팩트 생성 중 오류: {e}")
                    
                    print(f"{'='*70}")
                    self.stop_training()
                    return
            
            else:
                # 기존 커리큘럼 (StepCurriculum 등) 처리
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
                    prev_stage_name = stage_name  # 전이 학습용 저장
                    prev_stage_skill = self.skill_level  # 전이 학습용 저장

                    try:
                        self._save_model_for_stage(stage_name, self.skill_level)
                        self._generate_stage_plots(
                            stage_name, self.stage_start_episode, self.episode_count
                        )
                    except Exception as e:
                        print(f"⚠️  스테이지 아티팩트 생성 중 오류: {e}")

                    # 🔥 전이 학습: 다음 스테이지로 전환하면서 이전 체크포인트 로드
                    if stage_changed and self.episode_count < self.max_episodes:
                        print(f"\n🎓 스테이지 전환: {prev_stage_name} (skill {prev_stage_skill:.1f}) → {next_stage} (skill {next_skill:.1f})")
                        
                        # 이전 스테이지의 학습 결과를 로드하여 전이 학습
                        transfer_success = self._load_previous_stage_checkpoint(
                            prev_stage_name, prev_stage_skill
                        )

                        if transfer_success:
                            print("   ✅ 전이 학습 성공")
                        else:
                            print("   ⚠️ 전이 학습 실패 - 랜덤 초기화")

                    # 다음 스테이지로 전환 준비
                    self.current_stage_name = next_stage
                    self.stage_start_episode = self.episode_count + 1

                # 다음 에피소드용 스킬 레벨 반영 (학습 계속 시)
                if self.episode_count < self.max_episodes:
                    prev_skill = self.skill_level
                    self.skill_level = next_skill
                    self.game_agent.skill_level = next_skill
                    if not stage_changed:  # 스테이지 전환이 아닌 경우에만 출력 (중복 방지)
                        print(
                            f"🎓 커리큘럼 업데이트 → 다음 Ep {self.episode_count + 1}: Stage='{next_stage}', "
                            f"skill {prev_skill:.2f} → {next_skill:.2f}"
                        )

        # 목표 달성 확인 (max_episodes 도달)
        if self.episode_count >= self.max_episodes:
            # GoalBasedCurriculum 또는 ConvergenceBasedCurriculum이 아닌 경우에만 종료
            if not isinstance(self.curriculum, (GoalBasedCurriculum, ConvergenceBasedCurriculum)):
                print(f"🎯 목표 에피소드 달성! 학습을 종료합니다.")
                self.stop_training()

    def _try_save_replay(self, frames: list, survival_steps: int, skill_level: float):
        """베스트 플레이 리플레이 저장/갱신

        목표 생존 시간을 넘긴 플레이 중에서 가장 오래 생존한 플레이를 저장합니다.
        더 좋은 기록이 나오면 계속해서 덮어씁니다.

        Args:
            frames: 프레임 리스트
            survival_steps: 생존 시간 (스텝)
            skill_level: 현재 스킬 레벨
        """
        import json
        import time

        # 해당 스킬 레벨의 설정 찾기
        replay_config = self.collected_replays.get(skill_level)
        if not replay_config:
            # 정확한 스킬 레벨이 아니면 무시 (커리큘럼 러닝 중 중간값들)
            return

        # 목표 생존 시간 미달이면 스킵
        if survival_steps < replay_config["min_steps"]:
            return

        # 프레임이 없으면 스킵
        if not frames:
            return

        # 이전 베스트보다 좋지 않으면 스킵
        previous_best = replay_config["best_steps"]
        if survival_steps <= previous_best:
            return

        # 새로운 베스트 기록! 저장
        try:
            # 베스트 기록 갱신
            is_first_save = not replay_config["saved"]
            replay_config["best_steps"] = survival_steps
            replay_config["saved"] = True

            # 저장 디렉토리 확인 및 생성
            os.makedirs(self.replay_save_dir, exist_ok=True)

            # 파일명 생성
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"best_{replay_config['name']}_skill_{skill_level}.json"
            filepath = os.path.join(self.replay_save_dir, filename)

            # 리플레이 데이터 구성
            replay_data = {
                "metadata": {
                    "model_name": replay_config["name"],
                    "skill_level": skill_level,
                    "total_steps": survival_steps,
                    "episode_number": self.episode_count,
                    "timestamp": timestamp,
                },
                "frames": frames,
            }

            # JSON 저장 (덮어쓰기)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(replay_data, f, indent=2, ensure_ascii=False)

            # 리플레이 저장 로그 간소화 (불필요한 출력 제거)

        except Exception as e:
            print(f"❌ 리플레이 저장 실패: {e}")
            import traceback

            traceback.print_exc()

    def _print_final_stats(self):
        """최종 통계 출력"""
        if not self.episode_rewards:
            return

        training_time = 0
        if self.training_start_time:
            training_time = time.time() - self.training_start_time

        print(f"\n🏆 학습 완료 (시간: {training_time/60:.1f}분, 에피소드: {self.episode_count})")
        print(f"   - 평균 보상: {np.mean(self.episode_rewards):.2f} (최고: {np.max(self.episode_rewards):.2f})")
        print(f"   - 평균 생존: {np.mean(self.episode_survival_times):.1f} 스텝 (최장: {np.max(self.episode_survival_times)})")
        if self.episode_kills:
            print(f"   - 평균 킬: {np.mean(self.episode_kills):.1f} (총 {np.sum(self.episode_kills)}킬)")

    def _generate_training_plots(self):
        """학습 결과 그래프 생성"""
        try:
            import matplotlib

            matplotlib.use("Agg")  # GUI 없는 백엔드 사용
            import matplotlib.pyplot as plt
            from datetime import datetime

            # 폰트 설정
            plt.rcParams["font.family"] = ["DejaVu Sans"]
            plt.rcParams["axes.unicode_minus"] = False

            # 저장 디렉토리
            save_dir = "models"
            os.makedirs(save_dir, exist_ok=True)

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
                f"PPO Training Results - Optuna Optimized\n"
                f"(Skill: {self.skill_level}, Episodes: {len(episodes)}, LR: 7.67e-05, Batch: 64)",
                fontsize=16,
                fontweight="bold",
            )
            plt.tight_layout()

            # 파일 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            graph_file = os.path.join(
                save_dir, f"training_results_optuna_{timestamp}.png"
            )
            plt.savefig(graph_file, dpi=300, bbox_inches="tight")
            plt.close()

            print(f"📊 그래프 저장: {graph_file}")

        except Exception as e:
            print(f"❌ 그래프 생성 실패: {e}")

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
                end = min(
                    cumulative + max(0, stage.num_episodes), total_eps
                )  # 0-based exclusive
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
                        "scores": self.episode_scores[start:end]
                        if self.episode_scores
                        else [],
                        "kills": self.episode_kills[start:end]
                        if self.episode_kills
                        else [],
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
                ax.plot(
                    x_vals, y_vals, color=color, alpha=0.35, linewidth=1.0, label=label
                )
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
                plot_series(
                    ax2,
                    seg["episodes"],
                    seg["survival"],
                    color,
                    f"skill {seg['skill']:.1f}",
                )
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
                    plot_series(
                        ax3,
                        seg["episodes"],
                        seg["scores"],
                        color,
                        f"skill {seg['skill']:.1f}",
                    )
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
                    plot_series(
                        ax4,
                        seg["episodes"],
                        seg["kills"],
                        color,
                        f"skill {seg['skill']:.1f}",
                    )
            ax4.set_title("Kills - (Overlaid by Skill)")
            ax4.set_xlabel("Episode (relative in stage)")
            ax4.set_ylabel("Kills")
            ax4.legend()
            ax4.grid(True, alpha=0.3)

            # 제목 및 저장
            stage_desc = ", ".join(
                [f"{s['name']} (skill {s['skill']:.1f})" for s in stage_segments]
            )
            plt.suptitle(
                f"PPO Training - Combined by Skill\n({stage_desc})",
                fontsize=16,
                fontweight="bold",
            )
            plt.tight_layout()

            os.makedirs("src/models", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = os.path.join(
                "src/models", f"training_results_combined_by_skill_{timestamp}.png"
            )
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

        except Exception as e:
            print(f"❌ 스테이지 그래프 생성 실패: {e}")
    
    def _run_realtime_diagnosis(self):
        """실시간 학습 진단 실행"""
        print(f"\n{'='*70}")
        print(f"🔬 실시간 학습 진단 (에피소드 {self.episode_count})")
        print(f"{'='*70}\n")
        
        # 최근 N개 에피소드 분석
        analysis_window = min(self.diagnosis_interval, len(self.episode_rewards))
        
        if analysis_window < 10:
            print("⚠️  충분한 데이터가 없습니다 (최소 10 에피소드 필요)")
            return
        
        # 최근 에피소드 통계
        recent_steps = self.episode_survival_times[-analysis_window:]
        recent_kills = self.episode_kills[-analysis_window:]
        recent_rewards = self.episode_rewards[-analysis_window:]
        
        # 목표값
        target_steps = get_survival_target_steps(self.skill_level)
        target_kills = get_kill_target(self.skill_level)
        
        # 달성률 계산
        avg_steps = np.mean(recent_steps)
        avg_kills = np.mean(recent_kills)
        avg_reward = np.mean(recent_rewards)
        
        survival_achievement = avg_steps / target_steps if target_steps > 0 else 0
        kill_achievement = avg_kills / target_kills if target_kills > 0 else 0
        
        # 변동성 (CV: Coefficient of Variation)
        steps_cv = np.std(recent_steps) / avg_steps if avg_steps > 0 else 0
        kills_cv = np.std(recent_kills) / avg_kills if avg_kills > 0 else 0
        
        print(f"📊 분석 범위: 최근 {analysis_window} 에피소드")
        print(f"현재 스킬 레벨: {self.skill_level:.1f}\n")
        
        print(f"🎯 목표 달성률:")
        print(f"   - 생존: {avg_steps:.1f}/{target_steps} ({survival_achievement*100:.1f}%)")
        print(f"   - 킬: {avg_kills:.2f}/{target_kills:.1f} ({kill_achievement*100:.1f}%)")
        print(f"   - 평균 보상: {avg_reward:.3f}\n")
        
        print(f"📈 성능 안정성 (변동계수 CV):")
        print(f"   - 생존 CV: {steps_cv*100:.1f}% {'✅ 안정적' if steps_cv < 0.15 else '⚠️ 불안정'}")
        print(f"   - 킬 CV: {kills_cv*100:.1f}% {'✅ 안정적' if kills_cv < 0.25 else '⚠️ 불안정'}\n")
        
        # 보상 희소성 진단
        print(f"💰 보상 분석:")
        
        # Multiplicative reward 추정
        avg_mult_reward = survival_achievement * kill_achievement
        print(f"   - Multiplicative Reward 추정: {avg_mult_reward:.3f}")
        
        # Bonus 발생 가능성
        bonus_possible = survival_achievement >= 0.8 and kill_achievement >= 0.8
        if bonus_possible:
            print(f"   - Bonus: ✅ 발생 가능 (둘 다 80% 이상)")
        else:
            print(f"   - Bonus: ❌ 발생 불가 (80% 이상 필요)")
            if survival_achievement < 0.8:
                print(f"     → 생존 {survival_achievement*100:.1f}% < 80%")
            if kill_achievement < 0.8:
                print(f"     → 킬 {kill_achievement*100:.1f}% < 80%")
        
        print()
        
        # 진단 메시지
        print(f"🔍 진단 결과:")
        issues = []
        
        # 달성률 체크
        if survival_achievement < 0.5:
            issues.append(f"🚨 생존 목표 달성률이 매우 낮음 ({survival_achievement*100:.1f}%)")
        elif survival_achievement < 0.7:
            issues.append(f"⚠️ 생존 목표 달성률이 낮음 ({survival_achievement*100:.1f}%)")
        
        if kill_achievement < 0.5:
            issues.append(f"🚨 킬 목표 달성률이 매우 낮음 ({kill_achievement*100:.1f}%)")
        elif kill_achievement < 0.7:
            issues.append(f"⚠️ 킬 목표 달성률이 낮음 ({kill_achievement*100:.1f}%)")
        
        # 불균형 체크
        achievement_diff = abs(survival_achievement - kill_achievement)
        if achievement_diff > 0.3:
            if survival_achievement > kill_achievement:
                issues.append(f"⚠️ 생존 편향 (생존 {survival_achievement*100:.1f}% vs 킬 {kill_achievement*100:.1f}%)")
            else:
                issues.append(f"⚠️ 공격 편향 (킬 {kill_achievement*100:.1f}% vs 생존 {survival_achievement*100:.1f}%)")
        
        # Multiplicative reward 체크
        if avg_mult_reward < 0.15:
            issues.append(f"🚨 Multiplicative reward가 매우 낮음 ({avg_mult_reward:.3f}) - 학습 신호 약함")
        elif avg_mult_reward < 0.30:
            issues.append(f"⚠️ Multiplicative reward가 낮음 ({avg_mult_reward:.3f})")
        
        # Bonus 부재
        if not bonus_possible:
            issues.append("⚠️ Bonus가 발생하지 않음 (80% 이상 달성 필요)")
        
        # 불안정성 체크
        if steps_cv > 0.20:
            issues.append(f"⚠️ 생존 성능이 불안정함 (CV: {steps_cv*100:.1f}%)")
        if kills_cv > 0.35:
            issues.append(f"⚠️ 킬 성능이 불안정함 (CV: {kills_cv*100:.1f}%)")
        
        if issues:
            for issue in issues:
                print(f"   {issue}")
        else:
            print(f"   ✅ 학습이 정상적으로 진행 중입니다")
        
        print()
        
        # 개선 제안
        if survival_achievement < 0.6 or kill_achievement < 0.6:
            print(f"💡 개선 제안:")
            if avg_mult_reward < 0.20:
                print(f"   1. 목표가 너무 높을 수 있습니다")
                print(f"      → targets.py에서 목표값 40% 감소 권장")
            if not bonus_possible:
                print(f"   2. Bonus 임계값을 낮추는 것을 고려하세요")
                print(f"      → environment.py에서 80% → 60%로 조정")
            if achievement_diff > 0.3:
                print(f"   3. 불균형 해소를 위해 즉각 보상 강화 필요")
            print()
        
        print(f"{'='*70}\n")

    def _save_model_for_stage(self, stage_name: str, skill: float):
        """단계 종료 시 모델 저장 (스테이지별 디렉토리).

        전이학습을 위해 best.pth와 latest.pth를 모두 저장합니다.
        """
        try:
            import os
            import shutil

            slug = self._sanitize_stage_slug(stage_name, skill)
            save_dir = os.path.join("src/models/ppo/stages", slug)

            # 1. timestamp 버전 저장 (기존 동작)
            path = self.ppo_agent.save_model(save_dir=save_dir)

            # 2. 전이학습을 위해 latest.pth로 복사
            latest_path = os.path.join(save_dir, "latest.pth")
            shutil.copy2(path, latest_path)

        except Exception as e:
            print(f"❌ 스테이지 모델 저장 실패: {e}")

    def _load_previous_stage_checkpoint(
        self, prev_stage_name: str, prev_skill: float
    ) -> bool:
        """이전 스테이지의 체크포인트를 로드하여 전이 학습 수행

        커리큘럼 러닝의 핵심: 이전 단계에서 배운 지식을 다음 단계로 전달

        Args:
            prev_stage_name: 이전 스테이지 이름
            prev_skill: 이전 스킬 레벨

        Returns:
            체크포인트 로드 성공 여부
        """
        try:
            import os

            slug = self._sanitize_stage_slug(prev_stage_name, prev_skill)
            checkpoint_dir = os.path.join("src/models/ppo/stages", slug)

            # best.pth 우선 시도, 없으면 latest.pth 시도
            best_path = os.path.join(checkpoint_dir, "best.pth")
            latest_path = os.path.join(checkpoint_dir, "latest.pth")

            checkpoint_path = None
            if os.path.exists(best_path):
                checkpoint_path = best_path
            elif os.path.exists(latest_path):
                checkpoint_path = latest_path
            else:
                return False

            # 체크포인트 로드
            success = self.ppo_agent.load_model(checkpoint_path)
            return success

        except Exception as e:
            print(f"❌ 전이 학습 중 오류 발생: {e}")
            import traceback

            traceback.print_exc()
            return False


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(
        description="PPO를 사용한 실제 게임 학습 (Optuna 최적화된 하이퍼파라미터)"
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
        choices=["step", "linear", "exponential", "sigmoid", "polynomial", "goal_based", "convergence"],
        default="convergence",
        help="커리큘럼 유형 선택 (기본: convergence, 수렴 기반 - 권장)",
    )
    parser.add_argument(
        "--linear-start",
        type=float,
        default=0.1,
        help="연속 커리큘럼 시작 skill (기본: 0.1)",
    )
    parser.add_argument(
        "--linear-end",
        type=float,
        default=1.0,
        help="연속 커리큘럼 종료 skill (기본: 1.0)",
    )
    parser.add_argument(
        "--exp-rate",
        type=float,
        default=3.0,
        help="지수 커리큘럼 증가 속도 (기본: 3.0, 범위: 1.0-5.0)",
    )
    parser.add_argument(
        "--sigmoid-steepness",
        type=float,
        default=12.0,
        help="시그모이드 커리큘럼 기울기 (기본: 12.0, 범위: 6.0-15.0)",
    )
    parser.add_argument(
        "--poly-degree",
        type=float,
        default=2.0,
        help="다항 커리큘럼 차수 (기본: 2.0, 범위: 1.0-4.0)",
    )

    args = parser.parse_args()

    print("🚀 실제 게임 PPO 학습 시작 - Optuna 최적화된 하이퍼파라미터")
    print(f"📋 설정:")
    print(f"   - 실력값: {args.skill_level}")
    print(f"   - 최대 에피소드: {args.max_episodes}")
    print(f"   - 업데이트 간격: {args.update_interval}")
    print(f"   - Optuna 최적화 하이퍼파라미터 사용 (LR: 7.67e-05, Batch: 64)")

    try:
        # 커리큘럼 구성 (옵션)
        curriculum = None
        if args.use_curriculum:
            if args.curriculum_type == "step":
                # 4단계 점진적 커리큘럼: 0.1 → 0.3 → 0.6 → 1.0
                # 후반부 집중 학습: 초급은 빠르게, 고급은 충분히
                # 비율: 10% → 20% → 30% → 40% (어려울수록 많은 시간)
                total = max(1, args.max_episodes)
                
                # 후반 집중 비율 (초급 → 고급으로 갈수록 증가)
                stage_ratios = [0.1, 0.2, 0.3, 0.4]  # 합계 = 1.0
                stage_episodes = [int(total * ratio) for ratio in stage_ratios]
                
                # 반올림 오차 보정 (마지막 단계에 추가)
                remainder = total - sum(stage_episodes)
                stage_episodes[-1] += remainder

                stages = [
                    CurriculumStage(stage_episodes[0], 0.1, f"초급 (목표: 280스텝, 1.2킬, {stage_episodes[0]}ep)"),
                    CurriculumStage(stage_episodes[1], 0.3, f"중급 (목표: 440스텝, 3.6킬, {stage_episodes[1]}ep)"),
                    CurriculumStage(stage_episodes[2], 0.6, f"중상급 (목표: 680스텝, 7.2킬, {stage_episodes[2]}ep)"),
                    CurriculumStage(stage_episodes[3], 1.0, f"고급 (목표: 1000스텝, 12킬, {stage_episodes[3]}ep)"),
                ]
                curriculum = StepCurriculum(stages)
            elif args.curriculum_type == "linear":
                curriculum = LinearCurriculum(
                    start_skill=args.linear_start,
                    end_skill=args.linear_end,
                    total_episodes=args.max_episodes,
                )
                print(f"📐 선형 커리큘럼: {args.linear_start:.1f} → {args.linear_end:.1f}")
            elif args.curriculum_type == "exponential":
                from rl import ExponentialCurriculum
                curriculum = ExponentialCurriculum(
                    start_skill=args.linear_start,
                    end_skill=args.linear_end,
                    total_episodes=args.max_episodes,
                    rate=args.exp_rate,
                )
                print(f"📈 지수 커리큘럼: {args.linear_start:.1f} → {args.linear_end:.1f} (rate={args.exp_rate})")
            elif args.curriculum_type == "sigmoid":
                from rl import SigmoidCurriculum
                curriculum = SigmoidCurriculum(
                    start_skill=args.linear_start,
                    end_skill=args.linear_end,
                    total_episodes=args.max_episodes,
                    steepness=args.sigmoid_steepness,
                )
                print(f"〰️  시그모이드 커리큘럼: {args.linear_start:.1f} → {args.linear_end:.1f} (steepness={args.sigmoid_steepness})")
            elif args.curriculum_type == "polynomial":
                from rl import PolynomialCurriculum
                curriculum = PolynomialCurriculum(
                    start_skill=args.linear_start,
                    end_skill=args.linear_end,
                    total_episodes=args.max_episodes,
                    degree=args.poly_degree,
                )
                print(f"📊 다항 커리큘럼: {args.linear_start:.1f} → {args.linear_end:.1f} (degree={args.poly_degree})")
            elif args.curriculum_type == "goal_based":
                # 🎯 목표 달성 기반 커리큘럼 (권장)
                # 각 단계에서 목표의 80%를 달성해야만 다음 단계로
                # Skill 1.0 목표 달성 시 자동 종료
                stages = [
                    GoalBasedStage(
                        skill_level=0.1,
                        name="초급 (생존 중심)",
                        target_steps=get_survival_target_steps(0.1),  # 280
                        target_kills=get_kill_target(0.1),  # 1.2
                        min_episodes=50,
                        max_episodes=1000,
                        success_threshold=0.80,
                        window_size=50,
                    ),
                    GoalBasedStage(
                        skill_level=0.3,
                        name="중급 (균형)",
                        target_steps=get_survival_target_steps(0.3),  # 440
                        target_kills=get_kill_target(0.3),  # 3.6
                        min_episodes=100,
                        max_episodes=1500,
                        success_threshold=0.80,
                        window_size=50,
                    ),
                    GoalBasedStage(
                        skill_level=0.6,
                        name="중상급 (공격 중심)",
                        target_steps=get_survival_target_steps(0.6),  # 680
                        target_kills=get_kill_target(0.6),  # 7.2
                        min_episodes=150,
                        max_episodes=2000,
                        success_threshold=0.80,
                        window_size=50,
                    ),
                    GoalBasedStage(
                        skill_level=1.0,
                        name="고급 (마스터)",
                        target_steps=get_survival_target_steps(1.0),  # 1000
                        target_kills=get_kill_target(1.0),  # 12
                        min_episodes=200,
                        max_episodes=5000,
                        success_threshold=0.80,
                        window_size=50,
                        is_final=True,  # 최종 단계
                    ),
                ]
                curriculum = GoalBasedCurriculum(stages)
                print(f"🎯 목표 달성 기반 커리큘럼")
                print(f"   각 단계에서 80% 달성 시 자동 전환")
                print(f"   Skill 1.0 목표(1000스텝, 12킬) 달성 시 훈련 자동 종료")
            elif args.curriculum_type == "convergence":
                # 🎓 수렴 기반 커리큘럼 (세분화 버전) - catastrophic forgetting 방지
                # 목표 달성 + 성능 수렴 + 안정성 + 연속 달성 모두 확인
                # 6단계 세분화: 0.1 → 0.3 → 0.5 → 0.7 → 0.9 → 1.0
                stages = [
                    ConvergenceStage(
                        skill_level=0.1,
                        name="초급 (생존 기초)",
                        target_steps=get_survival_target_steps(0.1),  # 330
                        target_kills=get_kill_target(0.1),  # 1.2
                        min_episodes=50,
                        max_episodes=800,
                        success_threshold=0.75,  # 75% (완화)
                        window_size=1,  # 각 에피소드 개별 평가
                        convergence_window=50,
                        stability_threshold=0.20,  # CV 20% (완화)
                        consecutive_windows=10,  # 10 에피소드
                        consecutive_success_rate=1.0,  # 연속 10개 모두 달성
                    ),
                    ConvergenceStage(
                        skill_level=0.3,
                        name="초중급 (기본 공격)",
                        target_steps=get_survival_target_steps(0.3),  # 590
                        target_kills=get_kill_target(0.3),  # 3.6
                        min_episodes=80,
                        max_episodes=1200,
                        success_threshold=0.75,  # 75% (완화)
                        window_size=1,  # 각 에피소드 개별 평가
                        convergence_window=80,
                        stability_threshold=0.18,
                        consecutive_windows=10,  # 10 에피소드
                        consecutive_success_rate=1.0,  # 연속 10개 모두 달성
                    ),
                    ConvergenceStage(
                        skill_level=0.5,
                        name="중급 (균형)",
                        target_steps=get_survival_target_steps(0.5),  # 850
                        target_kills=get_kill_target(0.5),  # 6.0
                        min_episodes=100,
                        max_episodes=1500,
                        success_threshold=0.75,  # 75% (완화)
                        window_size=1,  # 각 에피소드 개별 평가
                        convergence_window=100,
                        stability_threshold=0.15,
                        consecutive_windows=10,  # 10 에피소드
                        consecutive_success_rate=1.0,  # 연속 10개 모두 달성
                    ),
                    ConvergenceStage(
                        skill_level=0.7,
                        name="중상급 (적극적 공격)",
                        target_steps=get_survival_target_steps(0.7),  # 1110
                        target_kills=get_kill_target(0.7),  # 8.4
                        min_episodes=120,
                        max_episodes=1800,
                        success_threshold=0.75,  # 75% (완화)
                        window_size=1,  # 각 에피소드 개별 평가
                        convergence_window=100,
                        stability_threshold=0.15,
                        consecutive_windows=10,  # 10 에피소드
                        consecutive_success_rate=1.0,  # 연속 10개 모두 달성
                    ),
                    ConvergenceStage(
                        skill_level=0.9,
                        name="상급 (고급 전략)",
                        target_steps=get_survival_target_steps(0.9),  # 1370
                        target_kills=get_kill_target(0.9),  # 10.8
                        min_episodes=150,
                        max_episodes=2000,
                        success_threshold=0.75,  # 75% (완화)
                        window_size=1,  # 각 에피소드 개별 평가
                        convergence_window=100,
                        stability_threshold=0.15,
                        consecutive_windows=10,  # 10 에피소드
                        consecutive_success_rate=1.0,  # 연속 10개 모두 달성
                    ),
                    ConvergenceStage(
                        skill_level=1.0,
                        name="최상급 (마스터)",
                        target_steps=get_survival_target_steps(1.0),  # 1500
                        target_kills=get_kill_target(1.0),  # 12
                        min_episodes=200,
                        max_episodes=2500,
                        success_threshold=0.75,  # 75% (완화)
                        window_size=1,  # 각 에피소드 개별 평가
                        convergence_window=100,
                        stability_threshold=0.15,
                        consecutive_windows=10,  # 10 에피소드
                        consecutive_success_rate=1.0,  # 연속 10개 모두 달성
                        is_final=True,
                    ),
                ]
                curriculum = ConvergenceBasedCurriculum(stages)
                print(f"🎓 세분화된 수렴 기반 커리큘럼 (6단계)")
                print(f"   0.1 → 0.3 → 0.5 → 0.7 → 0.9 → 1.0")
                print(f"   목표 달성 + 성능 수렴 + 안정성 + 연속 달성 모두 확인")
                print(f"   Catastrophic Forgetting 방지를 위한 점진적 난이도 상승")
                print(f"   Skill 1.0 (1500스텝/12킬) 수렴 달성 시 훈련 자동 종료")

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
