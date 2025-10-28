"""
Unit tests for risk management module
"""

import pytest
from datetime import datetime
from src.risk.position_sizing import PositionSizer
from src.risk.risk_checks import RiskValidator, RiskCheckResult
from src.risk.portfolio_monitor import PortfolioMonitor


class TestPositionSizer:
    """Test position sizing calculations"""
    
    @pytest.fixture
    def sizer(self):
        """Create position sizer instance"""
        config = {
            'default_risk_pct': 0.01,
            'max_position_pct': 0.1,
            'min_position_size': 0.001,
            'use_kelly': False
        }
        return PositionSizer(config)
    
    def test_risk_based_sizing(self, sizer):
        """Test risk-based position sizing"""
        result = sizer.calculate_position_size(
            account_balance=10000.0,
            entry_price=50000.0,
            stop_loss=49000.0,
            leverage=1.0
        )
        
        assert result['position_size'] > 0
        assert result['method'] == 'risk_based'
        assert result['risk_amount'] == 100.0  # 1% of 10000
        assert result['margin_required'] > 0
    
    def test_fixed_percentage_sizing(self, sizer):
        """Test fixed percentage sizing"""
        result = sizer.calculate_position_size(
            account_balance=10000.0,
            entry_price=50000.0,
            leverage=1.0
        )
        
        assert result['position_size'] > 0
        assert result['method'] == 'fixed_percentage'
        assert result['position_value'] <= 1000.0  # 10% max
    
    def test_volatility_adjusted_sizing(self, sizer):
        """Test volatility-adjusted sizing"""
        result = sizer.calculate_position_size(
            account_balance=10000.0,
            entry_price=50000.0,
            atr=500.0,
            leverage=1.0
        )
        
        assert result['position_size'] > 0
        assert 'volatility_adjusted' in result['method']
    
    def test_leverage_adjustment(self, sizer):
        """Test leverage adjustment in position sizing"""
        result_1x = sizer.calculate_position_size(
            account_balance=10000.0,
            entry_price=50000.0,
            stop_loss=49000.0,
            leverage=1.0
        )
        
        result_2x = sizer.calculate_position_size(
            account_balance=10000.0,
            entry_price=50000.0,
            stop_loss=49000.0,
            leverage=2.0
        )
        
        assert result_2x['position_size'] > result_1x['position_size']
    
    def test_minimum_position_size(self, sizer):
        """Test minimum position size constraint"""
        result = sizer.calculate_position_size(
            account_balance=10.0,  # Very small balance
            entry_price=50000.0,
            stop_loss=49000.0,
            leverage=1.0
        )
        
        assert result['position_size'] == 0.0
    
    def test_calculate_stop_loss(self, sizer):
        """Test stop-loss calculation"""
        stop_loss = sizer.calculate_stop_loss(
            entry_price=50000.0,
            side='BUY',
            risk_pct=0.02
        )
        
        assert stop_loss < 50000.0  # Stop should be below entry for BUY
        assert stop_loss == 49000.0  # 2% below entry
    
    def test_calculate_take_profit(self, sizer):
        """Test take-profit calculation"""
        take_profit = sizer.calculate_take_profit(
            entry_price=50000.0,
            stop_loss=49000.0,
            side='BUY',
            risk_reward_ratio=2.0
        )
        
        assert take_profit > 50000.0  # TP should be above entry for BUY
        assert take_profit == 52000.0  # 2:1 risk-reward


