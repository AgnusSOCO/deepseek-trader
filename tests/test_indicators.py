"""
Unit tests for Technical Indicators Module
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.data.indicators import TechnicalIndicators


@pytest.fixture
def sample_ohlcv_data():
    """Create sample OHLCV data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
    
    np.random.seed(42)
    close_prices = 100 + np.cumsum(np.random.randn(100) * 2)
    
    data = {
        'timestamp': dates,
        'open': close_prices + np.random.randn(100) * 0.5,
        'high': close_prices + np.abs(np.random.randn(100) * 1.5),
        'low': close_prices - np.abs(np.random.randn(100) * 1.5),
        'close': close_prices,
        'volume': np.random.randint(1000, 10000, 100)
    }
    
    return pd.DataFrame(data)


@pytest.fixture
def indicators():
    """Create TechnicalIndicators instance."""
    config = {
        'sma': {'periods': [20, 50]},
        'ema': {'periods': [12, 26]},
        'rsi': {'period': 14},
        'macd': {'fast': 12, 'slow': 26, 'signal': 9},
        'bollinger_bands': {'period': 20, 'std_dev': 2},
        'atr': {'period': 14}
    }
    return TechnicalIndicators(config)


class TestTechnicalIndicators:
    """Test suite for TechnicalIndicators class."""
    
    def test_initialization(self, indicators):
        """Test indicator initialization."""
        assert indicators is not None
        assert indicators.config is not None
    
    def test_validate_dataframe_valid(self, indicators, sample_ohlcv_data):
        """Test DataFrame validation with valid data."""
        assert indicators._validate_dataframe(sample_ohlcv_data) is True
    
    def test_validate_dataframe_invalid(self, indicators):
        """Test DataFrame validation with invalid data."""
        invalid_df = pd.DataFrame({'invalid': [1, 2, 3]})
        assert indicators._validate_dataframe(invalid_df) is False
    
    def test_calculate_sma(self, indicators, sample_ohlcv_data):
        """Test SMA calculation."""
        df = indicators.calculate_sma(sample_ohlcv_data, periods=[20])
        
        assert 'sma_20' in df.columns
        assert not df['sma_20'].isna().all()
        
        assert df['sma_20'].iloc[-1] > 0
    
    def test_calculate_ema(self, indicators, sample_ohlcv_data):
        """Test EMA calculation."""
        df = indicators.calculate_ema(sample_ohlcv_data, periods=[12, 26])
        
        assert 'ema_12' in df.columns
        assert 'ema_26' in df.columns
        assert not df['ema_12'].isna().all()
    
    def test_calculate_rsi(self, indicators, sample_ohlcv_data):
        """Test RSI calculation."""
        df = indicators.calculate_rsi(sample_ohlcv_data, period=14)
        
        assert 'rsi' in df.columns
        
        valid_rsi = df['rsi'].dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()
    
    def test_calculate_macd(self, indicators, sample_ohlcv_data):
        """Test MACD calculation."""
        df = indicators.calculate_macd(sample_ohlcv_data)
        
        assert 'macd' in df.columns
        assert 'macd_signal' in df.columns
        assert 'macd_hist' in df.columns
        
        valid_rows = df[['macd', 'macd_signal', 'macd_hist']].dropna()
        if len(valid_rows) > 0:
            calculated_hist = valid_rows['macd'] - valid_rows['macd_signal']
            np.testing.assert_array_almost_equal(
                calculated_hist.values,
                valid_rows['macd_hist'].values,
                decimal=5
            )
    
    def test_calculate_bollinger_bands(self, indicators, sample_ohlcv_data):
        """Test Bollinger Bands calculation."""
        df = indicators.calculate_bollinger_bands(sample_ohlcv_data)
        
        assert 'bb_upper' in df.columns
        assert 'bb_middle' in df.columns
        assert 'bb_lower' in df.columns
        assert 'bb_width' in df.columns
        
        valid_rows = df[['bb_upper', 'bb_middle', 'bb_lower']].dropna()
        if len(valid_rows) > 0:
            assert (valid_rows['bb_upper'] >= valid_rows['bb_middle']).all()
            assert (valid_rows['bb_middle'] >= valid_rows['bb_lower']).all()
    
    def test_calculate_atr(self, indicators, sample_ohlcv_data):
        """Test ATR calculation."""
        df = indicators.calculate_atr(sample_ohlcv_data, period=14)
        
        assert 'atr' in df.columns
        
        valid_atr = df['atr'].dropna()
        assert (valid_atr > 0).all()
    
    def test_calculate_vwap(self, indicators, sample_ohlcv_data):
        """Test VWAP calculation."""
        df = indicators.calculate_vwap(sample_ohlcv_data)
        
        assert 'vwap' in df.columns
        assert not df['vwap'].isna().all()
    
    def test_calculate_obv(self, indicators, sample_ohlcv_data):
        """Test OBV calculation."""
        df = indicators.calculate_obv(sample_ohlcv_data)
        
        assert 'obv' in df.columns
        assert not df['obv'].isna().all()
    
    def test_calculate_stochastic(self, indicators, sample_ohlcv_data):
        """Test Stochastic Oscillator calculation."""
        df = indicators.calculate_stochastic(sample_ohlcv_data)
        
        assert 'stoch_k' in df.columns
        assert 'stoch_d' in df.columns
        
        valid_k = df['stoch_k'].dropna()
        valid_d = df['stoch_d'].dropna()
        
        if len(valid_k) > 0:
            assert (valid_k >= 0).all()
            assert (valid_k <= 100).all()
        
        if len(valid_d) > 0:
            assert (valid_d >= 0).all()
            assert (valid_d <= 100).all()
    
    def test_calculate_cci(self, indicators, sample_ohlcv_data):
        """Test CCI calculation."""
        df = indicators.calculate_cci(sample_ohlcv_data, period=20)
        
        assert 'cci' in df.columns
        assert not df['cci'].isna().all()
    
    def test_calculate_adx(self, indicators, sample_ohlcv_data):
        """Test ADX calculation."""
        df = indicators.calculate_adx(sample_ohlcv_data, period=14)
        
        assert 'adx' in df.columns
        
        valid_adx = df['adx'].dropna()
        if len(valid_adx) > 0:
            assert (valid_adx >= 0).all()
            assert (valid_adx <= 100).all()
    
    def test_calculate_all(self, indicators, sample_ohlcv_data):
        """Test calculating all indicators at once."""
        df = indicators.calculate_all(sample_ohlcv_data)
        
        expected_indicators = [
            'sma_20', 'ema_12', 'rsi', 'macd', 'bb_upper', 
            'atr', 'vwap', 'obv', 'stoch_k', 'cci', 'adx'
        ]
        
        for indicator in expected_indicators:
            assert indicator in df.columns
    
    def test_get_latest_indicators(self, indicators, sample_ohlcv_data):
        """Test getting latest indicator values."""
        df = indicators.calculate_all(sample_ohlcv_data)
        latest = indicators.get_latest_indicators(df)
        
        assert isinstance(latest, dict)
        assert len(latest) > 0
        
        for key, value in latest.items():
            assert isinstance(value, (int, float))
    
    def test_get_signal_summary(self, indicators, sample_ohlcv_data):
        """Test getting signal summary."""
        df = indicators.calculate_all(sample_ohlcv_data)
        signals = indicators.get_signal_summary(df)
        
        assert isinstance(signals, dict)
        
        if 'rsi' in signals:
            assert signals['rsi'] in ['oversold', 'overbought', 'neutral']
        
        if 'macd' in signals:
            assert signals['macd'] in ['bullish', 'bearish']
        
        if 'bollinger' in signals:
            assert signals['bollinger'] in ['oversold', 'overbought', 'neutral']
    
    def test_empty_dataframe(self, indicators):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame()
        
        with pytest.raises(ValueError):
            indicators.calculate_sma(empty_df)
    
    def test_insufficient_data(self, indicators):
        """Test handling of insufficient data."""
        small_df = pd.DataFrame({
            'timestamp': pd.date_range(start='2024-01-01', periods=5, freq='1H'),
            'open': [100, 101, 102, 103, 104],
            'high': [101, 102, 103, 104, 105],
            'low': [99, 100, 101, 102, 103],
            'close': [100, 101, 102, 103, 104],
            'volume': [1000, 1100, 1200, 1300, 1400]
        })
        
        df = indicators.calculate_all(small_df)
        assert df is not None
        assert len(df) == 5


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
