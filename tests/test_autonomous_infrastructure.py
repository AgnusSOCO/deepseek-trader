"""
Tests for Phase B: Core Autonomous Infrastructure

Tests for:
- ExitPlanMonitor
- AutonomousDecisionEngine
- EnhancedRiskManager
"""

import unittest
from datetime import datetime, date
from unittest.mock import Mock, patch
import asyncio

from src.autonomous.exit_plan_monitor import ExitPlanMonitor, ExitPlan, ExitReason
from src.autonomous.enhanced_risk_manager import EnhancedRiskManager
from src.autonomous.autonomous_decision_engine import AutonomousDecisionEngine, Position
from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction


class TestExitPlanMonitor(unittest.TestCase):
    """Test ExitPlanMonitor functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.monitor = ExitPlanMonitor()
    
    def test_add_exit_plan(self):
        """Test adding an exit plan"""
        plan = ExitPlan(
            position_id='test_pos_1',
            symbol='BTC/USDT',
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            invalidation_conditions=['ADX < 25']
        )
        
        self.monitor.add_exit_plan(plan)
        
        self.assertIn('test_pos_1', self.monitor.exit_plans)
        self.assertEqual(self.monitor.exit_plans['test_pos_1'].symbol, 'BTC/USDT')
    
    def test_stop_loss_trigger_long(self):
        """Test stop-loss trigger for long position"""
        plan = ExitPlan(
            position_id='test_pos_1',
            symbol='BTC/USDT',
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            invalidation_conditions=[],
            is_short=False
        )
        
        self.monitor.add_exit_plan(plan)
        
        exit_signal = self.monitor.check_exit_conditions(
            'test_pos_1',
            48500.0,
            {},
            {}
        )
        
        self.assertIsNotNone(exit_signal)
        self.assertTrue(exit_signal['should_exit'])
        self.assertEqual(exit_signal['reason'], ExitReason.STOP_LOSS)
    
    def test_take_profit_trigger_long(self):
        """Test take-profit trigger for long position"""
        plan = ExitPlan(
            position_id='test_pos_1',
            symbol='BTC/USDT',
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            invalidation_conditions=[],
            is_short=False
        )
        
        self.monitor.add_exit_plan(plan)
        
        exit_signal = self.monitor.check_exit_conditions(
            'test_pos_1',
            52500.0,
            {},
            {}
        )
        
        self.assertIsNotNone(exit_signal)
        self.assertTrue(exit_signal['should_exit'])
        self.assertEqual(exit_signal['reason'], ExitReason.TAKE_PROFIT)
    
    def test_trailing_stop_long(self):
        """Test trailing stop for long position"""
        plan = ExitPlan(
            position_id='test_pos_1',
            symbol='BTC/USDT',
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=55000.0,
            invalidation_conditions=[],
            trailing_stop_pct=0.02,  # 2% trailing stop
            is_short=False
        )
        
        self.monitor.add_exit_plan(plan)
        
        self.monitor.update_trailing_stop('test_pos_1', 52000.0)
        
        updated_plan = self.monitor.get_exit_plan('test_pos_1')
        self.assertGreater(updated_plan.stop_loss, 49000.0)
        self.assertEqual(updated_plan.highest_price, 52000.0)
    
    def test_exit_statistics(self):
        """Test exit statistics tracking"""
        self.monitor.record_exit('pos1', ExitReason.STOP_LOSS, 49000.0, -100.0, 'SL hit')
        self.monitor.record_exit('pos2', ExitReason.TAKE_PROFIT, 52000.0, 200.0, 'TP hit')
        self.monitor.record_exit('pos3', ExitReason.TAKE_PROFIT, 53000.0, 300.0, 'TP hit')
        
        stats = self.monitor.get_exit_statistics()
        
        self.assertEqual(stats['total_exits'], 3)
        self.assertEqual(stats['stop_loss_exits'], 1)
        self.assertEqual(stats['take_profit_exits'], 2)
        self.assertAlmostEqual(stats['take_profit_pct'], 66.67, places=1)


class TestEnhancedRiskManager(unittest.TestCase):
    """Test EnhancedRiskManager functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.risk_manager = EnhancedRiskManager(
            initial_capital=10000.0,
            max_daily_loss_pct=5.0,
            max_daily_trades=20,
            max_position_size_pct=10.0,
            min_position_size_pct=1.0
        )
    
    def test_initial_state(self):
        """Test initial state"""
        self.assertEqual(self.risk_manager.current_capital, 10000.0)
        self.assertTrue(self.risk_manager.can_trade_today())
    
    def test_position_size_calculation(self):
        """Test position size calculation with confidence scaling"""
        size_high = self.risk_manager.calculate_position_size(0.9, 50000.0)
        
        size_low = self.risk_manager.calculate_position_size(0.7, 50000.0)
        
        self.assertGreater(size_high, size_low)
    
    def test_daily_loss_limit(self):
        """Test daily loss limit enforcement"""
        self.risk_manager.record_trade_result(-600.0, -6.0)
        
        self.assertFalse(self.risk_manager.can_trade_today())
    
    def test_daily_trade_limit(self):
        """Test daily trade limit enforcement"""
        for i in range(20):
            self.risk_manager.record_trade_result(10.0, 1.0)
        
        self.assertFalse(self.risk_manager.can_trade_today())
    
    def test_symbol_exposure_limit(self):
        """Test per-symbol exposure limit"""
        self.risk_manager.record_position_opened('BTC/USDT', 1500.0)
        
        self.assertTrue(self.risk_manager.can_open_position('BTC/USDT'))
        
        self.risk_manager.record_position_opened('BTC/USDT', 1000.0)
        
        self.assertFalse(self.risk_manager.can_open_position('BTC/USDT'))
        
    
    def test_statistics(self):
        """Test statistics reporting"""
        self.risk_manager.record_trade_result(100.0, 1.0)
        self.risk_manager.record_trade_result(-50.0, -0.5)
        self.risk_manager.record_trade_result(150.0, 1.5)
        
        stats = self.risk_manager.get_statistics()
        
        self.assertEqual(stats['total_trades'], 3)
        self.assertEqual(stats['daily_trades'], 3)
        self.assertEqual(stats['daily_winning_trades'], 2)
        self.assertEqual(stats['daily_losing_trades'], 1)
        self.assertAlmostEqual(stats['daily_pnl'], 200.0)
        self.assertAlmostEqual(stats['current_capital'], 10200.0)


