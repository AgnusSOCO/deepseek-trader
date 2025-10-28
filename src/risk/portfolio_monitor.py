"""
Portfolio Monitor

Real-time portfolio monitoring including P&L tracking, drawdown calculation,
margin monitoring, and circuit breakers for excessive losses.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from loguru import logger


@dataclass
class PortfolioSnapshot:
    """Snapshot of portfolio state at a point in time"""
    timestamp: datetime
    total_value: float
    cash_balance: float
    positions_value: float
    unrealized_pnl: float
    realized_pnl: float
    total_pnl: float
    num_positions: int
    margin_used: float
    margin_available: float
    leverage_ratio: float
    drawdown_from_peak: float
    daily_pnl: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class PortfolioMonitor:
    """
    Monitors portfolio in real-time
    
    Responsibilities:
    - Track real-time portfolio value
    - Calculate unrealized P&L for open positions
    - Monitor drawdown from peak equity
    - Track margin usage and liquidation risk
    - Implement circuit breakers for excessive losses
    - Maintain portfolio history
    """
    
    def __init__(self, initial_balance: float, config: Dict[str, Any]):
        """
        Initialize portfolio monitor
        
        Args:
            initial_balance: Starting portfolio balance
            config: Portfolio monitoring configuration
        """
        self.initial_balance = initial_balance
        self.config = config
        
        self.current_balance = initial_balance
        self.peak_balance = initial_balance
        self.daily_start_balance = initial_balance
        self.last_reset_date = datetime.now().date()
        
        self.realized_pnl = 0.0
        self.total_fees_paid = 0.0
        
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        self.daily_drawdown = 0.0
        
        self.circuit_breaker_triggered = False
        self.circuit_breaker_reason = None
        self.max_daily_loss_pct = config.get('max_daily_loss_pct', 0.05)  # 5%
        self.max_total_loss_pct = config.get('max_total_loss_pct', 0.15)  # 15%
        self.max_consecutive_losses = config.get('max_consecutive_losses', 5)
        
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        self.snapshots: List[PortfolioSnapshot] = []
        self.max_history_size = config.get('max_history_size', 10000)
        
        logger.info(f"Initialized portfolio monitor with balance: {initial_balance}")
    
    def update(self,
               current_positions: List[Dict[str, Any]],
               market_prices: Dict[str, float],
               cash_balance: float) -> PortfolioSnapshot:
        """
        Update portfolio state with current positions and prices
        
        Args:
            current_positions: List of current open positions
            market_prices: Current market prices for all symbols
            cash_balance: Current cash balance
            
        Returns:
            Portfolio snapshot
        """
        self._check_daily_reset()
        
        positions_value = 0.0
        unrealized_pnl = 0.0
        margin_used = 0.0
        
        for position in current_positions:
            symbol = position.get('symbol', '')
            quantity = position.get('quantity', 0)
            entry_price = position.get('entry_price', 0)
            leverage = position.get('leverage', 1.0)
            
            current_price = market_prices.get(symbol, entry_price)
            
            position_value = quantity * current_price
            positions_value += position_value
            
            position_pnl = (current_price - entry_price) * quantity
            unrealized_pnl += position_pnl
            
            margin_used += position_value / leverage if leverage > 1 else position_value
        
        total_value = cash_balance + positions_value
        
        total_pnl = self.realized_pnl + unrealized_pnl
        
        daily_pnl = total_value - self.daily_start_balance
        
        if total_value > self.peak_balance:
            self.peak_balance = total_value
        
        drawdown_from_peak = (self.peak_balance - total_value) / self.peak_balance if self.peak_balance > 0 else 0
        self.current_drawdown = drawdown_from_peak
        
        if drawdown_from_peak > self.max_drawdown:
            self.max_drawdown = drawdown_from_peak
        
        self.daily_drawdown = abs(daily_pnl) / self.daily_start_balance if self.daily_start_balance > 0 else 0
        
        leverage_ratio = positions_value / total_value if total_value > 0 else 0
        
        margin_available = cash_balance - margin_used
        
        snapshot = PortfolioSnapshot(
            timestamp=datetime.now(),
            total_value=total_value,
            cash_balance=cash_balance,
            positions_value=positions_value,
            unrealized_pnl=unrealized_pnl,
            realized_pnl=self.realized_pnl,
            total_pnl=total_pnl,
            num_positions=len(current_positions),
            margin_used=margin_used,
            margin_available=margin_available,
            leverage_ratio=leverage_ratio,
            drawdown_from_peak=drawdown_from_peak,
            daily_pnl=daily_pnl,
            metadata={
                'max_drawdown': self.max_drawdown,
                'daily_drawdown': self.daily_drawdown,
                'total_fees_paid': self.total_fees_paid,
                'total_trades': self.total_trades,
                'winning_trades': self.winning_trades,
                'losing_trades': self.losing_trades,
                'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
                'consecutive_losses': self.consecutive_losses,
                'consecutive_wins': self.consecutive_wins
            }
        )
        
        self._add_snapshot(snapshot)
        
        self._check_circuit_breakers(snapshot)
        
        self.current_balance = total_value
        
        return snapshot
    
    def record_trade(self, trade: Dict[str, Any]) -> None:
        """
        Record a completed trade
        
        Args:
            trade: Trade information (pnl, fees, etc.)
        """
        pnl = trade.get('pnl', 0)
        fees = trade.get('fees', 0)
        
        self.realized_pnl += pnl
        self.total_fees_paid += fees
        
        self.total_trades += 1
        
        if pnl > 0:
            self.winning_trades += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
        else:
            self.losing_trades += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        logger.info(f"Recorded trade: PnL={pnl:.2f}, Fees={fees:.2f}, "
                   f"Total trades={self.total_trades}, Win rate={self.winning_trades/self.total_trades*100:.1f}%")
    
    def _check_daily_reset(self) -> None:
        """Check if we need to reset daily tracking"""
        current_date = datetime.now().date()
        
        if current_date > self.last_reset_date:
            self.daily_start_balance = self.current_balance
            self.last_reset_date = current_date
            logger.info(f"Reset daily tracking: start balance={self.daily_start_balance:.2f}")
    
    def _check_circuit_breakers(self, snapshot: PortfolioSnapshot) -> None:
        """
        Check if circuit breakers should be triggered
        
        Args:
            snapshot: Current portfolio snapshot
        """
        if self.circuit_breaker_triggered:
            return
        
        if self.daily_drawdown > self.max_daily_loss_pct:
            self.circuit_breaker_triggered = True
            self.circuit_breaker_reason = f"Daily loss limit exceeded: {self.daily_drawdown*100:.1f}%"
            logger.error(f"CIRCUIT BREAKER TRIGGERED: {self.circuit_breaker_reason}")
            return
        
        total_loss_pct = (self.initial_balance - snapshot.total_value) / self.initial_balance if self.initial_balance > 0 else 0
        if total_loss_pct > self.max_total_loss_pct:
            self.circuit_breaker_triggered = True
            self.circuit_breaker_reason = f"Total loss limit exceeded: {total_loss_pct*100:.1f}%"
            logger.error(f"CIRCUIT BREAKER TRIGGERED: {self.circuit_breaker_reason}")
            return
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.circuit_breaker_triggered = True
            self.circuit_breaker_reason = f"Consecutive losses limit exceeded: {self.consecutive_losses}"
            logger.error(f"CIRCUIT BREAKER TRIGGERED: {self.circuit_breaker_reason}")
            return
    
    def reset_circuit_breaker(self) -> None:
        """Reset circuit breaker (manual intervention required)"""
        self.circuit_breaker_triggered = False
        self.circuit_breaker_reason = None
        logger.warning("Circuit breaker manually reset")
    
    def is_circuit_breaker_triggered(self) -> bool:
        """Check if circuit breaker is triggered"""
        return self.circuit_breaker_triggered
    
    def _add_snapshot(self, snapshot: PortfolioSnapshot) -> None:
        """Add snapshot to history"""
        self.snapshots.append(snapshot)
        
        if len(self.snapshots) > self.max_history_size:
            self.snapshots = self.snapshots[-self.max_history_size:]
    
    def get_current_snapshot(self) -> Optional[PortfolioSnapshot]:
        """Get most recent portfolio snapshot"""
        return self.snapshots[-1] if self.snapshots else None
    
    def get_snapshot_history(self, limit: int = 100) -> List[PortfolioSnapshot]:
        """
        Get recent snapshot history
        
        Args:
            limit: Maximum number of snapshots to return
            
        Returns:
            List of recent snapshots
        """
        return self.snapshots[-limit:]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate comprehensive performance metrics
        
        Returns:
            Dictionary with performance metrics
        """
        current_snapshot = self.get_current_snapshot()
        
        if not current_snapshot:
            return {}
        
        total_return = (current_snapshot.total_value - self.initial_balance) / self.initial_balance if self.initial_balance > 0 else 0
        daily_return = current_snapshot.daily_pnl / self.daily_start_balance if self.daily_start_balance > 0 else 0
        
        win_rate = self.winning_trades / self.total_trades if self.total_trades > 0 else 0
        
        avg_win = self.realized_pnl / self.winning_trades if self.winning_trades > 0 else 0
        avg_loss = abs(self.realized_pnl) / self.losing_trades if self.losing_trades > 0 else 0
        
        gross_profit = sum(s.realized_pnl for s in self.snapshots if s.realized_pnl > 0)
        gross_loss = abs(sum(s.realized_pnl for s in self.snapshots if s.realized_pnl < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        if len(self.snapshots) > 1:
            daily_returns = []
            for i in range(1, len(self.snapshots)):
                prev_value = self.snapshots[i-1].total_value
                curr_value = self.snapshots[i].total_value
                daily_return = (curr_value - prev_value) / prev_value if prev_value > 0 else 0
                daily_returns.append(daily_return)
            
            if daily_returns:
                import statistics
                avg_return = statistics.mean(daily_returns)
                std_return = statistics.stdev(daily_returns) if len(daily_returns) > 1 else 0
                sharpe_ratio = (avg_return / std_return * (252 ** 0.5)) if std_return > 0 else 0
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_return_pct': total_return * 100,
            'daily_return_pct': daily_return * 100,
            'total_pnl': current_snapshot.total_pnl,
            'realized_pnl': current_snapshot.realized_pnl,
            'unrealized_pnl': current_snapshot.unrealized_pnl,
            'total_fees_paid': self.total_fees_paid,
            'max_drawdown_pct': self.max_drawdown * 100,
            'current_drawdown_pct': self.current_drawdown * 100,
            'daily_drawdown_pct': self.daily_drawdown * 100,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate_pct': win_rate * 100,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'consecutive_wins': self.consecutive_wins,
            'consecutive_losses': self.consecutive_losses,
            'circuit_breaker_triggered': self.circuit_breaker_triggered,
            'circuit_breaker_reason': self.circuit_breaker_reason
        }
    
    def get_equity_curve(self, period: str = 'all') -> List[Dict[str, Any]]:
        """
        Get equity curve data
        
        Args:
            period: Time period ('1h', '1d', '1w', 'all')
            
        Returns:
            List of equity curve points
        """
        if period == 'all':
            snapshots = self.snapshots
        else:
            now = datetime.now()
            if period == '1h':
                cutoff = now - timedelta(hours=1)
            elif period == '1d':
                cutoff = now - timedelta(days=1)
            elif period == '1w':
                cutoff = now - timedelta(weeks=1)
            else:
                cutoff = now - timedelta(days=1)
            
            snapshots = [s for s in self.snapshots if s.timestamp >= cutoff]
        
        return [
            {
                'timestamp': s.timestamp.isoformat(),
                'total_value': s.total_value,
                'unrealized_pnl': s.unrealized_pnl,
                'realized_pnl': s.realized_pnl,
                'drawdown': s.drawdown_from_peak
            }
            for s in snapshots
        ]
    
    def reset(self) -> None:
        """Reset portfolio monitor to initial state"""
        self.current_balance = self.initial_balance
        self.peak_balance = self.initial_balance
        self.daily_start_balance = self.initial_balance
        self.realized_pnl = 0.0
        self.total_fees_paid = 0.0
        self.max_drawdown = 0.0
        self.current_drawdown = 0.0
        self.daily_drawdown = 0.0
        self.circuit_breaker_triggered = False
        self.circuit_breaker_reason = None
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.snapshots = []
        logger.info("Reset portfolio monitor")
