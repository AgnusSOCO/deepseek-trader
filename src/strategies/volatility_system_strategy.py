"""
Volatility System Strategy (ATR Breakout with Pyramiding)

ATR-based volatility breakout system with position pyramiding.
Catches big moves and adds to winning positions.

Entry Long: close_change > ATR * 2.0
Entry Short: close_change * -1 > ATR * 2.0
Exit: Opposite signal triggers exit

Features:
- Position pyramiding (adds to winning positions)
- 50% stake on initial entry, 50% on pyramid
- Max 2 successful entries per trade
- Leverage: 2x

Source: freqtrade-strategies/futures/VolatilitySystem.py
Reference: https://www.tradingview.com/script/3hhs0XbR/
Timeframe: 1h (resampled to 3h for ATR)
Complexity: Medium
Autonomous Suitability: ⭐⭐⭐⭐⭐
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class VolatilitySystemStrategy(BaseStrategy):
    """
    Volatility System strategy using ATR breakout with pyramiding.
    Catches explosive moves and scales into winners.
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "1h",
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        leverage: float = 2.0,
        initial_stake_pct: float = 0.5,  # 50% on initial entry
        pyramid_stake_pct: float = 0.5,  # 50% on pyramid
        max_pyramids: int = 1,  # Max 1 additional entry (2 total)
        stop_loss_pct: float = 0.05,  # 5% stop loss
        min_confidence: float = 0.75,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        
        config = {
            'timeframe': timeframe,
            'atr_period': atr_period,
            'atr_multiplier': atr_multiplier,
            'leverage': leverage,
            'initial_stake_pct': initial_stake_pct,
            'pyramid_stake_pct': pyramid_stake_pct,
            'max_pyramids': max_pyramids,
            'stop_loss_pct': stop_loss_pct,
            'min_confidence': min_confidence,
        }
        super().__init__(f"VolatilitySystem_{symbol}_{timeframe}", config)
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.leverage = leverage
        self.initial_stake_pct = initial_stake_pct
        self.pyramid_stake_pct = pyramid_stake_pct
        self.max_pyramids = max_pyramids
        self.stop_loss_pct = stop_loss_pct
        self.min_confidence = min_confidence
        
        self.prev_close = None
        
        self.pyramid_count = 0
        self.position_direction = None  # 'long' or 'short'
        
        logger.info(
            f"VolatilitySystemStrategy initialized: {symbol} {timeframe}, "
            f"ATR: {atr_period} * {atr_multiplier}, "
            f"leverage: {leverage}x, pyramiding: {max_pyramids}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy parameters and state"""
        logger.info(f"VolatilitySystemStrategy '{self.name}' initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Process new market data"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return {
            'timeframe': self.timeframe,
            'atr_period': self.atr_period,
            'atr_multiplier': self.atr_multiplier,
            'leverage': self.leverage,
            'max_pyramids': self.max_pyramids,
            'stop_loss_pct': self.stop_loss_pct,
            'min_confidence': self.min_confidence,
        }
    
    def generate_signal(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any],
        current_position: Optional[Dict[str, Any]] = None
    ) -> TradingSignal:
        """
        Generate trading signal based on ATR volatility breakout
        
        Entry Logic:
        - Long: close_change > ATR * multiplier
        - Short: close_change < -ATR * multiplier
        
        Pyramiding Logic:
        - Add to position on continued breakout
        - Max 2 entries total (1 initial + 1 pyramid)
        
        Exit Logic:
        - Opposite signal triggers exit
        """
        try:
            current_price = market_data['price']
            timestamp = market_data.get('timestamp', datetime.now())
            
            atr = indicators.get('atr', current_price * 0.02)  # Default 2% if missing
            
            if self.prev_close is not None:
                close_change = current_price - self.prev_close
                abs_close_change = abs(close_change)
            else:
                close_change = 0
                abs_close_change = 0
            
            self.prev_close = current_price
            
            atr_threshold = atr * self.atr_multiplier
            
            long_breakout = close_change > atr_threshold
            short_breakout = close_change < -atr_threshold
            
            if atr_threshold > 0:
                breakout_strength = abs_close_change / atr_threshold
                confidence = min(0.95, 0.75 + (0.2 * (breakout_strength - 1.0)))
            else:
                confidence = 0.75
            
            if not current_position:
                if long_breakout:
                    stop_loss = current_price * (1 - self.stop_loss_pct)
                    take_profit = current_price * (1 + (self.stop_loss_pct * 3))  # 3:1 R/R
                    
                    justification = (
                        f"Volatility breakout LONG: Price change ${close_change:.2f} "
                        f"> ATR threshold ${atr_threshold:.2f} ({self.atr_multiplier}x). "
                        f"Strong upward momentum detected. "
                        f"Initial position: {self.initial_stake_pct*100:.0f}% stake, "
                        f"{self.leverage}x leverage."
                    )
                    
                    invalidation_conditions = [
                        f"Price drops below ${stop_loss:.2f} (stop loss)",
                        f"Opposite breakout signal (short)",
                        f"ATR expansion reverses"
                    ]
                    
                    self.pyramid_count = 0
                    self.position_direction = 'long'
                    
                    signal = TradingSignal(
                        action=SignalAction.BUY,
                        symbol=self.symbol,
                        confidence=confidence,
                        price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        timestamp=timestamp,
                        metadata={
                            'strategy': 'VolatilitySystem',
                            'timeframe': self.timeframe,
                            'atr': atr,
                            'close_change': close_change,
                            'atr_threshold': atr_threshold,
                            'leverage': self.leverage,
                            'stake_pct': self.initial_stake_pct,
                            'is_pyramid': False,
                            'justification': justification,
                            'invalidation_conditions': invalidation_conditions,
                        }
                    )
                    self.record_signal(signal)
                    return signal
                
                elif short_breakout:
                    stop_loss = current_price * (1 + self.stop_loss_pct)
                    take_profit = current_price * (1 - (self.stop_loss_pct * 3))  # 3:1 R/R
                    
                    justification = (
                        f"Volatility breakout SHORT: Price change ${close_change:.2f} "
                        f"< -ATR threshold ${-atr_threshold:.2f} ({self.atr_multiplier}x). "
                        f"Strong downward momentum detected. "
                        f"Initial position: {self.initial_stake_pct*100:.0f}% stake, "
                        f"{self.leverage}x leverage."
                    )
                    
                    invalidation_conditions = [
                        f"Price rises above ${stop_loss:.2f} (stop loss)",
                        f"Opposite breakout signal (long)",
                        f"ATR expansion reverses"
                    ]
                    
                    self.pyramid_count = 0
                    self.position_direction = 'short'
                    
                    signal = TradingSignal(
                        action=SignalAction.SELL,
                        symbol=self.symbol,
                        confidence=confidence,
                        price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        timestamp=timestamp,
                        metadata={
                            'strategy': 'VolatilitySystem',
                            'timeframe': self.timeframe,
                            'atr': atr,
                            'close_change': close_change,
                            'atr_threshold': atr_threshold,
                            'leverage': self.leverage,
                            'stake_pct': self.initial_stake_pct,
                            'is_pyramid': False,
                            'is_short': True,
                            'justification': justification,
                            'invalidation_conditions': invalidation_conditions,
                        }
                    )
                    self.record_signal(signal)
                    return signal
            
            elif current_position and self.pyramid_count < self.max_pyramids:
                if self.position_direction == 'long' and long_breakout:
                    self.pyramid_count += 1
                    
                    justification = (
                        f"Pyramiding LONG (entry #{self.pyramid_count + 1}): "
                        f"Continued breakout ${close_change:.2f} > ${atr_threshold:.2f}. "
                        f"Adding {self.pyramid_stake_pct*100:.0f}% to winning position."
                    )
                    
                    signal = TradingSignal(
                        action=SignalAction.BUY,
                        symbol=self.symbol,
                        confidence=confidence * 0.9,  # Slightly lower confidence for pyramid
                        price=current_price,
                        stop_loss=current_price * (1 - self.stop_loss_pct),
                        take_profit=current_price * (1 + (self.stop_loss_pct * 3)),
                        timestamp=timestamp,
                        metadata={
                            'strategy': 'VolatilitySystem',
                            'timeframe': self.timeframe,
                            'atr': atr,
                            'close_change': close_change,
                            'leverage': self.leverage,
                            'stake_pct': self.pyramid_stake_pct,
                            'is_pyramid': True,
                            'pyramid_number': self.pyramid_count,
                            'justification': justification,
                        }
                    )
                    self.record_signal(signal)
                    return signal
                
                elif self.position_direction == 'short' and short_breakout:
                    self.pyramid_count += 1
                    
                    justification = (
                        f"Pyramiding SHORT (entry #{self.pyramid_count + 1}): "
                        f"Continued breakout ${close_change:.2f} < ${-atr_threshold:.2f}. "
                        f"Adding {self.pyramid_stake_pct*100:.0f}% to winning position."
                    )
                    
                    signal = TradingSignal(
                        action=SignalAction.SELL,
                        symbol=self.symbol,
                        confidence=confidence * 0.9,
                        price=current_price,
                        stop_loss=current_price * (1 + self.stop_loss_pct),
                        take_profit=current_price * (1 - (self.stop_loss_pct * 3)),
                        timestamp=timestamp,
                        metadata={
                            'strategy': 'VolatilitySystem',
                            'timeframe': self.timeframe,
                            'atr': atr,
                            'close_change': close_change,
                            'leverage': self.leverage,
                            'stake_pct': self.pyramid_stake_pct,
                            'is_pyramid': True,
                            'is_short': True,
                            'pyramid_number': self.pyramid_count,
                            'justification': justification,
                        }
                    )
                    self.record_signal(signal)
                    return signal
            
            if current_position:
                should_exit = False
                exit_reason = ""
                
                if self.position_direction == 'long' and short_breakout:
                    should_exit = True
                    exit_reason = f"Opposite breakout: SHORT signal detected (change ${close_change:.2f})"
                elif self.position_direction == 'short' and long_breakout:
                    should_exit = True
                    exit_reason = f"Opposite breakout: LONG signal detected (change ${close_change:.2f})"
                
                if should_exit:
                    self.pyramid_count = 0
                    self.position_direction = None
                    
                    justification = f"{exit_reason}. Exiting position to avoid reversal."
                    
                    signal = TradingSignal(
                        action=SignalAction.SELL if self.position_direction == 'long' else SignalAction.BUY,
                        symbol=self.symbol,
                        confidence=0.85,
                        price=current_price,
                        stop_loss=0,
                        take_profit=0,
                        timestamp=timestamp,
                        metadata={
                            'strategy': 'VolatilitySystem',
                            'timeframe': self.timeframe,
                            'atr': atr,
                            'close_change': close_change,
                            'justification': justification,
                            'exit_reason': exit_reason,
                        }
                    )
                    self.record_signal(signal)
                    return signal
            
            return self._create_hold_signal(current_price, timestamp)
            
        except Exception as e:
            logger.error(f"Error generating VolatilitySystem signal: {e}")
            return self._create_hold_signal(current_price, timestamp)
    
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
        
        self.pyramid_count = 0
        self.position_direction = None
        
        logger.info(
            f"VolatilitySystem trade completed: "
            f"Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, "
            f"P&L {profit_pct:.2f}%, Duration {trade_duration:.1f}h"
        )
