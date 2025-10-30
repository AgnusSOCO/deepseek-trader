"""
Tests for Health Endpoint and WebSocket Market Data

Tests health monitoring and WebSocket streaming functionality.
"""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from src.dashboard.health import HealthMonitor
from src.dashboard.websocket import ConnectionManager, MarketDataStreamer
from src.data.storage import SQLiteStorage
from src.autonomous.enhanced_risk_manager import EnhancedRiskManager



@pytest.fixture
def storage():
    """Create a test SQLite storage instance"""
    storage = SQLiteStorage(db_path=":memory:")
    yield storage
    storage.close()


@pytest.fixture
def risk_manager():
    """Create a test risk manager instance"""
    return EnhancedRiskManager(initial_capital=10000.0)


@pytest.fixture
def health_monitor(storage, risk_manager):
    """Create a health monitor instance"""
    return HealthMonitor(storage=storage, risk_manager=risk_manager)


def test_health_monitor_initialization(health_monitor):
    """Test health monitor initialization"""
    assert health_monitor.storage is not None
    assert health_monitor.risk_manager is not None
    assert health_monitor.start_time is not None
    assert health_monitor.error_log == []


def test_get_system_metrics(health_monitor):
    """Test getting system metrics"""
    metrics = health_monitor.get_system_metrics()
    
    assert 'cpu_percent' in metrics
    assert 'memory_percent' in metrics
    assert 'memory_available_mb' in metrics
    assert 'memory_total_mb' in metrics
    assert 'disk_percent' in metrics
    assert 'disk_free_gb' in metrics
    assert 'disk_total_gb' in metrics
    
    assert metrics['cpu_percent'] >= 0
    assert metrics['memory_percent'] >= 0
    assert metrics['disk_percent'] >= 0


def test_get_database_health_healthy(health_monitor):
    """Test database health check when healthy"""
    health = health_monitor.get_database_health()
    
    assert health['status'] == 'healthy'
    assert health['connected'] is True
    assert 'total_trades' in health


def test_get_database_health_not_configured():
    """Test database health check when not configured"""
    monitor = HealthMonitor(storage=None, risk_manager=None)
    health = monitor.get_database_health()
    
    assert health['status'] == 'not_configured'
    assert health['connected'] is False


def test_get_risk_manager_status_healthy(health_monitor):
    """Test risk manager status when healthy"""
    status = health_monitor.get_risk_manager_status()
    
    assert status['status'] == 'healthy'
    assert status['can_trade'] is True
    assert 'daily_trades' in status
    assert 'daily_pnl' in status
    assert 'open_positions' in status


def test_get_risk_manager_status_not_configured():
    """Test risk manager status when not configured"""
    monitor = HealthMonitor(storage=None, risk_manager=None)
    status = monitor.get_risk_manager_status()
    
    assert status['status'] == 'not_configured'
    assert status['can_trade'] is False


def test_get_uptime(health_monitor):
    """Test getting uptime"""
    uptime = health_monitor.get_uptime()
    
    assert 'uptime_seconds' in uptime
    assert 'uptime_hours' in uptime
    assert 'uptime_days' in uptime
    assert 'start_time' in uptime
    
    assert uptime['uptime_seconds'] >= 0


def test_log_error(health_monitor):
    """Test logging errors"""
    health_monitor.log_error('test_error', 'Test error message', {'detail': 'test'})
    
    assert len(health_monitor.error_log) == 1
    assert health_monitor.error_log[0]['type'] == 'test_error'
    assert health_monitor.error_log[0]['message'] == 'Test error message'
    assert health_monitor.error_log[0]['details']['detail'] == 'test'


def test_log_error_max_size(health_monitor):
    """Test error log max size"""
    for i in range(150):
        health_monitor.log_error(f'error_{i}', f'Error {i}')
    
    assert len(health_monitor.error_log) == health_monitor.max_error_log_size


def test_get_recent_errors(health_monitor):
    """Test getting recent errors"""
    for i in range(20):
        health_monitor.log_error(f'error_{i}', f'Error {i}')
    
    recent = health_monitor.get_recent_errors(limit=5)
    
    assert len(recent) == 5
    assert recent[-1]['type'] == 'error_19'


def test_get_comprehensive_health(health_monitor):
    """Test getting comprehensive health status"""
    health = health_monitor.get_comprehensive_health()
    
    assert 'status' in health
    assert 'timestamp' in health
    assert 'uptime' in health
    assert 'system' in health
    assert 'database' in health
    assert 'risk_manager' in health
    assert 'recent_errors' in health
    assert 'error_count' in health
    
    assert health['status'] == 'healthy'


def test_comprehensive_health_with_errors(health_monitor):
    """Test comprehensive health status with errors"""
    health_monitor.log_error('test_error', 'Test error')
    
    health = health_monitor.get_comprehensive_health()
    
    assert health['status'] == 'degraded'
    assert health['error_count'] == 1



