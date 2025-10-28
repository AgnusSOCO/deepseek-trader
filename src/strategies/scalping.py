"""
Scalping Strategy

High-frequency trading strategy for short-term profits.
Targets 0.1-0.5% gains with tight stop-losses.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from .base_strategy import BaseStrategy, TradingSignal, SignalAction

logger = logging.getLogger(__name__)


class ScalpingStrategy(BaseStrategy):
    """
    Scalping strategy for short-term trading
    
    Characteristics:
    - Timeframe: 1-5 minute candles
    - Trade duration: 30 seconds to 10 minutes
    - Profit target: 0.1-0.5% per trade
    - Leverage: 2x-5x
    - Trade frequency: 10-50 trades per day
    
    Entry Signals:
    - Order book imbalances (>60% bid or ask)
    - Rapid volume increases (>2x average)
    - Breakouts from tight ranges
    - VWAP deviation (>0.2%)
    - Bollinger Band squeeze breakouts
    
    Exit Signals:
    - Profit target reached (0.3-0.5%)
    - Stop-loss hit (0.3-0.5%)
    - Time-based exit (10 minutes max)
    - Reversal signals
    """
    
    def __init__(self, name: str, config: Dict[str, Any]):
        """
        Initialize scalping strategy
        
        Config parameters:
        - timeframe: Trading timeframe (default: '1m')
        - profit_target_pct: Profit target percentage (default: 0.3)
        - stop_loss_pct: Stop loss percentage (default: 0.4)
        - max_trade_duration_minutes: Maximum trade duration (default: 10)
        - min_volume_multiplier: Minimum volume increase (default: 2.0)
        - order_book_imbalance_threshold: Order book imbalance threshold (default: 0.6)
        - vwap_deviation_threshold: VWAP deviation threshold (default: 0.002)
        - bb_squeeze_threshold: Bollinger Band width threshold (default: 0.01)
        - max_leverage: Maximum leverage (default: 5.0)
        - daily_loss_limit_pct: Daily loss limit (default: 2.0)
        - min_confidence: Minimum confidence for trade (default: 0.7)
        """
        super().__init__(name, config)
        
        self.timeframe = config.get('timeframe', '1m')
        self.profit_target_pct = config.get('profit_target_pct', 0.3)
        self.stop_loss_pct = config.get('stop_loss_pct', 0.4)
        self.max_trade_duration_minutes = config.get('max_trade_duration_minutes', 10)
        self.min_volume_multiplier = config.get('min_volume_multiplier', 2.0)
        self.order_book_imbalance_threshold = config.get('order_book_imbalance_threshold', 0.6)
        self.vwap_deviation_threshold = config.get('vwap_deviation_threshold', 0.002)
        self.bb_squeeze_threshold = config.get('bb_squeeze_threshold', 0.01)
        self.max_leverage = config.get('max_leverage', 5.0)
        self.daily_loss_limit_pct = config.get('daily_loss_limit_pct', 2.0)
        self.min_confidence = config.get('min_confidence', 0.85)
        
        self.last_trade_time: Optional[datetime] = None
        self.daily_pnl = 0.0
        self.trades_today = 0
        
        logger.info(f"ScalpingStrategy '{name}' initialized with timeframe={self.timeframe}")
    
    def initialize(self) -> None:
        """Initialize strategy"""
        self.is_initialized = True
        logger.info(f"ScalpingStrategy '{self.name}' initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """Process new market data"""
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get strategy parameters"""
        return {
            'timeframe': self.timeframe,
            'profit_target_pct': self.profit_target_pct,
            'stop_loss_pct': self.stop_loss_pct,
            'max_trade_duration_minutes': self.max_trade_duration_minutes,
            'min_volume_multiplier': self.min_volume_multiplier,
            'order_book_imbalance_threshold': self.order_book_imbalance_threshold,
            'vwap_deviation_threshold': self.vwap_deviation_threshold,
            'bb_squeeze_threshold': self.bb_squeeze_threshold,
            'max_leverage': self.max_leverage,
            'daily_loss_limit_pct': self.daily_loss_limit_pct,
            'min_confidence': self.min_confidence
        }
    
    def generate_signal(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> TradingSignal:
        """
        Generate scalping signal
        
        Args:
            market_data: Market data dict with symbol, price, timestamp, order_book, volume
            indicators: Technical indicators dict with VWAP, BB, volume_avg, etc.
        
        Returns:
            TradingSignal with scalping decision
        """
        symbol = market_data['symbol']
        current_price = market_data['price']
        timestamp = market_data.get('timestamp', datetime.now())
        
        if self.daily_pnl < -self.daily_loss_limit_pct:
            logger.warning(f"Daily loss limit reached: {self.daily_pnl:.2f}%")
            return self._hold_signal(symbol, current_price, timestamp, "Daily loss limit reached")
        
        signals = self._analyze_scalping_signals(market_data, indicators)
        
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
                'strategy': 'scalping',
                'timeframe': self.timeframe,
                'leverage': leverage,
                'signals': signals,
                'signal_strength': signal_strength,
                'daily_pnl': self.daily_pnl,
                'trades_today': self.trades_today
            }
        )
        
        logger.info(
            f"Scalping signal: {action.value} with confidence {confidence:.2f}, "
            f"leverage {leverage:.1f}x, signals={signals}"
        )
        
        return signal
    
    def _analyze_scalping_signals(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Analyze multiple scalping signals
        
        Returns:
            Dict of signal names to strengths (-1 to 1)
        """
        signals = {}
        
        order_book_signal = self._check_order_book_imbalance(market_data)
        if order_book_signal != 0.0:
            signals['order_book_imbalance'] = order_book_signal
        
        signals['volume_surge'] = self._check_volume_surge(market_data, indicators)
        
        signals['vwap_deviation'] = self._check_vwap_deviation(market_data, indicators)
        
        signals['bb_breakout'] = self._check_bb_breakout(market_data, indicators)
        
        signals['price_momentum'] = self._check_price_momentum(indicators)
        
        return signals
    
    def _check_order_book_imbalance(self, market_data: Dict[str, Any]) -> float:
        """Check order book imbalance signal"""
        if 'bid_volume' in market_data and 'ask_volume' in market_data:
            bid_volume = market_data.get('bid_volume', 0)
            ask_volume = market_data.get('ask_volume', 0)
        else:
            order_book = market_data.get('order_book', {})
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            if not bids or not asks:
                return 0.0
            
            bid_volume = sum(bid.get('size', 0) for bid in bids[:10])
            ask_volume = sum(ask.get('size', 0) for ask in asks[:10])
        
        total_volume = bid_volume + ask_volume
        
        if total_volume == 0:
            return 0.0
        
        bid_ratio = bid_volume / total_volume
        
        if bid_ratio > self.order_book_imbalance_threshold:
            strength = (bid_ratio - self.order_book_imbalance_threshold) / (1.0 - self.order_book_imbalance_threshold)
            return min(1.0, strength)
        elif bid_ratio < (1 - self.order_book_imbalance_threshold):
            strength = (self.order_book_imbalance_threshold - bid_ratio) / self.order_book_imbalance_threshold
            return -min(1.0, strength)
        
        return 0.0
    
    def _check_volume_surge(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> float:
        """Check volume surge signal"""
        current_volume = market_data.get('volume', 0)
        avg_volume = indicators.get('volume_avg', 0)
        
        if avg_volume == 0:
            return 0.0
        
        volume_ratio = current_volume / avg_volume
        
        if volume_ratio > self.min_volume_multiplier:
            price_change = indicators.get('price_change_pct', 0)
            if price_change > 0:
                return min(1.0, (volume_ratio - 1) / 3)  # Scale to 0-1
            elif price_change < 0:
                return max(-1.0, -(volume_ratio - 1) / 3)  # Scale to -1-0
        
        return 0.0
    
    def _check_vwap_deviation(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> float:
        """Check VWAP deviation signal"""
        current_price = market_data['price']
        vwap = indicators.get('vwap', current_price)
        
        if vwap == 0:
            return 0.0
        
        deviation = (current_price - vwap) / vwap
        
        if abs(deviation) > self.vwap_deviation_threshold:
            return max(-1.0, min(1.0, -deviation * 10))
        
        return 0.0
    
    def _check_bb_breakout(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> float:
        """Check Bollinger Band breakout signal"""
        current_price = market_data['price']
        bb_upper = indicators.get('bb_upper', 0)
        bb_lower = indicators.get('bb_lower', 0)
        bb_middle = indicators.get('bb_middle', current_price)
        bb_width = indicators.get('bb_width', 0)
        
        if bb_upper == 0 or bb_lower == 0:
            return 0.0
        
        if bb_width < self.bb_squeeze_threshold:
            if current_price > bb_upper:
                return 0.8  # Strong buy on upward breakout
            elif current_price < bb_lower:
                return -0.8  # Strong sell on downward breakout
        
        return 0.0
    
    def _check_price_momentum(self, indicators: Dict[str, Any]) -> float:
        """Check price momentum signal"""
        roc = indicators.get('roc', 0)
        
        if roc > 2.0:
            return min(1.0, roc / 10)
        elif roc < -2.0:
            return max(-1.0, roc / 10)
        
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
        base_size = 0.10
        confidence_multiplier = 0.5 + (confidence * 0.5)  # 0.5-1.0
        return base_size * confidence_multiplier
    
    def _calculate_leverage(self, confidence: float, indicators: Dict[str, Any]) -> float:
        """Calculate dynamic leverage"""
        base_leverage = 3.0
        
        confidence_multiplier = 0.5 + confidence
        
        atr = indicators.get('atr', 0)
        current_price = indicators.get('price', 1)
        volatility_pct = (atr / current_price) * 100 if current_price > 0 else 0
        
        if volatility_pct > 2.0:
            volatility_adjustment = 0.5
        elif volatility_pct > 1.0:
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
                'strategy': 'scalping',
                'reason': reason
            }
        )
    
    def update_trade_result(self, pnl_pct: float):
        """Update strategy state after trade"""
        self.last_trade_time = datetime.now()
        self.daily_pnl += pnl_pct
        self.trades_today += 1
        
        logger.info(f"Trade result: PnL={pnl_pct:.2f}%, Daily PnL={self.daily_pnl:.2f}%, Trades={self.trades_today}")
    
    def reset_daily_stats(self):
        """Reset daily statistics"""
        self.daily_pnl = 0.0
        self.trades_today = 0
        logger.info("Daily stats reset")
