#!/usr/bin/env python3
"""
간단하고 직관적인 Pyxel 게임 데이터 수집기
Selenium을 사용하여 Helium과 유사한 직관적 API 제공
"""

import time
import sys
import asyncio
import json
import subprocess
import threading
import queue
import signal
from typing import Optional, List, Union, Any, Dict
from datetime import datetime
from pathlib import Path
import tempfile

# EventLogger import 추가
sys.path.append(str(Path(__file__).parent.parent.parent))
from src.utils.event_logger import EventLogger, LogLevel, EventType


def check_selenium_dependency() -> bool:
    """Selenium 의존성 확인"""
    try:
        import selenium
        from selenium import webdriver
        from webdriver_manager.chrome import ChromeDriverManager

        return True
    except ImportError:
        print("selenium이 설치되지 않았습니다.", file=sys.stderr)
        print("설치: pip install selenium", file=sys.stderr)
        return False


def check_websockets_dependency() -> bool:
    """WebSockets 및 aiohttp 의존성 확인"""
    try:
        import websockets
        import aiohttp

        return True
    except ImportError:
        print("websockets 또는 aiohttp가 설치되지 않았습니다.", file=sys.stderr)
        print("설치: pip install websockets aiohttp", file=sys.stderr)
        return False


class SimplePyxelCollector:
    """간단하고 직관적인 Pyxel 게임 데이터 수집기"""

    def __init__(
        self,
        headless: bool = True,
        verbose: bool = False,
        debug_port: int = 9222,
        namespace: str = "default",
    ):
        self.headless = headless
        self.verbose = verbose
        self.debug_port = debug_port
        self.namespace = namespace
        self.collected_data: List[str] = []
        self.is_collecting = False
        self.console_messages = queue.Queue()
        self.driver: Optional[object] = None

        # 속성들을 __init__에서 미리 초기화
        self.output_dir: Optional[Path] = None
        self.file_paths: Dict[str, Path] = {}
        self.created_files: set = set()

        # EventLogger 초기화 - data collector용으로 설정 (다른 초기화 전에 먼저 수행)
        self.logger = EventLogger(
            namespace=namespace,
            log_level=LogLevel.DEBUG if verbose else LogLevel.INFO,
            enable_console=verbose,
            enable_file=True,
            output_dir=f"data/{namespace}",
        )

        # 실제로 사용되는 console 타입들만 정의 (단순화)
        self.active_console_types = ["log", "info", "warn", "error", "debug"]

        # 모든 console 타입별 데이터 저장용
        self.console_data = {}  # {type: [messages]}
        self.console_raw_data = {}  # {type: [raw_data]}

        # 활성 타입들만 초기화
        for console_type in self.active_console_types:
            self.console_data[console_type] = []
            self.console_raw_data[console_type] = []

        # 실시간 저장을 위한 파일 준비
        self._setup_realtime_files()

        # Signal handler 등록
        self._register_signal_handlers()

    def _setup_realtime_files(self):
        """실시간 저장을 위한 디렉토리 준비 (단순한 구조)"""
        try:
            # 기본 출력 디렉토리만 생성
            self.output_dir = Path(f"data/{self.namespace}")
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # 파일 경로 딕셔너리 (동적 생성을 위해 준비만)
            self.file_paths = {}
            for console_type in self.active_console_types:
                # events_{console_type}.log 형태로 설정
                file_path = self.output_dir / f"events_{console_type}.log"
                self.file_paths[console_type] = file_path

            # 생성된 파일 추적을 위한 집합
            self.created_files = set()

            self.logger.info(f"📁 출력 디렉토리 준비 완료: {self.output_dir}")

        except Exception as e:
            self.logger.error(f"❌ 실시간 파일 준비 오류: {e}")

    def _save_console_data_realtime(
        self, console_type: str, message_text: str, raw_data: dict
    ):
        """콘솔 데이터를 실시간으로 파일에 저장 (데이터가 있을 때만 동적 생성)"""
        try:
            if console_type not in self.file_paths:
                return

            file_path = self.file_paths[console_type]
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[
                :-3
            ]  # 밀리초 포함

            # 파일이 처음 생성되는 경우에만 헤더 추가
            if console_type not in self.created_files:
                creation_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(
                        f"# Pyxel 게임 {console_type.upper()} 이벤트 로그 - {creation_timestamp}\n"
                    )
                    f.write(f"# 네임스페이스: {self.namespace}\n")
                    f.write(f"# 수집 시작: {creation_timestamp}\n")
                    f.write("# ===================================\n\n")

                self.created_files.add(console_type)
                self.logger.info(f"📝 새 이벤트 로그 생성: events_{console_type}.log")

            # 텍스트 데이터 추가
            with open(file_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] {str(message_text).strip()}\n")

            # 통계 업데이트를 위한 정보 저장
            self.console_data[console_type].append(message_text)
            self.console_raw_data[console_type].append(raw_data)

            # 실시간 로그
            total_count = len(self.console_data[console_type])
            self.logger.info(
                f"💾 {console_type.upper()} → events_{console_type}.log (총 {total_count}개)"
            )

        except Exception as e:
            self.logger.error(f"❌ 실시간 저장 오류 ({console_type}): {e}")

    def _register_signal_handlers(self):
        """시그널 핸들러 등록 - 강제 종료 시에도 데이터 저장"""

        def signal_handler(signum, frame):
            self.logger.info(
                f"\n🛑 시그널 {signum} 수신됨 - 데이터 저장 후 종료합니다..."
            )
            self.is_collecting = False

            # 수집된 데이터가 있으면 저장
            total_collected = sum(len(data) for data in self.console_data.values())
            if total_collected > 0:
                self.logger.info(
                    f"💾 수집된 데이터 ({total_collected}개)를 저장합니다..."
                )
                try:
                    # 기본값으로 저장 (collect_all=True, save_raw=True로 최대한 보존)
                    self.save_all_console_data(collect_all=True, save_raw=True)
                    self.logger.info("✅ 데이터 저장 완료")
                except Exception as e:
                    self.logger.error(f"❌ 데이터 저장 오류: {e}")

            # 브라우저 정리
            self.cleanup()

            # 종료
            sys.exit(0)

        # SIGINT (Ctrl+C)와 SIGTERM 처리
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    def log(self, message: str) -> None:
        """로그 메시지 출력 (직관적)"""
        if self.verbose:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] {message}")

    def start_browser(self, url: str) -> bool:
        """브라우저 시작 (매우 직관적)"""
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service

        try:
            options = Options()

            # 고유한 user data directory 생성 (충돌 방지)
            temp_dir = tempfile.mkdtemp(prefix="pyxel_collector_")
            options.add_argument(f"--user-data-dir={temp_dir}")

            options.add_argument(f"--remote-debugging-port={self.debug_port}")
            options.add_argument("--no-first-run")
            options.add_argument("--no-default-browser-check")
            options.add_argument("--disable-background-timer-throttling")
            options.add_argument("--disable-renderer-backgrounding")
            options.add_argument("--disable-backgrounding-occluded-windows")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-setuid-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-web-security")
            options.add_argument("--disable-features=VizDisplayCompositor")

            if self.headless:
                options.add_argument("--headless")

            self.logger.info(f"브라우저를 시작합니다: {url}")

            # WebDriver Manager로 ChromeDriver 자동 관리
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)
            self.driver = driver  # Assign after successful creation
            self.logger.info("✓ 브라우저 시작 완료")
            return True
        except Exception as e:
            self.logger.error(f"❌ 브라우저 시작 실패: {e}")
            return False

    def wait_for_text(self, text: str, timeout: int = 60) -> bool:
        """특정 텍스트가 나타날 때까지 대기 (직관적)"""
        if not self.driver:
            self.logger.info("브라우저가 시작되지 않았습니다")
            return False

        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        from selenium import webdriver

        self.logger.info(f"'{text}' 텍스트를 기다리는 중...")
        try:
            # 타입 안전성을 위해 간단한 방법 사용
            driver_ref = self.driver  # type: ignore
            wait = WebDriverWait(driver_ref, timeout)  # type: ignore
            wait.until(  # type: ignore
                EC.presence_of_element_located(
                    (By.XPATH, f"//*[contains(text(), '{text}')]")
                )
            )
            self.logger.info(f"✓ '{text}' 발견됨!")
            return True
        except Exception:
            self.logger.info(f"✗ '{text}' 텍스트 타임아웃")
            return False

    def click_center(self) -> None:
        """화면 중앙 클릭 (직관적) - Pyxel 게임 시작을 위한 개선된 클릭"""
        if not self.driver:
            self.logger.info("브라우저가 시작되지 않았습니다")
            return

        self.logger.info("화면 중앙을 클릭합니다...")
        try:
            # 먼저 페이지가 완전히 로드될 때까지 대기
            time.sleep(1)

            # 방법 1: Canvas 요소 직접 클릭 (Selenium native)
            try:
                from selenium.webdriver.common.by import By

                canvas_element = getattr(self.driver, "find_element")(
                    By.TAG_NAME, "canvas"
                )
                getattr(self.driver, "execute_script")(
                    "arguments[0].click();", canvas_element
                )
                self.logger.info("✓ Canvas 직접 클릭 완료")
                return
            except Exception as e:
                self.logger.debug(
                    f"Canvas 직접 클릭 실패: {e}, JavaScript 클릭으로 시도"
                )

            # 방법 2: JavaScript 클릭 (기존 방식 개선)
            getattr(self.driver, "execute_script")("""
                // Canvas 요소 찾기 (더 정확한 선택)
                const canvas = document.querySelector('canvas');
                if (canvas) {
                    // Canvas에 focus 부여
                    canvas.focus();
                    
                    // 클릭 이벤트 생성 및 발생
                    const rect = canvas.getBoundingClientRect();
                    const centerX = rect.left + rect.width / 2;
                    const centerY = rect.top + rect.height / 2;
                    
                    // 더 완전한 클릭 이벤트 시뮬레이션
                    ['mousedown', 'mouseup', 'click'].forEach(eventType => {
                        const event = new MouseEvent(eventType, {
                            view: window,
                            bubbles: true,
                            cancelable: true,
                            clientX: centerX,
                            clientY: centerY,
                            button: 0
                        });
                        canvas.dispatchEvent(event);
                    });
                    
                    console.log('Pyxel 게임 클릭 완료:', centerX, centerY);
                    return true;
                } else {
                    console.log('Canvas 요소를 찾을 수 없음');
                    return false;
                }
            """)
            self.logger.info("✓ 화면 클릭 완료")

        except Exception as e:
            self.logger.warning(f"⚠ 클릭 실패: {e}")

    def wait_for_pyxel_and_start_game(self, timeout: int = 60) -> bool:
        """Pyxel 로딩 대기 및 게임 시작 (개선된 버전)"""
        self.logger.info("🕒 Pyxel 게임 로딩을 기다리는 중...")
        start_time = time.time()

        # 1단계: Pyxel 로딩 대기
        pyxel_loaded = False
        while time.time() - start_time < timeout:
            try:
                message = self.console_messages.get(timeout=1)
                if message == "PYXEL_LOADED":
                    pyxel_loaded = True
                    break
            except queue.Empty:
                continue

        if not pyxel_loaded:
            self.logger.info("⏰ Pyxel 로딩 타임아웃")
            return False

        # 2단계: Pyxel 로딩 완료 후 안정화 대기
        self.logger.info("🎮 Pyxel 로딩 완료! 게임 안정화를 위해 대기 중...")
        time.sleep(2)  # Pyxel 게임이 완전히 초기화되도록 대기

        # 3단계: 게임 시작을 위한 클릭
        self.logger.info("🚀 게임을 시작합니다!")
        self.click_center()

        # 4단계: 클릭 후 게임 시작 대기
        time.sleep(2)  # 게임이 시작되고 데이터 생성을 시작할 시간 제공

        return True

    async def listen_to_console(self, url: str) -> None:
        """콘솔 메시지 청취 (활성 console 타입만 수집 + 동적 파일 생성)"""
        import websockets
        import aiohttp

        try:
            # DevTools에 연결
            await asyncio.sleep(2)  # 브라우저 안정화 대기

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://localhost:{self.debug_port}/json"
                ) as response:
                    tabs = await response.json()

            # 우리 페이지 찾기 - 더 유연한 매칭
            page_tab = None

            self.logger.debug(f"사용 가능한 탭들을 검색합니다... 총 {len(tabs)}개")

            for i, tab in enumerate(tabs):
                if tab is None:
                    continue
                tab_url = tab.get("url", "")
                tab_type = tab.get("type", "")
                self.logger.debug(f"탭 {i + 1}: {tab_url} (type: {tab_type})")

                # page 타입인 탭 중에서 매칭
                if tab_type == "page":
                    # 정확한 URL 매칭 또는 호스트:포트 매칭
                    if tab_url == url:
                        page_tab = tab
                        self.logger.info(f"✓ 정확한 URL 매칭: {tab_url}")
                        break
                    elif (
                        "0.0.0.0:5176" in tab_url
                        or "localhost:5176" in tab_url
                        or ":5176" in tab_url
                    ):
                        page_tab = tab
                        self.logger.info(f"✓ 포트 기반 매칭: {tab_url}")
                        break
                    elif (
                        "localhost" in tab_url
                        or "127.0.0.1" in tab_url
                        or "0.0.0.0" in tab_url
                    ):
                        # 로컬 서버면 일단 후보로 저장
                        if page_tab is None:  # 첫 번째 로컬 페이지만 저장
                            page_tab = tab
                            self.logger.info(f"? 로컬 호스트 후보: {tab_url}")

            if not page_tab:
                self.logger.error("페이지 탭을 찾을 수 없습니다")
                # 디버깅을 위해 사용 가능한 탭들 출력
                self.logger.info("사용 가능한 탭들:")
                for i, tab in enumerate(tabs[:5]):  # 처음 5개만 출력
                    if tab is not None:
                        self.logger.info(
                            f"  탭 {i + 1}: {tab.get('url', 'No URL')} (type: {tab.get('type', 'unknown')})"
                        )
                return

            ws_url = page_tab["webSocketDebuggerUrl"]
            self.logger.info(f"콘솔 연결: {ws_url}")

            async with websockets.connect(ws_url) as websocket:
                # Runtime 활성화
                await websocket.send(json.dumps({"id": 1, "method": "Runtime.enable"}))

                while self.is_collecting:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                        data = json.loads(message)

                        # 콘솔 메시지 처리
                        if data.get("method") == "Runtime.consoleAPICalled":
                            params = data.get("params", {})
                            console_type = params.get("type")

                            # 활성 console 타입인지 확인
                            if console_type in self.active_console_types:
                                args = params.get("args", [])
                                if args:
                                    message_text = args[0].get("value", "")

                                    # Pyxel 로딩 감지 (log 타입에서만)
                                    if console_type == "log" and "Loaded pyxel" in str(
                                        message_text
                                    ):
                                        self.console_messages.put("PYXEL_LOADED")
                                        self.logger.info("🎮 Pyxel 로딩 완료!")

                                    # 메시지가 있으면 수집 및 실시간 저장
                                    if message_text:
                                        # Raw 데이터 구성
                                        raw_entry = {
                                            "timestamp": datetime.now().isoformat(),
                                            "type": console_type,
                                            "level": params.get("level"),
                                            "args": params.get("args", []),
                                            "stackTrace": params.get("stackTrace"),
                                            "executionContextId": params.get(
                                                "executionContextId"
                                            ),
                                            "raw_params": params,
                                        }

                                        # 실시간 저장 (데이터가 있을 때만 파일 생성)
                                        self._save_console_data_realtime(
                                            console_type, message_text, raw_entry
                                        )

                                        # info 타입은 기존 호환성을 위해 queue에도 추가
                                        if console_type == "info":
                                            self.console_messages.put(message_text)

                                        # 로그 출력 (타입별 이모지)
                                        emoji_map = {
                                            "log": "📝",
                                            "info": "📊",
                                            "warn": "⚠️",
                                            "error": "❌",
                                            "debug": "🔍",
                                        }
                                        emoji = emoji_map.get(console_type, "💬")

                                        self.logger.info(
                                            f"{emoji} {console_type.upper()}: {message_text}"
                                        )

                    except asyncio.TimeoutError:
                        continue
                    except Exception as e:
                        self.logger.error(f"콘솔 청취 오류: {e}")
                        break

        except Exception as e:
            self.logger.error(f"콘솔 연결 실패: {e}")

    def collect_game_data(
        self,
        url: str,
        duration: Optional[int] = None,
        collect_all: bool = False,
        save_raw: bool = False,
    ) -> bool:
        """게임 데이터 수집 (메인 함수 - 새로운 namespace 기반)"""

        # 의존성 확인
        if not check_selenium_dependency() or not check_websockets_dependency():
            return False

        try:
            self.is_collecting = True

            # 1단계: 브라우저 시작
            if not self.start_browser(url):
                self.logger.error("❌ 브라우저 시작 실패")
                return False

            # 2단계: 콘솔 청취 시작
            console_task = threading.Thread(
                target=lambda: asyncio.run(self.listen_to_console(url))
            )
            console_task.daemon = True
            console_task.start()

            # 3단계: Pyxel 로딩 대기 및 게임 시작 (개선된 버전)
            if not self.wait_for_pyxel_and_start_game():
                self.logger.error("❌ Pyxel 게임을 시작할 수 없습니다")
                return False

            # 4단계: 데이터 수집 시작
            if duration:
                self.logger.info(f"📊 데이터 수집 시작... ({duration}초 동안)")
            else:
                self.logger.info(
                    "📊 데이터 수집 시작... (무한 수집 모드 - Ctrl+C로 종료)"
                )

            start_time = time.time()
            collected_count = 0

            # 5단계: 초기 대기 시간 (게임 데이터 생성 대기)
            initial_wait = 5  # 5초 동안 게임이 데이터를 생성할 시간 제공
            self.logger.info(f"⏳ 게임 데이터 생성 대기 중... ({initial_wait}초)")
            time.sleep(initial_wait)

            while self.is_collecting:
                # 시간 제한 확인 (duration이 설정된 경우에만)
                if duration and (time.time() - start_time) > duration:
                    self.logger.info(f"⏰ 시간 제한 ({duration}초) 도달")
                    break

                try:
                    message = self.console_messages.get(timeout=1)
                    if message != "PYXEL_LOADED" and message:
                        self.collected_data.append(message)
                        collected_count += 1

                        # 전체 수집된 데이터 수 계산
                        total_collected = sum(
                            len(data) for data in self.console_data.values()
                        )

                        # 무한 모드일 때는 경과 시간도 표시
                        if duration:
                            print(
                                f"📊 수집된 데이터: {collected_count}개 (전체: {total_collected}개)",
                                end="\r",
                            )
                        else:
                            elapsed = int(time.time() - start_time)
                            print(
                                f"📊 수집된 데이터: {collected_count}개 (전체: {total_collected}개) - 경과시간: {elapsed}초 [Ctrl+C로 종료]",
                                end="\r",
                            )

                except queue.Empty:
                    # 무한 모드에서는 주기적으로 상태 표시
                    if not duration:
                        elapsed = int(time.time() - start_time)
                        total_collected = sum(
                            len(data) for data in self.console_data.values()
                        )
                        print(
                            f"📊 수집 대기 중... (전체: {total_collected}개) - 경과시간: {elapsed}초 [Ctrl+C로 종료]",
                            end="\r",
                        )
                    continue
                except KeyboardInterrupt:
                    self.logger.info("\n⏹ 사용자가 중단했습니다 (Ctrl+C)")
                    break

            # 수집 결과 로깅
            total_collected = sum(len(data) for data in self.console_data.values())
            elapsed_time = int(time.time() - start_time)

            self.logger.info(
                f"\n🎉 총 {collected_count}개의 INFO 데이터를 수집했습니다!"
            )
            self.logger.info(
                f"🔍 전체 {total_collected}개의 console 데이터가 수집되었습니다!"
            )
            self.logger.info(f"⏱️ 총 수집 시간: {elapsed_time}초")

            # 타입별 수집 현황
            for console_type in self.active_console_types:
                if self.console_data[console_type]:
                    self.logger.info(
                        f"📝 {console_type.upper()}: {len(self.console_data[console_type])}개"
                    )

            # 데이터 저장
            self.save_all_console_data(collect_all=collect_all, save_raw=save_raw)

            return True

        except KeyboardInterrupt:
            self.logger.info("\n⏹ 사용자가 수집을 중단했습니다")

            # 중단되어도 지금까지 수집된 데이터는 저장
            total_collected = sum(len(data) for data in self.console_data.values())
            if total_collected > 0:
                self.logger.info(
                    f"💾 수집된 데이터 ({total_collected}개)를 저장합니다..."
                )
                self.save_all_console_data(collect_all=collect_all, save_raw=save_raw)

            return True

        except Exception as e:
            self.logger.error(f"❌ 수집 중 오류: {e}")
            return False
        finally:
            self.cleanup()

    def save_all_console_data(
        self, collect_all: bool = False, save_raw: bool = False
    ) -> None:
        """데이터가 있는 console 타입들만 최종 저장"""
        try:
            # 출력 디렉토리 생성
            output_dir = Path(f"data/{self.namespace}")
            output_dir.mkdir(parents=True, exist_ok=True)

            saved_files = []

            # 활성 타입들 중 실제 데이터가 있는 것들만 처리
            for console_type in self.active_console_types:
                if self.console_data[console_type]:  # 해당 타입에 데이터가 있으면
                    # 기본 데이터 저장이거나, collect_all 모드일 때 저장
                    if collect_all or console_type in ["log", "info"]:
                        # 최종 수집 파일 저장
                        final_file = output_dir / f"events_{console_type}_final.txt"
                        with open(final_file, "w", encoding="utf-8") as f:
                            f.write(
                                f"# Pyxel 게임 {console_type.upper()} 최종 수집 데이터 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            )
                            f.write(f"# 네임스페이스: {self.namespace}\n")
                            f.write(
                                f"# 총 {len(self.console_data[console_type])}개 이벤트\n"
                            )
                            f.write("# ===================================\n\n")
                            for message in self.console_data[console_type]:
                                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                f.write(f"[{timestamp}] {str(message).strip()}\n")

                        saved_files.append(str(final_file))
                        self.logger.info(
                            f"💾 {console_type.upper()} 최종 데이터 저장: events_{console_type}_final.txt ({len(self.console_data[console_type])}개)"
                        )

                        # Raw 데이터 저장 (요청 시)
                        if save_raw:
                            raw_file = output_dir / f"events_{console_type}_raw.json"
                            with open(raw_file, "w", encoding="utf-8") as f:
                                json.dump(
                                    {
                                        "collection_info": {
                                            "timestamp": datetime.now().isoformat(),
                                            "namespace": self.namespace,
                                            "console_type": console_type,
                                            "total_entries": len(
                                                self.console_raw_data[console_type]
                                            ),
                                            "collector_version": "SimplePyxelCollector v2.2",
                                        },
                                        "raw_console_data": self.console_raw_data[
                                            console_type
                                        ],
                                    },
                                    f,
                                    indent=2,
                                    ensure_ascii=False,
                                )

                            saved_files.append(str(raw_file))
                            self.logger.info(
                                f"💾 {console_type.upper()} Raw 데이터: events_{console_type}_raw.json ({len(self.console_raw_data[console_type])}개)"
                            )

            # 전체 통계 저장 (루트 디렉토리)
            stats_file = output_dir / "collection_summary.json"
            stats = {
                "collection_info": {
                    "timestamp": datetime.now().isoformat(),
                    "namespace": self.namespace,
                    "collector_version": "SimplePyxelCollector v2.2",
                },
                "console_type_counts": {
                    console_type: len(self.console_data[console_type])
                    for console_type in self.active_console_types
                    if self.console_data[console_type]
                },
                "total_events": sum(
                    len(self.console_data[console_type])
                    for console_type in self.active_console_types
                ),
                "active_event_types": [
                    console_type
                    for console_type in self.active_console_types
                    if self.console_data[console_type]
                ],
                "saved_files": saved_files,
            }

            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)

            self.logger.info(f"📊 수집 요약 저장 완료: {stats_file}")

        except Exception as e:
            self.logger.error(f"💾 데이터 저장 오류: {e}")

    def cleanup(self) -> None:
        """정리 작업 (직관적)"""
        self.is_collecting = False
        if self.driver:
            try:
                getattr(self.driver, "quit")()
                self.logger.info("🧹 브라우저 정리 완료")
            except:
                pass

    # 기존 save 메서드들은 호환성을 위해 유지하되 deprecated 처리
    def save_to_file(self, message: str, output_file: str) -> None:
        """파일에 저장 (직관적) - DEPRECATED: save_all_console_data 사용 권장"""
        try:
            # 출력 디렉토리 생성
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # 파일 헤더 확인/추가
            try:
                with open(output_file, "r", encoding="utf-8") as f:
                    pass
            except FileNotFoundError:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(
                        f"# Pyxel 게임 데이터 수집 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                    )

            # 데이터 추가
            with open(output_file, "a", encoding="utf-8") as f:
                clean_message = str(message).strip()
                f.write(f"[{timestamp}] {clean_message}\n")

        except Exception as e:
            self.logger.error(f"💾 파일 저장 오류: {e}")

    def save_raw_data(self, output_file: str) -> None:
        """Raw 데이터를 JSON 파일로 저장 - DEPRECATED"""
        # 호환성을 위해 info 타입 데이터를 저장
        try:
            if not self.console_raw_data.get("info"):
                self.logger.info("💾 저장할 Raw 데이터가 없습니다")
                return

            # .txt를 .raw.json으로 변경
            if output_file.endswith(".txt"):
                raw_output_file = output_file.replace(".txt", ".raw.json")
            else:
                raw_output_file = output_file + ".raw.json"

            # 출력 디렉토리 생성
            output_path = Path(raw_output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(raw_output_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "collection_info": {
                            "timestamp": datetime.now().isoformat(),
                            "total_entries": len(self.console_raw_data["info"]),
                            "collector_version": "SimplePyxelCollector v2.0",
                        },
                        "raw_console_data": self.console_raw_data["info"],
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            self.logger.info(
                f"💾 Raw 데이터 저장 완료: {raw_output_file} ({len(self.console_raw_data['info'])}개 항목)"
            )

        except Exception as e:
            self.logger.error(f"💾 Raw 데이터 저장 오류: {e}")

    def save_separated_data(self, base_output_file: str) -> None:
        """log와 info 데이터를 분리해서 저장 - DEPRECATED"""
        # 호환성을 위해 유지하되, 새로운 방식 사용 권장
        self.save_all_console_data(collect_all=True, save_raw=False)

    def save_separated_raw_data(self, base_output_file: str) -> None:
        """log와 info Raw 데이터를 분리해서 JSON으로 저장 - DEPRECATED"""
        # 호환성을 위해 유지하되, 새로운 방식 사용 권장
        self.save_all_console_data(collect_all=True, save_raw=True)


def collect_with_simple_api(
    url: str,
    output_file: Optional[str] = None,
    duration: Optional[int] = None,
    headless: bool = True,
    verbose: bool = False,
) -> int:
    """간단한 API로 Pyxel 데이터 수집"""

    collector = SimplePyxelCollector(headless=headless, verbose=verbose)

    success = collector.collect_game_data(
        url, duration=duration, collect_all=False, save_raw=False
    )
    return 0 if success else 1


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="간단한 Pyxel 데이터 수집기")
    parser.add_argument("--url", required=True, help="Pyxel 게임 URL")
    parser.add_argument(
        "--namespace", default="default", help="데이터 저장 네임스페이스"
    )
    parser.add_argument("--duration", type=int, help="수집 시간 (초)")
    parser.add_argument("--headless", action="store_true", help="헤드리스 모드")
    parser.add_argument("--verbose", action="store_true", help="상세 로그")
    parser.add_argument(
        "--debug", action="store_true", help="디버그 모드 (verbose와 동일)"
    )
    parser.add_argument(
        "--save-raw", action="store_true", help="Raw console 데이터도 JSON으로 저장"
    )
    parser.add_argument(
        "--collect-all",
        action="store_true",
        help="모든 console.* 타입을 개별 파일로 수집",
    )

    args = parser.parse_args()

    # debug는 verbose와 동일하게 처리
    verbose_mode = args.verbose or args.debug

    # 수집기 실행
    collector = SimplePyxelCollector(
        headless=args.headless, verbose=verbose_mode, namespace=args.namespace
    )
    success = collector.collect_game_data(
        url=args.url,
        duration=args.duration,
        collect_all=args.collect_all,
        save_raw=args.save_raw,
    )

    sys.exit(0 if success else 1)
