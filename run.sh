#!/bin/bash

# Simple script to build and run the apartment tracker

set -e

case "$1" in
    build)
        echo "🔨 Building apartment tracker..."
        docker-compose build
        echo "✅ Build complete!"
        ;;
    run)
        echo "🚀 Starting apartment tracker..."
        # Stop any existing containers first
        docker-compose down 2>/dev/null || true
        docker-compose up -d
        echo "✅ Apartment tracker started!"
        echo "📋 View logs: ./run.sh logs"
        ;;
    logs)
        echo "📋 Showing logs (Ctrl+C to exit)..."
        docker-compose logs -f
        ;;
    stop)
        echo "🛑 Stopping apartment tracker..."
        docker-compose down
        echo "✅ Stopped!"
        ;;
    restart)
        echo "🔄 Restarting apartment tracker..."
        docker-compose down
        docker-compose up -d
        echo "✅ Restarted!"
        ;;
    clean)
        echo "🧹 Cleaning up containers..."
        docker-compose down
        docker system prune -f
        echo "✅ Cleaned up!"
        ;;
    *)
        echo "Apartment Tracker - Simple Docker Setup"
        echo ""
        echo "Usage: ./run.sh <command>"
        echo ""
        echo "Commands:"
        echo "  build    Build the Docker image"
        echo "  run      Start the apartment tracker"
        echo "  logs     Show application logs"
        echo "  stop     Stop the apartment tracker"
        echo "  restart  Restart the apartment tracker"
        echo "  clean    Clean up containers and images"
        echo ""
        echo "Quick start:"
        echo "  ./run.sh build"
        echo "  ./run.sh run"
        ;;
esac 