# nof1.ai Alignment Plan

## Executive Summary

This plan aligns our autonomous trading bot with the nof1.ai approach while preserving our existing infrastructure. We'll add a single LLM agent strategy alongside our 19 rule-based strategies, implement nof1's risk management features, and enhance our execution system.

## Key Differences: nof1.ai vs Our Current Implementation

### nof1.ai Approach
- **Single LLM Agent**: DeepSeek V3.2 with comprehensive prompt
- **Structured Output**: JSON with action, symbol, leverage, position_size_percent, reasoning, confidence
- **Multi-timeframe Data**: 1m, 3m, 5m, 15m, 30m, 1h, 4h with time-series arrays
- **Risk Management**: 
  - 3 strategy profiles (conservative/balanced/aggressive)
  - Trailing stop-profit (+8%→+3%, +15%→+8%, +25%→+15%)
  - Account drawdown protection (15% = no new positions, 20% = close all)
  - 36-hour max holding time
  - Emphasis on BOTH long and short opportunities
- **Decision Loop**: Every 5 minutes
- **Exit Monitoring**: Continuous (implied fast checks)

### Our Current Implementation
- **19 Rule-based Strategies**: RSI, MACD, SuperTrend, etc.
- **Multi-agent Debate**: 7 agents (optional, behind flag)
- **Signal Selection**: Highest confidence wins
- **Risk Management**:
  - Daily loss limits (5%)
  - Daily trade limits (20)
  - Position sizing based on confidence
- **Decision Loop**: Every 3 minutes
- **Exit Monitoring**: Within decision loop (slow)

## Implementation Plan

### Phase N1: Data and Prompt Preparation (4-6 hours)

**Objectives:**
- Expand PriceFeed to support nof1 timeframes
- Build PromptBuilder for nof1-style context
- Add funding rate and order book data

**Tasks:**
1. **Expand PriceFeed Timeframes**
   - Add support for: 1m, 3m, 5m, 15m, 30m, 1h, 4h
   - Verify exchange support for each timeframe
   - Generate compact time-series arrays (last 50-200 points)
   - Store in memory for fast access

2. **Build PromptBuilder Class**
   - Format multi-timeframe market data
   - Include account metrics (balance, P&L, drawdown, Sharpe ratio)
   - Include current positions with leverage-aware pnl%
   - Include trade history (last 10 trades)
   - Include recent AI decisions for context
   - Generate nof1-style prompt structure

3. **Add Market Data Enhancements**
   - Fetch funding rates (if supported by exchange)
   - Fetch order book snapshots (top-of-book)
   - Add to prompt context

**Deliverables:**
- Enhanced PriceFeed with 7 timeframes
- PromptBuilder class (src/ai/prompt_builder.py)
- Configuration: PRICEFEED_TIMEFRAMES=1m,3m,5m,15m,30m,1h,4h

### Phase N2: SingleAgentStrategy Implementation (4-6 hours)

**Objectives:**
- Implement single LLM agent strategy matching nof1 approach
- Structured JSON output with validation
- Integration with existing engine

**Tasks:**
1. **Create SingleAgentStrategy Class**
   - Extends BaseStrategy
   - Uses PromptBuilder to generate context
   - Calls DeepSeek via OpenRouter
   - Validates structured JSON output (Pydantic)
   - Returns TradingSignal with all parameters

2. **Structured Output Schema**
   ```python
   {
     "action": "OPEN_LONG" | "OPEN_SHORT" | "CLOSE" | "HOLD",
     "symbol": "BTC/USDT",
     "leverage": 15-25,
     "position_size_percent": 15-32,
     "stop_loss_percent": -2.5 to -3.5,
     "take_profit_percent": 5-10,
     "reasoning": "Multi-timeframe analysis shows...",
     "confidence": 0.0-1.0
   }
   ```

3. **Configuration**
   - AI_SINGLE_AGENT_ENABLED=true|false
   - AI_MODEL_NAME=deepseek/deepseek-v3.2-exp
   - AI_MIN_CONFIDENCE=0.65
   - TRADING_STRATEGY=conservative|balanced|aggressive

**Deliverables:**
- SingleAgentStrategy class (src/strategies/single_agent_strategy.py)
- Structured output validation
- Integration with AutonomousDecisionEngine

