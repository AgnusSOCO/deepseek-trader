"""
Technical Indicators Module

Calculates various technical indicators from OHLCV market data.
Supports SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP, and more.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import talib

from ..utils.logger import get_logger

logger = get_logger()


class TechnicalIndicators:
    """Calculate technical indicators from OHLCV data."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize technical indicators calculator.
        
        Args:
            config: Configuration dictionary for indicator parameters
        """
        self.config = config or {}
        logger.info("Technical indicators calculator initialized")
    
    def _validate_dataframe(self, df: pd.DataFrame) -> bool:
        """
        Validate that DataFrame has required columns.
        
        Args:
            df: DataFrame to validate
            
        Returns:
            True if valid, False otherwise
        """
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        return all(col in df.columns for col in required_columns)
    
    def calculate_sma(self, df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """
        Calculate Simple Moving Average.
        
        Args:
            df: DataFrame with OHLCV data
            periods: List of periods to calculate (default: [20, 50, 200])
            
        Returns:
            DataFrame with SMA columns added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        if periods is None:
            periods = self.config.get('sma', {}).get('periods', [20, 50, 200])
        
        df = df.copy()
        for period in periods:
            df[f'sma_{period}'] = talib.SMA(df['close'].values, timeperiod=period)
        
        logger.bind(data=True).debug(f"Calculated SMA for periods: {periods}")
        return df
    
    def calculate_ema(self, df: pd.DataFrame, periods: List[int] = None) -> pd.DataFrame:
        """
        Calculate Exponential Moving Average.
        
        Args:
            df: DataFrame with OHLCV data
            periods: List of periods to calculate (default: [12, 26, 50, 200])
            
        Returns:
            DataFrame with EMA columns added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        if periods is None:
            periods = self.config.get('ema', {}).get('periods', [12, 26, 50, 200])
        
        df = df.copy()
        for period in periods:
            df[f'ema_{period}'] = talib.EMA(df['close'].values, timeperiod=period)
        
        logger.bind(data=True).debug(f"Calculated EMA for periods: {periods}")
        return df
    
    def calculate_rsi(self, df: pd.DataFrame, period: int = None) -> pd.DataFrame:
        """
        Calculate Relative Strength Index.
        
        Args:
            df: DataFrame with OHLCV data
            period: RSI period (default: 14)
            
        Returns:
            DataFrame with RSI column added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        if period is None:
            period = self.config.get('rsi', {}).get('period', 14)
        
        df = df.copy()
        df['rsi'] = talib.RSI(df['close'].values, timeperiod=period)
        
        logger.bind(data=True).debug(f"Calculated RSI with period {period}")
        return df
    
    def calculate_macd(self, df: pd.DataFrame, fast: int = None, slow: int = None, 
                      signal: int = None) -> pd.DataFrame:
        """
        Calculate MACD (Moving Average Convergence Divergence).
        
        Args:
            df: DataFrame with OHLCV data
            fast: Fast period (default: 12)
            slow: Slow period (default: 26)
            signal: Signal period (default: 9)
            
        Returns:
            DataFrame with MACD columns added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        macd_config = self.config.get('macd', {})
        if fast is None:
            fast = macd_config.get('fast', 12)
        if slow is None:
            slow = macd_config.get('slow', 26)
        if signal is None:
            signal = macd_config.get('signal', 9)
        
        df = df.copy()
        macd, macd_signal, macd_hist = talib.MACD(
            df['close'].values,
            fastperiod=fast,
            slowperiod=slow,
            signalperiod=signal
        )
        
        df['macd'] = macd
        df['macd_signal'] = macd_signal
        df['macd_hist'] = macd_hist
        
        logger.bind(data=True).debug(f"Calculated MACD ({fast}, {slow}, {signal})")
        return df
    
    def calculate_bollinger_bands(self, df: pd.DataFrame, period: int = None, 
                                 std_dev: float = None) -> pd.DataFrame:
        """
        Calculate Bollinger Bands.
        
        Args:
            df: DataFrame with OHLCV data
            period: Period (default: 20)
            std_dev: Standard deviation multiplier (default: 2)
            
        Returns:
            DataFrame with Bollinger Bands columns added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        bb_config = self.config.get('bollinger_bands', {})
        if period is None:
            period = bb_config.get('period', 20)
        if std_dev is None:
            std_dev = bb_config.get('std_dev', 2)
        
        df = df.copy()
        upper, middle, lower = talib.BBANDS(
            df['close'].values,
            timeperiod=period,
            nbdevup=std_dev,
            nbdevdn=std_dev,
            matype=0
        )
        
        df['bb_upper'] = upper
        df['bb_middle'] = middle
        df['bb_lower'] = lower
        df['bb_width'] = (upper - lower) / middle * 100  # Percentage width
        
        logger.bind(data=True).debug(f"Calculated Bollinger Bands ({period}, {std_dev})")
        return df
    
    def calculate_atr(self, df: pd.DataFrame, period: int = None) -> pd.DataFrame:
        """
        Calculate Average True Range.
        
        Args:
            df: DataFrame with OHLCV data
            period: ATR period (default: 14)
            
        Returns:
            DataFrame with ATR column added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        if period is None:
            period = self.config.get('atr', {}).get('period', 14)
        
        df = df.copy()
        df['atr'] = talib.ATR(
            df['high'].values,
            df['low'].values,
            df['close'].values,
            timeperiod=period
        )
        
        logger.bind(data=True).debug(f"Calculated ATR with period {period}")
        return df
    
    def calculate_vwap(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate Volume Weighted Average Price.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with VWAP column added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        df = df.copy()
        
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        
        df['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
        
        logger.bind(data=True).debug("Calculated VWAP")
        return df
    
    def calculate_obv(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate On-Balance Volume.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with OBV column added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        df = df.copy()
        df['obv'] = talib.OBV(
            df['close'].values.astype(np.float64), 
            df['volume'].values.astype(np.float64)
        )
        
        logger.bind(data=True).debug("Calculated OBV")
        return df
    
    def calculate_stochastic(self, df: pd.DataFrame, k_period: int = None, 
                            d_period: int = None) -> pd.DataFrame:
        """
        Calculate Stochastic Oscillator.
        
        Args:
            df: DataFrame with OHLCV data
            k_period: K period (default: 14)
            d_period: D period (default: 3)
            
        Returns:
            DataFrame with Stochastic columns added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        stoch_config = self.config.get('stochastic', {})
        if k_period is None:
            k_period = stoch_config.get('k_period', 14)
        if d_period is None:
            d_period = stoch_config.get('d_period', 3)
        
        df = df.copy()
        slowk, slowd = talib.STOCH(
            df['high'].values,
            df['low'].values,
            df['close'].values,
            fastk_period=k_period,
            slowk_period=d_period,
            slowk_matype=0,
            slowd_period=d_period,
            slowd_matype=0
        )
        
        df['stoch_k'] = slowk
        df['stoch_d'] = slowd
        
        logger.bind(data=True).debug(f"Calculated Stochastic ({k_period}, {d_period})")
        return df
    
    def calculate_cci(self, df: pd.DataFrame, period: int = None) -> pd.DataFrame:
        """
        Calculate Commodity Channel Index.
        
        Args:
            df: DataFrame with OHLCV data
            period: CCI period (default: 20)
            
        Returns:
            DataFrame with CCI column added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        if period is None:
            period = self.config.get('cci', {}).get('period', 20)
        
        df = df.copy()
        df['cci'] = talib.CCI(
            df['high'].values,
            df['low'].values,
            df['close'].values,
            timeperiod=period
        )
        
        logger.bind(data=True).debug(f"Calculated CCI with period {period}")
        return df
    
    def calculate_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """
        Calculate Average Directional Index (for trend strength).
        
        Args:
            df: DataFrame with OHLCV data
            period: ADX period (default: 14)
            
        Returns:
            DataFrame with ADX column added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        df = df.copy()
        df['adx'] = talib.ADX(
            df['high'].values,
            df['low'].values,
            df['close'].values,
            timeperiod=period
        )
        
        logger.bind(data=True).debug(f"Calculated ADX with period {period}")
        return df
    
    def calculate_all(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate all configured technical indicators.
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            DataFrame with all indicator columns added
        """
        if not self._validate_dataframe(df):
            raise ValueError("DataFrame missing required columns")
        
        logger.info("Calculating all technical indicators")
        
        df = df.copy()
        
        df = self.calculate_sma(df)
        df = self.calculate_ema(df)
        
        df = self.calculate_rsi(df)
        df = self.calculate_macd(df)
        df = self.calculate_stochastic(df)
        df = self.calculate_cci(df)
        df = self.calculate_adx(df)
        
        df = self.calculate_bollinger_bands(df)
        df = self.calculate_atr(df)
        
        df = self.calculate_vwap(df)
        df = self.calculate_obv(df)
        
        logger.info("All technical indicators calculated")
        return df
    
    def get_latest_indicators(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Get the latest values of all indicators as a dictionary.
        
        Args:
            df: DataFrame with calculated indicators
            
        Returns:
            Dictionary of indicator names and their latest values
        """
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        
        exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume']
        indicator_cols = [col for col in df.columns if col not in exclude_cols]
        
        indicators = {}
        for col in indicator_cols:
            value = latest[col]
            if pd.notna(value):
                if isinstance(value, (np.integer, np.floating)):
                    indicators[col] = float(value)
                else:
                    indicators[col] = value
        
        return indicators
    
    def get_signal_summary(self, df: pd.DataFrame) -> Dict[str, str]:
        """
        Generate a summary of trading signals from indicators.
        
        Args:
            df: DataFrame with calculated indicators
            
        Returns:
            Dictionary of signal summaries
        """
        if df.empty or len(df) < 2:
            return {}
        
        latest = df.iloc[-1]
        signals = {}
        
        if 'rsi' in df.columns and pd.notna(latest['rsi']):
            rsi = latest['rsi']
            if rsi < 30:
                signals['rsi'] = 'oversold'
            elif rsi > 70:
                signals['rsi'] = 'overbought'
            else:
                signals['rsi'] = 'neutral'
        
        if 'macd' in df.columns and 'macd_signal' in df.columns:
            if pd.notna(latest['macd']) and pd.notna(latest['macd_signal']):
                if latest['macd'] > latest['macd_signal']:
                    signals['macd'] = 'bullish'
                else:
                    signals['macd'] = 'bearish'
        
        if all(col in df.columns for col in ['bb_upper', 'bb_lower', 'close']):
            if pd.notna(latest['bb_upper']) and pd.notna(latest['bb_lower']):
                close = latest['close']
                if close >= latest['bb_upper']:
                    signals['bollinger'] = 'overbought'
                elif close <= latest['bb_lower']:
                    signals['bollinger'] = 'oversold'
                else:
                    signals['bollinger'] = 'neutral'
        
        if 'ema_12' in df.columns and 'ema_26' in df.columns:
            if pd.notna(latest['ema_12']) and pd.notna(latest['ema_26']):
                if latest['ema_12'] > latest['ema_26']:
                    signals['ema_trend'] = 'bullish'
                else:
                    signals['ema_trend'] = 'bearish'
        
        if 'adx' in df.columns and pd.notna(latest['adx']):
            adx = latest['adx']
            if adx > 25:
                signals['trend_strength'] = 'strong'
            elif adx > 20:
                signals['trend_strength'] = 'moderate'
            else:
                signals['trend_strength'] = 'weak'
        
        return signals
