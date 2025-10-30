"""
EMA-OBV Trend Following Strategy

Simple trend-following strategy using EMA(20) with OBV volume confirmation.
Reduces false breakouts by requiring volume confirmation.

Entry Long: Price crosses above EMA(20) AND OBV rising
Entry Short: Price crosses below EMA(20) AND OBV falling
Exit: Opposite crossover with OBV confirmation

Source: freqtrade-strategies/futures/TrendFollowingStrategy.py
Timeframe: 5m, 15m, 1h
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class EmaObvStrategy(BaseStrategy):
    """
    EMA-OBV Trend Following strategy
    
    Features:
    - EMA(20) for trend direction
    - OBV for volume confirmation
    - Reduces false breakouts
    - Works in trending markets
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "15m",
        ema_period: int = 20,
        obv_lookback: int = 5,
        min_confidence: float = 0.70,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.0,
        max_trade_duration_minutes: int = 720,
    ):
        """
        Initialize EMA-OBV strategy
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe (5m, 15m, 1h)
            ema_period: EMA period for trend
            obv_lookback: Periods to check OBV trend
            min_confidence: Minimum confidence threshold
            stop_loss_pct: Stop-loss percentage
            take_profit_pct: Take-profit percentage
            max_trade_duration_minutes: Maximum trade duration
        """
        config = {
            'timeframe': timeframe,
            'ema_period': ema_period,
            'obv_lookback': obv_lookback,
            'min_confidence': min_confidence,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'max_trade_duration_minutes': max_trade_duration_minutes,
        }
        super().__init__(name=f'EmaObv_{timeframe}', config=config)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.ema_period = ema_period
        self.obv_lookback = obv_lookback
        self.min_confidence = min_confidence
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_trade_duration_minutes = max_trade_duration_minutes
        
        self.last_ema = None
        self.last_obv = None
        self.obv_history = []
        
        logger.info(
            f"EmaObvStrategy initialized: {symbol} {timeframe}, "
            f"EMA={ema_period}, OBV lookback={obv_lookback}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy"""
        self.is_initialized = True
        logger.info(f"EmaObvStrategy '{self.name}' initialized")
    
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
        Generate trading signal based on EMA-OBV crossover
        
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
            
            ema = indicators.get('ema_20', current_price)
            obv = indicators.get('obv', 0)
            
            if ema == 0 or obv == 0:
                return self._create_hold_signal(current_price, timestamp)
            
            self.obv_history.append(obv)
            if len(self.obv_history) > self.obv_lookback + 1:
                self.obv_history.pop(0)
            
            if len(self.obv_history) < self.obv_lookback:
                self.last_ema = ema
                self.last_obv = obv
                return self._create_hold_signal(current_price, timestamp)
            
            price_above_ema = current_price > ema
            price_below_ema = current_price < ema
            
            ema_cross_up = False
            ema_cross_down = False
            
            if self.last_ema is not None:
                last_price_above_ema = market_data.get('last_price', current_price) > self.last_ema
                last_price_below_ema = market_data.get('last_price', current_price) < self.last_ema
                
                ema_cross_up = price_above_ema and not last_price_above_ema
                ema_cross_down = price_below_ema and not last_price_below_ema
            
            obv_rising = all(
                self.obv_history[i] < self.obv_history[i + 1]
                for i in range(len(self.obv_history) - 1)
            )
            obv_falling = all(
                self.obv_history[i] > self.obv_history[i + 1]
                for i in range(len(self.obv_history) - 1)
            )
            
            self.last_ema = ema
            self.last_obv = obv
            
            signal_strength = 0.0
            action = SignalAction.HOLD
            
            if ema_cross_up and obv_rising:
                distance_from_ema = (current_price - ema) / ema
                signal_strength = 0.7 + min(0.3, distance_from_ema * 10)
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.BUY
            
            elif ema_cross_down and obv_falling:
                distance_from_ema = (ema - current_price) / ema
                signal_strength = 0.7 + min(0.3, distance_from_ema * 10)
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.SELL
            
            if action == SignalAction.HOLD:
                return self._create_hold_signal(current_price, timestamp)
            
            stop_loss = self._calculate_stop_loss(current_price, action)
            take_profit = self._calculate_take_profit(current_price, action)
            
            justification = (
                f"EMA({self.ema_period}) crossover with OBV confirmation. "
                f"Price ${current_price:.2f} {'above' if action == SignalAction.BUY else 'below'} EMA ${ema:.2f}. "
                f"OBV {'rising' if action == SignalAction.BUY else 'falling'} - volume confirms trend."
            )
            
            invalidation_conditions = [
                f"Price crosses back {'below' if action == SignalAction.BUY else 'above'} EMA ${ema:.2f}",
                f"OBV reverses direction"
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
                    'strategy': 'EmaObv',
                    'timeframe': self.timeframe,
                    'ema': ema,
                    'obv': obv,
                    'obv_rising': obv_rising,
                    'obv_falling': obv_falling,
                    'justification': justification,
                    'invalidation_conditions': invalidation_conditions,
                }
            )
            self.record_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error generating EmaObv signal: {e}")
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
            f"EmaObv trade completed: "
            f"Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, "
            f"P&L {profit_pct:.2f}%, Duration {trade_duration:.1f}h"
        )
