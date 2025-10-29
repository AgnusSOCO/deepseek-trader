"""
Performance Monitor (Phase E)

Comprehensive performance tracking and monitoring for autonomous trading.
Tracks metrics, generates reports, and provides real-time insights.
"""

import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
import statistics

logger = logging.getLogger(__name__)


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time"""
    timestamp: datetime
    capital: float
    open_positions: int
    daily_pnl: float
    total_pnl: float
    total_trades: int
    daily_trades: int
    win_rate: float
    max_drawdown: float
    decision_count: int
    loop_count: int


class PerformanceMonitor:
    """
    Monitors and tracks trading system performance.
    
    Features:
    - Real-time metric tracking
    - Historical performance analysis
    - Report generation
    - Metric persistence
    """
    
    def __init__(
        self,
        initial_capital: float,
        data_dir: Path,
        snapshot_interval_seconds: int = 60
    ):
        """
        Initialize performance monitor
        
        Args:
            initial_capital: Starting capital
            data_dir: Directory for data storage
            snapshot_interval_seconds: Interval for taking snapshots
        """
        self.initial_capital = initial_capital
        self.data_dir = Path(data_dir)
        self.snapshot_interval_seconds = snapshot_interval_seconds
        
        self.snapshots: List[PerformanceSnapshot] = []
        self.last_snapshot_time: Optional[datetime] = None
        
        self.metrics_file = self.data_dir / "performance_metrics.jsonl"
        
        logger.info(
            f"PerformanceMonitor initialized: "
            f"initial_capital=${initial_capital:,.2f}, "
            f"data_dir={data_dir}"
        )
    
    def update_metrics(
        self,
        timestamp: datetime,
        capital: float,
        open_positions: int,
        daily_pnl: float,
        total_pnl: float,
        total_trades: int,
        daily_trades: int,
        win_rate: float,
        max_drawdown: float,
        decision_count: int,
        loop_count: int,
    ) -> None:
        """
        Update performance metrics
        
        Args:
            timestamp: Current timestamp
            capital: Current capital
            open_positions: Number of open positions
            daily_pnl: Daily profit/loss
            total_pnl: Total profit/loss
            total_trades: Total number of trades
            daily_trades: Daily number of trades
            win_rate: Win rate percentage
            max_drawdown: Maximum drawdown percentage
            decision_count: Number of decisions made
            loop_count: Number of loops executed
        """
        snapshot = PerformanceSnapshot(
            timestamp=timestamp,
            capital=capital,
            open_positions=open_positions,
            daily_pnl=daily_pnl,
            total_pnl=total_pnl,
            total_trades=total_trades,
            daily_trades=daily_trades,
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            decision_count=decision_count,
            loop_count=loop_count
        )
        
        self.snapshots.append(snapshot)
        self.last_snapshot_time = timestamp
        
        if len(self.snapshots) > 10000:
            self.snapshots = self.snapshots[-10000:]
        
        self._save_snapshot(snapshot)
    
    def _save_snapshot(self, snapshot: PerformanceSnapshot) -> None:
        """Save snapshot to disk"""
        try:
            with open(self.metrics_file, 'a') as f:
                data = asdict(snapshot)
                data['timestamp'] = snapshot.timestamp.isoformat()
                f.write(json.dumps(data) + '\n')
        except Exception as e:
            logger.error(f"Error saving snapshot: {e}")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get performance summary
        
        Returns:
            Dict with performance summary
        """
        if not self.snapshots:
            return {
                'total_snapshots': 0,
                'current_capital': self.initial_capital,
                'total_pnl': 0.0,
                'total_pnl_pct': 0.0
            }
        
        latest = self.snapshots[-1]
        
        return {
            'total_snapshots': len(self.snapshots),
            'first_snapshot': self.snapshots[0].timestamp.isoformat(),
            'latest_snapshot': latest.timestamp.isoformat(),
            'current_capital': latest.capital,
            'initial_capital': self.initial_capital,
            'total_pnl': latest.total_pnl,
            'total_pnl_pct': (latest.capital - self.initial_capital) / self.initial_capital * 100,
            'daily_pnl': latest.daily_pnl,
            'open_positions': latest.open_positions,
            'total_trades': latest.total_trades,
            'daily_trades': latest.daily_trades,
            'win_rate': latest.win_rate,
            'max_drawdown': latest.max_drawdown,
            'total_decisions': latest.decision_count,
            'total_loops': latest.loop_count
        }
    
    def generate_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive performance report
        
        Returns:
            Dict with detailed performance analysis
        """
        if not self.snapshots:
            return {'error': 'No performance data available'}
        
        latest = self.snapshots[-1]
        
        capital_values = [s.capital for s in self.snapshots]
        pnl_values = [s.total_pnl for s in self.snapshots]
        
        report = {
            'summary': {
                'initial_capital': self.initial_capital,
                'current_capital': latest.capital,
                'total_pnl': latest.total_pnl,
                'total_pnl_pct': (latest.capital - self.initial_capital) / self.initial_capital * 100,
                'total_trades': latest.total_trades,
                'win_rate': latest.win_rate,
                'max_drawdown': latest.max_drawdown,
            },
            'statistics': {
                'avg_capital': statistics.mean(capital_values),
                'median_capital': statistics.median(capital_values),
                'capital_std_dev': statistics.stdev(capital_values) if len(capital_values) > 1 else 0,
                'min_capital': min(capital_values),
                'max_capital': max(capital_values),
            },
            'recent_performance': {
                'last_hour': self._get_period_performance(timedelta(hours=1)),
                'last_day': self._get_period_performance(timedelta(days=1)),
                'last_week': self._get_period_performance(timedelta(days=7)),
            },
            'trading_activity': {
                'total_decisions': latest.decision_count,
                'total_loops': latest.loop_count,
                'decisions_per_loop': latest.decision_count / latest.loop_count if latest.loop_count > 0 else 0,
            },
            'timestamp': datetime.now().isoformat()
        }
        
        return report
    
    def _get_period_performance(self, period: timedelta) -> Dict[str, Any]:
        """Get performance for a specific time period"""
        if not self.snapshots:
            return {'error': 'No data'}
        
        cutoff_time = datetime.now() - period
        period_snapshots = [s for s in self.snapshots if s.timestamp >= cutoff_time]
        
        if not period_snapshots:
            return {'error': 'No data for period'}
        
        first = period_snapshots[0]
        last = period_snapshots[-1]
        
        return {
            'pnl': last.total_pnl - first.total_pnl,
            'pnl_pct': (last.capital - first.capital) / first.capital * 100 if first.capital > 0 else 0,
            'trades': last.total_trades - first.total_trades,
            'snapshots': len(period_snapshots)
        }
    
    def log_summary(self) -> None:
        """Log performance summary"""
        summary = self.get_summary()
        
        logger.info("=" * 80)
        logger.info("📊 PERFORMANCE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Current Capital: ${summary['current_capital']:,.2f}")
        logger.info(f"Total P&L: ${summary['total_pnl']:,.2f} ({summary['total_pnl_pct']:.2f}%)")
        logger.info(f"Daily P&L: ${summary['daily_pnl']:,.2f}")
        logger.info(f"Open Positions: {summary['open_positions']}")
        logger.info(f"Total Trades: {summary['total_trades']}")
        logger.info(f"Win Rate: {summary['win_rate']:.1f}%")
        logger.info(f"Max Drawdown: {summary['max_drawdown']:.2f}%")
        logger.info("=" * 80)
    
    def save_metrics(self) -> None:
        """Save all metrics to disk"""
        try:
            summary_file = self.data_dir / f"performance_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            with open(summary_file, 'w') as f:
                json.dump(self.generate_report(), f, indent=2, default=str)
            
            logger.info(f"✓ Performance metrics saved to {summary_file}")
        
        except Exception as e:
            logger.error(f"Error saving metrics: {e}")
