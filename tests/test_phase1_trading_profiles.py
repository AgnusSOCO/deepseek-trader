"""
Tests for Phase 1 Trading Profiles System
"""

import pytest
from src.autonomous.trading_profiles import (
    TradingProfile,
    TradingProfileManager,
    ProfileConfig,
    TrailingStopLevel,
    PartialTakeProfitStage,
    VolatilityAdjustment
)


class TestTradingProfiles:
    """Test trading profile configurations"""
    
    def test_profile_manager_initialization(self):
        """Test profile manager initializes with default profile"""
        manager = TradingProfileManager()
        assert manager.profile == TradingProfile.BALANCED
        assert manager.config.name == "Balanced"
    
    def test_profile_manager_custom_profile(self):
        """Test profile manager with custom profile"""
        manager = TradingProfileManager(TradingProfile.CONSERVATIVE)
        assert manager.profile == TradingProfile.CONSERVATIVE
        assert manager.config.name == "Conservative"
    
    def test_conservative_profile_config(self):
        """Test conservative profile has correct configuration"""
        manager = TradingProfileManager(TradingProfile.CONSERVATIVE)
        config = manager.get_config()
        
        assert config.name == "Conservative"
        assert config.leverage_min == 3
        assert config.leverage_max == 6
        assert config.position_size_min == 15.0
        assert config.position_size_max == 22.0
        assert config.peak_drawdown_threshold == 25.0
        assert config.min_timeframe_confirmations == 3
        assert len(config.trailing_stops) == 3
        assert len(config.partial_take_profit) == 3
    
    def test_balanced_profile_config(self):
        """Test balanced profile has correct configuration"""
        manager = TradingProfileManager(TradingProfile.BALANCED)
        config = manager.get_config()
        
        assert config.name == "Balanced"
        assert config.leverage_min == 6
        assert config.leverage_max == 8
        assert config.position_size_min == 20.0
        assert config.position_size_max == 27.0
        assert config.peak_drawdown_threshold == 30.0
        assert config.min_timeframe_confirmations == 2
    
    def test_aggressive_profile_config(self):
        """Test aggressive profile has correct configuration"""
        manager = TradingProfileManager(TradingProfile.AGGRESSIVE)
        config = manager.get_config()
        
        assert config.name == "Aggressive"
        assert config.leverage_min == 8
        assert config.leverage_max == 10
        assert config.position_size_min == 25.0
        assert config.position_size_max == 32.0
        assert config.peak_drawdown_threshold == 35.0
        assert config.min_timeframe_confirmations == 2
    
    def test_get_leverage_for_signal_strength(self):
        """Test leverage recommendation based on signal strength"""
        manager = TradingProfileManager(TradingProfile.BALANCED)
        config = manager.get_config()
        
        assert config.get_leverage_for_signal_strength("normal") == 6
        assert config.get_leverage_for_signal_strength("good") == 7
        assert config.get_leverage_for_signal_strength("strong") == 8
    
    def test_get_position_size_for_signal_strength(self):
        """Test position size recommendation based on signal strength"""
        manager = TradingProfileManager(TradingProfile.BALANCED)
        config = manager.get_config()
        
        normal_size = config.get_position_size_for_signal_strength("normal")
        good_size = config.get_position_size_for_signal_strength("good")
        strong_size = config.get_position_size_for_signal_strength("strong")
        
        assert normal_size < good_size < strong_size
        assert 20.0 <= normal_size <= 27.0
    
    def test_get_stop_loss_for_leverage(self):
        """Test stop-loss recommendation based on leverage"""
        manager = TradingProfileManager(TradingProfile.CONSERVATIVE)
        config = manager.get_config()
        
        low_lev_sl = config.get_stop_loss_for_leverage(3)  # Low leverage
        mid_lev_sl = config.get_stop_loss_for_leverage(5)  # Mid leverage
        high_lev_sl = config.get_stop_loss_for_leverage(6)  # Still mid (6 < 6.75)
        
        assert all(sl < 0 for sl in [low_lev_sl, mid_lev_sl, high_lev_sl])
        # Lower leverage should have wider stop-loss (more negative)
        assert low_lev_sl <= mid_lev_sl <= high_lev_sl
    
    def test_volatility_adjustment_high(self):
        """Test volatility adjustment for high volatility"""
        manager = TradingProfileManager(TradingProfile.BALANCED)
        config = manager.get_config()
        
        # High volatility (ATR > 5%)
        adj_lev, adj_pos = config.adjust_for_volatility(6.0, 7, 24.0)
        
        # Should reduce both leverage and position size
        assert adj_lev < 7
        assert adj_pos < 24.0
    
    def test_volatility_adjustment_normal(self):
        """Test volatility adjustment for normal volatility"""
        manager = TradingProfileManager(TradingProfile.BALANCED)
        config = manager.get_config()
        
        # Normal volatility (ATR 2-5%)
        adj_lev, adj_pos = config.adjust_for_volatility(3.5, 7, 24.0)
        
        # Should not adjust
        assert adj_lev == 7
        assert adj_pos == 24.0
    
    def test_volatility_adjustment_low(self):
        """Test volatility adjustment for low volatility"""
        manager = TradingProfileManager(TradingProfile.BALANCED)
        config = manager.get_config()
        
        # Low volatility (ATR < 2%)
        adj_lev, adj_pos = config.adjust_for_volatility(1.5, 7, 24.0)
        
        # Balanced profile increases leverage slightly for low volatility
        assert adj_lev >= 7
    
    def test_volatility_adjustment_respects_limits(self):
        """Test volatility adjustment respects profile limits"""
        manager = TradingProfileManager(TradingProfile.BALANCED)
        config = manager.get_config()
        
        # Try to adjust beyond limits
        adj_lev, adj_pos = config.adjust_for_volatility(10.0, 8, 27.0)
        
        # Should stay within profile limits
        assert config.leverage_min <= adj_lev <= config.leverage_max
        assert config.position_size_min <= adj_pos <= config.position_size_max
    
    def test_set_profile(self):
        """Test changing trading profile"""
        manager = TradingProfileManager(TradingProfile.CONSERVATIVE)
        assert manager.profile == TradingProfile.CONSERVATIVE
        
        manager.set_profile(TradingProfile.AGGRESSIVE)
        assert manager.profile == TradingProfile.AGGRESSIVE
        assert manager.config.name == "Aggressive"
    
    def test_get_all_profiles(self):
        """Test getting all available profiles"""
        profiles = TradingProfileManager.get_all_profiles()
        
        assert len(profiles) == 3
        assert TradingProfile.CONSERVATIVE in profiles
        assert TradingProfile.BALANCED in profiles
        assert TradingProfile.AGGRESSIVE in profiles
    
    def test_trailing_stop_levels_ascending(self):
        """Test trailing stop levels are in ascending order"""
        manager = TradingProfileManager(TradingProfile.BALANCED)
        config = manager.get_config()
        
        levels = config.trailing_stops
        for i in range(len(levels) - 1):
            assert levels[i].trigger_profit_pct < levels[i+1].trigger_profit_pct
            assert levels[i].stop_at_profit_pct < levels[i+1].stop_at_profit_pct
    
    def test_partial_take_profit_stages_ascending(self):
        """Test partial take-profit stages are in ascending order"""
        manager = TradingProfileManager(TradingProfile.BALANCED)
        config = manager.get_config()
        
        stages = config.partial_take_profit
        for i in range(len(stages) - 1):
            assert stages[i].trigger_profit_pct < stages[i+1].trigger_profit_pct


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
