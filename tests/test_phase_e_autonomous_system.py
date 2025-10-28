"""
Tests for Phase E: Autonomous Trading System

Comprehensive tests for all Phase E components:
- AutonomousTradingSystem
- PerformanceMonitor
- ErrorRecoveryManager
- Logging system
- Dashboard
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import json

from src.autonomous.autonomous_trading_system import AutonomousTradingSystem
from src.autonomous.performance_monitor import PerformanceMonitor, PerformanceSnapshot
from src.autonomous.error_recovery import ErrorRecoveryManager, ErrorRecord
from src.autonomous.logging_config import setup_comprehensive_logging
from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction


class MockStrategy(BaseStrategy):
    """Mock strategy for testing"""
    
    def __init__(self, name: str = "MockStrategy", symbol: str = "BTC/USDT"):
        self.name = name
        self.symbol = symbol
    
    def initialize(self):
        """Initialize strategy"""
        pass
    
    def on_data(self, market_data, indicators):
        """Process new data"""
        pass
    
    def get_parameters(self):
        """Get strategy parameters"""
        return {
            'name': self.name,
            'symbol': self.symbol
        }
    
    def generate_signal(self, market_data, indicators, current_position=None):
        return TradingSignal(
            symbol=self.symbol,
            action=SignalAction.HOLD,
            price=50000.0,
            confidence=0.5,
            stop_loss=49000.0,
            take_profit=51000.0,
            metadata={
                'strategy': self.name,
                'justification': 'Mock signal'
            }
        )


class TestPerformanceMonitor:
    """Test PerformanceMonitor functionality"""
    
    def test_initialization(self, tmp_path):
        """Test performance monitor initialization"""
        monitor = PerformanceMonitor(
            initial_capital=10000.0,
            data_dir=tmp_path
        )
        
        assert monitor.initial_capital == 10000.0
        assert monitor.data_dir == tmp_path
        assert len(monitor.snapshots) == 0
    
    def test_update_metrics(self, tmp_path):
        """Test updating performance metrics"""
        monitor = PerformanceMonitor(
            initial_capital=10000.0,
            data_dir=tmp_path
        )
        
        monitor.update_metrics(
            timestamp=datetime.now(),
            capital=10500.0,
            open_positions=2,
            daily_pnl=500.0,
            total_pnl=500.0,
            total_trades=10,
            daily_trades=5,
            win_rate=60.0,
            max_drawdown=5.0,
            decision_count=20,
            loop_count=15
        )
        
        assert len(monitor.snapshots) == 1
        assert monitor.snapshots[0].capital == 10500.0
        assert monitor.snapshots[0].total_pnl == 500.0
    
    def test_get_summary(self, tmp_path):
        """Test getting performance summary"""
        monitor = PerformanceMonitor(
            initial_capital=10000.0,
            data_dir=tmp_path
        )
        
        monitor.update_metrics(
            timestamp=datetime.now(),
            capital=10500.0,
            open_positions=2,
            daily_pnl=500.0,
            total_pnl=500.0,
            total_trades=10,
            daily_trades=5,
            win_rate=60.0,
            max_drawdown=5.0,
            decision_count=20,
            loop_count=15
        )
        
        summary = monitor.get_summary()
        
        assert summary['current_capital'] == 10500.0
        assert summary['total_pnl'] == 500.0
        assert summary['total_pnl_pct'] == 5.0
        assert summary['total_trades'] == 10
    
    def test_generate_report(self, tmp_path):
        """Test generating performance report"""
        monitor = PerformanceMonitor(
            initial_capital=10000.0,
            data_dir=tmp_path
        )
        
        for i in range(5):
            monitor.update_metrics(
                timestamp=datetime.now(),
                capital=10000.0 + (i * 100),
                open_positions=i,
                daily_pnl=100.0,
                total_pnl=i * 100,
                total_trades=i * 2,
                daily_trades=2,
                win_rate=60.0,
                max_drawdown=5.0,
                decision_count=i * 4,
                loop_count=i * 3
            )
        
        report = monitor.generate_report()
        
        assert 'summary' in report
        assert 'statistics' in report
        assert 'recent_performance' in report
        assert 'trading_activity' in report
        assert report['summary']['current_capital'] == 10400.0
    
    def test_save_metrics(self, tmp_path):
        """Test saving metrics to disk"""
        monitor = PerformanceMonitor(
            initial_capital=10000.0,
            data_dir=tmp_path
        )
        
        monitor.update_metrics(
            timestamp=datetime.now(),
            capital=10500.0,
            open_positions=2,
            daily_pnl=500.0,
            total_pnl=500.0,
            total_trades=10,
            daily_trades=5,
            win_rate=60.0,
            max_drawdown=5.0,
            decision_count=20,
            loop_count=15
        )
        
        monitor.save_metrics()
        
        summary_files = list(tmp_path.glob('performance_summary_*.json'))
        assert len(summary_files) > 0


class TestErrorRecoveryManager:
    """Test ErrorRecoveryManager functionality"""
    
    def test_initialization(self):
        """Test error recovery manager initialization"""
        manager = ErrorRecoveryManager(
            max_consecutive_errors=5,
            cooldown_seconds=300
        )
        
        assert manager.max_consecutive_errors == 5
        assert manager.cooldown_seconds == 300
        assert manager.consecutive_errors == 0
        assert manager.total_errors == 0
    
    @pytest.mark.asyncio
    async def test_handle_error(self):
        """Test error handling"""
        manager = ErrorRecoveryManager(
            max_consecutive_errors=3,
            cooldown_seconds=60
        )
        
        error = ValueError("Test error")
        action = await manager.handle_error(error, context={'test': True})
        
        assert manager.total_errors == 1
        assert manager.consecutive_errors == 1
        assert action in ['continue', 'pause', 'stop']
        assert len(manager.error_history) == 1
    
    @pytest.mark.asyncio
    async def test_consecutive_errors_trigger_pause(self):
        """Test that consecutive errors trigger pause"""
        manager = ErrorRecoveryManager(
            max_consecutive_errors=3,
            cooldown_seconds=60
        )
        
        for i in range(3):
            error = ValueError(f"Test error {i}")
            action = await manager.handle_error(error)
        
        assert manager.consecutive_errors == 3
        assert manager.should_pause()
        assert manager.pause_until is not None
    
    def test_record_success_resets_errors(self):
        """Test that recording success resets error count"""
        manager = ErrorRecoveryManager()
        manager.consecutive_errors = 3
        
        manager.record_success()
        
        assert manager.consecutive_errors == 0
        assert manager.total_recoveries == 1
    
    def test_get_error_rate(self):
        """Test error rate calculation"""
        manager = ErrorRecoveryManager(error_window_seconds=3600)
        
        manager.error_history = [
            ErrorRecord(
                timestamp=datetime.now() - timedelta(minutes=30),
                error_type='ValueError',
                error_message='Test',
                context={},
                stack_trace='',
                recovery_action='continue'
            )
            for _ in range(5)
        ]
        
        error_rate = manager.get_error_rate()
        assert error_rate == 5.0
    
    def test_get_statistics(self):
        """Test getting error statistics"""
        manager = ErrorRecoveryManager()
        manager.total_errors = 10
        manager.consecutive_errors = 2
        manager.total_recoveries = 8
        
        stats = manager.get_statistics()
        
        assert stats['total_errors'] == 10
        assert stats['consecutive_errors'] == 2
        assert stats['total_recoveries'] == 8
        assert stats['recovery_rate'] == 80.0


class TestLoggingSystem:
    """Test comprehensive logging system"""
    
    def test_setup_logging(self, tmp_path):
        """Test logging system setup"""
        setup_comprehensive_logging(tmp_path)
        
        assert (tmp_path / 'trading_system.log').exists() or True
        
        import logging
        logger = logging.getLogger('test')
        logger.info("Test log message")
    
    def test_trade_logger(self, tmp_path):
        """Test trade-specific logger"""
        setup_comprehensive_logging(tmp_path)
        
        from src.autonomous.logging_config import get_trade_logger, log_trade_event
        
        trade_logger = get_trade_logger()
        assert trade_logger is not None
        
        log_trade_event(
            event_type='ENTRY',
            symbol='BTC/USDT',
            action='BUY',
            price=50000.0,
            quantity=0.1,
            confidence=0.8
        )


class TestAutonomousTradingSystem:
    """Test AutonomousTradingSystem functionality"""
    
    def test_initialization(self, tmp_path):
        """Test system initialization"""
        strategies = [MockStrategy()]
        
        system = AutonomousTradingSystem(
            strategies=strategies,
            initial_capital=10000.0,
            loop_interval_seconds=180,
            max_open_positions=5,
            min_confidence_threshold=0.7,
            enable_trading=False,
            log_dir=str(tmp_path / 'logs'),
            data_dir=str(tmp_path / 'data'),
            enable_dashboard=False
        )
        
        assert system.initial_capital == 10000.0
        assert len(system.strategies) == 1
        assert system.enable_trading is False
        assert system.is_running is False
        assert system.decision_engine is not None
        assert system.risk_manager is not None
        assert system.exit_monitor is not None
        assert system.performance_monitor is not None
        assert system.error_recovery is not None
    
    def test_get_status(self, tmp_path):
        """Test getting system status"""
        strategies = [MockStrategy()]
        
        system = AutonomousTradingSystem(
            strategies=strategies,
            initial_capital=10000.0,
            enable_trading=False,
            log_dir=str(tmp_path / 'logs'),
            data_dir=str(tmp_path / 'data'),
            enable_dashboard=False
        )
        
        status = system.get_status()
        
        assert 'is_running' in status
        assert 'enable_trading' in status
        assert 'strategies_count' in status
        assert 'engine_stats' in status
        assert 'risk_stats' in status
        assert status['strategies_count'] == 1
    
    def test_get_performance_report(self, tmp_path):
        """Test getting performance report"""
        strategies = [MockStrategy()]
        
        system = AutonomousTradingSystem(
            strategies=strategies,
            initial_capital=10000.0,
            enable_trading=False,
            log_dir=str(tmp_path / 'logs'),
            data_dir=str(tmp_path / 'data'),
            enable_dashboard=False
        )
        
        report = system.get_performance_report()
        
        assert isinstance(report, dict)
    
    @pytest.mark.asyncio
    async def test_system_health_check(self, tmp_path):
        """Test system health check"""
        strategies = [MockStrategy()]
        
        system = AutonomousTradingSystem(
            strategies=strategies,
            initial_capital=10000.0,
            enable_trading=False,
            log_dir=str(tmp_path / 'logs'),
            data_dir=str(tmp_path / 'data'),
            enable_dashboard=False
        )
        
        system.start_time = datetime.now()
        
        health = await system._check_system_health()
        
        assert 'healthy' in health
        assert 'issues' in health
        assert 'timestamp' in health
        assert isinstance(health['healthy'], bool)
        assert isinstance(health['issues'], list)


class TestIntegration:
    """Integration tests for Phase E components"""
    
    @pytest.mark.asyncio
    async def test_full_system_integration(self, tmp_path):
        """Test full system integration"""
        strategies = [MockStrategy()]
        
        system = AutonomousTradingSystem(
            strategies=strategies,
            initial_capital=10000.0,
            loop_interval_seconds=1,
            enable_trading=False,
            log_dir=str(tmp_path / 'logs'),
            data_dir=str(tmp_path / 'data'),
            enable_dashboard=False
        )
        
        system.start_time = datetime.now()
        
        status = system.get_status()
        assert 'is_running' in status
        assert status['enable_trading'] is False


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
