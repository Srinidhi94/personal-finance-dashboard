# Deployment Guide

## Overview

This guide covers deployment strategies for the Personal Finance Dashboard across different environments.

## Prerequisites

### System Requirements
- **Python**: 3.8 or higher
- **Database**: SQLite (dev) / PostgreSQL (prod)
- **Memory**: Minimum 512MB RAM

### Required Services
- **LLM Provider**: OpenAI or Anthropic API access
- **Container Runtime**: Docker (for containerized deployment)

## Environment Configuration

Create a `.env` file with the following configuration:

```bash
# Application Configuration
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DEBUG=true

# Database Configuration
DATABASE_URL=sqlite:///finance.db
DB_ENCRYPTION_KEY=your-32-character-encryption-key

# LLM Configuration
OPENAI_API_KEY=your-openai-api-key
ANTHROPIC_API_KEY=your-anthropic-api-key
ENABLE_LLM_PARSING=true
```

## Development Deployment

### Local Setup

1. **Clone and Setup**
```bash
git clone <repository-url>
cd personal-finance-dashboard
python -m venv venv
source venv/bin/activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Environment**
```bash
cp env.example .env
# Edit .env with your configuration
```

4. **Initialize Database**
```bash
python init_db.py
```

5. **Run Application**
```bash
python app.py
```

Access at `http://localhost:5000`

## Production Deployment

### Docker Deployment

```bash
docker-compose up --build
```

## Security Checklist

- [ ] Environment variables secured
- [ ] Database encryption enabled
- [ ] HTTPS/TLS configured
- [ ] Secrets stored securely

## Maintenance

### Daily Tasks
- Monitor application logs
- Check system metrics
- Verify backup completion

### Weekly Tasks
- Review security alerts
- Update dependencies
- Performance analysis
