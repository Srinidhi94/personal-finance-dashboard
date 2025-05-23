# Expense Tracker Makefile
# 
# This Makefile provides common operations for the expense tracker app,
# including server management, database cleanup, and testing.

.PHONY: run stop clean test test-pipeline test-pipeline-clean test-hdfc backup restore install debug parse reset-db help

# Default port for the web server
PORT ?= 5000
# Default database file
DB_FILE = data/transactions.json
# Backup directory
BACKUP_DIR = data/backups

# Run the web server
run:
	@echo "Starting the personal finance dashboard server on port $(PORT)..."
	python app.py --port $(PORT)

# Run the server in debug mode
debug:
	@echo "Starting the personal finance dashboard server in debug mode on port $(PORT)..."
	FLASK_ENV=development FLASK_DEBUG=1 python app.py --port $(PORT)

# Stop the server (if running as a background process)
stop:
	@echo "Stopping the personal finance dashboard server..."
	-pkill -f "python app.py" || true

# Clean up temporary and cache files
clean:
	@echo "Cleaning up..."
	@find . -type d -name "__pycache__" -exec rm -rf {} +
	@find . -type f -name "*.pyc" -delete
	@rm -f pipeline_test_results.json
	@echo "Cleaned up __pycache__ directories, .pyc files, and test results"

# Reset transactions database
reset-db:
	@echo "Resetting transactions database..."
	@if [ -f $(DB_FILE) ]; then \
		mkdir -p $(BACKUP_DIR); \
		cp $(DB_FILE) $(BACKUP_DIR)/transactions_backup_$$(date +%Y%m%d_%H%M%S).json; \
		echo "[]" > $(DB_FILE); \
		echo "Transactions have been reset. Backup created."; \
	else \
		echo "[]" > $(DB_FILE); \
		echo "Transaction database created."; \
	fi

# Create a backup of the database
backup:
	@echo "Creating a backup of the transaction database..."
	@if [ -f $(DB_FILE) ]; then \
		mkdir -p $(BACKUP_DIR); \
		cp $(DB_FILE) $(BACKUP_DIR)/transactions_backup_$$(date +%Y%m%d_%H%M%S).json; \
		echo "Backup created in $(BACKUP_DIR)"; \
	else \
		echo "Transaction database not found."; \
	fi

# Restore from the latest backup
restore:
	@echo "Restoring transaction database from the latest backup..."
	@LATEST_BACKUP=$$(ls -t $(BACKUP_DIR)/transactions_backup_*.json 2>/dev/null | head -1); \
	if [ -n "$$LATEST_BACKUP" ]; then \
		cp $$LATEST_BACKUP $(DB_FILE); \
		echo "Restored from $$LATEST_BACKUP"; \
	else \
		echo "No backup files found in $(BACKUP_DIR)"; \
	fi

# Run all tests
test:
	@echo "Running tests..."
	python -m pytest tests/

# Test the full pipeline
test-pipeline:
	@echo "Testing the full parsing and categorization pipeline..."
	python tests/pipeline_test.py

# Test the full pipeline and clean up test results
test-pipeline-clean:
	@echo "Testing the full parsing and categorization pipeline (with cleanup)..."
	python tests/pipeline_test.py --clean

# Test the HDFC parser
test-hdfc:
	@echo "Testing bank statement parser..."
	python tests/test_hdfc_parser.py uploads/Statement_Example.pdf --verbose

# Parse a file and update the database
parse:
	@if [ -z "$(FILE)" ]; then \
		echo "Error: Please specify a file to parse with FILE=path/to/file.pdf"; \
		exit 1; \
	fi
	@echo "Parsing $(FILE) and updating database..."
	python tests/test_hdfc_parser.py $(FILE) --update-db

# Install dependencies
install:
	@echo "Installing dependencies..."
	pip install -r requirements.txt

# Help command
help:
	@echo "Available commands:"
	@echo "  make run         - Start the Flask server on port $(PORT)"
	@echo "  make debug       - Start the server in debug mode"
	@echo "  make stop        - Stop the running server"
	@echo "  make clean       - Clean up cache files"
	@echo "  make reset-db    - Reset the transactions database (with backup)"
	@echo "  make backup      - Create a backup of the transactions database"
	@echo "  make restore     - Restore from the latest backup"
	@echo "  make test        - Run all tests"
	@echo "  make test-pipeline - Test the full parsing and categorization pipeline"
	@echo "  make test-pipeline-clean - Test the pipeline and remove result files"
	@echo "  make test-hdfc   - Test the bank statement parser with a sample statement"
	@echo "  make parse FILE=path/to/file.pdf - Parse a bank statement and update the database"
	@echo "  make install     - Install required dependencies"
	@echo "  make help        - Show this help message"
