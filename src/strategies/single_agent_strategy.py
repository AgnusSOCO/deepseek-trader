"""
SingleAgentStrategy - nof1.ai-style LLM Trading Strategy

Uses a single LLM agent with comprehensive prompts to make autonomous trading decisions.
Integrates with existing BaseStrategy framework.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, ValidationError

from .base_strategy import BaseStrategy, TradingSignal, SignalAction
from ..ai.openrouter_client import OpenRouterClient
from ..ai.prompt_builder import PromptBuilder

logger = logging.getLogger(__name__)


class TradingDecision(BaseModel):
    """Structured trading decision from LLM (validated with Pydantic)"""
    action: str = Field(..., pattern="^(OPEN_LONG|OPEN_SHORT|CLOSE|HOLD)$")
    symbol: Optional[str] = None
    leverage: Optional[float] = Field(None, ge=1, le=25)
    position_size_percent: Optional[float] = Field(None, ge=0, le=100)
    stop_loss_percent: Optional[float] = Field(None, le=0)
    take_profit_percent: Optional[float] = Field(None, ge=0)
    reasoning: str
    confidence: float = Field(..., ge=0.0, le=1.0)


class SingleAgentStrategy(BaseStrategy):
    """
    Single LLM agent strategy matching nof1.ai approach
    
    Uses DeepSeek with comprehensive prompts containing:
    - Multi-timeframe market data
    - Account metrics and drawdown
    - Current positions with leverage-aware P&L
    - Trade history
    - Recent decisions
    
    Returns structured JSON decisions validated with Pydantic
    """
    
    def __init__(
        self,
        name: str = "SingleAgent",
        config: Dict[str, Any] = None,
        openrouter_api_key: str = "",
        model_name: str = "deepseek/deepseek-chat",
        strategy_profile: str = "balanced",
        interval_minutes: int = 5,
        min_confidence: float = 0.65,
        max_retries: int = 3,
        price_feed = None,
        performance_monitor = None,
        risk_manager = None
    ):
        """
        Initialize single agent strategy
        
        Args:
            name: Strategy name
            config: Strategy configuration dict
            openrouter_api_key: OpenRouter API key
            model_name: LLM model to use
            strategy_profile: conservative/balanced/aggressive
            interval_minutes: Decision loop interval
            min_confidence: Minimum confidence threshold
            max_retries: Max retries for invalid LLM responses
            price_feed: PriceFeed instance for market data
            performance_monitor: PerformanceMonitor for account metrics
            risk_manager: RiskManager for risk checks
        """
        if config is None:
            config = {}
        
        super().__init__(name, config)
        
        self.openrouter_api_key = openrouter_api_key
        self.model_name = model_name
        self.strategy_profile = strategy_profile
        self.interval_minutes = interval_minutes
        self.min_confidence = min_confidence
        self.max_retries = max_retries
        
        self.price_feed = price_feed
        self.performance_monitor = performance_monitor
        self.risk_manager = risk_manager
        
        self.openrouter_client = OpenRouterClient(api_key=openrouter_api_key)
        self.prompt_builder = PromptBuilder(
            strategy_name=strategy_profile,
            interval_minutes=interval_minutes
        )
        
        self.recent_decisions: List[Dict[str, Any]] = []
        self.max_recent_decisions = 10
        
        logger.info(
            f"SingleAgentStrategy initialized: {strategy_profile} profile, "
            f"model={model_name}, min_confidence={min_confidence}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy (required by BaseStrategy)"""
        self.is_initialized = True
        logger.info(f"SingleAgentStrategy '{self.name}' initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Process new market data (required by BaseStrategy)"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters (required by BaseStrategy)"""
        return {
            'name': self.name,
            'model_name': self.model_name,
            'strategy_profile': self.strategy_profile,
            'interval_minutes': self.interval_minutes,
            'min_confidence': self.min_confidence,
            'max_retries': self.max_retries
        }
    
    async def generate_signal(
        self,
        symbol: str,
        timeframe: str,
        data: Dict[str, Any]
    ) -> Optional[TradingSignal]:
        """
        Generate trading signal using LLM agent
        
        Args:
            symbol: Trading pair
            timeframe: Primary timeframe (not used, we use multi-timeframe)
            data: Market data dict
            
        Returns:
            TradingSignal or None
        """
        try:
            if not self.price_feed:
                logger.error("PriceFeed not configured for SingleAgentStrategy")
                return None
            
            market_data = self._get_market_data(symbol)
            account_info = self._get_account_info()
            positions = self._get_positions(symbol)
            trade_history = self._get_trade_history()
            
            funding_rate = await self._get_funding_rate(symbol)
            order_book = await self._get_order_book(symbol)
            
            prompt = self.prompt_builder.build_prompt(
                symbol=symbol,
                market_data=market_data,
                account_info=account_info,
                positions=positions,
                trade_history=trade_history,
                recent_decisions=self.recent_decisions,
                funding_rate=funding_rate,
                order_book=order_book
            )
            
            decision = await self._call_llm_with_retry(prompt)
            
            if not decision:
                logger.warning("LLM returned no valid decision")
                return None
            
            self._record_decision(decision)
            
            if decision.action == "HOLD":
                logger.info(f"LLM decided to HOLD: {decision.reasoning[:100]}")
                return None
            
            if decision.confidence < self.min_confidence:
                logger.info(
                    f"LLM confidence {decision.confidence:.2f} below threshold "
                    f"{self.min_confidence}, ignoring signal"
                )
                return None
            
            signal = self._convert_decision_to_signal(symbol, decision)
            
            return signal
        
        except Exception as e:
            logger.error(f"Error generating signal: {e}", exc_info=True)
            return None
    
    def _get_market_data(self, symbol: str) -> Dict[str, Dict[str, List[float]]]:
        """Get multi-timeframe market data from PriceFeed"""
        try:
            timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '4h']
            return self.price_feed.get_time_series_arrays(
                symbol=symbol,
                timeframes=timeframes,
                lookback_bars=50
            )
        except Exception as e:
            logger.error(f"Error getting market data: {e}")
            return {}
    
    def _get_account_info(self) -> Dict[str, Any]:
        """Get account metrics from PerformanceMonitor"""
        try:
            if not self.performance_monitor:
                return {
                    'balance': 10000,
                    'unrealized_pnl': 0,
                    'total_equity': 10000,
                    'peak_equity': 10000,
                    'drawdown_percent': 0,
                    'daily_pnl': 0,
                    'sharpe_ratio': 0
                }
            
            snapshot = self.performance_monitor.get_snapshot()
            
            return {
                'balance': snapshot.get('capital', 10000),
                'unrealized_pnl': snapshot.get('unrealized_pnl', 0),
                'total_equity': snapshot.get('total_equity', 10000),
                'peak_equity': snapshot.get('peak_capital', 10000),
                'drawdown_percent': snapshot.get('drawdown_percent', 0),
                'daily_pnl': snapshot.get('daily_pnl', 0),
                'sharpe_ratio': snapshot.get('sharpe_ratio', 0)
            }
        
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            return {
                'balance': 10000,
                'unrealized_pnl': 0,
                'total_equity': 10000,
                'peak_equity': 10000,
                'drawdown_percent': 0,
                'daily_pnl': 0,
                'sharpe_ratio': 0
            }
    
    def _get_positions(self, symbol: str) -> List[Dict[str, Any]]:
        """Get current positions from RiskManager or PerformanceMonitor"""
        try:
            if not self.performance_monitor:
                return []
            
            snapshot = self.performance_monitor.get_snapshot()
            positions = snapshot.get('positions', [])
            
            symbol_positions = [
                pos for pos in positions
                if pos.get('symbol') == symbol
            ]
            
            return symbol_positions
        
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            return []
    
    def _get_trade_history(self) -> List[Dict[str, Any]]:
        """Get recent trade history from PerformanceMonitor"""
        try:
            if not self.performance_monitor:
                return []
            
            snapshot = self.performance_monitor.get_snapshot()
            trades = snapshot.get('recent_trades', [])
            
            return trades[-10:]
        
        except Exception as e:
            logger.error(f"Error getting trade history: {e}")
            return []
    
    async def _get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get funding rate from PriceFeed"""
        try:
            if not self.price_feed:
                return None
            
            return await self.price_feed.get_funding_rate(symbol)
        
        except Exception as e:
            logger.debug(f"Error getting funding rate: {e}")
            return None
    
    async def _get_order_book(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get order book from PriceFeed"""
        try:
            if not self.price_feed:
                return None
            
            return await self.price_feed.get_order_book(symbol)
        
        except Exception as e:
            logger.debug(f"Error getting order book: {e}")
            return None
    
    async def _call_llm_with_retry(
        self,
        prompt: str
    ) -> Optional[TradingDecision]:
        """
        Call LLM with retry logic and validation
        
        Args:
            prompt: Trading prompt
            
        Returns:
            Validated TradingDecision or None
        """
        for attempt in range(self.max_retries):
            try:
                response = await self.openrouter_client.chat_completion(
                    model=self.model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert cryptocurrency trading agent. "
                                     "Analyze the market data and return your decision as valid JSON only."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.7,
                    max_tokens=1000
                )
                
                if not response or 'choices' not in response:
                    logger.warning(f"Invalid LLM response format (attempt {attempt+1})")
                    continue
                
                content = response['choices'][0]['message']['content']
                
                decision_dict = self._extract_json_from_response(content)
                
                if not decision_dict:
                    logger.warning(f"Could not extract JSON from response (attempt {attempt+1})")
                    continue
                
                decision = TradingDecision(**decision_dict)
                
                logger.info(
                    f"LLM decision: {decision.action} with confidence {decision.confidence:.2f}"
                )
                
                return decision
            
            except ValidationError as e:
                logger.warning(f"Pydantic validation error (attempt {attempt+1}): {e}")
                continue
            
            except Exception as e:
                logger.error(f"Error calling LLM (attempt {attempt+1}): {e}")
                continue
        
        logger.error(f"Failed to get valid LLM decision after {self.max_retries} attempts")
        return None
    
    def _extract_json_from_response(self, content: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from LLM response (handles markdown code blocks)"""
        try:
            content = content.strip()
            
            if '```json' in content:
                start = content.find('```json') + 7
                end = content.find('```', start)
                content = content[start:end].strip()
            elif '```' in content:
                start = content.find('```') + 3
                end = content.find('```', start)
                content = content[start:end].strip()
            
            return json.loads(content)
        
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Error extracting JSON: {e}")
            return None
    
    def _convert_decision_to_signal(
        self,
        symbol: str,
        decision: TradingDecision
    ) -> TradingSignal:
        """Convert LLM decision to TradingSignal"""
        action = SignalAction.HOLD
        if decision.action == "OPEN_LONG":
            action = SignalAction.BUY
        elif decision.action == "OPEN_SHORT":
            action = SignalAction.SELL
        elif decision.action == "CLOSE":
            action = SignalAction.CLOSE_LONG
        
        current_price = 0.0
        if self.price_feed:
            current_price = self.price_feed.get_latest_price(symbol)
        
        if current_price <= 0:
            current_price = 50000.0
        
        position_size_decimal = None
        if decision.position_size_percent:
            position_size_decimal = decision.position_size_percent / 100.0
        
        metadata = {
            'strategy': self.name,
            'model': self.model_name,
            'profile': self.strategy_profile,
            'reasoning': decision.reasoning,
            'leverage': decision.leverage,
            'stop_loss_percent': decision.stop_loss_percent,
            'take_profit_percent': decision.take_profit_percent,
            'invalidation_conditions': [
                "Account drawdown exceeds 15%",
                "Position holding time exceeds 36 hours",
                "Multi-timeframe trend reversal confirmed"
            ]
        }
        
        signal = TradingSignal(
            action=action,
            confidence=decision.confidence,
            symbol=symbol,
            timestamp=datetime.now(),
            metadata=metadata,
            price=current_price,
            stop_loss=None,
            take_profit=None,
            position_size=position_size_decimal
        )
        
        return signal
    
    def _record_decision(self, decision: TradingDecision) -> None:
        """Record decision for future context"""
        self.recent_decisions.append({
            'timestamp': datetime.now().isoformat(),
            'action': decision.action,
            'reasoning': decision.reasoning,
            'confidence': decision.confidence
        })
        
        if len(self.recent_decisions) > self.max_recent_decisions:
            self.recent_decisions = self.recent_decisions[-self.max_recent_decisions:]
