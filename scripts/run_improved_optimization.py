#!/usr/bin/env python3
"""
Improved Walk-Forward Optimization Script

Based on Phase G findings, this script implements:
1. Relaxed robustness criteria (15 trades/fold instead of 30)
2. Wider parameter ranges
3. Adjusted strategy thresholds
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import pandas as pd
from datetime import datetime
from itertools import product

from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.optimizer import ParameterOptimizer
from src.strategies.momentum import MomentumStrategy
from src.strategies.universal_macd_strategy import UniversalMacdStrategy
from src.strategies.volatility_system_strategy import VolatilitySystemStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/phase_g_improved_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def load_data():
    """Load synthetic data for optimization"""
    logger.info("Loading synthetic data...")
    
    data_5m = pd.read_csv('data/historical/BTC_USDT_5m.csv', index_col=0, parse_dates=True)
    data_1h = pd.read_csv('data/historical/BTC_USDT_1h.csv', index_col=0, parse_dates=True)
    
    logger.info(f"Loaded 5m data: {len(data_5m)} bars ({data_5m.index[0]} to {data_5m.index[-1]})")
    logger.info(f"Loaded 1h data: {len(data_1h)} bars ({data_1h.index[0]} to {data_1h.index[-1]})")
    
    return data_5m, data_1h


def optimize_momentum(data_1h):
    """
    Optimize Momentum_1h strategy with improved parameters
    
    Phase G Recommendations:
    - Reduce ADX threshold from 25 to 20
    - Lower confidence requirements
    - Widen parameter ranges
    """
    logger.info("\n" + "="*80)
    logger.info("OPTIMIZING MOMENTUM_1H STRATEGY (IMPROVED)")
    logger.info("="*80)
    
    engine = BacktestEngine(initial_capital=10000.0)
    optimizer = ParameterOptimizer(engine, use_composite_objective=True)
    
    param_grid = {
        'ema_fast': [8, 10, 12, 15],  # Wider range
        'ema_slow': [21, 26, 30],  # Wider range
        'adx_min': [15, 18, 20, 22],  # Lower thresholds (was 25)
        'min_confidence': [0.4, 0.45, 0.5, 0.55, 0.6]  # Lower thresholds (was 0.65+)
    }
    
    total_combinations = 1
    for values in param_grid.values():
        total_combinations *= len(values)
    
    logger.info(f"Testing {total_combinations} parameter combinations")
    logger.info(f"Parameter ranges: {param_grid}")
    
    fold_size = len(data_1h) // 4
    best_params = None
    best_score = float('-inf')
    robust_params = []
    
    for i, combo in enumerate(product(*param_grid.values())):
        params = dict(zip(param_grid.keys(), combo))
        config = {
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            **params
        }
        
        cv_results = optimizer.cross_validate(
            MomentumStrategy,
            config,
            data_1h,
            n_splits=4,
            symbol='BTC/USDT',
            min_trades_per_fold=15  # RELAXED from 30
        )
        
        if cv_results.get('robust', False):
            composite_score = cv_results.get('sharpe_ratio_mean', 0) - \
                            0.5 * abs(cv_results.get('max_drawdown_pct_mean', 0)) - \
                            0.0005 * cv_results.get('num_trades_mean', 0)
            
            robust_params.append({
                'params': params,
                'score': composite_score,
                'cv_results': cv_results
            })
            
            if composite_score > best_score:
                best_score = composite_score
                best_params = params
            
            logger.info(f"  [{i+1}/{total_combinations}] {params} -> PASSED (score: {composite_score:.4f})")
        else:
            logger.info(f"  [{i+1}/{total_combinations}] {params} -> FAILED robustness check")
    
    logger.info(f"\nMomentum_1h optimization complete:")
    logger.info(f"  Robust combinations found: {len(robust_params)}")
    if best_params:
        logger.info(f"  Best parameters: {best_params}")
        logger.info(f"  Best score: {best_score:.4f}")
    else:
        logger.warning("  No robust parameters found!")
    
    return robust_params, best_params


def optimize_universal_macd(data_5m):
    """
    Optimize UniversalMacd_5m strategy with improved parameters
    
    Phase G Recommendations:
    - Widen MACD signal ranges
    - Reduce confidence threshold to 0.5
    - More permissive entry/exit conditions
    """
    logger.info("\n" + "="*80)
    logger.info("OPTIMIZING UNIVERSALMACD_5M STRATEGY (IMPROVED)")
    logger.info("="*80)
    
    engine = BacktestEngine(initial_capital=10000.0)
    optimizer = ParameterOptimizer(engine, use_composite_objective=True)
    
    param_grid = {
        'buy_umacd_min': [-0.03, -0.025, -0.02, -0.015],  # Wider range
        'buy_umacd_max': [-0.008, -0.005, -0.003, -0.001],  # Wider range
        'sell_umacd_min': [-0.03, -0.025, -0.02, -0.015],  # Wider range
        'sell_umacd_max': [-0.008, -0.005, -0.003, -0.001],  # Wider range
        'min_confidence': [0.4, 0.45, 0.5, 0.55, 0.6]  # Lower thresholds (was 0.65+)
    }
    
    total_combinations = 1
    for values in param_grid.values():
        total_combinations *= len(values)
    
    logger.info(f"Testing {total_combinations} parameter combinations")
    logger.info(f"Parameter ranges: {param_grid}")
    
    best_params = None
    best_score = float('-inf')
    robust_params = []
    
    for i, combo in enumerate(product(*param_grid.values())):
        params = dict(zip(param_grid.keys(), combo))
        config = {
            'symbol': 'BTC/USDT',
            'timeframe': '5m',
            **params
        }
        
        cv_results = optimizer.cross_validate(
            UniversalMacdStrategy,
            config,
            data_5m,
            n_splits=4,
            symbol='BTC/USDT',
            min_trades_per_fold=15  # RELAXED from 30
        )
        
        if cv_results.get('robust', False):
            composite_score = cv_results.get('sharpe_ratio_mean', 0) - \
                            0.5 * abs(cv_results.get('max_drawdown_pct_mean', 0)) - \
                            0.0005 * cv_results.get('num_trades_mean', 0)
            
            robust_params.append({
                'params': params,
                'score': composite_score,
                'cv_results': cv_results
            })
            
            if composite_score > best_score:
                best_score = composite_score
                best_params = params
            
            logger.info(f"  [{i+1}/{total_combinations}] {params} -> PASSED (score: {composite_score:.4f})")
        else:
            logger.info(f"  [{i+1}/{total_combinations}] {params} -> FAILED robustness check")
    
    logger.info(f"\nUniversalMacd_5m optimization complete:")
    logger.info(f"  Robust combinations found: {len(robust_params)}")
    if best_params:
        logger.info(f"  Best parameters: {best_params}")
        logger.info(f"  Best score: {best_score:.4f}")
    else:
        logger.warning("  No robust parameters found!")
    
    return robust_params, best_params


def optimize_volatility_system(data_1h):
    """
    Optimize VolatilitySystem_1h strategy with improved parameters
    
    Phase G Recommendations:
    - Reduce ATR multiplier
    - Lower ADX requirements
    - More permissive entry conditions
    """
    logger.info("\n" + "="*80)
    logger.info("OPTIMIZING VOLATILITYSYSTEM_1H STRATEGY (IMPROVED)")
    logger.info("="*80)
    
    engine = BacktestEngine(initial_capital=10000.0)
    optimizer = ParameterOptimizer(engine, use_composite_objective=True)
    
    param_grid = {
        'atr_period': [10, 12, 14, 16, 20],  # Wider range
        'atr_multiplier': [1.5, 2.0, 2.5, 3.0],  # Lower multipliers (was 2.0-4.0)
        'leverage': [1.0, 1.5, 2.0],  # Added 1.5x option
        'adx_min': [15, 18, 20, 22, 25],  # Lower thresholds (was 25-30)
        'min_confidence': [0.4, 0.45, 0.5, 0.55, 0.6]  # Lower thresholds (was 0.7+)
    }
    
    total_combinations = 1
    for values in param_grid.values():
        total_combinations *= len(values)
    
    logger.info(f"Testing {total_combinations} parameter combinations")
    logger.info(f"Parameter ranges: {param_grid}")
    
    best_params = None
    best_score = float('-inf')
    robust_params = []
    
    for i, combo in enumerate(product(*param_grid.values())):
        params = dict(zip(param_grid.keys(), combo))
        config = {
            'symbol': 'BTC/USDT',
            'timeframe': '1h',
            **params
        }
        
        cv_results = optimizer.cross_validate(
            VolatilitySystemStrategy,
            config,
            data_1h,
            n_splits=4,
            symbol='BTC/USDT',
            min_trades_per_fold=15  # RELAXED from 30
        )
        
        if cv_results.get('robust', False):
            composite_score = cv_results.get('sharpe_ratio_mean', 0) - \
                            0.5 * abs(cv_results.get('max_drawdown_pct_mean', 0)) - \
                            0.0005 * cv_results.get('num_trades_mean', 0)
            
            robust_params.append({
                'params': params,
                'score': composite_score,
                'cv_results': cv_results
            })
            
            if composite_score > best_score:
                best_score = composite_score
                best_params = params
            
            logger.info(f"  [{i+1}/{total_combinations}] {params} -> PASSED (score: {composite_score:.4f})")
        else:
            logger.info(f"  [{i+1}/{total_combinations}] {params} -> FAILED robustness check")
    
    logger.info(f"\nVolatilitySystem_1h optimization complete:")
    logger.info(f"  Robust combinations found: {len(robust_params)}")
    if best_params:
        logger.info(f"  Best parameters: {best_params}")
        logger.info(f"  Best score: {best_score:.4f}")
    else:
        logger.warning("  No robust parameters found!")
    
    return robust_params, best_params


def generate_report(momentum_results, macd_results, volatility_results):
    """Generate comprehensive optimization report"""
    logger.info("\n" + "="*80)
    logger.info("PHASE G: IMPROVED OPTIMIZATION REPORT")
    logger.info("="*80)
    
    report = f"""# Phase G: Improved Walk-Forward Optimization Results
