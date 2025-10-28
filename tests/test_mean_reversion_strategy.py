"""
Unit tests for Mean Reversion Strategy
"""

import pytest
from datetime import datetime
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.base_strategy import SignalAction


class TestMeanReversionStrategy:
    """Test suite for MeanReversionStrategy"""
    
    @pytest.fixture
    def strategy(self):
        """Create mean reversion strategy instance"""
        config = {
            'timeframe': '5m',
            'profit_target_pct': 1.5,
            'stop_loss_pct': 2.0,
            'max_leverage': 3.0,
            'min_confidence': 0.65
        }
        return MeanReversionStrategy('test_mean_reversion', config)
    
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
            'rsi': 50.0,
            'bb_upper': 51000.0,
            'bb_lower': 49000.0,
            'bb_middle': 50000.0,
            'sma_20': 50000.0,
            'sma_50': 50000.0,
            'std_dev': 500.0,
            'adx': 20.0,
            'atr': 500.0,
            'price': 50000.0,
            'volume_avg': 800.0
        }
    
    def test_initialization(self, strategy):
        """Test strategy initialization"""
        assert strategy.name == 'test_mean_reversion'
        assert strategy.timeframe == '5m'
        assert strategy.profit_target_pct == 1.5
        assert strategy.stop_loss_pct == 2.0
        assert strategy.max_leverage == 3.0
        assert strategy.min_confidence == 0.65
    
    def test_generate_signal(self, strategy, market_data, indicators):
        """Test signal generation"""
        signal = strategy.generate_signal(market_data, indicators)
        
        assert signal.symbol == 'BTC/USDT'
        assert signal.price == 50000.0
        assert signal.action in [SignalAction.BUY, SignalAction.SELL, SignalAction.HOLD]
    
    def test_strong_trend_hold(self, strategy, market_data, indicators):
        """Test HOLD signal when strong trend exists"""
        indicators['adx'] = 30.0  # Strong trend
        
        signal = strategy.generate_signal(market_data, indicators)
        
        assert signal.action == SignalAction.HOLD
        assert 'strong trend' in signal.metadata.get('reason', '').lower()
    
    def test_bb_extreme_upper(self, strategy, market_data, indicators):
        """Test Bollinger Band extreme - upper band"""
        market_data['price'] = 50950.0  # Near upper band
        indicators['bb_upper'] = 51000.0
        indicators['bb_lower'] = 49000.0
        
        signal = strategy._check_bb_extreme(market_data, indicators)
        assert signal < 0.0  # Bearish (expect reversion down)
    
    def test_bb_extreme_lower(self, strategy, market_data, indicators):
        """Test Bollinger Band extreme - lower band"""
        market_data['price'] = 49050.0  # Near lower band
        indicators['bb_upper'] = 51000.0
        indicators['bb_lower'] = 49000.0
        
        signal = strategy._check_bb_extreme(market_data, indicators)
        assert signal > 0.0  # Bullish (expect reversion up)
    
    def test_rsi_overbought(self, strategy, indicators):
        """Test RSI overbought signal"""
        indicators['rsi'] = 75.0  # Overbought
        
        signal = strategy._check_rsi_extreme(indicators)
        assert signal < 0.0  # Bearish (expect reversion down)
    
    def test_rsi_oversold(self, strategy, indicators):
        """Test RSI oversold signal"""
        indicators['rsi'] = 25.0  # Oversold
        
        signal = strategy._check_rsi_extreme(indicators)
        assert signal > 0.0  # Bullish (expect reversion up)
    
    def test_rsi_neutral(self, strategy, indicators):
        """Test RSI neutral signal"""
        indicators['rsi'] = 50.0  # Neutral
        
        signal = strategy._check_rsi_extreme(indicators)
        assert signal == 0.0  # No signal
    
    def test_zscore_high(self, strategy, market_data, indicators):
        """Test Z-score - price too high"""
        market_data['price'] = 51500.0  # 3 std devs above mean
        indicators['sma_20'] = 50000.0
        indicators['std_dev'] = 500.0
        
        signal = strategy._check_zscore(market_data, indicators)
        assert signal < 0.0  # Bearish (expect reversion down)
    
    def test_zscore_low(self, strategy, market_data, indicators):
        """Test Z-score - price too low"""
        market_data['price'] = 48500.0  # 3 std devs below mean
        indicators['sma_20'] = 50000.0
        indicators['std_dev'] = 500.0
        
        signal = strategy._check_zscore(market_data, indicators)
        assert signal > 0.0  # Bullish (expect reversion up)
    
    def test_zscore_normal(self, strategy, market_data, indicators):
        """Test Z-score - normal range"""
        market_data['price'] = 50000.0
        indicators['sma_20'] = 50000.0
        indicators['std_dev'] = 500.0
        
        signal = strategy._check_zscore(market_data, indicators)
        assert signal == 0.0  # No signal
    
    def test_sma_deviation_high(self, strategy, market_data, indicators):
        """Test SMA deviation - price too high"""
        market_data['price'] = 52000.0  # 4% above SMA
        indicators['sma_50'] = 50000.0
        
        signal = strategy._check_sma_deviation(market_data, indicators)
        assert signal < 0.0  # Bearish (expect reversion down)
    
    def test_sma_deviation_low(self, strategy, market_data, indicators):
        """Test SMA deviation - price too low"""
        market_data['price'] = 48000.0  # 4% below SMA
        indicators['sma_50'] = 50000.0
        
        signal = strategy._check_sma_deviation(market_data, indicators)
        assert signal > 0.0  # Bullish (expect reversion up)
    
    def test_sma_deviation_normal(self, strategy, market_data, indicators):
        """Test SMA deviation - normal range"""
        market_data['price'] = 50000.0
        indicators['sma_50'] = 50000.0
        
        signal = strategy._check_sma_deviation(market_data, indicators)
        assert signal == 0.0  # No signal
    
    def test_volume_confirmation_low(self, strategy, market_data, indicators):
        """Test volume confirmation - low volume"""
        market_data['volume'] = 600.0  # Low volume
        indicators['volume_avg'] = 800.0
        
        signal = strategy._check_volume_confirmation(market_data, indicators)
        assert signal > 0.0  # Positive (weak move likely to reverse)
    
    def test_volume_confirmation_high(self, strategy, market_data, indicators):
        """Test volume confirmation - high volume"""
        market_data['volume'] = 1400.0  # High volume
        indicators['volume_avg'] = 800.0
        
        signal = strategy._check_volume_confirmation(market_data, indicators)
        assert signal < 0.0  # Negative (strong move may continue)
    
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
    
    def test_should_exit_early_strong_trend(self, strategy, indicators):
        """Test early exit - strong trend emerged"""
        indicators['adx'] = 30.0  # Strong trend
        
        should_exit = strategy.should_exit_early(50000.0, 49000.0, 'long', indicators)
        
        assert should_exit is True
    
    def test_should_exit_early_max_hold_time(self, strategy, indicators):
        """Test early exit - max hold time exceeded"""
        strategy.entry_time = datetime(2024, 1, 1, 0, 0, 0)
        
        should_exit = strategy.should_exit_early(50000.0, 49000.0, 'long', indicators)
        
        assert should_exit is True
    
    def test_should_exit_early_loss_long(self, strategy, indicators):
        """Test early exit - significant loss on long position"""
        current_price = 48500.0  # 3% loss
        entry_price = 50000.0
        
        should_exit = strategy.should_exit_early(current_price, entry_price, 'long', indicators)
        
        assert should_exit is True
    
    def test_should_exit_early_loss_short(self, strategy, indicators):
        """Test early exit - significant loss on short position"""
        current_price = 51500.0  # 3% loss
        entry_price = 50000.0
        
        should_exit = strategy.should_exit_early(current_price, entry_price, 'short', indicators)
        
        assert should_exit is True
    
    def test_should_not_exit_early(self, strategy, indicators):
        """Test no early exit - normal conditions"""
        strategy.entry_time = datetime.now()
        indicators['adx'] = 20.0  # No strong trend
        
        should_exit = strategy.should_exit_early(50000.0, 49500.0, 'long', indicators)
        
        assert should_exit is False
    
    def test_stop_loss_calculation_buy(self, strategy):
        """Test stop loss calculation for BUY"""
        current_price = 50000.0
        stop_loss = strategy._calculate_stop_loss(current_price, SignalAction.BUY)
        
        expected = 50000.0 * (1 - 2.0 / 100)  # 2% below
        assert abs(stop_loss - expected) < 0.01
    
    def test_stop_loss_calculation_sell(self, strategy):
        """Test stop loss calculation for SELL"""
        current_price = 50000.0
        stop_loss = strategy._calculate_stop_loss(current_price, SignalAction.SELL)
        
        expected = 50000.0 * (1 + 2.0 / 100)  # 2% above
        assert abs(stop_loss - expected) < 0.01
    
    def test_take_profit_calculation_buy(self, strategy):
        """Test take profit calculation for BUY"""
        current_price = 50000.0
        take_profit = strategy._calculate_take_profit(current_price, SignalAction.BUY)
        
        expected = 50000.0 * (1 + 1.5 / 100)  # 1.5% above
        assert abs(take_profit - expected) < 0.01
    
    def test_take_profit_calculation_sell(self, strategy):
        """Test take profit calculation for SELL"""
        current_price = 50000.0
        take_profit = strategy._calculate_take_profit(current_price, SignalAction.SELL)
        
        expected = 50000.0 * (1 - 1.5 / 100)  # 1.5% below
        assert abs(take_profit - expected) < 0.01
    
    def test_position_size_calculation(self, strategy):
        """Test position size calculation"""
        confidence = 0.8
        position_size = strategy._calculate_position_size(confidence)
        
        assert position_size > 0.0
        assert position_size <= 0.15  # Max 15% of portfolio
    
    def test_signal_aggregation(self, strategy, market_data, indicators):
        """Test signal aggregation from multiple sources"""
        signals = strategy._analyze_mean_reversion_signals(market_data, indicators)
        
        assert isinstance(signals, dict)
        assert 'bb_extreme' in signals
        assert 'rsi_extreme' in signals
        assert 'zscore' in signals
        assert 'sma_deviation' in signals
        assert 'volume_confirmation' in signals
        
        for signal_value in signals.values():
            assert isinstance(signal_value, float)
