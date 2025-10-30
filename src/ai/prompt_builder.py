"""
PromptBuilder for nof1-style LLM Trading Prompts

Generates comprehensive trading prompts with:
- Multi-timeframe market data
- Account metrics (balance, P&L, drawdown, Sharpe)
- Current positions with leverage-aware P&L
- Trade history
- Recent AI decisions
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds nof1-style comprehensive trading prompts for LLM agents
    """
    
    def __init__(
        self,
        strategy_name: str = "balanced",
        interval_minutes: int = 5
    ):
        """
        Initialize prompt builder
        
        Args:
            strategy_name: Trading strategy (conservative/balanced/aggressive)
            interval_minutes: Decision loop interval in minutes
        """
        self.strategy_name = strategy_name
        self.interval_minutes = interval_minutes
        
        self.strategy_params = self._get_strategy_params(strategy_name)
    
    def _get_strategy_params(self, strategy: str) -> Dict[str, Any]:
        """Get strategy-specific parameters"""
        strategies = {
            "conservative": {
                "leverage_min": 15,
                "leverage_max": 20,
                "position_size_min": 15,
                "position_size_max": 25,
                "stop_loss": {"low": -2.5, "mid": -3.0, "high": -3.5},
                "risk_tolerance": "Conservative - prioritize capital preservation",
                "trading_style": "Patient approach, wait for high-confidence setups"
            },
            "balanced": {
                "leverage_min": 18,
                "leverage_max": 23,
                "position_size_min": 20,
                "position_size_max": 28,
                "stop_loss": {"low": -2.8, "mid": -3.3, "high": -3.8},
                "risk_tolerance": "Balanced - moderate risk for moderate returns",
                "trading_style": "Balanced approach, trade good opportunities"
            },
            "aggressive": {
                "leverage_min": 20,
                "leverage_max": 25,
                "position_size_min": 25,
                "position_size_max": 32,
                "stop_loss": {"low": -3.0, "mid": -3.5, "high": -4.0},
                "risk_tolerance": "Aggressive - maximize returns with calculated risk",
                "trading_style": "Active trading, capitalize on all valid signals"
            }
        }
        
        return strategies.get(strategy, strategies["balanced"])
    
    def build_prompt(
        self,
        symbol: str,
        market_data: Dict[str, Dict[str, List[float]]],
        account_info: Dict[str, Any],
        positions: List[Dict[str, Any]],
        trade_history: List[Dict[str, Any]],
        recent_decisions: List[Dict[str, Any]],
        funding_rate: Optional[Dict[str, Any]] = None,
        order_book: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build comprehensive nof1-style trading prompt
        
        Args:
            symbol: Trading pair
            market_data: Multi-timeframe time-series data
            account_info: Account balance, P&L, drawdown, Sharpe
            positions: Current open positions
            trade_history: Recent trade history (last 10)
            recent_decisions: Recent AI decisions for context
            funding_rate: Funding rate info (optional)
            order_book: Order book snapshot (optional)
            
        Returns:
            Formatted prompt string
        """
        prompt = f"""You are an autonomous cryptocurrency trading agent managing a {self.strategy_name} strategy.

=== ACCOUNT STATUS ===
Balance: ${account_info.get('balance', 0):.2f} USDT
Unrealized P&L: ${account_info.get('unrealized_pnl', 0):.2f} USDT
Total Equity: ${account_info.get('total_equity', 0):.2f} USDT
Peak Equity: ${account_info.get('peak_equity', 0):.2f} USDT
Drawdown from Peak: {account_info.get('drawdown_percent', 0):.2f}%
Daily P&L: ${account_info.get('daily_pnl', 0):.2f} USDT
Sharpe Ratio: {account_info.get('sharpe_ratio', 0):.2f}

"""
        
        drawdown = account_info.get('drawdown_percent', 0)
        if drawdown >= 20:
            prompt += f"🚨 CRITICAL WARNING: Account drawdown {drawdown:.2f}% - MUST CLOSE ALL POSITIONS AND STOP TRADING!\n\n"
        elif drawdown >= 15:
            prompt += f"⚠️ WARNING: Account drawdown {drawdown:.2f}% - NO NEW POSITIONS ALLOWED! Only manage existing positions.\n\n"
        elif drawdown >= 10:
            prompt += f"⚠️ CAUTION: Account drawdown {drawdown:.2f}% - Trade carefully.\n\n"
        
        prompt += self._format_positions(positions)
        
        prompt += self._format_market_data(symbol, market_data)
        
        if funding_rate:
            prompt += self._format_funding_rate(funding_rate)
        
        if order_book:
            prompt += self._format_order_book(order_book)
        
        prompt += self._format_trade_history(trade_history)
        
        prompt += self._format_recent_decisions(recent_decisions)
        
        prompt += self._format_trading_rules()
        
        return prompt
    
    def _format_positions(self, positions: List[Dict[str, Any]]) -> str:
        """Format current positions section"""
        if not positions:
            return "=== CURRENT POSITIONS ===\nNo open positions\n\n"
        
        section = "=== CURRENT POSITIONS ===\n"
        
        for pos in positions:
            side = pos.get('side', 'unknown')
            symbol = pos.get('symbol', 'unknown')
            leverage = pos.get('leverage', 1)
            entry_price = pos.get('entry_price', 0)
            current_price = pos.get('current_price', 0)
            unrealized_pnl = pos.get('unrealized_pnl', 0)
            
            price_change_pct = 0
            if entry_price > 0:
                price_change_pct = ((current_price - entry_price) / entry_price * 100)
                if side == 'short':
                    price_change_pct *= -1
            
            pnl_percent = price_change_pct * leverage
            
            opened_at = pos.get('opened_at', datetime.now())
            if isinstance(opened_at, str):
                opened_at = datetime.fromisoformat(opened_at)
            
            holding_hours = (datetime.now() - opened_at).total_seconds() / 3600
            remaining_hours = max(0, 36 - holding_hours)
            
            section += f"\nPosition: {symbol} {'LONG' if side == 'long' else 'SHORT'}\n"
            section += f"  Leverage: {leverage}x\n"
            section += f"  P&L: {pnl_percent:+.2f}% (leverage-adjusted) | ${unrealized_pnl:+.2f} USDT\n"
            section += f"  Entry: ${entry_price:.2f} | Current: ${current_price:.2f}\n"
            section += f"  Holding Time: {holding_hours:.1f}h | Remaining: {remaining_hours:.1f}h until 36h limit\n"
            
            if remaining_hours < 2:
                section += f"  ⚠️ URGENT: Must close within 2 hours!\n"
            elif remaining_hours < 4:
                section += f"  ⚠️ WARNING: Approaching 36h limit, prepare to close\n"
            
            peak_pnl = pos.get('peak_pnl_percent', pnl_percent)
            if peak_pnl > pnl_percent:
                pullback = ((peak_pnl - pnl_percent) / peak_pnl * 100) if peak_pnl > 0 else 0
                section += f"  Peak P&L: {peak_pnl:+.2f}% | Pullback: {pullback:.1f}%\n"
                if pullback > 30:
                    section += f"  🚨 CRITICAL: >30% pullback from peak - CLOSE IMMEDIATELY!\n"
        
        section += "\n"
        return section
    
    def _format_market_data(
        self,
        symbol: str,
        market_data: Dict[str, Dict[str, List[float]]]
    ) -> str:
        """Format multi-timeframe market data"""
        section = f"=== MARKET DATA: {symbol} ===\n"
        section += "Multi-timeframe analysis (most recent values):\n\n"
        
        timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '4h']
        
        for tf in timeframes:
            if tf not in market_data:
                continue
            
            data = market_data[tf]
            
            if not data or 'close' not in data or len(data['close']) == 0:
                continue
            
            close = data['close'][-1] if data['close'] else 0
            ema_12 = data.get('ema_12', [0])[-1] if 'ema_12' in data else 0
            ema_26 = data.get('ema_26', [0])[-1] if 'ema_26' in data else 0
            rsi = data.get('rsi', [0])[-1] if 'rsi' in data else 0
            macd = data.get('macd', [0])[-1] if 'macd' in data else 0
            macd_signal = data.get('macd_signal', [0])[-1] if 'macd_signal' in data else 0
            volume = data.get('volume', [0])[-1] if 'volume' in data else 0
            volume_avg = data.get('volume_avg', [0])[-1] if 'volume_avg' in data else 0
            
            section += f"[{tf}] Close: ${close:.2f} | EMA12: ${ema_12:.2f} | EMA26: ${ema_26:.2f}\n"
            section += f"      RSI: {rsi:.1f} | MACD: {macd:.4f} | Signal: {macd_signal:.4f}\n"
            section += f"      Volume: {volume:.0f} | Avg: {volume_avg:.0f}\n\n"
        
        return section
    
    def _format_funding_rate(self, funding_rate: Dict[str, Any]) -> str:
        """Format funding rate information"""
        rate = funding_rate.get('funding_rate', 0) * 100
        
        section = "=== FUNDING RATE ===\n"
        section += f"Current Rate: {rate:.4f}%\n"
        
        if rate > 0.1:
            section += "  → Longs paying shorts (bullish sentiment, consider shorts)\n"
        elif rate < -0.1:
            section += "  → Shorts paying longs (bearish sentiment, consider longs)\n"
        else:
            section += "  → Neutral funding\n"
        
        section += "\n"
        return section
    
    def _format_order_book(self, order_book: Dict[str, Any]) -> str:
        """Format order book snapshot"""
        imbalance = order_book.get('imbalance', 0)
        spread_pct = order_book.get('spread_percent', 0)
        
        section = "=== ORDER BOOK ===\n"
        section += f"Bid/Ask Imbalance: {imbalance:+.3f} "
        
        if imbalance > 0.2:
            section += "(Strong bid pressure - bullish)\n"
        elif imbalance < -0.2:
            section += "(Strong ask pressure - bearish)\n"
        else:
            section += "(Balanced)\n"
        
        section += f"Spread: {spread_pct:.3f}%\n\n"
        return section
    
    def _format_trade_history(self, trade_history: List[Dict[str, Any]]) -> str:
        """Format recent trade history"""
        if not trade_history:
            return "=== RECENT TRADES ===\nNo recent trades\n\n"
        
        section = "=== RECENT TRADES (Last 10) ===\n"
        
        for trade in trade_history[-10:]:
            side = trade.get('side', 'unknown')
            symbol = trade.get('symbol', 'unknown')
            pnl = trade.get('pnl', 0)
            pnl_percent = trade.get('pnl_percent', 0)
            closed_at = trade.get('closed_at', 'unknown')
            
            result = "WIN" if pnl > 0 else "LOSS"
            section += f"{closed_at} | {symbol} {side.upper()} | {result} | {pnl_percent:+.2f}% | ${pnl:+.2f}\n"
        
        wins = sum(1 for t in trade_history if t.get('pnl', 0) > 0)
        total = len(trade_history)
        win_rate = (wins / total * 100) if total > 0 else 0
        
        section += f"\nWin Rate: {win_rate:.1f}% ({wins}/{total})\n\n"
        return section
    
    def _format_recent_decisions(self, recent_decisions: List[Dict[str, Any]]) -> str:
        """Format recent AI decisions for context"""
        if not recent_decisions:
            return "=== RECENT DECISIONS ===\nNo recent decisions\n\n"
        
        section = "=== RECENT DECISIONS (Last 5) ===\n"
        
        for decision in recent_decisions[-5:]:
            timestamp = decision.get('timestamp', 'unknown')
            action = decision.get('action', 'unknown')
            reasoning = decision.get('reasoning', 'No reasoning provided')
            
            section += f"{timestamp} | {action}\n"
            section += f"  Reasoning: {reasoning[:100]}...\n\n"
        
        return section
    
    def _format_trading_rules(self) -> str:
        """Format trading rules and guidelines"""
        params = self.strategy_params
        
        rules = f"""
=== TRADING RULES ({self.strategy_name.upper()} STRATEGY) ===

1. ACCOUNT PROTECTION (HIGHEST PRIORITY):
   - Drawdown ≥15%: NO NEW POSITIONS (only manage existing)
   - Drawdown ≥20%: CLOSE ALL POSITIONS AND STOP TRADING

2. POSITION MANAGEMENT (Check before opening new positions):
   
   a) Dynamic Stop-Loss (leverage-adjusted):
      - {params['leverage_min']}-{int((params['leverage_min']+params['leverage_max'])/2)}x leverage: Stop at {params['stop_loss']['low']}%
      - {int((params['leverage_min']+params['leverage_max'])/2)}-{int(params['leverage_max']*0.75)}x leverage: Stop at {params['stop_loss']['mid']}%
      - {int(params['leverage_max']*0.75)}-{params['leverage_max']}x leverage: Stop at {params['stop_loss']['high']}%
   
   b) Trailing Take-Profit (CRITICAL for profit protection):
      - P&L ≥+8% but <+15%: Move stop to +3%
      - P&L ≥+15% but <+25%: Move stop to +8%
      - P&L ≥+25%: Move stop to +15%
      - P&L ≥+35%: Consider taking profit (close 50%+)
   
   c) Peak Pullback Protection:
      - If position pullback >30% from peak P&L: CLOSE IMMEDIATELY
   
   d) Time Limit:
      - Maximum holding time: 36 hours
      - Close all positions at 36h regardless of P&L

