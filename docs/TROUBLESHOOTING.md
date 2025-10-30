# Troubleshooting Guide - AI Cryptocurrency Trading Bot

Comprehensive troubleshooting guide for common issues and their solutions.

## Table of Contents

1. [Startup Issues](#startup-issues)
2. [Trading Issues](#trading-issues)
3. [Performance Issues](#performance-issues)
4. [API & Exchange Issues](#api--exchange-issues)
5. [Risk Management Issues](#risk-management-issues)
6. [AI/LLM Issues](#aillm-issues)
7. [Data & Storage Issues](#data--storage-issues)
8. [Monitoring & Dashboard Issues](#monitoring--dashboard-issues)
9. [Diagnostic Commands](#diagnostic-commands)
10. [Getting Help](#getting-help)

---

## Startup Issues

### Issue: Bot Won't Start - Missing Environment Variables

**Symptoms**:
```
KeyError: 'OPENROUTER_API_KEY'
ValueError: EXCHANGE environment variable not set
```

**Cause**: Missing or incomplete `.env` file

**Solution**:
```bash
# Check if .env exists
ls -la .env

# If missing, copy from example
cp .env.example .env

# Edit and add required variables
nano .env

# Verify all required variables are set
grep -v "^#" .env | grep -v "^$" | grep "API_KEY\|EXCHANGE\|TRADING_MODE"
```

**Required Variables**:
- `EXCHANGE` (bybit, binance, or mexc)
- `TRADING_MODE` (demo or live)
- `OPENROUTER_API_KEY` (for AI features)
- Exchange API keys (testnet or live)

---

### Issue: Bot Crashes on Startup - Import Errors

**Symptoms**:
```
ModuleNotFoundError: No module named 'ccxt'
ImportError: cannot import name 'PriceFeed'
```

**Cause**: Missing dependencies or incorrect Python environment

**Solution**:
```bash
# Activate virtual environment
source venv/bin/activate

# Verify Python version (3.10+)
python --version

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Verify CCXT installation
python -c "import ccxt; print(ccxt.__version__)"

# Verify TA-Lib installation
python -c "import talib; print(talib.__version__)"
```

**If TA-Lib fails**:
```bash
# Install TA-Lib system library
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib/
./configure --prefix=/usr
make
sudo make install
cd ..
rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Reinstall Python wrapper
pip install TA-Lib --force-reinstall
```

---

### Issue: Bot Crashes - Redis Connection Failed

**Symptoms**:
```
redis.exceptions.ConnectionError: Error connecting to Redis
ConnectionRefusedError: [Errno 111] Connection refused
```

**Cause**: Redis server not running

**Solution**:
```bash
# Check Redis status
sudo systemctl status redis

# If not running, start it
sudo systemctl start redis

# Enable auto-start on boot
sudo systemctl enable redis

# Test connection
redis-cli ping
# Expected output: PONG

# If Redis not installed
sudo apt-get install redis-server
```

**Alternative**: Disable Redis caching (not recommended for production)
```bash
# In .env, comment out Redis URL
# REDIS_URL=redis://localhost:6379/0
```

---

### Issue: Bot Crashes - Database Error

**Symptoms**:
```
sqlalchemy.exc.OperationalError: unable to open database file
sqlite3.OperationalError: database is locked
```

**Cause**: Database file permissions or locked database

**Solution**:
```bash
# Check database directory exists
mkdir -p data

# Check permissions
ls -la data/

# Fix permissions
chmod 755 data/
chmod 644 data/trading_bot.db

# If database locked, check for other processes
ps aux | grep autonomous_trading_system

# Kill other instances if found
pkill -f autonomous_trading_system

# Remove lock file if exists
rm -f data/trading_bot.db-journal
```

---

## Trading Issues

### Issue: No Trades Being Executed

**Symptoms**: Bot running but no trades for extended period

**Possible Causes & Solutions**:

#### 1. Trading Paused Due to Drawdown

**Check**:
```bash
grep "trading_paused\|no_new_positions" logs/main.log | tail -5
```

**Solution**:
```bash
# Check current drawdown
grep "drawdown" logs/main.log | tail -1

# If drawdown > 15%, wait for recovery or adjust thresholds in .env
ACCOUNT_DRAWDOWN_WARN_PCT=20.0
ACCOUNT_DRAWDOWN_STOP_PCT=25.0
```

#### 2. Confidence Threshold Too High

**Check**:
```bash
grep "confidence.*below threshold" logs/main.log | tail -10
```

**Solution**:
```bash
# Lower confidence threshold in .env
AUTONOMOUS_MIN_CONFIDENCE=0.60  # Was 0.65
AI_MIN_CONFIDENCE=0.60
```

#### 3. Daily Limits Reached

**Check**:
```bash
grep "daily.*limit" logs/main.log | tail -5
```

**Solution**:
```bash
# Increase daily limits in .env
MAX_DAILY_TRADES=30  # Was 20
MAX_DAILY_LOSS_PCT=7.0  # Was 5.0

# Or wait for daily reset (midnight UTC)
```

#### 4. No Valid Signals Generated

**Check**:
```bash
grep "generate_signal" logs/main.log | tail -20
```

**Solution**:
```bash
# Check if strategies are running
grep "strategy.*initialized" logs/main.log

# Check market data is being received
grep "price.*updated" logs/main.log | tail -5

# Verify exchange connection
python scripts/validate_exchange_config.py
```

---

### Issue: Excessive Trading (Over-Trading)

**Symptoms**: Too many trades, high fees, poor performance

**Possible Causes & Solutions**:

#### 1. Confidence Threshold Too Low

**Solution**:
```bash
# Increase confidence threshold in .env
AUTONOMOUS_MIN_CONFIDENCE=0.75  # Was 0.65
AI_MIN_CONFIDENCE=0.75
```

#### 2. Multiple Strategies Conflicting

**Solution**:
```bash
# Disable some strategies or increase loop interval
AUTONOMOUS_LOOP_INTERVAL=600  # 10 minutes instead of 5

# Or reduce number of active strategies
# Edit strategy initialization in code
```

#### 3. Loop Interval Too Short

**Solution**:
```bash
# Increase loop interval in .env
AUTONOMOUS_LOOP_INTERVAL=900  # 15 minutes
```

---

### Issue: Positions Not Closing Automatically

**Symptoms**: Positions remain open past 36 hours or don't hit stop-loss

**Possible Causes & Solutions**:

#### 1. Exit Monitor Not Running

**Check**:
```bash
grep "ExitPlanMonitor" logs/main.log | tail -10
grep "check_exit_conditions" logs/main.log | tail -10
```

**Solution**:
```bash
# Restart the bot
sudo systemctl restart trading-bot

# Verify exit monitor is active
grep "exit_monitor.*initialized" logs/main.log
```

#### 2. Stop-Loss Not Set Correctly

**Check**:
```bash
grep "stop_loss" logs/trades.log | tail -10
```

**Solution**:
```bash
# Ensure strategies set stop-loss
# Check strategy configuration
grep "DEFAULT_STOP_LOSS_PCT" .env

# Manually close positions if needed
# Use exchange web interface or emergency script
```

#### 3. 36-Hour TTL Not Enforced

**Check**:
```bash
grep "TIMEOUT" logs/trades.log
grep "max_holding_hours" logs/main.log
```

**Solution**:
```bash
# Verify MAX_HOLDING_HOURS is set in .env
grep "MAX_HOLDING_HOURS" .env

# Should be 36.0
MAX_HOLDING_HOURS=36.0
```

---

## Performance Issues

### Issue: High CPU Usage

**Symptoms**: CPU usage consistently above 80%

**Possible Causes & Solutions**:

#### 1. Too Many Strategies Running

**Solution**:
```bash
# Reduce number of active strategies
# Edit strategy initialization to enable only top performers

# Or increase loop interval
AUTONOMOUS_LOOP_INTERVAL=600  # 10 minutes
```

#### 2. Indicator Calculation Overhead

**Solution**:
```bash
# Reduce candle lookback in .env
PRICEFEED_CANDLE_LOOKBACK=500  # Was 1000

# Or reduce number of timeframes monitored
```

#### 3. Logging Too Verbose

**Solution**:
```bash
# Reduce log level in .env
LOG_LEVEL=WARNING  # Was INFO or DEBUG
```

---

### Issue: High Memory Usage

**Symptoms**: Memory usage growing over time, eventual crash

**Possible Causes & Solutions**:

#### 1. Memory Leak in Price Feed

**Solution**:
```bash
# Restart bot daily via cron
# Add to crontab: 0 0 * * * systemctl restart trading-bot

# Or reduce candle lookback
PRICEFEED_CANDLE_LOOKBACK=300
```

#### 2. Too Much Historical Data

**Solution**:
```bash
# Clean up old database records
python scripts/cleanup_old_data.py --days 30

# Or use PostgreSQL instead of SQLite
```

---

### Issue: Slow Response Time

**Symptoms**: Dashboard slow to load, delayed trade execution

**Possible Causes & Solutions**:

#### 1. Database Performance

**Solution**:
```bash
# Vacuum SQLite database
sqlite3 data/trading_bot.db "VACUUM;"

# Add indexes
sqlite3 data/trading_bot.db "CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp);"

# Or migrate to PostgreSQL
```

#### 2. Network Latency

**Solution**:
```bash
# Test exchange API latency
ping api.bybit.com

# Use VPS closer to exchange servers
# Consider AWS/GCP in Singapore for Asian exchanges
```

---

## API & Exchange Issues

### Issue: API Rate Limiting

**Symptoms**:
```
ccxt.RateLimitExceeded: bybit {"retCode":10006,"retMsg":"rate limit exceeded"}
```

**Cause**: Too many API requests

**Solution**:
```bash
# Increase loop interval
AUTONOMOUS_LOOP_INTERVAL=600  # 10 minutes

# Reduce ticker poll frequency
PRICEFEED_TICKER_POLL_SEC=5.0  # Was 2.0

# Enable request throttling (already built-in)
# CCXT handles rate limiting automatically
```

---

### Issue: Invalid API Signature

**Symptoms**:
```
ccxt.AuthenticationError: bybit {"retCode":10003,"retMsg":"invalid signature"}
```

**Cause**: Incorrect API keys or system time mismatch

**Solution**:
```bash
# Verify API keys in .env
grep "API_KEY\|API_SECRET" .env

# Check system time
date
timedatectl status

# Sync system time
sudo ntpdate -s time.nist.gov

# Or use systemd-timesyncd
sudo systemctl restart systemd-timesyncd
```

---

### Issue: Insufficient Balance

**Symptoms**:
```
ccxt.InsufficientFunds: bybit insufficient balance
```

**Cause**: Not enough capital in exchange account

**Solution**:
```bash
# Check account balance
python -c "
from src.data.price_feed import PriceFeed
pf = PriceFeed('bybit', testnet=True)
print(pf.exchange.fetch_balance())
"

# Deposit more funds to exchange
# Or reduce position sizes in .env
MAX_POSITION_SIZE_PCT=10.0  # Was 20.0
```

---

### Issue: Order Rejected by Exchange

**Symptoms**:
```
ccxt.InvalidOrder: bybit order rejected
```

**Possible Causes & Solutions**:

#### 1. Minimum Order Size

**Solution**:
```bash
# Check exchange minimum order size
# For Bybit BTC/USDT: 0.001 BTC minimum

# Increase minimum position size
MIN_POSITION_SIZE_PCT=2.0  # Was 1.0
```

#### 2. Invalid Leverage

**Solution**:
```bash
# Check exchange leverage limits
# Bybit BTC/USDT: 1x-100x

# Ensure strategies don't exceed limits
# Check strategy leverage settings
```

---

## Risk Management Issues

### Issue: Drawdown Protection Not Working

**Symptoms**: Trading continues despite high drawdown

**Check**:
```bash
grep "check_drawdown_protection" logs/main.log | tail -10
grep "drawdown.*pct" logs/main.log | tail -10
```

**Solution**:
```bash
# Verify drawdown thresholds in .env
grep "DRAWDOWN" .env

# Should see:
# ACCOUNT_DRAWDOWN_WARN_PCT=15.0
# ACCOUNT_DRAWDOWN_STOP_PCT=20.0

# Check if risk manager is initialized
grep "EnhancedRiskManager.*initialized" logs/main.log

# Manually stop trading if needed
sudo systemctl stop trading-bot
```

---

### Issue: Position Sizes Too Large

**Symptoms**: Single positions using >20% of capital

**Check**:
```bash
grep "position_size" logs/trades.log | tail -10
```

**Solution**:
```bash
# Reduce maximum position size in .env
MAX_POSITION_SIZE_PCT=15.0  # Was 20.0

# Reduce confidence scaling
# Edit EnhancedRiskManager settings if needed
```

---

### Issue: Daily Loss Limit Not Enforced

**Symptoms**: Losses exceed daily limit

**Check**:
```bash
grep "daily_loss" logs/main.log | tail -10
```

**Solution**:
```bash
# Verify daily loss limit in .env
grep "MAX_DAILY_LOSS_PCT" .env

# Should be set (default: 5.0)
MAX_DAILY_LOSS_PCT=5.0

# Check if risk manager is checking limits
grep "can_trade_today" logs/main.log | tail -10
```

---

## AI/LLM Issues

### Issue: OpenRouter API Errors

**Symptoms**:
```
openrouter.error.APIError: 401 Unauthorized
openrouter.error.RateLimitError: 429 Too Many Requests
```

**Solutions**:

#### 1. Invalid API Key

```bash
# Verify API key in .env
grep "OPENROUTER_API_KEY" .env

# Test API key
curl https://openrouter.ai/api/v1/auth/key \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"
```

#### 2. Insufficient Credits

```bash
# Check OpenRouter balance
# Visit https://openrouter.ai/credits

# Add more credits or reduce AI usage
AI_ENABLED=false  # Disable AI temporarily
```

#### 3. Rate Limiting

```bash
# Increase loop interval to reduce API calls
AUTONOMOUS_LOOP_INTERVAL=600  # 10 minutes

# Or reduce AI usage
AI_MAX_COST_PER_DECISION=0.05  # Was 0.10
```

---

### Issue: LLM Returning Invalid JSON

**Symptoms**:
```
json.JSONDecodeError: Expecting value
ValidationError: Invalid trading decision
```

**Check**:
```bash
grep "parse.*error\|invalid.*json" logs/main.log | tail -10
```

**Solution**:
```bash
# System should automatically retry with better prompts
# If persistent, check LLM responses in logs

# Fallback to rule-based strategies
# Edit strategy configuration to prioritize non-AI strategies
```

---

### Issue: AI Decisions Too Conservative

**Symptoms**: AI always returns HOLD, no trades

**Check**:
```bash
grep "action.*HOLD" logs/main.log | tail -20
```

**Solution**:
```bash
# Lower AI confidence threshold
AI_MIN_CONFIDENCE=0.60  # Was 0.65

# Check if market data is being provided correctly
grep "market_data" logs/main.log | tail -5

# Verify prompt includes all required information
```

---

## Data & Storage Issues

### Issue: Database Corruption

**Symptoms**:
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solution**:
```bash
# Backup current database
cp data/trading_bot.db data/trading_bot.db.backup

# Try to recover
sqlite3 data/trading_bot.db ".recover" | sqlite3 data/trading_bot_recovered.db

# If recovery fails, restore from backup
# Or start fresh (will lose historical data)
rm data/trading_bot.db
# Bot will create new database on next start
```

---

### Issue: Disk Space Full

**Symptoms**:
```
OSError: [Errno 28] No space left on device
```

**Solution**:
```bash
# Check disk usage
df -h

# Clean up old logs
find logs/ -name "*.log.*" -mtime +30 -delete

# Clean up old backtest data
rm -rf backtest_data/*

# Vacuum database
sqlite3 data/trading_bot.db "VACUUM;"

# Configure log rotation
# Edit /etc/logrotate.d/trading-bot
```

---

### Issue: Missing Historical Data

**Symptoms**: Indicators not calculating, strategies not generating signals

**Check**:
```bash
grep "insufficient.*data" logs/main.log | tail -10
```

**Solution**:
```bash
# Increase candle lookback
PRICEFEED_CANDLE_LOOKBACK=1000  # Was 500

# Wait for data to accumulate (5-10 minutes)

# Or download historical data
python scripts/download_historical_data.py --symbol BTC/USDT --days 7
```

---

## Monitoring & Dashboard Issues

### Issue: Dashboard Not Accessible

**Symptoms**: Cannot access http://localhost:8080

**Check**:
```bash
# Check if dashboard is running
netstat -tulpn | grep 8080

# Check dashboard logs
grep "dashboard" logs/main.log | tail -10
```

**Solution**:
```bash
# Verify dashboard port in .env
grep "DASHBOARD_PORT" .env

# Check firewall
sudo ufw status
sudo ufw allow 8080/tcp

# If running on remote server, use SSH tunnel
ssh -L 8080:localhost:8080 user@server
```

---

### Issue: Dashboard Shows Stale Data

**Symptoms**: Dashboard not updating, shows old information

**Solution**:
```bash
# Check auto-refresh setting
grep "DASHBOARD_AUTO_REFRESH_SEC" .env

# Should be 5 seconds
DASHBOARD_AUTO_REFRESH_SEC=5

# Clear browser cache
# Or force refresh: Ctrl+Shift+R

# Check if performance monitor is running
grep "PerformanceMonitor" logs/main.log | tail -5
```

---

## Diagnostic Commands

### System Health Check

```bash
#!/bin/bash
echo "=== System Health Check ==="

echo -e "\n1. Bot Status:"
sudo systemctl status trading-bot | grep "Active:"

echo -e "\n2. Recent Errors:"
tail -20 logs/error.log

echo -e "\n3. Recent Trades:"
tail -10 logs/trades.log

echo -e "\n4. Current Capital:"
grep "current_capital" logs/main.log | tail -1

echo -e "\n5. Open Positions:"
grep "open_positions" logs/main.log | tail -1

echo -e "\n6. Drawdown Status:"
grep "drawdown" logs/main.log | tail -1

echo -e "\n7. Daily Stats:"
grep "daily.*trades\|daily.*loss" logs/main.log | tail -5

echo -e "\n8. Redis Status:"
redis-cli ping

echo -e "\n9. Disk Space:"
df -h | grep -E "Filesystem|/$"

echo -e "\n10. Memory Usage:"
free -h
```

### Performance Analysis

```bash
#!/bin/bash
echo "=== Performance Analysis ==="

echo -e "\n1. Total Trades:"
grep -c "TRADE_EXECUTED" logs/trades.log

echo -e "\n2. Win Rate:"
python -c "
import json
wins = 0
total = 0
with open('logs/trades.log') as f:
    for line in f:
        if 'pnl' in line:
            total += 1
            if 'pnl.*[0-9]' in line and float(line.split('pnl')[1].split()[0]) > 0:
                wins += 1
print(f'Win Rate: {wins/total*100:.1f}%' if total > 0 else 'No trades yet')
"

echo -e "\n3. Average Trade Duration:"
grep "position_duration" logs/trades.log | tail -20

echo -e "\n4. Strategy Performance:"
grep "strategy.*performance" logs/main.log | tail -10

echo -e "\n5. API Call Statistics:"
grep "api.*call\|request.*count" logs/main.log | tail -10
```

---

## Getting Help

### Before Asking for Help

1. **Check Logs**:
   ```bash
   tail -100 logs/error.log
   tail -100 logs/main.log
   ```

2. **Run Diagnostics**:
   ```bash
   python scripts/validate_exchange_config.py
   python -m pytest tests/ -v
   ```

3. **Check Configuration**:
   ```bash
   cat .env | grep -v "^#" | grep -v "^$"
   ```

4. **Review Recent Changes**:
   ```bash
   git log --oneline -10
   git diff HEAD~1
   ```

### Information to Provide

When asking for help, include:

1. **Error Message**: Full error with stack trace
2. **Log Excerpts**: Relevant log entries (last 50-100 lines)
3. **Configuration**: Sanitized .env file (remove API keys!)
4. **System Info**: OS, Python version, package versions
5. **Steps to Reproduce**: What you did before the error
6. **Expected vs Actual**: What should happen vs what happened

### Where to Get Help

1. **Documentation**:
   - `docs/DEPLOYMENT_GUIDE.md`
   - `docs/ARCHITECTURE.md`
   - `README.md`

2. **GitHub Issues**:
   - https://github.com/AgnusSOCO/deepseek-trader/issues
   - Search existing issues first
   - Create new issue with template

3. **Community**:
   - Discord server (if available)
   - Telegram group (if available)

---

## Emergency Procedures

### Emergency Stop

```bash
# Stop trading immediately
sudo systemctl stop trading-bot

# Or kill process
pkill -TERM -f autonomous_trading_system

# Verify stopped
ps aux | grep autonomous_trading_system
```

### Close All Positions

```bash
# Option 1: Use exchange web interface
# Log in to exchange and manually close all positions

# Option 2: Use emergency script (if implemented)
python scripts/emergency_close_all.py

# Option 3: Use CCXT directly
python -c "
from src.data.price_feed import PriceFeed
pf = PriceFeed('bybit', testnet=False)
positions = pf.exchange.fetch_positions()
for pos in positions:
    if pos['contracts'] > 0:
        pf.exchange.create_order(
            pos['symbol'],
            'market',
            'sell' if pos['side'] == 'long' else 'buy',
            pos['contracts']
        )
"
```

### System Recovery

1. **Stop the bot**
2. **Backup current state**:
   ```bash
   cp data/trading_bot.db data/trading_bot.db.emergency_backup
   cp .env .env.emergency_backup
   ```
3. **Review logs to identify issue**
4. **Fix configuration or code**
5. **Run tests**: `python -m pytest tests/ -v`
6. **Restart in demo mode first**
7. **Verify working correctly**
8. **Switch back to live mode**

---

## Preventive Maintenance

### Daily

- [ ] Check system status
- [ ] Review error logs
- [ ] Verify trades executed correctly
- [ ] Check capital and P&L
- [ ] Confirm no critical errors

### Weekly

- [ ] Review performance metrics
- [ ] Analyze strategy effectiveness
- [ ] Check for anomalies
- [ ] Update documentation
- [ ] Backup database

### Monthly

- [ ] Full system backup
- [ ] Performance report
- [ ] Strategy optimization
- [ ] System updates
- [ ] Security audit

---

## Conclusion

This troubleshooting guide covers the most common issues encountered when running the autonomous trading bot. Always prioritize safety and stop trading if you encounter persistent issues that you cannot resolve.

**Remember**:
- Check logs first
- Run diagnostics
- Start with simple solutions
- Document what you tried
- Ask for help if stuck

For additional support, refer to:
- `docs/DEPLOYMENT_GUIDE.md` - Deployment instructions
- `docs/ARCHITECTURE.md` - System architecture
- GitHub Issues - Community support
