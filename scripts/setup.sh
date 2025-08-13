#!/bin/bash

# =============================================================================
# Web Scraper Platform - Setup Script
# =============================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Check system requirements
check_requirements() {
    log "Checking system requirements..."
    
    # Check Python version
    if command_exists python3; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        log "Python version: $PYTHON_VERSION"
        
        # Check if Python 3.11+
        if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)'; then
            success "Python 3.11+ detected"
        else
            error "Python 3.11+ required. Current version: $PYTHON_VERSION"
            exit 1
        fi
    else
        error "Python 3 not found. Please install Python 3.11+"
        exit 1
    fi
    
    # Check Docker
    if command_exists docker; then
        success "Docker detected"
    else
        warn "Docker not found. Manual installation will be used."
    fi
    
    # Check Docker Compose
    if command_exists docker-compose || docker compose version >/dev/null 2>&1; then
        success "Docker Compose detected"
    else
        warn "Docker Compose not found."
    fi
    
    # Check Git
    if command_exists git; then
        success "Git detected"
    else
        error "Git is required but not found"
        exit 1
    fi
    
    # Check Node.js (for frontend)
    if command_exists node; then
        NODE_VERSION=$(node --version)
        log "Node.js version: $NODE_VERSION"
        success "Node.js detected"
    else
        warn "Node.js not found. Frontend development will not be available."
    fi
}

# Setup environment file
setup_env() {
    log "Setting up environment configuration..."
    
    if [ -f ".env" ]; then
        warn ".env file already exists"
        read -p "Do you want to overwrite it? [y/N]: " -r
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log "Keeping existing .env file"
            return
        fi
    fi
    
    cp .env.example .env
    
    # Generate secret key
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
    sed -i.bak "s/your-super-secret-key-change-this-in-production/$SECRET_KEY/" .env && rm .env.bak
    
    success "Environment file created with generated secret key"
    
    # Prompt for API keys
    echo
    log "Optional: Configure AI API keys for enhanced features"
    read -p "OpenAI API Key (press Enter to skip): " openai_key
    if [ ! -z "$openai_key" ]; then
        sed -i.bak "s/sk-your-openai-api-key-here/$openai_key/" .env && rm .env.bak
        success "OpenAI API key configured"
    fi
    
    read -p "Anthropic API Key (press Enter to skip): " anthropic_key
    if [ ! -z "$anthropic_key" ]; then
        sed -i.bak "s/your-anthropic-api-key-here/$anthropic_key/" .env && rm .env.bak
        success "Anthropic API key configured"
    fi
}

# Install Python dependencies
install_python_deps() {
    log "Installing Python dependencies..."
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "venv" ]; then
        log "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    # Activate virtual environment
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip
    
    # Install requirements
    pip install -r requirements.txt
    
    success "Python dependencies installed"
}

# Install Playwright browsers
install_playwright() {
    log "Installing Playwright browsers..."
    
    source venv/bin/activate
    
    # Install browsers
    playwright install chromium
    playwright install-deps chromium
    
    success "Playwright browsers installed"
}

# Setup database
setup_database() {
    log "Setting up database..."
    
    # Check if PostgreSQL is running
    if command_exists pg_isready; then
        if pg_isready -q; then
            log "PostgreSQL is running"
            
            # Create database
            read -p "Create database 'webscraper'? [Y/n]: " -r
            if [[ $REPLY =~ ^[Nn]$ ]]; then
                log "Skipping database creation"
            else
                createdb webscraper 2>/dev/null || log "Database might already exist"
                success "Database created"
            fi
        else
            warn "PostgreSQL is not running. Please start PostgreSQL service."
        fi
    else
        warn "PostgreSQL not found. Please install PostgreSQL."
        log "On Ubuntu/Debian: sudo apt-get install postgresql postgresql-contrib"
        log "On macOS: brew install postgresql"
        log "On RHEL/CentOS: sudo yum install postgresql-server postgresql-contrib"
    fi
}

# Setup Redis
setup_redis() {
    log "Checking Redis setup..."
    
    if command_exists redis-cli; then
        if redis-cli ping >/dev/null 2>&1; then
            success "Redis is running and accessible"
        else
            warn "Redis is not running. Please start Redis service."
        fi
    else
        warn "Redis not found. Please install Redis."
        log "On Ubuntu/Debian: sudo apt-get install redis-server"
        log "On macOS: brew install redis"
        log "On RHEL/CentOS: sudo yum install redis"
    fi
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    source venv/bin/activate
    
    # Check if alembic is configured
    if [ -f "alembic.ini" ]; then
        alembic upgrade head
        success "Database migrations completed"
    else
        warn "Alembic not configured. Skipping migrations."
    fi
}

# Setup directories
setup_directories() {
    log "Creating required directories..."
    
    mkdir -p logs
    mkdir -p data/uploads
    mkdir -p data/exports
    mkdir -p monitoring/prometheus
    mkdir -p monitoring/grafana/dashboards
    mkdir -p nginx
    
    success "Directories created"
}

# Docker setup
setup_docker() {
    if command_exists docker && (command_exists docker-compose || docker compose version >/dev/null 2>&1); then
        log "Setting up Docker environment..."
        
        read -p "Use Docker for setup? [Y/n]: " -r
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            return
        fi
        
        # Build and start services
        if command_exists docker-compose; then
            docker-compose build
            docker-compose up -d postgres redis
        else
            docker compose build
            docker compose up -d postgres redis
        fi
        
        # Wait for services
        log "Waiting for services to start..."
        sleep 10
        
        # Run migrations in Docker
        if command_exists docker-compose; then
            docker-compose run --rm web alembic upgrade head
        else
            docker compose run --rm web alembic upgrade head
        fi
        
        success "Docker environment ready"
        
        log "Services available at:"
        log "  - API: http://localhost:8000"
        log "  - Docs: http://localhost:8000/api/docs"
        log "  - Flower: http://localhost:5555"
        log "  - Grafana: http://localhost:3000"
        
        return 0
    fi
    
    return 1
}

# Manual setup
setup_manual() {
    log "Performing manual setup..."
    
    install_python_deps
    install_playwright
    setup_database
    setup_redis
    run_migrations
    
    success "Manual setup completed"
    
    log "To start the application:"
    log "  source venv/bin/activate"
    log "  uvicorn app.main:app --reload"
    log ""
    log "Application will be available at http://localhost:8000"
}

# Main setup function
main() {
    echo "================================"
    echo "  Web Scraper Platform Setup"
    echo "================================"
    echo
    
    check_requirements
    setup_directories
    setup_env
    
    # Try Docker setup first, fall back to manual
    if ! setup_docker; then
        setup_manual
    fi
    
    echo
    success "Setup completed successfully!"
    echo
    log "Next steps:"
    log "1. Review the .env file and update any required settings"
    log "2. Configure your AI API keys for enhanced features"
    log "3. Start the application and visit the documentation"
    log ""
    log "For help, see the README.md file or visit the docs"
    echo
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --docker-only)
            setup_docker
            exit $?
            ;;
        --manual-only)
            check_requirements
            setup_directories
            setup_env
            setup_manual
            exit 0
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --docker-only   Use Docker setup only"
            echo "  --manual-only   Use manual setup only"
            echo "  --help, -h      Show this help message"
            exit 0
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
    shift
done

# Run main setup
main