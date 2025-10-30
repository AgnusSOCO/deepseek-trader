"""
WebSocket Market Data Streaming

Provides real-time market data streaming via WebSocket connections.
Clients can subscribe to specific symbols and receive live price updates.
"""

import asyncio
import json
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from loguru import logger


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts market data
    """
    
    def __init__(self):
        """Initialize connection manager"""
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.client_subscriptions: Dict[WebSocket, Set[str]] = {}
        logger.info("ConnectionManager initialized")
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """
        Accept a new WebSocket connection
        
        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
        """
        await websocket.accept()
        self.client_subscriptions[websocket] = set()
        logger.info(f"WebSocket client connected: {client_id}")
    
    def disconnect(self, websocket: WebSocket, client_id: str):
        """
        Remove a WebSocket connection
        
        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
        """
        if websocket in self.client_subscriptions:
            subscribed_symbols = self.client_subscriptions[websocket]
            for symbol in subscribed_symbols:
                if symbol in self.active_connections:
                    self.active_connections[symbol].discard(websocket)
                    if not self.active_connections[symbol]:
                        del self.active_connections[symbol]
            
            del self.client_subscriptions[websocket]
        
        logger.info(f"WebSocket client disconnected: {client_id}")
    
    def subscribe(self, websocket: WebSocket, symbol: str):
        """
        Subscribe a client to a symbol
        
        Args:
            websocket: WebSocket connection
            symbol: Trading pair symbol
        """
        if symbol not in self.active_connections:
            self.active_connections[symbol] = set()
        
        self.active_connections[symbol].add(websocket)
        
        if websocket in self.client_subscriptions:
            self.client_subscriptions[websocket].add(symbol)
        
        logger.info(f"Client subscribed to {symbol}")
    
    def unsubscribe(self, websocket: WebSocket, symbol: str):
        """
        Unsubscribe a client from a symbol
        
        Args:
            websocket: WebSocket connection
            symbol: Trading pair symbol
        """
        if symbol in self.active_connections:
            self.active_connections[symbol].discard(websocket)
            if not self.active_connections[symbol]:
                del self.active_connections[symbol]
        
        if websocket in self.client_subscriptions:
            self.client_subscriptions[websocket].discard(symbol)
        
        logger.info(f"Client unsubscribed from {symbol}")
    
    async def broadcast_to_symbol(self, symbol: str, message: Dict[str, Any]):
        """
        Broadcast a message to all clients subscribed to a symbol
        
        Args:
            symbol: Trading pair symbol
            message: Message to broadcast
        """
        if symbol not in self.active_connections:
            return
        
        disconnected = []
        
        for connection in self.active_connections[symbol]:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.append(connection)
        
        for connection in disconnected:
            self.active_connections[symbol].discard(connection)
    
    async def send_personal_message(self, websocket: WebSocket, message: Dict[str, Any]):
        """
        Send a message to a specific client
        
        Args:
            websocket: WebSocket connection
            message: Message to send
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    def get_subscriptions(self, websocket: WebSocket) -> Set[str]:
        """
        Get all symbols a client is subscribed to
        
        Args:
            websocket: WebSocket connection
            
        Returns:
            Set of subscribed symbols
        """
        return self.client_subscriptions.get(websocket, set())
    
    def get_subscriber_count(self, symbol: str) -> int:
        """
        Get number of subscribers for a symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Number of subscribers
        """
        return len(self.active_connections.get(symbol, set()))
    
    def get_total_connections(self) -> int:
        """
        Get total number of active connections
        
        Returns:
            Number of active connections
        """
        return len(self.client_subscriptions)


