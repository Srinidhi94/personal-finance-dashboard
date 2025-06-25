#!/bin/bash

# AWS EC2 User Data Script for Personal Finance Dashboard
# This script runs on instance launch to set up the environment

set -e

# Log all output
exec > >(tee /var/log/user-data.log|logger -t user-data -s 2>/dev/console) 2>&1

echo "Starting Personal Finance Dashboard setup..."

# Update system
apt-get update
apt-get upgrade -y

# Install required packages
apt-get install -y \
    curl \
    wget \
    git \
    unzip \
    htop \
    nginx \
    certbot \
    python3-certbot-nginx \
    awscli

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
usermod -aG docker ubuntu

# Install Docker Compose
curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Create application directory
mkdir -p /opt/finance-dashboard
chown ubuntu:ubuntu /opt/finance-dashboard

# Create systemd service for Ollama
cat > /etc/systemd/system/ollama.service << 'EOF'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ubuntu
Group=ubuntu
Restart=always
RestartSec=3
Environment="HOME=/home/ubuntu"
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

[Install]
WantedBy=default.target
EOF

# Enable and start Ollama
systemctl daemon-reload
systemctl enable ollama
systemctl start ollama

# Wait for Ollama to start
sleep 10

# Pull required Ollama models
runuser -l ubuntu -c 'ollama pull llama2'

# Configure firewall
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

# Create swap file (recommended for smaller instances)
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' | tee -a /etc/fstab

# Set up log rotation
cat > /etc/logrotate.d/finance-dashboard << 'EOF'
/opt/finance-dashboard/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ubuntu ubuntu
    postrotate
        docker-compose -f /opt/finance-dashboard/docker-compose.yml restart app > /dev/null 2>&1 || true
    endscript
}
EOF

# Create directories
mkdir -p /opt/finance-dashboard/logs
mkdir -p /opt/finance-dashboard/backups
chown -R ubuntu:ubuntu /opt/finance-dashboard

# Set up automatic security updates
cat > /etc/apt/apt.conf.d/20auto-upgrades << 'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Download-Upgradeable-Packages "1";
APT::Periodic::AutocleanInterval "7";
APT::Periodic::Unattended-Upgrade "1";
EOF

# Install and configure fail2ban for security
apt-get install -y fail2ban
cat > /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3

[sshd]
enabled = true
port = ssh
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl enable fail2ban
systemctl start fail2ban

# Create backup script
cat > /opt/finance-dashboard/backup.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/opt/finance-dashboard/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create database backup
docker-compose -f /opt/finance-dashboard/docker-compose.yml exec -T db pg_dump -U finance_user finance_db > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Upload to S3 if configured
if [ ! -z "$BACKUP_S3_BUCKET" ]; then
    aws s3 cp $BACKUP_FILE.gz s3://$BACKUP_S3_BUCKET/database-backups/
fi

# Keep only last 7 days of local backups
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
EOF

chmod +x /opt/finance-dashboard/backup.sh
chown ubuntu:ubuntu /opt/finance-dashboard/backup.sh

# Set up daily backup cron job
cat > /tmp/crontab.txt << 'EOF'
# Daily backup at 2 AM
0 2 * * * /opt/finance-dashboard/backup.sh >> /opt/finance-dashboard/logs/backup.log 2>&1

# SSL certificate renewal check (twice daily)
0 12 * * * /usr/bin/certbot renew --quiet

# System updates (weekly on Sunday at 3 AM)
0 3 * * 0 apt-get update && apt-get upgrade -y >> /opt/finance-dashboard/logs/updates.log 2>&1
EOF

crontab -u ubuntu /tmp/crontab.txt
rm /tmp/crontab.txt

# Configure system limits for better performance
cat >> /etc/security/limits.conf << 'EOF'
ubuntu soft nofile 65536
ubuntu hard nofile 65536
ubuntu soft nproc 4096
ubuntu hard nproc 4096
EOF

