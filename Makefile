# Personal Finance Dashboard Makefile
# 
# This Makefile provides common operations for the personal finance app,
# including Docker operations, database management, and testing.

.PHONY: run stop clean test install debug help
.PHONY: docker-build docker-up docker-down docker-logs docker-shell docker-clean
.PHONY: db-init db-migrate db-upgrade db-reset
.PHONY: deploy-dev deploy-staging deploy-prod

# Default port for the web server
PORT ?= 5000
# Database URL for development
DATABASE_URL ?= sqlite:///personal_finance.db
# Environment
ENV ?= development

# =============================================================================
# Local Development Commands
# =============================================================================

# Run the web server locally
run:
	@echo "Starting the personal finance dashboard server on port $(PORT)..."
	FLASK_ENV=$(ENV) DATABASE_URL=$(DATABASE_URL) python app.py

# Run the server in debug mode
debug:
	@echo "Starting the personal finance dashboard server in debug mode on port $(PORT)..."
	FLASK_ENV=development FLASK_DEBUG=1 DATABASE_URL=$(DATABASE_URL) python app.py

# Stop the server (if running as a background process)
stop:
	@echo "Stopping the personal finance dashboard server..."
	-pkill -f "python app.py" || true

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

# =============================================================================
# Docker Commands
# =============================================================================

# Build Docker image
docker-build:
	@echo "Building Docker image..."
	docker build -t personal-finance .

# Start application with Docker Compose
docker-up:
	@echo "Starting application with Docker Compose..."
	docker-compose up --build -d

# Start application with Docker Compose (foreground)
docker-up-logs:
	@echo "Starting application with Docker Compose (with logs)..."
	docker-compose up --build

# Stop Docker containers
docker-down:
	@echo "Stopping Docker containers..."
	docker-compose down

# Stop Docker containers and remove volumes
docker-down-clean:
	@echo "Stopping Docker containers and removing volumes..."
	docker-compose down -v

# Stop Docker containers (alias for docker-down)
docker-stop:
	@echo "Stopping Docker containers (keeping data)..."
	docker-compose down

# Stop Docker containers and remove all data including volumes
docker-clean-all:
	@echo "Stopping Docker containers and removing all data..."
	docker-compose down -v
	docker volume prune -f
	@echo "All data has been removed!"

# View Docker logs
docker-logs:
	@echo "Showing Docker logs..."
	docker-compose logs -f

# Get a shell inside the app container
docker-shell:
	@echo "Opening shell in app container..."
	docker-compose exec app /bin/bash

# Get a shell inside the database container
docker-db-shell:
	@echo "Opening shell in database container..."
	docker-compose exec db psql -U financeuser -d personal_finance

# Clean up Docker containers, images, and volumes
docker-clean:
	@echo "Cleaning up Docker resources..."
	docker-compose down -v
	docker system prune -f

# Restart Docker containers
docker-restart: docker-down docker-up

# =============================================================================
# Database Commands
# =============================================================================

# Initialize database migrations
db-init:
	@echo "Initializing database migrations..."
	FLASK_APP=app.py flask db init

# Create a new migration
db-migrate:
	@echo "Creating new database migration..."
	FLASK_APP=app.py flask db migrate -m "$(MESSAGE)"

# Apply database migrations
db-upgrade:
	@echo "Applying database migrations..."
	FLASK_APP=app.py flask db upgrade

# Reset database (for development only)
db-reset:
	@echo "Resetting database..."
	@read -p "This will delete all data. Are you sure? (y/N) " confirm && \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		rm -f personal_finance.db; \
		FLASK_APP=app.py flask db upgrade; \
		echo "Database reset complete."; \
	else \
		echo "Database reset cancelled."; \
	fi

# =============================================================================
# Testing Commands
# =============================================================================

# Run all tests
test:
	@echo "Running tests..."
	python -m pytest tests/ -v

# Run tests with coverage
test-coverage:
	@echo "Running tests with coverage..."
	python -m pytest tests/ --cov=app --cov-report=html

# =============================================================================
# Deployment Commands
# =============================================================================

# Deploy to development environment
deploy-dev:
	@echo "Deploying to development environment..."
	./scripts/deploy.sh development

# Deploy to staging environment
deploy-staging:
	@echo "Deploying to staging environment..."
	./scripts/deploy.sh staging

# Deploy to production environment
deploy-prod:
	@echo "Deploying to production environment..."
	./scripts/deploy.sh production

# =============================================================================
# Utility Commands
# =============================================================================

# Clean up temporary and cache files
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@find . -type f -name "*.pyo" -delete
	@find . -name "*.backup" -delete
	@rm -rf .pytest_cache/
	@rm -rf htmlcov/
	@rm -rf .coverage
	@echo "Cleaned up cache files and temporary files"

# Show application status
status:
	@echo "Application Status:"
	@echo "==================="
	@if docker-compose ps | grep -q "personal-finance-dashboard-app"; then \
		echo "Docker Status: Running"; \
		docker-compose ps; \
	else \
		echo "Docker Status: Not running"; \
	fi

# Setup development environment
setup-dev:
	@echo "Setting up development environment..."
	@if [ ! -f ".env" ]; then \
		cp env.example .env; \
		echo "Created .env file from template"; \
	fi
	make install
	make db-upgrade
	@echo "Development environment setup complete!"

# Help command
help:
	@echo "Personal Finance Dashboard - Available Commands"
	@echo "=============================================="
	@echo ""
	@echo "Local Development:"
	@echo "  make run               - Start the Flask server locally"
	@echo "  make debug             - Start the server in debug mode"
	@echo "  make stop              - Stop the running server"
	@echo "  make install           - Install required dependencies"
	@echo "  make setup-dev         - Setup development environment"
	@echo ""
	@echo "Docker Commands:"
	@echo "  make docker-build      - Build Docker image"
	@echo "  make docker-up         - Start with Docker Compose (background)"
	@echo "  make docker-up-logs    - Start with Docker Compose (with logs)"
	@echo "  make docker-down       - Stop Docker containers (keep data)"
	@echo "  make docker-stop       - Stop Docker containers (keep data)"
	@echo "  make docker-down-clean - Stop containers and remove volumes"
	@echo "  make docker-clean-all  - Stop containers and remove ALL data"
	@echo "  make docker-logs       - View application logs"
	@echo "  make docker-shell      - Open shell in app container"
	@echo "  make docker-db-shell   - Open PostgreSQL shell"
	@echo "  make docker-clean      - Clean up Docker resources"
	@echo "  make docker-restart    - Restart Docker containers"
	@echo ""
	@echo "Database Commands:"
	@echo "  make db-init           - Initialize database migrations"
	@echo "  make db-migrate        - Create new migration (use MESSAGE='description')"
	@echo "  make db-upgrade        - Apply database migrations"
	@echo "  make db-reset          - Reset database (development only)"
	@echo ""
	@echo "Testing:"
	@echo "  make test              - Run all tests"
	@echo "  make test-coverage     - Run tests with coverage report"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-dev        - Deploy to development"
	@echo "  make deploy-staging    - Deploy to staging"
	@echo "  make deploy-prod       - Deploy to production"
	@echo ""
	@echo "Utilities:"
	@echo "  make clean             - Clean up cache and temporary files"
	@echo "  make status            - Show application status"
	@echo "  make help              - Show this help message"
	@echo ""
	@echo "Quick Start:"
	@echo "  make docker-up-logs    - Start everything with logs"
	@echo "  make docker-down       - Stop everything"
