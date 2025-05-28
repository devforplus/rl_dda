#!/bin/bash

# Chromium 원격 디버깅 스크립트
# 사용법: ./debug_chromium.sh [command] [debug_port]

# 기본값 설정
DEFAULT_DEBUG_PORT="9222"
DEBUG_PORT=${2:-$DEFAULT_DEBUG_PORT}
COMMAND=${1:-"status"}

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 도움말 함수
show_help() {
    echo "🔧 Chromium 원격 디버깅 도구"
    echo ""
    echo "사용법: $0 [command] [debug_port]"
    echo ""
    echo "Commands:"
    echo "  status    - 브라우저 상태 및 열린 탭 정보 표시 (기본값)"
    echo "  tabs      - 열린 탭 목록만 표시"
    echo "  version   - 브라우저 버전 정보"
    echo "  url       - 현재 활성 탭의 URL만 표시"
    echo "  title     - 현재 활성 탭의 제목만 표시"
    echo "  screenshot- 스크린샷 촬영 (Base64)"
    echo "  navigate  - 특정 URL로 이동 (3번째 인자로 URL 지정)"
    echo "  reload    - 현재 페이지 새로고침"
    echo "  help      - 이 도움말 표시"
    echo ""
    echo "Examples:"
    echo "  $0 status"
    echo "  $0 tabs 9222"
    echo "  $0 navigate 9222 https://google.com"
    echo "  $0 screenshot > screenshot.txt"
}

# 디버그 포트 연결 확인
check_debug_port() {
    if ! curl -s "http://localhost:$DEBUG_PORT/json/version" > /dev/null 2>&1; then
        echo -e "${RED}❌ 디버그 포트 $DEBUG_PORT 에 연결할 수 없습니다.${NC}"
        echo "Chromium이 --remote-debugging-port=$DEBUG_PORT 옵션으로 실행되었는지 확인하세요."
        exit 1
    fi
}

# 브라우저 버전 정보
show_version() {
    echo -e "${BLUE}🌐 브라우저 버전 정보:${NC}"
    curl -s "http://localhost:$DEBUG_PORT/json/version" | jq -r '
        "브라우저: " + .Browser + "\n" +
        "프로토콜 버전: " + .["Protocol-Version"] + "\n" +
        "User-Agent: " + .["User-Agent"] + "\n" +
        "V8 버전: " + .["V8-Version"] + "\n" +
        "WebKit 버전: " + .["WebKit-Version"]
    ' 2>/dev/null || curl -s "http://localhost:$DEBUG_PORT/json/version"
}

# 탭 목록 표시
show_tabs() {
    echo -e "${BLUE}📑 열린 탭 목록:${NC}"
    curl -s "http://localhost:$DEBUG_PORT/json" | jq -r '
        .[] | select(.type == "page") | 
        "ID: " + .id + "\n" +
        "제목: " + .title + "\n" +
        "URL: " + .url + "\n" +
        "---"
    ' 2>/dev/null || {
        echo "jq가 설치되지 않았습니다. 원시 JSON 데이터:"
        curl -s "http://localhost:$DEBUG_PORT/json"
    }
}

# 현재 활성 탭 URL
show_current_url() {
    curl -s "http://localhost:$DEBUG_PORT/json" | jq -r '.[0].url' 2>/dev/null || {
        curl -s "http://localhost:$DEBUG_PORT/json" | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4
    }
}

# 현재 활성 탭 제목
show_current_title() {
    curl -s "http://localhost:$DEBUG_PORT/json" | jq -r '.[0].title' 2>/dev/null || {
        curl -s "http://localhost:$DEBUG_PORT/json" | grep -o '"title":"[^"]*"' | head -1 | cut -d'"' -f4
    }
}

# 스크린샷 촬영
take_screenshot() {
    TAB_ID=$(curl -s "http://localhost:$DEBUG_PORT/json" | jq -r '.[0].id' 2>/dev/null)
    if [ "$TAB_ID" = "null" ] || [ -z "$TAB_ID" ]; then
        echo -e "${RED}❌ 활성 탭을 찾을 수 없습니다.${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}📸 스크린샷을 촬영합니다...${NC}"
    curl -s -X POST "http://localhost:$DEBUG_PORT/json/runtime/evaluate" \
        -H "Content-Type: application/json" \
        -d '{"expression": "JSON.stringify({screenshot: await new Promise(resolve => chrome.runtime.sendMessage({action: \"captureVisibleTab\"}, resolve))})"}' \
        2>/dev/null || echo "스크린샷 촬영 기능은 일부 환경에서 제한될 수 있습니다."
}

# URL 이동
navigate_to_url() {
    URL=$1
    if [ -z "$URL" ]; then
        echo -e "${RED}❌ URL을 지정해주세요.${NC}"
        echo "사용법: $0 navigate [debug_port] [URL]"
        return 1
    fi
    
    TAB_ID=$(curl -s "http://localhost:$DEBUG_PORT/json" | jq -r '.[0].id' 2>/dev/null)
    if [ "$TAB_ID" = "null" ] || [ -z "$TAB_ID" ]; then
        echo -e "${RED}❌ 활성 탭을 찾을 수 없습니다.${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}🔄 $URL 로 이동합니다...${NC}"
    curl -s -X POST "http://localhost:$DEBUG_PORT/json/runtime/evaluate" \
        -H "Content-Type: application/json" \
        -d "{\"expression\": \"window.location.href = '$URL'\"}" > /dev/null
    
    sleep 2
    echo -e "${GREEN}✅ 페이지 이동 완료${NC}"
}

# 페이지 새로고침
reload_page() {
    TAB_ID=$(curl -s "http://localhost:$DEBUG_PORT/json" | jq -r '.[0].id' 2>/dev/null)
    if [ "$TAB_ID" = "null" ] || [ -z "$TAB_ID" ]; then
        echo -e "${RED}❌ 활성 탭을 찾을 수 없습니다.${NC}"
        return 1
    fi
    
    echo -e "${YELLOW}🔄 페이지를 새로고침합니다...${NC}"
    curl -s -X POST "http://localhost:$DEBUG_PORT/json/runtime/evaluate" \
        -H "Content-Type: application/json" \
        -d '{"expression": "window.location.reload()"}' > /dev/null
    
    echo -e "${GREEN}✅ 새로고침 완료${NC}"
}

# 전체 상태 표시
show_status() {
    echo -e "${GREEN}🔍 Chromium 디버그 상태 (포트: $DEBUG_PORT)${NC}"
    echo ""
    
    show_version
    echo ""
    show_tabs
    
    echo ""
    echo -e "${BLUE}📊 추가 정보:${NC}"
    echo "현재 URL: $(show_current_url)"
    echo "현재 제목: $(show_current_title)"
    echo ""
    echo -e "${YELLOW}💡 사용 가능한 명령어: status, tabs, version, url, title, navigate, reload, help${NC}"
}

# 메인 로직
case $COMMAND in
    "help"|"-h"|"--help")
        show_help
        ;;
    "version")
        check_debug_port
        show_version
        ;;
    "tabs")
        check_debug_port
        show_tabs
        ;;
    "url")
        check_debug_port
        show_current_url
        ;;
    "title")
        check_debug_port
        show_current_title
        ;;
    "screenshot")
        check_debug_port
        take_screenshot
        ;;
    "navigate")
        check_debug_port
        navigate_to_url "$3"
        ;;
    "reload")
        check_debug_port
        reload_page
        ;;
    "status"|*)
        check_debug_port
        show_status
        ;;
esac 