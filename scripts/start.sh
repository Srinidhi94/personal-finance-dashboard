#!/bin/bash

# Personal Finance App Development Startup Script
set -e

echo "🚀 Starting Personal Finance App for Development..."

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check dependencies
echo "📋 Checking dependencies..."

if ! command_exists docker; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command_exists docker-compose; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ All dependencies are installed."

# Check if we should use existing data or start fresh
if [ "$1" = "--fresh" ]; then
    echo "🔄 Starting with fresh database..."
    docker-compose down -v
elif [ "$1" = "--clean" ]; then
    echo "🧹 Cleaning up containers and starting fresh..."
    docker-compose down -v
    docker system prune -f
fi

# Create necessary directories
echo "📂 Creating necessary directories..."
mkdir -p uploads logs data
touch uploads/.gitkeep logs/.gitkeep

# Copy environment file if it doesn't exist
if [ ! -f ".env" ]; then
    if [ -f "env.example" ]; then
        echo "📝 Creating .env file from example..."
        cp env.example .env
        echo "⚠️  Please edit .env file with your configuration before proceeding."
        echo "   Database will use default Docker Compose settings for development."
    fi
fi

# Start the application
echo "🐳 Starting Docker containers..."
docker-compose up --build

echo "🎉 Application should be running at http://localhost:5000" 