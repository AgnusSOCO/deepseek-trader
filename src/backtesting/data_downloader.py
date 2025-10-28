"""
Historical Data Downloader

Download and prepare historical cryptocurrency data for backtesting.
"""

import logging
from typing import Dict, Any, List, Optional
import pandas as pd
import ccxt
from datetime import datetime, timedelta
import time
import os

from ..data.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


class DataDownloader:
    """
    Download historical OHLCV data from exchanges
    
    Features:
    - Download multiple timeframes
    - Data validation
    - Gap detection
    - Indicator calculation
    - Data storage (CSV/Parquet)
    """
    
    def __init__(self, exchange_id: str = 'binance'):
        """
        Initialize data downloader
        
        Args:
            exchange_id: CCXT exchange ID
        """
        self.exchange_id = exchange_id
        self.exchange = getattr(ccxt, exchange_id)({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        
        logger.info(f"DataDownloader initialized with {exchange_id}")
    
    def download_historical_data(
        self,
        symbol: str,
        timeframe: str,
        start_date: str,
        end_date: Optional[str] = None,
        limit: int = 1000
    ) -> pd.DataFrame:
        """
        Download historical OHLCV data
        
        Args:
            symbol: Trading pair (e.g., 'BTC/USDT')
            timeframe: Timeframe (e.g., '1m', '5m', '1h', '1d')
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD), defaults to now
            limit: Number of candles per request
        
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(
            f"Downloading {symbol} {timeframe} data from {start_date} to {end_date or 'now'}"
        )
        
        start_ts = int(datetime.strptime(start_date, '%Y-%m-%d').timestamp() * 1000)
        if end_date:
            end_ts = int(datetime.strptime(end_date, '%Y-%m-%d').timestamp() * 1000)
        else:
            end_ts = int(datetime.now().timestamp() * 1000)
        
        all_candles = []
        current_ts = start_ts
        
        while current_ts < end_ts:
            try:
                candles = self.exchange.fetch_ohlcv(
                    symbol,
                    timeframe,
                    since=current_ts,
                    limit=limit
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                
                current_ts = candles[-1][0] + 1
                
                logger.debug(
                    f"Downloaded {len(candles)} candles, "
                    f"last timestamp: {datetime.fromtimestamp(candles[-1][0]/1000)}"
                )
                
                time.sleep(self.exchange.rateLimit / 1000)
                
                if candles[-1][0] >= end_ts:
                    break
                
            except Exception as e:
                logger.error(f"Error downloading data: {e}")
                time.sleep(5)
                continue
        
        df = pd.DataFrame(
            all_candles,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        df = df[~df.index.duplicated(keep='first')]
        
        df.sort_index(inplace=True)
        
        logger.info(
            f"Downloaded {len(df)} candles from {df.index[0]} to {df.index[-1]}"
        )
        
        return df
    
    def validate_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Validate data quality
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            Dict with validation results
        """
        validation = {
            'total_rows': len(df),
            'start_date': df.index[0],
            'end_date': df.index[-1],
            'missing_values': df.isnull().sum().to_dict(),
            'gaps': [],
            'outliers': []
        }
        
        time_diffs = df.index.to_series().diff()
        expected_diff = time_diffs.mode()[0]
        gaps = time_diffs[time_diffs > expected_diff * 1.5]
        
        if len(gaps) > 0:
            validation['gaps'] = [
                {
                    'timestamp': str(ts),
                    'gap_size': str(diff)
                }
                for ts, diff in gaps.items()
            ]
        
        price_changes = df['close'].pct_change()
        outliers = price_changes[abs(price_changes) > 0.2]  # 20% change
        
        if len(outliers) > 0:
            validation['outliers'] = [
                {
                    'timestamp': str(ts),
                    'change_pct': float(change * 100)
                }
                for ts, change in outliers.items()
            ]
        
        logger.info(
            f"Data validation: {validation['total_rows']} rows, "
            f"{len(validation['gaps'])} gaps, "
            f"{len(validation['outliers'])} outliers"
        )
        
        return validation
    
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add technical indicators to data
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            DataFrame with indicators added
        """
        logger.info("Calculating technical indicators")
        
        indicators = TechnicalIndicators()
        
        df = indicators.calculate_rsi(df)
        df = indicators.calculate_ema(df, periods=[12, 26])
        df = indicators.calculate_macd(df)
        df = indicators.calculate_bollinger_bands(df)
        df = indicators.calculate_atr(df)
        df = indicators.calculate_adx(df)
        df = indicators.calculate_obv(df)
        df = indicators.calculate_vwap(df)
        
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['sma_50'] = df['close'].rolling(window=50).mean()
        df['std_dev'] = df['close'].rolling(window=20).std()
        
        df['volume_avg'] = df['volume'].rolling(window=20).mean()
        df['volume_trend'] = df['volume'].pct_change(periods=5) * 100
        df['price_change_pct'] = df['close'].pct_change() * 100
        df['roc'] = df['close'].pct_change(periods=5) * 100  # Rate of change
        
        if 'bb_width' not in df.columns and 'bb_upper' in df.columns and 'bb_lower' in df.columns and 'bb_middle' in df.columns:
            df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_middle']) * 100
        
        if 'macd_hist' in df.columns:
            df['macd_histogram'] = df['macd_hist']
        
        df['ema_12_prev'] = df['ema_12'].shift(1)
        df['ema_26_prev'] = df['ema_26'].shift(1)
        df['macd_histogram_prev'] = df['macd_histogram'].shift(1)
        
        # Note: plus_di and minus_di are not calculated by TechnicalIndicators
        df['plus_di'] = 0.0
        df['minus_di'] = 0.0
        
        # Drop NaN rows from indicator calculation
        df.dropna(inplace=True)
        
        logger.info(f"Added indicators, {len(df)} rows remaining after dropna")
        
        return df
    
    def save_data(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        format: str = 'csv',
        output_dir: str = 'data/historical'
    ):
        """
        Save data to file
        
        Args:
            df: DataFrame to save
            symbol: Trading pair
            timeframe: Timeframe
            format: File format ('csv' or 'parquet')
            output_dir: Output directory
        """
        os.makedirs(output_dir, exist_ok=True)
        
        symbol_clean = symbol.replace('/', '_')
        filename = f"{symbol_clean}_{timeframe}.{format}"
        filepath = os.path.join(output_dir, filename)
        
        if format == 'csv':
            df.to_csv(filepath)
        elif format == 'parquet':
            df.to_parquet(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Data saved to {filepath}")
    
    def load_data(
        self,
        symbol: str,
        timeframe: str,
        format: str = 'csv',
        data_dir: str = 'data/historical'
    ) -> pd.DataFrame:
        """
        Load data from file
        
        Args:
            symbol: Trading pair
            timeframe: Timeframe
            format: File format ('csv' or 'parquet')
            data_dir: Data directory
        
        Returns:
            DataFrame with data
        """
        symbol_clean = symbol.replace('/', '_')
        filename = f"{symbol_clean}_{timeframe}.{format}"
        filepath = os.path.join(data_dir, filename)
        
        if format == 'csv':
            df = pd.read_csv(filepath, index_col=0, parse_dates=True)
        elif format == 'parquet':
            df = pd.read_parquet(filepath)
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        logger.info(f"Loaded {len(df)} rows from {filepath}")
        
        return df