class MockStrategy(BaseStrategy):
    """Mock strategy for testing"""
    
    def __init__(self, name: str, signal_action: SignalAction, confidence: float):
        super().__init__(name, {})
        self.signal_action = signal_action
        self.signal_confidence = confidence
        self.symbol = 'BTC/USDT'
    
    def initialize(self) -> None:
        """Initialize mock strategy"""
        self.is_initialized = True
    
    def on_data(self, market_data, indicators) -> None:
        """Process data (no-op for mock)"""
        pass
    
    def get_parameters(self):
        """Get parameters"""
        return {'signal_action': self.signal_action.value, 'confidence': self.signal_confidence}
    
    def generate_signal(self, market_data, indicators, current_position=None):
        return TradingSignal(
            action=self.signal_action,
            symbol=self.symbol,
            confidence=self.signal_confidence,
            price=market_data.get('price', 50000.0),
            stop_loss=market_data.get('price', 50000.0) * 0.95,
            take_profit=market_data.get('price', 50000.0) * 1.05,
            timestamp=datetime.now(),
            metadata={
                'strategy': self.name,
                'justification': 'Test signal',
                'invalidation_conditions': []
            }
        )


class TestAutonomousDecisionEngine(unittest.TestCase):
    """Test AutonomousDecisionEngine functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.exit_monitor = ExitPlanMonitor()
        self.risk_manager = EnhancedRiskManager(initial_capital=10000.0)
        
        self.strategies = [
            MockStrategy('TestStrategy1', SignalAction.BUY, 0.8),
            MockStrategy('TestStrategy2', SignalAction.HOLD, 0.5),
        ]
        
        self.engine = AutonomousDecisionEngine(
            strategies=self.strategies,
            exit_monitor=self.exit_monitor,
            risk_manager=self.risk_manager,
            loop_interval_seconds=1,  # Short interval for testing
            max_open_positions=5,
            min_confidence_threshold=0.7,
            enable_trading=False  # Simulation mode
        )
    
    def test_initialization(self):
        """Test engine initialization"""
        self.assertFalse(self.engine.is_running)
        self.assertEqual(len(self.engine.strategies), 2)
        self.assertEqual(self.engine.max_open_positions, 5)
    
    def test_signal_selection(self):
        """Test best signal selection"""
        signals = [
            TradingSignal(
                action=SignalAction.BUY,
                symbol='BTC/USDT',
                confidence=0.8,
                price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                timestamp=datetime.now(),
                metadata={'strategy': 'Strategy1'}
            ),
            TradingSignal(
                action=SignalAction.BUY,
                symbol='ETH/USDT',
                confidence=0.9,
                price=3000.0,
                stop_loss=2900.0,
                take_profit=3100.0,
                timestamp=datetime.now(),
                metadata={'strategy': 'Strategy2'}
            ),
        ]
        
        best_signal = self.engine._select_best_signal(signals)
        
        self.assertIsNotNone(best_signal)
        self.assertEqual(best_signal.confidence, 0.9)
        self.assertEqual(best_signal.symbol, 'ETH/USDT')
    
    def test_signal_filtering_by_confidence(self):
        """Test signal filtering by minimum confidence"""
        signals = [
            TradingSignal(
                action=SignalAction.BUY,
                symbol='BTC/USDT',
                confidence=0.6,  # Below threshold
                price=50000.0,
                stop_loss=49000.0,
                take_profit=52000.0,
                timestamp=datetime.now(),
                metadata={'strategy': 'Strategy1'}
            ),
        ]
        
        best_signal = self.engine._select_best_signal(signals)
        
        self.assertIsNone(best_signal)
    
    def test_statistics(self):
        """Test engine statistics"""
        stats = self.engine.get_statistics()
        
        self.assertFalse(stats['is_running'])
        self.assertEqual(stats['total_loops'], 0)
        self.assertEqual(stats['open_positions'], 0)
        self.assertEqual(stats['max_open_positions'], 5)


def run_async_test(coro):
    """Helper to run async tests"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


if __name__ == '__main__':
    unittest.main()
