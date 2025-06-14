# AWS Deployment Guide

This directory contains all the necessary configuration files and scripts to deploy the Personal Finance Dashboard to AWS using ECS Fargate, RDS PostgreSQL, and Application Load Balancer.

## Prerequisites

1. **AWS CLI** installed and configured
2. **Terraform** (>= 1.0) installed
3. **Docker** installed
4. **AWS Account** with appropriate permissions

## Quick Start

### 1. Set up AWS Infrastructure

```bash
# Navigate to the AWS directory
cd .aws

# Initialize Terraform
terraform init

# Review the infrastructure plan
terraform plan

# Apply the infrastructure (creates VPC, RDS, ECS, ALB, etc.)
terraform apply
```

### 2. Configure GitHub Secrets

After running Terraform, configure these secrets in your GitHub repository:

- `AWS_ACCESS_KEY_ID`: Your AWS access key
- `AWS_SECRET_ACCESS_KEY`: Your AWS secret key
- `AWS_SESSION_TOKEN`: (Optional) If using temporary credentials
- `CODECOV_TOKEN`: (Optional) For code coverage reporting

### 3. Update Task Definition

Update `.aws/task-definition.json` with the actual values from Terraform output:

```bash
# Get the outputs from Terraform
terraform output

# Update task-definition.json with:
# - ECR repository URL
# - RDS endpoint
# - Task execution role ARN
# - Task role ARN
```

### 4. Deploy Application

Use the GitHub Actions workflow to deploy:

1. Go to your repository's Actions tab
2. Select "Deploy to AWS" workflow
3. Click "Run workflow"
4. Choose environment (development/production)
5. Type "deploy" to confirm
6. Click "Run workflow"

## Infrastructure Components

### Networking
- **VPC**: Custom VPC with public and private subnets
- **Internet Gateway**: For public internet access
- **Route Tables**: Proper routing for public/private subnets
- **Security Groups**: Restrictive security rules

### Compute
- **ECS Cluster**: Fargate cluster for running containers
- **ECS Service**: Auto-scaling service definition
- **Application Load Balancer**: HTTP/HTTPS traffic distribution
- **Target Groups**: Health check and routing configuration

### Database
- **RDS PostgreSQL**: Managed database with automated backups
- **DB Subnet Group**: Database in private subnets
- **Security Groups**: Database access only from ECS tasks

### Storage & Monitoring
- **ECR Repository**: Container image storage
- **CloudWatch Logs**: Application logging
- **CloudWatch Metrics**: Performance monitoring

## Configuration Files

### `task-definition.json`
ECS task definition with:
- Container configuration
- Environment variables
- Health checks
- Resource limits
- Logging configuration

### `infrastructure.tf`
Complete Terraform configuration for:
- VPC and networking
- RDS database
- ECS cluster and services
- Load balancer
- IAM roles and policies
- Security groups

## Environment Variables

The application requires these environment variables:

| Variable | Description | Example |
|----------|-------------|---------|
| `FLASK_ENV` | Flask environment | `production` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | Flask secret key | Stored in AWS Secrets Manager |

## Security Best Practices

### Network Security
- Database in private subnets only
- Security groups with minimal required access
- No direct internet access to database

### Application Security
- Secrets stored in AWS Secrets Manager
- IAM roles with least privilege
- Container security scanning enabled

### Data Security
- RDS encryption at rest
- Automated backups with 7-day retention
- SSL/TLS for all connections

## Monitoring & Logging

### CloudWatch Logs
- Application logs: `/ecs/personal-finance`
- Log retention: 7 days (configurable)

### Health Checks
- ALB health checks on `/health` endpoint
- ECS task health checks
- RDS monitoring

### Metrics
- ECS service metrics
- ALB request metrics
- RDS performance metrics

## Scaling Configuration

### Auto Scaling
- ECS service auto-scaling based on CPU/memory
- RDS storage auto-scaling (20GB to 100GB)
- ALB automatically handles traffic distribution

### Resource Limits
- **Development**: 256 CPU, 512 MB memory
- **Production**: Configurable based on needs

## Cost Optimization

### Development Environment
- `db.t3.micro` RDS instance
- Minimal ECS resources
- 7-day log retention

### Production Recommendations
- `db.t3.small` or larger RDS instance
- Increased ECS resources
- Longer log retention
- Enable deletion protection

## Troubleshooting

### Common Issues

1. **Task fails to start**
   - Check CloudWatch logs
   - Verify environment variables
   - Check security group rules

2. **Database connection fails**
   - Verify RDS endpoint in task definition
   - Check security group rules
   - Verify database credentials

3. **Load balancer health checks fail**
   - Ensure `/health` endpoint is working
   - Check target group configuration
   - Verify security group rules

### Useful Commands

```bash
# Check ECS service status
aws ecs describe-services --cluster personal-finance-cluster --services personal-finance-service

# View CloudWatch logs
aws logs tail /ecs/personal-finance --follow

# Check RDS status
aws rds describe-db-instances --db-instance-identifier personal-finance-db

# List ECR images
aws ecr list-images --repository-name personal-finance
```

## Cleanup

To destroy all AWS resources:

```bash
cd .aws
terraform destroy
```

**Warning**: This will permanently delete all data. Make sure to backup any important data before running this command.

## Support

For issues with AWS deployment:

1. Check CloudWatch logs for application errors
2. Review Terraform output for infrastructure issues
3. Verify GitHub Actions logs for deployment problems
4. Check AWS console for service status

## Next Steps

After successful deployment:

1. Set up custom domain name
2. Configure SSL/TLS certificate
3. Set up monitoring alerts
4. Configure backup strategies
5. Implement CI/CD improvements 