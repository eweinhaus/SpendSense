#!/bin/bash

# Script to stop all SpendSense instances

echo "Stopping all SpendSense instances..."

for pidfile in /tmp/spendsense_*.pid; do
    if [ -f "$pidfile" ]; then
        pid=$(cat "$pidfile")
        if ps -p $pid > /dev/null 2>&1; then
            echo "Stopping process $pid..."
            kill $pid 2>/dev/null
        fi
        rm "$pidfile"
    fi
done

# Also kill any uvicorn processes on ports 8000-8002
for port in 8000 8001 8002; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "Killing process on port $port..."
        lsof -ti:$port | xargs kill -9 2>/dev/null
    fi
done

echo "✅ All instances stopped!"




