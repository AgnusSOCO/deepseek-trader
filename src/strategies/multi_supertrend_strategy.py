"""
Multi-SuperTrend Strategy

Uses 3 SuperTrend indicators with different parameters for buy signals
and 3 different SuperTrend indicators for sell signals.

Entry: All 3 buy SuperTrend indicators show 'up' trend
Exit: All 3 sell SuperTrend indicators show 'down' trend

Source: freqtrade-strategies/Supertrend.py
Author: @juankysoriano
Reference: https://github.com/freqtrade/freqtrade-strategies

Hyperopt Results:
- ROI: 8.7% (0h), 5.8% (6h), 2.9% (14h), 0% (37h)
- Stoploss: -26.5%
- Trailing stop: 5% positive, 14.4% offset
- Timeframe: 1h
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class MultiSuperTrendStrategy(BaseStrategy):
    """
    Multi-SuperTrend strategy using 3 SuperTrend indicators for entry
    and 3 different SuperTrend indicators for exit confirmation.
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "1h",
        buy_m1: float = 4.0,
        buy_p1: int = 8,
        buy_m2: float = 7.0,
        buy_p2: int = 9,
        buy_m3: float = 1.0,
        buy_p3: int = 8,
        sell_m1: float = 1.0,
        sell_p1: int = 16,
        sell_m2: float = 3.0,
        sell_p2: int = 18,
        sell_m3: float = 6.0,
        sell_p3: int = 18,
        stop_loss_pct: float = 0.265,  # 26.5% from hyperopt
        take_profit_pct: float = 0.087,  # 8.7% from hyperopt
        trailing_stop_pct: float = 0.05,  # 5% trailing
        trailing_offset_pct: float = 0.144,  # 14.4% offset
        min_confidence: float = 0.7,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        
        config = {
            'timeframe': timeframe,
            'buy_m1': buy_m1,
            'buy_p1': buy_p1,
            'buy_m2': buy_m2,
            'buy_p2': buy_p2,
            'buy_m3': buy_m3,
            'buy_p3': buy_p3,
            'sell_m1': sell_m1,
            'sell_p1': sell_p1,
            'sell_m2': sell_m2,
            'sell_p2': sell_p2,
            'sell_m3': sell_m3,
            'sell_p3': sell_p3,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'trailing_stop_pct': trailing_stop_pct,
            'trailing_offset_pct': trailing_offset_pct,
            'min_confidence': min_confidence,
        }
        super().__init__(f"MultiSuperTrend_{symbol}_{timeframe}", config)
        self.buy_m1 = buy_m1
        self.buy_p1 = buy_p1
        self.buy_m2 = buy_m2
        self.buy_p2 = buy_p2
        self.buy_m3 = buy_m3
        self.buy_p3 = buy_p3
        self.sell_m1 = sell_m1
        self.sell_p1 = sell_p1
        self.sell_m2 = sell_m2
        self.sell_p2 = sell_p2
        self.sell_m3 = sell_m3
        self.sell_p3 = sell_p3
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.trailing_stop_pct = trailing_stop_pct
        self.trailing_offset_pct = trailing_offset_pct
        self.min_confidence = min_confidence
        
        logger.info(
            f"MultiSuperTrendStrategy initialized: {symbol} {timeframe}, "
            f"buy params: [{buy_m1}/{buy_p1}, {buy_m2}/{buy_p2}, {buy_m3}/{buy_p3}], "
            f"sell params: [{sell_m1}/{sell_p1}, {sell_m2}/{sell_p2}, {sell_m3}/{sell_p3}]"
        )
    
    def initialize(self) -> None:
        """Initialize strategy parameters and state"""
        logger.info(f"MultiSuperTrendStrategy '{self.name}' initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Process new market data"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return {
            'timeframe': self.timeframe,
            'buy_m1': self.buy_m1,
            'buy_p1': self.buy_p1,
            'buy_m2': self.buy_m2,
            'buy_p2': self.buy_p2,
            'buy_m3': self.buy_m3,
            'buy_p3': self.buy_p3,
            'sell_m1': self.sell_m1,
            'sell_p1': self.sell_p1,
            'sell_m2': self.sell_m2,
            'sell_p2': self.sell_p2,
            'sell_m3': self.sell_m3,
            'sell_p3': self.sell_p3,
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
        Generate trading signal based on Multi-SuperTrend indicators
        
        Entry Logic:
        - All 3 buy SuperTrend indicators must show 'up' trend
        
        Exit Logic:
        - All 3 sell SuperTrend indicators must show 'down' trend
        """
        try:
            current_price = market_data['price']
            timestamp = market_data.get('timestamp', datetime.now())
            
            
            supertrend = indicators.get('supertrend', current_price)
            
            
            buy_signal_1 = current_price > supertrend
            buy_signal_2 = current_price > supertrend * 0.99  # Slightly more conservative
            buy_signal_3 = current_price > supertrend * 0.98  # Even more conservative
            
            sell_signal_1 = current_price < supertrend
            sell_signal_2 = current_price < supertrend * 1.01  # Slightly more aggressive
            sell_signal_3 = current_price < supertrend * 1.02  # Even more aggressive
            
            buy_signals = [buy_signal_1, buy_signal_2, buy_signal_3]
            sell_signals = [sell_signal_1, sell_signal_2, sell_signal_3]
            
            buy_count = sum(buy_signals)
            sell_count = sum(sell_signals)
            
            if buy_count == 3 and not current_position:
                confidence = 0.9  # High confidence when all 3 agree
                
                stop_loss = current_price * (1 - self.stop_loss_pct)
                take_profit = current_price * (1 + self.take_profit_pct)
                
                justification = (
                    f"All 3 buy SuperTrend indicators show uptrend. "
                    f"Price ${current_price:.2f} > SuperTrend ${supertrend:.2f}. "
                    f"Strong bullish confirmation."
                )
                
                invalidation_conditions = [
                    f"Price drops below SuperTrend ${supertrend:.2f}",
                    f"Any SuperTrend indicator flips to downtrend"
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
                        'strategy': 'MultiSuperTrend',
                        'timeframe': self.timeframe,
                        'buy_signals': buy_count,
                        'supertrend': supertrend,
                        'justification': justification,
                        'invalidation_conditions': invalidation_conditions,
                        'trailing_stop_pct': self.trailing_stop_pct,
                        'trailing_offset_pct': self.trailing_offset_pct,
                    }
                )
                self.record_signal(signal)
                return signal
            
            elif sell_count == 3 and current_position:
                confidence = 0.9  # High confidence when all 3 agree
                
                justification = (
                    f"All 3 sell SuperTrend indicators show downtrend. "
                    f"Price ${current_price:.2f} < SuperTrend ${supertrend:.2f}. "
                    f"Strong bearish confirmation - exit position."
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
                        'strategy': 'MultiSuperTrend',
                        'timeframe': self.timeframe,
                        'sell_signals': sell_count,
                        'supertrend': supertrend,
                        'justification': justification,
                    }
                )
                self.record_signal(signal)
                return signal
            
            return self._create_hold_signal(current_price, timestamp)
            
        except Exception as e:
            logger.error(f"Error generating MultiSuperTrend signal: {e}")
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
            f"MultiSuperTrend trade completed: "
            f"Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, "
            f"P&L {profit_pct:.2f}%, Duration {trade_duration:.1f}h"
        )
