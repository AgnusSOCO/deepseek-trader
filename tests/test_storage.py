"""
Unit tests for Storage Module
"""

import pytest
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from src.data.storage import SQLiteStorage, RedisCache


@pytest.fixture
def temp_db_path():
    """Create a temporary database path."""
    temp_dir = tempfile.mkdtemp()
    db_path = Path(temp_dir) / "test_trading_bot.db"
    yield str(db_path)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sqlite_storage(temp_db_path):
    """Create SQLiteStorage instance with temporary database."""
    storage = SQLiteStorage(temp_db_path)
    yield storage
    storage.close()


@pytest.fixture
def sample_market_data():
    """Create sample market data."""
    data = []
    base_time = datetime(2024, 1, 1, 0, 0, 0)
    
    for i in range(10):
        data.append({
            'timestamp': base_time + timedelta(minutes=i),
            'open': 100.0 + i,
            'high': 101.0 + i,
            'low': 99.0 + i,
            'close': 100.5 + i,
            'volume': 1000.0 + i * 10
        })
    
    return data


@pytest.fixture
def sample_trade_data():
    """Create sample trade data."""
    return {
        'symbol': 'BTC/USDT',
        'side': 'BUY',
        'order_type': 'market',
        'size': 0.1,
        'entry_price': 50000.0,
        'stop_loss': 49000.0,
        'take_profit': 52000.0,
        'leverage': 2.0,
        'status': 'open',
        'strategy': 'momentum',
        'confidence': 0.85,
        'entry_time': datetime.utcnow(),
        'notes': 'Test trade'
    }


class TestSQLiteStorage:
    """Test suite for SQLiteStorage class."""
    
    def test_initialization(self, sqlite_storage, temp_db_path):
        """Test storage initialization."""
        assert sqlite_storage is not None
        assert Path(temp_db_path).exists()
    
    def test_save_market_data(self, sqlite_storage, sample_market_data):
        """Test saving market data."""
        sqlite_storage.save_market_data('BTC/USDT', '5m', sample_market_data)
        
        df = sqlite_storage.get_market_data('BTC/USDT', '5m')
        assert len(df) == len(sample_market_data)
        assert df['close'].iloc[0] == sample_market_data[0]['close']
    
    def test_save_duplicate_market_data(self, sqlite_storage, sample_market_data):
        """Test that duplicate market data is not saved."""
        sqlite_storage.save_market_data('BTC/USDT', '5m', sample_market_data)
        sqlite_storage.save_market_data('BTC/USDT', '5m', sample_market_data)
        
        df = sqlite_storage.get_market_data('BTC/USDT', '5m')
        assert len(df) == len(sample_market_data)
    
    def test_get_market_data_with_filters(self, sqlite_storage, sample_market_data):
        """Test retrieving market data with time filters."""
        sqlite_storage.save_market_data('BTC/USDT', '5m', sample_market_data)
        
        start_time = sample_market_data[5]['timestamp']
        df = sqlite_storage.get_market_data('BTC/USDT', '5m', start_time=start_time)
        
        assert len(df) == 5  # Should get last 5 records
    
    def test_get_market_data_empty(self, sqlite_storage):
        """Test retrieving market data when none exists."""
        df = sqlite_storage.get_market_data('ETH/USDT', '1h')
        assert df.empty
    
    def test_save_trade(self, sqlite_storage, sample_trade_data):
        """Test saving a trade."""
        trade_id = sqlite_storage.save_trade(sample_trade_data)
        
        assert trade_id > 0
        
        trades = sqlite_storage.get_trades(symbol='BTC/USDT')
        assert len(trades) == 1
        assert trades[0]['side'] == 'BUY'
        assert trades[0]['size'] == 0.1
    
    def test_update_trade(self, sqlite_storage, sample_trade_data):
        """Test updating a trade."""
        trade_id = sqlite_storage.save_trade(sample_trade_data)
        
        updates = {
            'exit_price': 51000.0,
            'pnl': 100.0,
            'pnl_pct': 2.0,
            'status': 'closed',
            'exit_time': datetime.utcnow()
        }
        sqlite_storage.update_trade(trade_id, updates)
        
        trades = sqlite_storage.get_trades(symbol='BTC/USDT')
        assert trades[0]['status'] == 'closed'
        assert trades[0]['exit_price'] == 51000.0
        assert trades[0]['pnl'] == 100.0
    
    def test_get_trades_with_filters(self, sqlite_storage, sample_trade_data):
        """Test retrieving trades with filters."""
        trade1 = sample_trade_data.copy()
        trade1['symbol'] = 'BTC/USDT'
        trade1['status'] = 'open'
        sqlite_storage.save_trade(trade1)
        
        trade2 = sample_trade_data.copy()
        trade2['symbol'] = 'ETH/USDT'
        trade2['status'] = 'closed'
        sqlite_storage.save_trade(trade2)
        
        trade3 = sample_trade_data.copy()
        trade3['symbol'] = 'BTC/USDT'
        trade3['status'] = 'closed'
        sqlite_storage.save_trade(trade3)
        
        btc_trades = sqlite_storage.get_trades(symbol='BTC/USDT')
        assert len(btc_trades) == 2
        
        open_trades = sqlite_storage.get_trades(status='open')
        assert len(open_trades) == 1
        
        btc_closed = sqlite_storage.get_trades(symbol='BTC/USDT', status='closed')
        assert len(btc_closed) == 1
    
    def test_save_performance_metric(self, sqlite_storage):
        """Test saving performance metrics."""
        sqlite_storage.save_performance_metric(
            metric_name='sharpe_ratio',
            metric_value=1.85,
            symbol='BTC/USDT',
            strategy='momentum',
            metadata={'period': '30d'}
        )
        
        assert True
    
    def test_close(self, sqlite_storage):
        """Test closing storage."""
        sqlite_storage.close()


