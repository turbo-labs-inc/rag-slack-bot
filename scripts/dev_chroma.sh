#!/bin/bash

# Development ChromaDB management script

case "$1" in
    start)
        echo "🚀 Starting development ChromaDB..."
        docker compose -f ../docker-compose.dev.yml up -d chromadb
        echo "⏳ Waiting for ChromaDB to be ready..."
        sleep 5
        echo "✅ ChromaDB running at http://localhost:8000"
        echo "🔍 Health check:"
        curl -s http://localhost:8000/api/v1/heartbeat | jq '.' || echo "Health check failed"
        ;;
    stop)
        echo "🛑 Stopping development ChromaDB..."
        docker compose -f ../docker-compose.dev.yml down
        echo "✅ ChromaDB stopped"
        ;;
    restart)
        echo "🔄 Restarting development ChromaDB (clean slate)..."
        docker compose -f ../docker-compose.dev.yml down
        sleep 2
        docker compose -f ../docker-compose.dev.yml up -d chromadb
        echo "⏳ Waiting for ChromaDB to be ready..."
        sleep 5
        echo "✅ ChromaDB restarted with clean database"
        ;;
    status)
        echo "📊 ChromaDB status:"
        docker compose -f ../docker-compose.dev.yml ps
        echo ""
        echo "🔍 Health check:"
        curl -s http://localhost:8000/api/v1/heartbeat | jq '.' || echo "ChromaDB not responding"
        ;;
    logs)
        echo "📋 ChromaDB logs:"
        docker compose -f ../docker-compose.dev.yml logs -f chromadb
        ;;
    clean)
        echo "🧹 Cleaning up ChromaDB containers and images..."
        docker compose -f ../docker-compose.dev.yml down
        docker system prune -f
        echo "✅ Cleanup complete"
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs|clean}"
        echo ""
        echo "Commands:"
        echo "  start   - Start ChromaDB development instance"
        echo "  stop    - Stop ChromaDB"
        echo "  restart - Restart with clean database (ephemeral)"
        echo "  status  - Show container status and health"
        echo "  logs    - Show ChromaDB logs"
        echo "  clean   - Stop and clean up containers"
        echo ""
        echo "ChromaDB will be available at: http://localhost:8000"
        exit 1
        ;;
esac