"""
Tests for FundingTracker

Tests funding rate tracking, payment calculation, and database recording.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import ccxt

from src.execution.funding_tracker import FundingTracker
from src.data.storage import SQLiteStorage, FundingEventModel


@pytest.fixture
def mock_exchange():
    """Create a mock CCXT exchange"""
    exchange = Mock(spec=ccxt.Exchange)
    exchange.fetch_funding_rate = AsyncMock()
    return exchange


@pytest.fixture
def storage():
    """Create a test SQLite storage instance"""
    storage = SQLiteStorage(db_path=":memory:")
    yield storage
    storage.close()


@pytest.fixture
def funding_tracker(mock_exchange, storage):
    """Create a FundingTracker instance"""
    return FundingTracker(exchange=mock_exchange, storage=storage, enabled=True)


@pytest.fixture
def disabled_funding_tracker(mock_exchange, storage):
    """Create a disabled FundingTracker instance"""
    return FundingTracker(exchange=mock_exchange, storage=storage, enabled=False)


@pytest.mark.asyncio
async def test_fetch_funding_rate_success(funding_tracker, mock_exchange):
    """Test successful funding rate fetch"""
    mock_exchange.fetch_funding_rate.return_value = {
        'fundingRate': 0.0001,
        'timestamp': datetime.utcnow().timestamp() * 1000
    }
    
    rate = await funding_tracker.fetch_funding_rate('BTC/USDT:USDT')
    
    assert rate == 0.0001
    mock_exchange.fetch_funding_rate.assert_called_once_with('BTC/USDT:USDT')


@pytest.mark.asyncio
async def test_fetch_funding_rate_cached(funding_tracker, mock_exchange):
    """Test funding rate caching"""
    mock_exchange.fetch_funding_rate.return_value = {
        'fundingRate': 0.0001,
        'timestamp': datetime.utcnow().timestamp() * 1000
    }
    
    rate1 = await funding_tracker.fetch_funding_rate('BTC/USDT:USDT')
    rate2 = await funding_tracker.fetch_funding_rate('BTC/USDT:USDT')
    
    assert rate1 == rate2 == 0.0001
    mock_exchange.fetch_funding_rate.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_funding_rate_error(funding_tracker, mock_exchange):
    """Test funding rate fetch error handling"""
    mock_exchange.fetch_funding_rate.side_effect = Exception("API error")
    
    rate = await funding_tracker.fetch_funding_rate('BTC/USDT:USDT')
    
    assert rate == 0.0


@pytest.mark.asyncio
async def test_fetch_funding_rate_disabled(disabled_funding_tracker):
    """Test funding rate fetch when disabled"""
    rate = await disabled_funding_tracker.fetch_funding_rate('BTC/USDT:USDT')
    
    assert rate == 0.0


def test_calculate_funding_payment_long_positive_rate(funding_tracker):
    """Test funding payment calculation for long position with positive rate"""
    payment = funding_tracker.calculate_funding_payment(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        entry_price=50000.0,
        funding_rate=0.0001
    )
    
    assert payment == -5.0


def test_calculate_funding_payment_long_negative_rate(funding_tracker):
    """Test funding payment calculation for long position with negative rate"""
    payment = funding_tracker.calculate_funding_payment(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        entry_price=50000.0,
        funding_rate=-0.0001
    )
    
    assert payment == 5.0


def test_calculate_funding_payment_short_positive_rate(funding_tracker):
    """Test funding payment calculation for short position with positive rate"""
    payment = funding_tracker.calculate_funding_payment(
        symbol='BTC/USDT:USDT',
        side='SHORT',
        position_size=1.0,
        entry_price=50000.0,
        funding_rate=0.0001
    )
    
    assert payment == 5.0


def test_calculate_funding_payment_short_negative_rate(funding_tracker):
    """Test funding payment calculation for short position with negative rate"""
    payment = funding_tracker.calculate_funding_payment(
        symbol='BTC/USDT:USDT',
        side='SHORT',
        position_size=1.0,
        entry_price=50000.0,
        funding_rate=-0.0001
    )
    
    assert payment == -5.0


def test_calculate_funding_payment_zero_rate(funding_tracker):
    """Test funding payment calculation with zero rate"""
    payment = funding_tracker.calculate_funding_payment(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        entry_price=50000.0,
        funding_rate=0.0
    )
    
    assert payment == 0.0


def test_calculate_funding_payment_invalid_side(funding_tracker):
    """Test funding payment calculation with invalid side"""
    payment = funding_tracker.calculate_funding_payment(
        symbol='BTC/USDT:USDT',
        side='INVALID',
        position_size=1.0,
        entry_price=50000.0,
        funding_rate=0.0001
    )
    
    assert payment == 0.0


def test_calculate_funding_payment_disabled(disabled_funding_tracker):
    """Test funding payment calculation when disabled"""
    payment = disabled_funding_tracker.calculate_funding_payment(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        entry_price=50000.0,
        funding_rate=0.0001
    )
    
    assert payment == 0.0


@pytest.mark.asyncio
async def test_record_funding_event(funding_tracker):
    """Test recording funding event to database"""
    event_id = await funding_tracker.record_funding_event(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        notional_value=50000.0,
        funding_rate=0.0001,
        funding_amount=-5.0
    )
    
    assert event_id > 0
    
    events = funding_tracker.get_funding_events(symbol='BTC/USDT:USDT')
    assert len(events) == 1
    assert events[0]['symbol'] == 'BTC/USDT:USDT'
    assert events[0]['side'] == 'LONG'
    assert events[0]['position_size'] == 1.0
    assert events[0]['notional_value'] == 50000.0
    assert events[0]['funding_rate'] == 0.0001
    assert events[0]['funding_amount'] == -5.0


@pytest.mark.asyncio
async def test_record_funding_event_disabled(disabled_funding_tracker):
    """Test recording funding event when disabled"""
    event_id = await disabled_funding_tracker.record_funding_event(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        notional_value=50000.0,
        funding_rate=0.0001,
        funding_amount=-5.0
    )
    
    assert event_id == 0


def test_get_funding_events_empty(funding_tracker):
    """Test getting funding events from empty database"""
    events = funding_tracker.get_funding_events()
    
    assert events == []


@pytest.mark.asyncio
async def test_get_funding_events_multiple(funding_tracker):
    """Test getting multiple funding events"""
    await funding_tracker.record_funding_event(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        notional_value=50000.0,
        funding_rate=0.0001,
        funding_amount=-5.0
    )
    
    await funding_tracker.record_funding_event(
        symbol='ETH/USDT:USDT',
        side='SHORT',
        position_size=10.0,
        notional_value=30000.0,
        funding_rate=0.0002,
        funding_amount=6.0
    )
    
    events = funding_tracker.get_funding_events()
    assert len(events) == 2


@pytest.mark.asyncio
async def test_get_funding_events_filter_by_symbol(funding_tracker):
    """Test filtering funding events by symbol"""
    await funding_tracker.record_funding_event(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        notional_value=50000.0,
        funding_rate=0.0001,
        funding_amount=-5.0
    )
    
    await funding_tracker.record_funding_event(
        symbol='ETH/USDT:USDT',
        side='SHORT',
        position_size=10.0,
        notional_value=30000.0,
        funding_rate=0.0002,
        funding_amount=6.0
    )
    
    btc_events = funding_tracker.get_funding_events(symbol='BTC/USDT:USDT')
    assert len(btc_events) == 1
    assert btc_events[0]['symbol'] == 'BTC/USDT:USDT'


@pytest.mark.asyncio
async def test_get_total_funding_pnl(funding_tracker):
    """Test calculating total funding P&L"""
    await funding_tracker.record_funding_event(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        notional_value=50000.0,
        funding_rate=0.0001,
        funding_amount=-5.0
    )
    
    await funding_tracker.record_funding_event(
        symbol='BTC/USDT:USDT',
        side='SHORT',
        position_size=1.0,
        notional_value=50000.0,
        funding_rate=0.0001,
        funding_amount=5.0
    )
    
    total_pnl = funding_tracker.get_total_funding_pnl()
    assert total_pnl == 0.0


@pytest.mark.asyncio
async def test_get_total_funding_pnl_by_symbol(funding_tracker):
    """Test calculating total funding P&L by symbol"""
    await funding_tracker.record_funding_event(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        notional_value=50000.0,
        funding_rate=0.0001,
        funding_amount=-5.0
    )
    
    await funding_tracker.record_funding_event(
        symbol='ETH/USDT:USDT',
        side='SHORT',
        position_size=10.0,
        notional_value=30000.0,
        funding_rate=0.0002,
        funding_amount=6.0
    )
    
    btc_pnl = funding_tracker.get_total_funding_pnl(symbol='BTC/USDT:USDT')
    assert btc_pnl == -5.0
    
    eth_pnl = funding_tracker.get_total_funding_pnl(symbol='ETH/USDT:USDT')
    assert eth_pnl == 6.0


@pytest.mark.asyncio
async def test_get_total_funding_pnl_disabled(disabled_funding_tracker):
    """Test calculating total funding P&L when disabled"""
    total_pnl = disabled_funding_tracker.get_total_funding_pnl()
    
    assert total_pnl == 0.0


@pytest.mark.asyncio
async def test_process_position_funding(funding_tracker, mock_exchange):
    """Test processing position funding end-to-end"""
    mock_exchange.fetch_funding_rate.return_value = {
        'fundingRate': 0.0001,
        'timestamp': datetime.utcnow().timestamp() * 1000
    }
    
    funding_amount = await funding_tracker.process_position_funding(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        entry_price=50000.0
    )
    
    assert funding_amount == -5.0
    
    events = funding_tracker.get_funding_events(symbol='BTC/USDT:USDT')
    assert len(events) == 1
    assert events[0]['funding_amount'] == -5.0


@pytest.mark.asyncio
async def test_process_position_funding_disabled(disabled_funding_tracker):
    """Test processing position funding when disabled"""
    funding_amount = await disabled_funding_tracker.process_position_funding(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        entry_price=50000.0
    )
    
    assert funding_amount == 0.0


@pytest.mark.asyncio
async def test_process_position_funding_error(funding_tracker, mock_exchange):
    """Test processing position funding with error"""
    mock_exchange.fetch_funding_rate.side_effect = Exception("API error")
    
    funding_amount = await funding_tracker.process_position_funding(
        symbol='BTC/USDT:USDT',
        side='LONG',
        position_size=1.0,
        entry_price=50000.0
    )
    
    assert funding_amount == 0.0


def test_clear_cache(funding_tracker):
    """Test clearing funding rate cache"""
    funding_tracker.funding_cache['BTC/USDT:USDT'] = 0.0001
    
    assert len(funding_tracker.funding_cache) == 1
    
    funding_tracker.clear_cache()
    
    assert len(funding_tracker.funding_cache) == 0
