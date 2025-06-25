# Personal Finance Dashboard - Production Deployment Guide

## Overview

This guide provides step-by-step instructions for deploying the Personal Finance Dashboard to production environments, including AWS EC2, local server, or other cloud platforms.

## 🚀 Quick Start (AWS EC2)

### Option 1: CloudFormation (Recommended)

```bash
# Clone the repository
git clone <your-repo-url>
cd personal-finance-dashboard

# Deploy using CloudFormation
aws cloudformation create-stack \
  --stack-name finance-dashboard \
  --template-body file://deployment/aws/cloudformation-template.yaml \
  --parameters ParameterKey=KeyPairName,ParameterValue=your-key-pair \
  --capabilities CAPABILITY_IAM

# Wait for deployment to complete
aws cloudformation wait stack-create-complete --stack-name finance-dashboard

# Get the application URL
aws cloudformation describe-stacks \
  --stack-name finance-dashboard \
  --query 'Stacks[0].Outputs[?OutputKey==`ApplicationURL`].OutputValue' \
  --output text
```

### Option 2: Manual EC2 Deployment

```bash
# Launch EC2 instance with user data script
aws ec2 run-instances \
  --image-id ami-0c02fb55956c7d316 \
  --instance-type t3.medium \
  --key-name your-key-pair \
  --security-group-ids sg-xxxxxxxxx \
  --user-data file://deployment/aws/user-data.sh

# SSH to instance and complete setup
ssh -i your-key.pem ubuntu@your-ec2-ip
cd /opt/finance-dashboard
git clone <your-repo-url> .
sudo ./deployment/aws/deploy.sh
```

## 🛠️ Local Development Setup

### Prerequisites

- Python 3.10+
- Docker and Docker Compose
- Ollama (for AI features)

### Setup Steps

```bash
# Clone and setup
git clone <your-repo-url>
cd personal-finance-dashboard

# Install dependencies
pip install -r requirements.txt

# Setup environment
cp .env.example .env
# Edit .env with your configuration

# Start Ollama (if not using Docker)
make ollama-start

# Run with full functionality
make run-with-ollama

# Or run with Docker
make docker-restart
```

## 🔧 Configuration

### Required Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:port/db
DB_ENCRYPTION_KEY=your-32-character-encryption-key

# Security
SECRET_KEY=your-secret-key
FLASK_ENV=production

# AI/LLM
OLLAMA_BASE_URL=http://localhost:11434

# Monitoring
ENABLE_MONITORING=true
LOG_LEVEL=INFO

# Backup (AWS only)
BACKUP_ENABLED=true
BACKUP_S3_BUCKET=your-backup-bucket
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### Database Setup

#### PostgreSQL (Production)

```bash
# Install PostgreSQL
sudo apt install postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql
CREATE DATABASE finance_db;
CREATE USER finance_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE finance_db TO finance_user;
\q

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://finance_user:your_password@localhost:5432/finance_db
```

#### SQLite (Development)

```bash
# SQLite is used by default for development
DATABASE_URL=sqlite:///finance.db
```

## 🐳 Docker Deployment

### Production Docker Compose

```bash
# Use production configuration
cp deployment/aws/docker-compose.prod.yml docker-compose.yml

# Start services
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f app
```

### Services Included

- **Flask Application**: Main web server
- **PostgreSQL**: Production database
- **Nginx**: Reverse proxy with SSL
- **Redis**: Caching (optional)

## 🔒 Security Configuration

### SSL/TLS Setup

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Firewall Configuration

```bash
# Configure UFW
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable

# For development (local Ollama)
sudo ufw allow from 127.0.0.1 to any port 11434
```

### Database Security

- Use strong passwords
- Enable SSL connections
- Regular backups
- Access control (whitelist IPs)

## 📊 Monitoring and Logging

### Health Checks

```bash
# Application health
curl http://localhost/health

# Detailed health check
curl http://localhost/health/detailed

# Database connectivity
curl http://localhost/health/db
```

### Log Management

```bash
# Application logs
docker-compose logs -f app

# Database logs
docker-compose logs -f db

# System logs
sudo journalctl -u docker -f

# Log rotation (configured automatically)
cat /etc/logrotate.d/finance-dashboard
```

