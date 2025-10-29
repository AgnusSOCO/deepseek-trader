"""
Ensemble System Performance Analysis

Tests the autonomous trading system with multiple strategies running simultaneously
to analyze portfolio-level performance, diversification benefits, and risk metrics.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import asyncio
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.data_downloader import DataDownloader
from src.strategies.momentum import MomentumStrategy
from src.strategies.universal_macd_strategy import UniversalMacdStrategy
from src.strategies.mean_reversion import MeanReversionStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class EnsembleBacktester:
    """Backtest multiple strategies as an ensemble portfolio"""
    
    def __init__(self, initial_capital=10000.0):
        self.initial_capital = initial_capital
        self.results = {}
        
    def run_ensemble_backtest(self, strategies_config, symbol, data_dir='data/historical'):
        """
        Run backtest with multiple strategies simultaneously
        
        Args:
            strategies_config: List of (strategy, timeframe, allocation_pct) tuples
            symbol: Trading symbol
            data_dir: Data directory
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Running Ensemble Backtest for {symbol}")
        logger.info(f"{'='*80}")
        logger.info(f"Strategies: {len(strategies_config)}")
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        
        downloader = DataDownloader()
        data_by_timeframe = {}
        
        for strategy, timeframe, allocation in strategies_config:
            if timeframe not in data_by_timeframe:
                df = downloader.load_data(symbol, timeframe, data_dir=data_dir)
                data_by_timeframe[timeframe] = df
                logger.info(f"Loaded {len(df)} rows for {timeframe}")
        
        individual_results = []
        
        for strategy, timeframe, allocation_pct in strategies_config:
            allocated_capital = self.initial_capital * (allocation_pct / 100.0)
            
            logger.info(f"\n{'-'*80}")
            logger.info(f"Strategy: {strategy.name}")
            logger.info(f"Timeframe: {timeframe}")
            logger.info(f"Allocation: {allocation_pct}% (${allocated_capital:,.2f})")
            logger.info(f"{'-'*80}")
            
            engine = BacktestEngine(
                initial_capital=allocated_capital,
                maker_fee=0.0002,
                taker_fee=0.0005,
                slippage_pct=0.0005
            )
            
            df = data_by_timeframe[timeframe]
            results = engine.run_backtest(strategy, df)
            
            results['strategy_name'] = strategy.name
            results['timeframe'] = timeframe
            results['allocation_pct'] = allocation_pct
            results['allocated_capital'] = allocated_capital
            results['final_equity'] = allocated_capital * (1 + results['total_return_pct'] / 100.0)
            
            individual_results.append(results)
            
            logger.info(f"Trades: {results['num_trades']}")
            logger.info(f"Win Rate: {results['win_rate']:.2%}")
            logger.info(f"Return: {results['total_return_pct']:.2f}%")
            logger.info(f"Final Equity: ${results['final_equity']:,.2f}")
        
        total_final_equity = sum(r['final_equity'] for r in individual_results)
        total_return_pct = ((total_final_equity - self.initial_capital) / self.initial_capital) * 100
        
        total_trades = sum(r['num_trades'] for r in individual_results)
        total_wins = sum(r.get('num_wins', 0) for r in individual_results)
        ensemble_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
        
        weighted_sharpe = sum(
            r['sharpe_ratio'] * (r['allocation_pct'] / 100.0) 
            for r in individual_results
        )
        
        max_drawdown = max(r['max_drawdown_pct'] for r in individual_results)
        
        ensemble_results = {
            'initial_capital': self.initial_capital,
            'final_equity': total_final_equity,
            'total_return_pct': total_return_pct,
            'total_trades': total_trades,
            'ensemble_win_rate': ensemble_win_rate,
            'weighted_sharpe': weighted_sharpe,
            'max_drawdown_pct': max_drawdown,
            'individual_results': individual_results
        }
        
        logger.info(f"\n{'='*80}")
        logger.info(f"ENSEMBLE RESULTS")
        logger.info(f"{'='*80}")
        logger.info(f"Initial Capital: ${self.initial_capital:,.2f}")
        logger.info(f"Final Equity: ${total_final_equity:,.2f}")
        logger.info(f"Total Return: {total_return_pct:.2f}%")
        logger.info(f"Total Trades: {total_trades}")
        logger.info(f"Ensemble Win Rate: {ensemble_win_rate:.2f}%")
        logger.info(f"Weighted Sharpe: {weighted_sharpe:.2f}")
        logger.info(f"Max Drawdown: {max_drawdown:.2f}%")
        logger.info(f"{'='*80}\n")
        
        return ensemble_results


