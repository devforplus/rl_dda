#!/bin/bash

# Chromium 헤드리스 실행 스크립트 (가상 창 크기 지정)
# 사용법: ./start_chromium.sh [URL] [WIDTH] [HEIGHT] [DEBUG_PORT]

# 기본값 설정
DEFAULT_URL="http://localhost:5175"
DEFAULT_WIDTH="1920"
DEFAULT_HEIGHT="1080"
DEFAULT_DEBUG_PORT="9222"

# 매개변수 처리
URL=${1:-$DEFAULT_URL}
WIDTH=${2:-$DEFAULT_WIDTH}
HEIGHT=${3:-$DEFAULT_HEIGHT}
DEBUG_PORT=${4:-$DEFAULT_DEBUG_PORT}

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "🚀 Chromium 헤드리스 모드 실행"
echo "📍 URL: $URL"
echo "📐 창 크기: ${WIDTH}x${HEIGHT}"
echo "🔧 디버그 포트: $DEBUG_PORT"
echo ""

# 기존 Chromium 프로세스 확인
EXISTING_PIDS=$(pgrep -f chromium-browser)
if [ ! -z "$EXISTING_PIDS" ]; then
    echo -e "${YELLOW}⚠️  기존 Chromium 프로세스가 실행 중입니다:${NC}"
    ps -ef | grep chromium-browser | grep -v grep | awk '{print "PID:", $2}'
    echo ""
    read -p "기존 프로세스를 종료하고 계속하시겠습니까? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}🛑 기존 프로세스를 종료합니다...${NC}"
        pkill -f chromium-browser
        sleep 2
    else
        echo -e "${RED}❌ 실행을 취소합니다.${NC}"
        exit 1
    fi
fi

# 포트 사용 중인지 확인
if netstat -tuln 2>/dev/null | grep -q ":$DEBUG_PORT "; then
    echo -e "${YELLOW}⚠️  포트 $DEBUG_PORT 가 이미 사용 중입니다.${NC}"
    echo "다른 포트를 사용하거나 해당 프로세스를 종료해주세요."
    exit 1
fi

echo -e "${BLUE}▶️  Chromium을 백그라운드에서 실행합니다...${NC}"

# Chromium 실행 (직접 목표 URL로 시작)
chromium-browser \
    --headless \
    --disable-gpu \
    --remote-debugging-port=$DEBUG_PORT \
    --no-sandbox \
    --disable-dev-shm-usage \
    --window-size=$WIDTH,$HEIGHT \
    --disable-extensions \
    --disable-plugins \
    --disable-background-timer-throttling \
    --disable-backgrounding-occluded-windows \
    --disable-renderer-backgrounding \
    --no-first-run \
    --disable-default-apps \
    --disable-sync \
    --metrics-recording-only \
    --no-report-upload \
    --disable-web-security \
    --allow-running-insecure-content \
    --disable-features=VizDisplayCompositor \
    "$URL" &

CHROMIUM_PID=$!
echo -e "${GREEN}✅ Chromium이 시작되었습니다 (PID: $CHROMIUM_PID)${NC}"

# Chromium이 완전히 시작될 때까지 대기
echo -e "${YELLOW}⏳ Chromium 초기화를 기다리는 중...${NC}"
for i in {1..10}; do
    if curl -s "http://localhost:$DEBUG_PORT/json/version" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ 디버그 포트가 활성화되었습니다!${NC}"
        break
    fi
    echo "   시도 $i/10..."
    sleep 1
done

# 디버그 포트 연결 확인
if ! curl -s "http://localhost:$DEBUG_PORT/json/version" > /dev/null 2>&1; then
    echo -e "${RED}❌ 디버그 포트 연결에 실패했습니다.${NC}"
    kill $CHROMIUM_PID 2>/dev/null
    exit 1
fi

# URL 로딩 확인
echo -e "${YELLOW}⏳ 페이지 로딩을 확인하는 중...${NC}"
sleep 3