### Monitoring Endpoints

- `/health` - Basic health check
- `/health/detailed` - Comprehensive system status
- `/api/dashboard/summary` - Application metrics

## 🔄 Backup and Recovery

### Automated Backups

```bash
# Database backup (runs daily at 2 AM)
/opt/finance-dashboard/backup.sh

# Manual backup
docker-compose exec db pg_dump -U finance_user finance_db > backup.sql
```

### Restore Process

```bash
# Stop application
docker-compose down

# Restore database
docker-compose up -d db
docker-compose exec -T db psql -U finance_user finance_db < backup.sql

# Start application
docker-compose up -d
```

## 🚀 Performance Optimization

### Database Optimization

```sql
-- Create indexes for better performance
CREATE INDEX idx_transactions_date ON transactions(date);
CREATE INDEX idx_transactions_account ON transactions(account_id);
CREATE INDEX idx_audit_logs_trace ON audit_logs(trace_id);
```

### Application Optimization

- Enable Redis caching
- Use CDN for static files
- Optimize database queries
- Monitor memory usage

### Infrastructure Scaling

- Use Application Load Balancer
- Deploy multiple app instances
- Database read replicas
- Auto Scaling Groups

## 🧪 Testing

### Run Tests

```bash
# Unit tests
python -m pytest tests/ -v

# Integration tests
python -m pytest tests/test_comprehensive_integration.py -v

# Load testing
# Install: pip install locust
locust -f tests/load_test.py --host=http://localhost
```

### Test Coverage

```bash
# Generate coverage report
pip install pytest-cov
python -m pytest --cov=. --cov-report=html
open htmlcov/index.html
```

## 🔧 Troubleshooting

### Common Issues

#### Application Won't Start

```bash
# Check logs
docker-compose logs app

# Verify environment variables
docker-compose config

# Check database connection
docker-compose exec app python -c "from app import db; db.create_all()"
```

#### Database Connection Issues

```bash
# Check database status
docker-compose exec db pg_isready

# Reset database
docker-compose down -v
docker-compose up -d
```

#### Ollama Issues

```bash
# Check Ollama status
curl http://localhost:11434/api/tags

# Restart Ollama
sudo systemctl restart ollama

# Pull models
ollama pull llama2
```

#### SSL Certificate Issues

```bash
# Check certificate status
sudo certbot certificates

# Renew certificate
sudo certbot renew

# Test SSL configuration
curl -I https://yourdomain.com
```

### Performance Issues

#### High Memory Usage

```bash
# Monitor memory
docker stats

# Adjust container limits
# Edit docker-compose.yml memory limits

# Optimize database
docker-compose exec db psql -U finance_user -c "VACUUM ANALYZE;"
```

#### Slow Response Times

```bash
# Check application logs
docker-compose logs app | grep -i slow

# Monitor database queries
# Enable PostgreSQL query logging

# Check Ollama model loading
curl -s http://localhost:11434/api/ps
```

## 📋 Maintenance

### Regular Tasks

#### Daily
- Monitor application health
- Check error logs
- Verify backup completion

#### Weekly
- Update security patches
- Review performance metrics
- Clean up old logs

#### Monthly
- Update dependencies
- Review and optimize database
- Security audit

### Update Process

```bash
# Backup current version
./backup.sh

# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt

# Run migrations
flask db upgrade

# Restart application
docker-compose restart app

# Verify deployment
curl http://localhost/health
```

## 🆘 Support

### Getting Help

1. Check this documentation
2. Review application logs
3. Check GitHub issues
4. Contact support team

### Useful Commands

```bash
# Quick health check
make health-check

# View all logs
make logs

# Restart services
make restart

# Full system status
make status
```

## 📝 Additional Resources

- [Technical Documentation](TECHNICAL_DOCUMENTATION.md)
- [API Documentation](docs/api/)
- [Development Guide](docs/development/)
- [Security Best Practices](docs/security/)

---

**Note**: This deployment guide assumes you have basic knowledge of Linux system administration, Docker, and cloud platforms. For production deployments, consider consulting with a DevOps engineer or system administrator. 