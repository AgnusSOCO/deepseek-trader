# AI Cryptocurrency Trading Bot

A sophisticated AI-powered cryptocurrency trading bot that leverages DeepSeek LLM for intelligent trading decisions on cryptocurrency markets. The system supports multiple trading strategies including scalping, momentum trading, and mean reversion, with comprehensive risk management and both live and demo trading modes.

## Project Status

**Current Phase**: Phase 1 - Foundation & Data Acquisition ✅

### Completed Features (Phase 1)
- ✅ Project structure and configuration management
- ✅ Data acquisition from cryptocurrency exchanges (CCXT integration)
- ✅ Technical indicators calculation (15+ indicators)
- ✅ Data storage (SQLite for persistence, Redis for caching)
- ✅ Comprehensive logging system
- ✅ Unit tests with >80% coverage

### Upcoming Phases
- **Phase 2**: Core Trading Engine (Strategy engine, execution, risk management)
- **Phase 3**: AI Integration (DeepSeek multi-agent system)
- **Phase 4**: Advanced Trading Strategies (Scalping, momentum, mean reversion)
- **Phase 5**: Backtesting & Validation
- **Phase 6**: Live Trading Preparation
- **Phase 7**: Deployment & Monitoring

## Features

### Current Features (Phase 1)
- **Multi-Exchange Support**: Integration with Binance, Bybit, and other CCXT-supported exchanges
- **Real-Time Data**: WebSocket and REST API support for live market data
- **Technical Analysis**: 15+ technical indicators including SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP, and more
- **Data Storage**: SQLite for historical data and trade history, Redis for real-time caching
- **Configuration Management**: YAML-based configuration with environment variable support
- **Structured Logging**: JSON and text logging with rotation and retention policies
- **Observer Pattern**: Efficient data distribution to multiple subscribers

### Planned Features (Future Phases)
- **AI-Driven Decisions**: Multi-agent system using DeepSeek LLM
- **Multiple Strategies**: Scalping, momentum, mean reversion, and custom strategies
- **Risk Management**: Position sizing, stop-loss, take-profit, drawdown protection
- **Live & Demo Modes**: Safe paper trading before deploying real capital
- **Backtesting**: Comprehensive strategy testing on historical data
- **Web Dashboard**: Real-time monitoring and control interface
- **Automated Execution**: Fully autonomous trading with safety controls

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Configuration & Monitoring UI                 │
│              (Web Dashboard - Phase 2/6)                         │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────────────┐
│                     Core Trading Engine (Phase 2)                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Strategy   │  │  AI Decision │  │     Risk     │          │
│  │    Engine    │◄─┤    Module    │◄─┤  Management  │          │
│  └──────┬───────┘  └──────────────┘  └──────────────┘          │
│         │                                                         │
│  ┌──────▼───────┐                    ┌──────────────┐          │
│  │  Execution   │                    │  Backtesting │          │
│  │    Module    │                    │    Engine    │          │
│  └──────┬───────┘                    └──────────────┘          │
└─────────┼──────────────────────────────────────────────────────┘
          │
┌─────────▼──────────────────────────────────────────────────────┐
│              Data Acquisition Module (Phase 1) ✅                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  WebSocket   │  │  REST API    │  │  Historical  │          │
│  │   Streams    │  │   Client     │  │     Data     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────┬──────────────────────────────────────────────────────┘
          │