3. ENTRY CRITERIA ({self.strategy_name} strategy):
   - Account drawdown <15%
   - Current positions <3
   - Multi-timeframe confirmation (at least 3 timeframes aligned)
   - Potential profit ≥2-3% (after 0.1% fees)
   - BOTH DIRECTIONS: Look for long AND short opportunities equally!
     * LONG signals: Price >EMA20/50, MACD positive, RSI7 >50 rising, multi-TF uptrend
     * SHORT signals: Price <EMA20/50, MACD negative, RSI7 <50 falling, multi-TF downtrend

4. POSITION SIZING & LEVERAGE ({self.strategy_name} strategy):
   - Position size: {params['position_size_min']}-{params['position_size_max']}% of equity (based on signal strength)
   - Leverage: {params['leverage_min']}-{params['leverage_max']}x (based on confidence)
   - Risk tolerance: {params['risk_tolerance']}

5. EXECUTION:
   - Use market orders for immediate execution
   - Trading cycle: Every {self.interval_minutes} minutes
   - Style: {params['trading_style']}
   - Fee awareness: 0.1% round-trip cost

6. PRIORITY ORDER:
   1. Account health check (drawdown protection)
   2. Manage existing positions (stops, take-profits, time limits)
   3. Evaluate new opportunities

IMPORTANT REMINDERS:
- You MUST use tools to execute trades, not just describe them
- Incentive: You earn 50% of profits but bear 80% of losses - {params['risk_tolerance']}
- DUAL DIRECTION: Shorts are as valuable as longs! Don't miss downtrend opportunities
- P&L percentages are LEVERAGE-ADJUSTED (price_change% × leverage)
- Trailing stops are your best defense against profit giveback