# 목표 탭에 포커스
echo -e "${BLUE}🎯 목표 탭에 포커스합니다...${NC}"
ALL_TABS=$(curl -s "http://localhost:$DEBUG_PORT/json")
echo "  🔍 탭 검색 중..."

# 더 유연한 탭 검색 로직 - localhost:5175 우선 검색
TARGET_TAB_ID=$(echo "$ALL_TABS" | jq -r '.[] | select(.url | contains("localhost:5175")) | .id' 2>/dev/null | head -1)

# 대안 검색 방법들
if [ -z "$TARGET_TAB_ID" ] || [ "$TARGET_TAB_ID" = "null" ]; then
    echo "  🔍 대안 검색 방법 1: 5175 포트 검색..."
    TARGET_TAB_ID=$(echo "$ALL_TABS" | jq -r '.[] | select(.url | contains(":5175")) | .id' 2>/dev/null | head -1)
fi

if [ -z "$TARGET_TAB_ID" ] || [ "$TARGET_TAB_ID" = "null" ]; then
    echo "  🔍 대안 검색 방법 2: localhost 검색..."
    TARGET_TAB_ID=$(echo "$ALL_TABS" | jq -r '.[] | select(.url | contains("localhost")) | .id' 2>/dev/null | head -1)
fi

if [ -z "$TARGET_TAB_ID" ] || [ "$TARGET_TAB_ID" = "null" ]; then
    echo "  🔍 대안 검색 방법 3: page 타입 검색..."
    TARGET_TAB_ID=$(echo "$ALL_TABS" | jq -r '.[] | select(.type == "page") | .id' 2>/dev/null | head -1)
fi

# jq가 없는 경우 grep 사용
if [ -z "$TARGET_TAB_ID" ] || [ "$TARGET_TAB_ID" = "null" ]; then
    echo "  🔍 대안 검색 방법 4: grep 사용..."
    # localhost:5175가 포함된 줄을 찾고, 그 앞의 id를 추출
    TARGET_TAB_ID=$(echo "$ALL_TABS" | grep -B10 "localhost:5175" | grep '"id":' | tail -1 | sed 's/.*"id": *"\([^"]*\)".*/\1/')
fi

if [ ! -z "$TARGET_TAB_ID" ] && [ "$TARGET_TAB_ID" != "null" ]; then
    echo "  🎯 대상 탭 발견: $TARGET_TAB_ID"
    curl -s -X POST "http://localhost:$DEBUG_PORT/json/activate/$TARGET_TAB_ID" > /dev/null
    echo "  ✅ 탭 활성화 완료"
else
    echo "  ❌ 대상 탭을 찾을 수 없습니다."
    echo "  📋 현재 열린 탭들:"
    echo "$ALL_TABS" | grep -E '"(id|url|title)"' | sed 's/^/    /'
fi

sleep 1

# 페이지 완전 로딩 대기 및 자동 클릭 수행
echo -e "${YELLOW}⏳ Pyxel 로딩을 기다리는 중...${NC}"
echo -e "${BLUE}🔍 Console에서 'Loaded pyxel' 메시지를 감지합니다...${NC}"

# 화면 중앙 좌표 계산 (창 크기의 절반)
CLICK_X=$((WIDTH / 2))
CLICK_Y=$((HEIGHT / 2))