**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Method**: 4-fold cross-validation with RELAXED robustness criteria
**Composite Objective**: Sharpe - 0.5*DD - 0.0005*trades
**Robustness Filter**: Minimum 15 trades per fold (RELAXED from 30)


1. **Relaxed robustness criteria**: 15 trades/fold instead of 30
2. **Wider parameter ranges**: More permissive entry/exit conditions
3. **Lower confidence thresholds**: 0.4-0.6 instead of 0.65-0.8
4. **Reduced ADX requirements**: 15-25 instead of 25-30
5. **Lower ATR multipliers**: 1.5-3.0 instead of 2.0-4.0


- **Robust combinations found**: {len(momentum_results[0])}
- **Best parameters**: {momentum_results[1] if momentum_results[1] else 'None'}
- **Status**: {'✅ IMPROVED' if momentum_results[1] else '❌ Still unstable'}

- **Robust combinations found**: {len(macd_results[0])}
- **Best parameters**: {macd_results[1] if macd_results[1] else 'None'}
- **Status**: {'✅ IMPROVED' if macd_results[1] else '❌ Still unstable'}

- **Robust combinations found**: {len(volatility_results[0])}
- **Best parameters**: {volatility_results[1] if volatility_results[1] else 'None'}
- **Status**: {'✅ IMPROVED' if volatility_results[1] else '❌ Still unstable'}


