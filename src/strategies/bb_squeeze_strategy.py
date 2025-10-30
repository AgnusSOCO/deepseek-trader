"""
Bollinger Band Squeeze Strategy

Volatility breakout strategy that identifies periods of low volatility (squeeze)
and trades the subsequent breakout in either direction.

Entry: BB width narrows to minimum (squeeze), then price breaks out
Exit: BB width expands significantly or opposite breakout

Source: Common quant strategy pattern
Timeframe: 15m, 1h
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class BbSqueezeStrategy(BaseStrategy):
    """
    Bollinger Band Squeeze volatility breakout strategy
    
    Features:
    - Identifies low volatility periods (squeeze)
    - Trades breakouts from squeeze
    - Works in all market conditions
    - High win rate when properly timed
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "15m",
        bb_period: int = 20,
        bb_std: float = 2.0,
        squeeze_threshold: float = 0.02,
        breakout_threshold: float = 0.005,
        min_confidence: float = 0.70,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.5,
        max_trade_duration_minutes: int = 480,
        min_minutes_between_trades: int = 60,
    ):
        """
        Initialize BB Squeeze strategy
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe (15m, 1h)
            bb_period: Bollinger Band period
            bb_std: Bollinger Band standard deviations
            squeeze_threshold: BB width threshold for squeeze
            breakout_threshold: Price movement threshold for breakout
            min_confidence: Minimum confidence threshold
            stop_loss_pct: Stop-loss percentage
            take_profit_pct: Take-profit percentage
            max_trade_duration_minutes: Maximum trade duration
            min_minutes_between_trades: Minimum time between trades
        """
        config = {
            'timeframe': timeframe,
            'bb_period': bb_period,
            'bb_std': bb_std,
            'squeeze_threshold': squeeze_threshold,
            'breakout_threshold': breakout_threshold,
            'min_confidence': min_confidence,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'max_trade_duration_minutes': max_trade_duration_minutes,
            'min_minutes_between_trades': min_minutes_between_trades,
        }
        super().__init__(name=f'BbSqueeze_{timeframe}', config=config)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.squeeze_threshold = squeeze_threshold
        self.breakout_threshold = breakout_threshold
        self.min_confidence = min_confidence
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_trade_duration_minutes = max_trade_duration_minutes
        self.min_minutes_between_trades = min_minutes_between_trades
        
        self.in_squeeze = False
        self.last_bb_width = None
        self.last_price = None
        self.last_trade_time = None
        
        logger.info(
            f"BbSqueezeStrategy initialized: {symbol} {timeframe}, "
            f"BB={bb_period}/{bb_std}, squeeze<{squeeze_threshold}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy"""
        self.is_initialized = True
        logger.info(f"BbSqueezeStrategy '{self.name}' initialized")
    
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
        Generate trading signal based on BB Squeeze
        
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
            
            bb_upper = indicators.get('bb_upper', 0)
            bb_middle = indicators.get('bb_middle', current_price)
            bb_lower = indicators.get('bb_lower', 0)
            
            if bb_upper == 0 or bb_lower == 0:
                return self._create_hold_signal(current_price, timestamp)
            
            bb_width = (bb_upper - bb_lower) / bb_middle
            
            is_squeezed = bb_width < self.squeeze_threshold
            
            entering_squeeze = is_squeezed and not self.in_squeeze
            exiting_squeeze = not is_squeezed and self.in_squeeze
            
            self.in_squeeze = is_squeezed
            
            breakout_up = False
            breakout_down = False
            
            if exiting_squeeze and self.last_price is not None:
                price_change = (current_price - self.last_price) / self.last_price
                
                if price_change > self.breakout_threshold:
                    breakout_up = True
                elif price_change < -self.breakout_threshold:
                    breakout_down = True
            
            self.last_bb_width = bb_width
            self.last_price = current_price
            
            signal_strength = 0.0
            action = SignalAction.HOLD
            
            if breakout_up and not current_position:
                breakout_strength = abs(current_price - bb_middle) / (bb_upper - bb_middle)
                signal_strength = 0.7 + min(0.3, breakout_strength * 0.5)
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.BUY
            
            elif breakout_down and not current_position:
                breakout_strength = abs(bb_middle - current_price) / (bb_middle - bb_lower)
                signal_strength = 0.7 + min(0.3, breakout_strength * 0.5)
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.SELL
            
            if action == SignalAction.HOLD:
                return self._create_hold_signal(current_price, timestamp)
            
            stop_loss = self._calculate_stop_loss(current_price, action)
            take_profit = self._calculate_take_profit(current_price, action)
            
            justification = (
                f"BB Squeeze breakout: Price ${current_price:.2f} broke {'above' if action == SignalAction.BUY else 'below'} "
                f"after squeeze (BB width {bb_width:.4f} < {self.squeeze_threshold}). "
                f"Volatility expansion expected."
            )
            
            invalidation_conditions = [
                f"Price returns to BB middle ${bb_middle:.2f}",
                f"BB width contracts again",
                f"Opposite breakout occurs"
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
                    'strategy': 'BbSqueeze',
                    'timeframe': self.timeframe,
                    'bb_width': bb_width,
                    'bb_upper': bb_upper,
                    'bb_middle': bb_middle,
                    'bb_lower': bb_lower,
                    'in_squeeze': self.in_squeeze,
                    'justification': justification,
                    'invalidation_conditions': invalidation_conditions,
                }
            )
            
            if action in [SignalAction.BUY, SignalAction.SELL]:
                self.last_trade_time = timestamp
            
            self.record_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error generating BbSqueeze signal: {e}")
            import traceback
            traceback.print_exc()
            return self._create_hold_signal(current_price, timestamp)
    
    def _calculate_stop_loss(
        self,
        entry_price: float,
        action: SignalAction
    ) -> float:
        """Calculate stop-loss based on percentage"""
        stop_distance = entry_price * (self.stop_loss_pct / 100)
        
        if action == SignalAction.BUY:
            return entry_price - stop_distance
        else:
            return entry_price + stop_distance
    
    def _calculate_take_profit(
        self,
        entry_price: float,
        action: SignalAction
    ) -> float:
        """Calculate take-profit based on percentage"""
        profit_distance = entry_price * (self.take_profit_pct / 100)
        
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
            f"BbSqueeze trade completed: "
            f"Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, "
            f"P&L {profit_pct:.2f}%, Duration {trade_duration:.1f}h"
        )