@pytest.fixture
def connection_manager():
    """Create a connection manager instance"""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection"""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_connection_manager_connect(connection_manager, mock_websocket):
    """Test connecting a WebSocket client"""
    await connection_manager.connect(mock_websocket, 'client_1')
    
    assert mock_websocket in connection_manager.client_subscriptions
    assert len(connection_manager.client_subscriptions[mock_websocket]) == 0
    mock_websocket.accept.assert_called_once()


def test_connection_manager_disconnect(connection_manager, mock_websocket):
    """Test disconnecting a WebSocket client"""
    connection_manager.client_subscriptions[mock_websocket] = {'BTC/USDT', 'ETH/USDT'}
    connection_manager.active_connections['BTC/USDT'] = {mock_websocket}
    connection_manager.active_connections['ETH/USDT'] = {mock_websocket}
    
    connection_manager.disconnect(mock_websocket, 'client_1')
    
    assert mock_websocket not in connection_manager.client_subscriptions
    assert 'BTC/USDT' not in connection_manager.active_connections
    assert 'ETH/USDT' not in connection_manager.active_connections


def test_connection_manager_subscribe(connection_manager, mock_websocket):
    """Test subscribing to a symbol"""
    connection_manager.client_subscriptions[mock_websocket] = set()
    
    connection_manager.subscribe(mock_websocket, 'BTC/USDT')
    
    assert 'BTC/USDT' in connection_manager.active_connections
    assert mock_websocket in connection_manager.active_connections['BTC/USDT']
    assert 'BTC/USDT' in connection_manager.client_subscriptions[mock_websocket]


def test_connection_manager_unsubscribe(connection_manager, mock_websocket):
    """Test unsubscribing from a symbol"""
    connection_manager.client_subscriptions[mock_websocket] = {'BTC/USDT'}
    connection_manager.active_connections['BTC/USDT'] = {mock_websocket}
    
    connection_manager.unsubscribe(mock_websocket, 'BTC/USDT')
    
    assert 'BTC/USDT' not in connection_manager.active_connections
    assert 'BTC/USDT' not in connection_manager.client_subscriptions[mock_websocket]


@pytest.mark.asyncio
async def test_connection_manager_broadcast(connection_manager, mock_websocket):
    """Test broadcasting to symbol subscribers"""
    connection_manager.active_connections['BTC/USDT'] = {mock_websocket}
    
    message = {'type': 'price_update', 'price': 50000}
    await connection_manager.broadcast_to_symbol('BTC/USDT', message)
    
    mock_websocket.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_connection_manager_send_personal_message(connection_manager, mock_websocket):
    """Test sending personal message"""
    message = {'type': 'confirmation', 'status': 'ok'}
    await connection_manager.send_personal_message(mock_websocket, message)
    
    mock_websocket.send_json.assert_called_once_with(message)


def test_connection_manager_get_subscriptions(connection_manager, mock_websocket):
    """Test getting client subscriptions"""
    connection_manager.client_subscriptions[mock_websocket] = {'BTC/USDT', 'ETH/USDT'}
    
    subscriptions = connection_manager.get_subscriptions(mock_websocket)
    
    assert subscriptions == {'BTC/USDT', 'ETH/USDT'}


def test_connection_manager_get_subscriber_count(connection_manager, mock_websocket):
    """Test getting subscriber count"""
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    connection_manager.active_connections['BTC/USDT'] = {ws1, ws2}
    
    count = connection_manager.get_subscriber_count('BTC/USDT')
    
    assert count == 2


def test_connection_manager_get_total_connections(connection_manager):
    """Test getting total connections"""
    ws1 = AsyncMock()
    ws2 = AsyncMock()
    connection_manager.client_subscriptions[ws1] = set()
    connection_manager.client_subscriptions[ws2] = set()
    
    total = connection_manager.get_total_connections()
    
    assert total == 2


@pytest.fixture
def market_data_streamer(connection_manager):
    """Create a market data streamer instance"""
    return MarketDataStreamer(connection_manager)


@pytest.mark.asyncio
async def test_stream_price_update(market_data_streamer, connection_manager, mock_websocket):
    """Test streaming price update"""
    connection_manager.active_connections['BTC/USDT'] = {mock_websocket}
    
    await market_data_streamer.stream_price_update('BTC/USDT', 50000.0, 100.0)
    
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args['type'] == 'price_update'
    assert call_args['symbol'] == 'BTC/USDT'
    assert call_args['price'] == 50000.0
    assert call_args['volume'] == 100.0


@pytest.mark.asyncio
async def test_stream_trade_update(market_data_streamer, connection_manager, mock_websocket):
    """Test streaming trade update"""
    connection_manager.active_connections['BTC/USDT'] = {mock_websocket}
    
    await market_data_streamer.stream_trade_update('BTC/USDT', 'BUY', 0.5, 50000.0)
    
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args['type'] == 'trade_update'
    assert call_args['symbol'] == 'BTC/USDT'
    assert call_args['side'] == 'BUY'
    assert call_args['size'] == 0.5
    assert call_args['price'] == 50000.0


@pytest.mark.asyncio
async def test_stream_orderbook_update(market_data_streamer, connection_manager, mock_websocket):
    """Test streaming orderbook update"""
    connection_manager.active_connections['BTC/USDT'] = {mock_websocket}
    
    bids = [[50000, 1.0], [49999, 2.0]]
    asks = [[50001, 1.5], [50002, 2.5]]
    
    await market_data_streamer.stream_orderbook_update('BTC/USDT', bids, asks)
    
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args['type'] == 'orderbook_update'
    assert call_args['symbol'] == 'BTC/USDT'
    assert call_args['bids'] == bids
    assert call_args['asks'] == asks


@pytest.mark.asyncio
async def test_stream_indicator_update(market_data_streamer, connection_manager, mock_websocket):
    """Test streaming indicator update"""
    connection_manager.active_connections['BTC/USDT'] = {mock_websocket}
    
    indicators = {'rsi': 45.5, 'macd': 120.3, 'ema_12': 49800}
    
    await market_data_streamer.stream_indicator_update('BTC/USDT', indicators)
    
    mock_websocket.send_json.assert_called_once()
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args['type'] == 'indicator_update'
    assert call_args['symbol'] == 'BTC/USDT'
    assert call_args['indicators'] == indicators
