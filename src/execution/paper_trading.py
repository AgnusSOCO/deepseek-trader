"""
Paper Trading Framework

Simulates live trading without real capital for validation and testing.
Tracks simulated positions, P&L, and performance metrics.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import json
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PaperPosition:
    """Represents a simulated position in paper trading"""
    position_id: str
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    quantity: float
    leverage: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    entry_time: datetime = field(default_factory=datetime.now)
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    realized_pnl: Optional[float] = None
    realized_pnl_pct: Optional[float] = None
    max_pnl: float = 0.0
    min_pnl: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_pnl(self, current_price: float) -> Dict[str, float]:
        """
        Calculate current P&L for the position
        
        Returns:
            Dict with pnl, pnl_pct, pnl_leverage_adjusted
        """
        if self.side == 'long':
            price_change_pct = (current_price - self.entry_price) / self.entry_price
        else:  # short
            price_change_pct = (self.entry_price - current_price) / self.entry_price
        
        pnl_pct = price_change_pct * self.leverage * 100
        pnl = (self.entry_price * self.quantity) * (pnl_pct / 100)
        
        self.max_pnl = max(self.max_pnl, pnl_pct)
        self.min_pnl = min(self.min_pnl, pnl_pct)
        
        return {
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'price_change_pct': price_change_pct * 100,
            'max_pnl': self.max_pnl,
            'min_pnl': self.min_pnl
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'position_id': self.position_id,
            'symbol': self.symbol,
            'side': self.side,
            'entry_price': self.entry_price,
            'quantity': self.quantity,
            'leverage': self.leverage,
            'stop_loss': self.stop_loss,
            'take_profit': self.take_profit,
            'entry_time': self.entry_time.isoformat(),
            'exit_time': self.exit_time.isoformat() if self.exit_time else None,
            'exit_price': self.exit_price,
            'exit_reason': self.exit_reason,
            'realized_pnl': self.realized_pnl,
            'realized_pnl_pct': self.realized_pnl_pct,
            'max_pnl': self.max_pnl,
            'min_pnl': self.min_pnl,
            'metadata': self.metadata
        }


class PaperTradingEngine:
    """
    Paper trading engine for simulated trading
    
    Features:
    - Simulated position management
    - Realistic slippage and fees
    - P&L tracking
    - Performance metrics
    - Trade history logging
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        slippage_pct: float = 0.05,
        maker_fee_pct: float = 0.02,
        taker_fee_pct: float = 0.06,
        log_dir: str = "./paper_trading_logs"
    ):
        """
        Initialize paper trading engine
        
        Args:
            initial_capital: Starting capital
            slippage_pct: Slippage percentage
            maker_fee_pct: Maker fee percentage
            taker_fee_pct: Taker fee percentage
            log_dir: Directory for trade logs
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.peak_capital = initial_capital
        
        self.slippage_pct = slippage_pct / 100
        self.maker_fee_pct = maker_fee_pct / 100
        self.taker_fee_pct = taker_fee_pct / 100
        
        self.positions: Dict[str, PaperPosition] = {}
        self.closed_positions: List[PaperPosition] = []
        
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.session_start = datetime.now()
        
        logger.info(f"Paper trading engine initialized with ${initial_capital:,.2f}")
    
    def open_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        position_size_pct: float,
        leverage: float = 1.0,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[PaperPosition]:
        """
        Open a new paper trading position
        
        Args:
            symbol: Trading symbol
            side: 'long' or 'short'
            entry_price: Entry price
            position_size_pct: Position size as percentage of capital (0-100)
            leverage: Leverage multiplier
            stop_loss: Stop-loss price
            take_profit: Take-profit price
            metadata: Additional metadata
        
        Returns:
            PaperPosition if successful, None otherwise
        """
        if side == 'long':
            actual_entry_price = entry_price * (1 + self.slippage_pct)
        else:
            actual_entry_price = entry_price * (1 - self.slippage_pct)
        
        position_value = self.current_capital * (position_size_pct / 100)
        quantity = position_value / actual_entry_price
        
        fee = position_value * self.taker_fee_pct
        
        required_margin = position_value / leverage
        if required_margin + fee > self.current_capital:
            logger.warning(f"Insufficient capital for position: required ${required_margin + fee:,.2f}, available ${self.current_capital:,.2f}")
            return None
        
        position_id = f"{symbol}_{side}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        position = PaperPosition(
            position_id=position_id,
            symbol=symbol,
            side=side,
            entry_price=actual_entry_price,
            quantity=quantity,
            leverage=leverage,
            stop_loss=stop_loss,
            take_profit=take_profit,
            metadata=metadata or {}
        )
        
        self.current_capital -= (required_margin + fee)
        
        self.positions[position_id] = position
        self.total_trades += 1
        
        logger.info(f"Opened {side} position: {symbol} @ ${actual_entry_price:,.2f}, size: {position_size_pct}%, leverage: {leverage}x")
        
        self._log_trade('OPEN', position)
        
        return position
    
    def close_position(
        self,
        position_id: str,
        exit_price: float,
        reason: str = "manual"
    ) -> Optional[Dict[str, Any]]:
        """
        Close an existing position
        
        Args:
            position_id: Position identifier
            exit_price: Exit price
            reason: Reason for closing
        
        Returns:
            Dict with exit details if successful, None otherwise
        """
        if position_id not in self.positions:
            logger.warning(f"Position {position_id} not found")
            return None
        
        position = self.positions[position_id]
        
        if position.side == 'long':
            actual_exit_price = exit_price * (1 - self.slippage_pct)
        else:
            actual_exit_price = exit_price * (1 + self.slippage_pct)
        
        pnl_data = position.calculate_pnl(actual_exit_price)
        
        position_value = position.entry_price * position.quantity
        fee = position_value * self.taker_fee_pct
        
        margin = position_value / position.leverage
        self.current_capital += margin + pnl_data['pnl'] - fee
        
        self.peak_capital = max(self.peak_capital, self.current_capital)
        
        position.exit_time = datetime.now()
        position.exit_price = actual_exit_price
        position.exit_reason = reason
        position.realized_pnl = pnl_data['pnl']
        position.realized_pnl_pct = pnl_data['pnl_pct']
        
        if pnl_data['pnl'] > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        
        self.closed_positions.append(position)
        del self.positions[position_id]
        
        logger.info(f"Closed {position.side} position: {position.symbol} @ ${actual_exit_price:,.2f}, P&L: ${pnl_data['pnl']:,.2f} ({pnl_data['pnl_pct']:.2f}%), reason: {reason}")
        
        self._log_trade('CLOSE', position)
        
        return {
            'position_id': position_id,
            'exit_price': actual_exit_price,
            'pnl': pnl_data['pnl'],
            'pnl_pct': pnl_data['pnl_pct'],
            'reason': reason
        }
    
    def update_positions(self, current_prices: Dict[str, float]) -> List[Dict[str, Any]]:
        """
        Update all positions with current prices and check exit conditions
        
        Args:
            current_prices: Dict of symbol -> current price
        
        Returns:
            List of positions that should be closed
        """
        positions_to_close = []
        
        for position_id, position in list(self.positions.items()):
            if position.symbol not in current_prices:
                continue
            
            current_price = current_prices[position.symbol]
            pnl_data = position.calculate_pnl(current_price)
            
            if position.stop_loss is not None:
                if position.side == 'long' and current_price <= position.stop_loss:
                    positions_to_close.append({
                        'position_id': position_id,
                        'exit_price': current_price,
                        'reason': 'stop_loss'
                    })
                    continue
                elif position.side == 'short' and current_price >= position.stop_loss:
                    positions_to_close.append({
                        'position_id': position_id,
                        'exit_price': current_price,
                        'reason': 'stop_loss'
                    })
                    continue
            
            if position.take_profit is not None:
                if position.side == 'long' and current_price >= position.take_profit:
                    positions_to_close.append({
                        'position_id': position_id,
                        'exit_price': current_price,
                        'reason': 'take_profit'
                    })
                    continue
                elif position.side == 'short' and current_price <= position.take_profit:
                    positions_to_close.append({
                        'position_id': position_id,
                        'exit_price': current_price,
                        'reason': 'take_profit'
                    })
                    continue
        
        return positions_to_close
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Calculate performance metrics
        
        Returns:
            Dict with performance metrics
        """
        total_return = self.current_capital - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        drawdown = ((self.peak_capital - self.current_capital) / self.peak_capital) * 100
        
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        winning_pnls = [p.realized_pnl for p in self.closed_positions if p.realized_pnl and p.realized_pnl > 0]
        losing_pnls = [p.realized_pnl for p in self.closed_positions if p.realized_pnl and p.realized_pnl < 0]
        
        avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
        avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
        
        profit_factor = abs(sum(winning_pnls) / sum(losing_pnls)) if losing_pnls and sum(losing_pnls) != 0 else 0
        
        session_duration = datetime.now() - self.session_start
        
        return {
            'initial_capital': self.initial_capital,
            'current_capital': self.current_capital,
            'peak_capital': self.peak_capital,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'drawdown_pct': drawdown,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'open_positions': len(self.positions),
            'session_duration': str(session_duration).split('.')[0]
        }
    
    def _log_trade(self, action: str, position: PaperPosition):
        """Log trade to file"""
        log_file = self.log_dir / f"paper_trades_{self.session_start.strftime('%Y%m%d')}.jsonl"
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'action': action,
            'position': position.to_dict()
        }
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def save_session_report(self):
        """Save session report to file"""
        report_file = self.log_dir / f"session_report_{self.session_start.strftime('%Y%m%d_%H%M%S')}.json"
        
        metrics = self.get_performance_metrics()
        
        report = {
            'session_start': self.session_start.isoformat(),
            'session_end': datetime.now().isoformat(),
            'metrics': metrics,
            'closed_positions': [p.to_dict() for p in self.closed_positions],
            'open_positions': [p.to_dict() for p in self.positions.values()]
        }
        
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        logger.info(f"Session report saved to {report_file}")
        
        return report