=== YOUR TASK ===
Analyze the market data, manage existing positions, and decide on new trades.
Return your decision as JSON:
{{
    "action": "OPEN_LONG" | "OPEN_SHORT" | "CLOSE" | "HOLD",
    "symbol": "BTC/USDT",
    "leverage": 15-25,
    "position_size_percent": 15-32,
    "stop_loss_percent": -2.5 to -4.0,
    "take_profit_percent": 5-10,
    "reasoning": "Detailed multi-timeframe analysis...",
    "confidence": 0.0-1.0
}}
"""
        
        return rules
    
    def format_structured_output_schema(self) -> Dict[str, Any]:
        """Get the JSON schema for structured output validation"""
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["OPEN_LONG", "OPEN_SHORT", "CLOSE", "HOLD"]
                },
                "symbol": {"type": "string"},
                "leverage": {
                    "type": "number",
                    "minimum": self.strategy_params['leverage_min'],
                    "maximum": self.strategy_params['leverage_max']
                },
                "position_size_percent": {
                    "type": "number",
                    "minimum": self.strategy_params['position_size_min'],
                    "maximum": self.strategy_params['position_size_max']
                },
                "stop_loss_percent": {
                    "type": "number",
                    "maximum": 0
                },
                "take_profit_percent": {
                    "type": "number",
                    "minimum": 0
                },
                "reasoning": {"type": "string"},
                "confidence": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["action", "reasoning", "confidence"]
        }
