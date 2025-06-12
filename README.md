# Personal Finance Dashboard 💰

A modern, production-ready personal finance management application built with Flask, PostgreSQL, and deployed on AWS.

## 🌟 Features

- **Manual Transaction Entry**: Easy-to-use interface for adding income and expenses
- **Smart Categorization**: Automatic transaction categorization with machine learning
- **Interactive Dashboard**: Beautiful charts and analytics with Chart.js
- **Multi-Account Support**: Manage multiple bank accounts and credit cards
- **Responsive Design**: Works perfectly on desktop and mobile devices
- **Real-time Updates**: Live dashboard updates without page refreshes
- **Data Export**: Export transactions to CSV/Excel
- **Cloud-Ready**: Containerized and ready for AWS deployment

## 🏗️ Architecture

### Technology Stack

- **Backend**: Flask 3.1.1 with SQLAlchemy ORM
- **Database**: PostgreSQL (AWS RDS in production)
- **Frontend**: Bootstrap 5 + Chart.js + Vanilla JavaScript
- **Containerization**: Docker with multi-stage builds
- **Cloud Platform**: AWS (ECS Fargate + RDS + ALB)
- **Infrastructure as Code**: Terraform
- **CI/CD**: GitHub Actions

### System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Application    │    │   Load Balancer  │    │   ECS Fargate   │
│  Load Balancer  │◄──►│      (ALB)       │◄──►│    Cluster      │
│     (ALB)       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
                                                         ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│    ECR          │    │   CloudWatch     │    │   RDS           │
│  Container      │    │     Logs         │    │  PostgreSQL     │
│  Registry       │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 🚀 Quick Start

### Local Development

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd personal-finance-dashboard
   ```

2. **Run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - Open http://localhost:5000
   - Start adding transactions using the floating + button

### Manual Setup (Alternative)

1. **Set up Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements_new.txt
   ```

2. **Set up PostgreSQL database**
   ```bash
   # Install PostgreSQL locally or use Docker
   docker run --name postgres-finance -e POSTGRES_PASSWORD=password -p 5432:5432 -d postgres:15
   ```

3. **Configure environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your database credentials
   ```

4. **Run the application**
   ```bash
   python app_new.py
   ```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `FLASK_ENV` | Environment (development/production) | No | development |
| `SECRET_KEY` | Flask secret key | Yes | - |
| `DATABASE_URL` | PostgreSQL connection string | Yes | - |
| `DB_USER` | Database username | No | postgres |
| `DB_PASSWORD` | Database password | Yes | - |
| `DB_HOST` | Database host | No | localhost |
| `DB_PORT` | Database port | No | 5432 |
| `DB_NAME` | Database name | No | personal_finance |

### Database Migration

The application uses Flask-Migrate for database schema management:

```bash
# Initialize migration repository
flask db init

# Create migration
flask db migrate -m "Description"

# Apply migration
flask db upgrade
```

## 🌐 Deployment

### AWS Deployment

#### Prerequisites

1. **Install required tools**
   ```bash
   # AWS CLI
   curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
   unzip awscliv2.zip
   sudo ./aws/install
   
   # Terraform
   wget https://releases.hashicorp.com/terraform/1.6.0/terraform_1.6.0_linux_amd64.zip
   unzip terraform_1.6.0_linux_amd64.zip
   sudo mv terraform /usr/local/bin/
   
   # Docker (if not already installed)
   sudo apt-get update
   sudo apt-get install docker.io
   ```

2. **Configure AWS credentials**
   ```bash
   aws configure
   # Enter your AWS Access Key ID, Secret Access Key, and region
   ```

#### One-Click Deployment

```bash
# Make deployment script executable
chmod +x scripts/deploy.sh

# Deploy to staging
./scripts/deploy.sh staging

