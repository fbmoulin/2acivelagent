# Deployment Guide - Sistema de Automação Jurídica

Complete step-by-step tutorial for deploying the Judicial Automation System in production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Preparation](#server-preparation)
3. [Installation](#installation)
4. [Configuration](#configuration)
5. [SSL/TLS Setup](#ssltls-setup)
6. [Database Migrations](#database-migrations)
7. [Starting Services](#starting-services)
8. [Post-Deployment Verification](#post-deployment-verification)
9. [Monitoring Setup](#monitoring-setup)
10. [Backup Configuration](#backup-configuration)
11. [Security Hardening](#security-hardening)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Minimum System Requirements

| Environment | CPU | RAM | Disk | Network |
|-------------|-----|-----|------|---------|
| Development | 2 cores | 4GB | 20GB SSD | - |
| Staging | 4 cores | 8GB | 50GB SSD | 100Mbps |
| Production | 8 cores | 16GB | 100GB SSD | 1Gbps |

### Required Software

- Ubuntu 22.04 LTS (recommended) or Debian 12
- Docker Engine 24.0+
- Docker Compose v2.20+
- Git 2.40+
- OpenSSL 3.0+

### Required Accounts & API Keys

| Service | Purpose | How to Obtain |
|---------|---------|---------------|
| OpenAI | GPT-4 for legal analysis | https://platform.openai.com/api-keys |
| DATAJUD (CNJ) | Brazilian jurisprudence API | https://datajud-wiki.cnj.jus.br/ |
| Google Cloud | Document AI, Drive, Docs | https://console.cloud.google.com |
| Domain + DNS | Production URL | Your domain registrar |

---

## Server Preparation

### Step 1: Update System

```bash
# Update package lists and upgrade existing packages
sudo apt update && sudo apt upgrade -y

# Install essential tools
sudo apt install -y curl wget git nano htop ufw
```

### Step 2: Install Docker

```bash
# Remove old Docker versions
sudo apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null

# Install Docker using official script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add current user to docker group
sudo usermod -aG docker $USER

# Apply group changes (or logout/login)
newgrp docker

# Verify installation
docker --version
docker compose version
```

### Step 3: Configure Firewall

```bash
# Enable UFW firewall
sudo ufw enable

# Allow essential ports
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP (redirect to HTTPS)
sudo ufw allow 443/tcp   # HTTPS

# Block direct access to internal services
sudo ufw deny 5678/tcp   # N8N (access via nginx)
sudo ufw deny 5000/tcp   # Python API (access via nginx)
sudo ufw deny 5432/tcp   # PostgreSQL (internal only)
sudo ufw deny 6379/tcp   # Redis (internal only)
sudo ufw deny 9090/tcp   # Prometheus (internal only)

# Allow Grafana for monitoring
sudo ufw allow 3000/tcp  # Grafana dashboard

# Verify rules
sudo ufw status verbose
```

### Step 4: Create Application User

```bash
# Create dedicated user for the application
sudo useradd -m -s /bin/bash judicial
sudo usermod -aG docker judicial

# Set up directory structure
sudo mkdir -p /opt/judicial-automation
sudo chown judicial:judicial /opt/judicial-automation
```

---

## Installation

### Step 1: Clone Repository

```bash
# Switch to application user
sudo su - judicial

# Clone the repository
cd /opt/judicial-automation
git clone https://github.com/fbmoulin/2acivelagent.git .

# Verify structure
ls -la
```

### Step 2: Create Required Directories

```bash
# Create data directories
mkdir -p data/{n8n,postgres,uploads,exports}
mkdir -p monitoring/logs/{nginx,python}
mkdir -p security/{ssl_certificates,backup_policies}
mkdir -p config/credentials

# Set permissions
chmod 700 config/credentials
chmod 700 security/ssl_certificates
```

### Step 3: Configure Environment Variables

```bash
# Copy template
cp .env.template .env

# Generate secure secrets
echo "Generating secure secrets..."

# Generate JWT secret
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "JWT_SECRET=$JWT_SECRET"

# Generate encryption key
ENCRYPTION_KEY=$(python3 -c "import secrets; print(secrets.token_hex(16))")
echo "ENCRYPTION_KEY=$ENCRYPTION_KEY"

# Edit configuration
nano .env
```

### Step 4: Configure .env File

Edit `.env` with your production values:

```bash
# ===========================================
# PRODUCTION CONFIGURATION
# ===========================================

# N8N Configuration
N8N_HOST=your-domain.com
N8N_PORT=5678
N8N_PROTOCOL=https
N8N_USER=admin
N8N_PASSWORD=<strong-password-here>
WEBHOOK_URL=https://your-domain.com/

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=n8n
POSTGRES_USER=n8n_user
POSTGRES_PASSWORD=<strong-database-password>

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=<strong-redis-password>

# OpenAI Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4
OPENAI_MAX_TOKENS=4000

# DATAJUD API (CNJ)
DATAJUD_USERNAME=your-cnj-username
DATAJUD_PASSWORD=your-cnj-password
DATAJUD_BASE_URL=https://api-publica.datajud.cnj.jus.br

# Security Settings
JWT_SECRET=<generated-64-char-hex>
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=24
API_AUTH_ENABLED=true
ALLOWED_ORIGINS=https://your-domain.com,https://n8n.your-domain.com

# Application Settings
FLASK_ENV=production
FLASK_DEBUG=false
LOG_LEVEL=INFO
TIMEZONE=America/Sao_Paulo

# Monitoring
GRAFANA_USER=admin
GRAFANA_PASSWORD=<strong-grafana-password>
```

---

## SSL/TLS Setup

### Option A: Let's Encrypt (Recommended for Production)

```bash
# Install Certbot
sudo apt install -y certbot

# Stop any service on port 80
sudo systemctl stop nginx 2>/dev/null || true

# Obtain certificate
sudo certbot certonly --standalone \
  -d your-domain.com \
  -d www.your-domain.com \
  --email admin@your-domain.com \
  --agree-tos \
  --non-interactive

# Copy certificates to project
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem \
  /opt/judicial-automation/security/ssl_certificates/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem \
  /opt/judicial-automation/security/ssl_certificates/

# Set permissions
sudo chown judicial:judicial /opt/judicial-automation/security/ssl_certificates/*.pem
chmod 600 /opt/judicial-automation/security/ssl_certificates/*.pem

# Set up auto-renewal
sudo crontab -e
# Add: 0 3 * * * certbot renew --quiet --post-hook "docker compose -f /opt/judicial-automation/docker-compose.yml restart nginx"
```

### Option B: Self-Signed (Development/Testing Only)

```bash
# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout security/ssl_certificates/privkey.pem \
  -out security/ssl_certificates/fullchain.pem \
  -subj "/CN=localhost/O=Development/C=BR"
```

---

## Database Migrations

### Step 1: Start Database Service First

```bash
# Start only PostgreSQL
docker compose up -d postgres

# Wait for database to be ready
echo "Waiting for PostgreSQL to start..."
sleep 10

# Verify database is running
docker compose exec postgres pg_isready -U n8n_user -d n8n
```

### Step 2: Run Alembic Migrations

```bash
# Build Python services image
docker compose build python-services

# Run migrations
docker compose run --rm python-services alembic upgrade head

# Verify migrations
docker compose run --rm python-services alembic current
```

### Step 3: Initialize Database Schema

```bash
# The init script runs automatically, but verify:
docker compose exec postgres psql -U n8n_user -d n8n -c "\dt"
```

---

## Starting Services

### Step 1: Start All Services (Recommended Order)

```bash
# 1. Start infrastructure services
docker compose up -d postgres redis
sleep 15

# 2. Start application services
docker compose up -d n8n python-services
sleep 30

# 3. Start reverse proxy
docker compose up -d nginx
sleep 5

# 4. Start monitoring stack
docker compose up -d prometheus grafana
sleep 10

# 5. Start log management
docker compose up -d filebeat

# Verify all services are running
docker compose ps
```

### Step 2: Verify Services Health

```bash
# Check all container status
docker compose ps

# Expected output:
# NAME                    STATUS              PORTS
# judicial-n8n            Up (healthy)        5678/tcp
# judicial-postgres       Up (healthy)        5432/tcp
# judicial-redis          Up (healthy)        6379/tcp
# judicial-python         Up (healthy)        5000/tcp
# judicial-nginx          Up                  80/tcp, 443/tcp
# judicial-prometheus     Up                  9090/tcp
# judicial-grafana        Up                  3000/tcp

# Check logs for errors
docker compose logs --tail=50 n8n
docker compose logs --tail=50 python-services
```

### Step 3: Test Endpoints

```bash
# Test N8N health
curl -k https://localhost/healthz

# Test Python API health
curl -k https://localhost/api/health

# Test Grafana
curl -k http://localhost:3000/api/health
```

---

## Post-Deployment Verification

### Verification Checklist

```bash
#!/bin/bash
# save as verify-deployment.sh

echo "=== Deployment Verification ==="

# 1. Check all containers are running
echo -n "1. Containers running: "
if [ $(docker compose ps -q | wc -l) -ge 6 ]; then
  echo "PASS"
else
  echo "FAIL"
fi

# 2. Check N8N is accessible
echo -n "2. N8N accessible: "
if curl -s -o /dev/null -w "%{http_code}" https://localhost/healthz -k | grep -q "200"; then
  echo "PASS"
else
  echo "FAIL"
fi

# 3. Check API is accessible
echo -n "3. Python API accessible: "
if curl -s -o /dev/null -w "%{http_code}" https://localhost/api/health -k | grep -q "200"; then
  echo "PASS"
else
  echo "FAIL"
fi

# 4. Check database connection
echo -n "4. Database connection: "
if docker compose exec -T postgres pg_isready -U n8n_user -d n8n > /dev/null 2>&1; then
  echo "PASS"
else
  echo "FAIL"
fi

# 5. Check Redis connection
echo -n "5. Redis connection: "
if docker compose exec -T redis redis-cli ping | grep -q "PONG"; then
  echo "PASS"
else
  echo "FAIL"
fi

# 6. Check SSL certificate
echo -n "6. SSL certificate valid: "
if openssl s_client -connect localhost:443 -servername localhost 2>/dev/null | openssl x509 -noout -dates 2>/dev/null; then
  echo "PASS"
else
  echo "FAIL (self-signed or expired)"
fi

echo "=== Verification Complete ==="
```

---

## Monitoring Setup

### Step 1: Access Grafana

1. Open browser: `https://your-domain.com:3000`
2. Login with credentials from `.env`:
   - Username: `admin`
   - Password: `<GRAFANA_PASSWORD>`

### Step 2: Configure Data Sources

1. Go to **Configuration > Data Sources**
2. Add **Prometheus**:
   - URL: `http://prometheus:9090`
   - Access: Server (default)
3. Click **Save & Test**

### Step 3: Import Dashboards

Import these recommended dashboards:

| Dashboard | ID | Purpose |
|-----------|-----|---------|
| Docker Containers | 893 | Container metrics |
| Node Exporter | 1860 | System metrics |
| PostgreSQL | 9628 | Database metrics |
| Redis | 11835 | Cache metrics |

### Step 4: Configure Alerts

1. Go to **Alerting > Alert Rules**
2. Create alerts for:
   - High CPU usage (>80%)
   - High memory usage (>85%)
   - Disk space low (<10GB)
   - Service down (health check fails)

---

## Backup Configuration

### Step 1: Configure Automatic Backups

```bash
# Create backup script
cat > /opt/judicial-automation/scripts/shell/backup.sh << 'EOF'
#!/bin/bash
set -e

BACKUP_DIR="/opt/backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Starting backup at $(date)"

# Backup PostgreSQL
echo "Backing up PostgreSQL..."
docker compose exec -T postgres pg_dump -U n8n_user n8n | gzip > "$BACKUP_DIR/database.sql.gz"

# Backup N8N workflows
echo "Backing up N8N workflows..."
docker compose exec -T n8n n8n export:workflow --all --output=/home/node/.n8n/backup.json 2>/dev/null || true
docker cp judicial-n8n:/home/node/.n8n/backup.json "$BACKUP_DIR/workflows.json" 2>/dev/null || true

# Backup configuration
echo "Backing up configuration..."
tar -czf "$BACKUP_DIR/config.tar.gz" -C /opt/judicial-automation .env config/

# Cleanup old backups (keep 7 days)
find /opt/backups -type d -mtime +7 -exec rm -rf {} \; 2>/dev/null || true

echo "Backup completed: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"
EOF

chmod +x /opt/judicial-automation/scripts/shell/backup.sh
```

### Step 2: Schedule Automatic Backups

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/judicial-automation/scripts/shell/backup.sh >> /var/log/judicial-backup.log 2>&1
```

### Step 3: Test Backup Restore

```bash
# Restore database from backup
gunzip -c /opt/backups/YYYYMMDD_HHMMSS/database.sql.gz | \
  docker compose exec -T postgres psql -U n8n_user n8n
```

---

## Security Hardening

### Step 1: Configure Fail2Ban

```bash
# Install fail2ban
sudo apt install -y fail2ban

# Create jail configuration
sudo tee /etc/fail2ban/jail.local << EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /opt/judicial-automation/monitoring/logs/nginx/error.log
EOF

# Restart fail2ban
sudo systemctl restart fail2ban
sudo systemctl enable fail2ban
```

### Step 2: Configure Log Rotation

```bash
sudo tee /etc/logrotate.d/judicial-automation << EOF
/opt/judicial-automation/monitoring/logs/**/*.log {
    daily
    rotate 14
    compress
    delaycompress
    missingok
    notifempty
    create 0640 judicial judicial
}
EOF
```

### Step 3: Security Checklist

- [ ] All passwords are strong (16+ characters, mixed case, numbers, symbols)
- [ ] JWT_SECRET is unique and secure (64+ hex characters)
- [ ] SSL/TLS certificate is valid and not self-signed
- [ ] Firewall rules are properly configured
- [ ] Database ports are not exposed externally
- [ ] API authentication is enabled (`API_AUTH_ENABLED=true`)
- [ ] CORS is restricted to specific origins
- [ ] Fail2ban is active and monitoring logs
- [ ] Backups are running and tested

---

## Troubleshooting

### Common Issues

#### N8N Not Starting

```bash
# Check logs
docker compose logs n8n

# Common fixes:
# 1. Database not ready
docker compose restart postgres
sleep 30
docker compose restart n8n

# 2. Permission issues
docker compose exec n8n ls -la /home/node/.n8n

# 3. Memory issues
docker stats --no-stream
```

#### Python API 502 Error

```bash
# Check if container is running
docker compose ps python-services

# Check logs
docker compose logs python-services

# Rebuild if needed
docker compose build python-services
docker compose up -d python-services
```

#### Database Connection Failed

```bash
# Check PostgreSQL status
docker compose exec postgres pg_isready

# Check connection from app container
docker compose exec python-services python -c "
import psycopg2
import os
conn = psycopg2.connect(os.environ.get('POSTGRES_URL'))
print('Connection successful')
conn.close()
"
```

#### SSL Certificate Issues

```bash
# Check certificate validity
openssl s_client -connect your-domain.com:443 -servername your-domain.com 2>/dev/null | \
  openssl x509 -noout -dates

# Renew Let's Encrypt
sudo certbot renew --force-renewal
```

### Useful Commands

```bash
# View all logs
docker compose logs -f

# View specific service logs
docker compose logs -f n8n python-services

# Restart all services
docker compose restart

# Full rebuild
docker compose down
docker compose build --no-cache
docker compose up -d

# Enter container shell
docker compose exec python-services /bin/sh
docker compose exec postgres psql -U n8n_user -d n8n

# Check resource usage
docker stats

# Cleanup unused resources
docker system prune -a --volumes
```

---

## Production Deployment Summary

```bash
# Quick deployment commands summary:

# 1. Clone and configure
git clone https://github.com/fbmoulin/2acivelagent.git /opt/judicial-automation
cd /opt/judicial-automation
cp .env.template .env
nano .env  # Configure all variables

# 2. Set up SSL
sudo certbot certonly --standalone -d your-domain.com

# 3. Start services
docker compose up -d

# 4. Verify deployment
docker compose ps
curl -k https://localhost/api/health

# 5. Configure monitoring
# Access Grafana at https://your-domain.com:3000

# 6. Set up backups
crontab -e
# Add: 0 2 * * * /opt/judicial-automation/scripts/shell/backup.sh
```

---

**Deployment Complete!**

For additional support:
- GitHub Issues: https://github.com/fbmoulin/2acivelagent/issues
- API Documentation: [docs/API_DOCUMENTATION.md](API_DOCUMENTATION.md)
- Security Guide: [SECURITY.md](SECURITY.md)
