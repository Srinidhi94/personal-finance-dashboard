# Technical Architecture Documentation

## System Overview

The Personal Finance Dashboard is a Flask-based web application designed for secure financial data management with intelligent transaction parsing capabilities.

## Core Architecture

### Application Stack
```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
├─────────────────────────────────────────────────────────────┤
│ Frontend: Jinja2 Templates + Bootstrap 5 + Chart.js        │
│ - Responsive UI with mobile-first design                   │
│ - Interactive charts and data visualization                 │
│ - AJAX-based dynamic content loading                       │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Application Layer                        │
├─────────────────────────────────────────────────────────────┤
│ Flask Application (app.py)                                 │
│ - Route handling and request processing                    │
│ - Session management and authentication                    │
│ - Template rendering and response generation               │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                     │
├─────────────────────────────────────────────────────────────┤
│ Services Layer (services.py)                              │
│ - TransactionService: CRUD operations                     │
│ - AccountService: Account management                       │
│ - CategoryService: Category management                     │
│ - UserService: User management                             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Security Layer                           │
├─────────────────────────────────────────────────────────────┤
│ SecureTransaction (models/secure_transaction.py)           │
│ - Field-level encryption/decryption                       │
│ - Audit logging for all operations                        │
│ - User context and access control                         │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Data Access Layer                        │
├─────────────────────────────────────────────────────────────┤
│ SQLAlchemy ORM (models/models.py)                         │
│ - Transaction, Account, Category, User models             │
│ - Database relationships and constraints                   │
│ - Migration management                                     │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Database Layer                           │
├─────────────────────────────────────────────────────────────┤
│ SQLite (Development) / PostgreSQL (Production)            │
│ - Encrypted sensitive fields                              │
│ - Indexed queries for performance                         │
│ - ACID compliance                                          │
└─────────────────────────────────────────────────────────────┘
```

### External Services Integration
```
┌─────────────────────────────────────────────────────────────┐
│                    LLM Services                             │
├─────────────────────────────────────────────────────────────┤
│ LLMService (llm_services/llm_service.py)                  │
│ - OpenAI GPT-4 integration                                │
│ - Anthropic Claude integration                            │
│ - Timeout and retry management                            │
│ - Cost optimization strategies                             │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Parsing Engine                           │
├─────────────────────────────────────────────────────────────┤
│ Universal Parser (parsers/universal_llm_parser.py)        │
│ - LLM-first parsing strategy                              │
│ - Fallback to traditional parsers                         │
│ - Automatic transaction categorization                    │
│ - Format validation and normalization                     │
└─────────────────────────────────────────────────────────────┘
```

## Database Schema

### Core Tables

#### Transactions Table
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL,
    description TEXT NOT NULL,
    amount NUMERIC(12,2) NOT NULL,
    category VARCHAR(50) NOT NULL DEFAULT 'Miscellaneous',
    subcategory VARCHAR(50),
    tags TEXT,  -- JSON field
    account_id INTEGER NOT NULL,
    is_debit BOOLEAN NOT NULL DEFAULT 1,
    transaction_type VARCHAR(20) NOT NULL DEFAULT 'manual',
    balance NUMERIC(12,2),
    reference_number VARCHAR(100),
    notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    -- Encryption fields
    encrypted_description TEXT,
    encrypted_amount TEXT,
    encryption_key_id VARCHAR(50),
    is_encrypted BOOLEAN DEFAULT 0,
    
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    UNIQUE(date, description, amount, account_id)
);
```

#### Accounts Table
```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    bank VARCHAR(50) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    account_number VARCHAR(50),
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(bank, account_type, account_number)
);
```

#### Categories Table
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(50) NOT NULL UNIQUE,
    type VARCHAR(20) NOT NULL,  -- 'income' or 'expense'
    description TEXT,
    is_active BOOLEAN DEFAULT 1,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### Audit Log Table
```sql
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action VARCHAR(100) NOT NULL,
    user_id INTEGER,
    resource_type VARCHAR(50),
    resource_id VARCHAR(50),
    details TEXT,  -- JSON field
    ip_address VARCHAR(45),
    user_agent TEXT,
    success BOOLEAN DEFAULT 1,
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_audit_action (action),
    INDEX idx_audit_resource (resource_type, resource_id),
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_created (created_at)
);
```

### Database Relationships
```
Users (1) ──── (M) Transactions
Accounts (1) ── (M) Transactions
Categories (1) ─ (M) Transactions
Users (1) ────── (M) AuditLogs
```

## Security Implementation

### Field-Level Encryption

#### Encryption Strategy
- **Sensitive fields encrypted**: `description` and `amount`
- **Metadata fields in plaintext**: `date`, `category`, `bank_name` for querying
- **Fernet symmetric encryption**: Industry-standard encryption
- **Key derivation**: PBKDF2 with SHA-256 for string-based keys

#### Encryption Flow
```
User Input → Validation → Encryption → Database Storage
Database Query ← Decryption ← Retrieval ← User Display
```

### Audit Logging
- **Complete audit trail** for all transaction operations
- **User context tracking** with IP and user agent
- **Security event logging** for compliance
- **Tamper-proof logs** with cryptographic integrity

## LLM Integration Architecture

### Universal Parser Strategy
```
PDF Upload → Text Extract → LLM Parser (Primary)
                                 ↓
                           Success? → No → Traditional Parser (Fallback)
                                 ↓ Yes
                           Categorization (LLM) → Validation → Database
