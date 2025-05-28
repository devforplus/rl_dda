#!/bin/bash

# src 디렉토리를 HTTP 서버로 서빙하는 스크립트
# 포트: 5175

PORT=5175
DIRECTORY="src"
PID_FILE="/tmp/serve_src_sh.pid"
LOG_FILE="/tmp/serve_src_sh.log"

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 도움말 출력
show_help() {
    echo -e "${BLUE}src 디렉토리 HTTP 서버${NC}"
    echo "사용법:"
    echo "  $0                    # 포그라운드에서 실행"
    echo "  $0 --daemon          # 백그라운드에서 실행"
    echo "  $0 --stop            # 백그라운드 서버 종료"
    echo "  $0 --status          # 서버 상태 확인"
    echo "  $0 --help            # 도움말 출력"
    echo ""
    echo "옵션:"
    echo "  --daemon             백그라운드에서 서버 실행"
    echo "  --stop               백그라운드 서버 종료"
    echo "  --status             서버 상태 확인"
    echo "  --help               이 도움말 출력"
}

# PID 파일에서 프로세스 정보 읽기
load_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    else
        echo ""
    fi
}

# 프로세스가 실행 중인지 확인
is_process_running() {
    local pid=$1
    if [ -z "$pid" ]; then
        return 1
    fi
    
    if ps -p "$pid" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 백그라운드 서버 종료
stop_daemon() {
    local pid=$(load_pid)
    
    if [ -z "$pid" ]; then
        echo -e "${RED}❌ 실행 중인 서버를 찾을 수 없습니다.${NC}"
        return 1
    fi
    
    if ! is_process_running "$pid"; then
        echo -e "${RED}❌ 서버가 실행 중이지 않습니다.${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
    
    echo -e "${YELLOW}🛑 서버를 종료하는 중... (PID: $pid)${NC}"
    
    # SIGTERM으로 정상 종료 시도
    kill "$pid" 2>/dev/null
    sleep 2
    
    # 아직 실행 중이면 SIGKILL로 강제 종료
    if is_process_running "$pid"; then
        kill -9 "$pid" 2>/dev/null
        sleep 1
    fi
    
    if is_process_running "$pid"; then
        echo -e "${RED}❌ 서버 종료에 실패했습니다.${NC}"
        return 1
    else
        rm -f "$PID_FILE"
        echo -e "${GREEN}✅ 서버가 종료되었습니다.${NC}"
        return 0
    fi
}

# 서버 상태 확인
status_daemon() {
    local pid=$(load_pid)
    
    if [ -z "$pid" ]; then
        echo -e "${RED}❌ 실행 중인 서버를 찾을 수 없습니다.${NC}"
        return 1
    fi
    
    if ! is_process_running "$pid"; then
        echo -e "${RED}❌ 서버가 실행 중이지 않습니다.${NC}"
        rm -f "$PID_FILE"
        return 1
    fi
    
    # 프로세스 정보 가져오기
    local start_time=$(ps -p "$pid" -o lstart= 2>/dev/null | sed 's/^[[:space:]]*//')
    local cpu_time=$(ps -p "$pid" -o time= 2>/dev/null | sed 's/^[[:space:]]*//')
    
    echo -e "${GREEN}✅ 서버가 실행 중입니다${NC}"
    echo -e "   ${BLUE}PID:${NC} $pid"
    echo -e "   ${BLUE}포트:${NC} $PORT"
    echo -e "   ${BLUE}디렉토리:${NC} $(pwd)/$DIRECTORY"
    echo -e "   ${BLUE}시작 시간:${NC} $start_time"
    echo -e "   ${BLUE}CPU 시간:${NC} $cpu_time"
    echo -e "   ${BLUE}URL:${NC} http://localhost:$PORT"
    echo -e "   ${BLUE}로그:${NC} $LOG_FILE"
    return 0
}

# 백그라운드에서 서버 시작
start_daemon() {
    # 이미 실행 중인지 확인
    local existing_pid=$(load_pid)
    if [ -n "$existing_pid" ] && is_process_running "$existing_pid"; then
        echo -e "${RED}❌ 서버가 이미 실행 중입니다 (PID: $existing_pid)${NC}"
        return 1
    fi
    
    # src 디렉토리 존재 확인
    if [ ! -d "$DIRECTORY" ]; then
        echo -e "${RED}❌ 오류: '$DIRECTORY' 디렉토리를 찾을 수 없습니다.${NC}"
        echo -e "${YELLOW}현재 위치: $(pwd)${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}🚀 백그라운드에서 서버를 시작하는 중...${NC}"
    
    # 백그라운드에서 서버 실행
    (
        cd "$DIRECTORY" || exit 1
        echo "$(date): 서버 시작 - 포트 $PORT" > "$LOG_FILE"
        echo "$(date): 디렉토리 $(pwd)" >> "$LOG_FILE"
        
        # 신호 핸들러 설정을 위한 트랩
        trap 'echo "$(date): 서버 종료 신호 수신" >> "$LOG_FILE"; exit 0' TERM INT
        
        # Python HTTP 서버 시작
        python3 -m http.server "$PORT" >> "$LOG_FILE" 2>&1 &
        local server_pid=$!
        
        # 메인 프로세스 PID 저장
        echo $$ > "$PID_FILE"
        
        # 서버 프로세스 대기
        wait $server_pid
        
        # 정리
        rm -f "$PID_FILE"
        echo "$(date): 서버 종료 완료" >> "$LOG_FILE"
    ) &
    
    local daemon_pid=$!
    sleep 1
    
    # 데몬이 정상적으로 시작되었는지 확인
    if is_process_running "$daemon_pid"; then
        echo -e "${GREEN}✅ 서버가 백그라운드에서 시작되었습니다 (PID: $daemon_pid)${NC}"
        echo -e "${GREEN}🌐 URL: http://localhost:$PORT${NC}"
        echo -e "${GREEN}📝 로그: $LOG_FILE${NC}"
        echo -e "${GREEN}🛑 종료: $0 --stop${NC}"
        return 0
    else
        echo -e "${RED}❌ 서버 시작에 실패했습니다.${NC}"
        return 1
    fi
}

# 포그라운드에서 서버 실행
start_foreground() {
    echo -e "${BLUE}🚀 src 디렉토리 HTTP 서버 시작${NC}"

    # src 디렉토리 존재 확인
    if [ ! -d "$DIRECTORY" ]; then
        echo -e "${RED}❌ 오류: '$DIRECTORY' 디렉토리를 찾을 수 없습니다.${NC}"
        echo -e "${YELLOW}현재 위치: $(pwd)${NC}"
        exit 1
    fi

    # src 디렉토리로 이동
    cd "$DIRECTORY" || exit 1

    echo -e "${GREEN}📁 서빙 디렉토리: $(pwd)${NC}"
    echo -e "${GREEN}🌐 브라우저에서 http://localhost:$PORT 에 접속하세요.${NC}"
    echo -e "${YELLOW}🛑 종료하려면 Ctrl+C를 누르세요.${NC}"
    echo "----------------------------------------"

    # 신호 핸들러 설정
    trap 'echo -e "\n${YELLOW}🛑 서버가 종료되었습니다.${NC}"; exit 0' TERM INT

    # Python3 http.server 시작
    python3 -m http.server $PORT 
}

# 메인 로직
case "$1" in
    --daemon)
        start_daemon
        ;;
    --stop)
        stop_daemon
        ;;
    --status)
        status_daemon
        ;;
    --help|-h)
        show_help
        ;;
    "")
        start_foreground
        ;;
    *)
        echo -e "${RED}❌ 알 수 없는 옵션: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac 