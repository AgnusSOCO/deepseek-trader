"""
Keltner Channel Breakout Strategy

EMA-based channel breakout strategy refined by Linda Bradford Raschke.
Uses ATR for channel width, providing less whipsaw than Bollinger Bands.

Entry: Price breaks above/below Keltner Channel bands
Exit: Price returns to middle band or opposite band breakout
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class KeltnerStrategy(BaseStrategy):
    """
    Keltner Channel Breakout strategy
    
    Features:
    - EMA-based middle line with ATR-based bands
    - Less false signals than Bollinger Bands in trending markets
    - ATR-based stop-loss and take-profit
    - Works best in trending markets with moderate volatility
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = '1h',
        ema_period: int = 20,
        atr_period: int = 10,
        atr_multiplier: float = 1.8,
        min_confidence: float = 0.65,
        stop_loss_atr_multiplier: float = 1.3,
        take_profit_atr_multiplier: float = 2.8,
        max_trade_duration_minutes: int = 1440
    ):
        """
        Initialize Keltner strategy
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe (1h recommended)
            ema_period: EMA period for middle line
            atr_period: ATR period for band width
            atr_multiplier: Multiplier for ATR bands
            min_confidence: Minimum confidence threshold
            stop_loss_atr_multiplier: Stop-loss distance in ATR multiples
            take_profit_atr_multiplier: Take-profit distance in ATR multiples
            max_trade_duration_minutes: Maximum trade duration
        """
        config = {
            'ema_period': ema_period,
            'atr_period': atr_period,
            'atr_multiplier': atr_multiplier,
            'stop_loss_atr_multiplier': stop_loss_atr_multiplier,
            'take_profit_atr_multiplier': take_profit_atr_multiplier,
            'max_trade_duration_minutes': max_trade_duration_minutes,
        }
        super().__init__(name=f'Keltner_{timeframe}', config=config)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.min_confidence = min_confidence
        
        self.ema_period = ema_period
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.stop_loss_atr_multiplier = stop_loss_atr_multiplier
        self.take_profit_atr_multiplier = take_profit_atr_multiplier
        self.max_trade_duration_minutes = max_trade_duration_minutes
        
        self.last_upper = None
        self.last_lower = None
        
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        logger.info(
            f"KeltnerStrategy initialized: {symbol} {timeframe}, "
            f"EMA={ema_period}, ATR={atr_period}, multiplier={atr_multiplier}"
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
        Generate trading signal based on Keltner Channel breakout
        
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
            
            keltner_upper = indicators.get('keltner_upper', 0)
            keltner_middle = indicators.get('keltner_middle', 0)
            keltner_lower = indicators.get('keltner_lower', 0)
            atr = indicators.get('atr', 0)
            
            if keltner_upper == 0 or keltner_lower == 0 or atr == 0:
                return self._create_hold_signal(current_price, timestamp)
            
            channel_width = keltner_upper - keltner_lower
            if channel_width == 0:
                return self._create_hold_signal(current_price, timestamp)
            
            breakout_up = current_price > keltner_upper
            
            breakout_down = current_price < keltner_lower
            
            self.last_upper = keltner_upper
            self.last_lower = keltner_lower
            
            signal_strength = 0.0
            action = SignalAction.HOLD
            
            if breakout_up:
                breakout_distance = (current_price - keltner_upper) / atr
                distance_from_middle = (current_price - keltner_middle) / channel_width
                
                signal_strength = min(1.0, 0.7 + (0.15 * min(breakout_distance, 1.0)) + (0.15 * distance_from_middle))
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.BUY
                    
            elif breakout_down:
                breakout_distance = (keltner_lower - current_price) / atr
                distance_from_middle = (keltner_middle - current_price) / channel_width
                
                signal_strength = min(1.0, 0.7 + (0.15 * min(breakout_distance, 1.0)) + (0.15 * distance_from_middle))
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.SELL
            
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
                symbol=self.symbol,
                confidence=min(1.0, signal_strength),
                price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                timestamp=timestamp or datetime.now(),
                metadata={
                    'keltner_upper': keltner_upper,
                    'keltner_middle': keltner_middle,
                    'keltner_lower': keltner_lower,
                    'channel_width': channel_width,
                    'atr': atr,
                    'breakout_up': breakout_up,
                    'breakout_down': breakout_down
                }
            )
            self.record_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error generating Keltner signal: {e}")
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
            f"Keltner trade result: PnL={profit_loss:.2f}, "
            f"Duration={trade_duration_minutes}min, "
            f"Win rate={self.winning_trades/self.total_trades:.2%}"
        )
