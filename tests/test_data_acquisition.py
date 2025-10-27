"""
Unit tests for Data Acquisition Module
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
import pandas as pd

from src.data.acquisition import MarketDataManager
from src.data.storage import SQLiteStorage, RedisCache
from src.data.indicators import TechnicalIndicators


@pytest.fixture
def exchange_config():
    """Create test exchange configuration."""
    return {
        'name': 'binance',
        'symbols': ['BTC/USDT', 'ETH/USDT'],
        'timeframes': ['5m', '1h'],
        'api': {
            'api_key': 'test_key',
            'api_secret': 'test_secret',
            'base_url': 'https://testnet.binance.vision'
        }
    }


@pytest.fixture
def mock_storage():
    """Create mock SQLite storage."""
    storage = Mock(spec=SQLiteStorage)
    storage.save_market_data = Mock()
    storage.get_market_data = Mock(return_value=pd.DataFrame())
    return storage


@pytest.fixture
def mock_cache():
    """Create mock Redis cache."""
    cache = Mock(spec=RedisCache)
    cache.connect = AsyncMock()
    cache.disconnect = AsyncMock()
    cache.set = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set_market_data = AsyncMock()
    cache.get_market_data = AsyncMock(return_value=None)
    return cache


@pytest.fixture
def mock_indicators():
    """Create mock technical indicators."""
    indicators = Mock(spec=TechnicalIndicators)
    indicators.calculate_all = Mock(return_value=pd.DataFrame())
    indicators.get_latest_indicators = Mock(return_value={})
    indicators.get_signal_summary = Mock(return_value={})
    return indicators


@pytest.fixture
def data_manager(exchange_config, mock_storage, mock_cache, mock_indicators):
    """Create MarketDataManager instance with mocks."""
    return MarketDataManager(exchange_config, mock_storage, mock_cache, mock_indicators)


class TestMarketDataManager:
    """Test suite for MarketDataManager class."""
    
    def test_initialization(self, data_manager):
        """Test data manager initialization."""
        assert data_manager is not None
        assert data_manager.exchange_name == 'binance'
        assert data_manager.buffers == {}
        assert data_manager.latest_prices == {}
        assert data_manager.running is False
    
    def test_subscribe(self, data_manager):
        """Test subscribing to market data updates."""
        callback = Mock()
        
        data_manager.subscribe('BTC/USDT', '5m', callback)
        
        assert 'BTC/USDT:5m' in data_manager.subscribers
        assert callback in data_manager.subscribers['BTC/USDT:5m']
    
    def test_notify_subscribers(self, data_manager):
        """Test notifying subscribers."""
        callback1 = Mock()
        callback2 = Mock()
        
        data_manager.subscribe('BTC/USDT', '5m', callback1)
        data_manager.subscribe('BTC/USDT', '5m', callback2)
        
        test_data = {'price': 50000.0}
        data_manager._notify_subscribers('BTC/USDT', '5m', test_data)
        
        callback1.assert_called_once_with('BTC/USDT', '5m', test_data)
        callback2.assert_called_once_with('BTC/USDT', '5m', test_data)
    
    def test_parse_ohlcv(self, data_manager):
        """Test parsing OHLCV data."""
        raw_data = [
            [1704067200000, 50000.0, 50100.0, 49900.0, 50050.0, 1000.0],
            [1704067500000, 50050.0, 50150.0, 49950.0, 50100.0, 1100.0]
        ]
        
        parsed = data_manager._parse_ohlcv(raw_data)
        
        assert len(parsed) == 2
        assert parsed[0]['open'] == 50000.0
        assert parsed[0]['high'] == 50100.0
        assert parsed[0]['low'] == 49900.0
        assert parsed[0]['close'] == 50050.0
        assert parsed[0]['volume'] == 1000.0
        assert isinstance(parsed[0]['timestamp'], datetime)
    
    def test_get_buffer_empty(self, data_manager):
        """Test getting buffer when empty."""
        buffer = data_manager.get_buffer('BTC/USDT', '5m')
        assert buffer == []
    
    def test_get_buffer_with_data(self, data_manager):
        """Test getting buffer with data."""
        from collections import deque
        
        test_data = [
            {'timestamp': datetime.utcnow(), 'close': 50000.0},
            {'timestamp': datetime.utcnow(), 'close': 50100.0}
        ]
        
        data_manager.buffers['BTC/USDT:5m'] = deque(test_data, maxlen=1000)
        
        buffer = data_manager.get_buffer('BTC/USDT', '5m')
        assert len(buffer) == 2
        assert buffer[0]['close'] == 50000.0
    
    def test_get_buffer_with_limit(self, data_manager):
        """Test getting buffer with limit."""
        from collections import deque
        
        test_data = [{'timestamp': datetime.utcnow(), 'close': 50000.0 + i} for i in range(10)]
        data_manager.buffers['BTC/USDT:5m'] = deque(test_data, maxlen=1000)
        
        buffer = data_manager.get_buffer('BTC/USDT', '5m', limit=5)
        assert len(buffer) == 5
        assert buffer[0]['close'] == 50005.0  # Last 5 items
    
    def test_get_latest_price(self, data_manager):
        """Test getting latest price."""
        data_manager.latest_prices['BTC/USDT'] = 50000.0
        
        price = data_manager.get_latest_price('BTC/USDT')
        assert price == 50000.0
    
    def test_get_latest_price_not_found(self, data_manager):
        """Test getting latest price when not available."""
        price = data_manager.get_latest_price('ETH/USDT')
        assert price is None
    
    @pytest.mark.asyncio
    async def test_initialize(self, data_manager, mock_cache):
        """Test initializing exchange connection."""
        with patch('ccxt.async_support.binance') as mock_exchange_class:
            mock_exchange = AsyncMock()
            mock_exchange.load_markets = AsyncMock()
            mock_exchange_class.return_value = mock_exchange
            
            await data_manager.initialize()
            
            assert data_manager.exchange is not None
            mock_exchange.load_markets.assert_called_once()
            mock_cache.connect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close(self, data_manager, mock_cache):
        """Test closing connections."""
        data_manager.exchange = AsyncMock()
        data_manager.exchange.close = AsyncMock()
        data_manager.running = True
        
        await data_manager.close()
        
        assert data_manager.running is False
        data_manager.exchange.close.assert_called_once()
        mock_cache.disconnect.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_fetch_ohlcv(self, data_manager):
        """Test fetching OHLCV data."""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ohlcv = AsyncMock(return_value=[
            [1704067200000, 50000.0, 50100.0, 49900.0, 50050.0, 1000.0]
        ])
        data_manager.exchange = mock_exchange
        
        ohlcv = await data_manager.fetch_ohlcv('BTC/USDT', '5m', limit=100)
        
        assert len(ohlcv) == 1
        mock_exchange.fetch_ohlcv.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_account_balance(self, data_manager):
        """Test getting account balance."""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_balance = AsyncMock(return_value={
            'USDT': {'free': 10000.0, 'used': 0.0, 'total': 10000.0}
        })
        data_manager.exchange = mock_exchange
        
        balance = await data_manager.get_account_balance()
        
        assert 'USDT' in balance
        mock_exchange.fetch_balance.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_order_book(self, data_manager):
        """Test getting order book."""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_order_book = AsyncMock(return_value={
            'bids': [[50000.0, 1.0], [49990.0, 2.0]],
            'asks': [[50010.0, 1.0], [50020.0, 2.0]]
        })
        data_manager.exchange = mock_exchange
        
        order_book = await data_manager.get_order_book('BTC/USDT', limit=20)
        
        assert 'bids' in order_book
        assert 'asks' in order_book
        assert len(order_book['bids']) == 2
        mock_exchange.fetch_order_book.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_ticker(self, data_manager):
        """Test getting ticker data."""
        mock_exchange = AsyncMock()
        mock_exchange.fetch_ticker = AsyncMock(return_value={
            'symbol': 'BTC/USDT',
            'last': 50000.0,
            'bid': 49990.0,
            'ask': 50010.0,
            'volume': 1000.0
        })
        data_manager.exchange = mock_exchange
        
        ticker = await data_manager.get_ticker('BTC/USDT')
        
        assert ticker['symbol'] == 'BTC/USDT'
        assert ticker['last'] == 50000.0
        mock_exchange.fetch_ticker.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_market_snapshot(self, data_manager, mock_indicators):
        """Test getting market snapshot."""
        from collections import deque
        
        test_data = []
        for i in range(100):
            test_data.append({
                'timestamp': datetime.utcnow() - timedelta(minutes=100-i),
                'open': 50000.0 + i,
                'high': 50100.0 + i,
                'low': 49900.0 + i,
                'close': 50050.0 + i,
                'volume': 1000.0
            })
        
        data_manager.buffers['BTC/USDT:5m'] = deque(test_data, maxlen=1000)
        data_manager.latest_prices['BTC/USDT'] = 50149.0
        
        mock_df = pd.DataFrame(test_data)
        mock_indicators.calculate_all.return_value = mock_df
        mock_indicators.get_latest_indicators.return_value = {'rsi': 65.5}
        mock_indicators.get_signal_summary.return_value = {'rsi': 'neutral'}
        
        snapshot = await data_manager.get_market_snapshot('BTC/USDT', '5m', calculate_indicators=True)
        
        assert snapshot is not None
        assert snapshot['symbol'] == 'BTC/USDT'
        assert snapshot['timeframe'] == '5m'
        assert snapshot['price'] == 50149.0
        assert 'indicators' in snapshot
        assert 'signals' in snapshot
        assert snapshot['data_points'] == 100
    
    @pytest.mark.asyncio
    async def test_get_market_snapshot_no_data(self, data_manager):
        """Test getting market snapshot when no data available."""
        snapshot = await data_manager.get_market_snapshot('BTC/USDT', '5m')
        assert snapshot is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
