# Personal Finance Dashboard Makefile
# Simplified version with essential Docker commands only

.PHONY: help build up down logs shell test clean reset status
.DEFAULT_GOAL := help

# =============================================================================
# Essential Commands
# =============================================================================

## Build all Docker containers
build:
	@echo "🔨 Building Docker containers..."
	docker-compose build --no-cache
	@echo "✅ Build complete"

## Start the application stack
up:
	@echo "🚀 Starting application stack..."
	docker-compose up -d
	@echo "✅ Application started"
	@echo "   - Database: http://localhost:5433"
	@echo "   - Application: http://localhost:8080"
	@echo "   - Health check: http://localhost:8080/health"

## Stop the application stack
down:
	@echo "🛑 Stopping application stack..."
	docker-compose down
	@echo "✅ Application stopped"

## View application logs
logs:
	@echo "📋 Showing application logs..."
	docker-compose logs -f

## Access application container shell
shell:
	@echo "🐚 Opening shell in application container..."
	docker-compose exec app /bin/bash

## Run the complete test suite
test:
	@echo "🧪 Running test suite..."
	docker-compose exec app python -m pytest tests/ -v
	@echo "✅ Tests complete"

## Clean up containers and volumes
clean:
	@echo "🧹 Cleaning up containers and volumes..."
	docker-compose down -v
	docker system prune -f
	@echo "✅ Cleanup complete"

## Complete environment reset
reset: clean build up
	@echo "🔄 Environment reset complete"

# =============================================================================
# Utility Commands
# =============================================================================

## Check application status
status:
	@echo "📊 Application Status"
	@echo "===================="
	@docker-compose ps
	@echo ""
	@echo "🔍 Health Checks:"
	@curl -s http://localhost:8080/health 2>/dev/null || echo "❌ Application not responding"
	@curl -s http://localhost:11434/api/version 2>/dev/null || echo "❌ Ollama not responding"

## Start Ollama service (host system)
ollama-start:
	@echo "🤖 Starting Ollama service..."
	@if pgrep -f "ollama serve" > /dev/null; then \
		echo "✅ Ollama is already running"; \
	else \
		echo "Starting Ollama in background..."; \
		OLLAMA_HOST=0.0.0.0:11434 nohup ollama serve > /tmp/ollama.log 2>&1 & \
		sleep 3; \
		if pgrep -f "ollama serve" > /dev/null; then \
			echo "✅ Ollama started successfully"; \
		else \
			echo "❌ Failed to start Ollama"; \
			cat /tmp/ollama.log; \
		fi \
	fi

## Stop Ollama service
ollama-stop:
	@echo "🛑 Stopping Ollama service..."
	@if pgrep -f "ollama serve" > /dev/null; then \
		pkill -f "ollama serve"; \
		echo "✅ Ollama stopped"; \
	else \
		echo "Ollama is not running"; \
	fi

## Pull required LLM models
models:
	@echo "📥 Pulling required LLM models..."
	@if ! pgrep -f "ollama serve" > /dev/null; then \
		echo "❌ Ollama is not running. Please start it first with: make ollama-start"; \
		exit 1; \
	fi
	ollama pull llama3.2:3b
	@echo "✅ Models ready"

## Database shell access
db-shell:
	@echo "🗄️  Opening database shell..."
	docker-compose exec db psql -U financeuser -d personal_finance

## Full setup for new development environment
setup: ollama-start models build up
	@echo "🎉 Development environment setup complete!"
	@echo ""
	@echo "🔗 Quick Links:"
	@echo "   - Application: http://localhost:8080"
	@echo "   - Database: localhost:5433"
	@echo "   - Ollama API: http://localhost:11434"
	@echo ""
	@echo "📝 Next steps:"
	@echo "   - Upload a PDF statement to test LLM processing"
	@echo "   - Check logs with: make logs"
	@echo "   - Access shell with: make shell"

## Show this help message
help:
	@echo "Personal Finance Dashboard - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "🚀 Quick Start:"
	@echo "  make setup             - Complete development setup"
	@echo "  make up                - Start the application"
	@echo "  make down              - Stop the application"
	@echo ""
	@echo "🔧 Development:"
	@echo "  make build             - Build Docker containers"
	@echo "  make logs              - View application logs"
	@echo "  make shell             - Access application shell"
	@echo "  make test              - Run test suite"
	@echo ""
	@echo "🤖 LLM Management:"
	@echo "  make ollama-start      - Start Ollama service"
	@echo "  make ollama-stop       - Stop Ollama service"
	@echo "  make models            - Pull required LLM models"
	@echo ""
	@echo "🗄️  Database:"
	@echo "  make db-shell          - Access database shell"
	@echo ""
	@echo "🧹 Maintenance:"
	@echo "  make clean             - Clean containers and volumes"
	@echo "  make reset             - Complete environment reset"
	@echo "  make status            - Check application status"
