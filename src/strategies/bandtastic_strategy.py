"""
Bandtastic Strategy (Multi-Level Bollinger Bands)

Uses 4 levels of Bollinger Bands (1-4 standard deviations) for mean reversion.
Highly successful high-frequency strategy with proven results.

Entry: Price crosses below BB lower band with RSI/MFI/EMA filters
Exit: Price crosses above BB upper band with filters

Source: freqtrade-strategies/Bandtastic.py
Author: Robert Roman

Hyperopt Results: 119.93% total profit over 30,918 trades (1 year)
Timeframe: 15m
Complexity: Medium
Autonomous Suitability: ⭐⭐⭐⭐⭐
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class BandtasticStrategy(BaseStrategy):
    """
    Multi-level Bollinger Band mean reversion strategy.
    Uses 4 BB levels with RSI/MFI/EMA filters.
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "15m",
        bb_window: int = 20,
        buy_bb_level: int = 1,  # 1-4 std dev (default 1)
        buy_rsi_threshold: float = 52.0,
        buy_mfi_threshold: float = 30.0,
        sell_bb_level: int = 2,  # 1-4 std dev (default 2)
        sell_rsi_threshold: float = 57.0,
        sell_mfi_threshold: float = 46.0,
        fast_ema_period: int = 211,
        slow_ema_period: int = 250,
        stop_loss_pct: float = 0.02,  # 2% stop loss
        take_profit_pct: float = 0.03,  # 3% take profit
        min_confidence: float = 0.6,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        
        config = {
            'timeframe': timeframe,
            'bb_window': bb_window,
            'buy_bb_level': buy_bb_level,
            'buy_rsi_threshold': buy_rsi_threshold,
            'buy_mfi_threshold': buy_mfi_threshold,
            'sell_bb_level': sell_bb_level,
            'sell_rsi_threshold': sell_rsi_threshold,
            'sell_mfi_threshold': sell_mfi_threshold,
            'fast_ema_period': fast_ema_period,
            'slow_ema_period': slow_ema_period,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'min_confidence': min_confidence,
        }
        super().__init__(f"Bandtastic_{symbol}_{timeframe}", config)
        self.bb_window = bb_window
        self.buy_bb_level = buy_bb_level
        self.buy_rsi_threshold = buy_rsi_threshold
        self.buy_mfi_threshold = buy_mfi_threshold
        self.sell_bb_level = sell_bb_level
        self.sell_rsi_threshold = sell_rsi_threshold
        self.sell_mfi_threshold = sell_mfi_threshold
        self.fast_ema_period = fast_ema_period
        self.slow_ema_period = slow_ema_period
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.min_confidence = min_confidence
        
        logger.info(
            f"BandtasticStrategy initialized: {symbol} {timeframe}, "
            f"BB levels: buy={buy_bb_level}, sell={sell_bb_level}, "
            f"RSI: {buy_rsi_threshold}/{sell_rsi_threshold}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy parameters and state"""
        logger.info(f"BandtasticStrategy '{self.name}' initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Process new market data"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return {
            'timeframe': self.timeframe,
            'bb_window': self.bb_window,
            'buy_bb_level': self.buy_bb_level,
            'sell_bb_level': self.sell_bb_level,
            'stop_loss_pct': self.stop_loss_pct,
            'take_profit_pct': self.take_profit_pct,
            'min_confidence': self.min_confidence,
        }
    
    def generate_signal(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any],
        current_position: Optional[Dict[str, Any]] = None
    ) -> TradingSignal:
        """
        Generate trading signal based on multi-level Bollinger Bands
        
        Entry Logic:
        - Price < BB lower band (oversold)
        - RSI < threshold (momentum filter)
        - MFI < threshold (volume filter)
        - Price > fast EMA (trend filter)
        
        Exit Logic:
        - Price > BB upper band (overbought)
        - RSI > threshold
        - MFI > threshold
        """
        try:
            current_price = market_data['price']
            timestamp = market_data.get('timestamp', datetime.now())
            
            bb_upper = indicators.get('bb_upper', current_price * 1.02)
            bb_middle = indicators.get('bb_middle', current_price)
            bb_lower = indicators.get('bb_lower', current_price * 0.98)
            rsi = indicators.get('rsi', 50)
            mfi = indicators.get('mfi', 50)
            ema_12 = indicators.get('ema_12', current_price)
            ema_26 = indicators.get('ema_26', current_price)
            
            bb_std = (bb_upper - bb_middle) / 2.0  # Standard deviation
            
            buy_bb_lower = bb_middle - (self.buy_bb_level * bb_std)
            
            sell_bb_upper = bb_middle + (self.sell_bb_level * bb_std)
            
            distance_from_lower = (current_price - buy_bb_lower) / bb_std if bb_std > 0 else 0
            distance_from_upper = (sell_bb_upper - current_price) / bb_std if bb_std > 0 else 0
            
            if not current_position:
                if (current_price < buy_bb_lower and 
                    rsi < self.buy_rsi_threshold and
                    mfi < self.buy_mfi_threshold and
                    current_price > ema_12):  # Trend filter
                    
                    confidence = min(0.9, 0.6 + (0.3 * abs(distance_from_lower)))
                    
                    stop_loss = current_price * (1 - self.stop_loss_pct)
                    take_profit = current_price * (1 + self.take_profit_pct)
                    
                    justification = (
                        f"Oversold mean reversion setup: Price ${current_price:.2f} "
                        f"< BB lower({self.buy_bb_level}σ) ${buy_bb_lower:.2f}, "
                        f"RSI {rsi:.1f} < {self.buy_rsi_threshold}, "
                        f"MFI {mfi:.1f} < {self.buy_mfi_threshold}. "
                        f"Expecting bounce to BB middle ${bb_middle:.2f}."
                    )
                    
                    invalidation_conditions = [
                        f"Price continues below ${buy_bb_lower * 0.98:.2f} (breakdown)",
                        f"RSI drops below 30 (extreme oversold)",
                        f"Price drops below stop loss ${stop_loss:.2f}"
                    ]
                    
                    signal = TradingSignal(
                        action=SignalAction.BUY,
                        symbol=self.symbol,
                        confidence=confidence,
                        price=current_price,
                        stop_loss=stop_loss,
                        take_profit=take_profit,
                        timestamp=timestamp,
                        metadata={
                            'strategy': 'Bandtastic',
                            'timeframe': self.timeframe,
                            'bb_lower': buy_bb_lower,
                            'bb_middle': bb_middle,
                            'bb_upper': sell_bb_upper,
                            'rsi': rsi,
                            'mfi': mfi,
                            'justification': justification,
                            'invalidation_conditions': invalidation_conditions,
                        }
                    )
                    self.record_signal(signal)
                    return signal
            
            elif current_position:
                if (current_price > sell_bb_upper and
                    rsi > self.sell_rsi_threshold and
                    mfi > self.sell_mfi_threshold):
                    
                    confidence = min(0.9, 0.6 + (0.3 * abs(distance_from_upper)))
                    
                    justification = (
                        f"Overbought mean reversion: Price ${current_price:.2f} "
                        f"> BB upper({self.sell_bb_level}σ) ${sell_bb_upper:.2f}, "
                        f"RSI {rsi:.1f} > {self.sell_rsi_threshold}, "
                        f"MFI {mfi:.1f} > {self.sell_mfi_threshold}. "
                        f"Taking profit on mean reversion."
                    )
                    
                    signal = TradingSignal(
                        action=SignalAction.SELL,
                        symbol=self.symbol,
                        confidence=confidence,
                        price=current_price,
                        stop_loss=0,
                        take_profit=0,
                        timestamp=timestamp,
                        metadata={
                            'strategy': 'Bandtastic',
                            'timeframe': self.timeframe,
                            'bb_upper': sell_bb_upper,
                            'bb_middle': bb_middle,
                            'rsi': rsi,
                            'mfi': mfi,
                            'justification': justification,
                        }
                    )
                    self.record_signal(signal)
                    return signal
            
            return self._create_hold_signal(current_price, timestamp)
            
        except Exception as e:
            logger.error(f"Error generating Bandtastic signal: {e}")
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
        
        logger.info(
            f"Bandtastic trade completed: "
            f"Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, "
            f"P&L {profit_pct:.2f}%, Duration {trade_duration:.1f}h"
        )
