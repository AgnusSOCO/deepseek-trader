"""
Donchian Channel Breakout (Turtle Trading) Strategy

Classic trend-following strategy based on Richard Dennis's Turtle Trading system.
Proven track record with 80%+ annual returns over 4 years in original implementation.

Entry: Price breaks above N-period high (20-period default)
Exit: Price breaks below M-period low (10-period default)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class DonchianStrategy(BaseStrategy):
    """
    Donchian Channel Breakout (Turtle Trading) strategy
    
    Features:
    - Entry on breakout of N-period high/low
    - Exit on breakout of shorter M-period low/high
    - ATR-based position sizing and stop-loss
    - Works best in trending markets
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = '1h',
        entry_period: int = 20,
        exit_period: int = 10,
        min_confidence: float = 0.7,
        stop_loss_atr_multiplier: float = 2.0,
        take_profit_ratio: float = 3.0,
        max_trade_duration_minutes: int = 2880
    ):
        """
        Initialize Donchian strategy
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe (1h or 4h recommended)
            entry_period: Period for entry channel (20 default)
            exit_period: Period for exit channel (10 default)
            min_confidence: Minimum confidence threshold
            stop_loss_atr_multiplier: Stop-loss distance in ATR multiples
            take_profit_ratio: Take-profit as ratio of stop-loss distance
            max_trade_duration_minutes: Maximum trade duration
        """
        config = {
            'entry_period': entry_period,
            'exit_period': exit_period,
            'stop_loss_atr_multiplier': stop_loss_atr_multiplier,
            'take_profit_ratio': take_profit_ratio,
            'max_trade_duration_minutes': max_trade_duration_minutes,
        }
        super().__init__(name=f'Donchian_{timeframe}', config=config)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.min_confidence = min_confidence
        
        self.entry_period = entry_period
        self.exit_period = exit_period
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier
        self.take_profit_ratio = take_profit_ratio
        self.max_trade_duration_minutes = max_trade_duration_minutes
        
        self.last_high = None
        self.last_low = None
        
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        logger.info(
            f"DonchianStrategy initialized: {symbol} {timeframe}, "
            f"entry_period={entry_period}, exit_period={exit_period}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy"""
        self.is_initialized = True
        logger.info(f"{self.name} initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Process new market data"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return self.config
    
    def generate_signal(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any],
        current_position: Optional[Dict[str, Any]] = None
    ) -> TradingSignal:
        """
        Generate trading signal based on Donchian Channel breakout
        
        Args:
            current_price: Current market price
            indicators: Technical indicators
            timestamp: Current timestamp
        
        Returns:
            TradingSignal with action and parameters
        """
        try:
            current_price = market_data['price']
            timestamp = market_data.get('timestamp')
            
            donchian_high = indicators.get('donchian_high_20', 0)
            donchian_low = indicators.get('donchian_low_20', 0)
            donchian_exit_high = indicators.get('donchian_high_10', 0)
            donchian_exit_low = indicators.get('donchian_low_10', 0)
            atr = indicators.get('atr', 0)
            
            if donchian_high == 0 or donchian_low == 0 or atr == 0:
                return self._create_hold_signal(current_price, timestamp)
            
            channel_width = donchian_high - donchian_low
            if channel_width == 0:
                return self._create_hold_signal(current_price, timestamp)
            
            breakout_up = (
                current_price >= donchian_high and
                (self.last_high is None or current_price > self.last_high)
            )
            
            breakout_down = (
                current_price <= donchian_low and
                (self.last_low is None or current_price < self.last_low)
            )
            
            self.last_high = donchian_high
            self.last_low = donchian_low
            
            signal_strength = 0.0
            action = SignalAction.HOLD
            
            if breakout_up:
                breakout_distance = (current_price - donchian_high) / atr
                channel_position = (current_price - donchian_low) / channel_width
                
                signal_strength = min(1.0, 0.7 + (0.15 * min(breakout_distance, 1.0)) + (0.15 * channel_position))
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.BUY
                    
            elif breakout_down:
                breakout_distance = (donchian_low - current_price) / atr
                channel_position = (donchian_high - current_price) / channel_width
                
                signal_strength = min(1.0, 0.7 + (0.15 * min(breakout_distance, 1.0)) + (0.15 * channel_position))
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.SELL
            
            if action == SignalAction.HOLD:
                return self._create_hold_signal(current_price, timestamp)
            
            stop_loss = self._calculate_stop_loss(
                current_price, action, atr
            )
            take_profit = self._calculate_take_profit(
                current_price, action, stop_loss
            )
            
            signal = TradingSignal(
                action=action,
                symbol=self.symbol,
                confidence=min(1.0, signal_strength),
                price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=timestamp or datetime.now(),
                metadata={
                    'donchian_high': donchian_high,
                    'donchian_low': donchian_low,
                    'channel_width': channel_width,
                    'atr': atr,
                    'breakout_up': breakout_up,
                    'breakout_down': breakout_down
                }
            )
            self.record_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error generating Donchian signal: {e}")
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
        stop_loss: float
    ) -> float:
        """Calculate take-profit as ratio of stop-loss distance"""
        stop_distance = abs(entry_price - stop_loss)
        profit_distance = stop_distance * self.take_profit_ratio
        
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
            symbol=self.symbol,
            confidence=0.0,
            price=current_price,
            timestamp=timestamp or datetime.now(),
            metadata={}
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
            f"Donchian trade result: PnL={profit_loss:.2f}, "
            f"Duration={trade_duration_minutes}min, "
            f"Win rate={self.winning_trades/self.total_trades:.2%}"
        )
