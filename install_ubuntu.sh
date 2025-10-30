#!/bin/bash

#
#
#
#

set -e  # Exit on error

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

if [ "$EUID" -ne 0 ]; then 
    log_error "Please run as root (use sudo)"
    exit 1
fi

ACTUAL_USER="${SUDO_USER:-$USER}"
ACTUAL_HOME=$(eval echo ~$ACTUAL_USER)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$SCRIPT_DIR"

log_info "Starting AI Trading Bot installation on Ubuntu 22.04..."
log_info "Project directory: $PROJECT_DIR"
log_info "Installing for user: $ACTUAL_USER"
echo ""


log_info "Step 1/9: Updating system packages..."
apt-get update -qq
log_success "System packages updated"
echo ""


log_info "Step 2/9: Installing system dependencies..."

log_info "Installing build tools..."
apt-get install -y -qq \
    build-essential \
    wget \
    curl \
    git \
    software-properties-common \
    ca-certificates \
    gnupg \
    lsb-release

log_info "Installing Python 3.11..."
add-apt-repository -y ppa:deadsnakes/ppa
apt-get update -qq
apt-get install -y -qq \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip

PYTHON_VERSION=$(python3.11 --version)
log_success "Python installed: $PYTHON_VERSION"

log_success "System dependencies installed"
echo ""


log_info "Step 3/9: Installing Redis..."

apt-get install -y -qq redis-server

log_info "Configuring Redis..."
sed -i 's/supervised no/supervised systemd/' /etc/redis/redis.conf

systemctl enable redis-server
systemctl start redis-server

if redis-cli ping | grep -q "PONG"; then
    log_success "Redis installed and running"
else
    log_error "Redis installation failed"
    exit 1
fi

echo ""


log_info "Step 4/9: Installing TA-Lib..."

cd /tmp

if [ ! -f "ta-lib-0.4.0-src.tar.gz" ]; then
    log_info "Downloading TA-Lib..."
    wget -q http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
fi

log_info "Building TA-Lib (this may take a few minutes)..."
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr > /dev/null 2>&1
make > /dev/null 2>&1
make install > /dev/null 2>&1

ldconfig

if [ -f "/usr/lib/libta_lib.so" ]; then
    log_success "TA-Lib installed successfully"
else
    log_error "TA-Lib installation failed"
    exit 1
fi

cd "$PROJECT_DIR"
echo ""


log_info "Step 5/9: Creating Python virtual environment..."

if [ -d "venv" ]; then
    log_warning "Removing old virtual environment..."
    rm -rf venv
fi

sudo -u $ACTUAL_USER python3.11 -m venv venv

log_info "Upgrading pip..."
sudo -u $ACTUAL_USER venv/bin/pip install --upgrade pip setuptools wheel -q

log_success "Virtual environment created"
echo ""


log_info "Step 6/9: Installing Python packages..."

if [ ! -f "requirements.txt" ]; then
    log_error "requirements.txt not found!"
    exit 1
fi

log_info "This may take several minutes..."
sudo -u $ACTUAL_USER venv/bin/pip install -r requirements.txt -q

log_info "Verifying package installation..."
sudo -u $ACTUAL_USER venv/bin/python -c "import ccxt, talib, redis, pandas, numpy" 2>/dev/null

if [ $? -eq 0 ]; then
    log_success "All Python packages installed successfully"
else
    log_error "Some Python packages failed to install"
    exit 1
fi

echo ""


log_info "Step 7/9: Setting up configuration files..."

log_info "Creating directories..."
sudo -u $ACTUAL_USER mkdir -p data logs backtest_data backtest_results

