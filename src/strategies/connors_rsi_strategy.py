"""
Connors RSI(2) Mean Reversion Strategy

Short-term mean reversion strategy by Larry Connors.
Based on "Short Term Trading Strategies That Work" (2008).
Proven 60%+ win rate on S&P 500 backtests.

Entry: RSI(2) < 10 with price above SMA(200) for longs
       RSI(2) > 90 with price below SMA(200) for shorts
Exit: RSI(2) crosses back above 50 (longs) or below 50 (shorts)
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class ConnorsRSIStrategy(BaseStrategy):
    """
    Connors RSI(2) Mean Reversion strategy
    
    Features:
    - Ultra-short RSI period (2) for mean reversion signals
    - SMA(200) trend filter to trade with the trend
    - High win rate in ranging and mildly trending markets
    - Quick entries and exits
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = '15m',
        rsi_oversold: float = 5,
        rsi_overbought: float = 95,
        rsi_exit: float = 50,
        min_confidence: float = 0.75,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 3.0,
        max_trade_duration_minutes: int = 720,
        adx_max: float = 25.0,
        min_minutes_between_trades: int = 60,
        max_daily_trades: int = 15
    ):
        """
        Initialize Connors RSI strategy
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe (15m or 1h recommended)
            rsi_oversold: RSI threshold for oversold (10 default)
            rsi_overbought: RSI threshold for overbought (90 default)
            rsi_exit: RSI threshold for exit (50 default)
            min_confidence: Minimum confidence threshold
            stop_loss_pct: Stop-loss percentage
            take_profit_pct: Take-profit percentage
            max_trade_duration_minutes: Maximum trade duration
        """
        config = {
            'rsi_oversold': rsi_oversold,
            'rsi_overbought': rsi_overbought,
            'rsi_exit': rsi_exit,
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'max_trade_duration_minutes': max_trade_duration_minutes,
            'adx_max': adx_max,
            'min_minutes_between_trades': min_minutes_between_trades,
            'max_daily_trades': max_daily_trades,
        }
        super().__init__(name=f'ConnorsRSI_{timeframe}', config=config)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.min_confidence = min_confidence
        
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.rsi_exit = rsi_exit
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_trade_duration_minutes = max_trade_duration_minutes
        self.adx_max = adx_max
        
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        logger.info(
            f"ConnorsRSIStrategy initialized: {symbol} {timeframe}, "
            f"oversold={rsi_oversold}, overbought={rsi_overbought}"
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
        Generate trading signal based on Connors RSI(2)
        
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
            
            rsi_2 = indicators.get('rsi_2', 50)
            sma_200 = indicators.get('sma_200', current_price)
            sma_5 = indicators.get('sma_5', current_price)
            adx = indicators.get('adx', 0)
            volume = market_data.get('volume', 0)
            volume_avg = indicators.get('volume_avg', volume)
            
            if sma_200 == 0:
                sma_200 = current_price
            
            above_sma_200 = current_price > sma_200
            below_sma_200 = current_price < sma_200
            
            can_trade, reason = self.can_trade(timestamp or datetime.now())
            if not can_trade:
                return self._create_hold_signal(current_price, timestamp)
            
            if adx > self.adx_max:
                return self._create_hold_signal(current_price, timestamp)
            
            if volume < volume_avg * 0.8:
                return self._create_hold_signal(current_price, timestamp)
            
            signal_strength = 0.0
            action = SignalAction.HOLD
            
            if rsi_2 < self.rsi_oversold and above_sma_200:
                rsi_extreme = (self.rsi_oversold - rsi_2) / self.rsi_oversold
                trend_strength = (current_price - sma_200) / sma_200
                
                signal_strength = min(1.0, 0.7 + (0.2 * rsi_extreme) + (0.1 * min(trend_strength * 10, 1.0)))
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.BUY
                    
            elif rsi_2 > self.rsi_overbought and below_sma_200:
                rsi_extreme = (rsi_2 - self.rsi_overbought) / (100 - self.rsi_overbought)
                trend_strength = (sma_200 - current_price) / sma_200
                
                signal_strength = min(1.0, 0.7 + (0.2 * rsi_extreme) + (0.1 * min(trend_strength * 10, 1.0)))
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.SELL
            
            if action == SignalAction.HOLD:
                return self._create_hold_signal(current_price, timestamp)
            
            stop_loss = self._calculate_stop_loss(
                current_price, action
            )
            take_profit = self._calculate_take_profit(
                current_price, action
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
                    'rsi_2': rsi_2,
                    'sma_200': sma_200,
                    'sma_5': sma_5,
                    'above_sma_200': above_sma_200,
                    'below_sma_200': below_sma_200
                }
            )
            self.record_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error generating Connors RSI signal: {e}")
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
            f"Connors RSI trade result: PnL={profit_loss:.2f}, "
            f"Duration={trade_duration_minutes}min, "
            f"Win rate={self.winning_trades/self.total_trades:.2%}"
        )
