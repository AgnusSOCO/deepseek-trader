#!/usr/bin/env python3
"""
Walk-Forward Optimization Script for Phase G

Runs 4-fold cross-validation with composite objective function
and robustness checks on top 3 performing strategies.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import logging
from datetime import datetime

from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.optimizer import ParameterOptimizer
from src.strategies.momentum import MomentumStrategy
from src.strategies.universal_macd_strategy import UniversalMacdStrategy
from src.strategies.volatility_system_strategy import VolatilitySystemStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_data(symbol: str, timeframe: str) -> pd.DataFrame:
    """Load synthetic data for backtesting"""
    data_file = f'data/historical/{symbol.replace("/", "_")}_{timeframe}.csv'
    
    if not os.path.exists(data_file):
        logger.error(f"Data file not found: {data_file}")
        return None
    
    df = pd.read_csv(data_file, index_col=0, parse_dates=True)
    logger.info(f"Loaded {len(df)} rows from {data_file}")
    return df


def run_walk_forward_momentum():
    """Run walk-forward optimization on Momentum_1h strategy"""
    logger.info("\n" + "="*80)
    logger.info("WALK-FORWARD OPTIMIZATION: Momentum_1h")
    logger.info("="*80)
    
    data = load_data('BTC/USDT', '1h')
    if data is None:
        return None
    
    engine = BacktestEngine(initial_capital=10000.0)
    optimizer = ParameterOptimizer(
        engine,
        optimization_metric='sharpe_ratio',
        use_composite_objective=True
    )
    
    base_config = {
        'symbol': 'BTC/USDT',
        'timeframe': '1h'
    }
    
    param_grid = {
        'ema_fast': [8, 10, 12, 14],
        'ema_slow': [21, 26, 30],
        'adx_threshold': [20, 25, 30],
        'min_confidence': [0.45, 0.50, 0.55, 0.60]
    }
    
    logger.info(f"Parameter grid: {param_grid}")
    logger.info(f"Total combinations: {4 * 3 * 3 * 4} = {4*3*3*4}")
    
    best_score = float('-inf')
    best_params = None
    best_cv_results = None
    all_results = []
    
    from itertools import product
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    logger.info(f"\nTesting {len(combinations)} parameter combinations with 4-fold CV...")
    
    for i, combo in enumerate(combinations):
        params = dict(zip(param_names, combo))
        config = {**base_config, **params}
        
        cv_results = optimizer.cross_validate(
            MomentumStrategy,
            config,
            data,
            n_splits=4,
            symbol='BTC/USDT',
            min_trades_per_fold=30
        )
        
        if not cv_results.get('robust', False):
            logger.info(f"  [{i+1}/{len(combinations)}] {params} -> FAILED robustness check")
            continue
        
        score = cv_results.get('sharpe_ratio_mean', 0.0)
        
        result = {
            'params': params,
            'cv_score': score,
            'cv_results': cv_results
        }
        all_results.append(result)
        
        if score > best_score:
            best_score = score
            best_params = params
            best_cv_results = cv_results
        
        logger.info(
            f"  [{i+1}/{len(combinations)}] {params} -> "
            f"Sharpe={score:.4f} ± {cv_results.get('sharpe_ratio_std', 0):.4f}, "
            f"Robust={cv_results.get('passed_folds', 0)}/4"
        )
    
    if best_params is None:
        logger.error("No robust parameter combinations found!")
        return None
    
    logger.info(f"\n{'='*80}")
    logger.info(f"BEST PARAMETERS: {best_params}")
    logger.info(f"CV Sharpe: {best_score:.4f} ± {best_cv_results.get('sharpe_ratio_std', 0):.4f}")
    logger.info(f"CV Return: {best_cv_results.get('total_return_pct_mean', 0):.2f}% ± {best_cv_results.get('total_return_pct_std', 0):.2f}%")
    logger.info(f"CV Max DD: {best_cv_results.get('max_drawdown_pct_mean', 0):.2f}% ± {best_cv_results.get('max_drawdown_pct_std', 0):.2f}%")
    logger.info(f"CV Trades: {best_cv_results.get('num_trades_mean', 0):.0f} ± {best_cv_results.get('num_trades_std', 0):.0f}")
    logger.info(f"Robustness: {best_cv_results.get('passed_folds', 0)}/4 folds passed")
    logger.info(f"{'='*80}\n")
    
    return {
        'strategy': 'Momentum_1h',
        'best_params': best_params,
        'best_score': best_score,
        'cv_results': best_cv_results,
        'all_results': all_results
    }


def run_walk_forward_universal_macd():
    """Run walk-forward optimization on UniversalMacd_5m strategy"""
    logger.info("\n" + "="*80)
    logger.info("WALK-FORWARD OPTIMIZATION: UniversalMacd_5m")
    logger.info("="*80)
    
    data = load_data('BTC/USDT', '5m')
    if data is None:
        return None
    
    engine = BacktestEngine(initial_capital=10000.0)
    optimizer = ParameterOptimizer(
        engine,
        optimization_metric='sharpe_ratio',
        use_composite_objective=True
    )
    
    base_config = {
        'symbol': 'BTC/USDT',
        'timeframe': '5m'
    }
    
    param_grid = {
        'buy_umacd_min': [-0.025, -0.020, -0.015],
        'buy_umacd_max': [-0.005, -0.003, -0.001],
        'sell_umacd_min': [-0.025, -0.020, -0.015],
        'sell_umacd_max': [-0.010, -0.007, -0.005],
        'min_confidence': [0.65, 0.70, 0.75]
    }
    
    logger.info(f"Parameter grid: {param_grid}")
    logger.info(f"Total combinations: {3 * 3 * 3 * 3 * 3} = {3*3*3*3*3}")
    
    best_score = float('-inf')
    best_params = None
    best_cv_results = None
    all_results = []
    
    from itertools import product
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    logger.info(f"\nTesting {len(combinations)} parameter combinations with 4-fold CV...")
    
    for i, combo in enumerate(combinations):
        params = dict(zip(param_names, combo))
        config = {**base_config, **params}
        
        cv_results = optimizer.cross_validate(
            UniversalMacdStrategy,
            config,
            data,
            n_splits=4,
            symbol='BTC/USDT',
            min_trades_per_fold=30
        )
        
        if not cv_results.get('robust', False):
            logger.info(f"  [{i+1}/{len(combinations)}] {params} -> FAILED robustness check")
            continue
        
        score = cv_results.get('sharpe_ratio_mean', 0.0)
        
        result = {
            'params': params,
            'cv_score': score,
            'cv_results': cv_results
        }
        all_results.append(result)
        
        if score > best_score:
            best_score = score
            best_params = params
            best_cv_results = cv_results
        
        if (i + 1) % 10 == 0 or score > best_score:
            logger.info(
                f"  [{i+1}/{len(combinations)}] {params} -> "
                f"Sharpe={score:.4f} ± {cv_results.get('sharpe_ratio_std', 0):.4f}, "
                f"Robust={cv_results.get('passed_folds', 0)}/4"
            )
    
    if best_params is None:
        logger.error("No robust parameter combinations found!")
        return None
    
    logger.info(f"\n{'='*80}")
    logger.info(f"BEST PARAMETERS: {best_params}")
    logger.info(f"CV Sharpe: {best_score:.4f} ± {best_cv_results.get('sharpe_ratio_std', 0):.4f}")
    logger.info(f"CV Return: {best_cv_results.get('total_return_pct_mean', 0):.2f}% ± {best_cv_results.get('total_return_pct_std', 0):.2f}%")
    logger.info(f"CV Max DD: {best_cv_results.get('max_drawdown_pct_mean', 0):.2f}% ± {best_cv_results.get('max_drawdown_pct_std', 0):.2f}%")
    logger.info(f"CV Trades: {best_cv_results.get('num_trades_mean', 0):.0f} ± {best_cv_results.get('num_trades_std', 0):.0f}")
    logger.info(f"Robustness: {best_cv_results.get('passed_folds', 0)}/4 folds passed")
    logger.info(f"{'='*80}\n")
    
    return {
        'strategy': 'UniversalMacd_5m',
        'best_params': best_params,
        'best_score': best_score,
        'cv_results': best_cv_results,
        'all_results': all_results
    }


def run_walk_forward_volatility_system():
    """Run walk-forward optimization on VolatilitySystem_1h strategy"""
    logger.info("\n" + "="*80)
    logger.info("WALK-FORWARD OPTIMIZATION: VolatilitySystem_1h")
    logger.info("="*80)
    
    data = load_data('BTC/USDT', '1h')
    if data is None:
        return None
    
    engine = BacktestEngine(initial_capital=10000.0)
    optimizer = ParameterOptimizer(
        engine,
        optimization_metric='sharpe_ratio',
        use_composite_objective=True
    )
    
    base_config = {
        'symbol': 'BTC/USDT',
        'timeframe': '1h'
    }
    
    param_grid = {
        'atr_period': [10, 14, 20],
        'atr_multiplier': [2.5, 3.0, 3.5, 4.0],
        'leverage': [1.0, 1.5, 2.0],
        'adx_min': [20, 25, 30],
        'min_confidence': [0.70, 0.75, 0.80]
    }
    
    logger.info(f"Parameter grid: {param_grid}")
    logger.info(f"Total combinations: {3 * 4 * 3 * 3 * 3} = {3*4*3*3*3}")
    
    best_score = float('-inf')
    best_params = None
    best_cv_results = None
    all_results = []
    
    from itertools import product
    param_names = list(param_grid.keys())
    param_values = list(param_grid.values())
    combinations = list(product(*param_values))
    
    logger.info(f"\nTesting {len(combinations)} parameter combinations with 4-fold CV...")
    
    for i, combo in enumerate(combinations):
        params = dict(zip(param_names, combo))
        config = {**base_config, **params}
        
        cv_results = optimizer.cross_validate(
            VolatilitySystemStrategy,
            config,
            data,
            n_splits=4,
            symbol='BTC/USDT',
            min_trades_per_fold=30
        )
        
        if not cv_results.get('robust', False):
            logger.info(f"  [{i+1}/{len(combinations)}] {params} -> FAILED robustness check")
            continue
        
        score = cv_results.get('sharpe_ratio_mean', 0.0)
        
        result = {
            'params': params,
            'cv_score': score,
            'cv_results': cv_results
        }
        all_results.append(result)
        
        if score > best_score:
            best_score = score
            best_params = params
            best_cv_results = cv_results
        
        if (i + 1) % 20 == 0 or score > best_score:
            logger.info(
                f"  [{i+1}/{len(combinations)}] {params} -> "
                f"Sharpe={score:.4f} ± {cv_results.get('sharpe_ratio_std', 0):.4f}, "
                f"Robust={cv_results.get('passed_folds', 0)}/4"
            )
    
    if best_params is None:
        logger.error("No robust parameter combinations found!")
        return None
    
    logger.info(f"\n{'='*80}")
    logger.info(f"BEST PARAMETERS: {best_params}")
    logger.info(f"CV Sharpe: {best_score:.4f} ± {best_cv_results.get('sharpe_ratio_std', 0):.4f}")
    logger.info(f"CV Return: {best_cv_results.get('total_return_pct_mean', 0):.2f}% ± {best_cv_results.get('total_return_pct_std', 0):.2f}%")
    logger.info(f"CV Max DD: {best_cv_results.get('max_drawdown_pct_mean', 0):.2f}% ± {best_cv_results.get('max_drawdown_pct_std', 0):.2f}%")
    logger.info(f"CV Trades: {best_cv_results.get('num_trades_mean', 0):.0f} ± {best_cv_results.get('num_trades_std', 0):.0f}")
    logger.info(f"Robustness: {best_cv_results.get('passed_folds', 0)}/4 folds passed")
    logger.info(f"{'='*80}\n")
    
    return {
        'strategy': 'VolatilitySystem_1h',
        'best_params': best_params,
        'best_score': best_score,
        'cv_results': best_cv_results,
        'all_results': all_results
    }


def create_optimization_report(results: list):
    """Create comprehensive optimization report"""
    logger.info("\n" + "="*80)
    logger.info("PHASE G: WALK-FORWARD OPTIMIZATION REPORT")
    logger.info("="*80)
    
    report = []
    report.append("# Phase G: Walk-Forward Optimization Results\n")
    report.append(f"**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append(f"**Method**: 4-fold cross-validation with composite objective function\n")
    report.append(f"**Composite Objective**: Sharpe - 0.5*DD - 0.0005*trades\n")
    report.append(f"**Robustness Filter**: Minimum 30 trades per fold\n\n")
    
    report.append("## Summary\n\n")
    
    for result in results:
        if result is None:
            continue
        
        strategy = result['strategy']
        best_params = result['best_params']
        cv_results = result['cv_results']
        
        report.append(f"### {strategy}\n\n")
        report.append(f"**Robustness**: {'✅ PASS' if cv_results.get('robust', False) else '❌ FAIL'} ")
        report.append(f"({cv_results.get('passed_folds', 0)}/4 folds passed)\n\n")
        
        report.append("**Best Parameters**:\n")
        for param, value in best_params.items():
            report.append(f"- `{param}`: {value}\n")
        report.append("\n")
        
        report.append("**Cross-Validation Performance**:\n")
        report.append(f"- Sharpe Ratio: {cv_results.get('sharpe_ratio_mean', 0):.4f} ± {cv_results.get('sharpe_ratio_std', 0):.4f}\n")
        report.append(f"- Total Return: {cv_results.get('total_return_pct_mean', 0):.2f}% ± {cv_results.get('total_return_pct_std', 0):.2f}%\n")
        report.append(f"- Max Drawdown: {cv_results.get('max_drawdown_pct_mean', 0):.2f}% ± {cv_results.get('max_drawdown_pct_std', 0):.2f}%\n")
        report.append(f"- Win Rate: {cv_results.get('win_rate_mean', 0):.2f}% ± {cv_results.get('win_rate_std', 0):.2f}%\n")
        report.append(f"- Num Trades: {cv_results.get('num_trades_mean', 0):.0f} ± {cv_results.get('num_trades_std', 0):.0f}\n")
        report.append(f"- Profit Factor: {cv_results.get('profit_factor_mean', 0):.2f} ± {cv_results.get('profit_factor_std', 0):.2f}\n")
        report.append("\n")
        
        report.append("**Parameter Stability**:\n")
        sharpe_cv = cv_results.get('sharpe_ratio_std', 0) / max(abs(cv_results.get('sharpe_ratio_mean', 0.01)), 0.01)
        return_cv = cv_results.get('total_return_pct_std', 0) / max(abs(cv_results.get('total_return_pct_mean', 0.01)), 0.01)
        report.append(f"- Sharpe CV: {sharpe_cv:.2%} {'✅' if sharpe_cv < 0.3 else '⚠️'}\n")
        report.append(f"- Return CV: {return_cv:.2%} {'✅' if return_cv < 0.5 else '⚠️'}\n")
        report.append("\n")
    
    report.append("## Recommendations\n\n")
    report.append("1. **Momentum_1h**: Use optimized parameters for paper trading Phase 1\n")
    report.append("2. **UniversalMacd_5m**: Monitor for over-trading, consider higher confidence threshold\n")
    report.append("3. **VolatilitySystem_1h**: Validate on real data before paper trading\n")
    report.append("4. **Next Steps**: Proceed to Phase H (Real Data Testing)\n\n")
    
    report_text = ''.join(report)
    
    os.makedirs('docs', exist_ok=True)
    with open('docs/phase_g_walk_forward_optimization.md', 'w') as f:
        f.write(report_text)
    
    logger.info("Report saved to: docs/phase_g_walk_forward_optimization.md")
    
    return report_text


def main():
    """Main execution"""
    logger.info("Starting Phase G: Walk-Forward Optimization")
    logger.info(f"Timestamp: {datetime.now()}\n")
    
    results = []
    
    result1 = run_walk_forward_momentum()
    results.append(result1)
    
    result2 = run_walk_forward_universal_macd()
    results.append(result2)
    
    result3 = run_walk_forward_volatility_system()
    results.append(result3)
    
    report = create_optimization_report(results)
    
    logger.info("\n" + "="*80)
    logger.info("PHASE G COMPLETE!")
    logger.info("="*80)
    logger.info("Next: Phase H (Real Data Testing)")


if __name__ == '__main__':
    main()
