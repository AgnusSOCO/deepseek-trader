"""
Momentum Strategy

Trend-following strategy for capturing sustained price movements.
Targets 2-10% gains with trailing stop-losses.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class MomentumStrategy(BaseStrategy):
    """
    Momentum strategy for trend following
    
    Characteristics:
    - Timeframe: 15-minute to 4-hour candles
    - Trade duration: Several hours to multiple days
    - Profit target: 2-10% per trade
    - Leverage: 2x-5x
    - Trade frequency: 2-10 trades per week
    
    Entry Signals:
    - EMA crossovers (12/26)
    - ADX > 25 (strong trend)
    - RSI momentum confirmation (40-60 range)
    - MACD histogram expansion
    - Volume trend confirmation
    
    Exit Signals:
    - Trailing stop-loss (2-5%)
    - Trend reversal signals
    - ADX < 20 (weak trend)
    - EMA crossover reversal
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize momentum strategy
        
        Config parameters:
        - timeframe: Trading timeframe (default: '15m')
        - profit_target_pct: Profit target percentage (default: 5.0)
        - initial_stop_loss_pct: Initial stop loss percentage (default: 3.0)
        - trailing_stop_pct: Trailing stop percentage (default: 2.0)
        - ema_fast: Fast EMA period (default: 12)
        - ema_slow: Slow EMA period (default: 26)
        - adx_threshold: ADX threshold for strong trend (default: 25)
        - adx_weak_threshold: ADX threshold for weak trend (default: 20)
        - rsi_lower: RSI lower bound for momentum (default: 40)
        - rsi_upper: RSI upper bound for momentum (default: 60)
        - max_leverage: Maximum leverage (default: 5.0)
        - min_confidence: Minimum confidence for trade (default: 0.65)
        """
        super().__init__(name, config)
        
        self.timeframe = config.get('timeframe', '15m')
        self.profit_target_pct = config.get('profit_target_pct', 5.0)
        self.initial_stop_loss_pct = config.get('initial_stop_loss_pct', 3.0)
        self.trailing_stop_pct = config.get('trailing_stop_pct', 2.0)
        self.ema_fast = config.get('ema_fast', 12)
        self.ema_slow = config.get('ema_slow', 26)
        self.adx_threshold = config.get('adx_threshold', 25)
        self.adx_weak_threshold = config.get('adx_weak_threshold', 20)
        self.rsi_lower = config.get('rsi_lower', 40)
        self.rsi_upper = config.get('rsi_upper', 60)
        self.max_leverage = config.get('max_leverage', 5.0)
        self.min_confidence = config.get('min_confidence', 0.5)
        
        self.current_position: Optional[Dict] = None
        self.highest_price_since_entry = 0.0
        self.lowest_price_since_entry = float('inf')
        
        logger.info(f"MomentumStrategy '{name}' initialized with timeframe={self.timeframe}")
    
    def initialize(self) -> None:
        """Initialize strategy"""
        self.is_initialized = True
        logger.info(f"MomentumStrategy '{self.name}' initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Process new market data"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return {
            'timeframe': self.timeframe,
            'profit_target_pct': self.profit_target_pct,
            'initial_stop_loss_pct': self.initial_stop_loss_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
            'ema_fast': self.ema_fast,
            'ema_slow': self.ema_slow,
            'adx_threshold': self.adx_threshold,
            'adx_weak_threshold': self.adx_weak_threshold,
            'rsi_lower': self.rsi_lower,
            'rsi_upper': self.rsi_upper,
            'max_leverage': self.max_leverage,
            'min_confidence': self.min_confidence
        }
    
    def generate_signal(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> TradingSignal:
        """
        Generate momentum signal
        
        Args:
            market_data: Market data dict with symbol, price, timestamp, volume
            indicators: Technical indicators dict with EMA, ADX, RSI, MACD, etc.
        
        Returns:
            TradingSignal with momentum decision
        """
        symbol = market_data['symbol']
        current_price = market_data['price']
        timestamp = market_data.get('timestamp', datetime.now())
        
        signals = self._analyze_momentum_signals(market_data, indicators)
        
        signal_strength = sum(signals.values()) / len(signals)
        
        if signal_strength >= self.min_confidence:
            action = SignalAction.BUY
            confidence = min(1.0, abs(signal_strength))
        elif signal_strength <= -self.min_confidence:
            action = SignalAction.SELL
            confidence = min(1.0, abs(signal_strength))
        else:
            action = SignalAction.HOLD
            confidence = 0.5
        
        if action != SignalAction.HOLD:
            stop_loss = self._calculate_stop_loss(current_price, action)
            take_profit = self._calculate_take_profit(current_price, action)
            position_size = self._calculate_position_size(confidence)
            leverage = self._calculate_leverage(confidence, indicators)
        else:
            stop_loss = None
            take_profit = None
            position_size = 0.0
            leverage = 1.0
        
        signal = TradingSignal(
            action=action,
            confidence=confidence,
            symbol=symbol,
            timestamp=timestamp,
            price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            metadata={
                'strategy': 'momentum',
                'timeframe': self.timeframe,
                'leverage': leverage,
                'signals': signals,
                'signal_strength': signal_strength,
                'trailing_stop': self.trailing_stop_pct
            }
        )
        
        logger.info(
            f"Momentum signal: {action.value} with confidence {confidence:.2f}, "
            f"leverage {leverage:.1f}x, signals={signals}"
        )
        
        return signal
    
    def _analyze_momentum_signals(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Analyze multiple momentum signals
        
        Returns:
            Dict of signal names to strengths (-1 to 1)
        """
        signals = {}
        
        signals['ema_crossover'] = self._check_ema_crossover(indicators)
        
        signals['adx_strength'] = self._check_adx_strength(indicators)
        
        signals['rsi_momentum'] = self._check_rsi_momentum(indicators)
        
        signals['macd_histogram'] = self._check_macd_histogram(indicators)
        
        signals['volume_trend'] = self._check_volume_trend(market_data, indicators)
        
        return signals
    
    def _check_ema_crossover(self, indicators: Dict[str, Any]) -> float:
        """Check EMA crossover signal"""
        ema_fast = indicators.get(f'ema_{self.ema_fast}', 0)
        ema_slow = indicators.get(f'ema_{self.ema_slow}', 0)
        ema_fast_prev = indicators.get(f'ema_{self.ema_fast}_prev', ema_fast)
        ema_slow_prev = indicators.get(f'ema_{self.ema_slow}_prev', ema_slow)
        
        if ema_slow == 0 or ema_slow_prev == 0:
            return 0.0
        
        current_diff = (ema_fast - ema_slow) / ema_slow
        previous_diff = (ema_fast_prev - ema_slow_prev) / ema_slow_prev
        
        if current_diff > 0 and previous_diff <= 0:
            return 1.0
        elif current_diff < 0 and previous_diff >= 0:
            return -1.0
        elif current_diff > 0:
            return min(0.8, current_diff * 20)  # Scale to 0-0.8
        elif current_diff < 0:
            return max(-0.8, current_diff * 20)  # Scale to -0.8-0
        
        return 0.0
    
    def _check_adx_strength(self, indicators: Dict[str, Any]) -> float:
        """Check ADX trend strength signal"""
        adx = indicators.get('adx', 0)
        plus_di = indicators.get('plus_di', 0)
        minus_di = indicators.get('minus_di', 0)
        
        if adx < self.adx_weak_threshold:
            return 0.0
        
        if plus_di == 0 and minus_di == 0:
            return 0.0
        
        if adx > self.adx_threshold:
            if plus_di > minus_di:
                strength = min(1.0, (adx - self.adx_threshold) / 30)
                return strength
            else:
                strength = min(1.0, (adx - self.adx_threshold) / 30)
                return -strength
        
        return 0.0
    
    def _check_rsi_momentum(self, indicators: Dict[str, Any]) -> float:
        """Check RSI momentum signal"""
        rsi = indicators.get('rsi', 50)
        
        if self.rsi_lower < rsi < self.rsi_upper:
            if rsi > 50:
                return (rsi - 50) / 50  # Scale to 0-0.2
            else:
                return (rsi - 50) / 50  # Scale to -0.2-0
        elif rsi > 70:
            return -0.3  # Weak bearish signal
        elif rsi < 30:
            return 0.3  # Weak bullish signal
        
        return 0.0
    
    def _check_macd_histogram(self, indicators: Dict[str, Any]) -> float:
        """Check MACD histogram signal"""
        macd_histogram = indicators.get('macd_histogram', 0)
        macd_histogram_prev = indicators.get('macd_histogram_prev', macd_histogram)
        
        if macd_histogram > 0 and macd_histogram > macd_histogram_prev:
            return min(0.8, macd_histogram * 10)
        elif macd_histogram < 0 and macd_histogram < macd_histogram_prev:
            return max(-0.8, macd_histogram * 10)
        
        return 0.0
    
    def _check_volume_trend(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> float:
        """Check volume trend signal"""
        current_volume = market_data.get('volume', 0)
        avg_volume = indicators.get('volume_avg', 0)
        volume_trend = indicators.get('volume_trend', 0)  # Positive = increasing
        
        if avg_volume == 0:
            return 0.0
        
        volume_ratio = current_volume / avg_volume
        
        if volume_ratio > 1.2 and volume_trend > 0:
            price_change = indicators.get('price_change_pct', 0)
            if price_change > 0:
                return 0.6
            elif price_change < 0:
                return -0.6
        
        return 0.0
    
    def _calculate_stop_loss(self, current_price: float, action: SignalAction) -> float:
        """Calculate initial stop loss price"""
        if action == SignalAction.BUY:
            return current_price * (1 - self.initial_stop_loss_pct / 100)
        else:  # SELL
            return current_price * (1 + self.initial_stop_loss_pct / 100)
    
    def _calculate_take_profit(self, current_price: float, action: SignalAction) -> float:
        """Calculate take profit price"""
        if action == SignalAction.BUY:
            return current_price * (1 + self.profit_target_pct / 100)
        else:  # SELL
            return current_price * (1 - self.profit_target_pct / 100)
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Calculate position size based on confidence"""
        base_size = 0.15
        confidence_multiplier = 0.5 + (confidence * 0.5)  # 0.5-1.0
        return base_size * confidence_multiplier
    
    def _calculate_leverage(self, confidence: float, indicators: Dict[str, Any]) -> float:
        """Calculate dynamic leverage"""
        base_leverage = 3.0
        
        confidence_multiplier = 0.5 + confidence
        
        atr = indicators.get('atr', 0)
        current_price = indicators.get('price', 1)
        volatility_pct = (atr / current_price) * 100 if current_price > 0 else 0
        
        if volatility_pct > 3.0:
            volatility_adjustment = 0.6
        elif volatility_pct > 2.0:
            volatility_adjustment = 0.8
        else:
            volatility_adjustment = 1.0
        
        leverage = base_leverage * confidence_multiplier * volatility_adjustment
        
        return min(leverage, self.max_leverage)
    
    def calculate_trailing_stop(
        self,
        current_price: float,
        entry_price: float,
        position_side: str
    ) -> float:
        """
        Calculate trailing stop loss
        
        Args:
            current_price: Current market price
            entry_price: Entry price of position
            position_side: 'long' or 'short'
        
        Returns:
            Trailing stop loss price
        """
        if position_side == 'long':
            self.highest_price_since_entry = max(self.highest_price_since_entry, current_price)
            
            trailing_stop = self.highest_price_since_entry * (1 - self.trailing_stop_pct / 100)
            
            initial_stop = entry_price * (1 - self.initial_stop_loss_pct / 100)
            return max(trailing_stop, initial_stop)
        
        else:  # short
            self.lowest_price_since_entry = min(self.lowest_price_since_entry, current_price)
            
            trailing_stop = self.lowest_price_since_entry * (1 + self.trailing_stop_pct / 100)
            
            initial_stop = entry_price * (1 + self.initial_stop_loss_pct / 100)
            return min(trailing_stop, initial_stop)
    
    def reset_trailing_stop(self):
        """Reset trailing stop tracking"""
        self.highest_price_since_entry = 0.0
        self.lowest_price_since_entry = float('inf')
