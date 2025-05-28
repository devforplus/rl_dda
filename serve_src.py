#!/usr/bin/env python3
"""
src 디렉토리를 HTTP 서버로 서빙하는 스크립트
포트: 5175

사용법:
  python3 serve_src.py           # 포그라운드에서 실행
  python3 serve_src.py --daemon  # 백그라운드에서 실행
  python3 serve_src.py --stop    # 백그라운드 서버 종료
  python3 serve_src.py --status  # 서버 상태 확인
"""

import http.server
import socketserver
import os
import sys
import webbrowser
import threading
import time
import signal
import argparse
import subprocess
import json
from pathlib import Path

# 설정
PORT = 5175
DIRECTORY = "src"
PID_FILE = "/tmp/serve_src.pid"
LOG_FILE = "/tmp/serve_src.log"


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """CORS 헤더를 추가한 커스텀 HTTP 요청 핸들러"""

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        """로그 메시지를 파일에 기록"""
        if "--daemon" in sys.argv:
            with open(LOG_FILE, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {format % args}\n")
        else:
            super().log_message(format, *args)


def open_browser_delayed():
    """3초 후 브라우저를 자동으로 열기"""
    time.sleep(3)
    url = f"http://localhost:{PORT}"
    try:
        webbrowser.open(url)
        print(f"🌐 브라우저에서 {url} 을 열었습니다.")
    except Exception as e:
        print(f"⚠️  브라우저 자동 열기 실패: {e}")


def save_pid():
    """현재 프로세스 ID를 파일에 저장"""
    with open(PID_FILE, "w") as f:
        json.dump(
            {
                "pid": os.getpid(),
                "port": PORT,
                "directory": os.getcwd(),
                "started_at": time.time(),
            },
            f,
        )


def load_pid():
    """저장된 프로세스 정보 로드"""
    try:
        with open(PID_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def is_process_running(pid):
    """프로세스가 실행 중인지 확인"""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def stop_daemon():
    """데몬 프로세스 종료"""
    pid_info = load_pid()
    if not pid_info:
        print("❌ 실행 중인 서버를 찾을 수 없습니다.")
        return 1

    pid = pid_info["pid"]
    if not is_process_running(pid):
        print("❌ 서버가 실행 중이지 않습니다.")
        os.remove(PID_FILE)
        return 1

    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        if is_process_running(pid):
            os.kill(pid, signal.SIGKILL)

        os.remove(PID_FILE)
        print(f"✅ 서버가 종료되었습니다 (PID: {pid})")
        return 0
    except Exception as e:
        print(f"❌ 서버 종료 실패: {e}")
        return 1


def status_daemon():
    """데몬 상태 확인"""
    pid_info = load_pid()
    if not pid_info:
        print("❌ 실행 중인 서버를 찾을 수 없습니다.")
        return 1

    pid = pid_info["pid"]
    if not is_process_running(pid):
        print("❌ 서버가 실행 중이지 않습니다.")
        os.remove(PID_FILE)
        return 1

    started_at = time.strftime(
        "%Y-%m-%d %H:%M:%S", time.localtime(pid_info["started_at"])
    )
    uptime = time.time() - pid_info["started_at"]
    uptime_str = (
        f"{int(uptime // 3600)}시간 {int((uptime % 3600) // 60)}분 {int(uptime % 60)}초"
    )

    print(f"✅ 서버가 실행 중입니다")
    print(f"   PID: {pid}")
    print(f"   포트: {pid_info['port']}")
    print(f"   디렉토리: {pid_info['directory']}")
    print(f"   시작 시간: {started_at}")
    print(f"   업타임: {uptime_str}")
    print(f"   URL: http://localhost:{pid_info['port']}")
    return 0


def start_daemon():
    """데몬으로 서버 시작"""
    # 이미 실행 중인지 확인
    pid_info = load_pid()
    if pid_info and is_process_running(pid_info["pid"]):
        print(f"❌ 서버가 이미 실행 중입니다 (PID: {pid_info['pid']})")
        return 1

    # 백그라운드로 실행
    cmd = [sys.executable, __file__, "--daemon-process"]
    with open(LOG_FILE, "w") as log_file:
        process = subprocess.Popen(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )

    time.sleep(1)  # 프로세스 시작 대기

    if process.poll() is None:
        print(f"✅ 서버가 백그라운드에서 시작되었습니다 (PID: {process.pid})")
        print(f"🌐 URL: http://localhost:{PORT}")
        print(f"📝 로그: {LOG_FILE}")
        print(f"🛑 종료: python3 {__file__} --stop")
        return 0
    else:
        print("❌ 서버 시작에 실패했습니다.")
        return 1


def main_daemon_process():
    """실제 데몬 프로세스 메인 함수"""
    # src 디렉토리 존재 확인
    src_path = Path(DIRECTORY)
    if not src_path.exists():
        print(f"❌ 오류: '{DIRECTORY}' 디렉토리를 찾을 수 없습니다.")
        print(f"현재 위치: {os.getcwd()}")
        return 1

    if not src_path.is_dir():
        print(f"❌ 오류: '{DIRECTORY}'는 디렉토리가 아닙니다.")
        return 1

    # src 디렉토리로 이동
    os.chdir(src_path)

    # PID 저장
    save_pid()

    # 신호 핸들러 설정
    def signal_handler(signum, frame):
        print(f"\n🛑 서버가 종료되었습니다 (신호: {signum})")
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        sys.exit(0)

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # HTTP 서버 설정
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            print(f"🚀 HTTP 서버가 포트 {PORT}에서 시작되었습니다.")
            print(f"📁 서빙 디렉토리: {src_path.absolute()}")

            # 서버 시작
            httpd.serve_forever()

    except OSError as e:
        if e.errno == 98:  # Address already in use
            print(f"❌ 오류: 포트 {PORT}가 이미 사용 중입니다.")
        else:
            print(f"❌ 오류: {e}")
        return 1
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {e}")
        return 1


def main():
    parser = argparse.ArgumentParser(description="src 디렉토리 HTTP 서버")
    parser.add_argument("--daemon", action="store_true", help="백그라운드에서 실행")
    parser.add_argument(
        "--daemon-process", action="store_true", help="데몬 프로세스 (내부용)"
    )
    parser.add_argument("--stop", action="store_true", help="백그라운드 서버 종료")
    parser.add_argument("--status", action="store_true", help="서버 상태 확인")
    parser.add_argument(
        "--no-browser", action="store_true", help="브라우저 자동 열기 비활성화"
    )

    args = parser.parse_args()

    if args.daemon_process:
        return main_daemon_process()
    elif args.stop:
        return stop_daemon()
    elif args.status:
        return status_daemon()
    elif args.daemon:
        return start_daemon()
    else:
        # 포그라운드 실행
        # src 디렉토리 존재 확인
        src_path = Path(DIRECTORY)
        if not src_path.exists():
            print(f"❌ 오류: '{DIRECTORY}' 디렉토리를 찾을 수 없습니다.")
            print(f"현재 위치: {os.getcwd()}")
            return 1

        if not src_path.is_dir():
            print(f"❌ 오류: '{DIRECTORY}'는 디렉토리가 아닙니다.")
            return 1

        # src 디렉토리로 이동
        os.chdir(src_path)
        print(f"📁 서빙 디렉토리: {src_path.absolute()}")

        try:
            # HTTP 서버 설정
            with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
                print(f"🚀 HTTP 서버가 포트 {PORT}에서 시작되었습니다.")
                print(f"🌐 브라우저에서 http://localhost:{PORT} 에 접속하세요.")
                print("🛑 종료하려면 Ctrl+C를 누르세요.")
                print("-" * 50)

                # 브라우저 자동 열기 (백그라운드에서)
                if not args.no_browser:
                    browser_thread = threading.Thread(
                        target=open_browser_delayed, daemon=True
                    )
                    browser_thread.start()

                # 서버 시작
                httpd.serve_forever()

        except KeyboardInterrupt:
            print("\n🛑 서버가 종료되었습니다.")
            return 0
        except OSError as e:
            if e.errno == 98:  # Address already in use
                print(f"❌ 오류: 포트 {PORT}가 이미 사용 중입니다.")
                print("다른 프로세스가 해당 포트를 사용하고 있는지 확인하세요.")
            else:
                print(f"❌ 오류: {e}")
            return 1
        except Exception as e:
            print(f"❌ 예상치 못한 오류: {e}")
            return 1


if __name__ == "__main__":
    sys.exit(main())