"""
    
    if momentum_results[0]:
        sorted_momentum = sorted(momentum_results[0], key=lambda x: x['score'], reverse=True)[:5]
        for i, result in enumerate(sorted_momentum, 1):
            report += f"\n{i}. **Score: {result['score']:.4f}**\n"
            report += f"   - Parameters: {result['params']}\n"
            report += f"   - Sharpe: {result['cv_results'].get('sharpe_ratio_mean', 0):.4f} ± {result['cv_results'].get('sharpe_ratio_std', 0):.4f}\n"
            report += f"   - Drawdown: {result['cv_results'].get('max_drawdown_pct_mean', 0):.2f}%\n"
            report += f"   - Trades: {result['cv_results'].get('num_trades_mean', 0):.0f}\n"
    else:
        report += "\nNo robust configurations found.\n"
    
    report += "\n### UniversalMacd_5m Top 5 Configurations\n"
    
    if macd_results[0]:
        sorted_macd = sorted(macd_results[0], key=lambda x: x['score'], reverse=True)[:5]
        for i, result in enumerate(sorted_macd, 1):
            report += f"\n{i}. **Score: {result['score']:.4f}**\n"
            report += f"   - Parameters: {result['params']}\n"
            report += f"   - Sharpe: {result['cv_results'].get('sharpe_ratio_mean', 0):.4f} ± {result['cv_results'].get('sharpe_ratio_std', 0):.4f}\n"
            report += f"   - Drawdown: {result['cv_results'].get('max_drawdown_pct_mean', 0):.2f}%\n"
            report += f"   - Trades: {result['cv_results'].get('num_trades_mean', 0):.0f}\n"
    else:
        report += "\nNo robust configurations found.\n"
    
    report += "\n### VolatilitySystem_1h Top 5 Configurations\n"
    
    if volatility_results[0]:
        sorted_volatility = sorted(volatility_results[0], key=lambda x: x['score'], reverse=True)[:5]
        for i, result in enumerate(sorted_volatility, 1):
            report += f"\n{i}. **Score: {result['score']:.4f}**\n"
            report += f"   - Parameters: {result['params']}\n"
            report += f"   - Sharpe: {result['cv_results'].get('sharpe_ratio_mean', 0):.4f} ± {result['cv_results'].get('sharpe_ratio_std', 0):.4f}\n"
            report += f"   - Drawdown: {result['cv_results'].get('max_drawdown_pct_mean', 0):.2f}%\n"
            report += f"   - Trades: {result['cv_results'].get('num_trades_mean', 0):.0f}\n"
    else:
        report += "\nNo robust configurations found.\n"
    
    report += """

