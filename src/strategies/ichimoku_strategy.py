"""
Ichimoku Cloud Strategy

Comprehensive Japanese technical analysis system developed by Goichi Hosoda.
Used by Japanese institutional traders for decades.

Entry: Price above cloud, Tenkan > Kijun, Chikou above price
Exit: Price below cloud or Tenkan < Kijun
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class IchimokuStrategy(BaseStrategy):
    """
    Ichimoku Cloud strategy
    
    Features:
    - Multi-component trend system (5 lines)
    - Cloud provides support/resistance zones
    - Comprehensive trend direction signals
    - Works in all market conditions
    """
    
    def __init__(
        self,
        symbol: str,
        timeframe: str = '1h',
        min_confidence: float = 0.80,
        stop_loss_pct: float = 2.0,
        take_profit_pct: float = 4.5,
        max_trade_duration_minutes: int = 2880,
        min_minutes_between_trades: int = 180
    ):
        """
        Initialize Ichimoku strategy
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe (1h or 4h recommended)
            min_confidence: Minimum confidence threshold
            stop_loss_pct: Stop-loss percentage
            take_profit_pct: Take-profit percentage
            max_trade_duration_minutes: Maximum trade duration
        """
        config = {
            'stop_loss_pct': stop_loss_pct,
            'take_profit_pct': take_profit_pct,
            'max_trade_duration_minutes': max_trade_duration_minutes,
            'min_minutes_between_trades': min_minutes_between_trades,
        }
        super().__init__(name=f'Ichimoku_{timeframe}', config=config)
        
        self.symbol = symbol
        self.timeframe = timeframe
        self.min_confidence = min_confidence
        
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        self.max_trade_duration_minutes = max_trade_duration_minutes
        self.min_minutes_between_trades = min_minutes_between_trades
        
        self.total_trades = 0
        self.winning_trades = 0
        self.total_pnl = 0.0
        self.last_trade_time = None
        logger.info(
            f"IchimokuStrategy initialized: {symbol} {timeframe}"
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
        Generate trading signal based on Ichimoku Cloud
        
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
            
            tenkan_sen = indicators.get('tenkan_sen', current_price)
            kijun_sen = indicators.get('kijun_sen', current_price)
            senkou_span_a = indicators.get('senkou_span_a', current_price)
            senkou_span_b = indicators.get('senkou_span_b', current_price)
            chikou_span = indicators.get('chikou_span', current_price)
            
            if tenkan_sen == 0 or kijun_sen == 0:
                return self._create_hold_signal(current_price, timestamp)
            
            cloud_top = max(senkou_span_a, senkou_span_b)
            cloud_bottom = min(senkou_span_a, senkou_span_b)
            cloud_thickness = abs(senkou_span_a - senkou_span_b)
            
            price_above_cloud = current_price > cloud_top
            price_below_cloud = current_price < cloud_bottom
            price_in_cloud = not price_above_cloud and not price_below_cloud
            
            tenkan_above_kijun = tenkan_sen > kijun_sen
            tenkan_below_kijun = tenkan_sen < kijun_sen
            
            tk_cross_up = tenkan_above_kijun
            tk_cross_down = tenkan_below_kijun
            
            if self.last_trade_time is not None:
                time_since_last_trade = (timestamp - self.last_trade_time).total_seconds() / 60
                if time_since_last_trade < self.min_minutes_between_trades:
                    return self._create_hold_signal(current_price, timestamp)
            
            signal_strength = 0.0
            action = SignalAction.HOLD
            
            if price_above_cloud and tk_cross_up:
                distance_from_cloud = (current_price - cloud_top) / current_price
                tk_separation = (tenkan_sen - kijun_sen) / kijun_sen
                
                signal_strength = 0.6
                
                if distance_from_cloud > 0.01:
                    signal_strength += 0.15
                
                if tk_separation > 0.005:
                    signal_strength += 0.15
                
                if cloud_thickness > 0:
                    cloud_strength = min(cloud_thickness / current_price * 100, 0.1)
                    signal_strength += cloud_strength
                
                signal_strength = min(1.0, signal_strength)
                
                if signal_strength >= self.min_confidence:
                    action = SignalAction.BUY
                    
            elif price_below_cloud and tk_cross_down:
                distance_from_cloud = (cloud_bottom - current_price) / current_price
                tk_separation = (kijun_sen - tenkan_sen) / kijun_sen
                
                signal_strength = 0.6
                
                if distance_from_cloud > 0.01:
                    signal_strength += 0.15
                
                if tk_separation > 0.005:
                    signal_strength += 0.15
                
                if cloud_thickness > 0:
                    cloud_strength = min(cloud_thickness / current_price * 100, 0.1)
                    signal_strength += cloud_strength
                
                signal_strength = min(1.0, signal_strength)
                
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
                    'tenkan_sen': tenkan_sen,
                    'kijun_sen': kijun_sen,
                    'senkou_span_a': senkou_span_a,
                    'senkou_span_b': senkou_span_b,
                    'chikou_span': chikou_span,
                    'cloud_top': cloud_top,
                    'cloud_bottom': cloud_bottom,
                    'price_above_cloud': price_above_cloud,
                    'price_below_cloud': price_below_cloud,
                    'tenkan_above_kijun': tenkan_above_kijun
                }
            )
            self.last_trade_time = timestamp or datetime.now()
            self.record_signal(signal)
            return signal
            
        except Exception as e:
            logger.error(f"Error generating Ichimoku signal: {e}")
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
            f"Ichimoku trade result: PnL={profit_loss:.2f}, "
            f"Duration={trade_duration_minutes}min, "
            f"Win rate={self.winning_trades/self.total_trades:.2%}"
        )
