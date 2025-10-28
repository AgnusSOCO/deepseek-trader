"""
Unit tests for Leverage Manager
"""

import pytest
from src.execution.leverage_manager import (
    LeverageManager,
    LeverageConfig,
    MarginStatus
)


class TestLeverageManager:
    """Test suite for LeverageManager"""
    
    @pytest.fixture
    def manager(self):
        """Create leverage manager instance"""
        config = LeverageConfig(
            absolute_max=10.0,
            scalping_max=5.0,
            momentum_max=5.0,
            mean_reversion_max=3.0,
            margin_alert_threshold=0.70,
            margin_reduce_threshold=0.85
        )
        return LeverageManager(config)
    
    def test_initialization(self, manager):
        """Test manager initialization"""
        assert manager.config.absolute_max == 10.0
        assert manager.config.scalping_max == 5.0
        assert manager.config.momentum_max == 5.0
        assert manager.config.mean_reversion_max == 3.0
        assert manager.current_drawdown_pct == 0.0
    
    def test_calculate_leverage_scalping(self, manager):
        """Test leverage calculation for scalping strategy"""
        leverage = manager.calculate_leverage(
            strategy_type='scalping',
            confidence=0.8,
            volatility_pct=1.5,
            drawdown_pct=2.0
        )
        
        assert leverage >= 1.0
        assert leverage <= manager.config.scalping_max
    
    def test_calculate_leverage_momentum(self, manager):
        """Test leverage calculation for momentum strategy"""
        leverage = manager.calculate_leverage(
            strategy_type='momentum',
            confidence=0.8,
            volatility_pct=1.5,
            drawdown_pct=2.0
        )
        
        assert leverage >= 1.0
        assert leverage <= manager.config.momentum_max
    
    def test_calculate_leverage_mean_reversion(self, manager):
        """Test leverage calculation for mean reversion strategy"""
        leverage = manager.calculate_leverage(
            strategy_type='mean_reversion',
            confidence=0.8,
            volatility_pct=1.5,
            drawdown_pct=2.0
        )
        
        assert leverage >= 1.0
        assert leverage <= manager.config.mean_reversion_max
    
    def test_calculate_leverage_high_confidence(self, manager):
        """Test leverage calculation with high confidence"""
        leverage = manager.calculate_leverage(
            strategy_type='momentum',
            confidence=0.95,
            volatility_pct=1.0,
            drawdown_pct=0.0
        )
        
        assert leverage > 2.0
    
    def test_calculate_leverage_low_confidence(self, manager):
        """Test leverage calculation with low confidence"""
        leverage = manager.calculate_leverage(
            strategy_type='momentum',
            confidence=0.3,
            volatility_pct=1.0,
            drawdown_pct=0.0
        )
        
        assert leverage < 3.0
    
    def test_calculate_leverage_high_volatility(self, manager):
        """Test leverage calculation with high volatility"""
        leverage = manager.calculate_leverage(
            strategy_type='momentum',
            confidence=0.8,
            volatility_pct=5.0,
            drawdown_pct=0.0
        )
        
        assert leverage < 3.0
    
    def test_calculate_leverage_high_drawdown(self, manager):
        """Test leverage calculation with high drawdown"""
        leverage = manager.calculate_leverage(
            strategy_type='momentum',
            confidence=0.8,
            volatility_pct=1.0,
            drawdown_pct=10.0
        )
        
        assert leverage < 2.0
    
    def test_calculate_leverage_absolute_max(self, manager):
        """Test leverage never exceeds absolute max"""
        leverage = manager.calculate_leverage(
            strategy_type='scalping',
            confidence=1.0,
            volatility_pct=0.5,
            drawdown_pct=0.0,
            base_leverage=15.0  # Try to exceed max
        )
        
        assert leverage <= manager.config.absolute_max
    
    def test_calculate_leverage_minimum_one(self, manager):
        """Test leverage never goes below 1x"""
        leverage = manager.calculate_leverage(
            strategy_type='mean_reversion',
            confidence=0.1,
            volatility_pct=10.0,
            drawdown_pct=15.0
        )
        
        assert leverage >= 1.0
    
    def test_calculate_margin_status(self, manager):
        """Test margin status calculation"""
        positions = [
            {'id': 'pos1', 'size': 1.0, 'price': 50000.0, 'unrealized_pnl': 500.0},
            {'id': 'pos2', 'size': 0.5, 'price': 50000.0, 'unrealized_pnl': -200.0}
        ]
        leverage_by_position = {'pos1': 3.0, 'pos2': 2.0}
        
        status = manager.calculate_margin_status(
            account_balance=10000.0,
            positions=positions,
            leverage_by_position=leverage_by_position
        )
        
        assert isinstance(status, MarginStatus)
        assert status.total_margin > 0
        assert status.used_margin > 0
        assert status.available_margin >= 0
        assert 0 <= status.margin_ratio <= 1.0
        assert status.unrealized_pnl == 300.0  # 500 - 200
    
    def test_margin_status_alert_level(self, manager):
        """Test margin status alert level detection"""
        positions = [
            {'id': 'pos1', 'size': 10.0, 'price': 50000.0, 'unrealized_pnl': 0.0}
        ]
        leverage_by_position = {'pos1': 2.0}
        
        status = manager.calculate_margin_status(
            account_balance=300000.0,
            positions=positions,
            leverage_by_position=leverage_by_position
        )
        
        assert status.is_alert_level
    
    def test_margin_status_critical_level(self, manager):
        """Test margin status critical level detection"""
        positions = [
            {'id': 'pos1', 'size': 10.0, 'price': 50000.0, 'unrealized_pnl': 0.0}
        ]
        leverage_by_position = {'pos1': 2.0}
        
        status = manager.calculate_margin_status(
            account_balance=280000.0,
            positions=positions,
            leverage_by_position=leverage_by_position
        )
        
        assert status.is_critical_level
    
    def test_check_margin_requirements_approved(self, manager):
        """Test margin requirements check - approved"""
        status = MarginStatus(
            total_margin=10000.0,
            used_margin=5000.0,
            available_margin=5000.0,
            margin_ratio=0.5,
            positions_value=15000.0,
            unrealized_pnl=0.0
        )
        
        approved, reason = manager.check_margin_requirements(
            proposed_trade_value=6000.0,
            proposed_leverage=3.0,
            margin_status=status
        )
        
        assert approved is True
        assert 'met' in reason.lower()
    
    def test_check_margin_requirements_insufficient(self, manager):
        """Test margin requirements check - insufficient margin"""
        status = MarginStatus(
            total_margin=10000.0,
            used_margin=8000.0,
            available_margin=2000.0,
            margin_ratio=0.8,
            positions_value=24000.0,
            unrealized_pnl=0.0
        )
        
        approved, reason = manager.check_margin_requirements(
            proposed_trade_value=9000.0,
            proposed_leverage=3.0,
            margin_status=status
        )
        
        assert approved is False
        assert 'insufficient' in reason.lower()
    
    def test_check_margin_requirements_exceeds_threshold(self, manager):
        """Test margin requirements check - exceeds threshold"""
        status = MarginStatus(
            total_margin=10000.0,
            used_margin=7000.0,
            available_margin=3000.0,
            margin_ratio=0.7,
            positions_value=21000.0,
            unrealized_pnl=0.0
        )
        
        approved, reason = manager.check_margin_requirements(
            proposed_trade_value=6000.0,
            proposed_leverage=3.0,
            margin_status=status
        )
        
        assert approved is False
        assert 'exceed' in reason.lower()
    
    def test_check_margin_requirements_buffer(self, manager):
        """Test margin requirements check - insufficient buffer"""
        status = MarginStatus(
            total_margin=10000.0,
            used_margin=5000.0,
            available_margin=5000.0,
            margin_ratio=0.5,
            positions_value=15000.0,
            unrealized_pnl=0.0
        )
        
        approved, reason = manager.check_margin_requirements(
            proposed_trade_value=12000.0,
            proposed_leverage=3.0,
            margin_status=status
        )
        
        assert approved is False
        assert 'buffer' in reason.lower()
    
    def test_should_reduce_positions_critical(self, manager):
        """Test position reduction check - critical level"""
        status = MarginStatus(
            total_margin=10000.0,
            used_margin=8600.0,
            available_margin=1400.0,
            margin_ratio=0.86,
            positions_value=25800.0,
            unrealized_pnl=0.0
        )
        
        should_reduce = manager.should_reduce_positions(status)
        assert should_reduce is True
    
    def test_should_reduce_positions_normal(self, manager):
        """Test position reduction check - normal level"""
        status = MarginStatus(
            total_margin=10000.0,
            used_margin=5000.0,
            available_margin=5000.0,
            margin_ratio=0.5,
            positions_value=15000.0,
            unrealized_pnl=0.0
        )
        
        should_reduce = manager.should_reduce_positions(status)
        assert should_reduce is False
    
    def test_should_alert_margin_alert_level(self, manager):
        """Test margin alert check - alert level"""
        status = MarginStatus(
            total_margin=10000.0,
            used_margin=7200.0,
            available_margin=2800.0,
            margin_ratio=0.72,
            positions_value=21600.0,
            unrealized_pnl=0.0
        )
        
        should_alert = manager.should_alert_margin(status)
        assert should_alert is True
    
    def test_should_alert_margin_normal(self, manager):
        """Test margin alert check - normal level"""
        status = MarginStatus(
            total_margin=10000.0,
            used_margin=5000.0,
            available_margin=5000.0,
            margin_ratio=0.5,
            positions_value=15000.0,
            unrealized_pnl=0.0
        )
        
        should_alert = manager.should_alert_margin(status)
        assert should_alert is False
    
    def test_calculate_position_reduction(self, manager):
        """Test position reduction calculation"""
        status = MarginStatus(
            total_margin=10000.0,
            used_margin=8500.0,
            available_margin=1500.0,
            margin_ratio=0.85,
            positions_value=25500.0,
            unrealized_pnl=0.0
        )
        
        reduction_pct = manager.calculate_position_reduction(status, target_margin_ratio=0.70)
        
        assert reduction_pct > 0.0
        assert reduction_pct <= 1.0
    
    def test_calculate_position_reduction_no_reduction(self, manager):
        """Test position reduction calculation - no reduction needed"""
        status = MarginStatus(
            total_margin=10000.0,
            used_margin=5000.0,
            available_margin=5000.0,
            margin_ratio=0.5,
            positions_value=15000.0,
            unrealized_pnl=0.0
        )
        
        reduction_pct = manager.calculate_position_reduction(status, target_margin_ratio=0.70)
        
        assert reduction_pct == 0.0
    
    def test_update_drawdown_new_peak(self, manager):
        """Test drawdown update - new peak"""
        manager.update_drawdown(15000.0)
        
        assert manager.peak_portfolio_value == 15000.0
        assert manager.current_drawdown_pct == 0.0
    
    def test_update_drawdown_decline(self, manager):
        """Test drawdown update - decline from peak"""
        manager.update_drawdown(10000.0)
        manager.update_drawdown(9000.0)
        
        assert manager.peak_portfolio_value == 10000.0
        assert manager.current_drawdown_pct == 10.0  # 10% drawdown
    
    def test_update_drawdown_recovery(self, manager):
        """Test drawdown update - recovery"""
        manager.update_drawdown(10000.0)
        manager.update_drawdown(9000.0)
        manager.update_drawdown(11000.0)
        
        assert manager.peak_portfolio_value == 11000.0
        assert manager.current_drawdown_pct == 0.0
    
    def test_get_current_drawdown(self, manager):
        """Test get current drawdown"""
        manager.update_drawdown(10000.0)
        manager.update_drawdown(8500.0)
        
        drawdown = manager.get_current_drawdown()
        assert drawdown == 15.0  # 15% drawdown
    
    def test_reset_peak(self, manager):
        """Test peak reset"""
        manager.update_drawdown(10000.0)
        manager.update_drawdown(9000.0)
        
        manager.reset_peak()
        
        assert manager.peak_portfolio_value == 0.0
        assert manager.current_drawdown_pct == 0.0
    
    def test_confidence_multiplier_range(self, manager):
        """Test confidence multiplier stays in range"""
        mult_low = manager._calculate_confidence_multiplier(0.0)
        mult_high = manager._calculate_confidence_multiplier(1.0)
        
        assert mult_low == 0.5
        assert mult_high == 1.5
    
    def test_volatility_adjustment_range(self, manager):
        """Test volatility adjustment stays in range"""
        adj_low = manager._calculate_volatility_adjustment(0.5)
        adj_high = manager._calculate_volatility_adjustment(5.0)
        
        assert adj_low == 1.0
        assert adj_high == 0.5
    
    def test_drawdown_adjustment_range(self, manager):
        """Test drawdown adjustment stays in range"""
        adj_low = manager._calculate_drawdown_adjustment(0.0)
        adj_high = manager._calculate_drawdown_adjustment(15.0)
        
        assert adj_low == 1.0
        assert adj_high == 0.3