┌─────────▼──────────────────────────────────────────────────────┐
│         Cryptocurrency Exchanges (Binance, Bybit, etc.)          │
│              Live API ◄─► Demo/Testnet API                       │
└──────────────────────────────────────────────────────────────────┘
```

## Installation

### Prerequisites

- Python 3.11 or higher
- Redis server (for caching)
- Git

### System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8 GB minimum (16 GB recommended)
- **Storage**: 50 GB SSD
- **Network**: Stable internet connection with low latency to exchange servers

### Setup Instructions

1. **Clone the repository**:
```bash
git clone <repository-url>
cd ai-crypto-trading-bot
```

2. **Create a virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Install TA-Lib** (required for technical indicators):

On Ubuntu/Debian:
```bash
sudo apt-get install ta-lib
```

On macOS:
```bash
brew install ta-lib
```

On Windows:
Download and install from: https://github.com/mrjbq7/ta-lib#windows

5. **Install and start Redis**:

On Ubuntu/Debian:
```bash
sudo apt-get install redis-server
sudo systemctl start redis-server
```

On macOS:
```bash
brew install redis
brew services start redis
```

6. **Configure environment variables**:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

7. **Configure settings**:
Edit the configuration files in the `config/` directory:
- `config.yaml` - Main configuration
- `strategies.yaml` - Strategy parameters (for future phases)
- `risk_params.yaml` - Risk management settings (for future phases)

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Trading Mode
TRADING_MODE=demo  # or 'live'

# Binance Testnet API (for demo mode)
BINANCE_TESTNET_API_KEY=your_testnet_api_key_here
BINANCE_TESTNET_API_SECRET=your_testnet_api_secret_here

# Binance Live API (for live mode - Phase 6)
BINANCE_LIVE_API_KEY=your_live_api_key_here
BINANCE_LIVE_API_SECRET=your_live_api_secret_here

# DeepSeek API (for Phase 3)
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Database Configuration
DATABASE_URL=sqlite:///./data/trading_bot.db

# Logging
LOG_LEVEL=INFO
LOG_DIR=./logs
```

### Getting API Keys

#### Binance Testnet (Demo Mode)
1. Visit https://testnet.binance.vision/
2. Register for a testnet account
3. Generate API keys from the dashboard
4. Add keys to `.env` file

#### Binance Live (Production - Phase 6)
1. Visit https://www.binance.com/
2. Create an account and complete KYC
3. Enable 2FA for security
4. Generate API keys with trading permissions
5. **Important**: Disable withdrawal permissions for safety
6. Configure IP whitelist for additional security

## Usage

### Phase 1 - Data Acquisition (Current)

The current phase focuses on data acquisition and technical analysis. Here's how to use the implemented features:

#### Example 1: Fetch Historical Data

```python
import asyncio
from src.utils.config_loader import get_config
from src.utils.logger import init_logger
from src.data.storage import SQLiteStorage, RedisCache
from src.data.indicators import TechnicalIndicators
from src.data.acquisition import MarketDataManager

async def main():
    # Initialize components
    config = get_config()
    logger = init_logger()
    
    storage = SQLiteStorage()
    cache = RedisCache()
    indicators = TechnicalIndicators(config.get_indicator_config())
    
    exchange_config = config.get_exchange_config()
    data_manager = MarketDataManager(exchange_config, storage, cache, indicators)
    
    # Initialize exchange connection
    await data_manager.initialize()
    
    # Fetch initial historical data
    await data_manager.fetch_initial_data('BTC/USDT', '5m', lookback_days=7)
    
    # Get market snapshot with indicators
    snapshot = await data_manager.get_market_snapshot('BTC/USDT', '5m')
    
    print(f"Symbol: {snapshot['symbol']}")
    print(f"Price: ${snapshot['price']:,.2f}")
    print(f"Indicators: {snapshot['indicators']}")
    print(f"Signals: {snapshot['signals']}")
    
    # Cleanup
    await data_manager.close()

if __name__ == '__main__':
    asyncio.run(main())
```

#### Example 2: Calculate Technical Indicators

```python
import pandas as pd
from src.data.indicators import TechnicalIndicators

# Create sample OHLCV data
data = {
    'timestamp': pd.date_range(start='2024-01-01', periods=100, freq='1H'),
    'open': [100 + i for i in range(100)],
    'high': [101 + i for i in range(100)],
    'low': [99 + i for i in range(100)],
    'close': [100.5 + i for i in range(100)],
    'volume': [1000 + i * 10 for i in range(100)]
}
df = pd.DataFrame(data)

# Calculate indicators
indicators = TechnicalIndicators()
df = indicators.calculate_all(df)

# Get latest indicator values
latest = indicators.get_latest_indicators(df)
print(f"RSI: {latest.get('rsi', 'N/A')}")
print(f"MACD: {latest.get('macd', 'N/A')}")

# Get signal summary
signals = indicators.get_signal_summary(df)
print(f"Signals: {signals}")
```

#### Example 3: Stream Live Data

