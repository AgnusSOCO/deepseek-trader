"""
Universal MACD Strategy

Simplified MACD using EMA ratio instead of difference.
Formula: UMACD = (EMA12 / EMA26) - 1

Entry: UMACD between buy_min and buy_max thresholds
Exit: UMACD between sell_min and sell_max thresholds

Source: freqtrade-strategies/UniversalMACD.py
Author: @mablue
Reference: https://www.tradingview.com/script/xNEWcB8s-Universal-Moving-Average-Convergence-Divergence/

Hyperopt Results: 92.90% total profit over 40 trades
Timeframe: 5m
Complexity: Low
Autonomous Suitability: ⭐⭐⭐⭐⭐
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class UniversalMacdStrategy(BaseStrategy):
    """
    Universal MACD strategy using normalized EMA ratio.
    More stable across different price levels than traditional MACD.
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "5m",
        ema_fast_period: int = 12,
        ema_slow_period: int = 26,
        buy_umacd_min: float = -0.03,  # Optimized: was -0.01416
        buy_umacd_max: float = -0.008,  # Optimized: was -0.01176
        sell_umacd_min: float = -0.03,  # Optimized: was -0.02323
        sell_umacd_max: float = -0.008,  # Optimized: was -0.00707
        stop_loss_pct: float = 0.318,  # 31.8% from hyperopt
        take_profit_pct: float = 0.213,  # 21.3% from hyperopt
        min_confidence: float = 0.4,  # Optimized: was 0.65
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        
        config = {
            'timeframe': timeframe,
            'ema_fast_period': ema_fast_period,
            'ema_slow_period': ema_slow_period,
            'buy_umacd_min': buy_umacd_min,
            'buy_umacd_max': buy_umacd_max,
            'sell_umacd_min': sell_umacd_min,
            'sell_umacd_max': sell_umacd_max,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'min_confidence': min_confidence,
        }
        super().__init__(f"UniversalMacd_{symbol}_{timeframe}", config)
        self.ema_fast_period = ema_fast_period
        self.ema_slow_period = ema_slow_period
        self.buy_umacd_min = buy_umacd_min
        self.buy_umacd_max = buy_umacd_max
        self.sell_umacd_min = sell_umacd_min
        self.sell_umacd_max = sell_umacd_max
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.min_confidence = min_confidence
        
        logger.info(
            f"UniversalMacdStrategy initialized: {symbol} {timeframe}, "
            f"EMA: {ema_fast_period}/{ema_slow_period}, "
            f"buy range: [{buy_umacd_min:.5f}, {buy_umacd_max:.5f}]"
        )
    
    def initialize(self) -> None:
        """Initialize strategy parameters and state"""
        logger.info(f"UniversalMacdStrategy '{self.name}' initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Process new market data"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return {
            'timeframe': self.timeframe,
            'ema_fast_period': self.ema_fast_period,
            'ema_slow_period': self.ema_slow_period,
            'buy_umacd_min': self.buy_umacd_min,
            'buy_umacd_max': self.buy_umacd_max,
            'sell_umacd_min': self.sell_umacd_min,
            'sell_umacd_max': self.sell_umacd_max,
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
        Generate trading signal based on Universal MACD
        
        Entry Logic:
        - UMACD = (EMA12 / EMA26) - 1
        - UMACD in buy range [min, max]
        
        Exit Logic:
        - UMACD in sell range [min, max]
        """
        try:
            current_price = market_data['price']
            timestamp = market_data.get('timestamp', datetime.now())
            
            ema_12 = indicators.get('ema_12', current_price)
            ema_26 = indicators.get('ema_26', current_price)
            
            trend_1h = indicators.get('trend_1h', 1)
            ema_12_1h = indicators.get('ema_12_1h', ema_12)
            ema_26_1h = indicators.get('ema_26_1h', ema_26)
            
            if ema_26 > 0:
                umacd = (ema_12 / ema_26) - 1.0
            else:
                umacd = 0.0
            
            def calculate_confidence(value: float, min_val: float, max_val: float) -> float:
                """Calculate confidence based on position in range"""
                if min_val >= max_val:
                    return 0.5
                range_size = max_val - min_val
                center = (min_val + max_val) / 2.0
                distance_from_center = abs(value - center)
                confidence = 1.0 - (distance_from_center / (range_size / 2.0))
                return max(0.5, min(0.95, confidence))
            
            if not current_position:
                if self.buy_umacd_min <= umacd <= self.buy_umacd_max and trend_1h == 1:
                    confidence = calculate_confidence(umacd, self.buy_umacd_min, self.buy_umacd_max)
                    
                    stop_loss = current_price * (1 - self.stop_loss_pct)
                    take_profit = current_price * (1 + self.take_profit_pct)
                    
                    justification = (
                        f"Universal MACD buy signal: UMACD {umacd:.5f} in optimal buy range "
                        f"[{self.buy_umacd_min:.5f}, {self.buy_umacd_max:.5f}]. "
                        f"EMA12 ${ema_12:.2f} / EMA26 ${ema_26:.2f} = {ema_12/ema_26:.5f}. "
                        f"1h trend bullish (EMA12_1h ${ema_12_1h:.2f} > EMA26_1h ${ema_26_1h:.2f}). "
                        f"Normalized momentum indicates bullish setup with HTF confirmation."
                    )
                    
                    invalidation_conditions = [
                        f"UMACD drops below {self.buy_umacd_min:.5f} (momentum lost)",
                        f"UMACD rises above {self.buy_umacd_max:.5f} (overextended)",
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
                            'strategy': 'UniversalMacd',
                            'timeframe': self.timeframe,
                            'umacd': umacd,
                            'ema_12': ema_12,
                            'ema_26': ema_26,
                            'justification': justification,
                            'invalidation_conditions': invalidation_conditions,
                        }
                    )
                    self.record_signal(signal)
                    return signal
            
            elif current_position:
                if self.sell_umacd_min <= umacd <= self.sell_umacd_max:
                    confidence = calculate_confidence(umacd, self.sell_umacd_min, self.sell_umacd_max)
                    
                    justification = (
                        f"Universal MACD sell signal: UMACD {umacd:.5f} in optimal sell range "
                        f"[{self.sell_umacd_min:.5f}, {self.sell_umacd_max:.5f}]. "
                        f"Normalized momentum indicates exit point. Taking profit."
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
                            'strategy': 'UniversalMacd',
                            'timeframe': self.timeframe,
                            'umacd': umacd,
                            'ema_12': ema_12,
                            'ema_26': ema_26,
                            'justification': justification,
                        }
                    )
                    self.record_signal(signal)
                    return signal
            
            return self._create_hold_signal(current_price, timestamp)
            
        except Exception as e:
            logger.error(f"Error generating UniversalMacd signal: {e}")
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
            f"UniversalMacd trade completed: "
            f"Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, "
            f"P&L {profit_pct:.2f}%, Duration {trade_duration:.1f}h"
        )
