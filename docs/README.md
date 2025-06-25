# Personal Finance Dashboard

A comprehensive personal finance management system that automatically extracts and categorizes transactions from bank statements using AI-powered document processing.

## 🚀 Features

- **AI-Powered PDF Processing**: Automatically extract transactions from bank statements using LLM (Large Language Model)
- **Multi-Bank Support**: Supports Federal Bank, HDFC Bank, and other major banks
- **Intelligent Categorization**: Automatic transaction categorization using AI
- **Secure Data Storage**: Field-level encryption for sensitive financial data
- **Real-time Dashboard**: Interactive dashboard with charts and analytics
- **Audit Logging**: Comprehensive audit trail for all operations
- **RESTful API**: Full API support for integration

## 📋 Table of Contents

- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (Bootstrap)   │◄──►│   (Flask)       │◄──►│   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   LLM Service   │
                       │   (Ollama)      │
                       └─────────────────┘
```

### Key Components

1. **Frontend**: Bootstrap-based responsive web interface
2. **Backend**: Flask application with RESTful API
3. **Database**: PostgreSQL with field-level encryption
4. **LLM Service**: Ollama with llama3.2:1b model for document processing
5. **PDF Processing**: Advanced text extraction and parsing
6. **Security**: Encryption, audit logging, and secure session management

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Ollama with llama3.2:1b model

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd personal-finance-dashboard-1
   ```

2. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your configuration
   ```

3. **Start the application**
   ```bash
   make up
   ```

4. **Access the application**
   - Dashboard: http://localhost:5001
   - Health Check: http://localhost:5001/health
   - Database: localhost:5433

### Using the Application

1. **Upload Bank Statement**: Click "Upload Statement" and select a PDF file
2. **Review Transactions**: Review extracted transactions before saving
3. **Confirm & Save**: Confirm transactions to save to database
4. **View Dashboard**: Monitor your finances through interactive charts

## 📁 Project Structure

```
personal-finance-dashboard-1/
├── app.py                          # Main Flask application
├── config.py                       # Application configuration
├── requirements.txt                # Python dependencies
├── docker-compose.yml              # Docker services configuration
├── Dockerfile                      # Application container
├── Makefile                        # Development commands
│
├── config/                         # Configuration modules
│   └── categories.py              # Transaction categories
│
├── docs/                          # Documentation
│   ├── README.md                  # This file
│   ├── TECHNICAL_DOCUMENTATION.md # Technical details
│   └── DEPLOYMENT_GUIDE.md        # Deployment instructions
│
├── llm_services/                  # LLM integration
│   ├── __init__.py
│   └── llm_service.py            # LLM service implementation
│
├── models/                        # Database models
│   ├── __init__.py
│   ├── models.py                 # SQLAlchemy models
│   └── secure_transaction.py     # Encrypted transaction model
│
├── parsers/                       # Document parsers
│   ├── __init__.py
│   ├── exceptions.py             # Custom exceptions
│   ├── universal_llm_parser.py   # AI-powered universal parser
│   ├── federal_bank_parser.py    # Federal Bank specific parser
│   └── hdfc_savings.py          # HDFC Bank specific parser
│
├── scripts/                       # Utility scripts
│   ├── start-dev.py              # Development server
│   ├── background_tasks.py       # Background job processing
│   ├── monitoring.py             # Application monitoring
│   └── monitoring_routes.py      # Monitoring endpoints
│
├── static/                        # Static assets
│   └── css/
│       └── style.css             # Application styles
│
├── templates/                     # Jinja2 templates
│   ├── base.html                 # Base template
│   ├── index.html                # Dashboard
│   ├── transactions.html         # Transaction list
│   └── review_upload.html        # Upload review
│
├── tests/                         # Test suite
│   ├── conftest.py               # Test configuration
│   ├── test_real_pdf_processing.py # PDF processing tests
│   └── test_*.py                 # Other test modules
│
├── utils/                         # Utility modules
│   ├── __init__.py
│   ├── encryption.py             # Encryption utilities
│   └── pdf_utils.py              # PDF processing utilities
│
├── migrations/                    # Database migrations
│   ├── alembic.ini               # Alembic configuration
│   ├── env.py                    # Migration environment
│   └── versions/                 # Migration versions
│
└── deployment/                    # Deployment configurations
    └── aws/                      # AWS deployment files