if [ ! -f ".env" ]; then
    log_info "Creating .env file with interactive configuration..."
    echo ""
    echo "================================================================================"
    echo "                    CONFIGURATION SETUP"
    echo "================================================================================"
    echo ""
    echo "This script will help you configure the trading bot."
    echo "Press Enter to skip optional fields."
    echo ""
    
    echo "1. Trading Mode"
    echo "   - demo: Paper trading (recommended for testing)"
    echo "   - live: Real trading with real money"
    read -p "   Select mode [demo]: " TRADING_MODE
    TRADING_MODE=${TRADING_MODE:-demo}
    echo ""
    
    echo "2. Exchange Selection"
    echo "   - mexc: MEXC (recommended - low fees, no KYC)"
    echo "   - binance: Binance"
    echo "   - bybit: Bybit"
    read -p "   Select exchange [mexc]: " EXCHANGE
    EXCHANGE=${EXCHANGE:-mexc}
    echo ""
    
    if [ "$EXCHANGE" = "mexc" ]; then
        echo "3. MEXC API Keys"
        echo "   Get your keys from: https://www.mexc.com/"
        echo "   Account → API Management → Create API"
        echo "   Enable: Spot Trading (Read & Trade)"
        echo "   Disable: Withdrawal (for security)"
        read -p "   MEXC API Key: " MEXC_API_KEY
        read -p "   MEXC API Secret: " MEXC_API_SECRET
        BINANCE_TESTNET_API_KEY="your_binance_testnet_api_key_here"
        BINANCE_TESTNET_API_SECRET="your_binance_testnet_api_secret_here"
        BINANCE_LIVE_API_KEY="your_binance_live_api_key_here"
        BINANCE_LIVE_API_SECRET="your_binance_live_api_secret_here"
        BYBIT_TESTNET_API_KEY="your_bybit_testnet_api_key_here"
        BYBIT_TESTNET_API_SECRET="your_bybit_testnet_api_secret_here"
        BYBIT_LIVE_API_KEY="your_bybit_live_api_key_here"
        BYBIT_LIVE_API_SECRET="your_bybit_live_api_secret_here"
    elif [ "$EXCHANGE" = "binance" ]; then
        echo "3. Binance API Keys"
        if [ "$TRADING_MODE" = "demo" ]; then
            echo "   Get testnet keys from: https://testnet.binance.vision/"
            read -p "   Binance Testnet API Key: " BINANCE_TESTNET_API_KEY
            read -p "   Binance Testnet API Secret: " BINANCE_TESTNET_API_SECRET
            BINANCE_LIVE_API_KEY="your_binance_live_api_key_here"
            BINANCE_LIVE_API_SECRET="your_binance_live_api_secret_here"
        else
            echo "   Get live keys from: https://www.binance.com/"
            echo "   IMPORTANT: Disable withdrawal permissions!"
            read -p "   Binance Live API Key: " BINANCE_LIVE_API_KEY
            read -p "   Binance Live API Secret: " BINANCE_LIVE_API_SECRET
            BINANCE_TESTNET_API_KEY="your_binance_testnet_api_key_here"
            BINANCE_TESTNET_API_SECRET="your_binance_testnet_api_secret_here"
        fi
        MEXC_API_KEY="your_mexc_api_key_here"
        MEXC_API_SECRET="your_mexc_api_secret_here"
        BYBIT_TESTNET_API_KEY="your_bybit_testnet_api_key_here"
        BYBIT_TESTNET_API_SECRET="your_bybit_testnet_api_secret_here"
        BYBIT_LIVE_API_KEY="your_bybit_live_api_key_here"
        BYBIT_LIVE_API_SECRET="your_bybit_live_api_secret_here"
    else  # bybit
        echo "3. Bybit API Keys"
        if [ "$TRADING_MODE" = "demo" ]; then
            echo "   Get testnet keys from: https://testnet.bybit.com/"
            read -p "   Bybit Testnet API Key: " BYBIT_TESTNET_API_KEY
            read -p "   Bybit Testnet API Secret: " BYBIT_TESTNET_API_SECRET
            BYBIT_LIVE_API_KEY="your_bybit_live_api_key_here"
            BYBIT_LIVE_API_SECRET="your_bybit_live_api_secret_here"
        else
            echo "   Get live keys from: https://www.bybit.com/"
            read -p "   Bybit Live API Key: " BYBIT_LIVE_API_KEY
            read -p "   Bybit Live API Secret: " BYBIT_LIVE_API_SECRET
            BYBIT_TESTNET_API_KEY="your_bybit_testnet_api_key_here"
            BYBIT_TESTNET_API_SECRET="your_bybit_testnet_api_secret_here"
        fi
        MEXC_API_KEY="your_mexc_api_key_here"
        MEXC_API_SECRET="your_mexc_api_secret_here"
        BINANCE_TESTNET_API_KEY="your_binance_testnet_api_key_here"
        BINANCE_TESTNET_API_SECRET="your_binance_testnet_api_secret_here"
        BINANCE_LIVE_API_KEY="your_binance_live_api_key_here"
        BINANCE_LIVE_API_SECRET="your_binance_live_api_secret_here"
    fi
    echo ""
    
    echo "4. OpenRouter API Key (for DeepSeek AI)"
    echo "   Get your key from: https://openrouter.ai/"
    echo "   This enables AI-powered trading decisions"
    read -p "   OpenRouter API Key (optional): " OPENROUTER_API_KEY
    OPENROUTER_API_KEY=${OPENROUTER_API_KEY:-your_openrouter_api_key_here}
    echo ""
    
    echo "5. AI Configuration"
    read -p "   Enable AI trading? [true]: " AI_ENABLED
    AI_ENABLED=${AI_ENABLED:-true}
    read -p "   AI minimum confidence (0.0-1.0) [0.65]: " AI_MIN_CONFIDENCE
    AI_MIN_CONFIDENCE=${AI_MIN_CONFIDENCE:-0.65}
    echo ""
    
    echo "6. Trading Configuration"
    read -p "   Trading symbols (comma-separated) [BTC/USDT,ETH/USDT]: " TRADING_SYMBOLS
    TRADING_SYMBOLS=${TRADING_SYMBOLS:-BTC/USDT,ETH/USDT}
    read -p "   Initial capital for demo mode [10000]: " INITIAL_CAPITAL
    INITIAL_CAPITAL=${INITIAL_CAPITAL:-10000}
    echo ""
    
    echo "7. Risk Management"
    read -p "   Max daily loss percentage [5.0]: " MAX_DAILY_LOSS_PCT
    MAX_DAILY_LOSS_PCT=${MAX_DAILY_LOSS_PCT:-5.0}
    read -p "   Max daily trades [20]: " MAX_DAILY_TRADES
    MAX_DAILY_TRADES=${MAX_DAILY_TRADES:-20}
    read -p "   Max position size percentage [20.0]: " MAX_POSITION_SIZE_PCT
    MAX_POSITION_SIZE_PCT=${MAX_POSITION_SIZE_PCT:-20.0}
    echo ""
    
    log_info "Generating .env file..."
    
    cat > .env << EOF

