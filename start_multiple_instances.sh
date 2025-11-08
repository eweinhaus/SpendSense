#!/bin/bash

# Script to start multiple SpendSense instances on different ports
# Usage: ./start_multiple_instances.sh [worktree1] [worktree2] [worktree3]

# Default ports
PORT1=8000
PORT2=8001
PORT3=8002

# Default worktrees (can be overridden)
WORKTREE1=${1:-"/Users/user/Desktop/Github/SpendSense"}
WORKTREE2=${2:-"/Users/user/.cursor/worktrees/SpendSense/87UnV"}
WORKTREE3=${3:-"/Users/user/.cursor/worktrees/SpendSense/Ec8rF"}

echo "Starting SpendSense instances..."
echo ""
echo "Instance 1: $WORKTREE1 on port $PORT1"
echo "Instance 2: $WORKTREE2 on port $PORT2"
echo "Instance 3: $WORKTREE3 on port $PORT3"
echo ""

# Function to start an instance
start_instance() {
    local worktree=$1
    local port=$2
    local name=$3
    
    if [ ! -d "$worktree" ]; then
        echo "⚠️  Warning: $worktree does not exist, skipping..."
        return
    fi
    
    cd "$worktree" || return
    
    # Check if port is already in use
    if lsof -ti:$port > /dev/null 2>&1; then
        echo "⚠️  Port $port is already in use, killing existing process..."
        lsof -ti:$port | xargs kill -9 2>/dev/null
        sleep 1
    fi
    
    echo "🚀 Starting $name on port $port..."
    PYTHONPATH=src python3 -m uvicorn spendsense.app:app --reload --host 0.0.0.0 --port $port > "/tmp/spendsense_${port}.log" 2>&1 &
    echo $! > "/tmp/spendsense_${port}.pid"
    echo "   PID: $(cat /tmp/spendsense_${port}.pid)"
    echo "   Log: /tmp/spendsense_${port}.log"
    echo ""
}

# Start all instances
start_instance "$WORKTREE1" $PORT1 "Instance 1 (Main)"
start_instance "$WORKTREE2" $PORT2 "Instance 2"
start_instance "$WORKTREE3" $PORT3 "Instance 3"

sleep 3

echo "✅ All instances started!"
echo ""
echo "Access them at:"
echo "  Instance 1: http://localhost:$PORT1"
echo "  Instance 2: http://localhost:$PORT2"
echo "  Instance 3: http://localhost:$PORT3"
echo ""
echo "To stop all instances, run: ./stop_all_instances.sh"
echo "Or manually: kill \$(cat /tmp/spendsense_*.pid)"