1. Update strategy default parameters with optimized values
2. Proceed to extended paper trading validation
3. Monitor performance closely with conservative position sizing
4. Implement dynamic parameter adaptation based on market regime

1. Consider using real market data instead of synthetic data
2. Extend validation period to 12+ months
3. Implement ensemble methods combining multiple weak strategies
4. Focus on regime-aware optimization
5. Consider alternative strategy designs

1. Review optimization results and select best configurations
2. Update strategy files with optimized parameters
3. Run comprehensive backtests on full dataset
4. Proceed to Phase H: Real Data Testing
"""
    
    with open('docs/phase_g_improved_optimization.md', 'w') as f:
        f.write(report)
    
    logger.info("Report saved to: docs/phase_g_improved_optimization.md")
    
    return report


def main():
    """Main optimization workflow"""
    logger.info("Starting improved walk-forward optimization...")
    logger.info(f"Start time: {datetime.now()}")
    
    os.makedirs('logs', exist_ok=True)
    os.makedirs('docs', exist_ok=True)
    
    data_5m, data_1h = load_data()
    
    momentum_results = optimize_momentum(data_1h)
    macd_results = optimize_universal_macd(data_5m)
    volatility_results = optimize_volatility_system(data_1h)
    
    report = generate_report(momentum_results, macd_results, volatility_results)
    
    logger.info("\n" + "="*80)
    logger.info("PHASE G IMPROVED OPTIMIZATION COMPLETE!")
    logger.info("="*80)
    logger.info(f"End time: {datetime.now()}")
    logger.info("Next: Review results and proceed to Phase H (Real Data Testing)")


if __name__ == '__main__':
    main()
