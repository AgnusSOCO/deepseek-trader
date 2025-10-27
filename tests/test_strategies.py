"""
Unit tests for trading strategies
"""

import pytest
from datetime import datetime
from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction
from src.strategies.strategy_manager import StrategyManager
from src.strategies.simple_rsi import SimpleRSIStrategy


class TestBaseStrategy:
    """Test base strategy abstract class"""
    
    def test_signal_action_enum(self):
        """Test SignalAction enum values"""
        assert SignalAction.BUY.value == "BUY"
        assert SignalAction.SELL.value == "SELL"
        assert SignalAction.HOLD.value == "HOLD"
        assert SignalAction.CLOSE_LONG.value == "CLOSE_LONG"
        assert SignalAction.CLOSE_SHORT.value == "CLOSE_SHORT"
    
    def test_trading_signal_creation(self):
        """Test TradingSignal dataclass creation"""
        signal = TradingSignal(
            action=SignalAction.BUY,
            confidence=0.8,
            symbol="BTC/USDT",
            timestamp=datetime.now(),
            metadata={"test": "data"},
            price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            position_size=0.1
        )
        
        assert signal.action == SignalAction.BUY
        assert signal.confidence == 0.8
        assert signal.symbol == "BTC/USDT"
        assert signal.price == 50000.0
        assert signal.stop_loss == 49000.0
        assert signal.take_profit == 52000.0
        assert signal.position_size == 0.1


class TestSimpleRSIStrategy:
    """Test SimpleRSI strategy implementation"""
    
    @pytest.fixture
    def strategy(self):
        """Create SimpleRSI strategy instance"""
        config = {
            'rsi_period': 14,
            'oversold_threshold': 30,
            'overbought_threshold': 70,
            'min_confidence': 0.6,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04,
            'position_size': 0.1
        }
        return SimpleRSIStrategy("test_rsi", config)
    
    def test_strategy_initialization(self, strategy):
        """Test strategy initialization"""
        assert strategy.name == "test_rsi"
        assert strategy.config['rsi_period'] == 14
        assert strategy.config['oversold_threshold'] == 30
        assert strategy.config['overbought_threshold'] == 70
    
    def test_oversold_buy_signal(self, strategy):
        """Test BUY signal generation when RSI is oversold"""
        market_data = {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'timestamp': datetime.now()
        }
        
        indicators = {
            'rsi': 25.0  # Oversold
        }
        
        signal = strategy.generate_signal(market_data, indicators)
        
        assert signal.action == SignalAction.BUY
        assert signal.confidence > 0.6
        assert signal.symbol == 'BTC/USDT'
        assert signal.price == 50000.0
        assert signal.stop_loss < 50000.0
        assert signal.take_profit > 50000.0
    
    def test_overbought_sell_signal(self, strategy):
        """Test SELL signal generation when RSI is overbought"""
        market_data = {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'timestamp': datetime.now()
        }
        
        indicators = {
            'rsi': 75.0  # Overbought
        }
        
        signal = strategy.generate_signal(market_data, indicators)
        
        assert signal.action == SignalAction.SELL
        assert signal.confidence > 0.6
        assert signal.symbol == 'BTC/USDT'
    
    def test_neutral_hold_signal(self, strategy):
        """Test HOLD signal when RSI is neutral"""
        market_data = {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'timestamp': datetime.now()
        }
        
        indicators = {
            'rsi': 50.0  # Neutral
        }
        
        signal = strategy.generate_signal(market_data, indicators)
        
        assert signal.action == SignalAction.HOLD
        assert signal.confidence == 0.5  # Neutral confidence


class TestStrategyManager:
    """Test strategy manager"""
    
    @pytest.fixture
    def manager(self):
        """Create strategy manager instance"""
        return StrategyManager()
    
    @pytest.fixture
    def rsi_strategy(self):
        """Create RSI strategy"""
        config = {
            'rsi_period': 14,
            'oversold_threshold': 30,
            'overbought_threshold': 70,
            'min_confidence': 0.6,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04,
            'position_size': 0.1
        }
        return SimpleRSIStrategy("rsi_1", config)
    
    def test_register_strategy(self, manager, rsi_strategy):
        """Test strategy registration"""
        manager.register_strategy(rsi_strategy, weight=1.0)
        manager.start_strategy("rsi_1")
        
        status = manager.get_strategy_status()
        assert "rsi_1" in status
        assert status["rsi_1"]["active"] is True
        assert status["rsi_1"]["weight"] == 1.0
    
    def test_start_stop_strategy(self, manager, rsi_strategy):
        """Test starting and stopping strategies"""
        manager.register_strategy(rsi_strategy, weight=1.0)
        
        manager.stop_strategy("rsi_1")
        status = manager.get_strategy_status()
        assert status["rsi_1"]["active"] is False
        
        manager.start_strategy("rsi_1")
        status = manager.get_strategy_status()
        assert status["rsi_1"]["active"] is True
    
    def test_process_data(self, manager, rsi_strategy):
        """Test data processing"""
        manager.register_strategy(rsi_strategy, weight=1.0)
        
        market_data = {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'timestamp': datetime.now()
        }
        
        indicators = {
            'rsi': 25.0
        }
        
        manager.process_data('BTC/USDT', market_data, indicators)
    
    def test_generate_signals(self, manager, rsi_strategy):
        """Test signal generation"""
        manager.register_strategy(rsi_strategy, weight=1.0)
        manager.start_strategy("rsi_1")
        
        market_data = {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'timestamp': datetime.now()
        }
        
        indicators = {
            'rsi': 25.0  # Oversold - should generate BUY
        }
        
        signals = manager.generate_signals('BTC/USDT', market_data, indicators)
        
        assert len(signals) == 1
        assert signals[0].action == SignalAction.BUY
    
    def test_aggregate_signals_consensus(self, manager):
        """Test signal aggregation with consensus"""
        config = {
            'rsi_period': 14,
            'oversold_threshold': 30,
            'overbought_threshold': 70,
            'min_confidence': 0.6,
            'stop_loss_pct': 0.02,
            'take_profit_pct': 0.04,
            'position_size': 0.1
        }
        
        strategy1 = SimpleRSIStrategy("rsi_1", config)
        strategy2 = SimpleRSIStrategy("rsi_2", config)
        
        manager.register_strategy(strategy1, weight=1.0)
        manager.register_strategy(strategy2, weight=1.0)
        manager.start_strategy("rsi_1")
        manager.start_strategy("rsi_2")
        
        market_data = {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'timestamp': datetime.now()
        }
        
        indicators = {
            'rsi': 25.0  # Both should generate BUY
        }
        
        signals = manager.generate_signals('BTC/USDT', market_data, indicators)
        aggregated = manager.aggregate_signals(signals)
        
        assert aggregated.action == SignalAction.BUY
        assert aggregated.confidence > 0.6
    
    def test_update_strategy_weight(self, manager, rsi_strategy):
        """Test updating strategy weight"""
        manager.register_strategy(rsi_strategy, weight=1.0)
        
        manager.update_strategy_weight("rsi_1", 2.0)
        
        status = manager.get_strategy_status()
        assert status["rsi_1"]["weight"] == 2.0
