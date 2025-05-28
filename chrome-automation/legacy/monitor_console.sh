#!/bin/bash

# Chrome DevTools Console Monitor 실행 스크립트
# 사용법: ./monitor_console.sh [DEBUG_PORT] [URL_PATTERN]

# 기본값 설정
DEFAULT_DEBUG_PORT="9222"
DEFAULT_URL_PATTERN="localhost:5175"

# 매개변수 처리
DEBUG_PORT=${1:-$DEFAULT_DEBUG_PORT}
URL_PATTERN=${2:-$DEFAULT_URL_PATTERN}

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🔍 Chrome DevTools Console Monitor"
echo "📍 디버그 포트: $DEBUG_PORT"
echo "🎯 URL 패턴: $URL_PATTERN"
echo ""

# Node.js 설치 확인
if ! command -v node >/dev/null 2>&1; then
    echo -e "${RED}❌ Node.js가 설치되지 않았습니다.${NC}"
    echo "Node.js를 설치한 후 다시 시도해주세요."
    exit 1
fi

# ws 모듈 설치 확인
if ! node -e "require('ws')" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  ws 모듈이 설치되지 않았습니다.${NC}"
    echo "설치 중..."
    npm install ws
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ ws 모듈 설치에 실패했습니다.${NC}"
        exit 1
    fi
fi

# node-fetch 모듈 설치 확인 (Node.js 18 미만에서 필요)
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    if ! node -e "require('node-fetch')" 2>/dev/null; then
        echo -e "${YELLOW}⚠️  node-fetch 모듈이 설치되지 않았습니다.${NC}"
        echo "설치 중..."
        npm install node-fetch
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ node-fetch 모듈 설치에 실패했습니다.${NC}"
            exit 1
        fi
    fi
fi

# Chrome DevTools 연결 확인
if ! curl -s "http://localhost:$DEBUG_PORT/json/version" > /dev/null 2>&1; then
    echo -e "${RED}❌ Chrome DevTools에 연결할 수 없습니다.${NC}"
    echo "포트 $DEBUG_PORT 에서 Chrome이 실행 중인지 확인해주세요."
    echo ""
    echo "Chrome을 다음 옵션으로 실행해야 합니다:"
    echo "  --remote-debugging-port=$DEBUG_PORT"
    echo ""
    echo "또는 start_chromium.sh 스크립트를 먼저 실행해주세요."
    exit 1
fi

echo -e "${GREEN}✅ 모든 의존성이 준비되었습니다.${NC}"
echo -e "${BLUE}🚀 Console 모니터링을 시작합니다...${NC}"
echo ""
echo -e "${YELLOW}💡 종료하려면 Ctrl+C를 누르세요${NC}"
echo ""

# Console 모니터 실행
node console_monitor.js "$DEBUG_PORT" "$URL_PATTERN" 