class TestRiskValidator:
    """Test risk validation checks"""
    
    @pytest.fixture
    def validator(self):
        """Create risk validator instance"""
        config = {
            'max_position_risk_pct': 0.02,
            'min_risk_reward_ratio': 1.5,
            'max_single_asset_exposure': 0.3,
            'max_strategy_exposure': 0.4,
            'max_total_exposure': 0.8,
            'max_leverage': 10.0,
            'max_daily_drawdown_pct': 0.05,
            'max_total_drawdown_pct': 0.15,
            'fat_finger_threshold': 0.5,
            'require_stop_loss': True,
            'min_stop_loss_distance_pct': 0.005,
            'max_stop_loss_distance_pct': 0.1
        }
        return RiskValidator(config)
    
    def test_valid_trade(self, validator):
        """Test validation of a valid trade"""
        trade_params = {
            'symbol': 'BTC/USDT',
            'side': 'BUY',
            'quantity': 0.02,  # Smaller position: 0.02 * 50000 = 1000 (10% of account)
            'price': 50000.0,
            'stop_loss': 49000.0,
            'take_profit': 52000.0,
            'leverage': 1.0,
            'strategy': 'rsi'
        }
        
        passed, results = validator.validate_trade(
            trade_params=trade_params,
            account_balance=10000.0,
            current_positions=[],
            portfolio_state={'daily_drawdown_pct': 0.0, 'total_drawdown_pct': 0.0}
        )
        
        assert passed is True
        assert len(results) > 0
    
    def test_insufficient_balance(self, validator):
        """Test rejection due to insufficient balance"""
        trade_params = {
            'symbol': 'BTC/USDT',
            'side': 'BUY',
            'quantity': 1.0,  # Too large
            'price': 50000.0,
            'stop_loss': 49000.0,
            'leverage': 1.0
        }
        
        passed, results = validator.validate_trade(
            trade_params=trade_params,
            account_balance=10000.0,
            current_positions=[],
            portfolio_state={'daily_drawdown_pct': 0.0, 'total_drawdown_pct': 0.0}
        )
        
        assert passed is False
        errors = [r for r in results if not r.passed and r.severity == "ERROR"]
        assert any('balance' in r.message.lower() for r in errors)
    
    def test_missing_stop_loss(self, validator):
        """Test rejection due to missing stop-loss"""
        trade_params = {
            'symbol': 'BTC/USDT',
            'side': 'BUY',
            'quantity': 0.1,
            'price': 50000.0,
            'stop_loss': None,  # Missing
            'leverage': 1.0
        }
        
        passed, results = validator.validate_trade(
            trade_params=trade_params,
            account_balance=10000.0,
            current_positions=[],
            portfolio_state={'daily_drawdown_pct': 0.0, 'total_drawdown_pct': 0.0}
        )
        
        assert passed is False
        errors = [r for r in results if not r.passed and r.severity == "ERROR"]
        assert any('stop' in r.message.lower() for r in errors)
    
    def test_excessive_leverage(self, validator):
        """Test rejection due to excessive leverage"""
        trade_params = {
            'symbol': 'BTC/USDT',
            'side': 'BUY',
            'quantity': 0.1,
            'price': 50000.0,
            'stop_loss': 49000.0,
            'leverage': 20.0  # Too high
        }
        
        passed, results = validator.validate_trade(
            trade_params=trade_params,
            account_balance=10000.0,
            current_positions=[],
            portfolio_state={'daily_drawdown_pct': 0.0, 'total_drawdown_pct': 0.0}
        )
        
        assert passed is False
        errors = [r for r in results if not r.passed and r.severity == "ERROR"]
        assert any('leverage' in r.message.lower() for r in errors)
    
    def test_drawdown_limit_exceeded(self, validator):
        """Test rejection due to drawdown limit"""
        trade_params = {
            'symbol': 'BTC/USDT',
            'side': 'BUY',
            'quantity': 0.1,
            'price': 50000.0,
            'stop_loss': 49000.0,
            'leverage': 1.0
        }
        
        passed, results = validator.validate_trade(
            trade_params=trade_params,
            account_balance=10000.0,
            current_positions=[],
            portfolio_state={'daily_drawdown_pct': 0.06, 'total_drawdown_pct': 0.0}  # Exceeds 5%
        )
        
        assert passed is False
        errors = [r for r in results if not r.passed and r.severity == "ERROR"]
        assert any('drawdown' in r.message.lower() for r in errors)
    
    def test_fat_finger_detection(self, validator):
        """Test fat finger detection"""
        trade_params = {
            'symbol': 'BTC/USDT',
            'side': 'BUY',
            'quantity': 0.15,  # 75% of account - too large
            'price': 50000.0,
            'stop_loss': 49000.0,
            'leverage': 1.0
        }
        
        passed, results = validator.validate_trade(
            trade_params=trade_params,
            account_balance=10000.0,
            current_positions=[],
            portfolio_state={'daily_drawdown_pct': 0.0, 'total_drawdown_pct': 0.0}
        )
        
        assert passed is False
        errors = [r for r in results if not r.passed and r.severity == "ERROR"]
        assert any('fat' in r.message.lower() or 'large' in r.message.lower() for r in errors)
    
    def test_risk_summary(self, validator):
        """Test risk check summary generation"""
        trade_params = {
            'symbol': 'BTC/USDT',
            'side': 'BUY',
            'quantity': 0.1,
            'price': 50000.0,
            'stop_loss': 49000.0,
            'leverage': 1.0
        }
        
        passed, results = validator.validate_trade(
            trade_params=trade_params,
            account_balance=10000.0,
            current_positions=[],
            portfolio_state={'daily_drawdown_pct': 0.0, 'total_drawdown_pct': 0.0}
        )
        
        summary = validator.get_risk_summary(results)
        
        assert 'passed' in summary
        assert 'total_checks' in summary
        assert 'errors' in summary
        assert 'warnings' in summary