```

### Performance Optimizations
- **Smart timeout handling**: 15s for categorization, 60s for parsing
- **Retry logic**: Exponential backoff for failed requests
- **Fallback mechanisms**: Traditional parsers as backup
- **Cost optimization**: Efficient prompts and selective usage

## Deployment Architecture

### Development Environment
```yaml
services:
  web:
    build: .
    ports: ["5000:5000"]
    environment:
      - FLASK_ENV=development
      - DATABASE_URL=sqlite:///dev.db
```

### Production Environment
- **Containerized deployment** with Docker
- **AWS ECS** for container orchestration
- **Terraform** for infrastructure as code
- **Encrypted secrets** via AWS Secrets Manager

## Security Features

### Data Encryption
- **Field-level encryption** for sensitive transaction data
- **Environment-based key management**
- **Backward compatibility** with unencrypted data

### Compliance
- **GDPR compliance**: Right to be forgotten
- **Financial compliance**: Complete audit trails
- **Security standards**: Encryption at rest and in transit

## Monitoring and Observability

### Application Metrics
- **Response times**: API endpoint performance
- **Error rates**: Application error tracking
- **Database performance**: Query execution times
- **LLM usage**: API call metrics and costs

### Security Monitoring
- **Audit log analysis**: Suspicious activity detection
- **Failed authentication**: Brute force detection
- **Data access patterns**: Unusual access monitoring
- **Encryption status**: Data encryption compliance

### Performance Monitoring
- **Database queries**: Slow query identification
- **Memory usage**: Application memory consumption
- **CPU utilization**: Resource usage optimization
- **Cache hit rates**: Caching effectiveness

## Scalability Considerations

### Horizontal Scaling
- **Stateless application**: Session data in database
- **Load balancing**: Multiple application instances
- **Database connection pooling**: Efficient resource usage

### Database Scaling
- **Read replicas**: Read operation distribution
- **Connection pooling**: Connection reuse
- **Query optimization**: Index usage and query tuning

### Caching Strategy
- **Application-level caching**: Frequently accessed data
- **Database query caching**: Expensive query results
- **Static asset caching**: CSS, JS, and image files

## Backup and Disaster Recovery

### Database Backup
- **Automated backups**: Daily encrypted backups
- **Point-in-time recovery**: Transaction log backups
- **Cross-region replication**: Geographic redundancy

### Application Recovery
- **Blue-green deployment**: Zero-downtime updates
- **Health checks**: Automatic failure detection
- **Rollback procedures**: Quick recovery mechanisms

## Compliance and Governance

### Data Privacy
- **GDPR compliance**: Right to be forgotten
- **Data minimization**: Only necessary data collection
- **Consent management**: User consent tracking

### Financial Compliance
- **Audit trails**: Complete transaction history
- **Data integrity**: Tamper-proof audit logs
- **Access controls**: Role-based permissions

### Security Standards
- **Encryption at rest**: Database field encryption
- **Encryption in transit**: HTTPS/TLS
- **Key management**: Secure key storage and rotation 