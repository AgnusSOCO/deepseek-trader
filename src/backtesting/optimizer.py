"""
Parameter Optimizer

Grid search and random search optimization for strategy parameters.
"""

import logging
from typing import Dict, Any, List, Tuple, Callable
import pandas as pd
import numpy as np
from itertools import product
import random

from .backtest_engine import BacktestEngine
from .performance import PerformanceMetrics

logger = logging.getLogger(__name__)


class ParameterOptimizer:
    """
    Parameter optimization for trading strategies
    
    Supports:
    - Grid search optimization
    - Random search optimization
    - Cross-validation
    - Out-of-sample testing
    """
    
    def __init__(
        self,
        backtest_engine: BacktestEngine,
        optimization_metric: str = 'sharpe_ratio',
        use_composite_objective: bool = False
    ):
        """
        Initialize parameter optimizer
        
        Args:
            backtest_engine: BacktestEngine instance
            optimization_metric: Metric to optimize (sharpe_ratio, total_return_pct, etc.)
            use_composite_objective: Use composite objective function (Sharpe - 0.5*DD - 0.0005*trades)
        """
        self.backtest_engine = backtest_engine
        self.optimization_metric = optimization_metric
        self.use_composite_objective = use_composite_objective
        self.results: List[Dict[str, Any]] = []
        
        logger.info(f"ParameterOptimizer initialized with metric: {optimization_metric}")
        if use_composite_objective:
            logger.info("Using composite objective function: Sharpe - 0.5*DD - 0.0005*trades")
    
    def grid_search(
        self,
        strategy_class: type,
        base_config: Dict[str, Any],
        param_grid: Dict[str, List[Any]],
        data: pd.DataFrame,
        symbol: str = 'BTC/USDT'
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Perform grid search optimization
        
        Args:
            strategy_class: Strategy class to optimize
            base_config: Base configuration dict
            param_grid: Dict of parameter names to lists of values to try
            data: Historical data for backtesting
            symbol: Trading pair symbol
        
        Returns:
            Tuple of (best_params, all_results)
        """
        logger.info(f"Starting grid search optimization")
        logger.info(f"Parameter grid: {param_grid}")
        
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        combinations = list(product(*param_values))
        
        logger.info(f"Testing {len(combinations)} parameter combinations")
        
        self.results = []
        best_score = float('-inf')
        best_params = None
        
        for i, combo in enumerate(combinations):
            config = base_config.copy()
            params = dict(zip(param_names, combo))
            config.update(params)
            
            strategy = strategy_class(f"opt_{i}", config)
            
            try:
                results = self.backtest_engine.run_backtest(strategy, data, symbol)
                
                if self.use_composite_objective:
                    score = self._calculate_composite_score(results)
                else:
                    score = results.get(self.optimization_metric, 0.0)
                
                result = {
                    'params': params,
                    'score': score,
                    'metrics': results
                }
                self.results.append(result)
                
                if score > best_score:
                    best_score = score
                    best_params = params
                
                logger.debug(
                    f"Combination {i+1}/{len(combinations)}: "
                    f"{params} -> {self.optimization_metric}={score:.4f}"
                )
                
            except Exception as e:
                logger.error(f"Error testing combination {params}: {e}")
                continue
        
        logger.info(
            f"Grid search complete. Best {self.optimization_metric}: {best_score:.4f}"
        )
        logger.info(f"Best parameters: {best_params}")
        
        return best_params, self.results
    
    def random_search(
        self,
        strategy_class: type,
        base_config: Dict[str, Any],
        param_distributions: Dict[str, Tuple[Any, Any]],
        data: pd.DataFrame,
        n_iterations: int = 50,
        symbol: str = 'BTC/USDT'
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Perform random search optimization
        
        Args:
            strategy_class: Strategy class to optimize
            base_config: Base configuration dict
            param_distributions: Dict of parameter names to (min, max) tuples
            data: Historical data for backtesting
            n_iterations: Number of random combinations to try
            symbol: Trading pair symbol
        
        Returns:
            Tuple of (best_params, all_results)
        """
        logger.info(f"Starting random search optimization ({n_iterations} iterations)")
        logger.info(f"Parameter distributions: {param_distributions}")
        
        self.results = []
        best_score = float('-inf')
        best_params = None
        
        for i in range(n_iterations):
            params = {}
            for param_name, (min_val, max_val) in param_distributions.items():
                if isinstance(min_val, int) and isinstance(max_val, int):
                    params[param_name] = random.randint(min_val, max_val)
                elif isinstance(min_val, float) and isinstance(max_val, float):
                    params[param_name] = random.uniform(min_val, max_val)
                else:
                    params[param_name] = random.choice([min_val, max_val])
            
            config = base_config.copy()
            config.update(params)
            
            strategy = strategy_class(f"opt_{i}", config)
            
            try:
                results = self.backtest_engine.run_backtest(strategy, data, symbol)
                
                if self.use_composite_objective:
                    score = self._calculate_composite_score(results)
                else:
                    score = results.get(self.optimization_metric, 0.0)
                
                result = {
                    'params': params,
                    'score': score,
                    'metrics': results
                }
                self.results.append(result)
                
                if score > best_score:
                    best_score = score
                    best_params = params
                
                logger.debug(
                    f"Iteration {i+1}/{n_iterations}: "
                    f"{params} -> {self.optimization_metric}={score:.4f}"
                )
                
            except Exception as e:
                logger.error(f"Error testing parameters {params}: {e}")
                continue
        
        logger.info(
            f"Random search complete. Best {self.optimization_metric}: {best_score:.4f}"
        )
        logger.info(f"Best parameters: {best_params}")
        
        return best_params, self.results
    
    def cross_validate(
        self,
        strategy_class: type,
        config: Dict[str, Any],
        data: pd.DataFrame,
        n_splits: int = 5,
        symbol: str = 'BTC/USDT',
        min_trades_per_fold: int = 30
    ) -> Dict[str, Any]:
        """
        Perform k-fold cross-validation with robustness filters
        
        Args:
            strategy_class: Strategy class to test
            config: Strategy configuration
            data: Historical data
            n_splits: Number of folds
            symbol: Trading pair symbol
            min_trades_per_fold: Minimum trades required per fold for robustness
        
        Returns:
            Dict with cross-validation results and robustness flags
        """
        logger.info(f"Starting {n_splits}-fold cross-validation (min {min_trades_per_fold} trades/fold)")
        
        fold_size = len(data) // n_splits
        fold_results = []
        failed_folds = []
        
        for i in range(n_splits):
            start_idx = i * fold_size
            end_idx = start_idx + fold_size if i < n_splits - 1 else len(data)
            
            fold_data = data.iloc[start_idx:end_idx]
            
            strategy = strategy_class(f"cv_{i}", config)
            
            try:
                results = self.backtest_engine.run_backtest(strategy, fold_data, symbol)
                
                num_trades = results.get('num_trades', 0)
                if num_trades < min_trades_per_fold:
                    logger.warning(
                        f"Fold {i+1}/{n_splits}: Only {num_trades} trades (min {min_trades_per_fold} required) - FAILED robustness check"
                    )
                    failed_folds.append(i + 1)
                else:
                    logger.debug(
                        f"Fold {i+1}/{n_splits}: {num_trades} trades, "
                        f"{self.optimization_metric}={results.get(self.optimization_metric, 0):.4f}"
                    )
                
                fold_results.append(results)
                
            except Exception as e:
                logger.error(f"Error in fold {i+1}: {e}")
                failed_folds.append(i + 1)
                continue
        
        if not fold_results:
            return {'robust': False, 'failed_folds': failed_folds}
        
        metrics = {}
        for key in fold_results[0].keys():
            if isinstance(fold_results[0][key], (int, float)):
                values = [r[key] for r in fold_results if key in r]
                metrics[f"{key}_mean"] = np.mean(values)
                metrics[f"{key}_std"] = np.std(values)
                metrics[f"{key}_min"] = np.min(values)
                metrics[f"{key}_max"] = np.max(values)
        
        robust = len(failed_folds) == 0
        metrics['robust'] = robust
        metrics['failed_folds'] = failed_folds
        metrics['passed_folds'] = n_splits - len(failed_folds)
        
        logger.info(
            f"Cross-validation complete. "
            f"Mean {self.optimization_metric}: "
            f"{metrics.get(f'{self.optimization_metric}_mean', 0):.4f} "
            f"± {metrics.get(f'{self.optimization_metric}_std', 0):.4f}"
        )
        logger.info(f"Robustness: {'PASS' if robust else 'FAIL'} ({metrics['passed_folds']}/{n_splits} folds passed)")
        
        return metrics
    
    def out_of_sample_test(
        self,
        strategy_class: type,
        config: Dict[str, Any],
        train_data: pd.DataFrame,
        test_data: pd.DataFrame,
        symbol: str = 'BTC/USDT'
    ) -> Dict[str, Any]:
        """
        Test strategy on out-of-sample data
        
        Args:
            strategy_class: Strategy class to test
            config: Strategy configuration
            train_data: Training data (for reference)
            test_data: Out-of-sample test data
            symbol: Trading pair symbol
        
        Returns:
            Dict with in-sample and out-of-sample results
        """
        logger.info("Starting out-of-sample test")
        
        train_strategy = strategy_class("train", config)
        train_results = self.backtest_engine.run_backtest(
            train_strategy, train_data, symbol
        )
        
        test_strategy = strategy_class("test", config)
        test_results = self.backtest_engine.run_backtest(
            test_strategy, test_data, symbol
        )
        
        comparison = {
            'train': train_results,
            'test': test_results,
            'degradation': {}
        }
        
        for key in train_results.keys():
            if isinstance(train_results[key], (int, float)):
                train_val = train_results[key]
                test_val = test_results.get(key, 0)
                
                if train_val != 0:
                    degradation_pct = ((test_val - train_val) / abs(train_val)) * 100
                    comparison['degradation'][key] = degradation_pct
        
        logger.info(
            f"Out-of-sample test complete. "
            f"Train {self.optimization_metric}: {train_results.get(self.optimization_metric, 0):.4f}, "
            f"Test {self.optimization_metric}: {test_results.get(self.optimization_metric, 0):.4f}"
        )
        
        return comparison
    
    def get_results_dataframe(self) -> pd.DataFrame:
        """Convert optimization results to DataFrame"""
        if not self.results:
            return pd.DataFrame()
        
        rows = []
        for result in self.results:
            row = result['params'].copy()
            row['score'] = result['score']
            
            metrics = result['metrics']
            for key in ['total_return_pct', 'sharpe_ratio', 'max_drawdown_pct', 
                       'win_rate', 'profit_factor', 'num_trades']:
                if key in metrics:
                    row[key] = metrics[key]
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df = df.sort_values('score', ascending=False)
        return df
    
    def analyze_parameter_sensitivity(
        self,
        param_name: str
    ) -> pd.DataFrame:
        """
        Analyze sensitivity of results to a specific parameter
        
        Args:
            param_name: Name of parameter to analyze
        
        Returns:
            DataFrame with parameter values and corresponding scores
        """
        if not self.results:
            return pd.DataFrame()
        
        data = []
        for result in self.results:
            if param_name in result['params']:
                data.append({
                    'param_value': result['params'][param_name],
                    'score': result['score']
                })
        
        df = pd.DataFrame(data)
        df = df.sort_values('param_value')
        return df
    
    def _calculate_composite_score(self, results: Dict[str, Any]) -> float:
        """
        Calculate composite objective function
        
        Formula: Sharpe - 0.5*DD - 0.0005*trades
        
        Args:
            results: Backtest results dict
        
        Returns:
            Composite score
        """
        sharpe = results.get('sharpe_ratio', 0.0)
        drawdown = results.get('max_drawdown_pct', 0.0)
        num_trades = results.get('num_trades', 0)
        
        composite = sharpe - 0.5 * abs(drawdown) - 0.0005 * num_trades
        
        return composite