TRADING_MODE=$TRADING_MODE

EXCHANGE=$EXCHANGE

MEXC_API_KEY=$MEXC_API_KEY
MEXC_API_SECRET=$MEXC_API_SECRET

BINANCE_TESTNET_API_KEY=$BINANCE_TESTNET_API_KEY
BINANCE_TESTNET_API_SECRET=$BINANCE_TESTNET_API_SECRET
BINANCE_LIVE_API_KEY=$BINANCE_LIVE_API_KEY
BINANCE_LIVE_API_SECRET=$BINANCE_LIVE_API_SECRET

BYBIT_TESTNET_API_KEY=$BYBIT_TESTNET_API_KEY
BYBIT_TESTNET_API_SECRET=$BYBIT_TESTNET_API_SECRET
BYBIT_LIVE_API_KEY=$BYBIT_LIVE_API_KEY
BYBIT_LIVE_API_SECRET=$BYBIT_LIVE_API_SECRET

OPENROUTER_API_KEY=$OPENROUTER_API_KEY

AI_ENABLED=$AI_ENABLED
AI_MIN_CONFIDENCE=$AI_MIN_CONFIDENCE
AI_MAX_COST_PER_DECISION=0.10

REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=
REDIS_MAX_CONNECTIONS=10

DATABASE_URL=sqlite:///./data/trading_bot.db

LOG_LEVEL=INFO
LOG_DIR=./logs
LOG_MAX_SIZE=10485760
LOG_BACKUP_COUNT=10

TRADING_SYMBOLS=$TRADING_SYMBOLS
TRADING_TIMEFRAMES=5m,15m,1h
INITIAL_CAPITAL=$INITIAL_CAPITAL

MAX_DAILY_LOSS_PCT=$MAX_DAILY_LOSS_PCT
MAX_DAILY_TRADES=$MAX_DAILY_TRADES
MAX_POSITION_SIZE_PCT=$MAX_POSITION_SIZE_PCT
DEFAULT_STOP_LOSS_PCT=2.0
DEFAULT_TAKE_PROFIT_PCT=4.0

AUTONOMOUS_ENABLED=true
AUTONOMOUS_LOOP_INTERVAL=180
AUTONOMOUS_MIN_CONFIDENCE=0.65

DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8080
DASHBOARD_AUTO_REFRESH_SEC=5

TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
DISCORD_WEBHOOK_URL=
EMAIL_ENABLED=false
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_FROM=
EMAIL_TO=
EMAIL_PASSWORD=

DEBUG_MODE=false
PAPER_TRADING=false
DATA_RETENTION_DAYS=90
BACKTEST_DATA_DIR=./backtest_data
RESULTS_DIR=./backtest_results
EOF

    chown $ACTUAL_USER:$ACTUAL_USER .env
    log_success ".env file created with your configuration"
else
    log_info ".env file already exists, skipping configuration..."
fi

chown -R $ACTUAL_USER:$ACTUAL_USER "$PROJECT_DIR"
chmod 600 .env
chmod 700 config/ logs/ data/

log_success "Configuration files setup complete"
echo ""


