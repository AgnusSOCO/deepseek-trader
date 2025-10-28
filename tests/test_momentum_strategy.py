"""
Unit tests for Momentum Strategy
"""

import pytest
from datetime import datetime
from src.strategies.momentum import MomentumStrategy
from src.strategies.base_strategy import SignalAction


class TestMomentumStrategy:
    """Test suite for MomentumStrategy"""
    
    @pytest.fixture
    def strategy(self):
        """Create momentum strategy instance"""
        config = {
            'timeframe': '15m',
            'profit_target_pct': 5.0,
            'initial_stop_loss_pct': 3.0,
            'trailing_stop_pct': 2.0,
            'max_leverage': 5.0,
            'min_confidence': 0.65
        }
        return MomentumStrategy('test_momentum', config)
    
    @pytest.fixture
    def market_data(self):
        """Create sample market data"""
        return {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'timestamp': datetime.now(),
            'volume': 1000.0
        }
    
    @pytest.fixture
    def indicators(self):
        """Create sample indicators"""
        return {
            'ema_12': 49500.0,
            'ema_26': 49000.0,
            'adx': 30.0,
            'rsi': 55.0,
            'macd': 100.0,
            'macd_signal': 80.0,
            'macd_histogram': 20.0,
            'volume_avg': 800.0,
            'atr': 500.0,
            'price': 50000.0
        }
    
    def test_initialization(self, strategy):
        """Test strategy initialization"""
        assert strategy.name == 'test_momentum'
        assert strategy.timeframe == '15m'
        assert strategy.profit_target_pct == 5.0
        assert strategy.initial_stop_loss_pct == 3.0
        assert strategy.trailing_stop_pct == 2.0
        assert strategy.max_leverage == 5.0
        assert strategy.min_confidence == 0.65
    
    def test_generate_signal(self, strategy, market_data, indicators):
        """Test signal generation"""
        signal = strategy.generate_signal(market_data, indicators)
        
        assert signal.symbol == 'BTC/USDT'
        assert signal.price == 50000.0
        assert signal.action in [SignalAction.BUY, SignalAction.SELL, SignalAction.HOLD]
    
    def test_ema_crossover_bullish(self, strategy, indicators):
        """Test EMA crossover detection - bullish"""
        indicators['ema_12'] = 50000.0
        indicators['ema_26'] = 49500.0
        
        signal = strategy._check_ema_crossover(indicators)
        assert signal > 0.0  # Bullish signal
    
    def test_ema_crossover_bearish(self, strategy, indicators):
        """Test EMA crossover detection - bearish"""
        indicators['ema_12'] = 49000.0
        indicators['ema_26'] = 49500.0
        
        signal = strategy._check_ema_crossover(indicators)
        assert signal < 0.0  # Bearish signal
    
    def test_adx_strength_strong_trend(self, strategy, indicators):
        """Test ADX strength - strong trend"""
        indicators['adx'] = 35.0  # Strong trend
        indicators['ema_12'] = 50000.0
        indicators['ema_26'] = 49500.0
        
        signal = strategy._check_adx_strength(indicators)
        assert signal > 0.0  # Strong trend signal
    
    def test_adx_strength_weak_trend(self, strategy, indicators):
        """Test ADX strength - weak trend"""
        indicators['adx'] = 15.0  # Weak trend
        indicators['ema_12'] = 50000.0
        indicators['ema_26'] = 49500.0
        
        signal = strategy._check_adx_strength(indicators)
        assert signal == 0.0  # No signal (weak trend)
    
    def test_rsi_momentum_bullish(self, strategy, indicators):
        """Test RSI momentum - bullish"""
        indicators['rsi'] = 55.0  # In bullish range (40-60)
        
        signal = strategy._check_rsi_momentum(indicators)
        assert signal > 0.0  # Bullish signal
    
    def test_rsi_momentum_bearish(self, strategy, indicators):
        """Test RSI momentum - bearish"""
        indicators['rsi'] = 45.0  # In bearish range (40-60)
        
        signal = strategy._check_rsi_momentum(indicators)
        assert signal < 0.0  # Bearish signal
    
    def test_rsi_momentum_overbought(self, strategy, indicators):
        """Test RSI momentum - overbought"""
        indicators['rsi'] = 75.0  # Overbought
        
        signal = strategy._check_rsi_momentum(indicators)
        assert signal == 0.0  # No signal (overbought)
    
    def test_rsi_momentum_oversold(self, strategy, indicators):
        """Test RSI momentum - oversold"""
        indicators['rsi'] = 25.0  # Oversold
        
        signal = strategy._check_rsi_momentum(indicators)
        assert signal == 0.0  # No signal (oversold)
    
    def test_macd_histogram_expanding_bullish(self, strategy, indicators):
        """Test MACD histogram - expanding bullish"""
        indicators['macd'] = 100.0
        indicators['macd_signal'] = 80.0
        indicators['macd_histogram'] = 20.0  # Positive and expanding
        
        signal = strategy._check_macd_histogram(indicators)
        assert signal > 0.0  # Bullish signal
    
    def test_macd_histogram_expanding_bearish(self, strategy, indicators):
        """Test MACD histogram - expanding bearish"""
        indicators['macd'] = 80.0
        indicators['macd_signal'] = 100.0
        indicators['macd_histogram'] = -20.0  # Negative and expanding
        
        signal = strategy._check_macd_histogram(indicators)
        assert signal < 0.0  # Bearish signal
    
    def test_volume_trend_increasing(self, strategy, market_data, indicators):
        """Test volume trend - increasing"""
        market_data['volume'] = 1200.0
        indicators['volume_avg'] = 800.0
        
        signal = strategy._check_volume_trend(market_data, indicators)
        assert signal > 0.0  # Positive signal (volume confirms trend)
    
    def test_volume_trend_decreasing(self, strategy, market_data, indicators):
        """Test volume trend - decreasing"""
        market_data['volume'] = 600.0
        indicators['volume_avg'] = 800.0
        
        signal = strategy._check_volume_trend(market_data, indicators)
        assert signal < 0.0  # Negative signal (volume doesn't confirm)
    
    def test_calculate_leverage_high_confidence(self, strategy, indicators):
        """Test leverage calculation - high confidence"""
        confidence = 0.9
        indicators['atr'] = 300.0
        indicators['price'] = 50000.0
        
        leverage = strategy._calculate_leverage(confidence, indicators)
        
        assert leverage >= 1.0
        assert leverage <= strategy.max_leverage
    
    def test_calculate_leverage_low_confidence(self, strategy, indicators):
        """Test leverage calculation - low confidence"""
        confidence = 0.5
        indicators['atr'] = 300.0
        indicators['price'] = 50000.0
        
        leverage = strategy._calculate_leverage(confidence, indicators)
        
        assert leverage >= 1.0
        assert leverage <= strategy.max_leverage
    
    def test_calculate_leverage_high_volatility(self, strategy, indicators):
        """Test leverage calculation - high volatility"""
        confidence = 0.8
        indicators['atr'] = 2000.0  # High volatility
        indicators['price'] = 50000.0
        
        leverage = strategy._calculate_leverage(confidence, indicators)
        
        assert leverage >= 1.0
        assert leverage <= strategy.max_leverage
    
    def test_trailing_stop_long_position(self, strategy):
        """Test trailing stop calculation - long position"""
        strategy.current_position = {'side': 'long', 'entry_price': 50000.0}
        strategy.highest_price_since_entry = 52000.0
        
        current_price = 51500.0
        trailing_stop = strategy.calculate_trailing_stop(current_price)
        
        expected = 52000.0 * (1 - 0.02)
        assert abs(trailing_stop - expected) < 0.01
    
    def test_trailing_stop_short_position(self, strategy):
        """Test trailing stop calculation - short position"""
        strategy.current_position = {'side': 'short', 'entry_price': 50000.0}
        strategy.lowest_price_since_entry = 48000.0
        
        current_price = 48500.0
        trailing_stop = strategy.calculate_trailing_stop(current_price)
        
        expected = 48000.0 * (1 + 0.02)
        assert abs(trailing_stop - expected) < 0.01
    
    def test_trailing_stop_no_position(self, strategy):
        """Test trailing stop calculation - no position"""
        strategy.current_position = None
        
        trailing_stop = strategy.calculate_trailing_stop(50000.0)
        
        assert trailing_stop is None
    
    def test_reset_trailing_stop(self, strategy):
        """Test trailing stop reset"""
        strategy.highest_price_since_entry = 52000.0
        strategy.lowest_price_since_entry = 48000.0
        
        strategy.reset_trailing_stop()
        
        assert strategy.highest_price_since_entry == 0.0
        assert strategy.lowest_price_since_entry == float('inf')
    
    def test_stop_loss_calculation_buy(self, strategy):
        """Test stop loss calculation for BUY"""
        current_price = 50000.0
        stop_loss = strategy._calculate_stop_loss(current_price, SignalAction.BUY)
        
        expected = 50000.0 * (1 - 3.0 / 100)  # 3% below
        assert abs(stop_loss - expected) < 0.01
    
    def test_stop_loss_calculation_sell(self, strategy):
        """Test stop loss calculation for SELL"""
        current_price = 50000.0
        stop_loss = strategy._calculate_stop_loss(current_price, SignalAction.SELL)
        
        expected = 50000.0 * (1 + 3.0 / 100)  # 3% above
        assert abs(stop_loss - expected) < 0.01
    
    def test_take_profit_calculation_buy(self, strategy):
        """Test take profit calculation for BUY"""
        current_price = 50000.0
        take_profit = strategy._calculate_take_profit(current_price, SignalAction.BUY)
        
        expected = 50000.0 * (1 + 5.0 / 100)  # 5% above
        assert abs(take_profit - expected) < 0.01
    
    def test_take_profit_calculation_sell(self, strategy):
        """Test take profit calculation for SELL"""
        current_price = 50000.0
        take_profit = strategy._calculate_take_profit(current_price, SignalAction.SELL)
        
        expected = 50000.0 * (1 - 5.0 / 100)  # 5% below
        assert abs(take_profit - expected) < 0.01
    
    def test_position_size_calculation(self, strategy):
        """Test position size calculation"""
        confidence = 0.8
        position_size = strategy._calculate_position_size(confidence)
        
        assert position_size > 0.0
        assert position_size <= 0.25  # Max 25% of portfolio
    
    def test_signal_aggregation(self, strategy, market_data, indicators):
        """Test signal aggregation from multiple sources"""
        signals = strategy._analyze_momentum_signals(market_data, indicators)
        
        assert isinstance(signals, dict)
        assert 'ema_crossover' in signals
        assert 'adx_strength' in signals
        assert 'rsi_momentum' in signals
        assert 'macd_histogram' in signals
        assert 'volume_trend' in signals
        
        for signal_value in signals.values():
            assert isinstance(signal_value, float)
    
    def test_weak_trend_hold(self, strategy, market_data, indicators):
        """Test HOLD signal when trend is weak"""
        indicators['adx'] = 15.0  # Weak trend
        
        signal = strategy.generate_signal(market_data, indicators)
        
        assert signal.action == SignalAction.HOLD
        assert 'weak trend' in signal.metadata.get('reason', '').lower()
