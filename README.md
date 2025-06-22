# Personal Finance Dashboard 💰

A comprehensive personal finance management application built with Flask, featuring intelligent transaction parsing, secure data encryption, and advanced analytics.

## 🌟 Features

### Core Functionality
- **Multi-Bank Statement Parsing**: Automatic extraction from PDF statements (Federal Bank, HDFC, and more)
- **Universal LLM Parser**: AI-powered transaction parsing with automatic categorization
- **Manual Transaction Entry**: Quick manual transaction input with intelligent categorization
- **Secure Data Storage**: Field-level encryption for sensitive transaction data
- **Real-time Analytics**: Interactive dashboards with charts and insights

### Advanced Features
- **Intelligent Categorization**: LLM-powered automatic transaction categorization
- **Account Management**: Multi-account support with account-specific analytics
- **Transaction Filtering**: Advanced filtering by date, category, account, and amount
- **Audit Logging**: Comprehensive audit trail for all transaction operations
- **Responsive Design**: Modern, mobile-friendly interface

### Security & Privacy
- **Field-Level Encryption**: Sensitive data encrypted using Fernet symmetric encryption
- **Audit Logging**: Complete audit trail for compliance and security
- **Environment-Based Configuration**: Secure configuration via environment variables
- **Data Validation**: Comprehensive input validation and sanitization

## 🏗️ Architecture

### System Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   Database      │
│   (Jinja2)      │◄──►│   (Flask)       │◄──►│   (SQLite)      │
│   Bootstrap 5   │    │   SQLAlchemy    │    │   Encrypted     │
│   Chart.js      │    │   Secure Trans. │    │   Fields        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │   LLM Services  │
                    │   (OpenAI/      │
                    │   Anthropic)    │
                    └─────────────────┘
```

### Key Components

#### 1. **Universal LLM Parser** (`parsers/universal_llm_parser.py`)
- **Primary parsing method**: Uses LLM to extract and categorize transactions
- **Fallback mechanism**: Falls back to traditional parsers if LLM fails
- **Automatic categorization**: Intelligent category assignment
- **Format validation**: Ensures consistent transaction format

#### 2. **Secure Transaction System** (`models/secure_transaction.py`)
- **Encryption**: Automatic encryption of sensitive fields
- **Audit logging**: Complete operation tracking
- **Backward compatibility**: Works with existing unencrypted data
- **User context**: User-specific access controls

#### 3. **LLM Service Layer** (`llm_services/llm_service.py`)
- **Multi-provider support**: OpenAI and Anthropic Claude
- **Timeout handling**: Optimized timeouts for different operations
- **Retry logic**: Exponential backoff for failed requests
- **Performance optimization**: Fast categorization (2-8 seconds avg)

#### 4. **Traditional Parsers** (`parsers/`)
- **Bank-specific parsers**: Specialized parsers for different banks
- **PDF processing**: Advanced PDF text extraction
- **Pattern matching**: Regex-based transaction extraction
- **Data normalization**: Consistent transaction format

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- SQLite 3
- Git

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd personal-finance-dashboard
```

2. **Set up virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Environment Configuration**
```bash
cp env.example .env
# Edit .env with your configuration
```

5. **Database Setup**
```bash
python init_db.py
```

6. **Run the application**
```bash
python app.py
```

Visit `http://localhost:5000` to access the dashboard.

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```bash
# Database Configuration
DATABASE_URL=sqlite:///finance.db
DB_ENCRYPTION_KEY=your-32-character-encryption-key

# LLM Configuration
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
ENABLE_LLM_PARSING=true

# Application Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key
DEBUG=true
```

### Key Configuration Options

- **`ENABLE_LLM_PARSING`**: Enable/disable LLM-powered parsing
- **`DB_ENCRYPTION_KEY`**: 32-character key for field-level encryption
- **LLM API Keys**: Required for intelligent parsing and categorization

## 📊 Usage

### Uploading Statements
1. Click "Upload Statement" on the dashboard
2. Select your bank and account type
3. Upload PDF/CSV/Excel file
4. Review extracted transactions
5. Confirm to save to database

### Manual Transactions
1. Click "Add Transaction" on the dashboard
2. Fill in transaction details
3. Select transaction type (Income/Expense)
4. Choose category or let AI categorize
5. Save transaction

