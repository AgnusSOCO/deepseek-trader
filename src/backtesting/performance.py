"""
Performance Metrics Calculator

Comprehensive performance metrics for backtest analysis.
"""

import logging
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceMetrics:
    """
    Calculate comprehensive performance metrics for backtesting
    
    Metrics include:
    - Returns (total, annualized, monthly)
    - Risk metrics (Sharpe, Sortino, Calmar)
    - Drawdown analysis
    - Trade statistics
    - Win/loss analysis
    """
    
    @staticmethod
    def calculate_all_metrics(
        trades: List[Any],
        equity_curve: List[Tuple[datetime, float]],
        initial_capital: float,
        risk_free_rate: float = 0.02
    ) -> Dict[str, Any]:
        """
        Calculate all performance metrics
        
        Args:
            trades: List of Trade objects
            equity_curve: List of (timestamp, equity) tuples
            initial_capital: Starting capital
            risk_free_rate: Annual risk-free rate (default: 2%)
        
        Returns:
            Dict with all performance metrics
        """
        if not trades or not equity_curve:
            return PerformanceMetrics._empty_metrics()
        
        metrics = {}
        
        metrics.update(PerformanceMetrics._calculate_returns(
            equity_curve, initial_capital
        ))
        
        metrics.update(PerformanceMetrics._calculate_risk_metrics(
            trades, equity_curve, initial_capital, risk_free_rate
        ))
        
        metrics.update(PerformanceMetrics._calculate_drawdown_metrics(
            equity_curve
        ))
        
        metrics.update(PerformanceMetrics._calculate_trade_stats(trades))
        
        metrics.update(PerformanceMetrics._calculate_win_loss_stats(trades))
        
        metrics.update(PerformanceMetrics._calculate_time_stats(
            trades, equity_curve
        ))
        
        return metrics
    
    @staticmethod
    def _empty_metrics() -> Dict[str, Any]:
        """Return empty metrics dict"""
        return {
            'total_return_pct': 0.0,
            'annualized_return_pct': 0.0,
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'calmar_ratio': 0.0,
            'max_drawdown_pct': 0.0,
            'num_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0
        }
    
    @staticmethod
    def _calculate_returns(
        equity_curve: List[Tuple[datetime, float]],
        initial_capital: float
    ) -> Dict[str, Any]:
        """Calculate return metrics"""
        final_equity = equity_curve[-1][1]
        total_return = final_equity - initial_capital
        total_return_pct = (total_return / initial_capital) * 100
        
        start_date = equity_curve[0][0]
        end_date = equity_curve[-1][0]
        days = (end_date - start_date).days
        years = days / 365.25
        
        if years > 0:
            annualized_return_pct = ((final_equity / initial_capital) ** (1 / years) - 1) * 100
        else:
            annualized_return_pct = 0.0
        
        return {
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'annualized_return_pct': annualized_return_pct,
            'final_equity': final_equity
        }
    
    @staticmethod
    def _calculate_risk_metrics(
        trades: List[Any],
        equity_curve: List[Tuple[datetime, float]],
        initial_capital: float,
        risk_free_rate: float
    ) -> Dict[str, Any]:
        """Calculate risk-adjusted metrics"""
        returns = [t.pnl_pct for t in trades]
        
        if len(returns) < 2:
            return {
                'sharpe_ratio': 0.0,
                'sortino_ratio': 0.0,
                'calmar_ratio': 0.0
            }
        
        avg_return = np.mean(returns)
        std_return = np.std(returns, ddof=1)
        
        if std_return > 0:
            sharpe_ratio = (avg_return - (risk_free_rate / 252)) / std_return
        else:
            sharpe_ratio = 0.0
        
        negative_returns = [r for r in returns if r < 0]
        if negative_returns:
            downside_std = np.std(negative_returns, ddof=1)
            if downside_std > 0:
                sortino_ratio = (avg_return - (risk_free_rate / 252)) / downside_std
            else:
                sortino_ratio = 0.0
        else:
            sortino_ratio = 0.0
        
        max_dd = PerformanceMetrics._calculate_max_drawdown(equity_curve)
        if max_dd > 0:
            final_equity = equity_curve[-1][1]
            total_return_pct = ((final_equity / initial_capital) - 1) * 100
            calmar_ratio = total_return_pct / max_dd
        else:
            calmar_ratio = 0.0
        
        return {
            'sharpe_ratio': sharpe_ratio,
            'sortino_ratio': sortino_ratio,
            'calmar_ratio': calmar_ratio,
            'avg_return_pct': avg_return,
            'std_return_pct': std_return
        }
    
    @staticmethod
    def _calculate_drawdown_metrics(
        equity_curve: List[Tuple[datetime, float]]
    ) -> Dict[str, Any]:
        """Calculate drawdown metrics"""
        equity_values = [eq for _, eq in equity_curve]
        timestamps = [ts for ts, _ in equity_curve]
        
        peak = equity_values[0]
        max_drawdown = 0.0
        max_drawdown_duration = 0
        current_drawdown_duration = 0
        drawdown_start = None
        max_dd_start = None
        max_dd_end = None
        
        drawdowns = []
        
        for i, equity in enumerate(equity_values):
            if equity > peak:
                if drawdown_start:
                    drawdown_duration = (timestamps[i] - drawdown_start).days
                    max_drawdown_duration = max(max_drawdown_duration, drawdown_duration)
                    drawdown_start = None
                    current_drawdown_duration = 0
                peak = equity
            else:
                if not drawdown_start:
                    drawdown_start = timestamps[i]
                
                drawdown = ((peak - equity) / peak) * 100
                drawdowns.append(drawdown)
                
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
                    max_dd_start = drawdown_start
                    max_dd_end = timestamps[i]
                
                current_drawdown_duration = (timestamps[i] - drawdown_start).days
        
        avg_drawdown = np.mean(drawdowns) if drawdowns else 0.0
        
        return {
            'max_drawdown_pct': max_drawdown,
            'avg_drawdown_pct': avg_drawdown,
            'max_drawdown_duration_days': max_drawdown_duration,
            'max_drawdown_start': max_dd_start,
            'max_drawdown_end': max_dd_end
        }
    
    @staticmethod
    def _calculate_max_drawdown(equity_curve: List[Tuple[datetime, float]]) -> float:
        """Calculate maximum drawdown percentage"""
        equity_values = [eq for _, eq in equity_curve]
        peak = equity_values[0]
        max_drawdown = 0.0
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        return max_drawdown
    
    @staticmethod
    def _calculate_trade_stats(trades: List[Any]) -> Dict[str, Any]:
        """Calculate trade statistics"""
        num_trades = len(trades)
        
        if num_trades == 0:
            return {
                'num_trades': 0,
                'avg_trade_pnl': 0.0,
                'avg_trade_pnl_pct': 0.0,
                'best_trade_pnl': 0.0,
                'worst_trade_pnl': 0.0,
                'total_fees': 0.0
            }
        
        pnls = [t.pnl for t in trades]
        pnl_pcts = [t.pnl_pct for t in trades]
        fees = [t.fees for t in trades]
        
        return {
            'num_trades': num_trades,
            'avg_trade_pnl': np.mean(pnls),
            'avg_trade_pnl_pct': np.mean(pnl_pcts),
            'best_trade_pnl': max(pnls),
            'worst_trade_pnl': min(pnls),
            'total_fees': sum(fees),
            'avg_fees_per_trade': np.mean(fees)
        }
    
    @staticmethod
    def _calculate_win_loss_stats(trades: List[Any]) -> Dict[str, Any]:
        """Calculate win/loss statistics"""
        if not trades:
            return {
                'num_wins': 0,
                'num_losses': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'avg_win_loss_ratio': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'consecutive_wins_max': 0,
                'consecutive_losses_max': 0
            }
        
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]
        
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        win_rate = (num_wins / len(trades)) * 100
        
        total_profit = sum(t.pnl for t in winning_trades)
        total_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0.0
        
        avg_win = (total_profit / num_wins) if num_wins > 0 else 0.0
        avg_loss = (total_loss / num_losses) if num_losses > 0 else 0.0
        avg_win_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0
        
        largest_win = max((t.pnl for t in winning_trades), default=0.0)
        largest_loss = min((t.pnl for t in losing_trades), default=0.0)
        
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        
        for trade in trades:
            if trade.pnl > 0:
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
            else:
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
        
        expectancy = (win_rate / 100 * avg_win) - ((100 - win_rate) / 100 * avg_loss)
        
        return {
            'num_wins': num_wins,
            'num_losses': num_losses,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_win_loss_ratio': avg_win_loss_ratio,
            'largest_win': largest_win,
            'largest_loss': largest_loss,
            'consecutive_wins_max': max_consecutive_wins,
            'consecutive_losses_max': max_consecutive_losses,
            'expectancy': expectancy
        }
    
    @staticmethod
    def _calculate_time_stats(
        trades: List[Any],
        equity_curve: List[Tuple[datetime, float]]
    ) -> Dict[str, Any]:
        """Calculate time-based statistics"""
        if not trades:
            return {
                'avg_trade_duration_minutes': 0.0,
                'avg_trade_duration_hours': 0.0,
                'shortest_trade_minutes': 0.0,
                'longest_trade_minutes': 0.0,
                'total_trading_days': 0
            }
        
        durations = [t.duration_minutes for t in trades]
        
        start_date = equity_curve[0][0]
        end_date = equity_curve[-1][0]
        total_days = (end_date - start_date).days
        
        return {
            'avg_trade_duration_minutes': np.mean(durations),
            'avg_trade_duration_hours': np.mean(durations) / 60,
            'shortest_trade_minutes': min(durations),
            'longest_trade_minutes': max(durations),
            'total_trading_days': total_days,
            'trades_per_day': len(trades) / max(total_days, 1)
        }
    
    @staticmethod
    def print_summary(metrics: Dict[str, Any]):
        """Print formatted metrics summary"""
        print("\n" + "="*60)
        print("BACKTEST PERFORMANCE SUMMARY")
        print("="*60)
        
        print("\n--- Returns ---")
        print(f"Total Return: ${metrics.get('total_return', 0):.2f} ({metrics.get('total_return_pct', 0):.2f}%)")
        print(f"Annualized Return: {metrics.get('annualized_return_pct', 0):.2f}%")
        print(f"Final Equity: ${metrics.get('final_equity', 0):.2f}")
        
        print("\n--- Risk Metrics ---")
        print(f"Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}")
        print(f"Sortino Ratio: {metrics.get('sortino_ratio', 0):.2f}")
        print(f"Calmar Ratio: {metrics.get('calmar_ratio', 0):.2f}")
        print(f"Max Drawdown: {metrics.get('max_drawdown_pct', 0):.2f}%")
        print(f"Avg Drawdown: {metrics.get('avg_drawdown_pct', 0):.2f}%")
        
        print("\n--- Trade Statistics ---")
        print(f"Total Trades: {metrics.get('num_trades', 0)}")
        print(f"Wins: {metrics.get('num_wins', 0)} | Losses: {metrics.get('num_losses', 0)}")
        print(f"Win Rate: {metrics.get('win_rate', 0):.2f}%")
        print(f"Profit Factor: {metrics.get('profit_factor', 0):.2f}")
        print(f"Avg Win/Loss Ratio: {metrics.get('avg_win_loss_ratio', 0):.2f}")
        
        print("\n--- P&L Analysis ---")
        print(f"Avg Trade P&L: ${metrics.get('avg_trade_pnl', 0):.2f} ({metrics.get('avg_trade_pnl_pct', 0):.2f}%)")
        print(f"Best Trade: ${metrics.get('best_trade_pnl', 0):.2f}")
        print(f"Worst Trade: ${metrics.get('worst_trade_pnl', 0):.2f}")
        print(f"Expectancy: ${metrics.get('expectancy', 0):.2f}")
        
        print("\n--- Time Analysis ---")
        print(f"Avg Trade Duration: {metrics.get('avg_trade_duration_hours', 0):.2f} hours")
        print(f"Total Trading Days: {metrics.get('total_trading_days', 0)}")
        print(f"Trades per Day: {metrics.get('trades_per_day', 0):.2f}")
        
        print("\n--- Fees ---")
        print(f"Total Fees: ${metrics.get('total_fees', 0):.2f}")
        print(f"Avg Fees per Trade: ${metrics.get('avg_fees_per_trade', 0):.2f}")
        
        print("\n" + "="*60 + "\n")
