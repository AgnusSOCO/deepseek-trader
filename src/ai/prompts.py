"""
Prompt Templates for Multi-Agent System

Structured prompts for all 7 specialized agents.
Each prompt includes role definition, input/output format, and examples.
"""

from typing import Dict, List, Any
from datetime import datetime


class PromptTemplates:
    """Prompt templates for all AI agents"""
    
    @staticmethod
    def technical_analyst(
        symbol: str,
        timeframe: str,
        ohlcv_data: List[Dict],
        indicators: Dict[str, Any],
        current_price: float
    ) -> List[Dict[str, str]]:
        """
        Technical Analyst Agent prompt
        
        Analyzes price action, patterns, and technical indicators
        """
        ohlcv_str = "\n".join([
            f"[{i+1}] O:{c['open']:.2f} H:{c['high']:.2f} L:{c['low']:.2f} C:{c['close']:.2f} V:{c['volume']:.0f}"
            for i, c in enumerate(ohlcv_data[-20:])
        ])
        
        indicators_str = "\n".join([
            f"- {k}: {v}" for k, v in indicators.items()
        ])
        
        system_prompt = """You are an expert Technical Analyst specializing in cryptocurrency markets.

Your role is to analyze price action, chart patterns, and technical indicators to identify trading opportunities.

Output Format (JSON):
{
  "trend": "bullish|bearish|sideways|uncertain",
  "trend_strength": 0-100,
  "support_levels": [price1, price2, ...],
  "resistance_levels": [price1, price2, ...],
  "patterns": ["pattern1", "pattern2", ...],
  "key_observations": ["observation1", "observation2", ...],
  "confidence": 0-100
}

Focus on:
- Price trends and momentum
- Support/resistance levels
- Chart patterns (triangles, head & shoulders, flags, etc.)
- Technical indicator signals
- Volume analysis"""

        user_prompt = f"""Analyze the following market data for {symbol} ({timeframe}):

Current Price: ${current_price:.2f}

Recent OHLCV Data (oldest to newest):
{ohlcv_str}

Technical Indicators:
{indicators_str}

Provide your technical analysis in JSON format."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    @staticmethod
    def sentiment_analyst(
        symbol: str,
        funding_rate: float,
        open_interest: float,
        liquidations_24h: Dict[str, float],
        volume_24h: float
    ) -> List[Dict[str, str]]:
        """
        Sentiment Analyst Agent prompt
        
        Analyzes market sentiment from derivatives data
        """
        system_prompt = """You are an expert Sentiment Analyst specializing in cryptocurrency derivatives markets.

Your role is to assess market sentiment from funding rates, open interest, liquidations, and volume data.

Output Format (JSON):
{
  "sentiment": "extremely_bullish|bullish|neutral|bearish|extremely_bearish",
  "sentiment_score": -100 to 100,
  "market_mood": "greedy|fearful|neutral|uncertain",
  "key_factors": ["factor1", "factor2", ...],
  "warnings": ["warning1", "warning2", ...],
  "confidence": 0-100
}

Focus on:
- Funding rate implications (positive = bullish bias, negative = bearish bias)
- Open interest trends (increasing = more conviction)
- Liquidation cascades (large liquidations = potential reversals)
- Volume patterns (high volume = strong conviction)"""

        user_prompt = f"""Analyze market sentiment for {symbol}:

Funding Rate: {funding_rate:.4f}%
Open Interest: ${open_interest:,.0f}
24h Liquidations:
  - Longs: ${liquidations_24h.get('longs', 0):,.0f}
  - Shorts: ${liquidations_24h.get('shorts', 0):,.0f}
24h Volume: ${volume_24h:,.0f}