log_info "Step 8/9: Initializing database..."

sudo -u $ACTUAL_USER mkdir -p data

log_success "Database initialization complete"
echo ""


log_info "Step 9/9: Running verification tests..."

log_info "Testing Python imports..."
sudo -u $ACTUAL_USER venv/bin/python -c "
import sys
import ccxt
import talib
import redis
import pandas
import numpy
import yaml
from loguru import logger
print('✓ All imports successful')
" 2>/dev/null

if [ $? -eq 0 ]; then
    log_success "Python imports test passed"
else
    log_error "Python imports test failed"
    exit 1
fi

log_info "Testing Redis connection..."
if redis-cli ping | grep -q "PONG"; then
    log_success "Redis connection test passed"
else
    log_error "Redis connection test failed"
    exit 1
fi

log_info "Testing TA-Lib..."
sudo -u $ACTUAL_USER venv/bin/python -c "
import talib
import numpy as np
close = np.random.random(100)
sma = talib.SMA(close, timeperiod=20)
print('✓ TA-Lib working')
" 2>/dev/null

if [ $? -eq 0 ]; then
    log_success "TA-Lib test passed"
else
    log_error "TA-Lib test failed"
    exit 1
fi

echo ""
log_success "All verification tests passed!"
echo ""


read -p "Do you want to set up the bot as a systemd service? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Setting up systemd service..."
    
    cat > /etc/systemd/system/trading-bot.service << EOF
[Unit]
Description=AI Cryptocurrency Trading Bot
After=network.target redis-server.service
Requires=redis-server.service

[Service]
Type=simple
User=$ACTUAL_USER
WorkingDirectory=$PROJECT_DIR
Environment="PATH=$PROJECT_DIR/venv/bin"
ExecStart=$PROJECT_DIR/venv/bin/python -m src.autonomous.autonomous_trading_system
Restart=always
RestartSec=10
StandardOutput=append:$PROJECT_DIR/logs/systemd.log
StandardError=append:$PROJECT_DIR/logs/systemd-error.log

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    
    log_success "Systemd service created"
    log_info "To enable and start the service:"
    log_info "  sudo systemctl enable trading-bot"
    log_info "  sudo systemctl start trading-bot"
    log_info "To check status:"
    log_info "  sudo systemctl status trading-bot"
    echo ""
fi


echo ""
echo "================================================================================"
log_success "Installation completed successfully!"
echo "================================================================================"
echo ""
echo "Your trading bot is now fully configured and ready to use!"
echo ""
echo "Configuration Summary:"
echo "  - Trading Mode: $TRADING_MODE"
echo "  - Exchange: $EXCHANGE"
echo "  - AI Enabled: $AI_ENABLED"
echo "  - Initial Capital: \$$INITIAL_CAPITAL"
echo ""
echo "Next steps:"
echo ""
echo "1. Review your configuration (optional):"
echo "   nano .env"
echo ""
echo "2. Test exchange connection:"
if [ "$EXCHANGE" = "mexc" ]; then
    echo "   sudo -u $ACTUAL_USER $PROJECT_DIR/venv/bin/python scripts/test_mexc_connection.py"
else
    echo "   sudo -u $ACTUAL_USER $PROJECT_DIR/venv/bin/python -c 'import ccxt; print(ccxt.$EXCHANGE())'"
fi
echo ""
echo "3. Run backtests (optional but recommended):"
echo "   sudo -u $ACTUAL_USER $PROJECT_DIR/venv/bin/python scripts/run_all_backtests.py"
echo ""
echo "4. Start the trading bot:"
echo "   sudo -u $ACTUAL_USER $PROJECT_DIR/venv/bin/python -m src.autonomous.autonomous_trading_system"
echo ""
echo "5. Access the dashboard:"
echo "   http://localhost:8080"
echo ""
echo "For more information, see README.md"
echo ""
echo "================================================================================"
echo ""

cat > "$PROJECT_DIR/INSTALLATION_INFO.txt" << EOF
Installation completed: $(date)
Python version: $(python3.11 --version)
Redis version: $(redis-server --version | head -n1)
TA-Lib: Installed at /usr/lib/libta_lib.so
Virtual environment: $PROJECT_DIR/venv
User: $ACTUAL_USER
Project directory: $PROJECT_DIR

Systemd service: $([ -f /etc/systemd/system/trading-bot.service ] && echo "Installed" || echo "Not installed")
EOF

chown $ACTUAL_USER:$ACTUAL_USER "$PROJECT_DIR/INSTALLATION_INFO.txt"

log_success "Installation info saved to INSTALLATION_INFO.txt"
echo ""

exit 0
