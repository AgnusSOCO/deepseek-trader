"""
Script to download sample historical data for backtesting
Downloads 6 months of data for key timeframes
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
    """Download sample historical data for backtesting"""
    downloader = DataDownloader('binance')
    
    symbols = ['BTC/USDT', 'ETH/USDT']
    timeframes = ['5m', '15m', '1h']  # Key timeframes for our strategies
    
    start_date = '2024-06-01'
    end_date = '2024-12-01'
    
    for symbol in symbols:
        for timeframe in timeframes:
            try:
                logger.info(f"\n{'='*60}")
                logger.info(f"Downloading {symbol} {timeframe}")
                logger.info(f"{'='*60}")
                
                df = downloader.download_historical_data(
                    symbol=symbol,
                    timeframe=timeframe,
                    start_date=start_date,
                    end_date=end_date
                )
                
                logger.info(f"Downloaded {len(df)} candles")
                
                validation = downloader.validate_data(df)
                logger.info(f"Validation: {validation['total_rows']} rows, {len(validation['gaps'])} gaps")
                
                if validation['gaps']:
                    logger.warning(f"Found {len(validation['gaps'])} gaps in data")
                
                logger.info("Calculating technical indicators...")
                df = downloader.add_indicators(df)
                
                downloader.save_data(df, symbol, timeframe, format='csv')
                
                logger.info(f"✓ Successfully downloaded and saved {symbol} {timeframe}")
                logger.info(f"  Final rows: {len(df)}")
                logger.info(f"  Date range: {df.index[0]} to {df.index[-1]}\n")
                
            except Exception as e:
                logger.error(f"✗ Error downloading {symbol} {timeframe}: {e}")
                import traceback
                traceback.print_exc()
                continue
    
    logger.info("\n" + "="*60)
    logger.info("Data download complete!")
    logger.info("="*60)


if __name__ == '__main__':
    main()