### Phase N3: Risk & Exit Enhancements (4-6 hours)

**Objectives:**
- Add account-level drawdown protection
- Implement 36-hour max holding time
- Add tiered trailing stop-profit logic
- Create fast exit monitoring loop

**Tasks:**
1. **Account Drawdown Protection**
   - Track peak account equity
   - Calculate drawdown from peak and initial
   - 15% drawdown: Set "no new positions" flag
   - 20% drawdown: Close all positions and pause trading
   - Add to EnhancedRiskManager

2. **36-Hour Max Holding Time**
   - Add time-based exit check in ExitPlanMonitor
   - Force close positions after 36 hours regardless of P&L
   - Log warning at 34 hours

3. **Tiered Trailing Stop-Profit**
   - Track per-position peak pnl_percent (leverage-adjusted)
   - Implement tiered rules:
     - pnl ≥ +8%: Move stop to +3%
     - pnl ≥ +15%: Move stop to +8%
     - pnl ≥ +25%: Move stop to +15%
   - Peak pullback > 30%: Immediate close
   - Add to ExitPlanMonitor

4. **Fast Exit Monitoring Loop**
   - Separate async task running every 2-3 seconds
   - Uses PriceFeed.get_latest_price()
   - Checks all exit conditions immediately
   - Independent from 5-minute decision loop

**Deliverables:**
- Enhanced EnhancedRiskManager with drawdown protection
- Enhanced ExitPlanMonitor with TTL and tiered trailing
- Fast exit monitoring loop in AutonomousTradingSystem
- Configuration: MAX_HOLDING_HOURS=36

### Phase N4: Engine Alignment and Tests (4-6 hours)

**Objectives:**
- Align decision loop to 5 minutes
- Ensure both long and short support
- Add integration tests
- Verify derivatives trading support

**Tasks:**
1. **Loop Timing Alignment**
   - Set AUTONOMOUS_LOOP_INTERVAL=300 (5 minutes)
   - Verify exit monitoring runs every 2-3 seconds
   - Test timing accuracy

2. **Long/Short Support**
   - Verify exchange interface supports derivatives
   - Ensure MEXC uses 'swap' mode (not 'spot')
   - Test opening short positions
   - Update strategies to evaluate both directions

3. **Integration Tests**
   - Test structured JSON → execution mapping
   - Test drawdown gates (15%, 20%)
   - Test 36-hour TTL exit
   - Test tiered trailing profit
   - Test long/short execution
   - Test exit loop reacts <3s

4. **Exchange Configuration**
   - Verify derivatives endpoints
   - Check timeframe support
   - Test funding rate fetching
   - Test order book fetching

**Deliverables:**
- Updated loop timing
- Verified derivatives support
- Comprehensive integration tests
- Exchange configuration validation

### Phase N5: Paper Trading and Validation (1-2 days)

**Objectives:**
- Run paper trading with nof1-aligned system
- Validate behavior matches nof1 approach
- Compare with rule-based strategies

**Tasks:**
1. **Paper Trading Run**
   - Run for 24-48 hours
   - Record all decisions and trades
   - Monitor drawdown responses
   - Track exit timing

2. **Behavior Validation**
   - Verify tiered trailing profit triggers
   - Verify both long and short trades
   - Verify 36-hour exits
   - Verify drawdown protection
   - Compare AI vs rule-based performance

3. **Performance Analysis**
   - Win rate comparison
   - Sharpe ratio
   - Max drawdown
   - Trade frequency
   - Cost analysis

**Deliverables:**
- Paper trading report
- Behavior validation results
- Performance comparison
- Recommendations for live trading

## Configuration Changes

### New Environment Variables

