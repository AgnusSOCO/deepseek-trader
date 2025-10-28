"""
Unit tests for Scalping Strategy
"""

import pytest
from datetime import datetime
from src.strategies.scalping import ScalpingStrategy
from src.strategies.base_strategy import SignalAction


class TestScalpingStrategy:
    """Test suite for ScalpingStrategy"""
    
    @pytest.fixture
    def strategy(self):
        """Create scalping strategy instance"""
        config = {
            'timeframe': '1m',
            'profit_target_pct': 0.3,
            'stop_loss_pct': 0.4,
            'max_leverage': 5.0,
            'min_confidence': 0.7
        }
        return ScalpingStrategy('test_scalping', config)
    
    @pytest.fixture
    def market_data(self):
        """Create sample market data"""
        return {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'timestamp': datetime.now(),
            'volume': 1000.0,
            'bid_volume': 600.0,
            'ask_volume': 400.0
        }
    
    @pytest.fixture
    def indicators(self):
        """Create sample indicators"""
        return {
            'rsi': 50.0,
            'bb_upper': 51000.0,
            'bb_lower': 49000.0,
            'bb_middle': 50000.0,
            'vwap': 50000.0,
            'volume_avg': 500.0,
            'atr': 500.0,
            'roc': 0.5
        }
    
    def test_initialization(self, strategy):
        """Test strategy initialization"""
        assert strategy.name == 'test_scalping'
        assert strategy.timeframe == '1m'
        assert strategy.profit_target_pct == 0.3
        assert strategy.stop_loss_pct == 0.4
        assert strategy.max_leverage == 5.0
        assert strategy.min_confidence == 0.7
    
    def test_generate_signal_hold(self, strategy, market_data, indicators):
        """Test signal generation - HOLD case"""
        signal = strategy.generate_signal(market_data, indicators)
        
        assert signal.symbol == 'BTC/USDT'
        assert signal.price == 50000.0
        assert signal.action in [SignalAction.BUY, SignalAction.SELL, SignalAction.HOLD]
    
    def test_order_book_imbalance_bullish(self, strategy, market_data, indicators):
        """Test order book imbalance detection - bullish"""
        market_data['bid_volume'] = 700.0
        market_data['ask_volume'] = 300.0
        
        signal = strategy._check_order_book_imbalance(market_data)
        assert signal > 0.0  # Bullish signal
    
    def test_order_book_imbalance_bearish(self, strategy, market_data, indicators):
        """Test order book imbalance detection - bearish"""
        market_data['bid_volume'] = 300.0
        market_data['ask_volume'] = 700.0
        
        signal = strategy._check_order_book_imbalance(market_data)
        assert signal < 0.0  # Bearish signal
    
    def test_volume_surge_detected(self, strategy, market_data, indicators):
        """Test volume surge detection"""
        market_data['volume'] = 1500.0
        indicators['volume_avg'] = 500.0
        
        signal = strategy._check_volume_surge(market_data, indicators)
        assert signal != 0.0  # Signal detected
    
    def test_vwap_deviation_above(self, strategy, market_data, indicators):
        """Test VWAP deviation - price above VWAP"""
        market_data['price'] = 50200.0  # 0.4% above VWAP
        indicators['vwap'] = 50000.0
        
        signal = strategy._check_vwap_deviation(market_data, indicators)
        assert signal < 0.0  # Bearish (price too high)
    
    def test_vwap_deviation_below(self, strategy, market_data, indicators):
        """Test VWAP deviation - price below VWAP"""
        market_data['price'] = 49800.0  # 0.4% below VWAP
        indicators['vwap'] = 50000.0
        
        signal = strategy._check_vwap_deviation(market_data, indicators)
        assert signal > 0.0  # Bullish (price too low)
    
    def test_bb_breakout_upper(self, strategy, market_data, indicators):
        """Test Bollinger Band breakout - upper band"""
        market_data['price'] = 50950.0  # Near upper band
        indicators['bb_upper'] = 51000.0
        indicators['bb_lower'] = 49000.0
        indicators['bb_middle'] = 50000.0
        
        signal = strategy._check_bb_breakout(market_data, indicators)
        assert isinstance(signal, float)
    
    def test_bb_breakout_lower(self, strategy, market_data, indicators):
        """Test Bollinger Band breakout - lower band"""
        market_data['price'] = 49050.0  # Near lower band
        indicators['bb_upper'] = 51000.0
        indicators['bb_lower'] = 49000.0
        indicators['bb_middle'] = 50000.0
        
        signal = strategy._check_bb_breakout(market_data, indicators)
        assert isinstance(signal, float)
    
    def test_price_momentum_positive(self, strategy, indicators):
        """Test price momentum - positive"""
        indicators['roc'] = 1.5  # Strong positive momentum
        
        signal = strategy._check_price_momentum(indicators)
        assert signal > 0.0  # Bullish
    
    def test_price_momentum_negative(self, strategy, indicators):
        """Test price momentum - negative"""
        indicators['roc'] = -1.5  # Strong negative momentum
        
        signal = strategy._check_price_momentum(indicators)
        assert signal < 0.0  # Bearish
    
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
    
    def test_daily_loss_limit(self, strategy, market_data, indicators):
        """Test daily loss limit check"""
        strategy.daily_pnl = -2.5  # -2.5% loss
        strategy.daily_loss_limit_pct = 2.0
        
        signal = strategy.generate_signal(market_data, indicators)
        
        assert signal.action == SignalAction.HOLD
        assert 'daily loss limit' in signal.metadata.get('reason', '').lower()
    
    def test_update_trade_result_profit(self, strategy):
        """Test trade result update - profit"""
        strategy.update_trade_result(1.5)  # 1.5% profit
        
        assert strategy.daily_pnl == 1.5
        assert strategy.trades_today == 1
    
    def test_update_trade_result_loss(self, strategy):
        """Test trade result update - loss"""
        strategy.update_trade_result(-0.8)  # 0.8% loss
        
        assert strategy.daily_pnl == -0.8
        assert strategy.trades_today == 1
    
    def test_reset_daily_stats(self, strategy):
        """Test daily stats reset"""
        strategy.daily_pnl = 5.0
        strategy.trades_today = 10
        
        strategy.reset_daily_stats()
        
        assert strategy.daily_pnl == 0.0
        assert strategy.trades_today == 0
    
    def test_stop_loss_calculation_buy(self, strategy):
        """Test stop loss calculation for BUY"""
        current_price = 50000.0
        stop_loss = strategy._calculate_stop_loss(current_price, SignalAction.BUY)
        
        expected = 50000.0 * (1 - 0.4 / 100)  # 0.4% below
        assert abs(stop_loss - expected) < 0.01
    
    def test_stop_loss_calculation_sell(self, strategy):
        """Test stop loss calculation for SELL"""
        current_price = 50000.0
        stop_loss = strategy._calculate_stop_loss(current_price, SignalAction.SELL)
        
        expected = 50000.0 * (1 + 0.4 / 100)  # 0.4% above
        assert abs(stop_loss - expected) < 0.01
    
    def test_take_profit_calculation_buy(self, strategy):
        """Test take profit calculation for BUY"""
        current_price = 50000.0
        take_profit = strategy._calculate_take_profit(current_price, SignalAction.BUY)
        
        expected = 50000.0 * (1 + 0.3 / 100)  # 0.3% above
        assert abs(take_profit - expected) < 0.01
    
    def test_take_profit_calculation_sell(self, strategy):
        """Test take profit calculation for SELL"""
        current_price = 50000.0
        take_profit = strategy._calculate_take_profit(current_price, SignalAction.SELL)
        
        expected = 50000.0 * (1 - 0.3 / 100)  # 0.3% below
        assert abs(take_profit - expected) < 0.01
    
    def test_position_size_calculation(self, strategy):
        """Test position size calculation"""
        confidence = 0.8
        position_size = strategy._calculate_position_size(confidence)
        
        assert position_size > 0.0
        assert position_size <= 0.15  # Max 15% of portfolio
    
    def test_signal_aggregation(self, strategy, market_data, indicators):
        """Test signal aggregation from multiple sources"""
        signals = strategy._analyze_scalping_signals(market_data, indicators)
        
        assert isinstance(signals, dict)
        assert 'order_book_imbalance' in signals
        assert 'volume_surge' in signals
        assert 'vwap_deviation' in signals
        assert 'bb_breakout' in signals
        assert 'price_momentum' in signals
        
        for signal_value in signals.values():
            assert isinstance(signal_value, float)
