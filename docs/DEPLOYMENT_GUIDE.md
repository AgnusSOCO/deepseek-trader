# Deployment Guide - AI Cryptocurrency Trading Bot

Complete guide for deploying the autonomous trading system to production.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Setup](#environment-setup)
3. [Configuration](#configuration)
4. [Paper Trading Validation](#paper-trading-validation)
5. [Production Deployment](#production-deployment)
6. [Monitoring & Maintenance](#monitoring--maintenance)
7. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

- **Operating System**: Ubuntu 20.04+ or similar Linux distribution
- **Python**: 3.10 or higher
- **Memory**: Minimum 4GB RAM (8GB recommended)
- **Storage**: Minimum 20GB free space
- **Network**: Stable internet connection with low latency to exchange APIs

### Required Accounts

1. **Exchange Account** (Bybit, Binance, or MEXC)
   - API keys with trading permissions
   - Testnet account for paper trading validation
   - Sufficient capital for live trading

2. **OpenRouter Account** (for DeepSeek AI)
   - API key from https://openrouter.ai/
   - Sufficient credits for LLM calls

3. **Redis Server** (optional but recommended)
   - Local installation or cloud service
   - Used for caching and real-time state

### Software Dependencies

Install system dependencies:

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv redis-server build-essential

# Install TA-Lib (required for technical indicators)
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ..
rm -rf ta-lib ta-lib-0.4.0-src.tar.gz
```

---

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/AgnusSOCO/deepseek-trader.git
cd deepseek-trader
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Verify Installation

```bash
python -m pytest tests/ -v
```

Expected output: All tests passing (70/70)

---

## Configuration

### 1. Create Environment File

Copy the example environment file:

```bash
cp .env.example .env
```

### 2. Configure Exchange API Keys

Edit `.env` and add your exchange API keys:

```bash
# For Bybit Testnet (recommended for initial testing)
BYBIT_TESTNET_API_KEY=your_testnet_api_key_here
BYBIT_TESTNET_API_SECRET=your_testnet_api_secret_here

# For Bybit Live (production)
BYBIT_LIVE_API_KEY=your_live_api_key_here
BYBIT_LIVE_API_SECRET=your_live_api_secret_here
```

### 3. Configure OpenRouter API Key

Add your OpenRouter API key for DeepSeek AI:

```bash
OPENROUTER_API_KEY=sk-or-v1-your_api_key_here
```

### 4. Configure Trading Parameters

Adjust risk management settings in `.env`:

```bash
# Trading Mode
TRADING_MODE=demo  # Start with demo mode

# Exchange
EXCHANGE=bybit

# Risk Management
INITIAL_CAPITAL=10000
MAX_DAILY_LOSS_PCT=5.0
MAX_DAILY_TRADES=20
MAX_POSITION_SIZE_PCT=20.0

# Account Drawdown Protection (nof1.ai alignment)
ACCOUNT_DRAWDOWN_WARN_PCT=15.0  # No new positions at 15% drawdown
ACCOUNT_DRAWDOWN_STOP_PCT=20.0  # Pause all trading at 20% drawdown

# Position Management
MAX_HOLDING_HOURS=36.0  # 36-hour TTL for positions
TIERED_TRAILING_ENABLED=true  # Enable tiered trailing stops

# AI Configuration
AI_ENABLED=true
AI_MIN_CONFIDENCE=0.65
AI_MAX_COST_PER_DECISION=0.10

# Autonomous Trading
AUTONOMOUS_ENABLED=true
AUTONOMOUS_LOOP_INTERVAL=300  # 5 minutes (300 seconds)
AUTONOMOUS_MIN_CONFIDENCE=0.65
```

### 5. Validate Configuration

Run the exchange validation script:

```bash
python scripts/validate_exchange_config.py --exchange bybit
```

Expected output: All validation checks passing

---

## Paper Trading Validation

**CRITICAL**: Complete all 3 phases of paper trading validation before live deployment.

### Phase 1: Single Strategy Validation (1 week)

**Objective**: Validate core system with conservative settings

**Configuration**:
- Single strategy: Momentum_1h
- Single symbol: BTC/USDT
- Conservative risk limits (3% daily loss, 10% drawdown stop)

**Run**:

```bash
python scripts/run_paper_trading_validation.py \
  --phase 1 \
  --duration 168 \
  --exchange bybit \
  --capital 10000 \
  --output-dir ./validation_phase1
```

**Success Criteria**:
- ✅ System runs continuously for 7 days without crashes
- ✅ Total return > -10%
- ✅ Max drawdown < 15%
- ✅ Win rate > 30% (if >10 trades)
- ✅ Profit factor > 0.8
- ✅ No critical errors in logs

### Phase 2: Multi-Strategy Validation (1 week)

**Objective**: Validate multiple strategies working together

**Configuration**:
- Multiple strategies: Momentum_1h, MeanReversion_15m, UniversalMacd_5m
- Multiple symbols: BTC/USDT, ETH/USDT
- Moderate risk limits (4% daily loss, 18% drawdown stop)

**Run**:

```bash
python scripts/run_paper_trading_validation.py \
  --phase 2 \
  --duration 168 \
  --exchange bybit \
  --capital 10000 \
  --output-dir ./validation_phase2
```

**Success Criteria**:
- ✅ All Phase 1 criteria
- ✅ Strategies don't conflict or over-trade
- ✅ Portfolio diversification working correctly
- ✅ Risk management across multiple positions

### Phase 3: Full System Validation (1 week)

**Objective**: Validate production configuration

**Configuration**:
- All strategies enabled
- Multiple symbols: BTC/USDT, ETH/USDT, BNB/USDT
- Production risk limits (5% daily loss, 20% drawdown stop)

**Run**:

```bash
python scripts/run_paper_trading_validation.py \
  --phase 3 \
  --duration 168 \
  --exchange bybit \
  --capital 10000 \
  --output-dir ./validation_phase3
```

**Success Criteria**:
- ✅ All Phase 1 & 2 criteria
- ✅ System handles high-frequency decision making
- ✅ All safety mechanisms working (drawdown gates, TTL, trailing stops)
- ✅ Performance metrics acceptable for production

### Validation Review

After completing all 3 phases:

1. **Review all validation reports**:
   ```bash
   cat validation_phase1/phase_1_validation_summary.json
   cat validation_phase2/phase_2_validation_summary.json
   cat validation_phase3/phase_3_validation_summary.json
   ```

2. **Analyze trade logs**:
   ```bash
   # Check for patterns, errors, or anomalies
   grep "ERROR" paper_trading_validation.log
   grep "WARNING" paper_trading_validation.log
   ```

3. **Calculate aggregate metrics**:
   - Total return across all phases
   - Average win rate
   - Maximum drawdown observed
   - System uptime percentage

4. **Decision**: Only proceed to production if ALL success criteria are met

---

## Production Deployment

### 1. Pre-Deployment Checklist

- [ ] All 3 phases of paper trading validation completed successfully
- [ ] All validation success criteria met
- [ ] Exchange API keys verified for live trading
- [ ] Risk limits reviewed and approved
- [ ] Monitoring systems configured
- [ ] Emergency stop procedures documented
- [ ] Backup and recovery plan in place

### 2. Update Configuration for Production

Edit `.env`:

```bash
# Switch to live mode
TRADING_MODE=live
PRICEFEED_TESTNET=false

# Use live API keys
BYBIT_LIVE_API_KEY=your_live_api_key_here
BYBIT_LIVE_API_SECRET=your_live_api_secret_here

# Start with conservative capital allocation
INITIAL_CAPITAL=1000  # Start small!

# Keep conservative risk limits initially
MAX_DAILY_LOSS_PCT=3.0
MAX_DAILY_TRADES=10
MAX_POSITION_SIZE_PCT=15.0
ACCOUNT_DRAWDOWN_WARN_PCT=10.0
ACCOUNT_DRAWDOWN_STOP_PCT=15.0
```

### 3. Run System in Production

**Option A: Foreground (for testing)**

```bash
python -m src.autonomous.autonomous_trading_system
```

**Option B: Background with systemd (recommended)**

Create systemd service file `/etc/systemd/system/trading-bot.service`:

```ini
[Unit]
Description=AI Cryptocurrency Trading Bot
After=network.target redis.service

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/deepseek-trader
Environment="PATH=/home/ubuntu/deepseek-trader/venv/bin"
ExecStart=/home/ubuntu/deepseek-trader/venv/bin/python -m src.autonomous.autonomous_trading_system
Restart=always
RestartSec=10
StandardOutput=append:/var/log/trading-bot/output.log
StandardError=append:/var/log/trading-bot/error.log

[Install]
WantedBy=multi-user.target
```

Enable and start service:

```bash
sudo mkdir -p /var/log/trading-bot
sudo systemctl daemon-reload
sudo systemctl enable trading-bot
sudo systemctl start trading-bot
```

Check status:

```bash
sudo systemctl status trading-bot
sudo journalctl -u trading-bot -f
```

### 4. Gradual Capital Scaling

**Week 1**: Start with $1,000
- Monitor closely
- Verify all systems working
- Check for any issues

**Week 2**: Scale to $2,500 (if Week 1 successful)
- Continue monitoring
- Verify risk management working at scale

**Week 3**: Scale to $5,000 (if Week 2 successful)
- Full monitoring
- Performance review

**Week 4+**: Scale to target capital (if all previous weeks successful)
- Ongoing monitoring
- Regular performance reviews

---

## Monitoring & Maintenance

### Real-Time Monitoring

1. **Dashboard**: Access web dashboard at http://localhost:8080
   - Real-time capital and P&L
   - Open positions
   - Recent trades
   - Performance metrics

2. **Log Monitoring**:
   ```bash
   # Main logs
   tail -f logs/main.log
   
   # Error logs
   tail -f logs/error.log
   
   # Trade logs
   tail -f logs/trades.log
   ```

3. **System Metrics**:
   ```bash
   # Check system status
   sudo systemctl status trading-bot
   
   # Check resource usage
   htop
   
   # Check Redis
   redis-cli ping
   ```

### Daily Checks

- [ ] Review overnight trades
- [ ] Check current capital and P&L
- [ ] Verify no critical errors in logs
- [ ] Confirm system is running
- [ ] Review open positions
- [ ] Check drawdown levels

### Weekly Reviews

- [ ] Calculate weekly performance metrics
- [ ] Review all trades for patterns
- [ ] Analyze strategy performance
- [ ] Check for any anomalies
- [ ] Review risk management effectiveness
- [ ] Update documentation if needed

### Monthly Maintenance

- [ ] Full system backup
- [ ] Performance report generation
- [ ] Strategy optimization review
- [ ] Risk limit adjustment (if needed)
- [ ] System updates and patches
- [ ] Database cleanup

### Emergency Procedures

**Emergency Stop**:

```bash
# Stop trading immediately
sudo systemctl stop trading-bot

# Or send SIGTERM to process
kill -TERM $(pgrep -f autonomous_trading_system)
```

**Close All Positions**:

```bash
# Use exchange web interface to manually close all positions
# Or use emergency close script (if implemented)
python scripts/emergency_close_all.py
```

**System Recovery**:

1. Stop the trading bot
2. Review logs to identify issue
3. Fix configuration or code issue
4. Run tests to verify fix
5. Restart in demo mode first
6. Verify working correctly
7. Switch back to live mode

---

## Troubleshooting

### Common Issues

#### 1. System Won't Start

**Symptoms**: Bot crashes immediately on startup

**Possible Causes**:
- Missing environment variables
- Invalid API keys
- Redis not running
- Missing dependencies

**Solutions**:
```bash
# Check environment file
cat .env | grep -v "^#" | grep -v "^$"

# Verify API keys
python scripts/validate_exchange_config.py

# Check Redis
redis-cli ping

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

#### 2. No Trades Being Executed

**Symptoms**: System running but no trades

**Possible Causes**:
- Confidence threshold too high
- Risk limits too restrictive
- No valid signals generated
- Trading paused due to drawdown

**Solutions**:
```bash
# Check risk manager status
grep "trading_paused\|no_new_positions" logs/main.log

# Check signal generation
grep "generate_signal" logs/main.log

# Review confidence levels
grep "confidence" logs/main.log

# Lower confidence threshold (in .env)
AUTONOMOUS_MIN_CONFIDENCE=0.60
```

#### 3. Excessive Trading

**Symptoms**: Too many trades, high fees

**Possible Causes**:
- Confidence threshold too low
- Multiple strategies generating conflicting signals
- Loop interval too short

**Solutions**:
```bash
# Increase confidence threshold
AUTONOMOUS_MIN_CONFIDENCE=0.75

# Reduce max daily trades
MAX_DAILY_TRADES=10

# Increase loop interval
AUTONOMOUS_LOOP_INTERVAL=600  # 10 minutes
```

#### 4. High Drawdown

**Symptoms**: Capital decreasing rapidly

**Possible Causes**:
- Market conditions unfavorable
- Strategy not performing well
- Position sizing too aggressive
- Stop-losses not working

**Solutions**:
```bash
# Immediately reduce position sizes
MAX_POSITION_SIZE_PCT=10.0

# Tighten stop-losses
DEFAULT_STOP_LOSS_PCT=1.5

# Lower drawdown thresholds
ACCOUNT_DRAWDOWN_WARN_PCT=10.0
ACCOUNT_DRAWDOWN_STOP_PCT=12.0

# Consider stopping trading temporarily
sudo systemctl stop trading-bot
```

#### 5. API Rate Limiting

**Symptoms**: "Rate limit exceeded" errors

**Possible Causes**:
- Too many API calls
- Loop interval too short
- Multiple instances running

**Solutions**:
```bash
# Increase loop interval
AUTONOMOUS_LOOP_INTERVAL=600

# Check for multiple instances
ps aux | grep autonomous_trading_system

# Implement request throttling (already built-in)
```

### Getting Help

1. **Check Logs**: Always start by reviewing logs
   ```bash
   tail -100 logs/error.log
   ```

2. **Review Documentation**: Check relevant docs in `docs/` directory

3. **Run Tests**: Verify system integrity
   ```bash
   python -m pytest tests/ -v
   ```

4. **GitHub Issues**: Report bugs or ask questions
   - https://github.com/AgnusSOCO/deepseek-trader/issues

---

## Security Best Practices

1. **API Keys**:
   - Never commit API keys to version control
   - Use environment variables only
   - Rotate keys regularly
   - Disable withdrawal permissions

2. **Server Security**:
   - Use firewall (ufw)
   - Keep system updated
   - Use SSH keys (not passwords)
   - Limit sudo access

3. **Monitoring**:
   - Set up alerts for unusual activity
   - Monitor API usage
   - Track capital changes
   - Review logs daily

4. **Backups**:
   - Backup database daily
   - Backup configuration files
   - Store backups securely off-site
   - Test restore procedures

---

## Performance Optimization

### System Performance

1. **Redis Caching**: Ensure Redis is running for optimal performance
2. **Database Optimization**: Regular VACUUM for SQLite
3. **Log Rotation**: Configure logrotate to prevent disk fill
4. **Resource Monitoring**: Use htop/top to monitor CPU/memory

### Trading Performance

1. **Strategy Selection**: Disable underperforming strategies
2. **Parameter Tuning**: Use walk-forward optimization
3. **Risk Adjustment**: Adjust position sizes based on performance
4. **Market Regime**: Adapt to changing market conditions

---

## Conclusion

This deployment guide provides a comprehensive path from initial setup to production deployment. Always prioritize safety and thorough testing before risking real capital.

**Remember**:
- Start small with capital
- Monitor constantly
- Be prepared to stop trading if needed
- Review performance regularly
- Adjust parameters based on results

**Success Metrics**:
- Positive returns over time
- Controlled drawdowns
- Consistent performance
- System reliability
- Risk management effectiveness

For additional support, refer to:
- `docs/ARCHITECTURE.md` - System architecture
- `docs/TROUBLESHOOTING.md` - Detailed troubleshooting
- `docs/phase_n4_n5_completion_plan.md` - nof1.ai alignment details