```python
import asyncio
from src.utils.config_loader import get_config
from src.data.storage import SQLiteStorage, RedisCache
from src.data.indicators import TechnicalIndicators
from src.data.acquisition import MarketDataManager

async def on_data_update(symbol, timeframe, data):
    """Callback function for data updates."""
    print(f"Update: {symbol} {timeframe} - Price: ${data['close']:,.2f}")

async def main():
    config = get_config()
    
    storage = SQLiteStorage()
    cache = RedisCache()
    indicators = TechnicalIndicators()
    
    exchange_config = config.get_exchange_config()
    data_manager = MarketDataManager(exchange_config, storage, cache, indicators)
    
    await data_manager.initialize()
    
    # Subscribe to updates
    data_manager.subscribe('BTC/USDT', '5m', on_data_update)
    
    # Start streaming (runs continuously)
    symbols = ['BTC/USDT', 'ETH/USDT']
    timeframes = ['5m', '1h']
    
    try:
        await data_manager.stream_loop(symbols, timeframes, update_interval=60)
    except KeyboardInterrupt:
        print("Stopping...")
        await data_manager.close()

if __name__ == '__main__':
    asyncio.run(main())
```

## Testing

Run the test suite to verify the installation:

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_indicators.py -v

# Run tests with detailed output
pytest -v -s
```

### Test Coverage

Current test coverage for Phase 1:
- Technical Indicators: >90%
- Data Storage: >85%
- Data Acquisition: >80%
- Configuration & Logging: >75%

## Project Structure

```
ai-crypto-trading-bot/
├── config/                      # Configuration files
│   ├── config.yaml              # Main configuration
│   ├── strategies.yaml          # Strategy parameters
│   └── risk_params.yaml         # Risk management settings
├── src/                         # Source code
│   ├── __init__.py
│   ├── data/                    # Data acquisition and processing
│   │   ├── __init__.py
│   │   ├── acquisition.py       # Market data manager
│   │   ├── storage.py           # SQLite and Redis storage
│   │   └── indicators.py        # Technical indicators
│   └── utils/                   # Utilities
│       ├── __init__.py
│       ├── config_loader.py     # Configuration management
│       └── logger.py            # Logging system
├── tests/                       # Unit tests
│   ├── __init__.py
│   ├── test_data_acquisition.py
│   ├── test_indicators.py
│   └── test_storage.py
├── data/                        # Data storage directory
├── logs/                        # Log files
├── requirements.txt             # Python dependencies
├── .env.example                 # Environment variables template
├── .gitignore
└── README.md
```

## Technical Indicators

The bot calculates the following technical indicators:

### Trend Indicators
- **SMA** (Simple Moving Average): 20, 50, 200 periods
- **EMA** (Exponential Moving Average): 12, 26, 50, 200 periods

### Momentum Indicators
- **RSI** (Relative Strength Index): 14 period
- **MACD** (Moving Average Convergence Divergence): 12, 26, 9
- **Stochastic Oscillator**: K=14, D=3
- **CCI** (Commodity Channel Index): 20 period
- **ADX** (Average Directional Index): 14 period

### Volatility Indicators
- **Bollinger Bands**: 20 period, 2 standard deviations
- **ATR** (Average True Range): 14 period

### Volume Indicators
- **VWAP** (Volume Weighted Average Price)
- **OBV** (On-Balance Volume)

## Logging

The bot uses structured logging with multiple log files:

- `logs/trading_bot.log` - Main application log (all levels)
- `logs/trades.log` - Trade execution log (INFO and above)
- `logs/errors.log` - Error log (ERROR and above)
- `logs/data.log` - Data acquisition log (DEBUG and above)

Log files are automatically rotated at 10 MB and retained for 30 days (90 days for trades).

## Database Schema

### Market Data Table
- `id`: Primary key
- `symbol`: Trading symbol (e.g., 'BTC/USDT')
- `timeframe`: Timeframe (e.g., '5m', '1h')
- `timestamp`: Candle timestamp
- `open`, `high`, `low`, `close`, `volume`: OHLCV data
- `created_at`: Record creation timestamp

### Trades Table (Phase 2)
- `id`: Primary key
- `symbol`: Trading symbol
- `side`: BUY or SELL
- `order_type`: market, limit
- `size`: Position size
- `entry_price`, `exit_price`: Execution prices
- `stop_loss`, `take_profit`: Risk management levels
- `leverage`: Leverage multiplier
- `pnl`, `pnl_pct`: Profit/loss
- `status`: open, closed, canceled
- `strategy`: Strategy name
- `confidence`: AI confidence score
- `entry_time`, `exit_time`: Timestamps
- `notes`: Additional information

### Performance Metrics Table (Phase 2)
- `id`: Primary key
- `metric_name`: Name of the metric
- `metric_value`: Value
- `symbol`, `strategy`, `timeframe`: Context
- `timestamp`: Measurement timestamp
- `metadata`: Additional data (JSON)

## Development Roadmap

### Phase 1: Foundation & Data Acquisition ✅ (Weeks 1-2)
- [x] Project structure and configuration
- [x] Data acquisition module
- [x] Technical indicators
- [x] Data storage (SQLite + Redis)
- [x] Logging system
- [x] Unit tests

### Phase 2: Core Trading Engine (Weeks 3-4)
- [ ] Strategy engine with plugin architecture
- [ ] Execution module with order management
- [ ] Risk management module
- [ ] Basic monitoring dashboard
- [ ] Simple RSI strategy for testing

### Phase 3: AI Integration (Weeks 5-6)
- [ ] DeepSeek API integration
- [ ] Multi-agent system (7 specialized agents)
- [ ] Prompt engineering
- [ ] Agent workflow orchestration
- [ ] AI decision testing

### Phase 4: Advanced Strategies (Weeks 7-8)
- [ ] Scalping strategy
- [ ] Momentum strategy
- [ ] Mean reversion strategy
- [ ] Leverage trading logic
- [ ] Strategy optimization

### Phase 5: Backtesting & Validation (Weeks 9-10)
- [ ] Backtesting framework
- [ ] Historical data preparation
- [ ] Comprehensive strategy testing
- [ ] Performance analysis
- [ ] Walk-forward optimization

### Phase 6: Live Trading Preparation (Weeks 11-12)
- [ ] Live/demo mode switching
- [ ] Production safety features
- [ ] Enhanced monitoring dashboard
- [ ] Security audit
- [ ] Extended paper trading

### Phase 7: Deployment & Monitoring (Week 13+)
- [ ] Production deployment
- [ ] Live trading with small capital
- [ ] Performance monitoring
- [ ] Iterative improvement
- [ ] Capital scaling

## Contributing

This is a private project currently in active development. Contributions will be accepted after Phase 7 completion.

## Security

### API Key Security
- Never commit API keys to version control
- Use environment variables for sensitive data
- Enable IP whitelisting on exchange accounts
- Disable withdrawal permissions on trading API keys
- Rotate API keys regularly

### Risk Management
- Start with demo mode (testnet)
- Test thoroughly before live trading
- Use small capital initially
- Set strict risk limits
- Monitor continuously

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'talib'`
**Solution**: Install TA-Lib system library before installing Python package