# Deploy to production
./scripts/deploy.sh production
```

#### Manual Deployment Steps

1. **Deploy Infrastructure**
   ```bash
   cd terraform
   terraform init
   terraform plan -var="environment=production" -var="db_password=your-secure-password"
   terraform apply
   ```

2. **Build and Push Docker Image**
   ```bash
   # Get ECR login
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com
   
   # Build and push
   docker build -t personal-finance .
   docker tag personal-finance:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/personal-finance:latest
   docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/personal-finance:latest
   ```

3. **Update ECS Service**
   ```bash
   aws ecs update-service --cluster personal-finance-cluster --service personal-finance-service --force-new-deployment
   ```

### GitHub Actions CI/CD

The repository includes automated CI/CD pipeline:

1. **Set up GitHub Secrets**
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

2. **Push to main branch**
   ```bash
   git push origin main
   ```

The pipeline will automatically:
- Run tests
- Build Docker image
- Push to ECR
- Deploy to ECS
- Run database migrations

## 📊 API Documentation

### Endpoints

#### Transactions

- `GET /api/transactions` - List transactions
- `POST /api/transactions` - Create transaction
- `PUT /api/transactions/<id>` - Update transaction
- `DELETE /api/transactions/<id>` - Delete transaction

#### Dashboard

- `GET /api/dashboard/summary` - Get dashboard summary
- `GET /api/charts/category-distribution` - Category breakdown
- `GET /api/charts/monthly-trend` - Monthly income/expense trend

#### Example: Create Transaction

```javascript
POST /api/transactions
Content-Type: application/json

{
  "date": "25/12/2024",
  "description": "Grocery shopping",
  "amount": 150.75,
  "is_debit": true,
  "category": "Food",
  "account_id": 1,
  "notes": "Weekly groceries"
}
```

## 🧪 Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app_new

# Run specific test file
pytest tests/test_transactions.py
```

## 🔒 Security

### Production Security Features

- **Environment-based configuration**
- **Database connection encryption**
- **Secure container runtime**
- **VPC isolation**
- **Security group restrictions**
- **IAM role-based access**

### Security Checklist

- [ ] Change default secret keys
- [ ] Use strong database passwords
- [ ] Enable HTTPS in production
- [ ] Regular security updates
- [ ] Monitor CloudWatch logs
- [ ] Set up AWS CloudTrail

## 📈 Monitoring & Maintenance

### CloudWatch Monitoring

- **Application logs**: `/ecs/personal-finance`
- **Health checks**: Load balancer health checks
- **Database monitoring**: RDS CloudWatch metrics

### Backup Strategy

- **Database**: Automated RDS backups (7-day retention)
- **Application**: Versioned container images in ECR

### Performance Optimization

- **Database indexing**: Indexed on date and category fields
- **Connection pooling**: SQLAlchemy connection pooling
- **Static file serving**: Served through CDN (future enhancement)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### Development Guidelines

- Follow PEP 8 for Python code
- Write tests for new features
- Update documentation
- Use meaningful commit messages

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

1. **Database connection errors**
   - Check DATABASE_URL format
   - Verify PostgreSQL is running
   - Check network connectivity

2. **Docker build failures**
   - Update Docker to latest version
   - Check Dockerfile syntax
   - Verify base image availability

3. **AWS deployment issues**
   - Verify AWS credentials
   - Check IAM permissions
   - Review CloudWatch logs

### Getting Help

- Check the [Issues](../../issues) page
- Review CloudWatch logs for errors
- Check application health endpoint: `/health`

## 🗺️ Roadmap

### Phase 1: Core Features ✅
- [x] Manual transaction entry
- [x] Dashboard with charts
- [x] Database integration
- [x] Docker containerization
- [x] AWS deployment

### Phase 2: Enhanced Features (Coming Soon)
- [ ] User authentication
- [ ] PDF statement parsing (premium feature)
- [ ] Mobile app (React Native)
- [ ] API authentication
- [ ] Advanced analytics

### Phase 3: Enterprise Features
- [ ] Multi-tenant support
- [ ] Advanced reporting
- [ ] Integration with banks
- [ ] Machine learning insights
- [ ] Automated categorization

---

**Made with ❤️ for better financial management** 