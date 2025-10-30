"""
SuperTrend Strategy

ATR-based trend-following strategy that uses dynamic support/resistance levels.
Based on the freqtrade community implementation with proven track record.

Entry: Price crosses above SuperTrend line (trend reversal to bullish)
Exit: Price crosses below SuperTrend line (trend reversal to bearish)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class SuperTrendStrategy(BaseStrategy):
    """
    SuperTrend trend-following strategy
    
    Features:
    - ATR-based dynamic support/resistance
    - Clear trend direction signals
    - Works best in strong trending markets
    - Low false signals in ranging markets
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = '1h',
        atr_period: int = 10,
        atr_multiplier: float = 2.5,
        min_confidence: float = 0.65,
        stop_loss_atr_multiplier: float = 1.5,
        take_profit_atr_multiplier: float = 3.5,
        max_trade_duration_minutes: int = 1440
    ):
        """
        Initialize SuperTrend strategy
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe (1h recommended)
            atr_period: ATR calculation period
            atr_multiplier: Multiplier for SuperTrend bands
            min_confidence: Minimum confidence threshold
            stop_loss_atr_multiplier: Stop-loss distance in ATR multiples
            take_profit_atr_multiplier: Take-profit distance in ATR multiples
            max_trade_duration_minutes: Maximum trade duration
        """
        config = {
            'timeframe': timeframe,
            'atr_period': atr_period,
            'atr_multiplier': atr_multiplier,
            'min_confidence': min_confidence,
            'stop_loss_atr_multiplier': stop_loss_atr_multiplier,
            'take_profit_atr_multiplier': take_profit_atr_multiplier,
            'max_trade_duration_minutes': max_trade_duration_minutes
        }
        super().__init__(name=f'SuperTrend_{timeframe}', config=config)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.min_confidence = min_confidence
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier
        self.take_profit_atr_multiplier = take_profit_atr_multiplier
        self.max_trade_duration_minutes = max_trade_duration_minutes
        
        self.last_direction = None
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        
        logger.info(
            f"SuperTrendStrategy initialized: {symbol} {timeframe}, "
            f"ATR period={atr_period}, multiplier={atr_multiplier}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy"""
        self.is_initialized = True
        logger.info(f"SuperTrendStrategy '{self.name}' initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Process new market data"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return {
            'timeframe': self.timeframe,
            'atr_period': self.atr_period,
            'atr_multiplier': self.atr_multiplier,
            'min_confidence': self.min_confidence,
            'stop_loss_atr_multiplier': self.stop_loss_atr_multiplier,
            'take_profit_atr_multiplier': self.take_profit_atr_multiplier,
            'max_trade_duration_minutes': self.max_trade_duration_minutes
        }
    
    def generate_signal(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any],
        current_position: Optional[Dict[str, Any]] = None
    ) -> TradingSignal:
        """
        Generate trading signal based on SuperTrend indicator
        
        Args:
            market_data: Current market data
            indicators: Technical indicators
            current_position: Current open position (if any)
        
        Returns:
            TradingSignal with action and parameters
        """
        try:
            current_price = market_data['price']
            timestamp = market_data.get('timestamp')
            
            supertrend = indicators.get('supertrend', current_price)
            supertrend_direction = indicators.get('supertrend_direction', 0)
            atr = indicators.get('atr', 0)
            
            if atr == 0:
                return self._create_hold_signal(current_price, timestamp)
            
            trend_bullish = supertrend_direction == 1
            trend_bearish = supertrend_direction == 0
            
            direction_changed = (
                self.last_direction is not None and 
                self.last_direction != supertrend_direction
            )
            
            signal_strength = 0.0
            action = SignalAction.HOLD
            
            if trend_bullish and direction_changed:
                distance_from_supertrend = abs(current_price - supertrend) / atr
                signal_strength = min(1.0, 0.7 + (0.3 * (1 - min(distance_from_supertrend, 1.0))))
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.BUY
                    
            elif trend_bearish and direction_changed:
                distance_from_supertrend = abs(current_price - supertrend) / atr
                signal_strength = min(1.0, 0.7 + (0.3 * (1 - min(distance_from_supertrend, 1.0))))
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.SELL
            
            self.last_direction = supertrend_direction
            
            if action == SignalAction.HOLD:
                return self._create_hold_signal(current_price, timestamp)
            
            stop_loss = self._calculate_stop_loss(
                current_price, action, atr
            )
            take_profit = self._calculate_take_profit(
                current_price, action, atr
            )
            
            signal = TradingSignal(
                action=action,
                confidence=min(1.0, signal_strength),
                symbol=self.symbol,
                timestamp=timestamp or datetime.now(),
                metadata={
                    'supertrend': supertrend,
                    'supertrend_direction': supertrend_direction,
                    'atr': atr,
                    'direction_changed': direction_changed
                },
                price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit
            )
            self.record_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error generating SuperTrend signal: {e}")
            return self._create_hold_signal(current_price, timestamp)
    
    def _calculate_stop_loss(
        self,
        entry_price: float,
        action: SignalAction,
        atr: float
    ) -> float:
        """Calculate stop-loss based on ATR"""
        stop_distance = atr * self.stop_loss_atr_multiplier
        
        if action == SignalAction.BUY:
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance
    
    def _calculate_take_profit(
        self,
        entry_price: float,
        action: SignalAction,
        atr: float
    ) -> float:
        """Calculate take-profit based on ATR"""
        profit_distance = atr * self.take_profit_atr_multiplier
        
        if action == SignalAction.BUY:
            return entry_price + profit_distance
        else:
            return entry_price - profit_distance
    
    def _create_hold_signal(
        self,
        current_price: float,
        timestamp: Optional[datetime] = None
    ) -> TradingSignal:
        """Create a HOLD signal"""
        signal = TradingSignal(
            action=SignalAction.HOLD,
            confidence=0.0,
            symbol=self.symbol,
            timestamp=timestamp or datetime.now(),
            metadata={},
            price=current_price
        )
        self.record_signal(signal)
        return signal
    
    def update_trade_result(
        self,
        entry_price: float,
        exit_price: float,
        profit_loss: float,
        trade_duration_minutes: int
    ):
        """Update strategy based on trade result"""
        self.total_trades += 1
        
        if profit_loss > 0:
            self.winning_trades += 1
        
        self.total_pnl += profit_loss
        
        logger.debug(
            f"SuperTrend trade result: PnL={profit_loss:.2f}, "
            f"Duration={trade_duration_minutes}min, "
            f"Win rate={self.winning_trades/self.total_trades:.2%}"
        )