class MarketDataStreamer:
    """
    Streams market data to WebSocket clients
    """
    
    def __init__(self, connection_manager: ConnectionManager):
        """
        Initialize market data streamer
        
        Args:
            connection_manager: Connection manager instance
        """
        self.connection_manager = connection_manager
        self.running = False
        logger.info("MarketDataStreamer initialized")
    
    async def stream_price_update(
        self,
        symbol: str,
        price: float,
        volume: float,
        timestamp: Optional[datetime] = None
    ):
        """
        Stream a price update to subscribers
        
        Args:
            symbol: Trading pair symbol
            price: Current price
            volume: Current volume
            timestamp: Update timestamp
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        message = {
            'type': 'price_update',
            'symbol': symbol,
            'price': price,
            'volume': volume,
            'timestamp': timestamp.isoformat()
        }
        
        await self.connection_manager.broadcast_to_symbol(symbol, message)
    
    async def stream_trade_update(
        self,
        symbol: str,
        side: str,
        size: float,
        price: float,
        timestamp: Optional[datetime] = None
    ):
        """
        Stream a trade update to subscribers
        
        Args:
            symbol: Trading pair symbol
            side: Trade side (BUY/SELL)
            size: Trade size
            price: Trade price
            timestamp: Trade timestamp
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        message = {
            'type': 'trade_update',
            'symbol': symbol,
            'side': side,
            'size': size,
            'price': price,
            'timestamp': timestamp.isoformat()
        }
        
        await self.connection_manager.broadcast_to_symbol(symbol, message)
    
    async def stream_orderbook_update(
        self,
        symbol: str,
        bids: list,
        asks: list,
        timestamp: Optional[datetime] = None
    ):
        """
        Stream an orderbook update to subscribers
        
        Args:
            symbol: Trading pair symbol
            bids: List of bid levels [[price, size], ...]
            asks: List of ask levels [[price, size], ...]
            timestamp: Update timestamp
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        message = {
            'type': 'orderbook_update',
            'symbol': symbol,
            'bids': bids,
            'asks': asks,
            'timestamp': timestamp.isoformat()
        }
        
        await self.connection_manager.broadcast_to_symbol(symbol, message)
    
    async def stream_indicator_update(
        self,
        symbol: str,
        indicators: Dict[str, float],
        timestamp: Optional[datetime] = None
    ):
        """
        Stream technical indicator updates to subscribers
        
        Args:
            symbol: Trading pair symbol
            indicators: Dictionary of indicator values
            timestamp: Update timestamp
        """
        if timestamp is None:
            timestamp = datetime.utcnow()
        
        message = {
            'type': 'indicator_update',
            'symbol': symbol,
            'indicators': indicators,
            'timestamp': timestamp.isoformat()
        }
        
        await self.connection_manager.broadcast_to_symbol(symbol, message)


_connection_manager: Optional[ConnectionManager] = None
_market_data_streamer: Optional[MarketDataStreamer] = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
    return _connection_manager


def get_market_data_streamer() -> MarketDataStreamer:
    """Get the global market data streamer instance"""
    global _market_data_streamer
    if _market_data_streamer is None:
        _market_data_streamer = MarketDataStreamer(get_connection_manager())
    return _market_data_streamer


async def handle_websocket_connection(websocket: WebSocket, client_id: str):
    """
    Handle a WebSocket connection
    
    Args:
        websocket: WebSocket connection
        client_id: Unique client identifier
    """
    manager = get_connection_manager()
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            action = message.get('action')
            symbol = message.get('symbol')
            
            if action == 'subscribe' and symbol:
                manager.subscribe(websocket, symbol)
                await manager.send_personal_message(websocket, {
                    'type': 'subscription_confirmed',
                    'symbol': symbol,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            elif action == 'unsubscribe' and symbol:
                manager.unsubscribe(websocket, symbol)
                await manager.send_personal_message(websocket, {
                    'type': 'unsubscription_confirmed',
                    'symbol': symbol,
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            elif action == 'ping':
                await manager.send_personal_message(websocket, {
                    'type': 'pong',
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            elif action == 'get_subscriptions':
                subscriptions = manager.get_subscriptions(websocket)
                await manager.send_personal_message(websocket, {
                    'type': 'subscriptions',
                    'symbols': list(subscriptions),
                    'timestamp': datetime.utcnow().isoformat()
                })
            
            else:
                await manager.send_personal_message(websocket, {
                    'type': 'error',
                    'message': f'Unknown action: {action}',
                    'timestamp': datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, client_id)
