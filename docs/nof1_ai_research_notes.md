# Nof1.ai Alpha Arena Research Notes

## Source
https://nof1.ai/blog/TechPost1 - "Exploring the Limits of Large Language Models (LLMs) as Quant Traders in Live Markets"

## Key Concept: Zero Human Interaction Trading

Nof1.ai gave 6 leading LLMs $10k each to trade autonomously in real markets with **zero human intervention**. This is directly relevant to our goal.

## Critical Design Principles for Autonomous Trading

### 1. Agent Loop Architecture
```
Every 2-3 minutes:
1. Receive live market data + account state
2. Process with LLM (system prompt + user prompt)
3. Return structured action (coin, direction, quantity, leverage, justification, confidence, exit plan)
4. Execute trade on exchange
5. Monitor position against exit plan
```

### 2. Action Space (Keep Simple)
- **Actions**: BUY (long), SELL (short), HOLD, CLOSE
- **Asset Universe**: Limited to 6 popular coins (BTC, ETH, SOL, BNB, DOGE, XRP)
- **Frequency**: Mid-to-low frequency (minutes to hours, not microseconds)
- **Leverage**: Allowed (increases capital efficiency and speeds feedback)

### 3. Required Output Fields (Critical for Autonomous Operation)
Each trade decision must include:
- **Coin**: Which asset to trade
- **Direction**: Long or short
- **Quantity**: Position size (computed by agent based on risk preference)
- **Leverage**: 1x-10x
- **Justification**: Short reasoning for the trade
- **Confidence Score**: [0, 1] - used for position sizing
- **Exit Plan**: Pre-defined profit targets, stop losses, invalidation conditions
- **Invalidation Conditions**: Specific signals that void the plan

### 4. Market Data Provided
- Current and historical mid-prices
- Volume data
- Selected technical indicators
- Short and long timescale features
- Account state (available cash, positions, PnL, Sharpe ratio)

### 5. Key Findings on Model Behavior

**Behavioral Differences Across Models:**
- **Bullish vs Bearish Tilt**: Some models (Grok, GPT-5, Gemini) short frequently; Claude rarely shorts
- **Holding Periods**: Large variation (Grok had longest holding times)
- **Trade Frequency**: Gemini most active, Grok least active
- **Risk Posture**: Qwen sizes positions largest, GPT-5/Gemini smallest
- **Confidence Scores**: Qwen reports highest confidence, GPT-5 lowest (decoupled from performance)
- **Exit Plan Tightness**: Qwen uses narrowest stops, Grok/DeepSeek loosest
- **Active Positions**: Some hold all 6 positions, Claude/Qwen hold 1-2 at a time

**Critical Failure Modes Discovered:**
1. **Ordering Bias**: Models misread data order (newest→oldest vs oldest→newest)
2. **Ambiguous Terms**: "Free collateral" vs "available cash" caused confusion
3. **Rule-Gaming**: Models complied with letter but not intent of constraints
4. **Self-Referential Confusion**: Models misread their own prior exit plans
5. **Over-Trading**: Early runs dominated by trading fees from too many small trades

### 6. Solutions to Over-Trading Problem
- Require explicit exit plans (targets, stops, invalidation)
- Encourage fewer but larger, higher-conviction positions
- Introduce leverage for capital efficiency
- Tie position size to model's confidence score
- Tighten prompt with clear rules

### 7. What's Missing (Future Improvements)
- **Regime Awareness**: No explicit market regime detection
- **State-Action History**: No access to prior trades/mistakes
- **Pyramiding**: Can't add to or reduce existing positions
- **Tool Use**: No code execution or web search
- **Multi-Agent**: No agent orchestration (yet)

## Implications for Our System

### Must-Have Features for Zero Human Interaction:
1. **Structured Output Format**: Every signal must include all required fields
2. **Exit Plan Enforcement**: Automatic monitoring and execution of stop-loss/take-profit
3. **Position Sizing Logic**: Confidence-based sizing with risk limits
4. **Invalidation Monitoring**: Track conditions that void the plan
5. **Fee Awareness**: Prevent over-trading by requiring minimum profit targets
6. **Clear Data Formatting**: Avoid ambiguous terms and ordering issues
7. **Self-Consistency Checks**: Validate that exit plans are executable

### Strategy Improvements Needed:
1. **Add Confidence Scores**: All strategies should output confidence [0, 1]
2. **Add Invalidation Conditions**: Define when to exit early (beyond stop-loss)
3. **Add Justification Field**: Short reasoning for each trade
4. **Leverage Integration**: Use confidence to determine leverage (1x-5x)
5. **Exit Plan Monitoring**: Track profit targets and invalidation conditions
6. **Regime Detection**: Detect trending vs ranging vs high volatility markets

### Workflow Automation:
1. **Continuous Loop**: Run every 2-3 minutes (not on every candle)
2. **Automatic Execution**: No manual approval needed
3. **Position Monitoring**: Check exit conditions every iteration
4. **Risk Management**: Enforce max positions, max leverage, daily loss limits
5. **Performance Tracking**: Log all decisions with justifications for analysis

## Key Takeaways

1. **Simplicity Works**: Limited action space (4 actions, 6 coins) is sufficient
2. **Exit Plans Are Critical**: Pre-defined targets/stops prevent indecision
3. **Confidence-Based Sizing**: Tie position size to model confidence
4. **Over-Trading Is The Enemy**: Fees dominate PnL if trading too frequently
5. **Prompt Engineering Matters**: Small changes cause large behavioral differences
6. **Real-World Testing Required**: Paper trading doesn't surface execution challenges

## Next Steps for Our Implementation

1. Add confidence scoring to all strategies
2. Implement exit plan monitoring system
3. Add invalidation condition tracking
4. Implement confidence-based position sizing
5. Add regime detection for strategy selection
6. Create continuous trading loop (2-3 min intervals)
7. Add comprehensive logging with justifications
8. Test on real exchange (testnet first)
