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
        
        df['donchian_high_20'] = df['high'].rolling(window=20).max()
        df['donchian_low_20'] = df['low'].rolling(window=20).min()
        df['donchian_high_10'] = df['high'].rolling(window=10).max()
        df['donchian_low_10'] = df['low'].rolling(window=10).min()
        
        df['keltner_middle'] = df['close'].ewm(span=20).mean()
        df['keltner_upper'] = df['keltner_middle'] + (2.0 * df['atr'])
        df['keltner_lower'] = df['keltner_middle'] - (2.0 * df['atr'])
        
        df = self._calculate_supertrend(df, multiplier=3.0, period=10)
        
        df = self._calculate_ichimoku(df)
        
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=2).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=2).mean()
        rs = gain / (loss + 1e-10)
        df['rsi_2'] = 100 - (100 / (1 + rs))
        
        df['sma_200'] = df['close'].rolling(window=200).mean()
        df['sma_5'] = df['close'].rolling(window=5).mean()
        
        if len(df) > 12:  # Need at least 12 bars for EMA12
            df_1h = df['close'].resample('1H').last().dropna()
            if len(df_1h) >= 26:  # Need at least 26 bars for EMA26
                ema_12_1h = df_1h.ewm(span=12, adjust=False).mean()
                ema_26_1h = df_1h.ewm(span=26, adjust=False).mean()
                
                df['ema_12_1h'] = ema_12_1h.reindex(df.index, method='ffill')
                df['ema_26_1h'] = ema_26_1h.reindex(df.index, method='ffill')
                
                df['trend_1h'] = (df['ema_12_1h'] > df['ema_26_1h']).astype(int)
                
                logger.info("Added HTF (1h) indicators for trend confirmation")
            else:
                df['ema_12_1h'] = df['ema_12']
                df['ema_26_1h'] = df['ema_26']
                df['trend_1h'] = (df['ema_12'] > df['ema_26']).astype(int)
        else:
            df['ema_12_1h'] = df['ema_12']
            df['ema_26_1h'] = df['ema_26']
            df['trend_1h'] = (df['ema_12'] > df['ema_26']).astype(int)
        
        df.ffill(inplace=True)
        df.bfill(inplace=True)
        
        df.dropna(inplace=True)
        
        logger.info(f"Added indicators, {len(df)} rows remaining after dropna")
        
        return df
    
    def _calculate_supertrend(self, df: pd.DataFrame, multiplier: float = 3.0, period: int = 10) -> pd.DataFrame:
        """Calculate SuperTrend indicator"""
        hl2 = (df['high'] + df['low']) / 2
        atr = df['atr'].bfill().ffill().fillna(1.0)
        
        basic_ub = hl2 + (multiplier * atr)
        basic_lb = hl2 - (multiplier * atr)
        
        final_ub = basic_ub.copy()
        final_lb = basic_lb.copy()
        
        for i in range(1, len(df)):
            if pd.isna(basic_ub.iloc[i]) or pd.isna(final_ub.iloc[i-1]):
                continue
            if basic_ub.iloc[i] < final_ub.iloc[i-1] or df['close'].iloc[i-1] > final_ub.iloc[i-1]:
                final_ub.iloc[i] = basic_ub.iloc[i]
            else:
                final_ub.iloc[i] = final_ub.iloc[i-1]
            
            if pd.isna(basic_lb.iloc[i]) or pd.isna(final_lb.iloc[i-1]):
                continue
            if basic_lb.iloc[i] > final_lb.iloc[i-1] or df['close'].iloc[i-1] < final_lb.iloc[i-1]:
                final_lb.iloc[i] = basic_lb.iloc[i]
            else:
                final_lb.iloc[i] = final_lb.iloc[i-1]
        
        supertrend = pd.Series(index=df.index, dtype=float)
        supertrend.iloc[0] = final_ub.iloc[0]
        
        for i in range(1, len(df)):
            if pd.isna(supertrend.iloc[i-1]) or pd.isna(final_ub.iloc[i-1]):
                supertrend.iloc[i] = final_ub.iloc[i]
                continue
                
            if supertrend.iloc[i-1] == final_ub.iloc[i-1] and df['close'].iloc[i] <= final_ub.iloc[i]:
                supertrend.iloc[i] = final_ub.iloc[i]
            elif supertrend.iloc[i-1] == final_ub.iloc[i-1] and df['close'].iloc[i] > final_ub.iloc[i]:
                supertrend.iloc[i] = final_lb.iloc[i]
            elif supertrend.iloc[i-1] == final_lb.iloc[i-1] and df['close'].iloc[i] >= final_lb.iloc[i]:
                supertrend.iloc[i] = final_lb.iloc[i]
            elif supertrend.iloc[i-1] == final_lb.iloc[i-1] and df['close'].iloc[i] < final_lb.iloc[i]:
                supertrend.iloc[i] = final_ub.iloc[i]
            else:
                supertrend.iloc[i] = supertrend.iloc[i-1]
        
        df['supertrend'] = supertrend
        df['supertrend_direction'] = (df['close'] > df['supertrend']).astype(int)
        
        return df
    
    def _calculate_ichimoku(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate Ichimoku Cloud indicators"""
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