class TestPortfolioMonitor:
    """Test portfolio monitoring"""
    
    @pytest.fixture
    def monitor(self):
        """Create portfolio monitor instance"""
        config = {
            'max_daily_loss_pct': 0.05,
            'max_total_loss_pct': 0.15,
            'max_consecutive_losses': 5,
            'max_history_size': 1000
        }
        return PortfolioMonitor(initial_balance=10000.0, config=config)
    
    def test_initialization(self, monitor):
        """Test monitor initialization"""
        assert monitor.initial_balance == 10000.0
        assert monitor.current_balance == 10000.0
        assert monitor.peak_balance == 10000.0
        assert monitor.realized_pnl == 0.0
    
    def test_update_with_no_positions(self, monitor):
        """Test update with no open positions"""
        snapshot = monitor.update(
            current_positions=[],
            market_prices={},
            cash_balance=10000.0
        )
        
        assert snapshot.total_value == 10000.0
        assert snapshot.cash_balance == 10000.0
        assert snapshot.positions_value == 0.0
        assert snapshot.num_positions == 0
    
    def test_update_with_positions(self, monitor):
        """Test update with open positions"""
        positions = [
            {
                'symbol': 'BTC/USDT',
                'quantity': 0.1,
                'entry_price': 50000.0,
                'leverage': 1.0
            }
        ]
        
        market_prices = {
            'BTC/USDT': 51000.0  # Profit
        }
        
        snapshot = monitor.update(
            current_positions=positions,
            market_prices=market_prices,
            cash_balance=5000.0
        )
        
        assert snapshot.num_positions == 1
        assert snapshot.positions_value > 0
        assert snapshot.unrealized_pnl > 0  # Profit
    
    def test_record_winning_trade(self, monitor):
        """Test recording a winning trade"""
        trade = {
            'pnl': 100.0,
            'fees': 5.0
        }
        
        monitor.record_trade(trade)
        
        assert monitor.realized_pnl == 100.0
        assert monitor.total_fees_paid == 5.0
        assert monitor.winning_trades == 1
        assert monitor.consecutive_wins == 1
        assert monitor.consecutive_losses == 0
    
    def test_record_losing_trade(self, monitor):
        """Test recording a losing trade"""
        trade = {
            'pnl': -50.0,
            'fees': 5.0
        }
        
        monitor.record_trade(trade)
        
        assert monitor.realized_pnl == -50.0
        assert monitor.losing_trades == 1
        assert monitor.consecutive_losses == 1
        assert monitor.consecutive_wins == 0
    
    def test_circuit_breaker_daily_loss(self, monitor):
        """Test circuit breaker on daily loss"""
        snapshot = monitor.update(
            current_positions=[],
            market_prices={},
            cash_balance=9000.0  # 10% loss
        )
        
        assert monitor.circuit_breaker_triggered is True
        assert 'daily' in monitor.circuit_breaker_reason.lower()
    
    def test_circuit_breaker_consecutive_losses(self, monitor):
        """Test circuit breaker on consecutive losses"""
        for _ in range(5):
            monitor.record_trade({'pnl': -10.0, 'fees': 1.0})
        
        monitor.update(
            current_positions=[],
            market_prices={},
            cash_balance=9950.0
        )
        
        assert monitor.circuit_breaker_triggered is True
        assert 'consecutive' in monitor.circuit_breaker_reason.lower()
    
    def test_reset_circuit_breaker(self, monitor):
        """Test resetting circuit breaker"""
        monitor.circuit_breaker_triggered = True
        monitor.circuit_breaker_reason = "Test"
        
        monitor.reset_circuit_breaker()
        
        assert monitor.circuit_breaker_triggered is False
        assert monitor.circuit_breaker_reason is None
    
    def test_performance_metrics(self, monitor):
        """Test performance metrics calculation"""
        monitor.record_trade({'pnl': 100.0, 'fees': 5.0})
        monitor.record_trade({'pnl': -50.0, 'fees': 5.0})
        monitor.record_trade({'pnl': 75.0, 'fees': 5.0})
        
        monitor.update(
            current_positions=[],
            market_prices={},
            cash_balance=10125.0
        )
        
        metrics = monitor.get_performance_metrics()
        
        assert 'total_return_pct' in metrics
        assert 'win_rate_pct' in metrics
        assert 'total_trades' in metrics
        assert metrics['total_trades'] == 3
        assert metrics['winning_trades'] == 2
        assert metrics['losing_trades'] == 1
    
    def test_equity_curve(self, monitor):
        """Test equity curve generation"""
        for i in range(5):
            monitor.update(
                current_positions=[],
                market_prices={},
                cash_balance=10000.0 + (i * 100)
            )
        
        curve = monitor.get_equity_curve('all')
        
        assert len(curve) == 5
        assert all('timestamp' in point for point in curve)
        assert all('total_value' in point for point in curve)
    
    def test_reset(self, monitor):
        """Test monitor reset"""
        monitor.record_trade({'pnl': 100.0, 'fees': 5.0})
        monitor.update(
            current_positions=[],
            market_prices={},
            cash_balance=10100.0
        )
        
        monitor.reset()
        
        assert monitor.current_balance == 10000.0
        assert monitor.realized_pnl == 0.0
        assert monitor.total_trades == 0
        assert len(monitor.snapshots) == 0
