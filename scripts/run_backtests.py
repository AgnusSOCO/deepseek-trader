"""
Script to run comprehensive backtests for all strategies
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import pandas as pd
from datetime import datetime

from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.performance import PerformanceMetrics
from src.backtesting.data_downloader import DataDownloader
from src.strategies.scalping import ScalpingStrategy
from src.strategies.momentum import MomentumStrategy
from src.strategies.mean_reversion import MeanReversionStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def run_strategy_backtest(
    strategy_class,
    strategy_name: str,
    config: dict,
    data: pd.DataFrame,
    symbol: str,
    engine: BacktestEngine
):
    """Run backtest for a single strategy"""
    logger.info(f"\n{'='*60}")
    logger.info(f"Running backtest: {strategy_name} on {symbol}")
    logger.info(f"{'='*60}")
    
    strategy = strategy_class(strategy_name, config)
    
    results = engine.run_backtest(strategy, data, symbol)
    
    metrics = PerformanceMetrics.calculate_all_metrics(
        trades=results['trades'],
        equity_curve=results['equity_curve'],
        initial_capital=engine.initial_capital
    )
    
    PerformanceMetrics.print_summary(metrics)
    
    return results, metrics


def main():
    """Run comprehensive backtests"""
    
    engine = BacktestEngine(
        initial_capital=10000.0,
        maker_fee=0.0002,
        taker_fee=0.0005,
        slippage_pct=0.0005,
        max_positions=3
    )
    
    downloader = DataDownloader('binance')
    
    test_configs = [
        {
            'strategy_class': ScalpingStrategy,
            'strategy_name': 'Scalping_1m',
            'symbol': 'BTC/USDT',
            'timeframe': '1m',
            'config': {
                'timeframe': '1m',
                'profit_target_pct': 0.3,
                'stop_loss_pct': 0.5,
                'max_trade_duration_minutes': 10
            }
        },
        {
            'strategy_class': ScalpingStrategy,
            'strategy_name': 'Scalping_5m',
            'symbol': 'BTC/USDT',
            'timeframe': '5m',
            'config': {
                'timeframe': '5m',
                'profit_target_pct': 0.5,
                'stop_loss_pct': 0.7,
                'max_trade_duration_minutes': 30
            }
        },
        {
            'strategy_class': MomentumStrategy,
            'strategy_name': 'Momentum_15m',
            'symbol': 'BTC/USDT',
            'timeframe': '15m',
            'config': {
                'timeframe': '15m',
                'profit_target_pct': 3.0,
                'initial_stop_loss_pct': 2.0,
                'trailing_stop_pct': 2.5
            }
        },
        {
            'strategy_class': MomentumStrategy,
            'strategy_name': 'Momentum_1h',
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            'config': {
                'timeframe': '1h',
                'profit_target_pct': 5.0,
                'initial_stop_loss_pct': 3.0,
                'trailing_stop_pct': 3.5
            }
        },
        {
            'strategy_class': MeanReversionStrategy,
            'strategy_name': 'MeanReversion_5m',
            'symbol': 'BTC/USDT',
            'timeframe': '5m',
            'config': {
                'timeframe': '5m',
                'profit_target_pct': 1.0,
                'stop_loss_pct': 1.5,
                'max_hold_minutes': 120
            }
        },
        {
            'strategy_class': MeanReversionStrategy,
            'strategy_name': 'MeanReversion_15m',
            'symbol': 'BTC/USDT',
            'timeframe': '15m',
            'config': {
                'timeframe': '15m',
                'profit_target_pct': 2.0,
                'stop_loss_pct': 2.5,
                'max_hold_minutes': 240
            }
        }
    ]
    
    all_results = []
    
    for test_config in test_configs:
        try:
            logger.info(f"\nLoading data: {test_config['symbol']} {test_config['timeframe']}")
            data = downloader.load_data(
                symbol=test_config['symbol'],
                timeframe=test_config['timeframe']
            )
            
            results, metrics = run_strategy_backtest(
                strategy_class=test_config['strategy_class'],
                strategy_name=test_config['strategy_name'],
                config=test_config['config'],
                data=data,
                symbol=test_config['symbol'],
                engine=engine
            )
            
            all_results.append({
                'strategy_name': test_config['strategy_name'],
                'symbol': test_config['symbol'],
                'timeframe': test_config['timeframe'],
                'metrics': metrics
            })
            
        except Exception as e:
            logger.error(f"Error running backtest {test_config['strategy_name']}: {e}")
            continue
    
    logger.info(f"\n{'='*80}")
    logger.info("BACKTEST COMPARISON SUMMARY")
    logger.info(f"{'='*80}\n")
    
    comparison_df = pd.DataFrame([
        {
            'Strategy': r['strategy_name'],
            'Symbol': r['symbol'],
            'Timeframe': r['timeframe'],
            'Return %': f"{r['metrics'].get('total_return_pct', 0):.2f}",
            'Sharpe': f"{r['metrics'].get('sharpe_ratio', 0):.2f}",
            'Max DD %': f"{r['metrics'].get('max_drawdown_pct', 0):.2f}",
            'Win Rate %': f"{r['metrics'].get('win_rate', 0):.2f}",
            'Profit Factor': f"{r['metrics'].get('profit_factor', 0):.2f}",
            'Trades': r['metrics'].get('num_trades', 0)
        }
        for r in all_results
    ])
    
    print(comparison_df.to_string(index=False))
    
    logger.info(f"\n{'='*80}\n")


if __name__ == '__main__':
    main()