### Analytics & Insights
- **Dashboard**: Overview of financial health
- **Transactions**: Detailed transaction history with filtering
- **Charts**: Visual analytics with Chart.js
- **Account Summary**: Per-account breakdown

## 🔧 Development

### Project Structure
```
personal-finance-dashboard/
├── app.py                 # Main Flask application
├── config.py             # Configuration management
├── services.py           # Business logic layer
├── init_db.py           # Database initialization
├── models/              # Database models
│   ├── models.py        # Core models
│   └── secure_transaction.py  # Encryption layer
├── parsers/             # Transaction parsers
│   ├── universal_llm_parser.py  # LLM parser
│   ├── federal_bank_parser.py   # Bank parsers
│   └── ...
├── llm_services/        # LLM integration
│   └── llm_service.py
├── utils/               # Utilities
│   └── encryption.py    # Encryption utilities
├── templates/           # Jinja2 templates
├── static/              # CSS, JS, images
├── tests/               # Test suite
├── migrations/          # Database migrations
└── scripts/             # Utility scripts
```

### Running Tests
```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_universal_parser.py

# Run with coverage
python -m pytest --cov=. tests/
```

### Adding New Bank Parsers
1. Create parser in `parsers/` directory
2. Implement standard interface
3. Add to universal parser mapping
4. Add tests in `tests/test_parsers.py`

## 🐳 Deployment

### Docker Deployment

1. **Build the image**
```bash
docker build -t finance-dashboard .
```

2. **Run with Docker Compose**
```bash
docker-compose up -d
```

### Production Configuration

1. **Set production environment variables**
```bash
FLASK_ENV=production
DEBUG=false
DB_ENCRYPTION_KEY=<secure-32-char-key>
```

2. **Use production database**
```bash
DATABASE_URL=postgresql://user:pass@host:port/dbname
```

3. **Configure reverse proxy** (nginx recommended)

### AWS Deployment
- ECS task definition available in `.aws/`
- Terraform configuration in `terraform/`
- GitHub Actions workflow for CI/CD

## 🔒 Security Features

### Data Encryption
- **Field-level encryption** for sensitive transaction data
- **Fernet symmetric encryption** with secure key derivation
- **Automatic encryption/decryption** transparent to application logic

### Audit Logging
- **Complete audit trail** for all transaction operations
- **User context tracking** with IP and user agent
- **Security event logging** for compliance

### Input Validation
- **Comprehensive validation** for all user inputs
- **SQL injection prevention** via SQLAlchemy ORM
- **XSS protection** via template escaping

## 🤖 LLM Integration

### Supported Providers
- **OpenAI GPT-4**: Primary LLM for parsing and categorization
- **Anthropic Claude**: Alternative LLM provider
- **Configurable timeouts**: Optimized for different operations

### Performance Optimizations
- **Smart timeout handling**: 15s for categorization, 60s for parsing
- **Retry logic**: Exponential backoff for failed requests
- **Fallback mechanisms**: Traditional parsers as backup

### Cost Optimization
- **Efficient prompts**: Optimized for minimal token usage
- **Caching**: Avoid redundant API calls
- **Selective usage**: Only for complex parsing tasks

## 📈 Performance

### Database Performance
- **Indexed queries**: Optimized database indexes
- **Connection pooling**: Efficient database connections
- **Query optimization**: Minimized N+1 queries

### Application Performance
- **Lazy loading**: Efficient data loading
- **Caching**: Strategic caching of expensive operations
- **Async processing**: Background processing for heavy tasks

## 🧪 Testing Strategy

### Test Coverage
- **Unit tests**: Individual component testing
- **Integration tests**: End-to-end workflow testing
- **Parser tests**: Comprehensive parser validation
- **Security tests**: Encryption and audit logging

### Test Data
- **Sample statements**: Test data for all supported banks
- **Edge cases**: Handling of malformed data
- **Performance tests**: Load testing for large datasets

## 🤝 Contributing

### Development Workflow
1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Make changes with tests
4. Ensure all tests pass
5. Submit pull request

### Code Standards
- **PEP 8**: Python code style
- **Type hints**: Use type annotations
- **Documentation**: Comprehensive docstrings
- **Testing**: Test all new features

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenAI** for GPT-4 API
- **Anthropic** for Claude API
- **Flask** community for excellent framework
- **Bootstrap** for responsive UI components

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Check existing documentation
- Review test cases for examples

---

**Built with ❤️ for better financial management**
