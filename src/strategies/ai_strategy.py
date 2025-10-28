"""
AI Strategy

Integrates multi-agent system into the trading strategy framework.
Uses DeepSeek-powered agents for autonomous trading decisions.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base_strategy import BaseStrategy, TradingSignal, SignalAction
from ..ai.deepseek_client import DeepSeekClient
from ..ai.agents import MultiAgentSystem, MultiAgentResult

logger = logging.getLogger(__name__)


class AIStrategy(BaseStrategy):
    """
    AI-powered trading strategy using multi-agent system
    
    Leverages 7 specialized agents for comprehensive market analysis
    and autonomous trading decisions.
    """
    
    def __init__(
        self,
        name: str,
        config: Dict[str, Any],
        deepseek_api_key: str,
        enable_cache: bool = True,
        fallback_to_rules: bool = True
    ):
        """
        Initialize AI strategy
        
        Args:
            name: Strategy name
            config: Strategy configuration
            deepseek_api_key: DeepSeek API key
            enable_cache: Enable response caching
            fallback_to_rules: Fallback to rule-based decisions if AI fails
        """
        super().__init__(name, config)
        
        self.client = DeepSeekClient(
            api_key=deepseek_api_key,
            enable_cache=enable_cache,
            cache_ttl=config.get('cache_ttl', 300)
        )
        
        self.multi_agent_system = MultiAgentSystem(self.client)
        
        self.fallback_to_rules = fallback_to_rules
        self.last_ai_result: Optional[MultiAgentResult] = None
        
        logger.info(f"AIStrategy '{name}' initialized with multi-agent system")
    
    def generate_signal(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> TradingSignal:
        """
        Generate trading signal using AI multi-agent system
        
        Args:
            market_data: Market data dict with symbol, price, timestamp, etc.
            indicators: Technical indicators dict
        
        Returns:
            TradingSignal with AI-driven decision
        """
        symbol = market_data['symbol']
        current_price = market_data['price']
        timestamp = market_data.get('timestamp', datetime.now())
        
        try:
            ai_market_data = self._prepare_market_data(market_data, indicators)
            
            portfolio_state = self._get_portfolio_state()
            
            import asyncio
            result = asyncio.run(
                self.multi_agent_system.execute_workflow(
                    symbol=symbol,
                    timeframe=self.config.get('timeframe', '5m'),
                    market_data=ai_market_data,
                    portfolio_state=portfolio_state,
                    account_balance=self.config.get('account_balance', 10000.0),
                    current_positions=[]
                )
            )
            
            self.last_ai_result = result
            
            if not result.success or not result.final_decision:
                logger.warning(f"AI workflow failed: {result.errors}")
                if self.fallback_to_rules:
                    return self._fallback_signal(market_data, indicators)
                else:
                    return self._hold_signal(symbol, current_price, timestamp)
            
            decision = result.final_decision
            
            action_map = {
                'BUY': SignalAction.BUY,
                'SELL': SignalAction.SELL,
                'HOLD': SignalAction.HOLD
            }
            action = action_map.get(decision['action'], SignalAction.HOLD)
            
            signal = TradingSignal(
                action=action,
                confidence=decision['confidence'] / 100.0,  # Convert to 0-1
                symbol=symbol,
                timestamp=timestamp,
                price=current_price,
                stop_loss=decision.get('stop_loss'),
                take_profit=decision.get('take_profit'),
                position_size=decision.get('position_size_pct', 0) / 100.0,
                metadata={
                    'ai_driven': True,
                    'rationale': decision.get('rationale', ''),
                    'risk_approved': decision.get('risk_approved', False),
                    'risk_score': decision.get('risk_score', 0),
                    'timeframe': decision.get('timeframe', ''),
                    'risk_reward_ratio': decision.get('risk_reward_ratio', 0),
                    'total_cost': result.total_cost,
                    'total_tokens': result.total_tokens,
                    'elapsed_seconds': result.elapsed_seconds,
                    'technical_analysis': result.technical_analysis,
                    'sentiment_analysis': result.sentiment_analysis,
                    'bull_thesis': result.bull_thesis,
                    'bear_thesis': result.bear_thesis
                }
            )
            
            logger.info(
                f"AI signal generated: {action.value} with confidence {signal.confidence:.2f}, "
                f"cost=${result.total_cost:.4f}, time={result.elapsed_seconds:.2f}s"
            )
            
            return signal
            
        except Exception as e:
            logger.error(f"AI strategy failed: {str(e)}")
            if self.fallback_to_rules:
                return self._fallback_signal(market_data, indicators)
            else:
                return self._hold_signal(symbol, current_price, timestamp)
    
    def _prepare_market_data(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare market data for AI agents"""
        return {
            'current_price': market_data['price'],
            'ohlcv': market_data.get('ohlcv', []),
            'indicators': indicators,
            'funding_rate': market_data.get('funding_rate', 0.0),
            'open_interest': market_data.get('open_interest', 0.0),
            'liquidations_24h': market_data.get('liquidations_24h', {'longs': 0, 'shorts': 0}),
            'volume_24h': market_data.get('volume_24h', 0.0),
            'order_book': market_data.get('order_book', {'bids': [], 'asks': []}),
            'bid_ask_spread': market_data.get('bid_ask_spread', 0.0),
            'volume_profile': market_data.get('volume_profile', {})
        }
    
    def _get_portfolio_state(self) -> Dict[str, Any]:
        """Get current portfolio state"""
        return {
            'total_value': self.config.get('account_balance', 10000.0),
            'cash_balance': self.config.get('account_balance', 10000.0),
            'positions_value': 0.0,
            'unrealized_pnl': 0.0,
            'realized_pnl': 0.0,
            'num_positions': 0,
            'daily_drawdown_pct': 0.0,
            'total_drawdown_pct': 0.0
        }
    
    def _fallback_signal(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> TradingSignal:
        """
        Fallback to simple rule-based signal if AI fails
        
        Uses RSI-based logic as fallback
        """
        logger.info("Using fallback rule-based signal")
        
        symbol = market_data['symbol']
        current_price = market_data['price']
        timestamp = market_data.get('timestamp', datetime.now())
        
        rsi = indicators.get('rsi', 50.0)
        
        if rsi < 30:
            action = SignalAction.BUY
            confidence = 0.6
            stop_loss = current_price * 0.98
            take_profit = current_price * 1.04
        elif rsi > 70:
            action = SignalAction.SELL
            confidence = 0.6
            stop_loss = current_price * 1.02
            take_profit = current_price * 0.96
        else:
            action = SignalAction.HOLD
            confidence = 0.5
            stop_loss = None
            take_profit = None
        
        return TradingSignal(
            action=action,
            confidence=confidence,
            symbol=symbol,
            timestamp=timestamp,
            price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=0.1,
            metadata={'fallback': True, 'rsi': rsi}
        )
    
    def _hold_signal(
        self,
        symbol: str,
        current_price: float,
        timestamp: datetime
    ) -> TradingSignal:
        """Generate HOLD signal"""
        return TradingSignal(
            action=SignalAction.HOLD,
            confidence=0.0,
            symbol=symbol,
            timestamp=timestamp,
            price=current_price,
            metadata={'reason': 'AI failed, no fallback'}
        )
    
    def get_last_ai_result(self) -> Optional[MultiAgentResult]:
        """Get last AI multi-agent result for analysis"""
        return self.last_ai_result
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get API usage statistics"""
        return self.client.get_usage_stats()