```env
# nof1 Alignment Configuration
AI_SINGLE_AGENT_ENABLED=true
AI_MODEL_NAME=deepseek/deepseek-v3.2-exp
TRADING_STRATEGY=balanced  # conservative|balanced|aggressive

# Loop Timing
AUTONOMOUS_LOOP_INTERVAL=300  # 5 minutes
EXIT_MONITOR_INTERVAL=2  # 2 seconds

# Timeframes
PRICEFEED_TIMEFRAMES=1m,3m,5m,15m,30m,1h,4h

# Risk Management
MAX_HOLDING_HOURS=36
ACCOUNT_DRAWDOWN_WARN=15  # Percentage
ACCOUNT_DRAWDOWN_STOP=20  # Percentage

# Trailing Profit Tiers
TRAILING_PROFIT_TIER1=8  # Move SL to +3%
TRAILING_PROFIT_TIER2=15  # Move SL to +8%
TRAILING_PROFIT_TIER3=25  # Move SL to +15%
PEAK_PULLBACK_THRESHOLD=30  # Percentage

# Exchange Configuration
EXCHANGE_MODE=swap  # For derivatives trading
```

## Critical Considerations

### 1. Derivatives vs Spot Trading
- **Current**: PriceFeed uses 'spot' for MEXC
- **Required**: Must use 'swap' or 'future' for leverage and shorts
- **Action**: Update exchange configuration to derivatives mode

### 2. Exit Monitoring Cadence
- **Current**: Exit checks run in decision loop (3 minutes)
- **Required**: Fast exit loop (2-3 seconds) for immediate SL/TP
- **Action**: Add separate async task for exit monitoring

### 3. Timeframe Support
- **Risk**: Not all exchanges support all timeframes (e.g., 3m, 30m)
- **Action**: Verify exchange support and fallback to supported timeframes

### 4. Funding Rate and Order Book
- **Risk**: May not be supported by all exchanges via CCXT
- **Action**: Check support and gate features if unavailable

### 5. Leverage-Adjusted P&L
- **Current**: ExitPlanMonitor operates on price levels
- **Required**: Track leverage-adjusted pnl_percent
- **Action**: Add helper to compute pnl% with leverage

### 6. Structured Output Validation
- **Risk**: LLM may return invalid JSON
- **Action**: Strict schema validation with retries, default to HOLD on failure

## Success Criteria

### Phase N1
- ✅ PriceFeed supports 7 timeframes
- ✅ PromptBuilder generates nof1-style context
- ✅ Funding rate and order book data available

### Phase N2
- ✅ SingleAgentStrategy returns valid structured JSON
- ✅ Integration with existing engine works
- ✅ AI decisions route through risk management

### Phase N3
- ✅ Drawdown protection triggers at 15% and 20%
- ✅ 36-hour TTL forces position closure
- ✅ Tiered trailing profit adjusts stop-loss
- ✅ Exit monitoring responds <3 seconds

### Phase N4
- ✅ Decision loop runs every 5 minutes
- ✅ Both long and short positions work
- ✅ All integration tests pass
- ✅ Derivatives trading verified

### Phase N5
- ✅ Paper trading runs 24-48 hours without errors
- ✅ Behavior matches nof1 approach
- ✅ Performance metrics acceptable
- ✅ Ready for live trading

## Timeline

- **Phase N1**: 4-6 hours
- **Phase N2**: 4-6 hours
- **Phase N3**: 4-6 hours
- **Phase N4**: 4-6 hours
- **Phase N5**: 1-2 days

**Total**: 2-3 days of development + 1-2 days of validation

## Risks and Mitigations

### Risk 1: Exchange Doesn't Support Required Features
- **Mitigation**: Verify support early, implement fallbacks

### Risk 2: LLM Returns Invalid Decisions
- **Mitigation**: Strict validation, retries, safe defaults

### Risk 3: Fast Exit Loop Causes Performance Issues
- **Mitigation**: Optimize price fetching, use in-memory cache

### Risk 4: Derivatives Trading Not Configured
- **Mitigation**: Update exchange configuration, test thoroughly

### Risk 5: Cost Overruns from LLM Calls
- **Mitigation**: Set AI_MAX_COST_PER_DECISION, monitor usage

## Conclusion

This plan aligns our bot with nof1.ai's autonomous approach while preserving our existing infrastructure. We'll add a single LLM agent strategy alongside our 19 rule-based strategies, implement nof1's risk management features, and enhance our execution system for optimal performance.

The phased approach allows for incremental validation and reduces risk. Each phase has clear deliverables and success criteria. The entire implementation can be completed in 2-3 days of development plus 1-2 days of validation.
