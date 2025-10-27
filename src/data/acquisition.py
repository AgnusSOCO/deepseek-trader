"""
Data Acquisition Module

Handles real-time and historical market data acquisition from cryptocurrency exchanges.
Supports WebSocket streaming and REST API calls using CCXT library.
"""

import asyncio
import ccxt.async_support as ccxt
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from collections import deque
import json

from ..utils.logger import get_logger
from .storage import SQLiteStorage, RedisCache
from .indicators import TechnicalIndicators

logger = get_logger()


class MarketDataManager:
    """Manages market data acquisition from cryptocurrency exchanges."""
    
    def __init__(self, exchange_config: Dict[str, Any], storage: SQLiteStorage,
                 cache: RedisCache, indicators: TechnicalIndicators):
        """
        Initialize market data manager.
        
        Args:
            exchange_config: Exchange configuration dictionary
            storage: SQLite storage instance
            cache: Redis cache instance
            indicators: Technical indicators calculator
        """
        self.exchange_config = exchange_config
        self.storage = storage
        self.cache = cache
        self.indicators = indicators
        
        self.exchange_name = exchange_config.get('name', 'binance')
        self.exchange: Optional[ccxt.Exchange] = None
        
        self.buffers: Dict[str, deque] = {}
        
        self.latest_prices: Dict[str, float] = {}
        
        self.subscribers: Dict[str, List[Callable]] = {}
        
        self.ws_connected = False
        
        self.running = False
        
        logger.info(f"Market data manager initialized for {self.exchange_name}")
    
    async def initialize(self):
        """Initialize exchange connection."""
        try:
            api_config = self.exchange_config.get('api', {})
            api_key = api_config.get('api_key', '')
            api_secret = api_config.get('api_secret', '')
            base_url = api_config.get('base_url', '')
            
            exchange_class = getattr(ccxt, self.exchange_name)
            
            config = {
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # For perpetual futures
                }
            }
            
            if base_url:
                config['urls'] = {'api': base_url}
            
            self.exchange = exchange_class(config)
            
            await self.exchange.load_markets()
            
            logger.info(f"Connected to {self.exchange_name} exchange")
            
            await self.cache.connect()
            
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise
    
    async def close(self):
        """Close exchange connection and cleanup."""
        self.running = False
        
        if self.exchange:
            await self.exchange.close()
            logger.info("Exchange connection closed")
        
        await self.cache.disconnect()
    
    def subscribe(self, symbol: str, timeframe: str, callback: Callable):
        """
        Subscribe to market data updates (observer pattern).
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            callback: Callback function to call on updates
        """
        key = f"{symbol}:{timeframe}"
        if key not in self.subscribers:
            self.subscribers[key] = []
        self.subscribers[key].append(callback)
        logger.info(f"Subscriber added for {key}")
    
    def _notify_subscribers(self, symbol: str, timeframe: str, data: Dict[str, Any]):
        """
        Notify all subscribers of data update.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            data: Market data
        """
        key = f"{symbol}:{timeframe}"
        if key in self.subscribers:
            for callback in self.subscribers[key]:
                try:
                    callback(symbol, timeframe, data)
                except Exception as e:
                    logger.error(f"Error in subscriber callback: {e}")
    
    async def fetch_ohlcv(self, symbol: str, timeframe: str = '5m', 
                         limit: int = 1000, since: Optional[int] = None) -> List[List]:
        """
        Fetch historical OHLCV data from exchange.
        
        Args:
            symbol: Trading symbol (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1m', '5m', '1h')
            limit: Number of candles to fetch
            since: Timestamp in milliseconds (optional)
            
        Returns:
            List of OHLCV candles
        """
        try:
            if not self.exchange:
                await self.initialize()
            
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol,
                timeframe=timeframe,
                limit=limit,
                since=since
            )
            
            logger.bind(data=True).info(f"Fetched {len(ohlcv)} candles for {symbol} {timeframe}")
            return ohlcv
            
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            raise
    
    def _parse_ohlcv(self, ohlcv_data: List[List]) -> List[Dict[str, Any]]:
        """
        Parse OHLCV data from exchange format to dictionary format.
        
        Args:
            ohlcv_data: Raw OHLCV data from exchange
            
        Returns:
            List of OHLCV dictionaries
        """
        parsed = []
        for candle in ohlcv_data:
            parsed.append({
                'timestamp': datetime.fromtimestamp(candle[0] / 1000),
                'open': float(candle[1]),
                'high': float(candle[2]),
                'low': float(candle[3]),
                'close': float(candle[4]),
                'volume': float(candle[5])
            })
        return parsed
    
    async def fetch_initial_data(self, symbol: str, timeframe: str, lookback_days: int = 30):
        """
        Fetch initial historical data and store in database.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            lookback_days: Number of days to fetch
        """
        try:
            logger.info(f"Fetching initial data for {symbol} {timeframe} ({lookback_days} days)")
            
            since = int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)
            
            all_data = []
            current_since = since
            
            while True:
                ohlcv = await self.fetch_ohlcv(symbol, timeframe, limit=1000, since=current_since)
                
                if not ohlcv:
                    break
                
                all_data.extend(ohlcv)
                
                last_timestamp = ohlcv[-1][0]
                if last_timestamp == current_since:
                    break  # No more data
                current_since = last_timestamp + 1
                
                if last_timestamp >= int(datetime.now().timestamp() * 1000):
                    break
                
                await asyncio.sleep(0.5)
            
            parsed_data = self._parse_ohlcv(all_data)
            self.storage.save_market_data(symbol, timeframe, parsed_data)
            
            buffer_key = f"{symbol}:{timeframe}"
            self.buffers[buffer_key] = deque(parsed_data, maxlen=1000)
            
            if parsed_data:
                self.latest_prices[symbol] = parsed_data[-1]['close']
            
            logger.info(f"Stored {len(parsed_data)} candles for {symbol} {timeframe}")
            
        except Exception as e:
            logger.error(f"Error fetching initial data: {e}")
            raise
    
    async def fetch_latest_candle(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """
        Fetch the latest candle for a symbol/timeframe.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            
        Returns:
            Latest candle dictionary or None
        """
        try:
            ohlcv = await self.fetch_ohlcv(symbol, timeframe, limit=1)
            if ohlcv:
                parsed = self._parse_ohlcv(ohlcv)
                return parsed[0] if parsed else None
            return None
        except Exception as e:
            logger.error(f"Error fetching latest candle: {e}")
            return None
    
    async def update_data(self, symbol: str, timeframe: str):
        """
        Update data buffer with latest candle.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
        """
        try:
            latest_candle = await self.fetch_latest_candle(symbol, timeframe)
            
            if latest_candle:
                buffer_key = f"{symbol}:{timeframe}"
                
                if buffer_key not in self.buffers:
                    self.buffers[buffer_key] = deque(maxlen=1000)
                
                self.buffers[buffer_key].append(latest_candle)
                
                self.latest_prices[symbol] = latest_candle['close']
                
                self.storage.save_market_data(symbol, timeframe, [latest_candle])
                
                await self.cache.set_market_data(symbol, timeframe, latest_candle, expire=300)
                
                self._notify_subscribers(symbol, timeframe, latest_candle)
                
                logger.bind(data=True).debug(f"Updated data for {symbol} {timeframe}: {latest_candle['close']}")
                
        except Exception as e:
            logger.error(f"Error updating data: {e}")
    
    def get_buffer(self, symbol: str, timeframe: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get data from buffer.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            limit: Maximum number of candles to return
            
        Returns:
            List of candles
        """
        buffer_key = f"{symbol}:{timeframe}"
        
        if buffer_key not in self.buffers:
            return []
        
        buffer_data = list(self.buffers[buffer_key])
        
        if limit:
            return buffer_data[-limit:]
        
        return buffer_data
    
    def get_latest_price(self, symbol: str) -> Optional[float]:
        """
        Get latest price for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Latest price or None
        """
        return self.latest_prices.get(symbol)
    
    async def get_account_balance(self) -> Dict[str, Any]:
        """
        Get account balance from exchange.
        
        Returns:
            Balance dictionary
        """
        try:
            if not self.exchange:
                await self.initialize()
            
            balance = await self.exchange.fetch_balance()
            
            logger.bind(data=True).info("Fetched account balance")
            return balance
            
        except Exception as e:
            logger.error(f"Error fetching account balance: {e}")
            return {}
    
    async def get_open_positions(self) -> List[Dict[str, Any]]:
        """
        Get open positions from exchange.
        
        Returns:
            List of open positions
        """
        try:
            if not self.exchange:
                await self.initialize()
            
            if hasattr(self.exchange, 'fetch_positions'):
                positions = await self.exchange.fetch_positions()
                open_positions = [p for p in positions if float(p.get('contracts', 0)) > 0]
                logger.bind(data=True).info(f"Fetched {len(open_positions)} open positions")
                return open_positions
            
            return []
            
        except Exception as e:
            logger.error(f"Error fetching open positions: {e}")
            return []
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Get order book for a symbol.
        
        Args:
            symbol: Trading symbol
            limit: Depth limit
            
        Returns:
            Order book dictionary with bids and asks
        """
        try:
            if not self.exchange:
                await self.initialize()
            
            order_book = await self.exchange.fetch_order_book(symbol, limit=limit)
            
            logger.bind(data=True).debug(f"Fetched order book for {symbol}")
            return order_book
            
        except Exception as e:
            logger.error(f"Error fetching order book: {e}")
            return {'bids': [], 'asks': []}
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Get ticker data for a symbol.
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Ticker dictionary
        """
        try:
            if not self.exchange:
                await self.initialize()
            
            ticker = await self.exchange.fetch_ticker(symbol)
            
            logger.bind(data=True).debug(f"Fetched ticker for {symbol}")
            return ticker
            
        except Exception as e:
            logger.error(f"Error fetching ticker: {e}")
            return {}
    
    async def stream_loop(self, symbols: List[str], timeframes: List[str], update_interval: int = 60):
        """
        Main streaming loop for continuous data updates.
        
        Args:
            symbols: List of symbols to monitor
            timeframes: List of timeframes to monitor
            update_interval: Update interval in seconds
        """
        self.running = True
        logger.info(f"Starting data stream loop for {symbols} on {timeframes}")
        
        try:
            for symbol in symbols:
                for timeframe in timeframes:
                    await self.fetch_initial_data(symbol, timeframe)
                    await asyncio.sleep(1)  # Rate limiting
            
            while self.running:
                for symbol in symbols:
                    for timeframe in timeframes:
                        try:
                            await self.update_data(symbol, timeframe)
                        except Exception as e:
                            logger.error(f"Error updating {symbol} {timeframe}: {e}")
                        
                        await asyncio.sleep(0.5)  # Rate limiting between updates
                
                await asyncio.sleep(update_interval)
                
        except Exception as e:
            logger.error(f"Error in stream loop: {e}")
            raise
        finally:
            self.running = False
            logger.info("Data stream loop stopped")
    
    async def get_market_snapshot(self, symbol: str, timeframe: str, 
                                  calculate_indicators: bool = True) -> Optional[Dict[str, Any]]:
        """
        Get a complete market snapshot with OHLCV data and indicators.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            calculate_indicators: Whether to calculate technical indicators
            
        Returns:
            Market snapshot dictionary
        """
        try:
            buffer_data = self.get_buffer(symbol, timeframe)
            
            if not buffer_data:
                logger.warning(f"No data in buffer for {symbol} {timeframe}")
                return None
            
            import pandas as pd
            df = pd.DataFrame(buffer_data)
            
            if calculate_indicators:
                df = self.indicators.calculate_all(df)
                latest_indicators = self.indicators.get_latest_indicators(df)
                signal_summary = self.indicators.get_signal_summary(df)
            else:
                latest_indicators = {}
                signal_summary = {}
            
            latest_price = self.get_latest_price(symbol)
            
            snapshot = {
                'symbol': symbol,
                'timeframe': timeframe,
                'timestamp': datetime.utcnow(),
                'price': latest_price,
                'ohlcv_window': buffer_data[-100:],  # Last 100 candles
                'indicators': latest_indicators,
                'signals': signal_summary,
                'data_points': len(buffer_data)
            }
            
            await self.cache.set(f"snapshot:{symbol}:{timeframe}", snapshot, expire=60)
            
            return snapshot
            
        except Exception as e:
            logger.error(f"Error creating market snapshot: {e}")
            return None