def main():
    """Run ensemble analysis"""
    logger.info("Starting Ensemble System Performance Analysis")
    logger.info(f"Timestamp: {datetime.now()}")
    
    logger.info("\n" + "="*80)
    logger.info("TEST 1: RECOMMENDED PORTFOLIO (50/30/20)")
    logger.info("="*80)
    
    strategies_config_1 = [
        (MomentumStrategy('Momentum_1h', {'timeframe': '1h', 'min_confidence': 0.5}), '1h', 50),
        (UniversalMacdStrategy('BTC/USDT', '5m'), '5m', 30),
        (MeanReversionStrategy('MeanReversion_15m', {'timeframe': '15m'}), '15m', 20),
    ]
    
    backtester1 = EnsembleBacktester(initial_capital=10000.0)
    results1 = backtester1.run_ensemble_backtest(strategies_config_1, 'BTC/USDT')
    
    logger.info("\n" + "="*80)
    logger.info("TEST 2: CONSERVATIVE PORTFOLIO (70/30)")
    logger.info("="*80)
    
    strategies_config_2 = [
        (MomentumStrategy('Momentum_1h', {'timeframe': '1h', 'min_confidence': 0.5}), '1h', 70),
        (MeanReversionStrategy('MeanReversion_15m', {'timeframe': '15m'}), '15m', 30),
    ]
    
    backtester2 = EnsembleBacktester(initial_capital=10000.0)
    results2 = backtester2.run_ensemble_backtest(strategies_config_2, 'BTC/USDT')
    
    logger.info("\n" + "="*80)
    logger.info("TEST 3: AGGRESSIVE PORTFOLIO (40/60)")
    logger.info("="*80)
    
    strategies_config_3 = [
        (MomentumStrategy('Momentum_1h', {'timeframe': '1h', 'min_confidence': 0.5}), '1h', 40),
        (UniversalMacdStrategy('BTC/USDT', '5m'), '5m', 60),
    ]
    
    backtester3 = EnsembleBacktester(initial_capital=10000.0)
    results3 = backtester3.run_ensemble_backtest(strategies_config_3, 'BTC/USDT')
    
    logger.info("\n" + "="*80)
    logger.info("ENSEMBLE PORTFOLIO COMPARISON")
    logger.info("="*80)
    
    logger.info(f"\n{'Portfolio':<30} {'Return':<12} {'Sharpe':<10} {'Max DD':<10} {'Trades':<10}")
    logger.info("-" * 80)
    
    portfolios = [
        ("Recommended (50/30/20)", results1),
        ("Conservative (70/30)", results2),
        ("Aggressive (40/60)", results3),
    ]
    
    for name, results in portfolios:
        logger.info(
            f"{name:<30} "
            f"{results['total_return_pct']:>10.2f}%  "
            f"{results['weighted_sharpe']:>8.2f}  "
            f"{results['max_drawdown_pct']:>8.2f}%  "
            f"{results['total_trades']:>8}"
        )
    
    logger.info("\n" + "="*80)
    logger.info("Ensemble Analysis Complete!")
    logger.info("="*80)
    
    return {
        'recommended': results1,
        'conservative': results2,
        'aggressive': results3
    }


if __name__ == '__main__':
    main()
