# AWS EC2 Production Deployment Guide

This guide provides comprehensive instructions for deploying the Personal Finance Dashboard to AWS EC2 using Docker Compose.

## Prerequisites

### AWS Requirements
- AWS Account with EC2 access
- EC2 instance (t3.medium or larger recommended)
- Security Group configured with required ports
- Elastic IP (recommended for production)
- Domain name and SSL certificate (optional but recommended)

### Local Requirements
- AWS CLI configured with appropriate permissions
- SSH key pair for EC2 access
- Docker and Docker Compose knowledge

## Quick Deployment

### 1. Launch EC2 Instance

```bash
# Launch Ubuntu 22.04 LTS instance
aws ec2 run-instances \
    --image-id ami-0c02fb55956c7d316 \
    --instance-type t3.medium \
    --key-name your-key-pair \
    --security-group-ids sg-xxxxxxxxx \
    --subnet-id subnet-xxxxxxxxx \
    --user-data file://user-data.sh
```

### 2. Configure Security Group

Required inbound rules:
- SSH (22): Your IP
- HTTP (80): 0.0.0.0/0
- HTTPS (443): 0.0.0.0/0
- Custom (11434): 127.0.0.1/32 (Ollama - localhost only)

### 3. Deploy Application

```bash
# Copy deployment files to EC2
scp -r deployment/aws/* ubuntu@your-ec2-ip:~/

# SSH to EC2 and run deployment
ssh ubuntu@your-ec2-ip
cd ~/
chmod +x deploy.sh
sudo ./deploy.sh
```

## Manual Deployment Steps

### 1. Server Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Application Deployment

```bash
# Clone repository
git clone <your-repo-url>
cd personal-finance-dashboard

# Copy production configuration
cp deployment/aws/docker-compose.prod.yml docker-compose.yml
cp deployment/aws/nginx.conf nginx.conf

# Set up environment
cp .env.example .env
# Edit .env with production values

# Start services
docker-compose up -d
```

### 3. SSL Configuration (Optional)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Configuration

### Environment Variables

Required production environment variables:

```bash
# Database
DATABASE_URL=postgresql://username:password@db:5432/finance_db
DB_ENCRYPTION_KEY=your-32-character-encryption-key

# Security
SECRET_KEY=your-secret-key
FLASK_ENV=production

# Ollama
OLLAMA_BASE_URL=http://localhost:11434

# Monitoring
ENABLE_MONITORING=true
LOG_LEVEL=INFO

# Backup
BACKUP_ENABLED=true
BACKUP_S3_BUCKET=your-backup-bucket
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
```

### Database Configuration

The production setup uses PostgreSQL with:
- Persistent data volumes
- Connection pooling
- Automated backups
- Performance monitoring

### Security Features

- Nginx reverse proxy with security headers
- Rate limiting and DDoS protection
- SSL/TLS encryption
- Database connection encryption
- Field-level data encryption
- Audit logging

## Monitoring and Maintenance

### Health Checks

```bash
# Application health
curl http://localhost/health

# Detailed health check
curl http://localhost/health/detailed

# Database status
docker-compose exec db pg_isready

# Ollama status
curl http://localhost:11434/api/tags
```

### Logs

```bash
# Application logs
docker-compose logs -f app

# Database logs
docker-compose logs -f db

# Nginx logs
docker-compose logs -f nginx

# System logs
sudo journalctl -u docker -f
```

### Backups

Automated backups are configured to run daily:

```bash
# Manual backup
docker-compose exec db pg_dump -U username finance_db > backup_$(date +%Y%m%d).sql

# Restore backup
docker-compose exec -T db psql -U username finance_db < backup_file.sql
```

### Updates

```bash
# Update application
git pull origin main
docker-compose build --no-cache
docker-compose up -d

# Update Ollama models
docker-compose exec app ollama pull llama2
```

## Scaling and Performance

### Horizontal Scaling

For high-traffic scenarios:
1. Use Application Load Balancer
2. Deploy multiple app instances
3. Use Redis for session storage
4. Implement database read replicas

### Performance Optimization

1. **Database Optimization**
   - Connection pooling
   - Query optimization
   - Index management
   - Regular VACUUM operations

2. **Application Optimization**
   - Caching with Redis
   - Static file CDN
   - Database query optimization
   - Background job processing

3. **Infrastructure Optimization**
   - Use larger EC2 instances
   - SSD storage
   - VPC optimization
   - CloudWatch monitoring

## Troubleshooting

### Common Issues

1. **Application won't start**
   ```bash
   # Check logs
   docker-compose logs app
   
   # Verify environment variables
   docker-compose config
   
   # Check database connection
   docker-compose exec app python -c "from app import db; db.create_all()"
   ```

2. **Database connection issues**
   ```bash
   # Check database status
   docker-compose exec db pg_isready
   
   # Reset database
   docker-compose down -v
   docker-compose up -d
   ```

3. **Ollama not responding**
   ```bash
   # Check Ollama status
   systemctl status ollama
   
   # Restart Ollama
   sudo systemctl restart ollama
   
   # Check models
   ollama list
   ```

4. **SSL certificate issues**
   ```bash
   # Renew certificate
   sudo certbot renew
   
   # Check certificate status
   sudo certbot certificates
   ```

### Performance Issues

1. **High memory usage**
   - Monitor with `docker stats`
   - Adjust container memory limits
   - Optimize database queries

2. **Slow response times**
   - Check database performance
   - Monitor Ollama model loading
   - Review nginx configuration

3. **Storage issues**
   - Monitor disk usage
   - Clean up old logs
   - Optimize database size

## Security Considerations

### Network Security
- Use VPC with private subnets
- Configure security groups restrictively
- Enable VPC Flow Logs
- Use AWS WAF for additional protection

### Data Security
- Enable encryption at rest
- Use encrypted database connections
- Implement proper backup encryption
- Regular security updates

### Access Control
- Use IAM roles and policies
- Implement least privilege access
- Enable CloudTrail logging
- Regular access reviews

## Cost Optimization

### EC2 Optimization
- Use Reserved Instances for predictable workloads
- Consider Spot Instances for development
- Right-size instances based on usage
- Use Auto Scaling for variable loads

### Storage Optimization
- Use GP3 volumes for better price/performance
- Implement lifecycle policies for backups
- Monitor and optimize database size
- Use S3 for static file storage

## Support and Maintenance

### Regular Maintenance Tasks
- Weekly security updates
- Monthly backup verification
- Quarterly performance reviews
- Annual security audits

### Monitoring Setup
- CloudWatch alarms for key metrics
- Log aggregation and analysis
- Performance monitoring
- Error tracking and alerting

For additional support or questions, refer to the main project documentation or create an issue in the repository. 