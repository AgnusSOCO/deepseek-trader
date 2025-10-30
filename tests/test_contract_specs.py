"""
Tests for Contract Specification Enforcement

Tests the ContractSpecManager for proper rounding, validation, and spec fetching.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.execution.contract_specs import ContractSpec, ContractSpecManager


@pytest.fixture
def mock_exchange():
    """Create a mock CCXT exchange"""
    exchange = Mock()
    exchange.markets = {
        'BTC/USDT': {
            'symbol': 'BTC/USDT',
            'precision': {
                'price': 0.01,
                'amount': 0.001
            },
            'limits': {
                'cost': {'min': 10.0},
                'amount': {'min': 0.001}
            },
            'contractSize': 1.0,
            'quanto': False
        },
        'ETH/USDT': {
            'symbol': 'ETH/USDT',
            'precision': {
                'price': 0.1,
                'amount': 0.01
            },
            'limits': {
                'cost': {'min': 5.0},
                'amount': {'min': 0.01}
            },
            'contractSize': 1.0,
            'quanto': False
        }
    }
    exchange.load_markets = AsyncMock()
    return exchange


@pytest.fixture
def spec_manager(mock_exchange):
    """Create a ContractSpecManager with mock exchange"""
    return ContractSpecManager(mock_exchange)


@pytest.mark.asyncio
async def test_fetch_specs_btc(spec_manager, mock_exchange):
    """Test fetching contract specs for BTC/USDT"""
    spec = await spec_manager.fetch_specs('BTC/USDT')
    
    assert spec.symbol == 'BTC/USDT'
    assert spec.tick_size == 0.01
    assert spec.step_size == 0.001
    assert spec.min_notional == 10.0
    assert spec.lot_size == 0.001
    assert spec.contract_multiplier == 1.0
    assert spec.quanto == False
    
    mock_exchange.load_markets.assert_called_once()


@pytest.mark.asyncio
async def test_fetch_specs_eth(spec_manager, mock_exchange):
    """Test fetching contract specs for ETH/USDT"""
    spec = await spec_manager.fetch_specs('ETH/USDT')
    
    assert spec.symbol == 'ETH/USDT'
    assert spec.tick_size == 0.1
    assert spec.step_size == 0.01
    assert spec.min_notional == 5.0
    assert spec.lot_size == 0.01


@pytest.mark.asyncio
async def test_fetch_specs_caching(spec_manager, mock_exchange):
    """Test that specs are cached after first fetch"""
    spec1 = await spec_manager.fetch_specs('BTC/USDT')
    spec2 = await spec_manager.fetch_specs('BTC/USDT')
    
    assert spec1 == spec2
    assert mock_exchange.load_markets.call_count == 1


@pytest.mark.asyncio
async def test_fetch_specs_invalid_symbol(spec_manager, mock_exchange):
    """Test fetching specs for invalid symbol"""
    with pytest.raises(ValueError, match="Symbol INVALID/USDT not found"):
        await spec_manager.fetch_specs('INVALID/USDT')


def test_calculate_precision():
    """Test precision calculation from values"""
    manager = ContractSpecManager(Mock())
    
    assert manager._calculate_precision(1.0) == 0
    assert manager._calculate_precision(0.1) == 1
    assert manager._calculate_precision(0.01) == 2
    assert manager._calculate_precision(0.001) == 3
    assert manager._calculate_precision(0.0001) == 4


def test_round_price():
    """Test price rounding to tick size"""
    spec = ContractSpec(
        symbol='BTC/USDT',
        tick_size=0.01,
        step_size=0.001,
        min_notional=10.0,
        lot_size=0.001,
        price_precision=2,
        quantity_precision=3
    )
    
    manager = ContractSpecManager(Mock())
    
    assert manager.round_price(50000.123, spec) == 50000.12
    assert manager.round_price(50000.125, spec) == 50000.12
    assert manager.round_price(50000.129, spec) == 50000.12
    assert manager.round_price(50000.999, spec) == 50000.99


def test_round_price_larger_tick():
    """Test price rounding with larger tick size"""
    spec = ContractSpec(
        symbol='ETH/USDT',
        tick_size=0.1,
        step_size=0.01,
        min_notional=5.0,
        lot_size=0.01,
        price_precision=1,
        quantity_precision=2
    )
    
    manager = ContractSpecManager(Mock())
    
    assert manager.round_price(3000.45, spec) == 3000.4
    assert manager.round_price(3000.49, spec) == 3000.4
    assert manager.round_price(3000.99, spec) == 3000.9


def test_round_quantity():
    """Test quantity rounding to step size"""
    spec = ContractSpec(
        symbol='BTC/USDT',
        tick_size=0.01,
        step_size=0.001,
        min_notional=10.0,
        lot_size=0.001,
        price_precision=2,
        quantity_precision=3
    )
    
    manager = ContractSpecManager(Mock())
    
    assert manager.round_quantity(0.1234, spec) == 0.123
    assert manager.round_quantity(0.1235, spec) == 0.123
    assert manager.round_quantity(0.1239, spec) == 0.123
    assert manager.round_quantity(1.9999, spec) == 1.999


def test_round_quantity_larger_step():
    """Test quantity rounding with larger step size"""
    spec = ContractSpec(
        symbol='ETH/USDT',
        tick_size=0.1,
        step_size=0.01,
        min_notional=5.0,
        lot_size=0.01,
        price_precision=1,
        quantity_precision=2
    )
    
    manager = ContractSpecManager(Mock())
    
    assert manager.round_quantity(1.234, spec) == 1.23
    assert manager.round_quantity(1.235, spec) == 1.23
    assert manager.round_quantity(1.999, spec) == 1.99


@pytest.mark.asyncio
async def test_validate_order_valid(spec_manager):
    """Test validating a valid order"""
    await spec_manager.fetch_specs('BTC/USDT')
    
    result = spec_manager.validate_order('BTC/USDT', 'BUY', 0.1, 50000.0)
    
    assert result['valid'] == True
    assert result['errors'] == []
    assert result['rounded_quantity'] == 0.1
    assert result['rounded_price'] == 50000.0


@pytest.mark.asyncio
async def test_validate_order_below_lot_size(spec_manager):
    """Test validating order below minimum lot size"""
    await spec_manager.fetch_specs('BTC/USDT')
    
    result = spec_manager.validate_order('BTC/USDT', 'BUY', 0.0001, 50000.0)
    
    assert result['valid'] == False
    assert len(result['errors']) > 0
    assert 'lot size' in result['errors'][0].lower()


@pytest.mark.asyncio
async def test_validate_order_below_min_notional(spec_manager):
    """Test validating order below minimum notional"""
    await spec_manager.fetch_specs('BTC/USDT')
    
    result = spec_manager.validate_order('BTC/USDT', 'BUY', 0.001, 1.0)
    
    assert result['valid'] == False
    assert len(result['errors']) > 0
    assert 'notional' in result['errors'][0].lower()


@pytest.mark.asyncio
async def test_validate_order_rounding(spec_manager):
    """Test that validation rounds prices and quantities"""
    await spec_manager.fetch_specs('BTC/USDT')
    
    result = spec_manager.validate_order('BTC/USDT', 'BUY', 0.1234, 50000.123)
    
    assert result['valid'] == True
    assert result['rounded_quantity'] == 0.123
    assert result['rounded_price'] == 50000.12


@pytest.mark.asyncio
async def test_validate_order_no_specs(spec_manager):
    """Test validating order without fetching specs first"""
    result = spec_manager.validate_order('BTC/USDT', 'BUY', 0.1, 50000.0)
    
    assert result['valid'] == False
    assert 'not loaded' in result['errors'][0].lower()


@pytest.mark.asyncio
async def test_get_min_order_size(spec_manager):
    """Test calculating minimum order size"""
    await spec_manager.fetch_specs('BTC/USDT')
    
    min_size = spec_manager.get_min_order_size('BTC/USDT', 50000.0)
    
    assert min_size >= 0.001
    notional = min_size * 50000.0
    assert notional >= 10.0


@pytest.mark.asyncio
async def test_get_min_order_size_high_price(spec_manager):
    """Test minimum order size with high price"""
    await spec_manager.fetch_specs('BTC/USDT')
    
    min_size = spec_manager.get_min_order_size('BTC/USDT', 100000.0)
    
    assert min_size >= 0.001
    notional = min_size * 100000.0
    assert notional >= 10.0


@pytest.mark.asyncio
async def test_get_min_order_size_low_price(spec_manager):
    """Test minimum order size with low price"""
    await spec_manager.fetch_specs('ETH/USDT')
    
    min_size = spec_manager.get_min_order_size('ETH/USDT', 100.0)
    
    assert min_size >= 0.01
    notional = min_size * 100.0
    assert notional >= 5.0


def test_clear_cache(spec_manager):
    """Test clearing the specs cache"""
    spec_manager.specs_cache['BTC/USDT'] = ContractSpec(
        symbol='BTC/USDT',
        tick_size=0.01,
        step_size=0.001,
        min_notional=10.0,
        lot_size=0.001,
        price_precision=2,
        quantity_precision=3
    )
    
    assert len(spec_manager.specs_cache) == 1
    
    spec_manager.clear_cache()
    
    assert len(spec_manager.specs_cache) == 0
