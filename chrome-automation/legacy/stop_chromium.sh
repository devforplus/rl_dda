#!/bin/bash

# Chromium 프로세스 종료 스크립트
# 사용법: ./stop_chromium.sh

echo "🔍 현재 실행 중인 Chromium 프로세스 확인..."
CHROMIUM_PIDS=$(pgrep -f chromium-browser)

if [ -z "$CHROMIUM_PIDS" ]; then
    echo "✅ 실행 중인 Chromium 프로세스가 없습니다."
    exit 0
fi

echo "📋 발견된 Chromium 프로세스:"
ps -ef | grep chromium-browser | grep -v grep | awk '{print "PID:", $2, "CMD:", $8, $9, $10, $11}'

echo ""
echo "🛑 Chromium 프로세스를 종료합니다..."

# SIGTERM으로 정상 종료 시도
pkill -TERM -f chromium-browser
sleep 3

# 아직 실행 중인 프로세스가 있는지 확인
REMAINING_PIDS=$(pgrep -f chromium-browser)

if [ ! -z "$REMAINING_PIDS" ]; then
    echo "⚠️  일부 프로세스가 여전히 실행 중입니다. 강제 종료합니다..."
    pkill -KILL -f chromium-browser
    sleep 1
fi

# 최종 확인
FINAL_CHECK=$(pgrep -f chromium-browser)
if [ -z "$FINAL_CHECK" ]; then
    echo "✅ 모든 Chromium 프로세스가 성공적으로 종료되었습니다."
else
    echo "❌ 일부 프로세스 종료에 실패했습니다:"
    ps -ef | grep chromium-browser | grep -v grep
fi 