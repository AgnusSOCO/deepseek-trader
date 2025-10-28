"""
Script to download historical data for backtesting
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from src.backtesting.data_downloader import DataDownloader

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Download historical data for backtesting"""
    downloader = DataDownloader('binance')
    
    symbols = ['BTC/USDT', 'ETH/USDT']
    timeframes = ['1m', '5m', '15m', '1h', '4h', '1d']
    
    start_date = '2023-01-01'
    end_date = '2024-12-31'
    
    for symbol in symbols:
        for timeframe in timeframes:
            try:
                logger.info(f"Downloading {symbol} {timeframe}")
                
                df = downloader.download_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date
                )
                
                validation = downloader.validate_data(df)
                logger.info(f"Validation: {validation['total_rows']} rows, {len(validation['gaps'])} gaps")
                
                df = downloader.add_indicators(df)
                
                downloader.save_data(df, symbol, timeframe, format='csv')
                
                logger.info(f"Successfully downloaded and saved {symbol} {timeframe}\n")
                
            except Exception as e:
                logger.error(f"Error downloading {symbol} {timeframe}: {e}")
                continue


if __name__ == '__main__':
    main()
