#!/bin/bash
# 🚀 START THE RAG SLACK BOT

# Check for --tunnel flag
USE_TUNNEL=false
if [[ "$1" == "--tunnel" ]]; then
    USE_TUNNEL=true
fi

echo "=================================================="
echo "🤖 STARTING RAG SLACK BOT"
if [ "$USE_TUNNEL" = true ]; then
    echo "🌐 WITH CLOUDFLARE TUNNEL"
fi
echo "=================================================="

# 1. Ensure ChromaDB is running
echo "1️⃣ Starting ChromaDB..."
docker-compose -f docker-compose.local.yml up -d

# Wait for ChromaDB
sleep 3

# 2. Activate Python environment
echo "2️⃣ Activating Python environment..."
source .venv/bin/activate

# 3. Start Cloudflare tunnel if requested
if [ "$USE_TUNNEL" = true ]; then
    # Check if cloudflared is installed
    if ! command -v cloudflared &> /dev/null; then
        echo "❌ cloudflared is not installed. Please install it first:"
        echo "   brew install cloudflared"
        exit 1
    fi
    
    echo "3️⃣ Starting Cloudflare tunnel..."
    cloudflared tunnel --config cloudflared-config.yml run &
    TUNNEL_PID=$!
    
    # Wait for tunnel to be ready
    sleep 5
    
    # Check if tunnel is running
    if ! kill -0 $TUNNEL_PID 2>/dev/null; then
        echo "❌ Failed to start Cloudflare tunnel"
        exit 1
    fi
    
    echo "✅ Tunnel connected at https://bot.capspire-training.com"
    
    # Set up cleanup trap
    cleanup() {
        echo -e "\n🛑 Shutting down tunnel..."
        kill $TUNNEL_PID 2>/dev/null || true
        exit 0
    }
    trap cleanup EXIT INT TERM
fi

# 4. Start the bot
echo "4️⃣ Starting bot application..."
echo "=================================================="
echo "✅ Bot is starting..."
echo "📊 Indexed documents: 1,117"
echo "🧩 Total chunks: 17,074"
echo "🤖 Using: Qwen 2.5 32B"
echo ""
if [ "$USE_TUNNEL" = true ]; then
    echo "🌐 Teams webhook: https://bot.capspire-training.com/api/teams/messages"
fi
echo "Go to Slack/Teams and start asking questions!"
echo "Press Ctrl+C to stop the bot"
echo "=================================================="

python -m app.main