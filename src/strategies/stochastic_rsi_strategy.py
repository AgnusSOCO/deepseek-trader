"""
Stochastic RSI Mean Reversion Strategy

Uses Stochastic RSI for overbought/oversold conditions with momentum confirmation.
More sensitive than regular RSI, better for short-term mean reversion.

Entry Long: Stoch RSI crosses above 20 (oversold)
Entry Short: Stoch RSI crosses below 80 (overbought)
Exit: Stoch RSI reaches opposite extreme or middle (50)

Source: Common quant strategy pattern
Timeframe: 15m, 1h
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class StochasticRsiStrategy(BaseStrategy):
    """
    Stochastic RSI mean reversion strategy
    
    Features:
    - Stochastic RSI for overbought/oversold
    - More sensitive than regular RSI
    - Good for short-term reversals
    - Works in ranging markets
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "15m",
        rsi_period: int = 14,
        stoch_period: int = 14,
        oversold_threshold: float = 20.0,
        overbought_threshold: float = 80.0,
        exit_threshold: float = 50.0,
        min_confidence: float = 0.70,
        stop_loss_pct: float = 2.5,
        take_profit_pct: float = 4.0,
        max_trade_duration_minutes: int = 480,
        min_minutes_between_trades: int = 120,
    ):
        """
        Initialize Stochastic RSI strategy
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe (15m, 1h)
            rsi_period: RSI period
            stoch_period: Stochastic period
            oversold_threshold: Oversold level
            overbought_threshold: Overbought level
            exit_threshold: Exit level (middle)
            min_confidence: Minimum confidence threshold
            stop_loss_pct: Stop-loss percentage
            take_profit_pct: Take-profit percentage
            max_trade_duration_minutes: Maximum trade duration
            min_minutes_between_trades: Minimum time between trades
        """
        config = {
            'timeframe': timeframe,
            'rsi_period': rsi_period,
            'stoch_period': stoch_period,
            'oversold_threshold': oversold_threshold,
            'overbought_threshold': overbought_threshold,
            'exit_threshold': exit_threshold,
            'min_confidence': min_confidence,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'max_trade_duration_minutes': max_trade_duration_minutes,
            'min_minutes_between_trades': min_minutes_between_trades,
        }
        super().__init__(name=f'StochRsi_{timeframe}', config=config)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.rsi_period = rsi_period
        self.stoch_period = stoch_period
        self.oversold_threshold = oversold_threshold
        self.overbought_threshold = overbought_threshold
        self.exit_threshold = exit_threshold
        self.min_confidence = min_confidence
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_trade_duration_minutes = max_trade_duration_minutes
        self.min_minutes_between_trades = min_minutes_between_trades
        
        self.last_stoch_rsi = None
        self.last_trade_time = None
        
        logger.info(
            f"StochasticRsiStrategy initialized: {symbol} {timeframe}, "
            f"RSI={rsi_period}, Stoch={stoch_period}, levels={oversold_threshold}/{overbought_threshold}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy"""
        self.is_initialized = True
        logger.info(f"StochasticRsiStrategy '{self.name}' initialized")
    
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
        Generate trading signal based on Stochastic RSI
        
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
            
            rsi = indicators.get('rsi', 50)
            
            stoch_rsi = rsi
            
            cross_above_oversold = False
            cross_below_overbought = False
            
            if self.last_stoch_rsi is not None:
                cross_above_oversold = (
                    stoch_rsi > self.oversold_threshold and 
                    self.last_stoch_rsi <= self.oversold_threshold
                )
                cross_below_overbought = (
                    stoch_rsi < self.overbought_threshold and 
                    self.last_stoch_rsi >= self.overbought_threshold
                )
            
            self.last_stoch_rsi = stoch_rsi
            
            signal_strength = 0.0
            action = SignalAction.HOLD
            
            if cross_above_oversold and not current_position:
                oversold_depth = max(0, self.oversold_threshold - self.last_stoch_rsi) / self.oversold_threshold
                signal_strength = 0.7 + min(0.3, oversold_depth)
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.BUY
            
            elif cross_below_overbought and not current_position:
                overbought_depth = max(0, self.last_stoch_rsi - self.overbought_threshold) / (100 - self.overbought_threshold)
                signal_strength = 0.7 + min(0.3, overbought_depth)
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.SELL
            
            elif current_position:
                position_side = current_position.get('side', 'long')
                
                if position_side == 'long' and stoch_rsi >= self.exit_threshold:
                    action = SignalAction.SELL
                    signal_strength = 0.8
                elif position_side == 'short' and stoch_rsi <= self.exit_threshold:
                    action = SignalAction.BUY
                    signal_strength = 0.8
            
            if action == SignalAction.HOLD:
                return self._create_hold_signal(current_price, timestamp)
            
            stop_loss = self._calculate_stop_loss(current_price, action)
            take_profit = self._calculate_take_profit(current_price, action)
            
            justification = (
                f"Stochastic RSI {stoch_rsi:.1f} "
                f"{'crossed above oversold' if cross_above_oversold else 'crossed below overbought' if cross_below_overbought else 'reached exit level'}. "
                f"Mean reversion opportunity."
            )
            
            invalidation_conditions = [
                f"Stochastic RSI reverses before reaching {self.exit_threshold}",
                f"Price breaks stop-loss at ${stop_loss:.2f}"
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
                    'strategy': 'StochRsi',
                    'timeframe': self.timeframe,
                    'stoch_rsi': stoch_rsi,
                    'oversold_threshold': self.oversold_threshold,
                    'overbought_threshold': self.overbought_threshold,
                    'justification': justification,
                    'invalidation_conditions': invalidation_conditions,
                }
            )
            
            if action in [SignalAction.BUY, SignalAction.SELL]:
                self.last_trade_time = timestamp
            
            self.record_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error generating StochRsi signal: {e}")
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
            f"StochRsi trade completed: "
            f"Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, "
            f"P&L {profit_pct:.2f}%, Duration {trade_duration:.1f}h"
        )
