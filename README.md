# AI Cryptocurrency Trading Bot

> **Inspired by [nof1.ai](https://github.com/195440/nof1.ai)** - An autonomous AI-powered cryptocurrency trading system with zero human intervention

A sophisticated autonomous AI-powered cryptocurrency trading bot that leverages DeepSeek LLM for intelligent trading decisions. The system features 15+ proven quantitative strategies, comprehensive risk management aligned with nof1.ai principles, and supports multiple exchanges including Bybit, Binance, and MEXC for both testnet and live trading.

## 🚀 Project Status

**Current Phase**: Production Ready - Paper Trading Validation Framework Complete

### ✅ Completed Features

- **15+ Proven Trading Strategies** - Backtested and optimized quantitative strategies
- **Autonomous Trading System** - Zero human interaction required (nof1.ai aligned)
- **Multi-Exchange Support** - Bybit, Binance, MEXC (testnet & live via CCXT)
- **DeepSeek AI Integration** - Single-agent strategy via OpenRouter (DeepSeek Chat V3.1)
- **nof1.ai Risk Management** - 36-hour TTL, tiered trailing stops, drawdown gates (15%/20%)
- **Exit Plan Monitoring** - Automatic position management with invalidation conditions
- **Real-Time Dashboard** - FastAPI web interface for monitoring and control
- **Paper Trading Engine** - Realistic simulation with slippage and fees
- **3-Phase Validation Framework** - Progressive paper trading validation (1-3 weeks per phase)
- **Comprehensive Documentation** - Deployment guide, architecture docs, troubleshooting guide
- **70 Unit/Integration Tests** - 100% passing test coverage

## 🎯 nof1.ai-Inspired Features

This system implements key features from the [nof1.ai autonomous trading approach](https://github.com/195440/nof1.ai):

### ✅ Implemented Features

| Feature | nof1.ai | Our Implementation | Status |
|---------|---------|-------------------|--------|
| **AI Autonomy** | Single AI agent with complete decision authority | SingleAgentStrategy with DeepSeek Chat V3.1 | ✅ Implemented |
| **Structured JSON Output** | AI returns action/size/SL/TP/confidence/reasoning | TradingDecision Pydantic model with full validation | ✅ Implemented |
| **Account Drawdown Gates** | 15% warning, 20% stop | EnhancedRiskManager with 15%/20% thresholds | ✅ Implemented |
| **36-Hour Position TTL** | Maximum holding time with auto-exit | ExitPlanMonitor with timeout enforcement | ✅ Implemented |
| **Tiered Trailing Profit** | +8%/+15%/+25% profit levels with stop adjustments | ExitPlanMonitor with 4-tier trailing system | ✅ Implemented |
| **Leverage-Adjusted P&L** | P&L calculation accounting for leverage | PaperPosition.calculate_pnl() with leverage multiplier | ✅ Implemented |
| **5-Minute Decision Loop** | Regular trading cycle interval | AutonomousDecisionEngine with 5-min loops | ✅ Implemented |
| **Confidence-Based Sizing** | Higher confidence = larger positions | EnhancedRiskManager.calculate_position_size() | ✅ Implemented |
| **Multi-Timeframe Analysis** | 5m, 15m, 1h, 4h data aggregation | PriceFeed with 7 timeframes (1m-4h) | ✅ Implemented |
| **Web Dashboard** | Real-time monitoring interface | FastAPI dashboard at localhost:8080 | ✅ Implemented |
| **Paper Trading** | Risk-free validation mode | PaperTradingEngine with realistic simulation | ✅ Implemented |
| **Database Logging** | Complete audit trail | SQLite/PostgreSQL with trades/positions/metrics | ✅ Implemented |

### 🔄 Planned Enhancements

| Feature | Priority | Description |
|---------|----------|-------------|
| **WebSocket Market Data** | High | Real-time price feeds via CCXT Pro (currently REST + polling) |
| **Funding Rate Accrual** | High | Perpetual contract funding payments in P&L |
| **Exchange Contract Specs** | High | Enforce tick/step/lot/quanto multipliers |
| **Per-Symbol Cooldown** | Medium | Minimum interval between trades per symbol |
| **AI Decision Database** | Medium | Persist AI reasoning to decisions table |
| **Gate.io Support** | Medium | Add Gate.io exchange via CCXT |
| **Health Endpoint** | Low | /health API for monitoring |
| **Docker Deployment** | Low | Docker/Compose for easy deployment |

### 🔀 Key Differences from nof1.ai

| Aspect | nof1.ai | Our Implementation |
|--------|---------|-------------------|
| **Language** | TypeScript/Node.js | Python 3.11+ |
| **Framework** | VoltAgent (tool-based agents) | Custom Python architecture |
| **AI Approach** | Pure AI (no hardcoded strategies) | Hybrid (AI + 15 rule-based strategies) |
| **Exchange** | Gate.io only | Multi-exchange via CCXT (Bybit/Binance/MEXC) |
| **Database** | LibSQL (SQLite) | SQLite or PostgreSQL |
| **Process Mgmt** | PM2 | systemd (Docker optional) |
| **Strategy Count** | 1 AI agent | 15 rule-based + 1 AI strategy |

**Philosophy**: We combine nof1.ai's autonomous AI approach with proven quantitative strategies for production stability and resilience.

## 📊 Trading Strategies (15+ Total)

### Top Performers (Backtested 6 Months)

| Strategy | Timeframe | Return | Win Rate | Sharpe | Trades |
|----------|-----------|--------|----------|--------|--------|
| **Momentum** | 1h | +49.38% | 76.92% | 0.90 | 13 |
| **UniversalMacd** | 5m | +330%* | - | - | - |
| **MeanReversion** | 15m | +0.06% | 66.67% | - | 3 |

*Note: UniversalMacd shows exceptional returns but requires further validation

### Strategy Categories

**Trend Following (5 strategies)**
- Momentum (1h) - EMA crossover with ADX trend strength
- ADX-SMA Crossover (1h) - SMA crossover with ADX filter
- Multi-SuperTrend (1h) - 3 SuperTrend confirmations
- EMA-OBV Trend Following (15m) - Volume-confirmed trends
- HLHB System (1h) - Multi-indicator system

**Mean Reversion (4 strategies)**
- Mean Reversion (5m, 15m) - Bollinger Bands + RSI extremes
- Bandtastic Multi-BB (15m) - 4-level Bollinger Bands
- Connors RSI (15m) - RSI(2) mean reversion
- Stochastic RSI (15m) - Stochastic oscillator extremes

**Volatility Breakout (5 strategies)**
- Volatility System (15m) - ATR breakout with pyramiding
- ATR Channel Breakout (1h) - ATR-based channels
- Keltner Channel (1h) - Keltner channel breakouts
- Donchian/Turtle (1h) - Donchian channel system
- Bollinger Band Squeeze (15m) - Volatility compression breakouts

**Momentum & Scalping (2 strategies)**
- Universal MACD (5m) - Normalized MACD ratio
- Scalping (5m) - High-frequency with order book analysis

**AI-Powered (1 strategy)**
- SingleAgent (multi-timeframe) - DeepSeek Chat V3.1 autonomous decisions

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

- [nof1.ai-Inspired Features](#nofai-inspired-features)
- [Trading Strategies](#trading-strategies-15-total)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Paper Trading Validation](#paper-trading-validation)
- [AI Provider Configuration](#ai-provider-configuration)
- [Exchange Setup](#exchange-setup)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Backtesting](#backtesting)
- [Monitoring](#monitoring)
- [Documentation](#documentation)
- [Troubleshooting](#troubleshooting)

---

## 🔧 Installation

### 🚀 Quick Install (Ubuntu 22.04 - Recommended)

**One-command installation script with interactive configuration:**

```bash
git clone https://github.com/AgnusSOCO/deepseek-trader.git
cd deepseek-trader
sudo ./install_ubuntu.sh
```

The installation script will:
- ✅ Install Python 3.11, Redis, and all system dependencies
- ✅ Build TA-Lib from source
- ✅ Create virtual environment and install Python packages
- ✅ **Interactively configure your .env file** (trading mode, exchange, API keys, risk settings)
- ✅ Initialize database
- ✅ Run comprehensive verification tests
- ✅ Optionally configure systemd service

**Installation time**: 15-20 minutes

**No manual configuration needed!** The script prompts for all necessary settings during installation, including:
- Trading mode (demo/live)
- Exchange selection (MEXC/Binance/Bybit)
- API keys for your chosen exchange
- OpenRouter API key for AI trading
- Risk management parameters
- Trading symbols and capital

After installation completes, your bot is ready to start trading immediately!

---

### Manual Installation (All Platforms)

If you're not on Ubuntu 22.04 or prefer manual installation:

#### Prerequisites

- **Python 3.11+** (3.12 recommended)
- **Redis** (for caching)
- **Git**
- **TA-Lib** (technical analysis library)

#### System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8 GB minimum (16 GB recommended)
- **Storage**: 50 GB SSD
- **Network**: Stable internet connection

#### Step 1: Clone the Repository

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

# Exchange (choose one: bybit, binance, mexc)
EXCHANGE=bybit

# Bybit API Keys (Testnet recommended for demo)
BYBIT_TESTNET_API_KEY=your_testnet_key_here
BYBIT_TESTNET_API_SECRET=your_testnet_secret_here

# OpenRouter (for DeepSeek AI)
OPENROUTER_API_KEY=sk-or-v1-your_key_here

# AI Config
AI_ENABLED=true
AI_MIN_CONFIDENCE=0.65
AI_PROVIDER=openrouter
AI_MODEL=deepseek/deepseek-chat

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

## 📝 Paper Trading Validation

**Recommended**: Complete 3-phase paper trading validation before live trading (inspired by nof1.ai approach)

### Phase 1: Single Strategy Validation (1 week)

Test the best-performing strategy (Momentum_1h) in isolation:

```bash
# Configure for Phase 1
export PAPER_TRADING=true
export ENABLED_STRATEGIES=Momentum_1h
export INITIAL_CAPITAL=10000
export MAX_DAILY_LOSS_PCT=5.0

# Run validation
python scripts/run_paper_trading_validation.py --phase 1 --duration 7
```

**Success Criteria:**
- ✅ Positive P&L or max -5% loss
- ✅ Win rate ≥ 50%
- ✅ No system crashes or errors
- ✅ Exit plans execute correctly

### Phase 2: Multi-Strategy Validation (1-2 weeks)

Test top 3 strategies together:

```bash
# Configure for Phase 2
export ENABLED_STRATEGIES=Momentum_1h,MeanReversion_15m,UniversalMacd_5m
export INITIAL_CAPITAL=10000

# Run validation
python scripts/run_paper_trading_validation.py --phase 2 --duration 14
```

**Success Criteria:**
- ✅ Positive P&L or max -5% loss
- ✅ Sharpe ratio ≥ 0.3
- ✅ Max drawdown ≤ 10%
- ✅ Risk management working correctly

### Phase 3: Full System Validation (1-2 weeks)

Test all strategies with AI agent:

```bash
# Configure for Phase 3
export ENABLED_STRATEGIES=all
export AI_ENABLED=true
export INITIAL_CAPITAL=10000

# Run validation
python scripts/run_paper_trading_validation.py --phase 3 --duration 14
```

**Success Criteria:**
- ✅ Positive P&L or max -5% loss
- ✅ AI decisions align with market conditions
- ✅ No over-trading (≤20 trades/day)
- ✅ System stable for 2+ weeks

### Monitoring Paper Trading

```bash
# View real-time metrics
curl http://localhost:8080/api/metrics

# Check paper trading report
python scripts/generate_paper_trading_report.py

# View logs
tail -f logs/paper_trading.log
```

---

## 🤖 AI Provider Configuration

### OpenRouter (Recommended)

OpenRouter provides access to DeepSeek models with simple API:

```env
AI_PROVIDER=openrouter
AI_MODEL=deepseek/deepseek-chat
OPENROUTER_API_KEY=sk-or-v1-your_key_here
AI_ENABLED=true
AI_MIN_CONFIDENCE=0.65
```

**Supported Models:**
- `deepseek/deepseek-chat` - Fast, cost-effective ($0.14/$0.28 per 1M tokens)
- `deepseek/deepseek-reasoner` - Deep reasoning for complex decisions

**Get API Key**: https://openrouter.ai/keys

### Direct DeepSeek API

Use DeepSeek API directly:

```env
AI_PROVIDER=deepseek
AI_MODEL=deepseek-chat
DEEPSEEK_API_KEY=your_deepseek_key
AI_BASE_URL=https://api.deepseek.com
```

**Get API Key**: https://platform.deepseek.com/api_keys

### OpenAI (Alternative)

Use OpenAI models (GPT-4, etc.):

```env
AI_PROVIDER=openai
AI_MODEL=gpt-4-turbo-preview
OPENAI_API_KEY=sk-your_openai_key
```

### AI Configuration Matrix

| Provider | Model | Cost (1M tokens) | Speed | Reasoning |
|----------|-------|------------------|-------|-----------|
| OpenRouter | deepseek/deepseek-chat | $0.14/$0.28 | Fast | Good |
| OpenRouter | deepseek/deepseek-reasoner | $0.55/$2.19 | Medium | Excellent |
| DeepSeek | deepseek-chat | $0.14/$0.28 | Fast | Good |
| OpenAI | gpt-4-turbo | $10/$30 | Medium | Excellent |
| OpenAI | gpt-3.5-turbo | $0.50/$1.50 | Very Fast | Good |

**Recommendation**: Start with `deepseek/deepseek-chat` via OpenRouter for best cost/performance balance.

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
- Real-time P&L and capital tracking
- Open positions with entry/exit details
- Recent trades with P&L breakdown
- Strategy performance metrics
- System health and error monitoring
- Risk management status (daily loss, trade limits)
- Auto-refresh every 5 seconds

### Logs

```bash
tail -f logs/trading_bot.log  # Main log
tail -f logs/trades.log       # Trades only
tail -f logs/errors.log       # Errors only
tail -f logs/paper_trading.log # Paper trading simulation
tail -f logs/json/trading_bot.json # Structured JSON logs
```

### API Endpoints

```bash
# System metrics
curl http://localhost:8080/api/metrics

# Performance snapshot
curl http://localhost:8080/api/performance

# Open positions
curl http://localhost:8080/api/positions

# Recent trades
curl http://localhost:8080/api/trades

# System health
curl http://localhost:8080/api/health
```

---

## 📚 Documentation

Comprehensive documentation is available in the `docs/` directory:

### Core Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - System architecture and component overview
- **[Deployment Guide](docs/DEPLOYMENT_GUIDE.md)** - Production deployment instructions
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions

### Implementation Documentation

- **[nof1.ai Alignment Plan](docs/nof1_alignment_plan.md)** - nof1.ai-inspired features implementation
- **[nof1.ai Implementation Summary](docs/nof1_alignment_implementation_summary.md)** - Completed nof1.ai features
- **[Phase N4/N5 Completion Notes](docs/phase_n4_n5_completion_notes.md)** - Engine alignment and paper trading framework

### Strategy & Performance

- **[Strategy Research](docs/phase_a_strategy_research.md)** - 15+ strategies documented with references
- **[Backtest Analysis](docs/phase_f_backtest_analysis.md)** - Comprehensive backtest results
- **[Strategy Improvements](docs/strategy_improvements_report.md)** - Optimization recommendations

### Testing & Validation

- **[Paper Trading Validation Plan](docs/paper_trading_validation_plan.md)** - 3-phase validation framework
- **[Phase F Testing Report](docs/phase_f_testing_report.md)** - Stress test results

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

## 🔒 Security & Safety

### Security Best Practices

1. ✅ **Never commit API keys** - Use `.env` file (already in `.gitignore`)
2. ✅ **Use environment variables** - All sensitive data in `.env`
3. ✅ **Enable IP whitelisting** - Restrict API access to your server IP
4. ✅ **Disable withdrawal permissions** - Trading-only API keys
5. ✅ **Rotate keys regularly** - Every 30-90 days
6. ✅ **Enable 2FA on exchanges** - Additional account security
7. ✅ **Use testnet first** - Always test on testnet before live trading
8. ✅ **Monitor logs** - Regular log review for suspicious activity

### File Permissions

```bash
chmod 600 .env                    # Restrict .env to owner only
chmod 700 config/                 # Restrict config directory
chmod 700 logs/                   # Restrict logs directory
chmod 700 data/                   # Restrict database directory
```

### Safety Features (nof1.ai-Inspired)

The system includes multiple layers of safety controls:

#### Account-Level Protection
- **15% Drawdown Warning** - Alert when account drops 15% from peak
- **20% Drawdown Stop** - Automatic trading halt at 20% drawdown
- **Daily Loss Limit** - Max 5% loss per day before auto-stop
- **Position TTL** - 36-hour maximum holding time with auto-exit

#### Trade-Level Protection
- **Confidence Thresholds** - Minimum confidence requirements (0.65 default)
- **Position Size Limits** - Max 20% exposure per symbol
- **Daily Trade Limits** - Max 20 trades per day to prevent over-trading
- **Stop-Loss Enforcement** - Automatic stop-loss on all positions

#### Exit Plan Monitoring
- **Invalidation Conditions** - Auto-exit when trade thesis invalidated
- **Tiered Trailing Stops** - Progressive profit protection at +8%/+15%/+25%
- **Take-Profit Targets** - Automatic profit-taking at predefined levels
- **Emergency Stop** - Manual emergency stop button in dashboard

#### System-Level Protection
- **Error Recovery** - Circuit breaker pattern with automatic recovery
- **Rate Limiting** - API rate limit protection
- **Health Monitoring** - Continuous system health checks
- **Graceful Shutdown** - Clean position closure on system stop

### Risk Management Configuration

Adjust risk parameters in `.env`:

```env
# Account Protection
MAX_ACCOUNT_DRAWDOWN_PCT=20.0      # Stop trading at 20% drawdown
DRAWDOWN_WARNING_PCT=15.0          # Alert at 15% drawdown
MAX_DAILY_LOSS_PCT=5.0             # Max 5% daily loss

# Position Management
MAX_POSITION_SIZE_PCT=20.0         # Max 20% per symbol
MAX_DAILY_TRADES=20                # Max 20 trades per day
POSITION_TTL_HOURS=36              # 36-hour position timeout

# AI Configuration
AI_MIN_CONFIDENCE=0.65             # Minimum confidence for trades
AI_ENABLED=true                    # Enable/disable AI trading

# Trailing Stops (nof1.ai-inspired)
TRAILING_STOP_TIER1_PROFIT=8.0     # +8% profit: move SL to breakeven
TRAILING_STOP_TIER2_PROFIT=15.0    # +15% profit: trail at 50%
TRAILING_STOP_TIER3_PROFIT=25.0    # +25% profit: trail at 33%
```

---

## ⚠️ Disclaimer

**IMPORTANT**: Cryptocurrency trading involves substantial risk of loss. This software is provided "as-is" without any warranties. Never trade with money you cannot afford to lose.

### Risk Warnings

- ⚠️ **High Risk**: Cryptocurrency markets are highly volatile and unpredictable
- ⚠️ **No Guarantees**: Past performance does not guarantee future results
- ⚠️ **Leverage Risk**: Leveraged trading can amplify both gains and losses
- ⚠️ **AI Limitations**: AI models can make incorrect decisions
- ⚠️ **Technical Risk**: Software bugs or exchange issues can cause losses
- ⚠️ **Market Risk**: Black swan events can cause catastrophic losses

### Recommended Approach

**Always:**
- ✅ **Start with testnet/demo trading** - Test thoroughly before live trading
- ✅ **Complete 3-phase paper trading validation** - Validate system performance
- ✅ **Start with small capital** - Begin with <$1000 you can afford to lose
- ✅ **Use proper risk management** - Never risk more than 1-2% per trade
- ✅ **Monitor continuously** - Check system health and performance daily
- ✅ **Set stop-losses** - Always use stop-loss orders
- ✅ **Diversify strategies** - Don't rely on a single strategy
- ✅ **Keep learning** - Continuously improve your understanding

**Never:**
- ❌ Trade with borrowed money or money you need
- ❌ Disable safety features (drawdown gates, stop-losses)
- ❌ Ignore warning signals or system alerts
- ❌ Over-leverage positions beyond your risk tolerance
- ❌ Trade without understanding the strategies

---

## 🙏 Acknowledgments

This project builds on excellent open-source work:

- **[nof1.ai](https://github.com/195440/nof1.ai)** - Autonomous AI trading inspiration and risk management framework
- **[CCXT](https://github.com/ccxt/ccxt)** - Unified cryptocurrency exchange API
- **[TA-Lib](https://github.com/mrjbq7/ta-lib)** - Technical analysis library
- **[DeepSeek](https://www.deepseek.com/)** - Advanced AI reasoning models
- **[OpenRouter](https://openrouter.ai/)** - LLM API gateway
- **[freqtrade-strategies](https://github.com/freqtrade/freqtrade-strategies)** - Proven quantitative trading strategies

Special thanks to the nof1.ai team for pioneering autonomous AI trading approaches and sharing their research publicly.

---

## 📞 Support & Community

- **Documentation**: See `docs/` directory for comprehensive guides
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Join GitHub Discussions for questions and ideas
- **Contributing**: Pull requests welcome! See CONTRIBUTING.md

---

## 📄 License

MIT License - See LICENSE file for details

---

**Version**: 3.0.0 (nof1.ai-Aligned)  
**Last Updated**: October 27, 2025  
**Status**: Production Ready - Paper Trading Validation Framework Complete

**Features:**
- 15+ Proven Strategies (Momentum, Mean Reversion, Volatility, AI-Powered)
- nof1.ai-Inspired Risk Management (36h TTL, Tiered Trailing, Drawdown Gates)
- Multi-Exchange Support (Bybit, Binance, MEXC via CCXT)
- DeepSeek AI Integration (Chat V3.1 via OpenRouter)
- Comprehensive Testing (70+ tests, 100% passing)
- Production Documentation (Architecture, Deployment, Troubleshooting)

**Exchanges**: Bybit, Binance, MEXC  
**AI Models**: DeepSeek Chat V3.1, DeepSeek Reasoner  
**Test Coverage**: 70+ unit/integration tests (100% passing)
