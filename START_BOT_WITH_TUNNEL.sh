#!/bin/bash

# Start Bot with Cloudflare Tunnel
# This script runs both the bot and tunnel in the same terminal

set -e

echo "🚀 Starting Captain Spire Bot with Cloudflare Tunnel..."
echo "=================================================="

# Check if cloudflared is installed
if ! command -v cloudflared &> /dev/null; then
    echo "❌ cloudflared is not installed. Please install it first:"
    echo "   brew install cloudflared"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "📦 Creating virtual environment..."
    uv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies
echo "📚 Installing dependencies..."
uv pip install -e .

# Function to cleanup on exit
cleanup() {
    echo -e "\n🛑 Shutting down..."
    # Kill all child processes
    kill $(jobs -p) 2>/dev/null || true
    exit 0
}

# Set up trap for cleanup on script exit
trap cleanup EXIT INT TERM

# Start Cloudflare tunnel in background
echo "🌐 Starting Cloudflare tunnel..."
cloudflared tunnel --config cloudflared-config.yml run &
TUNNEL_PID=$!

# Wait for tunnel to be ready
echo "⏳ Waiting for tunnel to connect..."
sleep 5

# Check if tunnel is running
if ! kill -0 $TUNNEL_PID 2>/dev/null; then
    echo "❌ Failed to start Cloudflare tunnel"
    exit 1
fi

echo "✅ Tunnel connected at https://bot.capspire-training.com"
echo ""

# Start the bot (in foreground)
echo "🤖 Starting bot application..."
echo "=================================================="
echo ""
python -m app.main

# This line will only be reached if the bot exits
wait