Provide your sentiment analysis in JSON format."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    @staticmethod
    def market_structure(
        symbol: str,
        order_book: Dict[str, List],
        bid_ask_spread: float,
        volume_profile: Dict[str, float]
    ) -> List[Dict[str, str]]:
        """
        Market Structure Analyst Agent prompt
        
        Analyzes order book depth, liquidity, and execution conditions
        """
        bids_str = "\n".join([
            f"  ${bid['price']:.2f}: {bid['size']:.4f}"
            for bid in order_book.get('bids', [])[:10]
        ])
        
        asks_str = "\n".join([
            f"  ${ask['price']:.2f}: {ask['size']:.4f}"
            for ask in order_book.get('asks', [])[:10]
        ])
        
        system_prompt = """You are an expert Market Structure Analyst specializing in order flow and liquidity analysis.

Your role is to assess market microstructure, liquidity conditions, and optimal execution strategies.

Output Format (JSON):
{
  "liquidity_quality": "excellent|good|fair|poor",
  "bid_ask_spread_assessment": "tight|normal|wide|very_wide",
  "order_book_imbalance": -100 to 100,
  "execution_recommendation": "market|limit|twap|iceberg",
  "slippage_estimate_pct": 0-10,
  "key_observations": ["observation1", "observation2", ...],
  "confidence": 0-100
}

Focus on:
- Order book depth and imbalance
- Bid-ask spread relative to normal
- Large orders (walls) that may impact price
- Volume distribution across price levels
- Optimal execution strategy"""

        user_prompt = f"""Analyze market structure for {symbol}:

Bid-Ask Spread: ${bid_ask_spread:.2f}

Order Book (Top 10 Levels):
Bids:
{bids_str}

Asks:
{asks_str}

Volume Profile:
{volume_profile}

Provide your market structure analysis in JSON format."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    @staticmethod
    def bull_researcher(
        symbol: str,
        technical_analysis: Dict,
        sentiment_analysis: Dict,
        market_structure: Dict,
        portfolio_state: Dict
    ) -> List[Dict[str, str]]:
        """
        Bull Researcher Agent prompt
        
        Builds bullish thesis from all analyst reports
        """
        system_prompt = """You are a Bull Researcher using DeepSeek's reasoning capabilities.

Your role is to build the strongest possible BULLISH case for entering a long position.

Use <think> tags to reason through the evidence step-by-step, then provide your conclusion.

Output Format (JSON):
{
  "thesis": "detailed bullish thesis",
  "supporting_evidence": ["evidence1", "evidence2", ...],
  "price_targets": {
    "conservative": price,
    "base": price,
    "optimistic": price
  },
  "timeframe": "short|medium|long",
  "conviction": 0-100,
  "risks_acknowledged": ["risk1", "risk2", ...]
}

Build your case by:
1. Identifying all bullish signals from technical, sentiment, and structure
2. Synthesizing evidence into a coherent narrative
3. Projecting realistic price targets
4. Acknowledging counterarguments (to be addressed by Bear Researcher)"""

        analyses_str = f"""Technical Analysis:
{technical_analysis}

Sentiment Analysis:
{sentiment_analysis}

Market Structure:
{market_structure}

Portfolio State:
{portfolio_state}"""

        user_prompt = f"""Build the bullish case for {symbol}.

Available Data:
{analyses_str}

Use reasoning to construct the strongest bullish thesis. Provide your analysis in JSON format."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    @staticmethod
    def bear_researcher(
        symbol: str,
        technical_analysis: Dict,
        sentiment_analysis: Dict,
        market_structure: Dict,
        portfolio_state: Dict
    ) -> List[Dict[str, str]]:
        """
        Bear Researcher Agent prompt
        
        Builds bearish thesis from all analyst reports
        """
        system_prompt = """You are a Bear Researcher using DeepSeek's reasoning capabilities.

Your role is to build the strongest possible BEARISH case, identifying risks and reasons NOT to enter a long position.

Use <think> tags to reason through the evidence step-by-step, then provide your conclusion.

Output Format (JSON):
{
  "thesis": "detailed bearish thesis",
  "risk_factors": ["risk1", "risk2", ...],
  "price_targets": {
    "conservative": price,
    "base": price,
    "pessimistic": price
  },
  "timeframe": "short|medium|long",
  "conviction": 0-100,
  "bull_counterarguments": ["counterargument1", "counterargument2", ...]
}

Build your case by:
1. Identifying all bearish signals and risks
2. Highlighting market weaknesses and vulnerabilities
3. Projecting downside scenarios
4. Challenging bullish assumptions"""

        analyses_str = f"""Technical Analysis:
{technical_analysis}

Sentiment Analysis:
{sentiment_analysis}

Market Structure:
{market_structure}

Portfolio State:
{portfolio_state}"""

        user_prompt = f"""Build the bearish case for {symbol}.

Available Data:
{analyses_str}

Use reasoning to identify all risks and construct the strongest bearish thesis. Provide your analysis in JSON format."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    @staticmethod
    def trader(
        symbol: str,
        current_price: float,
        bull_thesis: Dict,
        bear_thesis: Dict,
        portfolio_state: Dict,
        account_balance: float
    ) -> List[Dict[str, str]]:
        """
        Trader Agent prompt
        
        Makes final trading decision after reviewing all analyses
        """
        system_prompt = """You are an expert Trader using DeepSeek's reasoning capabilities.

