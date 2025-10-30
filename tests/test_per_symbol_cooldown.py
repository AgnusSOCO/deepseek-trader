"""
Tests for Per-Symbol Cooldown Feature

Tests the per-symbol trade cooldown in EnhancedRiskManager.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from src.autonomous.enhanced_risk_manager import EnhancedRiskManager


@pytest.fixture
def risk_manager():
    """Create an EnhancedRiskManager with short cooldown for testing"""
    return EnhancedRiskManager(
        initial_capital=10000.0,
        min_trade_interval_sec=60  # 1 minute cooldown for testing
    )


def test_can_trade_symbol_no_history(risk_manager):
    """Test that we can trade a symbol with no trade history"""
    assert risk_manager.can_trade_symbol('BTC/USDT') == True
    assert risk_manager.can_trade_symbol('ETH/USDT') == True


def test_can_trade_symbol_after_cooldown(risk_manager):
    """Test that we can trade after cooldown period"""
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now() - timedelta(seconds=120)
    
    assert risk_manager.can_trade_symbol('BTC/USDT') == True


def test_cannot_trade_symbol_during_cooldown(risk_manager):
    """Test that we cannot trade during cooldown period"""
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now() - timedelta(seconds=30)
    
    assert risk_manager.can_trade_symbol('BTC/USDT') == False


def test_can_trade_symbol_exact_cooldown(risk_manager):
    """Test trading exactly at cooldown boundary"""
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now() - timedelta(seconds=60)
    
    assert risk_manager.can_trade_symbol('BTC/USDT') == True


def test_can_trade_symbol_just_before_cooldown(risk_manager):
    """Test trading just before cooldown expires"""
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now() - timedelta(seconds=59)
    
    assert risk_manager.can_trade_symbol('BTC/USDT') == False


def test_different_symbols_independent_cooldowns(risk_manager):
    """Test that different symbols have independent cooldowns"""
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now() - timedelta(seconds=30)
    risk_manager.last_trade_time['ETH/USDT'] = datetime.now() - timedelta(seconds=120)
    
    assert risk_manager.can_trade_symbol('BTC/USDT') == False
    assert risk_manager.can_trade_symbol('ETH/USDT') == True


def test_record_position_opened_updates_cooldown(risk_manager):
    """Test that recording a position updates the cooldown timer"""
    assert 'BTC/USDT' not in risk_manager.last_trade_time
    
    risk_manager.record_position_opened('BTC/USDT', 1000.0)
    
    assert 'BTC/USDT' in risk_manager.last_trade_time
    assert isinstance(risk_manager.last_trade_time['BTC/USDT'], datetime)


def test_can_open_position_respects_cooldown(risk_manager):
    """Test that can_open_position checks cooldown"""
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now() - timedelta(seconds=30)
    
    assert risk_manager.can_open_position('BTC/USDT') == False


def test_can_open_position_after_cooldown(risk_manager):
    """Test that can_open_position allows trading after cooldown"""
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now() - timedelta(seconds=120)
    
    assert risk_manager.can_open_position('BTC/USDT') == True


def test_cooldown_with_zero_interval(risk_manager):
    """Test cooldown with zero interval (disabled)"""
    risk_manager.min_trade_interval_sec = 0
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now()
    
    assert risk_manager.can_trade_symbol('BTC/USDT') == True


def test_cooldown_with_long_interval():
    """Test cooldown with long interval (30 minutes)"""
    risk_manager = EnhancedRiskManager(
        initial_capital=10000.0,
        min_trade_interval_sec=1800  # 30 minutes
    )
    
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now() - timedelta(seconds=900)
    
    assert risk_manager.can_trade_symbol('BTC/USDT') == False


def test_multiple_trades_same_symbol(risk_manager):
    """Test multiple trades on same symbol respecting cooldown"""
    risk_manager.record_position_opened('BTC/USDT', 1000.0)
    
    assert risk_manager.can_trade_symbol('BTC/USDT') == False
    
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now() - timedelta(seconds=120)
    
    assert risk_manager.can_trade_symbol('BTC/USDT') == True


def test_cooldown_persists_across_position_close(risk_manager):
    """Test that cooldown persists even after position is closed"""
    risk_manager.record_position_opened('BTC/USDT', 1000.0)
    risk_manager.record_position_closed('BTC/USDT', 1000.0)
    
    assert risk_manager.can_trade_symbol('BTC/USDT') == False


def test_cooldown_initialization():
    """Test that cooldown is properly initialized"""
    risk_manager = EnhancedRiskManager(
        initial_capital=10000.0,
        min_trade_interval_sec=1800
    )
    
    assert risk_manager.min_trade_interval_sec == 1800
    assert isinstance(risk_manager.last_trade_time, dict)
    assert len(risk_manager.last_trade_time) == 0


def test_cooldown_with_daily_limits(risk_manager):
    """Test cooldown interaction with daily trade limits"""
    for i in range(20):
        risk_manager.record_position_opened(f'SYMBOL{i}/USDT', 100.0)
        risk_manager.record_trade_result(10.0, 1.0)
    
    assert risk_manager.can_trade_today() == False
    
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now() - timedelta(seconds=120)
    assert risk_manager.can_open_position('BTC/USDT') == False


def test_cooldown_with_symbol_exposure_limit(risk_manager):
    """Test cooldown interaction with symbol exposure limits"""
    risk_manager.record_position_opened('BTC/USDT', 2000.0)
    
    risk_manager.last_trade_time['BTC/USDT'] = datetime.now() - timedelta(seconds=120)
    
    assert risk_manager.can_trade_symbol('BTC/USDT') == True
    assert risk_manager.can_open_position('BTC/USDT') == False


def test_cooldown_statistics_tracking(risk_manager):
    """Test that cooldown doesn't interfere with statistics"""
    risk_manager.record_position_opened('BTC/USDT', 1000.0)
    
    stats = risk_manager.get_statistics()
    
    assert stats['open_positions'] == 1
    assert 'BTC/USDT' in risk_manager.last_trade_time
