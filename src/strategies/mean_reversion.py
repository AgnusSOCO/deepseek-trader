"""
Mean Reversion Strategy

Counter-trend strategy that profits from price returning to average.
Targets 0.5-3% gains with quick exits if reversal fails.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class MeanReversionStrategy(BaseStrategy):
    """
    Mean reversion strategy for range-bound markets
    
    Characteristics:
    - Timeframe: 5-minute to 1-hour candles
    - Trade duration: 30 minutes to several hours
    - Profit target: 0.5-3% per trade
    - Leverage: 1x-3x
    - Trade frequency: 5-20 trades per week
    
    Entry Signals:
    - Price at Bollinger Band extremes
    - RSI overbought (>70) or oversold (<30)
    - Z-score > 2 or < -2
    - Price deviation from moving average
    
    Exit Signals:
    - Price returns to mean
    - Profit target reached
    - Stop-loss hit (quick exit if reversal fails)
    - Strong trend emerges (avoid counter-trend)
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize mean reversion strategy
        
        Config parameters:
        - timeframe: Trading timeframe (default: '5m')
        - profit_target_pct: Profit target percentage (default: 1.5)
        - stop_loss_pct: Stop loss percentage (default: 2.0)
        - max_hold_minutes: Maximum hold time (default: 240)
        - bb_std_dev: Bollinger Band standard deviations (default: 2.0)
        - rsi_overbought: RSI overbought threshold (default: 70)
        - rsi_oversold: RSI oversold threshold (default: 30)
        - zscore_threshold: Z-score threshold (default: 2.0)
        - adx_max: Maximum ADX for mean reversion (default: 25)
        - max_leverage: Maximum leverage (default: 3.0)
        - min_confidence: Minimum confidence for trade (default: 0.65)
        """
        super().__init__(name, config)
        
        self.timeframe = config.get('timeframe', '5m')
        self.profit_target_pct = config.get('profit_target_pct', 1.5)
        self.stop_loss_pct = config.get('stop_loss_pct', 2.0)
        self.max_hold_minutes = config.get('max_hold_minutes', 240)
        self.bb_std_dev = config.get('bb_std_dev', 2.0)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.zscore_threshold = config.get('zscore_threshold', 2.0)
        self.adx_max = config.get('adx_max', 25)
        self.max_leverage = config.get('max_leverage', 3.0)
        self.min_confidence = config.get('min_confidence', 0.65)
        
        self.entry_time: Optional[datetime] = None
        
        logger.info(f"MeanReversionStrategy '{name}' initialized with timeframe={self.timeframe}")
    
    def initialize(self) -> None:
        """Initialize strategy"""
        self.is_initialized = True
        logger.info(f"MeanReversionStrategy '{self.name}' initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Process new market data"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return {
            'timeframe': self.timeframe,
            'profit_target_pct': self.profit_target_pct,
            'stop_loss_pct': self.stop_loss_pct,
            'max_hold_minutes': self.max_hold_minutes,
            'bb_std_dev': self.bb_std_dev,
            'rsi_overbought': self.rsi_overbought,
            'rsi_oversold': self.rsi_oversold,
            'zscore_threshold': self.zscore_threshold,
            'adx_max': self.adx_max,
            'max_leverage': self.max_leverage,
            'min_confidence': self.min_confidence
        }
    
    def generate_signal(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> TradingSignal:
        """
        Generate mean reversion signal
        
        Args:
            market_data: Market data dict with symbol, price, timestamp
            indicators: Technical indicators dict with BB, RSI, SMA, ADX, etc.
        
        Returns:
            TradingSignal with mean reversion decision
        """
        symbol = market_data['symbol']
        current_price = market_data['price']
        timestamp = market_data.get('timestamp', datetime.now())
        
        adx = indicators.get('adx', 0)
        if adx > self.adx_max:
            logger.info(f"Strong trend detected (ADX={adx:.1f}), skipping mean reversion")
            return self._hold_signal(symbol, current_price, timestamp, "Strong trend - avoid counter-trend")
        
        signals = self._analyze_mean_reversion_signals(market_data, indicators)
        
        signal_strength = sum(signals.values()) / len(signals)
        
        if signal_strength >= self.min_confidence:
            action = SignalAction.BUY
            confidence = signal_strength
        elif signal_strength <= -self.min_confidence:
            action = SignalAction.SELL
            confidence = abs(signal_strength)
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
                'strategy': 'mean_reversion',
                'timeframe': self.timeframe,
                'leverage': leverage,
                'signals': signals,
                'signal_strength': signal_strength,
                'adx': adx
            }
        )
        
        logger.info(
            f"Mean reversion signal: {action.value} with confidence {confidence:.2f}, "
            f"leverage {leverage:.1f}x, signals={signals}"
        )
        
        return signal
    
    def _analyze_mean_reversion_signals(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Analyze multiple mean reversion signals
        
        Returns:
            Dict of signal names to strengths (-1 to 1)
        """
        signals = {}
        
        signals['bb_extreme'] = self._check_bb_extreme(market_data, indicators)
        
        signals['rsi_extreme'] = self._check_rsi_extreme(indicators)
        
        signals['zscore'] = self._check_zscore(market_data, indicators)
        
        signals['sma_deviation'] = self._check_sma_deviation(market_data, indicators)
        
        signals['volume_confirmation'] = self._check_volume_confirmation(market_data, indicators)
        
        return signals
    
    def _check_bb_extreme(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> float:
        """Check Bollinger Band extreme signal"""
        current_price = market_data['price']
        bb_upper = indicators.get('bb_upper', 0)
        bb_lower = indicators.get('bb_lower', 0)
        bb_middle = indicators.get('bb_middle', current_price)
        
        if bb_upper == 0 or bb_lower == 0:
            return 0.0
        
        bb_range = bb_upper - bb_lower
        if bb_range == 0:
            return 0.0
        
        position = (current_price - bb_lower) / bb_range
        
        if position > 0.95:
            return -0.9
        elif position < 0.05:
            return 0.9
        elif position > 0.8:
            return -0.6
        elif position < 0.2:
            return 0.6
        
        return 0.0
    
    def _check_rsi_extreme(self, indicators: Dict[str, Any]) -> float:
        """Check RSI extreme signal"""
        rsi = indicators.get('rsi', 50)
        
        if rsi > self.rsi_overbought:
            strength = min(1.0, (rsi - self.rsi_overbought) / 20)
            return -strength
        elif rsi < self.rsi_oversold:
            strength = min(1.0, (self.rsi_oversold - rsi) / 20)
            return strength
        
        return 0.0
    
    def _check_zscore(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> float:
        """Check Z-score deviation signal"""
        current_price = market_data['price']
        sma = indicators.get('sma_20', current_price)
        std_dev = indicators.get('std_dev', 0)
        
        if std_dev == 0 or sma == 0:
            return 0.0
        
        zscore = (current_price - sma) / std_dev
        
        if zscore > self.zscore_threshold:
            return -min(1.0, abs(zscore) / 3)
        elif zscore < -self.zscore_threshold:
            return min(1.0, abs(zscore) / 3)
        
        return 0.0
    
    def _check_sma_deviation(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> float:
        """Check SMA deviation signal"""
        current_price = market_data['price']
        sma_50 = indicators.get('sma_50', current_price)
        
        if sma_50 == 0:
            return 0.0
        
        deviation_pct = ((current_price - sma_50) / sma_50) * 100
        
        if deviation_pct > 3.0:
            return -min(0.8, deviation_pct / 5)
        elif deviation_pct < -3.0:
            return min(0.8, abs(deviation_pct) / 5)
        
        return 0.0
    
    def _check_volume_confirmation(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> float:
        """Check volume confirmation signal"""
        current_volume = market_data.get('volume', 0)
        avg_volume = indicators.get('volume_avg', 0)
        
        if avg_volume == 0:
            return 0.0
        
        volume_ratio = current_volume / avg_volume
        
        if volume_ratio < 0.8:
            return 0.5  # Weak move likely to reverse
        elif volume_ratio > 1.5:
            return -0.3  # Strong move may continue
        
        return 0.0
    
    def _calculate_stop_loss(self, current_price: float, action: SignalAction) -> float:
        """Calculate stop loss price"""
        if action == SignalAction.BUY:
            return current_price * (1 - self.stop_loss_pct / 100)
        else:  # SELL
            return current_price * (1 + self.stop_loss_pct / 100)
    
    def _calculate_take_profit(self, current_price: float, action: SignalAction) -> float:
        """Calculate take profit price"""
        if action == SignalAction.BUY:
            return current_price * (1 + self.profit_target_pct / 100)
        else:  # SELL
            return current_price * (1 - self.profit_target_pct / 100)
    
    def _calculate_position_size(self, confidence: float) -> float:
        """Calculate position size based on confidence"""
        base_size = 0.12
        confidence_multiplier = 0.5 + (confidence * 0.5)  # 0.5-1.0
        return base_size * confidence_multiplier
    
    def _calculate_leverage(self, confidence: float, indicators: Dict[str, Any]) -> float:
        """Calculate dynamic leverage"""
        base_leverage = 2.0
        
        confidence_multiplier = 0.5 + confidence
        
        atr = indicators.get('atr', 0)
        current_price = indicators.get('price', 1)
        volatility_pct = (atr / current_price) * 100 if current_price > 0 else 0
        
        if volatility_pct > 2.5:
            volatility_adjustment = 0.5
        elif volatility_pct > 1.5:
            volatility_adjustment = 0.75
        else:
            volatility_adjustment = 1.0
        
        leverage = base_leverage * confidence_multiplier * volatility_adjustment
        
        return min(leverage, self.max_leverage)
    
    def _hold_signal(
        self,
        symbol: str,
        current_price: float,
        timestamp: datetime,
        reason: str
    ) -> TradingSignal:
        """Generate HOLD signal"""
        return TradingSignal(
            action=SignalAction.HOLD,
            confidence=0.5,
            symbol=symbol,
            timestamp=timestamp,
            price=current_price,
            metadata={
                'strategy': 'mean_reversion',
                'reason': reason
            }
        )
    
    def should_exit_early(
        self,
        current_price: float,
        entry_price: float,
        position_side: str,
        indicators: Dict[str, Any]
    ) -> bool:
        """
        Check if position should be exited early
        
        Args:
            current_price: Current market price
            entry_price: Entry price of position
            position_side: 'long' or 'short'
            indicators: Current technical indicators
        
        Returns:
            True if should exit early
        """
        adx = indicators.get('adx', 0)
        if adx > self.adx_max:
            logger.info(f"Strong trend emerged (ADX={adx:.1f}), exiting mean reversion position")
            return True
        
        if self.entry_time:
            hold_duration = (datetime.now() - self.entry_time).total_seconds() / 60
            if hold_duration > self.max_hold_minutes:
                logger.info(f"Max hold time reached ({hold_duration:.0f} minutes), exiting position")
                return True
        
        if position_side == 'long':
            loss_pct = ((current_price - entry_price) / entry_price) * 100
            if loss_pct < -self.stop_loss_pct * 0.5:
                logger.info(f"Price moving against position (loss={loss_pct:.2f}%), considering early exit")
                return True
        else:  # short
            loss_pct = ((entry_price - current_price) / entry_price) * 100
            if loss_pct < -self.stop_loss_pct * 0.5:
                logger.info(f"Price moving against position (loss={loss_pct:.2f}%), considering early exit")
                return True
        
        return False