**Issue**: `redis.exceptions.ConnectionError`
**Solution**: Ensure Redis server is running: `redis-cli ping` should return `PONG`

**Issue**: `ccxt.ExchangeError: binance {"code":-2015,"msg":"Invalid API-key"}`
**Solution**: Verify API keys in `.env` file are correct and have proper permissions

**Issue**: Database locked error
**Solution**: Ensure only one instance of the bot is running

## Performance Expectations

### Phase 1 Performance
- Data fetch latency: <500ms per request
- Indicator calculation: <100ms for 1000 candles
- Database write: <50ms per batch
- Redis cache: <10ms per operation

### Future Performance Targets (Phase 7)
- Order execution latency: <1 second
- AI decision time: <30 seconds
- System uptime: >99%
- Data update frequency: 1-60 seconds

## License

Proprietary - All rights reserved

## Support

For questions or issues:
- Create an issue in the repository
- Contact: [Your contact information]

## Disclaimer

**IMPORTANT**: This trading bot is for educational and research purposes. Cryptocurrency trading involves substantial risk of loss. Never trade with money you cannot afford to lose. Past performance does not guarantee future results. The developers are not responsible for any financial losses incurred through the use of this software.

Always:
- Start with demo/paper trading
- Test thoroughly before using real capital
- Use proper risk management
- Monitor the system continuously
- Understand the risks involved

## Acknowledgments

- [CCXT](https://github.com/ccxt/ccxt) - Cryptocurrency exchange integration
- [TA-Lib](https://github.com/mrjbq7/ta-lib) - Technical analysis library
- [DeepSeek](https://www.deepseek.com/) - AI language model
- Inspired by [TradingAgents](https://tradingagents-ai.github.io/) and [Nof1 AI Alpha Arena](https://nof1.ai/)

---

**Version**: 0.1.0 (Phase 1)  
**Last Updated**: October 27, 2025  
**Status**: Active Development