```

## ⚙️ Configuration

### Environment Variables

```bash
# Database Configuration
DATABASE_URL=postgresql://user:password@db:5432/finance_db
DB_HOST=db
DB_PORT=5432
DB_NAME=finance_db
DB_USER=finance_user
DB_PASSWORD=secure_password

# LLM Configuration
OLLAMA_BASE_URL=http://192.168.0.118:11434
LLM_MODEL=llama3.2:1b
LLM_ENDPOINT=http://192.168.0.118:11434

# Security
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# Application
FLASK_ENV=production
DEBUG=False
```

### Supported Banks

- **Federal Bank**: Savings and current account statements
- **HDFC Bank**: Savings, current, and credit card statements
- **Generic**: Universal parser for other banks

## 🔌 API Documentation

### Core Endpoints

#### Upload Statement
```http
POST /upload
Content-Type: multipart/form-data

Parameters:
- file: PDF file (required)
- account_type: savings|credit_card (required)
```

#### Get Pending Transactions
```http
GET /api/pending-transactions
Response: {
  "transactions": [...],
  "count": 10
}
```

#### Confirm Transactions
```http
POST /confirm-transactions
Content-Type: application/json

Body: {
  "transactions": [...]
}
```

#### Health Check
```http
GET /health
Response: {
  "status": "healthy",
  "timestamp": "2025-01-01T00:00:00Z"
}
```

## 🛠️ Development

### Development Commands

```bash
# Start development environment
make up

# View logs
make logs

# Stop services
make down

# Run tests
make test

# Clean up
make clean
```

### Adding New Bank Parser

1. Create parser in `parsers/` directory
2. Implement required methods
3. Register in `parsers/__init__.py`
4. Add tests in `tests/`

### LLM Integration

The system uses Ollama with llama3.2:1b model for document processing:

```python
from llm_services.llm_service import LLMService

llm = LLMService()
transactions = llm.parse_bank_statement(pdf_text, "Bank Name")
```

## 🧪 Testing

### Running Tests

```bash
# Run all tests
docker-compose exec app python3 -m pytest tests/

# Run specific test
docker-compose exec app python3 /app/tests/test_real_pdf_processing.py

# Run with coverage
docker-compose exec app python3 -m pytest tests/ --cov=.
```

### Test Structure

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end pipeline testing
- **Real PDF Tests**: Testing with actual bank statements
- **API Tests**: RESTful endpoint testing

## 🚀 Deployment

### Production Deployment

1. **AWS Deployment**
   ```bash
   cd deployment/aws
   ./deploy.sh
   ```

2. **Docker Production**
   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Manual Deployment**
   - Set up PostgreSQL database
   - Configure Ollama service
   - Deploy Flask application
   - Set up reverse proxy (nginx)

### Environment Setup

- **Development**: Local Docker containers
- **Staging**: AWS ECS with RDS
- **Production**: AWS ECS with Multi-AZ RDS

## 🔧 Troubleshooting

### Common Issues

#### LLM Timeout Errors
- **Cause**: Large PDF files or slow LLM processing
- **Solution**: Increase timeout values in `llm_service.py`
- **Prevention**: Use smaller PDF chunks

#### Database Connection Issues
- **Cause**: Database not ready or connection refused
- **Solution**: Check database health and connection string
- **Prevention**: Use proper health checks

#### PDF Processing Failures
- **Cause**: Corrupted PDF or unsupported format
- **Solution**: Validate PDF before processing
- **Prevention**: Add PDF format validation

### Debug Mode

```bash
# Enable debug logging
export FLASK_ENV=development
export DEBUG=True

# View detailed logs
make logs
```

### Performance Optimization

- **Database**: Use connection pooling and indexes
- **LLM**: Implement request caching and batch processing
- **Frontend**: Use CDN for static assets
- **API**: Implement rate limiting and pagination

## 📊 Monitoring

### Health Checks

- **Application**: `/health` endpoint
- **Database**: Connection and query performance
- **LLM Service**: Model availability and response time
- **System**: CPU, memory, and disk usage

### Metrics

- **Transaction Processing**: Success rate and processing time
- **API Performance**: Response time and error rate
- **User Activity**: Upload frequency and dashboard usage
- **System Health**: Resource utilization and error logs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with tests
4. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the troubleshooting guide
- Review the technical documentation 