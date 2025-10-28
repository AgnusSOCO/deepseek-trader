"""
Run backtests for all trading strategies

Tests all 15 strategies (10 existing + 5 new Tier 1) across multiple timeframes
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from datetime import datetime

from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.data_downloader import DataDownloader
from src.strategies.scalping import ScalpingStrategy
from src.strategies.momentum import MomentumStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.supertrend_strategy import SuperTrendStrategy
from src.strategies.donchian_strategy import DonchianStrategy
from src.strategies.keltner_strategy import KeltnerStrategy
from src.strategies.connors_rsi_strategy import ConnorsRSIStrategy
from src.strategies.ichimoku_strategy import IchimokuStrategy
# New Tier 1 strategies
from src.strategies.multi_supertrend_strategy import MultiSuperTrendStrategy
from src.strategies.adx_sma_strategy import AdxSmaStrategy
from src.strategies.bandtastic_strategy import BandtasticStrategy
from src.strategies.universal_macd_strategy import UniversalMacdStrategy
from src.strategies.volatility_system_strategy import VolatilitySystemStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_backtest(strategy, symbol, timeframe, data_dir='data/historical'):
    """Run backtest for a single strategy"""
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"Running backtest: {strategy.name} on {symbol} {timeframe}")
        logger.info(f"{'='*80}")
        
        downloader = DataDownloader()
        df = downloader.load_data(symbol, timeframe, data_dir=data_dir)
        
        if len(df) == 0:
            logger.error(f"No data available for {symbol} {timeframe}")
            return None
        
        logger.info(f"Loaded {len(df)} rows from {df.index[0]} to {df.index[-1]}")
        
        engine = BacktestEngine(
            initial_capital=10000.0,
            maker_fee=0.0002,
            taker_fee=0.0005,
            slippage_pct=0.0005
        )
        
        results = engine.run_backtest(strategy, df)
        
        logger.info(f"\n{'='*80}")
        logger.info(f"Results for {strategy.name}:")
        logger.info(f"{'='*80}")
        logger.info(f"Total Trades: {results['num_trades']}")
        logger.info(f"Winning Trades: {results['num_wins']}")
        logger.info(f"Win Rate: {results['win_rate']:.2%}")
        logger.info(f"Total Return: {results['total_return_pct']:.2f}%")
        logger.info(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        logger.info(f"Max Drawdown: {results['max_drawdown_pct']:.2f}%")
        logger.info(f"Profit Factor: {results['profit_factor']:.2f}")
        logger.info(f"{'='*80}\n")
        
        return results
        
    except Exception as e:
        logger.error(f"Error running backtest for {strategy.name}: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Run all backtests"""
    logger.info("Starting comprehensive backtest suite")
    logger.info(f"Timestamp: {datetime.now()}")
    
    symbols = ['BTC/USDT', 'ETH/USDT']
    
    strategies_config = [
        # Existing strategies
        ('Scalping_5m', lambda s: ScalpingStrategy('Scalping_5m', {'timeframe': '5m', 'min_confidence': 0.75}), '5m'),
        ('Momentum_15m', lambda s: MomentumStrategy('Momentum_15m', {'timeframe': '15m', 'min_confidence': 0.5}), '15m'),
        ('Momentum_1h', lambda s: MomentumStrategy('Momentum_1h', {'timeframe': '1h', 'min_confidence': 0.5}), '1h'),
        ('MeanReversion_5m', lambda s: MeanReversionStrategy('MeanReversion_5m', {'timeframe': '5m'}), '5m'),
        ('MeanReversion_15m', lambda s: MeanReversionStrategy('MeanReversion_15m', {'timeframe': '15m'}), '15m'),
        ('SuperTrend_1h', lambda s: SuperTrendStrategy(s, '1h'), '1h'),
        ('Donchian_1h', lambda s: DonchianStrategy(s, '1h'), '1h'),
        ('Keltner_1h', lambda s: KeltnerStrategy(s, '1h'), '1h'),
        ('ConnorsRSI_15m', lambda s: ConnorsRSIStrategy(s, '15m'), '15m'),
        ('Ichimoku_1h', lambda s: IchimokuStrategy(s, '1h'), '1h'),
        # New Tier 1 strategies
        ('MultiSuperTrend_1h', lambda s: MultiSuperTrendStrategy(s, '1h'), '1h'),
        ('AdxSma_1h', lambda s: AdxSmaStrategy(s, '1h'), '1h'),
        ('Bandtastic_15m', lambda s: BandtasticStrategy(s, '15m'), '15m'),
        ('UniversalMacd_5m', lambda s: UniversalMacdStrategy(s, '5m'), '5m'),
        ('VolatilitySystem_1h', lambda s: VolatilitySystemStrategy(s, '1h'), '1h'),
    ]
    
    all_results = []
    
    for symbol in symbols:
        for strategy_name, strategy_factory, timeframe in strategies_config:
            strategy = strategy_factory(symbol)
            results = run_backtest(strategy, symbol, timeframe)
            
            if results:
                all_results.append({
                    'strategy': strategy_name,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    **results
                })
    
    logger.info("\n" + "="*80)
    logger.info("SUMMARY OF ALL BACKTESTS")
    logger.info("="*80)
    
    all_results.sort(key=lambda x: x['total_return_pct'], reverse=True)
    
    logger.info(f"\n{'Strategy':<25} {'Symbol':<12} {'Trades':<8} {'Win Rate':<10} {'Return':<12} {'Sharpe':<8} {'Max DD':<10}")
    logger.info("-" * 100)
    
    for result in all_results:
        logger.info(
            f"{result['strategy']:<25} "
            f"{result['symbol']:<12} "
            f"{result['num_trades']:<8} "
            f"{result['win_rate']:>8.2%}  "
            f"{result['total_return_pct']:>10.2f}%  "
            f"{result['sharpe_ratio']:>6.2f}  "
            f"{result['max_drawdown_pct']:>8.2f}%"
        )
    
    logger.info("\n" + "="*80)
    logger.info("Backtest suite complete!")
    logger.info("="*80)


if __name__ == '__main__':
    main()
