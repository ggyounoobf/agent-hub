#!/bin/bash

# Script to safely restart the chart MCP server to resolve stack overflow issues

echo "🔄 Restarting Chart MCP Server..."

# Find and kill existing chart server processes
echo "📡 Finding existing chart server processes..."
CHART_PIDS=$(pgrep -f "mcp-server-chart" || true)

if [ ! -z "$CHART_PIDS" ]; then
    echo "🛑 Stopping existing chart server processes: $CHART_PIDS"
    kill -TERM $CHART_PIDS 2>/dev/null || true
    sleep 3
    
    # Force kill if still running
    REMAINING_PIDS=$(pgrep -f "mcp-server-chart" || true)
    if [ ! -z "$REMAINING_PIDS" ]; then
        echo "🔨 Force killing remaining processes: $REMAINING_PIDS"
        kill -KILL $REMAINING_PIDS 2>/dev/null || true
    fi
fi

# Wait a moment for cleanup
sleep 2

# Check if port 1122 is still in use
if lsof -Pi :1122 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 1122 still in use, waiting for release..."
    sleep 5
fi

# Start the chart server with improved settings
echo "🚀 Starting chart MCP server..."

# Set Node.js memory and stack size limits
export NODE_OPTIONS="--max-old-space-size=2048 --stack-size=2048"

# Start the server in background with logging
nohup npx @antv/mcp-server-chart --transport streamable > chart_server.log 2>&1 &

# Wait for server to start
sleep 5

# Check if server is running
if pgrep -f "mcp-server-chart" > /dev/null; then
    echo "✅ Chart MCP server started successfully"
    echo "📋 Server PID: $(pgrep -f 'mcp-server-chart')"
    echo "🌐 Server URL: http://localhost:1122/mcp"
    
    # Test server health
    echo "🔍 Testing server health..."
    if curl -s http://localhost:1122/health > /dev/null 2>&1; then
        echo "✅ Server health check passed"
    else
        echo "⚠️  Server health check failed - server may still be starting"
    fi
else
    echo "❌ Failed to start chart MCP server"
    echo "📋 Last 10 lines of log:"
    tail -10 chart_server.log 2>/dev/null || echo "No log file found"
    exit 1
fi

echo "🎯 Chart MCP server restart complete"