# Chrome DevTools Protocol을 사용한 Console 모니터링 및 클릭 수행
if [ ! -z "$TARGET_TAB_ID" ] && [ "$TARGET_TAB_ID" != "null" ]; then
    # WebSocket URL 생성 - jq 우선 사용
    WS_URL=$(echo "$ALL_TABS" | jq -r ".[] | select(.id == \"$TARGET_TAB_ID\") | .webSocketDebuggerUrl" 2>/dev/null)
    
    # jq가 실패하거나 없는 경우 grep 사용
    if [ -z "$WS_URL" ] || [ "$WS_URL" = "null" ]; then
        echo "  🔍 WebSocket URL grep으로 검색..."
        WS_URL=$(echo "$ALL_TABS" | grep -A20 "\"id\": *\"$TARGET_TAB_ID\"" | grep '"webSocketDebuggerUrl"' | head -1 | sed 's/.*"webSocketDebuggerUrl": *"\([^"]*\)".*/\1/')
    fi
    
    echo "  🔗 WebSocket URL: $WS_URL"
    
    if [ ! -z "$WS_URL" ] && [ "$WS_URL" != "null" ]; then
        # 임시 스크립트 파일 생성 - Console 모니터링 및 클릭
        TEMP_SCRIPT="/tmp/pyxel_click_script_$$.js"
        cat > "$TEMP_SCRIPT" << 'EOF'
const WebSocket = require('ws');

const wsUrl = process.argv[2];
const x = parseInt(process.argv[3]);
const y = parseInt(process.argv[4]);

console.log(`🔗 WebSocket 연결 중: ${wsUrl}`);
console.log(`🎯 클릭 좌표: (${x}, ${y})`);

const ws = new WebSocket(wsUrl);
let pyxelLoaded = false;

ws.on('open', function() {
    console.log('✅ WebSocket 연결 성공');
    
    // Runtime 활성화 (Console 이벤트를 위해 필요)
    ws.send(JSON.stringify({
        id: 1,
        method: 'Runtime.enable'
    }));
    
    // Console 도메인 활성화
    ws.send(JSON.stringify({
        id: 2,
        method: 'Console.enable'
    }));
    
    // Input 도메인 활성화
    ws.send(JSON.stringify({
        id: 3,
        method: 'Input.enable'
    }));
    
    console.log('📺 Console 메시지 모니터링 시작...');
    
    // 타임아웃 설정 (30초 후 강제 종료)
    setTimeout(() => {
        if (!pyxelLoaded) {
            console.log('⏰ 타임아웃: Pyxel 로딩 메시지를 찾지 못했습니다.');
            ws.close();
            process.exit(1);
        }
    }, 30000);
});

ws.on('message', function(data) {
    try {
        const message = JSON.parse(data);
        
        // Console API 호출 이벤트 감지
        if (message.method === 'Runtime.consoleAPICalled') {
            const consoleMessage = message.params;
            
            // 메시지 텍스트 추출
            let text = '';
            if (consoleMessage.args && consoleMessage.args.length > 0) {
                text = consoleMessage.args.map(arg => {
                    if (arg.value !== undefined) {
                        return arg.value;
                    } else if (arg.description) {
                        return arg.description;
                    }
                    return '';
                }).join(' ');
            }
            
            console.log(`📝 Console: ${text}`);
            
            // "Loaded pyxel" 메시지 감지
            if (text.includes('Loaded pyxel') && !pyxelLoaded) {
                pyxelLoaded = true;
                console.log('🎉 Pyxel 로딩 완료 감지!');
                console.log('⏳ 1초 후 클릭을 수행합니다...');
                
                setTimeout(() => {
                    console.log(`🖱️  화면 중앙(${x}, ${y})을 클릭합니다...`);
                    
                    // 마우스 클릭 이벤트 전송
                    ws.send(JSON.stringify({
                        id: 10,
                        method: 'Input.dispatchMouseEvent',
                        params: {
                            type: 'mousePressed',
                            x: x,
                            y: y,
                            button: 'left',
                            clickCount: 1
                        }
                    }));
                    
                    setTimeout(() => {
                        ws.send(JSON.stringify({
                            id: 11,
                            method: 'Input.dispatchMouseEvent',
                            params: {
                                type: 'mouseReleased',
                                x: x,
                                y: y,
                                button: 'left',
                                clickCount: 1
                            }
                        }));
                        
                        console.log('✅ 클릭 완료!');
                        
                        setTimeout(() => {
                            ws.close();
                            process.exit(0);
                        }, 500);
                    }, 100);
                }, 1000);
            }
        }
        
    } catch (error) {
        console.error(`❌ 메시지 파싱 오류: ${error.message}`);
    }
});

