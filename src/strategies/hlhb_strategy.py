"""
HLHB System (Huck Loves Her Bucks)

Multi-indicator trend catching system with strong performance.
Uses RSI, EMA crossover, and ADX for trend confirmation.

Entry: RSI(10) crosses above 50 AND EMA(5) crosses above EMA(10) AND ADX > 25
Exit: RSI(10) crosses below 50 AND EMA(5) crosses below EMA(10) AND ADX > 25

Source: freqtrade-strategies/hlhb.py
Reference: https://www.babypips.com/trading/forex-hlhb-system-explained
Hyperopt Results: 62.25% ROI, -32.11% stoploss
Timeframe: 4h, 1h
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class HlhbStrategy(BaseStrategy):
    """
    HLHB (Huck Loves Her Bucks) multi-indicator trend strategy
    
    Features:
    - RSI(10) for momentum
    - EMA(5)/EMA(10) crossover for trend
    - ADX > 25 for trend strength
    - Catches strong trends with multiple confirmations
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "1h",
        rsi_period: int = 10,
        rsi_threshold: float = 50.0,
        ema_fast: int = 5,
        ema_slow: int = 10,
        adx_threshold: float = 25.0,
        min_confidence: float = 0.70,
        stop_loss_pct: float = 3.0,
        take_profit_pct: float = 6.0,
        max_trade_duration_minutes: int = 2880,
    ):
        """
        Initialize HLHB strategy
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe (1h, 4h recommended)
            rsi_period: RSI period
            rsi_threshold: RSI threshold for signals
            ema_fast: Fast EMA period
            ema_slow: Slow EMA period
            adx_threshold: Minimum ADX for trend strength
            min_confidence: Minimum confidence threshold
            stop_loss_pct: Stop-loss percentage
            take_profit_pct: Take-profit percentage
            max_trade_duration_minutes: Maximum trade duration
        """
        config = {
            'timeframe': timeframe,
            'rsi_period': rsi_period,
            'rsi_threshold': rsi_threshold,
            'ema_fast': ema_fast,
            'ema_slow': ema_slow,
            'adx_threshold': adx_threshold,
            'min_confidence': min_confidence,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'max_trade_duration_minutes': max_trade_duration_minutes,
        }
        super().__init__(name=f'Hlhb_{timeframe}', config=config)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.rsi_period = rsi_period
        self.rsi_threshold = rsi_threshold
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.adx_threshold = adx_threshold
        self.min_confidence = min_confidence
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_trade_duration_minutes = max_trade_duration_minutes
        
        self.last_rsi = None
        self.last_ema_fast = None
        self.last_ema_slow = None
        
        logger.info(
            f"HlhbStrategy initialized: {symbol} {timeframe}, "
            f"RSI={rsi_period}, EMA={ema_fast}/{ema_slow}, ADX>{adx_threshold}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy"""
        self.is_initialized = True
        logger.info(f"HlhbStrategy '{self.name}' initialized")
    
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
        Generate trading signal based on HLHB system
        
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
            
            rsi = indicators.get('rsi', 50)
            ema_fast = indicators.get('ema_5', current_price)
            ema_slow = indicators.get('ema_10', current_price)
            adx = indicators.get('adx', 0)
            
            if adx == 0:
                return self._create_hold_signal(current_price, timestamp)
            
            rsi_cross_up = False
            rsi_cross_down = False
            
            if self.last_rsi is not None:
                rsi_cross_up = rsi > self.rsi_threshold and self.last_rsi <= self.rsi_threshold
                rsi_cross_down = rsi < self.rsi_threshold and self.last_rsi >= self.rsi_threshold
            
            ema_cross_up = False
            ema_cross_down = False
            
            if self.last_ema_fast is not None and self.last_ema_slow is not None:
                ema_bullish = ema_fast > ema_slow
                ema_bearish = ema_fast < ema_slow
                last_ema_bullish = self.last_ema_fast > self.last_ema_slow
                last_ema_bearish = self.last_ema_fast < self.last_ema_slow
                
                ema_cross_up = ema_bullish and not last_ema_bullish
                ema_cross_down = ema_bearish and not last_ema_bearish
            
            self.last_rsi = rsi
            self.last_ema_fast = ema_fast
            self.last_ema_slow = ema_slow
            
            signal_strength = 0.0
            action = SignalAction.HOLD
            
            if rsi_cross_up and ema_cross_up and adx > self.adx_threshold:
                rsi_strength = min(1.0, (rsi - self.rsi_threshold) / 50)
                ema_separation = (ema_fast - ema_slow) / ema_slow
                adx_strength = min(1.0, (adx - self.adx_threshold) / 50)
                
                signal_strength = 0.6 + (0.15 * rsi_strength) + (0.15 * min(1.0, ema_separation * 10)) + (0.1 * adx_strength)
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.BUY
            
            elif rsi_cross_down and ema_cross_down and adx > self.adx_threshold:
                rsi_strength = min(1.0, (self.rsi_threshold - rsi) / 50)
                ema_separation = (ema_slow - ema_fast) / ema_slow
                adx_strength = min(1.0, (adx - self.adx_threshold) / 50)
                
                signal_strength = 0.6 + (0.15 * rsi_strength) + (0.15 * min(1.0, ema_separation * 10)) + (0.1 * adx_strength)
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.SELL
            
            if action == SignalAction.HOLD:
                return self._create_hold_signal(current_price, timestamp)
            
            stop_loss = self._calculate_stop_loss(current_price, action)
            take_profit = self._calculate_take_profit(current_price, action)
            
            justification = (
                f"HLHB system: RSI({self.rsi_period}) crossed {'above' if action == SignalAction.BUY else 'below'} {self.rsi_threshold}, "
                f"EMA({self.ema_fast}) crossed {'above' if action == SignalAction.BUY else 'below'} EMA({self.ema_slow}), "
                f"ADX {adx:.1f} > {self.adx_threshold} confirms strong trend."
            )
            
            invalidation_conditions = [
                f"RSI crosses back {'below' if action == SignalAction.BUY else 'above'} {self.rsi_threshold}",
                f"EMA crossover reverses",
                f"ADX drops below {self.adx_threshold}"
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
                    'strategy': 'Hlhb',
                    'timeframe': self.timeframe,
                    'rsi': rsi,
                    'ema_fast': ema_fast,
                    'ema_slow': ema_slow,
                    'adx': adx,
                    'justification': justification,
                    'invalidation_conditions': invalidation_conditions,
                }
            )
            self.record_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error generating Hlhb signal: {e}")
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
            f"Hlhb trade completed: "
            f"Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, "
            f"P&L {profit_pct:.2f}%, Duration {trade_duration:.1f}h"
        )