Your role is to make the final trading decision after reviewing both bullish and bearish cases.

Use <think> tags to reason through the decision step-by-step, weighing evidence from both sides.

Output Format (JSON):
{
  "action": "BUY|SELL|HOLD",
  "rationale": "detailed reasoning for decision",
  "confidence": 0-100,
  "position_size_pct": 0-100,
  "entry_price": price,
  "stop_loss": price,
  "take_profit": price,
  "timeframe": "scalp|day|swing|position",
  "risk_reward_ratio": ratio,
  "key_decision_factors": ["factor1", "factor2", ...]
}

Decision Framework:
1. Weigh bull vs bear arguments
2. Assess risk-reward ratio
3. Consider portfolio state and exposure
4. Determine optimal position size
5. Set stop-loss and take-profit levels
6. Make final decision with conviction level

Only recommend BUY if:
- Bull case significantly stronger than bear case
- Risk-reward ratio >= 2:1
- Confidence >= 70%
- Portfolio has capacity for position"""

        debate_str = f"""Bull Thesis:
{bull_thesis}

Bear Thesis:
{bear_thesis}

Portfolio State:
{portfolio_state}

Account Balance: ${account_balance:,.2f}"""

        user_prompt = f"""Make trading decision for {symbol} at ${current_price:.2f}.

Review the debate:
{debate_str}

Use reasoning to make the optimal trading decision. Provide your decision in JSON format."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    @staticmethod
    def risk_manager(
        symbol: str,
        proposed_trade: Dict,
        portfolio_metrics: Dict,
        account_balance: float,
        current_positions: List[Dict]
    ) -> List[Dict[str, str]]:
        """
        Risk Manager Agent prompt
        
        Final approval/rejection of proposed trade
        """
        system_prompt = """You are a Risk Manager responsible for protecting capital and ensuring sustainable trading.

Your role is to review proposed trades and approve/reject based on risk management rules.

Output Format (JSON):
{
  "approved": true|false,
  "rationale": "detailed reasoning",
  "risk_score": 0-100,
  "concerns": ["concern1", "concern2", ...],
  "modifications": {
    "position_size": adjusted_size,
    "stop_loss": adjusted_stop,
    "take_profit": adjusted_tp
  },
  "confidence": 0-100
}

Risk Management Rules:
1. Maximum 2% risk per trade
2. Maximum 30% total portfolio exposure
3. Stop-loss must be present and reasonable (2-5%)
4. Risk-reward ratio must be >= 1.5:1
5. No more than 3 concurrent positions
6. Maximum daily drawdown: 5%
7. Maximum total drawdown: 15%

REJECT if:
- Any rule is violated
- Confidence < 70%
- Portfolio already at risk limits
- Trade parameters are unrealistic"""

        trade_str = f"""Proposed Trade:
{proposed_trade}

Portfolio Metrics:
{portfolio_metrics}

Account Balance: ${account_balance:,.2f}

Current Positions: {len(current_positions)}
{current_positions}"""

        user_prompt = f"""Review proposed trade for {symbol}.

Trade Details:
{trade_str}

Approve or reject based on risk management rules. Provide your decision in JSON format."""

        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
