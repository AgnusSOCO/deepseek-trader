"""
Generate realistic synthetic historical data for backtesting

Creates data that mimics real cryptocurrency market behavior including:
- Trending periods
- Volatile periods
- Mean-reverting periods
- Realistic volume patterns
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backtesting.data_downloader import DataDownloader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def generate_realistic_price_series(
    num_bars: int,
    start_price: float,
    trend: float = 0.0001,
    volatility: float = 0.01,
    mean_reversion_strength: float = 0.1
) -> np.ndarray:
    """
    Generate realistic price series with trend, volatility, and mean reversion
    
    Args:
        num_bars: Number of price bars
        start_price: Starting price
        trend: Drift/trend component
        volatility: Volatility (std dev of returns)
        mean_reversion_strength: Strength of mean reversion (0-1)
    
    Returns:
        Array of prices
    """
    np.random.seed(42)
    
    prices = np.zeros(num_bars)
    prices[0] = start_price
    
    for i in range(1, num_bars):
        shock = np.random.normal(0, volatility)
        
        log_price = np.log(prices[i-1])
        log_start = np.log(start_price)
        mean_reversion = -mean_reversion_strength * (log_price - log_start)
        
        ret = trend + shock + mean_reversion
        
        prices[i] = prices[i-1] * np.exp(ret)
    
    return prices


def add_market_regimes(prices: np.ndarray) -> np.ndarray:
    """
    Add different market regimes (bull, bear, sideways) to price series
    
    Args:
        prices: Base price series
    
    Returns:
        Modified price series with regimes
    """
    num_bars = len(prices)
    regime_length = num_bars // 5
    
    regimes = [
        {'trend': 0.0003, 'volatility': 0.008},  # Bull market
        {'trend': -0.0002, 'volatility': 0.015},  # Bear market
        {'trend': 0.0, 'volatility': 0.005},      # Sideways
        {'trend': 0.0002, 'volatility': 0.012},   # Volatile bull
        {'trend': 0.0001, 'volatility': 0.006}    # Slow growth
    ]
    
    modified_prices = prices.copy()
    
    for i, regime in enumerate(regimes):
        start_idx = i * regime_length
        end_idx = min((i + 1) * regime_length, num_bars)
        
        for j in range(start_idx + 1, end_idx):
            shock = np.random.normal(0, regime['volatility'])
            ret = regime['trend'] + shock
            modified_prices[j] = modified_prices[j-1] * np.exp(ret)
    
    return modified_prices


def generate_ohlcv_from_close(close_prices: np.ndarray) -> dict:
    """
    Generate OHLCV data from close prices
    
    Args:
        close_prices: Array of close prices
    
    Returns:
        Dict with OHLCV arrays
    """
    num_bars = len(close_prices)
    
    high = close_prices * (1 + np.abs(np.random.normal(0, 0.005, num_bars)))
    low = close_prices * (1 - np.abs(np.random.normal(0, 0.005, num_bars)))
    open_prices = np.roll(close_prices, 1)
    open_prices[0] = close_prices[0]
    
    volatility = np.abs(np.diff(np.log(close_prices), prepend=np.log(close_prices[0])))
    base_volume = 1000
    volume = base_volume * (1 + volatility * 100) * np.random.uniform(0.8, 1.2, num_bars)
    
    return {
        'open': open_prices,
        'high': high,
        'low': low,
        'close': close_prices,
        'volume': volume
    }


def generate_data_for_timeframe(
    symbol: str,
    timeframe: str,
    start_date: str,
    end_date: str,
    start_price: float
) -> pd.DataFrame:
    """
    Generate synthetic data for a specific timeframe
    
    Args:
        symbol: Trading pair symbol
        timeframe: Timeframe (5m, 15m, 1h, etc.)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        start_price: Starting price
    
    Returns:
        DataFrame with OHLCV data and indicators
    """
    logger.info(f"Generating {symbol} {timeframe} data")
    
    start_dt = datetime.strptime(start_date, '%Y-%m-%d')
    end_dt = datetime.strptime(end_date, '%Y-%m-%d')
    
    timeframe_minutes = {
        '1m': 1,
        '5m': 5,
        '15m': 15,
        '1h': 60,
        '4h': 240,
        '1d': 1440
    }
    
    minutes = timeframe_minutes.get(timeframe, 60)
    total_minutes = int((end_dt - start_dt).total_seconds() / 60)
    num_bars = total_minutes // minutes
    
    logger.info(f"Generating {num_bars} bars")
    
    close_prices = generate_realistic_price_series(
        num_bars=num_bars,
        start_price=start_price,
        trend=0.0001,
        volatility=0.01,
        mean_reversion_strength=0.05
    )
    
    close_prices = add_market_regimes(close_prices)
    
    ohlcv = generate_ohlcv_from_close(close_prices)
    
    timestamps = pd.date_range(
        start=start_dt,
        periods=num_bars,
        freq=f'{minutes}min'
    )
    
    df = pd.DataFrame({
        'open': ohlcv['open'],
        'high': ohlcv['high'],
        'low': ohlcv['low'],
        'close': ohlcv['close'],
        'volume': ohlcv['volume']
    }, index=timestamps)
    
    logger.info(f"Generated {len(df)} bars from {df.index[0]} to {df.index[-1]}")
    
    return df


def main():
    """Generate synthetic historical data"""
    downloader = DataDownloader('binance')  # Just for indicator calculation
    
    symbols_config = {
        'BTC/USDT': 50000.0,
        'ETH/USDT': 3000.0
    }
    
    timeframes = ['5m', '15m', '1h']
    
    start_date = '2024-06-01'
    end_date = '2024-12-01'
    
    for symbol, start_price in symbols_config.items():
        for timeframe in timeframes:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Processing {symbol} {timeframe}")
                logger.info(f"{'='*60}")
                
                df = generate_data_for_timeframe(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date,
                    start_price=start_price
                )
                
                validation = downloader.validate_data(df)
                logger.info(f"Validation: {validation['total_rows']} rows")
                
                logger.info("Calculating technical indicators...")
                df = downloader.add_indicators(df)
                
                downloader.save_data(df, symbol, timeframe, format='csv')
                
                logger.info(f"✓ Successfully generated and saved {symbol} {timeframe}")
                logger.info(f"  Final rows: {len(df)}")
                logger.info(f"  Price range: ${df['close'].min():.2f} - ${df['close'].max():.2f}")
                logger.info(f"  Date range: {df.index[0]} to {df.index[-1]}\n")
                
            except Exception as e:
                logger.error(f"✗ Error generating {symbol} {timeframe}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    logger.info("\n" + "="*60)
    logger.info("Synthetic data generation complete!")
    logger.info("="*60)


if __name__ == '__main__':
    main()
