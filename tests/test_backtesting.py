"""
Unit tests for backtesting module
"""

import unittest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backtesting.backtest_engine import BacktestEngine, Trade, Position
from src.backtesting.performance import PerformanceMetrics
from src.backtesting.optimizer import ParameterOptimizer
from src.backtesting.walk_forward import WalkForwardOptimizer
from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction


class MockStrategy(BaseStrategy):
    """Mock strategy for testing"""
    
    def __init__(self, name: str, config: dict):
        super().__init__(name, config)
        self.signal_action = config.get('signal_action', SignalAction.HOLD)
        self.signal_confidence = config.get('signal_confidence', 0.5)
    
    def initialize(self):
        self.is_initialized = True
    
    def on_data(self, market_data, indicators):
        pass
    
    def get_parameters(self):
        return {'signal_action': self.signal_action}
    
    def generate_signal(self, market_data, indicators):
        if self.signal_action == SignalAction.HOLD:
            return TradingSignal(
                action=SignalAction.HOLD,
                confidence=0.0,
                symbol=market_data['symbol'],
                timestamp=market_data['timestamp'],
                price=market_data['price'],
                metadata={}
            )
        
        return TradingSignal(
            action=self.signal_action,
            confidence=self.signal_confidence,
            symbol=market_data['symbol'],
            timestamp=market_data['timestamp'],
            price=market_data['price'],
            metadata={'leverage': 1.0},
            stop_loss=market_data['price'] * 0.98 if self.signal_action == SignalAction.BUY else market_data['price'] * 1.02,
            take_profit=market_data['price'] * 1.02 if self.signal_action == SignalAction.BUY else market_data['price'] * 0.98,
            position_size=0.1
        )


