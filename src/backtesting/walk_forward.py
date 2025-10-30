c"""
Walk-Forward Optimizer

Rolling window optimization for strategy validation.
"""

import logging
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from .backtest_engine import BacktestEngine
from .optimizer import ParameterOptimizer
from .performance import PerformanceMetrics

logger = logging.getLogger(__name__)


class WalkForwardOptimizer:
    """
    Walk-forward optimization for trading strategies

    Process:
    1. Split data into rolling windows
    2. Optimize on training window
    3. Test on out-of-sample window
    4. Roll forward and repeat
    5. Analyze stability and efficiency
    """

    def __init__(
        self,
        backtest_engine: BacktestEngine,
        optimizer: ParameterOptimizer
    ):
        """
        Initialize walk-forward optimizer

        Args:
            backtest_engine: BacktestEngine instance
            optimizer: ParameterOptimizer instance
        """
        self.backtest_engine = backtest_engine
        self.optimizer = optimizer
        self.results: List[Dict[str, Any]] = []

        logger.info("WalkForwardOptimizer initialized")

    def run_walk_forward(
        self,
        strategy_class: type,
        base_config: Dict[str, Any],
        param_grid: Dict[str, List[Any]],
        data: pd.DataFrame,
        train_months: int = 6,
        test_months: int = 1,
        symbol: str = 'BTC/USDT'
    ) -> Dict[str, Any]:
        """
        Run walk-forward optimization

        Args:
            strategy_class: Strategy class to optimize
            base_config: Base configuration dict
            param_grid: Parameter grid for optimization
            data: Full historical data
            train_months: Number of months for training window
            test_months: Number of months for test window
            symbol: Trading pair symbol

        Returns:
            Dict with walk-forward results and metrics
        """
        logger.info(
            f"Starting walk-forward optimization: "
            f"train={train_months}m, test={test_months}m"
        )

        self.results = []

        total_months = train_months + test_months
        start_date = data.index[0]
        end_date = data.index[-1]

        windows = self._generate_windows(
            data, train_months, test_months
        )

        logger.info(f"Generated {len(windows)} walk-forward windows")

        for i, (train_data, test_data) in enumerate(windows):
            logger.info(
                f"\nWindow {i+1}/{len(windows)}: "
                f"Train {train_data.index[0]} to {train_data.index[-1]}, "
                f"Test {test_data.index[0]} to {test_data.index[-1]}"
            )

            best_params, opt_results = self.optimizer.grid_search(
                strategy_class,
                base_config,
                param_grid,
                train_data,
                symbol
            )

            test_strategy = strategy_class(f"wf_test_{i}", {**base_config, **best_params})
            test_results = self.backtest_engine.run_backtest(
                test_strategy, test_data, symbol
            )

            window_result = {
                'window': i + 1,
                'train_start': train_data.index[0],
                'train_end': train_data.index[-1],
                'test_start': test_data.index[0],
                'test_end': test_data.index[-1],
                'best_params': best_params,
                'test_metrics': test_results
            }
            self.results.append(window_result)

            logger.info(
                f"Window {i+1} complete: "
                f"Test {self.optimizer.optimization_metric}="
                f"{test_results.get(self.optimizer.optimization_metric, 0):.4f}"
            )

        wf_metrics = self._calculate_wf_metrics()

        logger.info(
            f"\nWalk-forward optimization complete. "
            f"WF Efficiency: {wf_metrics.get('wf_efficiency', 0):.2f}%"
        )

        return {
            'windows': self.results,
            'metrics': wf_metrics
        }

    def _generate_windows(
        self,
        data: pd.DataFrame,
        train_months: int,
        test_months: int
    ) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Generate rolling windows for walk-forward"""
        windows = []

        days_per_month = 30
        train_days = train_months * days_per_month
        test_days = test_months * days_per_month
        window_days = train_days + test_days

        total_days = (data.index[-1] - data.index[0]).days

        current_start = 0

        while True:
            train_end = current_start + int(len(data) * train_days / total_days)

            if train_end >= len(data):
                break

            test_end = train_end + int(len(data) * test_days / total_days)

            if test_end > len(data):
                test_end = len(data)

            train_data = data.iloc[current_start:train_end]
            test_data = data.iloc[train_end:test_end]

            if len(train_data) > 0 and len(test_data) > 0:
                windows.append((train_data, test_data))

            current_start = train_end

            if test_end >= len(data):
                break

        return windows

    def _calculate_wf_metrics(self) -> Dict[str, Any]:
        """Calculate walk-forward efficiency metrics"""
        if not self.results:
            return {}

        test_scores = [
            r['test_metrics'].get(self.optimizer.optimization_metric, 0)
            for r in self.results
        ]

        metrics = {
            'num_windows': len(self.results),
            'avg_test_score': np.mean(test_scores),
            'std_test_score': np.std(test_scores),
            'min_test_score': np.min(test_scores),
            'max_test_score': np.max(test_scores),
            'positive_windows': sum(1 for s in test_scores if s > 0),
            'negative_windows': sum(1 for s in test_scores if s <= 0)
        }

        if metrics['avg_test_score'] != 0:
            metrics['wf_efficiency'] = metrics['avg_test_score'] * 100
        else:
            metrics['wf_efficiency'] = 0.0

        param_stability = self._analyze_parameter_stability()
        metrics.update(param_stability)

        return metrics

    def _analyze_parameter_stability(self) -> Dict[str, Any]:
        """Analyze stability of optimal parameters across windows"""
        if not self.results:
            return {}

        all_params = {}
        for result in self.results:
            for param_name, param_value in result['best_params'].items():
                if param_name not in all_params:
                    all_params[param_name] = []
                all_params[param_name].append(param_value)

        stability = {}
        for param_name, values in all_params.items():
            if isinstance(values[0], (int, float)):
                stability[f'{param_name}_mean'] = np.mean(values)
                stability[f'{param_name}_std'] = np.std(values)
                stability[f'{param_name}_cv'] = (
                    np.std(values) / np.mean(values) if np.mean(values) != 0 else 0
                )
            else:
                unique_values = len(set(values))
                stability[f'{param_name}_unique_count'] = unique_values

        return stability

    def get_results_dataframe(self) -> pd.DataFrame:
        """Convert walk-forward results to DataFrame"""
        if not self.results:
            return pd.DataFrame()

        rows = []
        for result in self.results:
            row = {
                'window': result['window'],
                'train_start': result['train_start'],
                'train_end': result['train_end'],
                'test_start': result['test_start'],
                'test_end': result['test_end']
            }

            for param_name, param_value in result['best_params'].items():
                row[f'param_{param_name}'] = param_value

            test_metrics = result['test_metrics']
            for key in ['total_return_pct', 'sharpe_ratio', 'max_drawdown_pct',
                       'win_rate', 'profit_factor', 'num_trades']:
                if key in test_metrics:
                    row[f'test_{key}'] = test_metrics[key]

            rows.append(row)

        return pd.DataFrame(rows)

    def plot_walk_forward_results(self) -> None:
        """Plot walk-forward results (requires matplotlib)"""
        try:
            import matplotlib.pyplot as plt

            df = self.get_results_dataframe()

            if df.empty:
                logger.warning("No results to plot")
                return

            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            fig.suptitle('Walk-Forward Optimization Results', fontsize=16)

            if 'test_total_return_pct' in df.columns:
                axes[0, 0].plot(df['window'], df['test_total_return_pct'], marker='o')
                axes[0, 0].set_xlabel('Window')
                axes[0, 0].set_ylabel('Return (%)')
                axes[0, 0].set_title('Test Returns by Window')
                axes[0, 0].grid(True)

            if 'test_sharpe_ratio' in df.columns:
                axes[0, 1].plot(df['window'], df['test_sharpe_ratio'], marker='o', color='green')
                axes[0, 1].set_xlabel('Window')
                axes[0, 1].set_ylabel('Sharpe Ratio')
                axes[0, 1].set_title('Test Sharpe Ratio by Window')
                axes[0, 1].grid(True)

            if 'test_max_drawdown_pct' in df.columns:
                axes[1, 0].plot(df['window'], df['test_max_drawdown_pct'], marker='o', color='red')
                axes[1, 0].set_xlabel('Window')
                axes[1, 0].set_ylabel('Max Drawdown (%)')
                axes[1, 0].set_title('Test Max Drawdown by Window')
                axes[1, 0].grid(True)

            if 'test_win_rate' in df.columns:
                axes[1, 1].plot(df['window'], df['test_win_rate'], marker='o', color='purple')
                axes[1, 1].set_xlabel('Window')
                axes[1, 1].set_ylabel('Win Rate (%)')
                axes[1, 1].set_title('Test Win Rate by Window')
                axes[1, 1].grid(True)

            plt.tight_layout()
            plt.savefig('walk_forward_results.png')
            logger.info("Walk-forward results plot saved to walk_forward_results.png")

        except ImportError:
            logger.warning("matplotlib not available, skipping plot")
