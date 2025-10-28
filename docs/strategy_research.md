# Quant Strategy Research for AI Crypto Trading Bot

## Research Sources
- **freqtrade-strategies**: https://github.com/freqtrade/freqtrade-strategies (4.6k stars)
- **QuantConnect/Lean**: Popular algorithmic trading engine
- **Academic papers**: Turtle Trading, Donchian Channels, Mean Reversion
- **Trading literature**: Technical Analysis of Financial Markets, Algorithmic Trading

## Selected Strategies for Implementation

### 1. **Donchian Channel Breakout (Turtle Trading)**
**Source**: Richard Dennis's Turtle Trading system (1980s), widely documented
**Description**: Enter long when price breaks above N-period high, exit when price breaks below shorter M-period low
**Indicators Required**: 
- Donchian Channel (highest high, lowest low over N periods)
- ATR for position sizing
**Parameters**:
- Entry channel: 20 periods (default)
- Exit channel: 10 periods (default)
- Stop-loss: 2x ATR
**Proven Track Record**: Original Turtle Traders achieved 80%+ annual returns over 4 years
**Market Conditions**: Works best in trending markets
**Reference**: https://www.investopedia.com/articles/trading/08/turtle-trading.asp

### 2. **Keltner Channel Breakout**
**Source**: Chester Keltner (1960), refined by Linda Bradford Raschke
**Description**: Breakout strategy using EMA-based channels with ATR width
**Indicators Required**:
- EMA (20-period default)
- ATR (10-period default)
- Keltner Upper/Lower bands: EMA ± (multiplier × ATR)
**Parameters**:
- EMA period: 20
- ATR period: 10
- ATR multiplier: 2.0
- Stop-loss: 1.5x ATR
**Proven Track Record**: Used by professional traders, less whipsaw than Bollinger Bands
**Market Conditions**: Trending markets with moderate volatility
**Reference**: https://www.investopedia.com/terms/k/keltnerchannel.asp

### 3. **Connors RSI(2) Mean Reversion**
**Source**: Larry Connors, "Short Term Trading Strategies That Work" (2008)
**Description**: Buy when RSI(2) < 10 with price above SMA(200), sell when RSI(2) > 90
**Indicators Required**:
- RSI with 2-period lookback
- SMA(200) for trend filter
- Optional: SMA(5) for exit
**Parameters**:
- RSI period: 2
- RSI oversold: 10
- RSI overbought: 90
- Trend filter: SMA(200)
- Stop-loss: 2% or below recent swing low
**Proven Track Record**: Backtested extensively by Connors, 60%+ win rate on S&P 500
**Market Conditions**: Works in ranging and mildly trending markets
**Reference**: "Short Term Trading Strategies That Work" by Larry Connors

### 4. **SuperTrend Strategy**
**Source**: Olivier Seban, freqtrade community (validated implementation)
**Description**: ATR-based trend-following indicator that provides dynamic support/resistance
**Indicators Required**:
- ATR (10-period default)
- SuperTrend calculation: (High + Low)/2 ± (multiplier × ATR)
**Parameters**:
- ATR period: 10
- Multiplier: 3.0
- Multiple SuperTrend confirmation (3 indicators with different params)
**Proven Track Record**: Widely used in crypto/forex trading, freqtrade implementation has 6 months of testing
**Market Conditions**: Strong trending markets
**Reference**: https://github.com/freqtrade/freqtrade-strategies/blob/main/user_data/strategies/Supertrend.py

### 5. **Ichimoku Cloud Strategy**
**Source**: Goichi Hosoda (1960s), Japanese technical analysis
**Description**: Multi-component trend system with cloud, conversion/base lines, and lagging span
**Indicators Required**:
- Tenkan-sen (Conversion Line): (9-period high + 9-period low) / 2
- Kijun-sen (Base Line): (26-period high + 26-period low) / 2
- Senkou Span A (Leading Span A): (Tenkan + Kijun) / 2, shifted 26 periods forward
- Senkou Span B (Leading Span B): (52-period high + 52-period low) / 2, shifted 26 periods forward
- Chikou Span (Lagging Span): Close price shifted 26 periods backward
**Parameters**:
- Tenkan period: 9
- Kijun period: 26
- Senkou B period: 52
- Entry: Price above cloud, Tenkan > Kijun, Chikou above price
- Exit: Price below cloud or Tenkan < Kijun
**Proven Track Record**: Used by Japanese institutional traders for decades, comprehensive trend system
**Market Conditions**: All market conditions, provides clear trend direction
**Reference**: https://www.investopedia.com/terms/i/ichimoku-cloud.asp

## Implementation Priority
1. SuperTrend (already has freqtrade implementation to reference)
2. Donchian/Turtle (simple, proven, widely documented)
3. Keltner Channel (similar to Bollinger Bands we already have)
4. Connors RSI(2) (simple mean reversion, complements existing strategies)
5. Ichimoku (comprehensive but more complex)

## Scalping Strategy Fix
**Issue**: 0 trades with min_confidence=0.85
**Root Cause**: Equal-weight averaging of 4 signals (order_book excluded) requires almost all signals at max to reach 0.85
**Solution**:
- Use weighted averaging: vwap_deviation (0.4), price_momentum (0.3), volume_surge (0.2), bb_breakout (0.1)
- Lower min_confidence to 0.75
- Clamp all signal components to [-1, 1]

## Next Steps
1. Add new indicators to DataDownloader (Donchian, Keltner, SuperTrend, Ichimoku, RSI(2))
2. Implement 5 new strategy classes
3. Fix Scalping strategy with weighted averaging
4. Re-run backtests on all strategies
5. Document results and update PR