class TestBacktestEngine(unittest.TestCase):
    """Test BacktestEngine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = BacktestEngine(
            initial_capital=10000.0,
            maker_fee=0.0002,
            taker_fee=0.0005,
            slippage_pct=0.0005
        )
    
    def _create_test_data(self, num_bars=100, start_price=50000.0):
        """Create test OHLCV data"""
        dates = pd.date_range(start='2024-01-01', periods=num_bars, freq='1h')
        
        np.random.seed(42)
        returns = np.random.normal(0.0001, 0.01, num_bars)
        prices = start_price * (1 + returns).cumprod()
        
        data = pd.DataFrame({
            'open': prices * 0.999,
            'high': prices * 1.001,
            'low': prices * 0.998,
            'close': prices,
            'volume': np.random.uniform(100, 1000, num_bars),
            'rsi': np.random.uniform(30, 70, num_bars),
            'ema_12': prices * 0.999,
            'ema_26': prices * 1.001
        }, index=dates)
        
        return data
    
    def test_initialization(self):
        """Test engine initialization"""
        self.assertEqual(self.engine.initial_capital, 10000.0)
        self.assertEqual(self.engine.capital, 10000.0)
        self.assertEqual(len(self.engine.positions), 0)
        self.assertEqual(len(self.engine.trades), 0)
    
    def test_backtest_no_trades(self):
        """Test backtest with no trades (HOLD strategy)"""
        data = self._create_test_data()
        strategy = MockStrategy('test', {'signal_action': SignalAction.HOLD})
        
        results = self.engine.run_backtest(strategy, data, 'BTC/USDT')
        
        self.assertEqual(results['num_trades'], 0)
        self.assertEqual(results['final_equity'], 10000.0)
        self.assertEqual(results['total_return_pct'], 0.0)
    
    def test_backtest_with_trades(self):
        """Test backtest with trades"""
        data = self._create_test_data()
        strategy = MockStrategy('test', {
            'signal_action': SignalAction.BUY,
            'signal_confidence': 0.8
        })
        
        results = self.engine.run_backtest(strategy, data, 'BTC/USDT')
        
        self.assertGreater(len(results['trades']), 0)
        self.assertIsInstance(results['final_equity'], float)
    
    def test_position_opening(self):
        """Test position opening logic"""
        data = self._create_test_data(num_bars=10)
        strategy = MockStrategy('test', {
            'signal_action': SignalAction.BUY,
            'signal_confidence': 0.8
        })
        
        results = self.engine.run_backtest(strategy, data, 'BTC/USDT')
        
        self.assertGreater(len(results['trades']), 0)
        
        trade = results['trades'][0]
        self.assertIsInstance(trade, Trade)
        self.assertEqual(trade.symbol, 'BTC/USDT')
        self.assertEqual(trade.side, 'long')
    
    def test_stop_loss_trigger(self):
        """Test stop-loss triggering"""
        dates = pd.date_range(start='2024-01-01', periods=10, freq='1h')
        prices = [50000, 49000, 48000, 47000, 46000, 45000, 44000, 43000, 42000, 41000]
        
        data = pd.DataFrame({
            'open': prices,
            'high': [p * 1.001 for p in prices],
            'low': [p * 0.999 for p in prices],
            'close': prices,
            'volume': [100] * 10,
            'rsi': [50] * 10,
            'ema_12': prices,
            'ema_26': prices
        }, index=dates)
        
        strategy = MockStrategy('test', {
            'signal_action': SignalAction.BUY,
            'signal_confidence': 0.8
        })
        
        results = self.engine.run_backtest(strategy, data, 'BTC/USDT')
        
        stop_loss_trades = [t for t in results['trades'] if t.exit_reason == 'stop_loss']
        self.assertGreater(len(stop_loss_trades), 0)


class TestPerformanceMetrics(unittest.TestCase):
    """Test PerformanceMetrics"""
    
    def _create_test_trades(self):
        """Create test trades"""
        base_time = datetime(2024, 1, 1)
        
        trades = [
            Trade(
                entry_time=base_time,
                exit_time=base_time + timedelta(hours=1),
                symbol='BTC/USDT',
                side='long',
                entry_price=50000,
                exit_price=50500,
                size=0.1,
                leverage=1.0,
                pnl=50,
                pnl_pct=1.0,
                fees=5,
                duration_minutes=60,
                exit_reason='take_profit'
            ),
            Trade(
                entry_time=base_time + timedelta(hours=2),
                exit_time=base_time + timedelta(hours=3),
                symbol='BTC/USDT',
                side='long',
                entry_price=50500,
                exit_price=50250,
                size=0.1,
                leverage=1.0,
                pnl=-25,
                pnl_pct=-0.5,
                fees=5,
                duration_minutes=60,
                exit_reason='stop_loss'
            )
        ]
        
        return trades
    
    def _create_test_equity_curve(self):
        """Create test equity curve"""
        base_time = datetime(2024, 1, 1)
        equity_curve = [
            (base_time, 10000),
            (base_time + timedelta(hours=1), 10050),
            (base_time + timedelta(hours=2), 10025),
            (base_time + timedelta(hours=3), 10000)
        ]
        return equity_curve
    
    def test_calculate_returns(self):
        """Test return calculations"""
        trades = self._create_test_trades()
        equity_curve = self._create_test_equity_curve()
        
        metrics = PerformanceMetrics.calculate_all_metrics(
            trades, equity_curve, 10000.0
        )
        
        self.assertIn('total_return_pct', metrics)
        self.assertIn('annualized_return_pct', metrics)
        self.assertIsInstance(metrics['total_return_pct'], float)
    
    def test_calculate_risk_metrics(self):
        """Test risk metric calculations"""
        trades = self._create_test_trades()
        equity_curve = self._create_test_equity_curve()
        
        metrics = PerformanceMetrics.calculate_all_metrics(
            trades, equity_curve, 10000.0
        )
        
        self.assertIn('sharpe_ratio', metrics)
        self.assertIn('sortino_ratio', metrics)
        self.assertIn('calmar_ratio', metrics)
    
    def test_calculate_trade_stats(self):
        """Test trade statistics"""
        trades = self._create_test_trades()
        equity_curve = self._create_test_equity_curve()
        
        metrics = PerformanceMetrics.calculate_all_metrics(
            trades, equity_curve, 10000.0
        )
        
        self.assertEqual(metrics['num_trades'], 2)
        self.assertEqual(metrics['num_wins'], 1)
        self.assertEqual(metrics['num_losses'], 1)
        self.assertEqual(metrics['win_rate'], 50.0)
    
    def test_empty_metrics(self):
        """Test metrics with no trades"""
        metrics = PerformanceMetrics.calculate_all_metrics([], [], 10000.0)
        
        self.assertEqual(metrics['total_return_pct'], 0.0)
        self.assertEqual(metrics['num_trades'], 0)


class TestParameterOptimizer(unittest.TestCase):
    """Test ParameterOptimizer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = BacktestEngine(initial_capital=10000.0)
        self.optimizer = ParameterOptimizer(self.engine, 'sharpe_ratio')
    
    def _create_test_data(self):
        """Create test data"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1h')
        np.random.seed(42)
        prices = 50000 * (1 + np.random.normal(0.0001, 0.01, 100)).cumprod()
        
        return pd.DataFrame({
            'open': prices,
            'high': prices * 1.001,
            'low': prices * 0.999,
            'close': prices,
            'volume': np.random.uniform(100, 1000, 100),
            'rsi': np.random.uniform(30, 70, 100)
        }, index=dates)
    
    def test_grid_search(self):
        """Test grid search optimization"""
        data = self._create_test_data()
        
        param_grid = {
            'signal_confidence': [0.5, 0.7, 0.9]
        }
        
        base_config = {'signal_action': SignalAction.BUY}
        
        best_params, results = self.optimizer.grid_search(
            MockStrategy,
            base_config,
            param_grid,
            data,
            'BTC/USDT'
        )
        
        self.assertIsInstance(best_params, dict)
        self.assertEqual(len(results), 3)  # 3 combinations
    
    def test_random_search(self):
        """Test random search optimization"""
        data = self._create_test_data()
        
        param_distributions = {
            'signal_confidence': (0.5, 1.0)
        }
        
        base_config = {'signal_action': SignalAction.BUY}
        
        best_params, results = self.optimizer.random_search(
            MockStrategy,
            base_config,
            param_distributions,
            data,
            n_iterations=5,
            symbol='BTC/USDT'
        )
        
        self.assertIsInstance(best_params, dict)
        self.assertEqual(len(results), 5)


class TestWalkForwardOptimizer(unittest.TestCase):
    """Test WalkForwardOptimizer"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = BacktestEngine(initial_capital=10000.0)
        self.param_optimizer = ParameterOptimizer(self.engine, 'sharpe_ratio')
        self.wf_optimizer = WalkForwardOptimizer(self.engine, self.param_optimizer)
    
    def _create_test_data(self):
        """Create test data"""
        dates = pd.date_range(start='2024-01-01', periods=8760, freq='1h')
        np.random.seed(42)
        prices = 50000 * (1 + np.random.normal(0.0001, 0.01, 8760)).cumprod()
        
        return pd.DataFrame({
            'open': prices,
            'high': prices * 1.001,
            'low': prices * 0.999,
            'close': prices,
            'volume': np.random.uniform(100, 1000, 8760),
            'rsi': np.random.uniform(30, 70, 8760)
        }, index=dates)
    
    def test_generate_windows(self):
        """Test window generation"""
        data = self._create_test_data()
        
        windows = self.wf_optimizer._generate_windows(
            data,
            train_months=6,
            test_months=1
        )
        
        self.assertGreater(len(windows), 0)
        
        train_data, test_data = windows[0]
        self.assertIsInstance(train_data, pd.DataFrame)
        self.assertIsInstance(test_data, pd.DataFrame)
        self.assertGreater(len(train_data), 0)
        self.assertGreater(len(test_data), 0)


if __name__ == '__main__':
    unittest.main()