@pytest.mark.asyncio
class TestRedisCache:
    """Test suite for RedisCache class."""
    
    @pytest.fixture
    async def redis_cache(self):
        """Create RedisCache instance."""
        cache = RedisCache("redis://localhost:6379/15")
        try:
            await cache.connect()
            yield cache
        except Exception as e:
            pytest.skip(f"Redis not available: {e}")
        finally:
            await cache.disconnect()
    
    async def test_initialization(self):
        """Test cache initialization."""
        cache = RedisCache("redis://localhost:6379/15")
        assert cache is not None
        assert cache.redis_url == "redis://localhost:6379/15"
    
    async def test_connect(self, redis_cache):
        """Test connecting to Redis."""
        assert redis_cache.redis is not None
    
    async def test_set_and_get(self, redis_cache):
        """Test setting and getting values."""
        test_data = {'price': 50000.0, 'volume': 1000}
        
        await redis_cache.set('test_key', test_data)
        retrieved = await redis_cache.get('test_key')
        
        assert retrieved == test_data
    
    async def test_set_with_expiration(self, redis_cache):
        """Test setting values with expiration."""
        await redis_cache.set('expire_key', {'value': 123}, expire=1)
        
        value = await redis_cache.get('expire_key')
        assert value == {'value': 123}
        
        await asyncio.sleep(2)
        
        value = await redis_cache.get('expire_key')
        assert value is None
    
    async def test_delete(self, redis_cache):
        """Test deleting keys."""
        await redis_cache.set('delete_key', {'value': 456})
        
        assert await redis_cache.exists('delete_key')
        
        await redis_cache.delete('delete_key')
        
        assert not await redis_cache.exists('delete_key')
    
    async def test_exists(self, redis_cache):
        """Test checking key existence."""
        await redis_cache.set('exists_key', {'value': 789})
        
        assert await redis_cache.exists('exists_key')
        assert not await redis_cache.exists('nonexistent_key')
    
    async def test_set_market_data(self, redis_cache):
        """Test caching market data."""
        market_data = {
            'symbol': 'BTC/USDT',
            'price': 50000.0,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        await redis_cache.set_market_data('BTC/USDT', '5m', market_data)
        
        retrieved = await redis_cache.get_market_data('BTC/USDT', '5m')
        assert retrieved['symbol'] == 'BTC/USDT'
        assert retrieved['price'] == 50000.0
    
    async def test_set_indicator(self, redis_cache):
        """Test caching indicator values."""
        await redis_cache.set_indicator('BTC/USDT', '5m', 'rsi', 65.5)
        
        retrieved = await redis_cache.get_indicator('BTC/USDT', '5m', 'rsi')
        assert retrieved == 65.5
    
    async def test_get_nonexistent_key(self, redis_cache):
        """Test getting a nonexistent key."""
        value = await redis_cache.get('nonexistent')
        assert value is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
