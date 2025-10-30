"""
Test script for real-time price feed integration

This script tests the PriceFeed service with a live exchange connection
to verify that real-time price data is being fetched correctly.
"""

import asyncio
import logging
import os
from dotenv import load_dotenv

from src.data.price_feed import PriceFeed

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_price_feed():
    """Test PriceFeed with live exchange connection"""
    
    load_dotenv()
    
    exchange_id = os.getenv('PRICEFEED_EXCHANGE', 'mexc')
    api_key = os.getenv(f'{exchange_id.upper()}_API_KEY', 'test_key')
    api_secret = os.getenv(f'{exchange_id.upper()}_API_SECRET', 'test_secret')
    symbols = os.getenv('TRADING_SYMBOLS', 'BTC/USDT,ETH/USDT').split(',')
    timeframes = os.getenv('TRADING_TIMEFRAMES', '5m,15m,1h').split(',')
    ticker_poll_interval = float(os.getenv('PRICEFEED_TICKER_POLL_SEC', '2.0'))
    candle_lookback = int(os.getenv('PRICEFEED_CANDLE_LOOKBACK', '500'))
    redis_url = os.getenv('REDIS_URL', None)
    testnet = os.getenv('PRICEFEED_TESTNET', 'true').lower() == 'true'
    
    logger.info("=" * 80)
    logger.info("🧪 TESTING PRICEFEED SERVICE")
    logger.info("=" * 80)
    logger.info(f"Exchange: {exchange_id}")
    logger.info(f"Symbols: {symbols}")
    logger.info(f"Timeframes: {timeframes}")
    logger.info(f"Ticker Poll Interval: {ticker_poll_interval}s")
    logger.info(f"Candle Lookback: {candle_lookback}")
    logger.info(f"Redis URL: {redis_url}")
    logger.info(f"Testnet: {testnet}")
    logger.info("=" * 80)
    
    price_feed = PriceFeed(
        exchange_id=exchange_id,
        api_key=api_key,
        api_secret=api_secret,
        symbols=symbols,
        timeframes=timeframes,
        ticker_poll_interval=ticker_poll_interval,
        candle_lookback_bars=candle_lookback,
        redis_url=redis_url,
        testnet=testnet
    )
    
    try:
        logger.info("\n🔌 Starting PriceFeed service...")
        await price_feed.start()
        logger.info("✅ PriceFeed service started successfully")
        
        logger.info("\n⏳ Waiting 10 seconds for data to populate...")
        await asyncio.sleep(10)
        
        logger.info("\n📊 Testing price data retrieval...")
        
        for symbol in symbols:
            logger.info(f"\n--- {symbol} ---")
            
            latest_price = price_feed.get_latest_price(symbol)
            logger.info(f"Latest Price: ${latest_price:,.2f}")
            
            if latest_price == 0:
                logger.error(f"❌ FAILED: No price data for {symbol}")
                continue
            else:
                logger.info(f"✅ PASSED: Got real-time price for {symbol}")
            
            snapshot = price_feed.get_price_snapshot(symbol)
            if snapshot:
                logger.info(f"Bid: ${snapshot.bid:,.2f}")
                logger.info(f"Ask: ${snapshot.ask:,.2f}")
                logger.info(f"24h Volume: ${snapshot.volume_24h:,.2f}")
                logger.info(f"Timestamp: {snapshot.timestamp}")
            
            for timeframe in timeframes:
                logger.info(f"\n  Timeframe: {timeframe}")
                
                df = price_feed.get_ohlcv(symbol, timeframe)
                if df is not None and len(df) > 0:
                    logger.info(f"  ✅ OHLCV Data: {len(df)} candles")
                    logger.info(f"  Latest Close: ${df['close'].iloc[-1]:,.2f}")
                    logger.info(f"  Latest Volume: {df['volume'].iloc[-1]:,.2f}")
                else:
                    logger.error(f"  ❌ FAILED: No OHLCV data for {symbol} {timeframe}")
                    continue
                
                indicators = price_feed.get_indicators(symbol, timeframe)
                if indicators:
                    logger.info(f"  ✅ Indicators: {len(indicators)} calculated")
                    logger.info(f"  RSI: {indicators.get('rsi', 0):.2f}")
                    logger.info(f"  EMA 12: ${indicators.get('ema_12', 0):,.2f}")
                    logger.info(f"  EMA 26: ${indicators.get('ema_26', 0):,.2f}")
                    logger.info(f"  MACD: {indicators.get('macd', 0):.4f}")
                    logger.info(f"  ATR: {indicators.get('atr', 0):.2f}")
                else:
                    logger.error(f"  ❌ FAILED: No indicators for {symbol} {timeframe}")
                    continue
                
                latest_candle = price_feed.get_latest_candle(symbol, timeframe)
                if latest_candle:
                    logger.info(f"  Latest Candle Close: ${latest_candle['close']:,.2f}")
                    logger.info(f"  Latest Candle Timestamp: {latest_candle['timestamp']}")
        
        logger.info("\n📈 PriceFeed Statistics:")
        stats = price_feed.get_statistics()
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        logger.info("\n✅ ALL TESTS PASSED!")
        logger.info("Real-time price feed is working correctly")
        
    except Exception as e:
        logger.error(f"\n❌ TEST FAILED: {e}", exc_info=True)
        raise
    
    finally:
        logger.info("\n🔌 Stopping PriceFeed service...")
        await price_feed.stop()
        logger.info("✅ PriceFeed service stopped")
        logger.info("=" * 80)


if __name__ == '__main__':
    asyncio.run(test_price_feed())
