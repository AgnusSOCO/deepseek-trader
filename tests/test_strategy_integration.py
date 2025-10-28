"""
Integration tests for Phase 4 strategy combination
"""

import pytest
from datetime import datetime
from src.strategies.scalping import ScalpingStrategy
from src.strategies.momentum import MomentumStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.strategy_manager import StrategyManager
from src.execution.leverage_manager import LeverageManager, LeverageConfig
from src.strategies.base_strategy import SignalAction


class TestStrategyIntegration:
    """Integration tests for multiple strategies working together"""
    
    @pytest.fixture
    def strategy_manager(self):
        """Create strategy manager with all Phase 4 strategies"""
        manager = StrategyManager()
        
        scalping_config = {
            'timeframe': '1m',
            'profit_target_pct': 0.3,
            'stop_loss_pct': 0.4,
            'max_leverage': 5.0,
            'min_confidence': 0.7
        }
        scalping = ScalpingStrategy('scalping', scalping_config)
        manager.register_strategy(scalping, weight=1.0)
        
        momentum_config = {
            'timeframe': '15m',
            'profit_target_pct': 5.0,
            'initial_stop_loss_pct': 3.0,
            'trailing_stop_pct': 2.0,
            'max_leverage': 5.0,
            'min_confidence': 0.65
        }
        momentum = MomentumStrategy('momentum', momentum_config)
        manager.register_strategy(momentum, weight=1.0)
        
        mean_reversion_config = {
            'timeframe': '5m',
            'profit_target_pct': 1.5,
            'stop_loss_pct': 2.0,
            'max_leverage': 3.0,
            'min_confidence': 0.65
        }
        mean_reversion = MeanReversionStrategy('mean_reversion', mean_reversion_config)
        manager.register_strategy(mean_reversion, weight=1.0)
        
        return manager
    
    @pytest.fixture
    def leverage_manager(self):
        """Create leverage manager"""
        config = LeverageConfig(
            absolute_max=10.0,
            scalping_max=5.0,
            momentum_max=5.0,
            mean_reversion_max=3.0
        )
        return LeverageManager(config)
    
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
        """Create comprehensive indicators"""
        return {
            'rsi': 55.0,
            'bb_upper': 51000.0,
            'bb_lower': 49000.0,
            'bb_middle': 50000.0,
            'bb_width': 0.04,
            'vwap': 50000.0,
            'volume_avg': 800.0,
            'atr': 500.0,
            'roc': 0.5,
            'ema_12': 49800.0,
            'ema_26': 49500.0,
            'adx': 22.0,
            'macd': 100.0,
            'macd_signal': 80.0,
            'macd_histogram': 20.0,
            'sma_20': 50000.0,
            'sma_50': 50000.0,
            'std_dev': 500.0,
            'price': 50000.0
        }
    
    def test_all_strategies_registered(self, strategy_manager):
        """Test all Phase 4 strategies are registered"""
        strategies = list(strategy_manager.strategies.keys())
        
        assert 'scalping' in strategies
        assert 'momentum' in strategies
        assert 'mean_reversion' in strategies
        assert len(strategies) == 3
    
    def test_start_all_strategies(self, strategy_manager):
        """Test starting all strategies"""
        strategy_manager.start_all()
        
        active = strategy_manager.get_active_strategies()
        assert len(active) == 3
        assert 'scalping' in active
        assert 'momentum' in active
        assert 'mean_reversion' in active
    
    def test_generate_signals_from_all_strategies(self, strategy_manager, market_data, indicators):
        """Test generating signals from all strategies"""
        strategy_manager.start_all()
        
        signals = strategy_manager.generate_signals('BTC/USDT', market_data, indicators)
        
        assert len(signals) == 3
        assert all(signal.symbol == 'BTC/USDT' for signal in signals)
        assert all(signal.action in [SignalAction.BUY, SignalAction.SELL, SignalAction.HOLD] for signal in signals)
    
    def test_aggregate_signals(self, strategy_manager, market_data, indicators):
        """Test aggregating signals from multiple strategies"""
        strategy_manager.start_all()
        
        signals = strategy_manager.generate_signals('BTC/USDT', market_data, indicators)
        aggregated = strategy_manager.aggregate_signals(signals)
        
        assert aggregated is not None
        assert aggregated.symbol == 'BTC/USDT'
        assert aggregated.action in [SignalAction.BUY, SignalAction.SELL, SignalAction.HOLD]
        assert 0 <= aggregated.confidence <= 1.0
        assert aggregated.metadata['aggregated'] is True
        assert aggregated.metadata['num_signals'] == 3
    
    def test_market_regime_detection_high_volatility(self, strategy_manager, indicators):
        """Test market regime detection - high volatility"""
        indicators['atr'] = 2000.0  # High volatility
        indicators['price'] = 50000.0
        
        regime = strategy_manager.detect_market_regime(indicators)
        
        assert regime == 'high_volatility'
    
    def test_market_regime_detection_trending(self, strategy_manager, indicators):
        """Test market regime detection - trending"""
        indicators['adx'] = 30.0  # Strong trend
        indicators['atr'] = 500.0
        indicators['price'] = 50000.0
        
        regime = strategy_manager.detect_market_regime(indicators)
        
        assert regime == 'trending'
    
    def test_market_regime_detection_sideways(self, strategy_manager, indicators):
        """Test market regime detection - sideways"""
        indicators['adx'] = 20.0  # Weak trend
        indicators['atr'] = 500.0
        indicators['price'] = 50000.0
        
        regime = strategy_manager.detect_market_regime(indicators)
        
        assert regime == 'sideways'
    
    def test_capital_allocation_high_volatility(self, strategy_manager):
        """Test capital allocation - high volatility regime"""
        total_capital = 10000.0
        market_regime = 'high_volatility'
        strategy_performance = {
            'scalping': 0.8,
            'momentum': 0.6,
            'mean_reversion': 0.9
        }
        
        allocations = strategy_manager.allocate_capital(
            total_capital,
            market_regime,
            strategy_performance
        )
        
        assert sum(allocations.values()) == pytest.approx(total_capital, rel=0.01)
        assert allocations['mean_reversion'] > allocations['momentum']
    
    def test_capital_allocation_trending(self, strategy_manager):
        """Test capital allocation - trending regime"""
        total_capital = 10000.0
        market_regime = 'trending'
        strategy_performance = {
            'scalping': 0.7,
            'momentum': 0.9,
            'mean_reversion': 0.5
        }
        
        allocations = strategy_manager.allocate_capital(
            total_capital,
            market_regime,
            strategy_performance
        )
        
        assert sum(allocations.values()) == pytest.approx(total_capital, rel=0.01)
        assert allocations['momentum'] > allocations['mean_reversion']
    
    def test_capital_allocation_sideways(self, strategy_manager):
        """Test capital allocation - sideways regime"""
        total_capital = 10000.0
        market_regime = 'sideways'
        strategy_performance = {
            'scalping': 0.9,
            'momentum': 0.5,
            'mean_reversion': 0.7
        }
        
        allocations = strategy_manager.allocate_capital(
            total_capital,
            market_regime,
            strategy_performance
        )
        
        assert sum(allocations.values()) == pytest.approx(total_capital, rel=0.01)
        assert allocations['scalping'] > allocations['momentum']
    
    def test_select_strategies_for_regime_high_volatility(self, strategy_manager):
        """Test strategy selection - high volatility"""
        available = ['scalping', 'momentum', 'mean_reversion']
        selected = strategy_manager.select_strategies_for_regime('high_volatility', available)
        
        assert 'mean_reversion' in selected
        assert 'scalping' in selected
    
    def test_select_strategies_for_regime_trending(self, strategy_manager):
        """Test strategy selection - trending"""
        available = ['scalping', 'momentum', 'mean_reversion']
        selected = strategy_manager.select_strategies_for_regime('trending', available)
        
        assert 'momentum' in selected
        assert 'scalping' in selected
    
    def test_select_strategies_for_regime_sideways(self, strategy_manager):
        """Test strategy selection - sideways"""
        available = ['scalping', 'momentum', 'mean_reversion']
        selected = strategy_manager.select_strategies_for_regime('sideways', available)
        
        assert 'scalping' in selected
        assert 'mean_reversion' in selected
    
    def test_activate_strategies_for_regime(self, strategy_manager):
        """Test activating strategies for regime"""
        strategy_manager.activate_strategies_for_regime('trending')
        
        active = strategy_manager.get_active_strategies()
        assert 'momentum' in active
        assert 'scalping' in active
    
    def test_check_combined_exposure_within_limits(self, strategy_manager):
        """Test combined exposure check - within limits"""
        proposed_trades = [
            {'size': 0.1, 'price': 50000.0},
            {'size': 0.2, 'price': 50000.0}
        ]
        current_positions = [
            {'size': 0.1, 'price': 50000.0}
        ]
        
        approved, reason = strategy_manager.check_combined_exposure(
            proposed_trades,
            current_positions,
            max_exposure_pct=30.0
        )
        
        assert approved is True
        assert 'within limits' in reason.lower()
    
    def test_check_combined_exposure_exceeds_limits(self, strategy_manager):
        """Test combined exposure check - exceeds limits"""
        proposed_trades = [
            {'size': 0.5, 'price': 50000.0},
            {'size': 0.3, 'price': 50000.0}
        ]
        current_positions = [
            {'size': 0.4, 'price': 50000.0}
        ]
        
        approved, reason = strategy_manager.check_combined_exposure(
            proposed_trades,
            current_positions,
            max_exposure_pct=30.0
        )
        
        assert approved is False
        assert 'exceeds' in reason.lower()
    
    def test_leverage_calculation_for_all_strategies(self, leverage_manager):
        """Test leverage calculation for all strategy types"""
        strategies = ['scalping', 'momentum', 'mean_reversion']
        
        for strategy_type in strategies:
            leverage = leverage_manager.calculate_leverage(
                strategy_type=strategy_type,
                confidence=0.8,
                volatility_pct=1.5,
                drawdown_pct=2.0
            )
            
            assert leverage >= 1.0
            assert leverage <= 10.0
    
    def test_leverage_respects_strategy_limits(self, leverage_manager):
        """Test leverage respects strategy-specific limits"""
        scalping_leverage = leverage_manager.calculate_leverage(
            strategy_type='scalping',
            confidence=1.0,
            volatility_pct=0.5,
            drawdown_pct=0.0,
            base_leverage=10.0
        )
        assert scalping_leverage <= 5.0
        
        mean_rev_leverage = leverage_manager.calculate_leverage(
            strategy_type='mean_reversion',
            confidence=1.0,
            volatility_pct=0.5,
            drawdown_pct=0.0,
            base_leverage=10.0
        )
        assert mean_rev_leverage <= 3.0
    
    def test_end_to_end_signal_generation_and_leverage(
        self,
        strategy_manager,
        leverage_manager,
        market_data,
        indicators
    ):
        """Test end-to-end: signal generation + leverage calculation"""
        strategy_manager.start_all()
        
        signals = strategy_manager.generate_signals('BTC/USDT', market_data, indicators)
        
        aggregated = strategy_manager.aggregate_signals(signals)
        
        if aggregated and aggregated.action != SignalAction.HOLD:
            strategy_type = aggregated.metadata.get('strategy', 'momentum')
            leverage = leverage_manager.calculate_leverage(
                strategy_type=strategy_type,
                confidence=aggregated.confidence,
                volatility_pct=(indicators['atr'] / indicators['price']) * 100,
                drawdown_pct=0.0
            )
            
            assert leverage >= 1.0
            assert leverage <= 10.0
    
    def test_strategy_manager_status(self, strategy_manager):
        """Test getting strategy manager status"""
        strategy_manager.start_all()
        
        status = strategy_manager.get_strategy_status()
        
        assert 'scalping' in status
        assert 'momentum' in status
        assert 'mean_reversion' in status
        
        for strategy_name, strategy_status in status.items():
            assert 'active' in strategy_status
            assert 'initialized' in strategy_status
            assert 'weight' in strategy_status
