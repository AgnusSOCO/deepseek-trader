"""
Unit tests for execution module
"""

import pytest
import pytest_asyncio
from datetime import datetime
from src.execution.order_manager import OrderManager, Order, OrderStatus, OrderType, OrderSide
from src.execution.simulator import ExecutionSimulator


class TestOrderManager:
    """Test order manager"""
    
    @pytest_asyncio.fixture
    async def simulator(self):
        """Create execution simulator"""
        return ExecutionSimulator(initial_balance=10000.0)
    
    @pytest_asyncio.fixture
    async def order_manager(self, simulator):
        """Create order manager with simulator"""
        return OrderManager(simulator)
    
    @pytest.mark.asyncio
    async def test_place_market_order(self, order_manager, simulator):
        """Test placing a market order"""
        simulator.update_market_price('BTC/USDT', 50000.0)
        
        order = await order_manager.place_order(
            symbol='BTC/USDT',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1,
            metadata={'test': 'market_order'}
        )
        
        assert order is not None
        assert order.symbol == 'BTC/USDT'
        assert order.side == OrderSide.BUY
        assert order.order_type == OrderType.MARKET
        assert order.quantity == 0.1
        assert order.status in [OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED]
    
    @pytest.mark.asyncio
    async def test_place_limit_order(self, order_manager, simulator):
        """Test placing a limit order"""
        simulator.update_market_price('BTC/USDT', 50000.0)
        
        order = await order_manager.place_order(
            symbol='BTC/USDT',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=49000.0  # Below market - should fill
        )
        
        assert order is not None
        assert order.order_type == OrderType.LIMIT
        assert order.price == 49000.0
    
    @pytest.mark.asyncio
    async def test_cancel_order(self, order_manager, simulator):
        """Test canceling an order"""
        simulator.update_market_price('BTC/USDT', 50000.0)
        
        order = await order_manager.place_order(
            symbol='BTC/USDT',
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            quantity=0.1,
            price=40000.0  # Well below market
        )
        
        if order and order.status not in [OrderStatus.FILLED, OrderStatus.CANCELED]:
            canceled = await order_manager.cancel_order(order.client_order_id)
            assert canceled is True
    
    @pytest.mark.asyncio
    async def test_get_order_history(self, order_manager, simulator):
        """Test getting order history"""
        simulator.update_market_price('BTC/USDT', 50000.0)
        
        await order_manager.place_order(
            symbol='BTC/USDT',
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.1
        )
        
        await order_manager.place_order(
            symbol='BTC/USDT',
            side=OrderSide.SELL,
            order_type=OrderType.MARKET,
            quantity=0.05
        )
        
        history = order_manager.get_order_history('BTC/USDT')
        assert len(history) >= 2


class TestExecutionSimulator:
    """Test execution simulator"""
    
    @pytest.fixture
    def simulator(self):
        """Create execution simulator"""
        return ExecutionSimulator(initial_balance=10000.0)
    
    def test_initialization(self, simulator):
        """Test simulator initialization"""
        assert simulator.initial_balance == 10000.0
        assert simulator.balance['USDT'] == 10000.0
        assert len(simulator.positions) == 0
    
    @pytest.mark.asyncio
    async def test_market_order_execution(self, simulator):
        """Test market order execution"""
        simulator.update_market_price('BTC/USDT', 50000.0)
        
        order = await simulator.submit_order(
            symbol='BTC/USDT',
            side='BUY',
            order_type='MARKET',
            quantity=0.1
        )
        
        assert order['status'] == 'FILLED'
        assert order['filled'] == 0.1
        assert 'BTC' in simulator.balance
        assert simulator.balance['BTC'] == 0.1
    
    @pytest.mark.asyncio
    async def test_limit_order_execution(self, simulator):
        """Test limit order execution"""
        simulator.update_market_price('BTC/USDT', 50000.0)
        
        order = await simulator.submit_order(
            symbol='BTC/USDT',
            side='BUY',
            order_type='LIMIT',
            quantity=0.1,
            price=50000.0
        )
        
        assert order['status'] in ['FILLED', 'PARTIALLY_FILLED', 'NEW']
    
    @pytest.mark.asyncio
    async def test_slippage_calculation(self, simulator):
        """Test slippage is applied"""
        simulator.update_market_price('BTC/USDT', 50000.0)
        
        order = await simulator.submit_order(
            symbol='BTC/USDT',
            side='BUY',
            order_type='MARKET',
            quantity=0.1
        )
        
        if order['avgPrice']:
            assert order['avgPrice'] >= 50000.0
    
    @pytest.mark.asyncio
    async def test_fee_calculation(self, simulator):
        """Test trading fees are applied"""
        simulator.update_market_price('BTC/USDT', 50000.0)
        
        initial_balance = simulator.balance['USDT']
        
        order = await simulator.submit_order(
            symbol='BTC/USDT',
            side='BUY',
            order_type='MARKET',
            quantity=0.1
        )
        
        cost = 0.1 * 50000.0
        assert simulator.balance['USDT'] < initial_balance - cost
    
    @pytest.mark.asyncio
    async def test_position_tracking(self, simulator):
        """Test position tracking"""
        simulator.update_market_price('BTC/USDT', 50000.0)
        
        await simulator.submit_order(
            symbol='BTC/USDT',
            side='BUY',
            order_type='MARKET',
            quantity=0.1
        )
        
        positions = await simulator.get_positions()
        assert len(positions) > 0
        
        btc_position = next((p for p in positions if p['symbol'] == 'BTC/USDT'), None)
        assert btc_position is not None
        assert btc_position['contracts'] == 0.1
    
    @pytest.mark.asyncio
    async def test_account_summary(self, simulator):
        """Test account summary"""
        simulator.update_market_price('BTC/USDT', 50000.0)
        
        await simulator.submit_order(
            symbol='BTC/USDT',
            side='BUY',
            order_type='MARKET',
            quantity=0.1
        )
        
        summary = simulator.get_account_summary()
        
        assert 'initial_balance' in summary
        assert 'current_balance' in summary
        assert 'total_value' in summary
        assert 'total_pnl' in summary
        assert summary['num_positions'] > 0
    
    def test_reset(self, simulator):
        """Test simulator reset"""
        simulator.update_market_price('BTC/USDT', 50000.0)
        
        import asyncio
        asyncio.run(simulator.submit_order(
            symbol='BTC/USDT',
            side='BUY',
            order_type='MARKET',
            quantity=0.1
        ))
        
        simulator.reset()
        
        assert simulator.balance['USDT'] == 10000.0
        assert len(simulator.positions) == 0
        assert len(simulator.orders) == 0
