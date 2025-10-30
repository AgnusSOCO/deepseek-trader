"""
Real-Time Price Feed Service

Central service for fetching and managing real-time price data for all strategies.
Uses a hybrid approach for optimal performance:
- REST API fetch_ohlcv for candle data and indicators
- Fast background ticker polling (1-3s) for instant prices
- In-memory storage with optional Redis mirroring

This replaces simulated prices with actual market data.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import pandas as pd
import numpy as np
from collections import defaultdict
import ccxt.async_support as ccxt
import redis.asyncio as aioredis
import json

from ..data.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


@dataclass
class PriceSnapshot:
    """Latest price snapshot for a symbol"""
    symbol: str
    price: float
    bid: float
    ask: float
    volume_24h: float
    timestamp: datetime
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'symbol': self.symbol,
            'price': self.price,
            'bid': self.bid,
            'ask': self.ask,
            'volume_24h': self.volume_24h,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class OHLCVWindow:
    """Rolling OHLCV window for a symbol/timeframe"""
    symbol: str
    timeframe: str
    df: pd.DataFrame
    indicators: Dict[str, Any] = field(default_factory=dict)
    last_update: datetime = field(default_factory=datetime.now)
    last_candle_close: Optional[datetime] = None
    
    def get_latest_candle(self) -> Optional[Dict[str, Any]]:
        """Get the latest closed candle"""
        if self.df is None or len(self.df) == 0:
            return None
        
        latest = self.df.iloc[-1]
        return {
            'timestamp': latest.name,
            'open': float(latest['open']),
            'high': float(latest['high']),
            'low': float(latest['low']),
            'close': float(latest['close']),
            'volume': float(latest['volume'])
        }


class PriceFeed:
    """
    Central price feed service for real-time market data.
    
    Features:
    - Fast ticker polling (1-3s) for instant prices
    - OHLCV fetching with indicator calculation
    - In-memory storage with Redis mirroring
    - Shared across all strategies
    - Rate-limit aware
    """
    
    def __init__(
        self,
        exchange_id: str,
        api_key: str,
        api_secret: str,
        symbols: List[str],
        timeframes: List[str],
        ticker_poll_interval: float = 2.0,
        candle_lookback_bars: int = 500,
        redis_url: Optional[str] = None,
        testnet: bool = True
    ):
        """
        Initialize price feed service
        
        Args:
            exchange_id: Exchange name (mexc, binance, bybit)
            api_key: API key
            api_secret: API secret
            symbols: List of symbols to track (e.g., ['BTC/USDT', 'ETH/USDT'])
            timeframes: List of timeframes (e.g., ['5m', '15m', '1h'])
            ticker_poll_interval: Seconds between ticker polls (default 2.0)
            candle_lookback_bars: Number of historical bars to maintain
            redis_url: Redis URL for caching (optional)
            testnet: Use testnet/demo mode
        """
        self.exchange_id = exchange_id.lower()
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbols = symbols
        self.timeframes = timeframes
        self.ticker_poll_interval = ticker_poll_interval
        self.candle_lookback_bars = candle_lookback_bars
        self.redis_url = redis_url
        self.testnet = testnet
        
        self.exchange: Optional[ccxt.Exchange] = None
        self.redis: Optional[aioredis.Redis] = None
        
        self.price_snapshots: Dict[str, PriceSnapshot] = {}
        self.ohlcv_windows: Dict[Tuple[str, str], OHLCVWindow] = {}
        
        self.is_running = False
        self.ticker_task: Optional[asyncio.Task] = None
        self.candle_tasks: List[asyncio.Task] = []
        
        self.indicators_calculator = TechnicalIndicators()
        
        self._rate_limit_delay = 0.1
        self._last_request_time = datetime.now()
        
        logger.info(
            f"PriceFeed initialized: {exchange_id}, "
            f"symbols={symbols}, timeframes={timeframes}, "
            f"ticker_interval={ticker_poll_interval}s"
        )
    
    async def start(self) -> None:
        """Start the price feed service"""
        if self.is_running:
            logger.warning("PriceFeed already running")
            return
        
        self.is_running = True
        
        await self._initialize_exchange()
        
        if self.redis_url:
            await self._initialize_redis()
        
        await self._fetch_initial_ohlcv()
        
        self.ticker_task = asyncio.create_task(self._ticker_poll_loop())
        
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                task = asyncio.create_task(
                    self._candle_update_loop(symbol, timeframe)
                )
                self.candle_tasks.append(task)
        
        logger.info("✅ PriceFeed started successfully")
    
    async def stop(self) -> None:
        """Stop the price feed service"""
        logger.info("Stopping PriceFeed...")
        self.is_running = False
        
        if self.ticker_task:
            self.ticker_task.cancel()
            try:
                await self.ticker_task
            except asyncio.CancelledError:
                pass
        
        for task in self.candle_tasks:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        if self.exchange:
            await self.exchange.close()
        
        if self.redis:
            await self.redis.close()
        
        logger.info("✅ PriceFeed stopped")
    
    async def _initialize_exchange(self) -> None:
        """Initialize CCXT exchange with async support"""
        try:
            exchange_class = getattr(ccxt, self.exchange_id)
            
            config = {
                'apiKey': self.api_key,
                'secret': self.api_secret,
                'enableRateLimit': True,
                'options': {}
            }
            
            if self.exchange_id == 'mexc':
                config['options']['defaultType'] = 'spot'
                config['options']['adjustForTimeDifference'] = True
            elif self.exchange_id in ['binance', 'bybit']:
                config['options']['defaultType'] = 'future'
                if self.testnet:
                    config['options']['test'] = True
            
            self.exchange = exchange_class(config)
            
            if self.testnet and self.exchange_id in ['binance', 'bybit']:
                self.exchange.set_sandbox_mode(True)
            
            await self.exchange.load_markets()
            
            logger.info(f"✅ Exchange {self.exchange_id} initialized (testnet={self.testnet})")
        
        except Exception as e:
            logger.error(f"Failed to initialize exchange: {e}")
            raise
    
    async def _initialize_redis(self) -> None:
        """Initialize Redis connection"""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("✅ Redis connected")
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, continuing without Redis")
            self.redis = None
    
    async def _fetch_initial_ohlcv(self) -> None:
        """Fetch initial OHLCV data for all symbol/timeframe pairs"""
        logger.info("Fetching initial OHLCV data...")
        
        tasks = []
        for symbol in self.symbols:
            for timeframe in self.timeframes:
                tasks.append(self._fetch_ohlcv(symbol, timeframe, initial=True))
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
        logger.info(f"✅ Initial OHLCV data fetched for {len(tasks)} pairs")
    
    async def _ticker_poll_loop(self) -> None:
        """Background task to poll tickers for instant prices"""
        logger.info(f"Starting ticker poll loop (interval={self.ticker_poll_interval}s)")
        
        while self.is_running:
            try:
                await self._update_all_tickers()
                await asyncio.sleep(self.ticker_poll_interval)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in ticker poll loop: {e}")
                await asyncio.sleep(5)
    
    async def _update_all_tickers(self) -> None:
        """Update ticker prices for all symbols"""
        try:
            tasks = [self._fetch_ticker(symbol) for symbol in self.symbols]
            await asyncio.gather(*tasks, return_exceptions=True)
        
        except Exception as e:
            logger.error(f"Error updating tickers: {e}")
    
    async def _fetch_ticker(self, symbol: str) -> None:
        """Fetch ticker for a single symbol"""
        try:
            await self._rate_limit()
            
            ticker = await self.exchange.fetch_ticker(symbol)
            
            snapshot = PriceSnapshot(
                symbol=symbol,
                price=float(ticker.get('last', ticker.get('close', 0))),
                bid=float(ticker.get('bid', 0)),
                ask=float(ticker.get('ask', 0)),
                volume_24h=float(ticker.get('quoteVolume', 0)),
                timestamp=datetime.now()
            )
            
            self.price_snapshots[symbol] = snapshot
            
            if self.redis:
                await self._cache_price_to_redis(snapshot)
        
        except Exception as e:
            logger.error(f"Error fetching ticker for {symbol}: {e}")
    
    async def _candle_update_loop(self, symbol: str, timeframe: str) -> None:
        """Background task to update OHLCV on candle close"""
        logger.info(f"Starting candle update loop for {symbol} {timeframe}")
        
        timeframe_seconds = self._timeframe_to_seconds(timeframe)
        
        while self.is_running:
            try:
                now = datetime.now()
                next_candle_close = self._get_next_candle_close(now, timeframe_seconds)
                sleep_duration = (next_candle_close - now).total_seconds() + 5
                
                if sleep_duration > 0:
                    await asyncio.sleep(sleep_duration)
                
                await self._fetch_ohlcv(symbol, timeframe, initial=False)
            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in candle update loop {symbol} {timeframe}: {e}")
                await asyncio.sleep(60)
    
    async def _fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        initial: bool = False
    ) -> None:
        """Fetch OHLCV data and calculate indicators"""
        try:
            await self._rate_limit()
            
            limit = self.candle_lookback_bars if initial else 100
            
            ohlcv = await self.exchange.fetch_ohlcv(
                symbol,
                timeframe,
                limit=limit
            )
            
            if not ohlcv:
                logger.warning(f"No OHLCV data for {symbol} {timeframe}")
                return
            
            df = pd.DataFrame(
                ohlcv,
                columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
            )
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            key = (symbol, timeframe)
            
            if key in self.ohlcv_windows and not initial:
                existing_df = self.ohlcv_windows[key].df
                df = pd.concat([existing_df, df])
                df = df[~df.index.duplicated(keep='last')]
                df = df.tail(self.candle_lookback_bars)
            
            df = self._calculate_indicators(df)
            
            window = OHLCVWindow(
                symbol=symbol,
                timeframe=timeframe,
                df=df,
                indicators=self._extract_latest_indicators(df),
                last_update=datetime.now(),
                last_candle_close=df.index[-1] if len(df) > 0 else None
            )
            
            self.ohlcv_windows[key] = window
            
            if self.redis:
                await self._cache_ohlcv_to_redis(window)
            
            logger.debug(
                f"Updated OHLCV for {symbol} {timeframe}: "
                f"{len(df)} bars, last close: {window.last_candle_close}"
            )
        
        except Exception as e:
            logger.error(f"Error fetching OHLCV {symbol} {timeframe}: {e}")
    
    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators on OHLCV data"""
        try:
            df = self.indicators_calculator.calculate_rsi(df)
            df = self.indicators_calculator.calculate_ema(df, periods=[12, 26])
            df = self.indicators_calculator.calculate_macd(df)
            df = self.indicators_calculator.calculate_bollinger_bands(df)
            df = self.indicators_calculator.calculate_atr(df)
            df = self.indicators_calculator.calculate_adx(df)
            df = self.indicators_calculator.calculate_obv(df)
            df = self.indicators_calculator.calculate_vwap(df)
            
            df['sma_20'] = df['close'].rolling(window=20).mean()
            df['sma_50'] = df['close'].rolling(window=50).mean()
            df['sma_200'] = df['close'].rolling(window=200).mean()
            df['sma_5'] = df['close'].rolling(window=5).mean()
            df['std_dev'] = df['close'].rolling(window=20).std()
            
            df['volume_avg'] = df['volume'].rolling(window=20).mean()
            df['volume_trend'] = df['volume'].pct_change(periods=5) * 100
            df['price_change_pct'] = df['close'].pct_change() * 100
            df['roc'] = df['close'].pct_change(periods=5) * 100
            
            if 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'bb_middle' in df.columns:
                df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_middle']) * 100
            
            if 'macd_hist' in df.columns:
                df['macd_histogram'] = df['macd_hist']
            
            df['ema_12_prev'] = df['ema_12'].shift(1)
            df['ema_26_prev'] = df['ema_26'].shift(1)
            if 'macd_histogram' in df.columns:
                df['macd_histogram_prev'] = df['macd_histogram'].shift(1)
            
            df['donchian_high_20'] = df['high'].rolling(window=20).max()
            df['donchian_low_20'] = df['low'].rolling(window=20).min()
            df['donchian_high_10'] = df['high'].rolling(window=10).max()
            df['donchian_low_10'] = df['low'].rolling(window=10).min()
            
            df['keltner_middle'] = df['close'].ewm(span=20).mean()
            df['keltner_upper'] = df['keltner_middle'] + (2.0 * df['atr'])
            df['keltner_lower'] = df['keltner_middle'] - (2.0 * df['atr'])
            
            df = self._calculate_supertrend(df)
            df = self._calculate_ichimoku(df)
            df = self._calculate_rsi_2(df)
            
            df.ffill(inplace=True)
            df.bfill(inplace=True)
            
            return df
        
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            return df
    
    def _calculate_supertrend(self, df: pd.DataFrame, multiplier: float = 3.0) -> pd.DataFrame:
        """Calculate SuperTrend indicator"""
        try:
            hl2 = (df['high'] + df['low']) / 2
            atr = df['atr'].fillna(method='bfill').fillna(method='ffill').fillna(1.0)
            
            basic_ub = hl2 + (multiplier * atr)
            basic_lb = hl2 - (multiplier * atr)
            
            df['supertrend'] = basic_ub
            df['supertrend_direction'] = (df['close'] > df['supertrend']).astype(int)
            
            return df
        except Exception as e:
            logger.error(f"Error calculating SuperTrend: {e}")
            return df
    
    def _calculate_ichimoku(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Ichimoku Cloud indicators"""
        try:
            period9_high = df['high'].rolling(window=9).max()
            period9_low = df['low'].rolling(window=9).min()
            df['tenkan_sen'] = (period9_high + period9_low) / 2
            
            period26_high = df['high'].rolling(window=26).max()
            period26_low = df['low'].rolling(window=26).min()
            df['kijun_sen'] = (period26_high + period26_low) / 2
            
            df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(26)
            
            period52_high = df['high'].rolling(window=52).max()
            period52_low = df['low'].rolling(window=52).min()
            df['senkou_span_b'] = ((period52_high + period52_low) / 2).shift(26)
            
            df['chikou_span'] = df['close'].shift(-26)
            
            return df
        except Exception as e:
            logger.error(f"Error calculating Ichimoku: {e}")
            return df
    
    def _calculate_rsi_2(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate RSI(2) for Connors RSI"""
        try:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=2).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=2).mean()
            rs = gain / (loss + 1e-10)
            df['rsi_2'] = 100 - (100 / (1 + rs))
            return df
        except Exception as e:
            logger.error(f"Error calculating RSI(2): {e}")
            return df
    
    def _extract_latest_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Extract latest indicator values from dataframe"""
        if df is None or len(df) == 0:
            return {}
        
        latest = df.iloc[-1]
        indicators = {}
        
        for col in df.columns:
            if col not in ['open', 'high', 'low', 'close', 'volume']:
                try:
                    indicators[col] = float(latest[col]) if not pd.isna(latest[col]) else 0.0
                except:
                    indicators[col] = 0.0
        
        return indicators
    
    async def _cache_price_to_redis(self, snapshot: PriceSnapshot) -> None:
        """Cache price snapshot to Redis"""
        try:
            key = f"price:{snapshot.symbol}"
            await self.redis.setex(
                key,
                30,
                json.dumps(snapshot.to_dict())
            )
        except Exception as e:
            logger.error(f"Error caching price to Redis: {e}")
    
    async def _cache_ohlcv_to_redis(self, window: OHLCVWindow) -> None:
        """Cache OHLCV window to Redis"""
        try:
            key = f"ohlcv:{window.symbol}:{window.timeframe}"
            
            data = {
                'symbol': window.symbol,
                'timeframe': window.timeframe,
                'last_update': window.last_update.isoformat(),
                'last_candle_close': window.last_candle_close.isoformat() if window.last_candle_close else None,
                'latest_candle': window.get_latest_candle()
            }
            
            await self.redis.setex(
                key,
                300,
                json.dumps(data, default=str)
            )
            
            indicators_key = f"indicators:{window.symbol}:{window.timeframe}"
            await self.redis.setex(
                indicators_key,
                300,
                json.dumps(window.indicators, default=str)
            )
        
        except Exception as e:
            logger.error(f"Error caching OHLCV to Redis: {e}")
    
    async def _rate_limit(self) -> None:
        """Rate limiting to avoid exchange bans"""
        now = datetime.now()
        elapsed = (now - self._last_request_time).total_seconds()
        
        if elapsed < self._rate_limit_delay:
            await asyncio.sleep(self._rate_limit_delay - elapsed)
        
        self._last_request_time = datetime.now()
    
    def _timeframe_to_seconds(self, timeframe: str) -> int:
        """Convert timeframe string to seconds"""
        multipliers = {'m': 60, 'h': 3600, 'd': 86400}
        unit = timeframe[-1]
        value = int(timeframe[:-1])
        return value * multipliers.get(unit, 60)
    
    def _get_next_candle_close(self, now: datetime, timeframe_seconds: int) -> datetime:
        """Calculate next candle close time"""
        timestamp = int(now.timestamp())
        next_close = ((timestamp // timeframe_seconds) + 1) * timeframe_seconds
        return datetime.fromtimestamp(next_close)
    
    def get_latest_price(self, symbol: str) -> float:
        """
        Get latest price for a symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Latest price
        """
        snapshot = self.price_snapshots.get(symbol)
        if snapshot:
            return snapshot.price
        
        logger.warning(f"No price data for {symbol}, returning 0")
        return 0.0
    
    def get_price_snapshot(self, symbol: str) -> Optional[PriceSnapshot]:
        """Get full price snapshot for a symbol"""
        return self.price_snapshots.get(symbol)
    
    def get_ohlcv(self, symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
        """
        Get OHLCV dataframe for a symbol/timeframe
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe (e.g., '5m', '1h')
            
        Returns:
            DataFrame with OHLCV data and indicators
        """
        key = (symbol, timeframe)
        window = self.ohlcv_windows.get(key)
        
        if window:
            return window.df.copy()
        
        logger.warning(f"No OHLCV data for {symbol} {timeframe}")
        return None
    
    def get_indicators(self, symbol: str, timeframe: str) -> Dict[str, Any]:
        """
        Get latest indicator values for a symbol/timeframe
        
        Args:
            symbol: Trading pair symbol
            timeframe: Timeframe
            
        Returns:
            Dict of indicator values
        """
        key = (symbol, timeframe)
        window = self.ohlcv_windows.get(key)
        
        if window:
            return window.indicators.copy()
        
        logger.warning(f"No indicators for {symbol} {timeframe}")
        return {}
    
    def get_latest_candle(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """Get the latest closed candle for a symbol/timeframe"""
        key = (symbol, timeframe)
        window = self.ohlcv_windows.get(key)
        
        if window:
            return window.get_latest_candle()
        
        return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get price feed statistics"""
        return {
            'is_running': self.is_running,
            'exchange': self.exchange_id,
            'symbols': self.symbols,
            'timeframes': self.timeframes,
            'ticker_poll_interval': self.ticker_poll_interval,
            'price_snapshots_count': len(self.price_snapshots),
            'ohlcv_windows_count': len(self.ohlcv_windows),
            'redis_connected': self.redis is not None,
            'latest_prices': {
                symbol: snapshot.price
                for symbol, snapshot in self.price_snapshots.items()
            }
        }
    
    def get_multi_timeframe_data(
        self,
        symbol: str,
        timeframes: Optional[List[str]] = None,
        lookback_bars: int = 200
    ) -> Dict[str, pd.DataFrame]:
        """
        Get OHLCV data across multiple timeframes for nof1-style prompts
        
        Args:
            symbol: Trading pair symbol
            timeframes: List of timeframes (defaults to all available)
            lookback_bars: Number of bars to return per timeframe
            
        Returns:
            Dict mapping timeframe to DataFrame with OHLCV and indicators
        """
        if timeframes is None:
            timeframes = self.timeframes
        
        result = {}
        for tf in timeframes:
            actual_tf = tf
            if tf == '3m' and self.exchange_id == 'mexc':
                actual_tf = '5m'
                logger.debug(f"Using 5m data as fallback for 3m on MEXC")
            
            key = (symbol, actual_tf)
            window = self.ohlcv_windows.get(key)
            
            if window and window.df is not None:
                df = window.df.tail(lookback_bars).copy()
                result[tf] = df
            else:
                logger.warning(f"No data for {symbol} {tf}")
        
        return result
    
    def get_time_series_arrays(
        self,
        symbol: str,
        timeframes: Optional[List[str]] = None,
        lookback_bars: int = 50
    ) -> Dict[str, Dict[str, List[float]]]:
        """
        Get compact time-series arrays for LLM prompts (nof1-style)
        
        Returns data in format:
        {
            '1m': {
                'close': [100.1, 100.2, ...],
                'ema_12': [99.8, 99.9, ...],
                'rsi': [45.2, 46.1, ...],
                ...
            },
            '5m': {...},
            ...
        }
        
        Args:
            symbol: Trading pair symbol
            timeframes: List of timeframes
            lookback_bars: Number of recent bars to include
            
        Returns:
            Dict mapping timeframe to dict of indicator arrays
        """
        multi_tf_data = self.get_multi_timeframe_data(symbol, timeframes, lookback_bars)
        
        result = {}
        for tf, df in multi_tf_data.items():
            if df is None or len(df) == 0:
                continue
            
            tf_data = {}
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    tf_data[col] = df[col].fillna(0).tolist()
            
            indicator_cols = [
                'ema_12', 'ema_26', 'ema_20', 'ema_50',
                'macd', 'macd_signal', 'macd_hist',
                'rsi', 'rsi_7', 'rsi_14',
                'atr', 'adx',
                'bb_upper', 'bb_middle', 'bb_lower',
                'volume_avg', 'obv'
            ]
            
            for col in indicator_cols:
                if col in df.columns:
                    tf_data[col] = df[col].fillna(0).tolist()
            
            result[tf] = tf_data
        
        return result
    
    async def get_funding_rate(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get current funding rate for perpetual futures
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            Dict with funding rate info or None if not supported
        """
        try:
            await self._rate_limit()
            
            if not hasattr(self.exchange, 'fetch_funding_rate'):
                logger.debug(f"{self.exchange_id} does not support funding rates")
                return None
            
            funding = await self.exchange.fetch_funding_rate(symbol)
            
            return {
                'symbol': symbol,
                'funding_rate': float(funding.get('fundingRate', 0)),
                'funding_timestamp': funding.get('fundingTimestamp'),
                'next_funding_time': funding.get('nextFundingTime'),
                'info': funding.get('info', {})
            }
        
        except Exception as e:
            logger.debug(f"Error fetching funding rate for {symbol}: {e}")
            return None
    
    async def get_order_book(
        self,
        symbol: str,
        limit: int = 20
    ) -> Optional[Dict[str, Any]]:
        """
        Get order book snapshot for market depth analysis
        
        Args:
            symbol: Trading pair symbol
            limit: Number of levels to fetch (default 20)
            
        Returns:
            Dict with bids, asks, and depth metrics
        """
        try:
            await self._rate_limit()
            
            order_book = await self.exchange.fetch_order_book(symbol, limit=limit)
            
            bids = order_book.get('bids', [])
            asks = order_book.get('asks', [])
            
            bid_volume = sum(bid[1] for bid in bids) if bids else 0
            ask_volume = sum(ask[1] for ask in asks) if asks else 0
            
            imbalance = 0
            if bid_volume + ask_volume > 0:
                imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
            
            return {
                'symbol': symbol,
                'timestamp': order_book.get('timestamp'),
                'bids': bids[:5],  # Top 5 levels
                'asks': asks[:5],  # Top 5 levels
                'bid_volume': bid_volume,
                'ask_volume': ask_volume,
                'imbalance': imbalance,  # -1 (all asks) to +1 (all bids)
                'spread': asks[0][0] - bids[0][0] if bids and asks else 0,
                'spread_percent': ((asks[0][0] - bids[0][0]) / bids[0][0] * 100) if bids and asks else 0
            }
        
        except Exception as e:
            logger.error(f"Error fetching order book for {symbol}: {e}")
            return None
