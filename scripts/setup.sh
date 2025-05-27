#!/bin/bash

# 🤖 EasyRSVP AI Team - Setup Script
# ===================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Logo and header
echo -e "${PURPLE}"
echo "  ____                 ____  ______     ______    _    ___   _____"
echo " | __ )  __ _ ___  __ _|  _ \/ ___\ \   / |  _ \  / \  |_ _| |_   _|__  __ _ _ __ ___"
echo " |  _ \ / _\` / __|/ _\` | |_) \___ \\\\ \   / /| |_) |/ _ \  | |    | |/ _ \/ _\` | '_ \` _ \\"
echo " | |_) | (_| \__ \ (_| |  _ < ___) |\ \_/ / |  __// ___ \ | |    | |  __/ (_| | | | | | |"
echo " |____/ \__,_|___/\__,_|_| \_\____/  \___/  |_|  /_/   \_\___|   |_|\___|\__,_|_| |_| |_|"
echo ""
echo -e "${NC}"
echo -e "${CYAN}🤖 EasyRSVP AI Team - Automated Development Workflow Setup${NC}"
echo -e "${CYAN}=================================================================${NC}"
echo ""

# Function to print colored messages
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   print_error "This script should not be run as root for security reasons."
   exit 1
fi

# Check system requirements
print_step "Checking system requirements..."

# Check Docker
if ! command -v docker &> /dev/null; then
    print_error "Docker is required but not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is required but not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3.9+ is required but not installed. Please install Python first."
    exit 1
fi

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js 18+ is required but not installed. Please install Node.js first."
    exit 1
fi

print_success "All system requirements are met!"

# Create directory structure
print_step "Creating directory structure..."

mkdir -p {logs,data,config,monitoring,tests,docs}
mkdir -p data/{uploads,backups,exports}
mkdir -p config/{grafana,prometheus,redis}
mkdir -p logs/{agents,n8n,monitoring}

print_success "Directory structure created!"

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_step "Setting up environment configuration..."
    
    if [ -f "env.example" ]; then
        cp env.example .env
        print_warning "Environment file created from template. Please edit .env with your actual values."
    else
        print_error "env.example file not found. Please create it first."
        exit 1
    fi
else
    print_status "Environment file already exists."
fi

# Install Node.js dependencies
print_step "Installing Node.js dependencies..."
if [ -f "package.json" ]; then
    npm install
    print_success "Node.js dependencies installed!"
else
    print_warning "package.json not found, skipping Node.js dependencies."
fi

# Create Python virtual environment
print_step "Setting up Python virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    print_success "Python virtual environment created!"
fi

# Activate virtual environment and install dependencies
print_step "Installing Python dependencies..."
source venv/bin/activate
if [ -f "requirements.txt" ]; then
    pip install --upgrade pip
    pip install -r requirements.txt
    print_success "Python dependencies installed!"
else
    print_warning "requirements.txt not found, skipping Python dependencies."
fi

# Create configuration files
print_step "Creating configuration files..."

# Redis configuration
cat > config/redis.conf << EOF
# EasyRSVP AI Team Redis Configuration
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
EOF

# Prometheus configuration
cat > config/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'n8n'
    static_configs:
      - targets: ['n8n:5678']

  - job_name: 'ai-agents'
    static_configs:
      - targets: ['ai-agents:8000']

  - job_name: 'monitoring'
    static_configs:
      - targets: ['monitoring:3000']
EOF

# Database initialization SQL
cat > scripts/init-db.sql << EOF
-- EasyRSVP AI Team Database Initialization

-- Create databases
CREATE DATABASE IF NOT EXISTS easyrsvp_ai;
CREATE DATABASE IF NOT EXISTS n8n;
CREATE DATABASE IF NOT EXISTS easyrsvp_ai_test;

-- Create extensions
\c easyrsvp_ai;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c n8n;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c easyrsvp_ai_test;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOF

print_success "Configuration files created!"

# Set up Git hooks (if in Git repository)
if [ -d ".git" ]; then
    print_step "Setting up Git hooks..."
    
    mkdir -p .git/hooks
    
    # Pre-commit hook
    cat > .git/hooks/pre-commit << EOF
#!/bin/bash
# EasyRSVP AI Team Pre-commit Hook

echo "Running pre-commit checks..."

# Run Python linting
if command -v flake8 &> /dev/null; then
    echo "Running flake8..."
    flake8 agents/ tests/ scripts/ || exit 1
fi

# Run Python formatting check
if command -v black &> /dev/null; then
    echo "Running black formatting check..."
    black --check agents/ tests/ scripts/ || exit 1
fi

# Run tests
if [ -f "requirements.txt" ]; then
    echo "Running tests..."
    python -m pytest tests/ -q || exit 1
fi

