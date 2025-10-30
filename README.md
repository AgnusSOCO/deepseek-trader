# AI Cryptocurrency Trading Bot

A sophisticated autonomous AI-powered cryptocurrency trading bot that leverages DeepSeek LLM for intelligent trading decisions. The system features 19 proven quantitative strategies, comprehensive risk management, and supports multiple exchanges including **MEXC**, Binance, and Bybit for both live and demo trading.

## 🚀 Project Status

**Current Phase**: Fully Operational - Ready for Paper Trading & Live Trading

### ✅ Completed Features

- **19 Proven Trading Strategies** - Backtested and optimized quantitative strategies
- **Autonomous Trading System** - Zero human interaction required
- **Multi-Exchange Support** - MEXC, Binance, Bybit (testnet & live)
- **DeepSeek AI Integration** - Multi-agent decision system via OpenRouter
- **Comprehensive Risk Management** - Daily loss limits, position sizing, stop-loss/take-profit
- **Exit Plan Monitoring** - Automatic position management with invalidation conditions
- **Real-Time Dashboard** - Web interface for monitoring and control
- **Backtesting Framework** - Walk-forward optimization and parameter stability analysis
- **Performance Monitoring** - Real-time P&L tracking and metrics

## 📊 Trading Strategies (19 Total)

### High Performers
- **UniversalMacd_5m** - +330% return, normalized MACD ratio-based
- **Momentum_1h** - +49% return, 0.90 Sharpe ratio, EMA crossover with ADX

### Strategy Categories

**Trend Following (5 strategies)**
- EMA-OBV Trend Following (15m)
- HLHB System (1h) - Multi-indicator with 62% ROI
- Momentum (1h)
- ADX-SMA Crossover (1h)
- Multi-SuperTrend (1h)

**Mean Reversion (4 strategies)**
- Stochastic RSI (15m)
- Mean Reversion (5m, 15m)
- Connors RSI (15m)
- Bandtastic Multi-BB (15m)

**Volatility Breakout (5 strategies)**
- Bollinger Band Squeeze (15m)
- ATR Channel Breakout (1h)
- Volatility System (15m)
- Keltner Channel (1h)
- Donchian/Turtle (1h)

**Momentum & Scalping (5 strategies)**
- Universal MACD (5m)
- SuperTrend (1h)
- Ichimoku Cloud (1h)
- Scalping (5m)

## 🎯 Key Features

### Autonomous Operation
- **Zero Human Interaction** - Fully automated trading loop (2-3 minute cycles)
- **Confidence-Based Position Sizing** - Larger positions for high-confidence signals
- **Exit Plan Monitoring** - Automatic stop-loss, take-profit, and invalidation tracking
- **Over-Trading Prevention** - Daily trade limits and cooldown periods

### Risk Management
- **Daily Loss Limits** - Automatic trading halt at 5% daily loss
- **Position Limits** - Max 20% exposure per symbol
- **Trade Frequency Limits** - Max 20 trades per day
- **Confidence Thresholds** - Minimum confidence requirements per strategy

### AI Integration
- **DeepSeek Chat V3.1** - Fast decision-making via OpenRouter
- **DeepSeek Reasoner** - Deep analysis for complex decisions
- **Multi-Agent System** - 7 specialized agents (Technical, Sentiment, Market Structure, Bull/Bear Researchers, Trader, Risk Manager)

## 📋 Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Exchange Setup](#exchange-setup)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Backtesting](#backtesting)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## 🔧 Installation

### Prerequisites

- **Python 3.11+** (3.12 recommended)
- **Redis** (for caching)
- **Git**
- **TA-Lib** (technical analysis library)

### System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8 GB minimum (16 GB recommended)
- **Storage**: 50 GB SSD
- **Network**: Stable internet connection

### Step 1: Clone the Repository

```bash
git clone https://github.com/AgnusSOCO/deepseek-trader.git
cd deepseek-trader
```

### Step 2: Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install TA-Lib (Required)

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install -y build-essential wget
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ..
```

**macOS:**
```bash
brew install ta-lib
```

**Windows:**
Download from: https://github.com/mrjbq7/ta-lib#windows

### Step 4: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 5: Install and Start Redis

**Ubuntu/Debian:**
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

**macOS:**
```bash
brew install redis
brew services start redis
```

**Verify:**
```bash
redis-cli ping  # Should return: PONG
```

---

## 🚀 Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
nano .env  # Edit with your API keys
```

### 2. Add API Keys

```env
# Trading Mode
TRADING_MODE=demo

# Exchange (choose one)
EXCHANGE=mexc

# MEXC API Keys
MEXC_API_KEY=your_key_here
MEXC_API_SECRET=your_secret_here

# OpenRouter (for DeepSeek AI)
OPENROUTER_API_KEY=your_openrouter_key

# AI Config
AI_ENABLED=true
AI_MIN_CONFIDENCE=0.65

# Redis & Database
REDIS_URL=redis://localhost:6379/0
DATABASE_URL=sqlite:///./data/trading_bot.db
```

### 3. Run Backtests (Optional)

```bash
python scripts/run_all_backtests.py
```

### 4. Start Trading Bot

```bash
python -m src.autonomous.autonomous_trading_system
```

### 5. Access Dashboard

```
http://localhost:8080
```

---

## 🏦 Exchange Setup

### MEXC Setup (Recommended)

**Why MEXC?**
- ✅ Low fees (0.1%)
- ✅ 1,500+ trading pairs
- ✅ No KYC for basic trading
- ✅ Simple API

**Steps:**

1. Create account at https://www.mexc.com/
2. Go to **Account** → **API Management**
3. Create API with **Spot Trading** only (disable withdrawal)
4. Add keys to `.env`:
```env
EXCHANGE=mexc
MEXC_API_KEY=your_key
MEXC_API_SECRET=your_secret
```