# Configure kernel parameters
cat >> /etc/sysctl.conf << 'EOF'
# Network performance
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 12582912 16777216
net.ipv4.tcp_wmem = 4096 12582912 16777216

# File system
fs.file-max = 65536

# Virtual memory
vm.swappiness = 10
vm.dirty_ratio = 15
vm.dirty_background_ratio = 5
EOF

sysctl -p

# Create health check script
cat > /opt/finance-dashboard/health-check.sh << 'EOF'
#!/bin/bash

# Health check script for monitoring
set -e

echo "=== Health Check Report $(date) ==="

# Check disk space
echo "Disk Usage:"
df -h

# Check memory usage
echo -e "\nMemory Usage:"
free -h

# Check Docker containers
echo -e "\nDocker Containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Check application health
echo -e "\nApplication Health:"
curl -s http://localhost/health || echo "Application health check failed"

# Check database
echo -e "\nDatabase Status:"
docker-compose -f /opt/finance-dashboard/docker-compose.yml exec -T db pg_isready -U finance_user || echo "Database check failed"

# Check Ollama
echo -e "\nOllama Status:"
curl -s http://localhost:11434/api/tags || echo "Ollama check failed"

echo -e "\n=== End Health Check ==="
EOF

chmod +x /opt/finance-dashboard/health-check.sh
chown ubuntu:ubuntu /opt/finance-dashboard/health-check.sh

# Create monitoring script
cat > /opt/finance-dashboard/monitor.sh << 'EOF'
#!/bin/bash

# Simple monitoring script
LOG_FILE="/opt/finance-dashboard/logs/monitor.log"
DATE=$(date '+%Y-%m-%d %H:%M:%S')

# Check if application is responding
if curl -s -f http://localhost/health > /dev/null; then
    echo "[$DATE] Application: OK" >> $LOG_FILE
else
    echo "[$DATE] Application: FAILED" >> $LOG_FILE
    # Restart application if it's down
    docker-compose -f /opt/finance-dashboard/docker-compose.yml restart app
fi

# Check disk space (alert if > 85%)
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 85 ]; then
    echo "[$DATE] Disk usage critical: ${DISK_USAGE}%" >> $LOG_FILE
fi

# Check memory usage (alert if > 90%)
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
if [ $MEM_USAGE -gt 90 ]; then
    echo "[$DATE] Memory usage critical: ${MEM_USAGE}%" >> $LOG_FILE
fi
EOF

chmod +x /opt/finance-dashboard/monitor.sh
chown ubuntu:ubuntu /opt/finance-dashboard/monitor.sh

# Add monitoring to cron (every 5 minutes)
(crontab -u ubuntu -l 2>/dev/null; echo "*/5 * * * * /opt/finance-dashboard/monitor.sh") | crontab -u ubuntu -

# Create welcome message
cat > /etc/motd << 'EOF'
Welcome to Personal Finance Dashboard Server!

Quick Commands:
- cd /opt/finance-dashboard    # Go to application directory
- docker-compose logs -f app  # View application logs
- ./health-check.sh           # Run health check
- ./backup.sh                 # Create manual backup

Monitoring:
- Application: http://localhost/health
- Logs: /opt/finance-dashboard/logs/
- Backups: /opt/finance-dashboard/backups/

For more information, see the deployment documentation.
EOF

# Final setup message
echo "Personal Finance Dashboard server setup completed!"
echo "Next steps:"
echo "1. Clone your application repository to /opt/finance-dashboard"
echo "2. Configure environment variables in .env file"
echo "3. Run docker-compose up -d to start the application"
echo "4. Configure SSL with: sudo certbot --nginx -d yourdomain.com"

# Create setup completion marker
touch /opt/finance-dashboard/.setup-complete
chown ubuntu:ubuntu /opt/finance-dashboard/.setup-complete

echo "User data script completed successfully!" 