#!/bin/bash
# AWS EC2 Deployment Script for Personal Finance Dashboard
# This script sets up and deploys the application on a fresh EC2 instance

set -e

# Configuration
APP_NAME="personal-finance-dashboard"
APP_DIR="/opt/${APP_NAME}"
DOCKER_COMPOSE_VERSION="2.24.0"
OLLAMA_VERSION="0.1.17"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
    exit 1
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   error "This script should not be run as root for security reasons"
fi

# Update system
log "Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# Install required packages
log "Installing required packages..."
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release \
    unzip \
    htop \
    nginx \
    certbot \
    python3-certbot-nginx

# Install Docker
log "Installing Docker..."
if ! command -v docker &> /dev/null; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io
    sudo usermod -aG docker $USER
    log "Docker installed successfully"
else
    log "Docker already installed"
fi

# Install Docker Compose
log "Installing Docker Compose..."
if ! command -v docker-compose &> /dev/null; then
    sudo curl -L "https://github.com/docker/compose/releases/download/v${DOCKER_COMPOSE_VERSION}/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    log "Docker Compose installed successfully"
else
    log "Docker Compose already installed"
fi

# Install Ollama
log "Installing Ollama..."
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.ai/install.sh | sh
    log "Ollama installed successfully"
else
    log "Ollama already installed"
fi

# Create application directory
log "Setting up application directory..."
sudo mkdir -p $APP_DIR
sudo chown $USER:$USER $APP_DIR

# Create required directories
mkdir -p $APP_DIR/{logs,backups,nginx,uploads}
mkdir -p $APP_DIR/nginx/{ssl,logs}

# Create environment file
log "Creating environment configuration..."
cat > $APP_DIR/.env << 'EOL'
# Production Environment Configuration
FLASK_ENV=production
SECRET_KEY=CHANGE_THIS_IN_PRODUCTION
DB_ENCRYPTION_KEY=CHANGE_THIS_IN_PRODUCTION

# Database Configuration
POSTGRES_USER=financeuser
POSTGRES_PASSWORD=CHANGE_THIS_IN_PRODUCTION
POSTGRES_DB=personal_finance

# Docker Configuration
DOCKER_USERNAME=your-docker-username
IMAGE_TAG=latest

# Redis Configuration
REDIS_PASSWORD=CHANGE_THIS_IN_PRODUCTION

# Domain Configuration
DOMAIN_NAME=your-domain.com
EOL

# Set proper permissions
chmod 600 $APP_DIR/.env

# Copy deployment files
log "Setting up deployment files..."
cp deployment/aws/docker-compose.prod.yml $APP_DIR/docker-compose.yml
cp deployment/aws/nginx.conf $APP_DIR/nginx/nginx.conf

# Create systemd service for Ollama
log "Setting up Ollama service..."
sudo tee /etc/systemd/system/ollama.service > /dev/null << 'EOL'
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"

[Install]
WantedBy=default.target
EOL

# Create ollama user
sudo useradd -r -s /bin/false -m -d /usr/share/ollama ollama

# Start and enable Ollama
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama

# Wait for Ollama to start
log "Waiting for Ollama to start..."
sleep 10

# Pull required models
log "Pulling Ollama models..."
sudo -u ollama ollama pull llama2:7b-chat

# Generate SSL certificates (self-signed for development)
log "Generating SSL certificates..."
if [ ! -f "$APP_DIR/nginx/ssl/cert.pem" ]; then
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout $APP_DIR/nginx/ssl/key.pem \
        -out $APP_DIR/nginx/ssl/cert.pem \
        -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"
fi

# Setup log rotation
log "Setting up log rotation..."
sudo tee /etc/logrotate.d/personal-finance-dashboard > /dev/null << 'EOL'
/opt/personal-finance-dashboard/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 root root
}
EOL

# Create backup script
log "Creating backup script..."
cat > $APP_DIR/backup.sh << 'EOL'
#!/bin/bash
# Database backup script

BACKUP_DIR="/opt/personal-finance-dashboard/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/backup_$DATE.sql"

# Create backup directory if it doesn't exist
mkdir -p $BACKUP_DIR

# Create database backup
docker-compose exec -T db pg_dump -U financeuser personal_finance > $BACKUP_FILE

# Compress backup
gzip $BACKUP_FILE

# Remove backups older than 30 days
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: $BACKUP_FILE.gz"
EOL

chmod +x $APP_DIR/backup.sh

# Setup cron job for backups
log "Setting up automated backups..."
(crontab -l 2>/dev/null; echo "0 2 * * * $APP_DIR/backup.sh") | crontab -

# Create deployment script
cat > $APP_DIR/deploy.sh << 'EOL'
#!/bin/bash
# Application deployment script

cd /opt/personal-finance-dashboard

# Pull latest images
docker-compose pull

# Stop services
docker-compose down

# Start services
docker-compose up -d

# Wait for services to be healthy
sleep 30

# Check health
docker-compose ps
curl -f http://localhost:8080/health || echo "Health check failed"

echo "Deployment completed"
EOL

chmod +x $APP_DIR/deploy.sh

# Setup firewall
log "Configuring firewall..."
sudo ufw --force enable
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443

# Create monitoring script
cat > $APP_DIR/monitor.sh << 'EOL'
#!/bin/bash
# System monitoring script

echo "=== System Status ==="
date
echo ""

echo "=== Disk Usage ==="
df -h
echo ""

echo "=== Memory Usage ==="
free -h
echo ""

echo "=== Docker Services ==="
docker-compose ps
echo ""

echo "=== Application Health ==="
curl -s http://localhost:8080/health | jq .
echo ""

echo "=== Recent Logs ==="
docker-compose logs --tail=10 app
EOL

chmod +x $APP_DIR/monitor.sh

log "Deployment setup completed!"
log "Next steps:"
log "1. Edit $APP_DIR/.env with your production values"
log "2. Configure your domain name and SSL certificates"
log "3. Run: cd $APP_DIR && docker-compose up -d"
log "4. Setup monitoring and alerting"

warn "Remember to:"
warn "- Change all default passwords in .env file"
warn "- Setup proper SSL certificates for production"
warn "- Configure monitoring and alerting"
warn "- Setup regular security updates"