ws.on('error', function(error) {
    console.error(`❌ WebSocket 오류: ${error.message}`);
    process.exit(1);
});

ws.on('close', function() {
    if (pyxelLoaded) {
        console.log('🏁 작업 완료');
    } else {
        console.log('⚠️  WebSocket 연결이 예상치 못하게 종료되었습니다');
    }
});
EOF

        # Node.js가 설치되어 있는지 확인
        if command -v node >/dev/null 2>&1; then
            # WebSocket 모듈 설치 확인
            if node -e "require('ws')" 2>/dev/null; then
                # 현재 디렉토리에서 node_modules를 사용할 수 있도록 NODE_PATH 설정
                export NODE_PATH="$(pwd)/node_modules:$NODE_PATH"
                cd "$(dirname "$0")" 2>/dev/null || true
                node "$TEMP_SCRIPT" "$WS_URL" "$CLICK_X" "$CLICK_Y"
                CLICK_RESULT=$?
                if [ $CLICK_RESULT -eq 0 ]; then
                    echo -e "${GREEN}✅ Pyxel 로딩 감지 후 자동 클릭이 완료되었습니다!${NC}"
                else
                    echo -e "${YELLOW}⚠️  Pyxel 로딩 메시지를 감지하지 못했습니다.${NC}"
                fi
            else
                echo -e "${YELLOW}⚠️  ws 모듈이 설치되지 않아 자동 클릭을 건너뜁니다.${NC}"
                echo "   npm install ws 명령으로 설치할 수 있습니다."
            fi
        else
            echo -e "${YELLOW}⚠️  Node.js가 설치되지 않아 자동 클릭을 건너뜁니다.${NC}"
        fi
        
        # 임시 파일 정리
        rm -f "$TEMP_SCRIPT"
    else
        echo -e "${YELLOW}⚠️  WebSocket URL을 찾을 수 없어 자동 클릭을 건너뜁니다.${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  대상 탭을 찾을 수 없어 자동 클릭을 건너뜁니다.${NC}"
fi

sleep 1

# 최종 상태 확인
CURRENT_URL=$(curl -s "http://localhost:$DEBUG_PORT/json" | grep -o '"url":"[^"]*"' | head -1 | cut -d'"' -f4)
CURRENT_TITLE=$(curl -s "http://localhost:$DEBUG_PORT/json" | grep -o '"title":"[^"]*"' | head -1 | cut -d'"' -f4)

if ps -p $CHROMIUM_PID > /dev/null; then
    echo -e "${GREEN}🎉 Chromium이 성공적으로 실행 중입니다!${NC}"
    echo ""
    echo -e "${BLUE}📊 현재 상태:${NC}"
    echo "  현재 URL: $CURRENT_URL"
    echo "  페이지 제목: $CURRENT_TITLE"
    echo ""
    echo -e "${BLUE}📊 상태 확인 명령어:${NC}"
    echo "  프로세스 확인: ps -ef | grep chromium-browser | grep -v grep"
    echo "  디버그 정보: ./debug_chromium.sh"
    echo "  종료: ./stop_chromium.sh 또는 kill $CHROMIUM_PID"
    echo ""
    echo -e "${BLUE}🌐 원격 디버깅 URL:${NC}"
    echo "  http://localhost:$DEBUG_PORT"
    
    # URL이 제대로 로드되었는지 확인
    if [[ "$CURRENT_URL" == *"$URL"* ]] || [[ "$CURRENT_URL" == "$URL" ]]; then
        echo -e "${GREEN}✅ 지정된 URL이 성공적으로 로드되었습니다!${NC}"
    else
        echo -e "${YELLOW}⚠️  URL 로딩에 문제가 있을 수 있습니다. debug_chromium.sh로 상태를 확인해보세요.${NC}"
    fi
else
    echo -e "${RED}❌ Chromium 실행에 실패했습니다.${NC}"
    exit 1
fi 