echo "All pre-commit checks passed!"
EOF

    chmod +x .git/hooks/pre-commit
    print_success "Git hooks configured!"
fi

# Create systemd service (optional)
if command -v systemctl &> /dev/null; then
    print_step "Do you want to create a systemd service for auto-start? (y/n)"
    read -r response
    if [[ "$response" =~ ^([yY][eE][sS]|[yY])$ ]]; then
        cat > easyrsvp-ai-team.service << EOF
[Unit]
Description=EasyRSVP AI Team
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$(pwd)
ExecStart=/usr/bin/docker-compose up -d
ExecStop=/usr/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF
        print_warning "Systemd service file created. To install run:"
        echo "sudo mv easyrsvp-ai-team.service /etc/systemd/system/"
        echo "sudo systemctl enable easyrsvp-ai-team.service"
    fi
fi

# Create useful scripts
print_step "Creating utility scripts..."

# Health check script
cat > scripts/health-check.py << 'EOF'
#!/usr/bin/env python3
"""
EasyRSVP AI Team Health Check Script
"""

import requests
import sys
import time

def check_service(name, url, timeout=10):
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code == 200:
            print(f"✅ {name}: Healthy")
            return True
        else:
            print(f"❌ {name}: Unhealthy (Status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ {name}: Unhealthy ({str(e)})")
        return False

def main():
    print("🏥 EasyRSVP AI Team Health Check")
    print("=" * 40)
    
    services = [
        ("n8n", "http://localhost:5678/healthz"),
        ("AI Agents", "http://localhost:8000/health"),
        ("Monitoring", "http://localhost:3000/health"),
        ("Prometheus", "http://localhost:9090/-/healthy"),
        ("Grafana", "http://localhost:3001/api/health"),
    ]
    
    healthy_count = 0
    
    for name, url in services:
        if check_service(name, url):
            healthy_count += 1
        time.sleep(1)
    
    print("=" * 40)
    print(f"Health Score: {healthy_count}/{len(services)}")
    
    if healthy_count == len(services):
        print("🎉 All services are healthy!")
        sys.exit(0)
    else:
        print("⚠️ Some services are unhealthy!")
        sys.exit(1)

if __name__ == "__main__":
    main()
EOF

chmod +x scripts/health-check.py

# Quick start script
cat > quick-start.sh << 'EOF'
#!/bin/bash
# EasyRSVP AI Team Quick Start

echo "🚀 Starting EasyRSVP AI Team..."

# Start services
docker-compose up -d

echo "⏳ Waiting for services to start..."
sleep 30

# Run health check
python3 scripts/health-check.py

echo ""
echo "🎉 EasyRSVP AI Team is ready!"
echo ""
echo "📍 Service URLs:"
echo "  • n8n Workflows:     http://localhost:5678"
echo "  • AI Agents API:     http://localhost:8000"
echo "  • Monitoring:        http://localhost:3000"
echo "  • Prometheus:        http://localhost:9090"
echo "  • Grafana:           http://localhost:3001"
echo ""
echo "📖 Documentation: ./docs/README.md"
echo "🔧 Logs: docker-compose logs -f"
EOF

chmod +x quick-start.sh

print_success "Utility scripts created!"

# Final setup completion
print_step "Running final setup tasks..."

# Build Docker images if Dockerfiles exist
if [ -f "Dockerfile.agents" ]; then
    print_status "Building AI agents Docker image..."
    docker build -f Dockerfile.agents -t easyrsvp-ai-agents .
fi

if [ -f "Dockerfile.monitoring" ]; then
    print_status "Building monitoring Docker image..."
    docker build -f Dockerfile.monitoring -t easyrsvp-monitoring .
fi

# Set correct permissions
chmod +x scripts/*.py scripts/*.sh
chmod 644 config/*

print_success "Setup completed successfully!"

echo ""
echo -e "${GREEN}🎉 EasyRSVP AI Team Setup Complete!${NC}"
echo ""
echo -e "${CYAN}Next Steps:${NC}"
echo "1. 📝 Edit .env file with your API keys and configuration"
echo "2. 🚀 Run: ./quick-start.sh"
echo "3. 🌐 Access n8n at: http://localhost:5678"
echo "4. 📊 Access monitoring at: http://localhost:3000"
echo "5. 📖 Read the documentation in ./docs/"
echo ""
echo -e "${YELLOW}Important:${NC}"
echo "• Make sure to configure your API keys (OpenAI, Slack, etc.)"
echo "• Review security settings in .env before production use"
echo "• Run 'python3 scripts/health-check.py' to verify all services"
echo ""
echo -e "${PURPLE}Support:${NC}"
echo "• Documentation: ./docs/README.md"
echo "• Issues: https://github.com/easyrsvp/ai-team/issues"
echo "• Email: support@easyrsvp.com"
echo ""

# Deactivate virtual environment
deactivate 