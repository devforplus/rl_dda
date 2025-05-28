#!/bin/bash

# Python HTTP Server 시작 스크립트
# 포트 5175에서 현재 디렉토리를 웹 서버로 제공합니다.

set -e  # 오류 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수들
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 포트 설정
PORT=5175
HOST="0.0.0.0"

# Python 버전 확인
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
        log_info "Python3 발견: $(python3 --version)"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
        log_info "Python 발견: $(python --version)"
    else
        log_error "Python이 설치되어 있지 않습니다."
        exit 1
    fi
}

# 포트 사용 중인지 확인
check_port() {
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        log_warning "포트 $PORT가 이미 사용 중입니다."
        log_info "기존 프로세스를 종료하시겠습니까? (y/N)"
        read -r response
        if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
            log_info "포트 $PORT를 사용하는 프로세스를 종료합니다..."
            lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
            sleep 1
        else
            log_error "서버 시작을 취소합니다."
            exit 1
        fi
    fi
}

# 서버 시작
start_server() {
    log_info "Python HTTP 서버를 시작합니다..."
    log_info "호스트: $HOST"
    log_info "포트: $PORT"
    log_info "디렉토리: $(pwd)"
    log_info ""
    log_success "서버가 시작되었습니다!"
    log_info "브라우저에서 다음 주소로 접속하세요:"
    log_info "  - 로컬: http://localhost:$PORT"
    log_info "  - 네트워크: http://$(hostname -I | awk '{print $1}'):$PORT"
    log_info ""
    log_warning "서버를 중지하려면 Ctrl+C를 누르세요."
    log_info ""
    
    # 서버 시작
    $PYTHON_CMD -m http.server $PORT --bind $HOST
}

# 신호 처리 (Ctrl+C)
cleanup() {
    log_info ""
    log_info "서버를 종료합니다..."
    exit 0
}

# 메인 실행
main() {
    log_info "=== Python HTTP Server 시작 스크립트 ==="
    log_info ""
    
    check_python
    check_port
    
    # 신호 처리 설정
    trap cleanup SIGINT SIGTERM
    
    start_server
}

# 스크립트 실행
main "$@" 