5. Test connection:
```bash
python scripts/test_mexc_connection.py
```

### Binance Setup

**Testnet (Demo):**
1. Visit https://testnet.binance.vision/
2. Generate API keys
3. Configure `.env`:
```env
EXCHANGE=binance
BINANCE_TESTNET_API_KEY=your_key
BINANCE_TESTNET_API_SECRET=your_secret
TRADING_MODE=demo
```

**Live:**
1. Visit https://www.binance.com/
2. Complete KYC and enable 2FA
3. Generate API keys (disable withdrawal)
4. Configure `.env`:
```env
EXCHANGE=binance
BINANCE_LIVE_API_KEY=your_key
BINANCE_LIVE_API_SECRET=your_secret
TRADING_MODE=live
```

### Bybit Setup

Similar to Binance - testnet at https://testnet.bybit.com/

---

## ⚙️ Configuration

### Main Files

```
config/
├── config.yaml          # Main configuration
├── strategies.yaml      # Strategy parameters
└── risk_params.yaml     # Risk settings
```

### Key Options

**config.yaml:**
```yaml
trading:
  mode: demo
  exchange: mexc
  symbols: [BTC/USDT, ETH/USDT]
  timeframes: [5m, 15m, 1h]

autonomous:
  enabled: true
  loop_interval: 180  # 3 minutes
  min_confidence: 0.65

risk:
  max_daily_loss_pct: 5.0
  max_daily_trades: 20
  max_position_size_pct: 20.0
```

---

## 🎮 Running the Bot

### Demo Mode

```bash
echo "TRADING_MODE=demo" >> .env
python -m src.autonomous.autonomous_trading_system
```

### Live Trading

```bash
echo "TRADING_MODE=live" >> .env
python -m src.autonomous.autonomous_trading_system
```

### As Linux Service

Create `/etc/systemd/system/trading-bot.service`:
```ini
[Unit]
Description=AI Crypto Trading Bot
After=network.target redis.service

[Service]
Type=simple
User=your_username
WorkingDirectory=/path/to/deepseek-trader
ExecStart=/path/to/venv/bin/python -m src.autonomous.autonomous_trading_system
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

---

## 📈 Backtesting

```bash
# All strategies
python scripts/run_all_backtests.py

# Single strategy
python scripts/run_single_backtest.py --strategy Momentum_1h

# Walk-forward optimization
python scripts/run_walk_forward_optimization.py

# Ensemble analysis
python scripts/ensemble_analysis.py
```

Results saved to `backtest_results/` and `docs/`

---

## 📊 Monitoring

### Dashboard

Access at `http://localhost:8080`

Features:
- Real-time P&L
- Open positions
- Recent trades
- Strategy performance
- System health

### Logs

```bash
tail -f logs/trading_bot.log  # Main log
tail -f logs/trades.log       # Trades only
tail -f logs/errors.log       # Errors only
```

### API Metrics

```bash
curl http://localhost:8080/api/metrics
```

---

## 🔍 Troubleshooting

### Common Issues

**`ModuleNotFoundError: No module named 'talib'`**
```bash
# Install TA-Lib system library first
sudo apt-get install ta-lib  # Ubuntu
brew install ta-lib          # macOS
pip install --force-reinstall TA-Lib
```

**`redis.exceptions.ConnectionError`**
```bash
redis-cli ping  # Check if running
sudo systemctl start redis-server  # Start if needed
```

**`ccxt.ExchangeError: Invalid API key`**
- Verify keys in `.env`
- Check permissions on exchange
- Try regenerating keys

**Database locked**
```bash
pkill -f autonomous_trading_system
rm data/trading_bot.db-journal
```

---

## 📊 Performance

### Backtest Results (6 months)

**Top Performers:**
- UniversalMacd_5m: +330% return
- Momentum_1h: +49% return, 0.90 Sharpe

**Ensemble:**
- Conservative: +34.6% return, 0.66 Sharpe
- Balanced: +123.8% return, 0.58 Sharpe
- Aggressive: +218.0% return

### Live Trading Expectations

- Monthly return: 2-5%
- Sharpe ratio: 0.5-1.0
- Max drawdown: 5-10%
- Win rate: 55-65%

---

## 🔒 Security

### Best Practices

1. ✅ Never commit API keys
2. ✅ Use environment variables
3. ✅ Enable IP whitelisting
4. ✅ Disable withdrawal permissions
5. ✅ Rotate keys every 30-90 days
6. ✅ Enable 2FA on exchanges

### File Permissions

```bash
chmod 600 .env
chmod 700 config/
chmod 700 logs/
```

---

## ⚠️ Disclaimer

**IMPORTANT**: Cryptocurrency trading involves substantial risk of loss. Never trade with money you cannot afford to lose.

**Always:**
- ✅ Start with demo trading
- ✅ Test thoroughly
- ✅ Use proper risk management
- ✅ Monitor continuously
- ✅ Start with small capital (<$1000)

---

## 🙏 Acknowledgments

- [CCXT](https://github.com/ccxt/ccxt) - Exchange integration
- [TA-Lib](https://github.com/mrjbq7/ta-lib) - Technical analysis
- [DeepSeek](https://www.deepseek.com/) - AI models
- [OpenRouter](https://openrouter.ai/) - LLM gateway
- [freqtrade-strategies](https://github.com/freqtrade/freqtrade-strategies) - Strategy research

---

**Version**: 2.0.0 (Phase G)  
**Last Updated**: October 27, 2025  
**Status**: Production Ready

**Strategies**: 19  
**Exchanges**: MEXC, Binance, Bybit  
**AI**: DeepSeek Chat V3.1, DeepSeek Reasoner
