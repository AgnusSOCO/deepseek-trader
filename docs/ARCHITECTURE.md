# System Architecture - AI Cryptocurrency Trading Bot

Complete technical architecture documentation for the autonomous trading system.

## Table of Contents

1. [Overview](#overview)
2. [System Components](#system-components)
3. [Data Flow](#data-flow)
4. [nof1.ai Alignment](#nof1ai-alignment)
5. [Technology Stack](#technology-stack)
6. [Design Patterns](#design-patterns)
7. [Scalability & Performance](#scalability--performance)

---

## Overview

The AI Cryptocurrency Trading Bot is an autonomous trading system that uses DeepSeek LLM for trading decisions, combined with rule-based strategies and comprehensive risk management. The system is designed for zero human interaction once deployed.

### Key Features

- **Autonomous Operation**: Runs continuously with 5-minute decision loops
- **AI-Powered Decisions**: Uses DeepSeek Chat V3.1 for trading analysis
- **Multi-Strategy**: Supports 15+ trading strategies (momentum, mean reversion, scalping, etc.)
- **Comprehensive Risk Management**: Account drawdown protection, position limits, daily loss limits
- **nof1.ai Alignment**: 36-hour TTL, tiered trailing stops, leverage-adjusted P&L
- **Paper Trading**: Full simulation mode for validation
- **Real-Time Monitoring**: Web dashboard and comprehensive logging

### Architecture Principles

1. **Safety First**: Multiple layers of risk management and safety checks
2. **Modularity**: Clear separation of concerns with well-defined interfaces
3. **Testability**: Comprehensive test coverage (70+ tests)
4. **Observability**: Detailed logging and metrics at every level
5. **Resilience**: Error recovery, circuit breakers, graceful degradation

---

## System Components

### 1. Data Layer

#### PriceFeed (`src/data/price_feed.py`)

**Purpose**: Real-time market data acquisition and management

**Key Features**:
- Multi-exchange support (Bybit, Binance, MEXC) via CCXT
- 7 timeframes (1m, 3m, 5m, 15m, 30m, 1h, 4h)
- Hybrid data mode: REST API + fast ticker polling
- Technical indicator calculation (RSI, EMA, MACD, BB, ATR, etc.)
- Funding rate and order book fetching
- In-memory candle management with automatic updates

**Data Structure**:
```python
{
    'symbol': 'BTC/USDT',
    'timeframes': {
        '1m': {'close': [...], 'volume': [...], 'rsi': [...], ...},
        '5m': {'close': [...], 'volume': [...], 'ema_12': [...], ...},
        ...
    }
}
```

**Performance**:
- 2-second ticker polling for instant price updates
- 500-1000 candle lookback for indicator calculation
- Redis caching for frequently accessed data

#### Storage (`src/data/storage.py`)

**Purpose**: Persistent storage for trades, positions, and metrics

**Database Schema**:
- `trades`: Trade execution history
- `positions`: Open and closed positions
- `metrics`: Performance metrics snapshots
- `signals`: Trading signals generated

**Technology**: SQLite (default) or PostgreSQL (production)

---

### 2. Strategy Layer

#### BaseStrategy (`src/strategies/base_strategy.py`)

**Purpose**: Abstract base class for all trading strategies

**Interface**:
```python
class BaseStrategy(ABC):
    @abstractmethod
    def initialize(self) -> None
    
    @abstractmethod
    async def on_data(self, symbol: str, timeframe: str, data: Dict) -> None
    
    @abstractmethod
    async def generate_signal(self, symbol: str, timeframe: str, indicators: Dict) -> Optional[TradingSignal]
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]
```

**TradingSignal Structure**:
```python
@dataclass
class TradingSignal:
    action: SignalAction  # BUY, SELL, HOLD
    symbol: str
    timestamp: datetime
    confidence: float  # 0.0 to 1.0
    price: float
    position_size: float  # Percentage of capital
    stop_loss: Optional[float]
    take_profit: Optional[float]
    metadata: Dict[str, Any]
```

#### Strategy Implementations

**Rule-Based Strategies** (10 strategies):
1. **MomentumStrategy**: EMA crossover + ADX trend strength
2. **MeanReversionStrategy**: Bollinger Bands + RSI extremes
3. **ScalpingStrategy**: High-frequency with order book analysis
4. **UniversalMacdStrategy**: Normalized MACD for all price levels
5. **MultiSuperTrendStrategy**: 3 SuperTrend confirmations
6. **AdxSmaStrategy**: SMA crossover with ADX filter
7. **BandtasticStrategy**: 4-level Bollinger Bands
8. **VolatilitySystemStrategy**: ATR breakout with pyramiding
9. **IchimokuStrategy**: Ichimoku Cloud system
10. **KeltnerStrategy**: Keltner Channel breakouts

**AI-Powered Strategy**:
- **SingleAgentStrategy**: Uses DeepSeek Chat V3.1 for decisions
  - Analyzes 7 timeframes of market data
  - Considers funding rates and order book
  - Returns structured JSON with full trade specification
  - Includes confidence, reasoning, and invalidation conditions

#### StrategyManager (`src/strategies/strategy_manager.py`)

**Purpose**: Orchestrates multiple strategies and aggregates signals

**Features**:
- Weighted signal aggregation
- Market regime detection (trending, sideways, high volatility)
- Dynamic strategy activation based on regime
- Capital allocation across strategies
- Combined exposure limits

---

### 3. Risk Management Layer

#### EnhancedRiskManager (`src/autonomous/enhanced_risk_manager.py`)

**Purpose**: Comprehensive risk management and position sizing

**Key Features**:

1. **Account-Level Protection**:
   - 15% drawdown warning (no new positions)
   - 20% drawdown stop (pause all trading)
   - Peak capital tracking

2. **Daily Limits**:
   - Maximum daily loss percentage (default: 5%)
   - Maximum daily trades (default: 20)
   - Automatic reset at midnight

3. **Position Sizing**:
   - Confidence-based sizing (higher confidence = larger size)
   - Per-symbol exposure limits (default: 20%)
   - Maximum position size (default: 20% of capital)
   - Minimum position size (default: 1% of capital)

4. **Validation Checks**:
   - `can_trade_today()`: Checks daily limits
   - `can_open_position(symbol)`: Checks symbol exposure
   - `check_drawdown_protection()`: Updates protection flags
   - `calculate_position_size()`: Confidence-based sizing

**Risk Calculation**:
```python
# Confidence-based position sizing
base_size = max_position_size_pct
confidence_multiplier = (confidence - min_confidence) / (1.0 - min_confidence)
position_size = base_size * confidence_multiplier

# Clamped to min/max limits
position_size = max(min_position_size_pct, min(position_size, max_position_size_pct))
```

#### ExitPlanMonitor (`src/autonomous/exit_plan_monitor.py`)

**Purpose**: Monitor and enforce exit conditions for open positions

**Key Features**:

1. **36-Hour TTL**:
   - Maximum holding time: 36 hours
   - Automatic exit after timeout
   - Leverage-adjusted P&L calculation at exit

2. **Tiered Trailing Stops**:
   - +8% profit → move stop to +3%
   - +15% profit → move stop to +8%
   - +25% profit → move stop to +15%
   - 30% pullback from peak → immediate exit

3. **Invalidation Conditions**:
   - Strategy-specific conditions (e.g., "ADX < 25")
   - Checked every loop iteration
   - Automatic exit if conditions met

4. **Stop-Loss & Take-Profit**:
   - Standard stop-loss monitoring
   - Take-profit target monitoring
   - Supports both long and short positions

**Exit Plan Structure**:
```python
@dataclass
class ExitPlan:
    position_id: str
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: float
    invalidation_conditions: List[str]
    created_at: datetime
    leverage: float
    peak_pnl_pct: float = 0.0
    tiered_trailing_enabled: bool = True
```

---

### 4. Execution Layer

#### OrderManager (`src/execution/order_manager.py`)

**Purpose**: Execute trades on exchanges with retry logic

**Features**:
- Order lifecycle tracking (pending → filled → closed)
- Retry logic with exponential backoff
- Slippage handling
- Fee calculation
- Order validation

#### ExchangeInterface (`src/execution/exchange_interface.py`)

**Purpose**: Abstraction layer for exchange APIs

**Supported Exchanges**:
- Binance (spot & futures)
- Bybit (spot & derivatives)
- MEXC (spot)

**Methods**:
- `create_order()`: Place market/limit orders
- `cancel_order()`: Cancel pending orders
- `get_order()`: Fetch order status
- `get_balance()`: Get account balance
- `get_positions()`: Get open positions

#### PaperTradingEngine (`src/execution/paper_trading.py`)

**Purpose**: Simulate live trading without real capital

**Features**:
- Realistic slippage (0.05%)
- Maker/taker fees (0.02%/0.06%)
- Position management (open/close)
- Leverage-adjusted P&L
- Performance metrics
- Trade history logging
- Session reports

**Use Cases**:
- Pre-production validation
- Strategy testing
- Parameter optimization
- Risk-free experimentation

---

### 5. Autonomous Trading Layer

#### AutonomousDecisionEngine (`src/autonomous/autonomous_decision_engine.py`)

**Purpose**: Main decision-making loop for autonomous trading

**Decision Loop** (every 5 minutes):

1. **Check Daily Limits**:
   - Verify trading not paused
   - Check daily loss/trade limits
   - Update drawdown protection

2. **Monitor Existing Positions**:
   - Check exit conditions (stop-loss, take-profit, TTL, invalidation)
   - Execute exits if needed
   - Update exit plans with tiered trailing stops

3. **Generate New Signals**:
   - Run all active strategies in parallel
   - Collect signals from each strategy
   - Filter by minimum confidence threshold

4. **Select Best Signal**:
   - Choose signal with highest confidence
   - Validate against risk limits
   - Calculate position size

5. **Execute Trade**:
   - Create exit plan
   - Place order via OrderManager
   - Log decision with full justification

**Error Handling**:
- Try/except around each step
- Continue on non-critical errors
- Log all errors for review
- Automatic recovery on next iteration

#### AutonomousTradingSystem (`src/autonomous/autonomous_trading_system.py`)

**Purpose**: Main orchestrator for the entire system

**Components**:
- AutonomousDecisionEngine
- PerformanceMonitor
- ErrorRecoveryManager
- Web Dashboard (FastAPI)

**Parallel Execution**:
```python
async def run():
    await asyncio.gather(
        decision_engine.run(),      # Main trading loop
        performance_monitor.run(),  # Metrics collection
        health_checker.run(),       # System health
        dashboard.run()             # Web interface
    )
```

**Graceful Shutdown**:
- Signal handlers (SIGINT, SIGTERM)
- Close all positions (optional)
- Save final state
- Generate session report

---

### 6. AI Integration Layer

#### OpenRouterClient (`src/ai/openrouter_client.py`)

**Purpose**: Interface to DeepSeek models via OpenRouter

**Features**:
- Async API calls
- Retry logic with exponential backoff
- Rate limiting
- Cost tracking
- Response caching

**Models Used**:
- `deepseek/deepseek-chat`: Fast analysis and decisions
- `deepseek/deepseek-reasoner`: Deep reasoning for complex scenarios

#### PromptBuilder (`src/ai/prompt_builder.py`)

**Purpose**: Build structured prompts for LLM

**Prompt Structure**:
```
=== MARKET DATA ===
Symbol: BTC/USDT
Current Price: $50,000
24h Change: +2.5%

=== TECHNICAL INDICATORS (7 timeframes) ===
1m: RSI=65, EMA12=49800, ...
5m: RSI=68, EMA12=49900, ...
...

=== FUNDING RATE ===
Current Rate: 0.01% (longs paying shorts)

=== ORDER BOOK ===
Bid depth: $2.5M, Ask depth: $2.3M
Imbalance: +8% (bullish)

=== INSTRUCTIONS ===
Analyze and return JSON with:
{
  "action": "OPEN_LONG|OPEN_SHORT|CLOSE|HOLD",
  "symbol": "BTC/USDT",
  "leverage": 1-25,
  "position_size_percent": 1-25,
  "stop_loss_percent": -1 to -5,
  "take_profit_percent": 3-15,
  "reasoning": "...",
  "confidence": 0.0-1.0
}
```

#### ResponseParser (`src/ai/response_parser.py`)

**Purpose**: Parse and validate LLM responses

**Features**:
- JSON extraction from text
- Pydantic validation
- Schema enforcement
- Error handling with retries
- Fallback to HOLD on parse errors

---

### 7. Monitoring Layer

#### PerformanceMonitor (`src/autonomous/performance_monitor.py`)

**Purpose**: Track and analyze system performance

**Metrics Collected**:
- Real-time capital and P&L
- Position count and exposure
- Trade statistics (win rate, profit factor)
- Drawdown tracking
- Strategy performance
- System uptime

**Metric Snapshots**:
- Saved every 5 minutes
- Stored in database
- Used for historical analysis

#### Web Dashboard (`src/autonomous/dashboard.py`)

**Purpose**: Real-time monitoring interface

**Endpoints**:
- `GET /`: Dashboard HTML
- `GET /api/status`: System status
- `GET /api/metrics`: Performance metrics
- `GET /api/positions`: Open positions
- `GET /api/trades`: Recent trades
- `POST /api/stop`: Emergency stop

**Features**:
- Auto-refresh every 5 seconds
- Real-time capital display
- Position table
- Trade history
- Performance charts (future)

#### Logging System (`src/autonomous/logging_config.py`)

**Purpose**: Comprehensive logging infrastructure

**Log Handlers**:
1. **Console**: INFO level, colored output
2. **Main Log**: All levels, rotating (10MB, 10 backups)
3. **Error Log**: ERROR level only
4. **Trade Log**: Trade-specific events
5. **JSON Log**: Structured logging for analysis

**Log Rotation**:
- Size-based: 10MB per file
- Time-based: Daily rotation
- Backup count: 10 files

---

## Data Flow

### Trading Decision Flow

```
┌─────────────────┐
│  Price Feed     │ ← Exchange APIs (CCXT)
│  (Market Data)  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Strategies     │ ← Generate signals
│  (15+ types)    │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Strategy Manager│ ← Aggregate & filter
│ (Signal Fusion) │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  Risk Manager   │ ← Validate & size
│  (Safety Checks)│
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Decision Engine │ ← Select best signal
│ (Orchestrator)  │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Order Manager   │ ← Execute trade
│ (Execution)     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Exit Monitor    │ ← Track & enforce exits
│ (Position Mgmt) │
└─────────────────┘
```

### AI Decision Flow (SingleAgentStrategy)

```
┌─────────────────┐
│  Price Feed     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Prompt Builder  │ ← Format market data
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ OpenRouter API  │ ← DeepSeek Chat V3.1
│ (LLM Call)      │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│Response Parser  │ ← Extract & validate JSON
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│ Trading Signal  │ ← Convert to signal
└─────────────────┘
```

### Exit Monitoring Flow

```
┌─────────────────┐
│ Open Positions  │
└────────┬────────┘
         │
         ↓ (every 5 min)
┌─────────────────┐
│ Exit Monitor    │
└────────┬────────┘
         │
         ├──→ Check Stop-Loss
         ├──→ Check Take-Profit
         ├──→ Check 36-Hour TTL
         ├──→ Check Invalidation Conditions
         └──→ Check Tiered Trailing Stops
                │
                ↓ (if exit needed)
         ┌─────────────────┐
         │ Close Position  │
         └─────────────────┘
```

---

## nof1.ai Alignment

The system implements key features from the nof1.ai autonomous trading approach:

### 1. Structured JSON Output

**Implementation**: `SingleAgentStrategy` + `TradingDecision` Pydantic model

LLM returns validated JSON with all trade parameters:
```json
{
  "action": "OPEN_LONG",
  "symbol": "BTC/USDT",
  "leverage": 20,
  "position_size_percent": 25,
  "stop_loss_percent": -3.0,
  "take_profit_percent": 8.0,
  "reasoning": "Strong bullish momentum with ADX > 30",
  "confidence": 0.85
}
```

### 2. Account Drawdown Protection

**Implementation**: `EnhancedRiskManager.check_drawdown_protection()`

- **15% Warning**: `no_new_positions = True` (close only)
- **20% Stop**: `trading_paused = True` (no trading)
- Automatic recovery when drawdown improves

### 3. 36-Hour Position TTL

**Implementation**: `ExitPlanMonitor.check_exit_conditions()`

- Maximum holding time: 36 hours
- Automatic exit after timeout
- Leverage-adjusted P&L calculation
- Logged with reason: `ExitReason.TIMEOUT`

### 4. Tiered Trailing Profit

**Implementation**: `ExitPlanMonitor.check_tiered_trailing_profit()`

Profit levels and stop adjustments:
- +8% profit → stop at +3% (lock in 3%)
- +15% profit → stop at +8% (lock in 8%)
- +25% profit → stop at +15% (lock in 15%)
- 30% pullback from peak → immediate exit

### 5. Leverage-Adjusted P&L

**Implementation**: `PaperPosition.calculate_pnl()`

```python
price_change_pct = (current_price - entry_price) / entry_price
pnl_pct = price_change_pct * leverage * 100
```

Example: 2% price move with 10x leverage = 20% P&L

### 6. 5-Minute Decision Loop

**Implementation**: `AutonomousDecisionEngine.run()`

- Loop interval: 300 seconds (5 minutes)
- Configurable via `AUTONOMOUS_LOOP_INTERVAL`
- Ensures timely decision-making without over-trading

### 7. Confidence-Based Position Sizing

**Implementation**: `EnhancedRiskManager.calculate_position_size()`

Higher confidence → larger position size (within limits)

---

## Technology Stack

### Core Technologies

- **Python 3.10+**: Main programming language
- **AsyncIO**: Asynchronous I/O for concurrent operations
- **CCXT**: Cryptocurrency exchange integration
- **TA-Lib**: Technical analysis indicators
- **Pydantic**: Data validation and settings management
- **FastAPI**: Web dashboard and API
- **SQLAlchemy**: Database ORM
- **Redis**: Caching and real-time state

### AI/ML Stack

- **OpenRouter**: LLM API gateway
- **DeepSeek Chat V3.1**: Trading analysis and decisions
- **DeepSeek Reasoner**: Deep reasoning for complex scenarios

### Testing & Quality

- **pytest**: Unit and integration testing
- **pytest-asyncio**: Async test support
- **pytest-cov**: Code coverage
- **unittest.mock**: Mocking for tests

### Deployment

- **systemd**: Service management
- **Docker**: Containerization (optional)
- **Git**: Version control
- **GitHub Actions**: CI/CD (optional)

---

## Design Patterns

### 1. Strategy Pattern

**Used In**: Trading strategies

All strategies implement `BaseStrategy` interface, allowing easy addition of new strategies without modifying existing code.

### 2. Factory Pattern

**Used In**: Strategy initialization

`StrategyManager` creates strategy instances based on configuration.

### 3. Observer Pattern

**Used In**: Price feed updates

Strategies subscribe to price feed updates and react to new data.

### 4. Singleton Pattern

**Used In**: System-wide components

`AutonomousTradingSystem` ensures single instance of core components.

### 5. Circuit Breaker Pattern

**Used In**: Error recovery

`ErrorRecoveryManager` implements circuit breaker to prevent cascading failures.

### 6. Repository Pattern

**Used In**: Data access

`Storage` class abstracts database operations from business logic.

---

## Scalability & Performance

### Current Limitations

- **Single Instance**: Designed for single-server deployment
- **SQLite**: Default database not suitable for high concurrency
- **In-Memory State**: Limited by server RAM

### Scaling Strategies

#### Horizontal Scaling

1. **Multiple Symbols**: Run separate instances per symbol
2. **Strategy Sharding**: Distribute strategies across instances
3. **Load Balancing**: Use Redis for shared state

#### Vertical Scaling

1. **Increase Resources**: More CPU/RAM for single instance
2. **PostgreSQL**: Replace SQLite for better performance
3. **Redis Cluster**: Distributed caching

#### Performance Optimization

1. **Caching**: Redis for frequently accessed data
2. **Batch Processing**: Group API calls where possible
3. **Async Operations**: Maximize concurrent execution
4. **Database Indexing**: Optimize query performance

### Monitoring & Observability

1. **Metrics**: Prometheus + Grafana (future)
2. **Logging**: ELK stack (future)
3. **Alerting**: PagerDuty/Slack integration (future)
4. **Tracing**: OpenTelemetry (future)

---

## Security Considerations

### API Key Management

- Environment variables only
- Never committed to version control
- Rotation policy recommended
- Withdrawal permissions disabled

### Network Security

- Firewall configuration (ufw)
- SSH key authentication
- VPN for remote access (optional)
- Rate limiting on dashboard

### Data Security

- Database encryption at rest
- Secure log storage
- Regular backups
- Access control

### Operational Security

- Principle of least privilege
- Regular security audits
- Dependency updates
- Incident response plan

---

## Future Enhancements

### Short-Term (1-3 months)

1. **Enhanced Monitoring**: Prometheus metrics, Grafana dashboards
2. **Telegram Alerts**: Real-time notifications
3. **Strategy Optimization**: Walk-forward optimization framework
4. **Multi-Exchange**: Simultaneous trading on multiple exchanges

### Medium-Term (3-6 months)

1. **Machine Learning**: ML-based strategy selection
2. **Portfolio Optimization**: Modern portfolio theory integration
3. **Advanced Risk Models**: VaR, CVaR calculations
4. **Backtesting Framework**: Historical strategy validation

### Long-Term (6-12 months)

1. **Multi-Agent System**: Specialized AI agents (as in original Phase 3)
2. **Distributed Architecture**: Microservices with Kubernetes
3. **Advanced AI**: Reinforcement learning for strategy adaptation
4. **Social Trading**: Copy trading and signal sharing

---

## Conclusion

This architecture provides a solid foundation for autonomous cryptocurrency trading with comprehensive risk management, multiple strategy support, and AI integration. The modular design allows for easy extension and customization while maintaining safety and reliability.

**Key Strengths**:
- Comprehensive risk management
- nof1.ai alignment for proven autonomous trading
- Extensive testing and validation
- Clear separation of concerns
- Production-ready monitoring and logging

**Areas for Improvement**:
- Horizontal scalability
- Advanced ML integration
- Multi-exchange arbitrage
- Real-time performance optimization

For implementation details, refer to:
- `docs/DEPLOYMENT_GUIDE.md` - Deployment instructions
- `docs/TROUBLESHOOTING.md` - Common issues and solutions
- Source code documentation in each module
