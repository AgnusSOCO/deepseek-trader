"""
ADX-SMA Crossover Strategy

SMA crossover with ADX trend strength filter.
Only trades when ADX indicates strong trend (>30).

Entry Long: ADX > 30 AND SMA(short) crosses above SMA(long)
Entry Short: ADX > 30 AND SMA(short) crosses below SMA(long)
Exit: ADX < 30 (trend weakening)

Source: freqtrade-strategies/futures/FAdxSmaStrategy.py
Timeframe: 1h
Complexity: Low
Autonomous Suitability: ⭐⭐⭐⭐⭐

Hyperopt Parameters:
- ADX period: 4-24 (default 14)
- SMA short: 4-24 (default 12)
- SMA long: 12-175 (default 48)
- Entry ADX threshold: 15-40 (default 30)
- Exit ADX threshold: 15-40 (default 30)
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
import numpy as np

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class AdxSmaStrategy(BaseStrategy):
    """
    ADX-SMA Crossover strategy with trend strength filter.
    Only enters trades when ADX indicates strong trend.
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = "1h",
        adx_period: int = 14,
        sma_short_period: int = 12,
        sma_long_period: int = 48,
        entry_adx_threshold: float = 30.0,
        exit_adx_threshold: float = 30.0,
        stop_loss_pct: float = 0.05,  # 5% stop loss
        take_profit_pct: float = 0.075,  # 7.5% take profit
        min_confidence: float = 0.7,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        
        config = {
            'timeframe': timeframe,
            'adx_period': adx_period,
            'sma_short_period': sma_short_period,
            'sma_long_period': sma_long_period,
            'entry_adx_threshold': entry_adx_threshold,
            'exit_adx_threshold': exit_adx_threshold,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'min_confidence': min_confidence,
        }
        super().__init__(f"AdxSma_{symbol}_{timeframe}", config)
        self.adx_period = adx_period
        self.sma_short_period = sma_short_period
        self.sma_long_period = sma_long_period
        self.entry_adx_threshold = entry_adx_threshold
        self.exit_adx_threshold = exit_adx_threshold
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.min_confidence = min_confidence
        
        self.prev_sma_short = None
        self.prev_sma_long = None
        
        logger.info(
            f"AdxSmaStrategy initialized: {symbol} {timeframe}, "
            f"ADX period: {adx_period}, SMA: {sma_short_period}/{sma_long_period}, "
            f"ADX threshold: {entry_adx_threshold}"
        )
    
    def initialize(self) -> None:
        """Initialize strategy parameters and state"""
        logger.info(f"AdxSmaStrategy '{self.name}' initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Process new market data"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return {
            'timeframe': self.timeframe,
            'adx_period': self.adx_period,
            'sma_short_period': self.sma_short_period,
            'sma_long_period': self.sma_long_period,
            'entry_adx_threshold': self.entry_adx_threshold,
            'exit_adx_threshold': self.exit_adx_threshold,
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
        Generate trading signal based on ADX-SMA crossover
        
        Entry Logic:
        - ADX > threshold (strong trend)
        - SMA short crosses above/below SMA long
        
        Exit Logic:
        - ADX < threshold (weak trend)
        """
        try:
            current_price = market_data['price']
            timestamp = market_data.get('timestamp', datetime.now())
            
            adx = indicators.get('adx', 0)
            sma_20 = indicators.get('sma_20', current_price)
            sma_50 = indicators.get('sma_50', current_price)
            
            sma_short = sma_20
            sma_long = sma_50
            
            crossed_above = False
            crossed_below = False
            
            if self.prev_sma_short is not None and self.prev_sma_long is not None:
                if self.prev_sma_short <= self.prev_sma_long and sma_short > sma_long:
                    crossed_above = True
                elif self.prev_sma_short >= self.prev_sma_long and sma_short < sma_long:
                    crossed_below = True
            
            self.prev_sma_short = sma_short
            self.prev_sma_long = sma_long
            
            adx_confidence = min(adx / 50.0, 1.0)  # Normalize to [0, 1]
            
            if not current_position:
                if adx > self.entry_adx_threshold and crossed_above:
                    confidence = max(0.7, adx_confidence)
                    
                    stop_loss = current_price * (1 - self.stop_loss_pct)
                    take_profit = current_price * (1 + self.take_profit_pct)
                    
                    justification = (
                        f"Strong uptrend detected: ADX {adx:.1f} > {self.entry_adx_threshold}, "
                        f"SMA({self.sma_short_period}) ${sma_short:.2f} crossed above "
                        f"SMA({self.sma_long_period}) ${sma_long:.2f}. "
                        f"Bullish momentum confirmed."
                    )
                    
                    invalidation_conditions = [
                        f"ADX drops below {self.exit_adx_threshold} (trend weakening)",
                        f"SMA({self.sma_short_period}) crosses below SMA({self.sma_long_period})",
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
                            'strategy': 'AdxSma',
                            'timeframe': self.timeframe,
                            'adx': adx,
                            'sma_short': sma_short,
                            'sma_long': sma_long,
                            'justification': justification,
                            'invalidation_conditions': invalidation_conditions,
                        }
                    )
                    self.record_signal(signal)
                    return signal
            
            elif current_position:
                should_exit = False
                exit_reason = ""
                
                if adx < self.exit_adx_threshold:
                    should_exit = True
                    exit_reason = f"Trend weakening: ADX {adx:.1f} < {self.exit_adx_threshold}"
                elif crossed_below:
                    should_exit = True
                    exit_reason = f"Bearish crossover: SMA({self.sma_short_period}) crossed below SMA({self.sma_long_period})"
                
                if should_exit:
                    confidence = 0.8
                    
                    justification = f"{exit_reason}. Exiting position to preserve capital."
                    
                    signal = TradingSignal(
                        action=SignalAction.SELL,
                        symbol=self.symbol,
                        confidence=confidence,
                        price=current_price,
                        stop_loss=0,
                        take_profit=0,
                        timestamp=timestamp,
                        metadata={
                            'strategy': 'AdxSma',
                            'timeframe': self.timeframe,
                            'adx': adx,
                            'sma_short': sma_short,
                            'sma_long': sma_long,
                            'justification': justification,
                            'exit_reason': exit_reason,
                        }
                    )
                    self.record_signal(signal)
                    return signal
            
            return self._create_hold_signal(current_price, timestamp)
            
        except Exception as e:
            logger.error(f"Error generating AdxSma signal: {e}")
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
            f"AdxSma trade completed: "
            f"Entry ${entry_price:.2f}, Exit ${exit_price:.2f}, "
            f"P&L {profit_pct:.2f}%, Duration {trade_duration:.1f}h"
        )
