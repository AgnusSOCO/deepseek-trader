"""
Comprehensive tests for Phase 1 Integrated Risk Management System
Tests all Phase 1 components together
"""

import pytest
from datetime import datetime, timedelta
from src.autonomous.trading_profiles import TradingProfile
from src.autonomous.phase1_risk_manager import Phase1RiskManager


class TestPhase1Integration:
    """Test Phase 1 integrated risk management system"""
    
    def test_phase1_risk_manager_initialization(self):
        """Test Phase 1 risk manager initializes correctly"""
        manager = Phase1RiskManager(
            profile=TradingProfile.BALANCED,
            initial_equity=10000.0,
            max_holding_hours=36.0
        )
        
        assert manager.profile_config.name == "Balanced"
        assert manager.trailing_stops is not None
        assert manager.partial_take_profit is not None
        assert manager.peak_drawdown is not None
        assert manager.max_holding_time is not None
        assert manager.account_drawdown is not None
    
    def test_add_position_to_all_components(self):
        """Test adding position registers with all risk components"""
        manager = Phase1RiskManager(profile=TradingProfile.BALANCED)
        
        manager.add_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size=0.1
        )
        
        assert "BTC/USDT" in manager.trailing_stops.trailing_stops
        assert "BTC/USDT" in manager.partial_take_profit.positions
        assert "BTC/USDT" in manager.peak_drawdown.positions
        assert "BTC/USDT" in manager.max_holding_time.positions
    
    def test_update_position_across_components(self):
        """Test updating position price updates all components"""
        manager = Phase1RiskManager(profile=TradingProfile.BALANCED)
        
        manager.add_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size=0.1
        )
        
        updates = manager.update_position("BTC/USDT", 54000.0)
        
        assert updates['symbol'] == "BTC/USDT"
        assert updates['current_price'] == 54000.0
        assert updates['trailing_stop_update'] is not None
    
    def test_trailing_stop_exit_recommendation(self):
        """Test trailing stop triggers exit recommendation"""
        manager = Phase1RiskManager(profile=TradingProfile.BALANCED)
        
        manager.add_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size=0.1
        )
        
        manager.update_position("BTC/USDT", 55000.0)
        manager.update_position("BTC/USDT", 51000.0)
        
        should_exit, reasons = manager.should_exit_position("BTC/USDT")
        assert should_exit
        assert any("Trailing Stop" in r for r in reasons)
    
    def test_partial_take_profit_recommendation(self):
        """Test partial take-profit triggers close recommendation"""
        manager = Phase1RiskManager(profile=TradingProfile.BALANCED)
        
        manager.add_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size=0.1
        )
        
        updates = manager.update_position("BTC/USDT", 65000.0)
        
        assert updates['partial_tp_update'] is not None
        ptp_update = updates['partial_tp_update']
        assert ptp_update['stage'] == 1
        assert ptp_update['close_percent'] == 50.0
        assert ptp_update['trigger_profit'] == 30.0
    
    def test_peak_drawdown_exit_recommendation(self):
        """Test peak drawdown protection triggers exit"""
        manager = Phase1RiskManager(profile=TradingProfile.BALANCED)
        
        manager.add_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size=0.1
        )
        
        manager.update_position("BTC/USDT", 70000.0)
        manager.update_position("BTC/USDT", 63000.0)
        
        should_exit, reasons = manager.should_exit_position("BTC/USDT")
        assert should_exit
        assert any("Peak Drawdown" in r for r in reasons)
    
    def test_max_holding_time_exit_recommendation(self):
        """Test max holding time triggers exit"""
        manager = Phase1RiskManager(
            profile=TradingProfile.BALANCED,
            max_holding_hours=1.0
        )
        
        entry_time = datetime.now() - timedelta(hours=2)
        manager.add_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size=0.1,
            entry_time=entry_time
        )
        
        manager.update_position("BTC/USDT", 51000.0)
        
        should_exit, reasons = manager.should_exit_position("BTC/USDT")
        assert should_exit
        assert any("Max Holding Time" in r for r in reasons)
    
    def test_account_drawdown_blocks_new_positions(self):
        """Test account drawdown blocks new positions"""
        manager = Phase1RiskManager(
            profile=TradingProfile.BALANCED,
            initial_equity=10000.0,
            account_drawdown_no_new=30.0
        )
        
        manager.update_account_equity(6500.0)
        
        can_open, reason = manager.can_open_new_position()
        assert not can_open
        assert "blocked" in reason.lower()
    
    def test_get_position_risk_state(self):
        """Test getting complete position risk state"""
        manager = Phase1RiskManager(profile=TradingProfile.BALANCED)
        
        manager.add_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size=0.1
        )
        
        manager.update_position("BTC/USDT", 54000.0)
        
        state = manager.get_position_risk_state("BTC/USDT")
        
        assert state is not None
        assert state.symbol == "BTC/USDT"
        assert state.side == "long"
        assert state.current_pnl_percent > 0
        assert state.trailing_stop_active
    
    def test_remove_position_from_all_components(self):
        """Test removing position removes from all components"""
        manager = Phase1RiskManager(profile=TradingProfile.BALANCED)
        
        manager.add_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size=0.1
        )
        
        manager.remove_position("BTC/USDT")
        
        assert "BTC/USDT" not in manager.trailing_stops.trailing_stops
        assert "BTC/USDT" not in manager.partial_take_profit.positions
        assert "BTC/USDT" not in manager.peak_drawdown.positions
        assert "BTC/USDT" not in manager.max_holding_time.positions


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
