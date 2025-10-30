"""
ATR Channel Breakout Strategy

Volatility-based channel strategy using ATR for dynamic support/resistance.
Similar to Donchian but uses ATR for adaptive channel width.

Entry: Price breaks above/below ATR channel
Exit: Price returns to channel middle or opposite breakout

Source: Common quant strategy pattern
Timeframe: 1h, 4h
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class AtrChannelStrategy(BaseStrategy):
    """
    ATR Channel Breakout strategy
    
    Features:
    - ATR-based dynamic channels
    - Adapts to volatility changes
    - Clear breakout signals
    - Works in trending markets
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "1h",
        atr_period: int = 14,
        atr_multiplier: float = 2.5,
        channel_period: int = 20,
        min_confidence: float = 0.70,
        stop_loss_atr_mult: float = 1.5,
        take_profit_atr_mult: float = 3.0,
        max_trade_duration_minutes: int = 1440,
        min_minutes_between_trades: int = 120,
    ):
        """
        Initialize ATR Channel strategy
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe (1h, 4h)
            atr_period: ATR period
            atr_multiplier: ATR multiplier for channel width
            channel_period: Period for channel middle (SMA)
            min_confidence: Minimum confidence threshold
            stop_loss_atr_mult: Stop-loss in ATR multiples
            take_profit_atr_mult: Take-profit in ATR multiples
            max_trade_duration_minutes: Maximum trade duration
            min_minutes_between_trades: Minimum time between trades
        """
        config = {
            'timeframe': timeframe,
            'atr_period': atr_period,
            'atr_multiplier': atr_multiplier,
            'channel_period': channel_period,
            'min_confidence': min_confidence,
            'stop_loss_atr_mult': stop_loss_atr_mult,
            'take_profit_atr_mult': take_profit_atr_mult,
            'max_trade_duration_minutes': max_trade_duration_minutes,
            'min_minutes_between_trades': min_minutes_between_trades,
        }
        super().__init__(name=f'AtrChannel_{timeframe}', config=config)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.channel_period = channel_period
        self.min_confidence = min_confidence
        self.stop_loss_atr_mult = stop_loss_atr_mult
        self.take_profit_atr_mult = take_profit_atr_mult
        self.max_trade_duration_minutes = max_trade_duration_minutes
        self.min_minutes_between_trades = min_minutes_between_trades
        
        self.last_upper = None
        self.last_lower = None
        self.last_trade_time = None
        
        logger.info(
            f"AtrChannelStrategy initialized: {symbol} {timeframe}, "
            f"ATR={atr_period}x{atr_multiplier}, channel={channel_period}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy"""
        self.is_initialized = True
        logger.info(f"AtrChannelStrategy '{self.name}' initialized")
    
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
        Generate trading signal based on ATR Channel breakout
        
        Args:
            market_data: Current market data
            indicators: Technical indicators
            current_position: Current open position (if any)
        
        Returns:
            TradingSignal with action and parameters
        """
        try:
            current_price = market_data['price']
            timestamp = market_data.get('timestamp', datetime.now())
            
            if self.last_trade_time is not None:
                time_since_last_trade = (timestamp - self.last_trade_time).total_seconds() / 60
                if time_since_last_trade < self.min_minutes_between_trades:
                    return self._create_hold_signal(current_price, timestamp)
            
            atr = indicators.get('atr', 0)
            sma = indicators.get('sma_20', current_price)
            
            if atr == 0:
                return self._create_hold_signal(current_price, timestamp)
            
            channel_upper = sma + (atr * self.atr_multiplier)
            channel_middle = sma
            channel_lower = sma - (atr * self.atr_multiplier)
            
            breakout_up = current_price > channel_upper
            breakout_down = current_price < channel_lower
            
            new_breakout_up = breakout_up and (self.last_upper is None or current_price > self.last_upper)
            new_breakout_down = breakout_down and (self.last_lower is None or current_price < self.last_lower)
            
            self.last_upper = channel_upper
            self.last_lower = channel_lower
            
            signal_strength = 0.0
            action = SignalAction.HOLD
            
            if new_breakout_up and not current_position:
                breakout_distance = (current_price - channel_upper) / atr
                signal_strength = 0.7 + min(0.3, breakout_distance * 0.3)
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.BUY
            
            elif new_breakout_down and not current_position:
                breakout_distance = (channel_lower - current_price) / atr
                signal_strength = 0.7 + min(0.3, breakout_distance * 0.3)
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.SELL
            
            if action == SignalAction.HOLD:
                return self._create_hold_signal(current_price, timestamp)
            
            stop_loss = self._calculate_stop_loss(current_price, action, atr)
            take_profit = self._calculate_take_profit(current_price, action, atr)
            
            justification = (
                f"ATR Channel breakout: Price ${current_price:.2f} broke {'above' if action == SignalAction.BUY else 'below'} "
                f"channel {'upper' if action == SignalAction.BUY else 'lower'} ${channel_upper if action == SignalAction.BUY else channel_lower:.2f}. "
                f"ATR {atr:.2f} indicates {'high' if atr > sma * 0.02 else 'moderate'} volatility."
            )
            
            invalidation_conditions = [
                f"Price returns to channel middle ${channel_middle:.2f}",
                f"Opposite channel breakout occurs",
                f"ATR contracts significantly"
            ]
            
            signal = TradingSignal(
                action=action,
                symbol=self.symbol,
                confidence=min(1.0, signal_strength),
                price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=timestamp,
                metadata={
                    'strategy': 'AtrChannel',
                    'timeframe': self.timeframe,
                    'atr': atr,
                    'channel_upper': channel_upper,
                    'channel_middle': channel_middle,
                    'channel_lower': channel_lower,
                    'justification': justification,
                    'invalidation_conditions': invalidation_conditions,
                }
            )
            
            if action in [SignalAction.BUY, SignalAction.SELL]:
                self.last_trade_time = timestamp
            
            self.record_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error generating AtrChannel signal: {e}")
            import traceback
            traceback.print_exc()
            return self._create_hold_signal(current_price, timestamp)
    
    def _calculate_stop_loss(
        self,
        entry_price: float,
        action: SignalAction,
        atr: float
    ) -> float:
        """Calculate stop-loss based on ATR"""
        stop_distance = atr * self.stop_loss_atr_mult
        
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
        profit_distance = atr * self.take_profit_atr_mult
        
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
            stop_loss=0,
            take_profit=0,
            timestamp=timestamp or datetime.now(),
            metadata={}
        )
        self.record_signal(signal)
        return signal
    
    def update_trade_result(
        self,
        entry_price: float,
        exit_price: float,
        profit_pct: float,
        trade_duration: float
    ) -> None:
        """Update strategy performance metrics"""
        self.total_trades += 1
        
        if profit_pct > 0:
            self.winning_trades += 1
            self.total_profit += profit_pct
        else:
            self.losing_trades += 1
            self.total_loss += abs(profit_pct)
        
        logger.info(
            f"AtrChannel trade completed: "
            f"Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, "
            f"P&L {profit_pct:.2f}%, Duration {trade_duration:.1f}h"
        )
