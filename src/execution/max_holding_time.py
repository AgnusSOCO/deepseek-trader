"""
Maximum Holding Time Enforcement - nof1.ai inspired

Enforces maximum holding time for positions (default: 36 hours).
Automatically closes positions that exceed the time limit regardless of P&L.

This prevents capital from being tied up too long and ensures regular
portfolio turnover.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging


logger = logging.getLogger(__name__)


@dataclass
class HoldingTimeState:
    """State tracking for a position's holding time"""
    symbol: str
    side: str
    entry_time: datetime
    entry_price: float
    max_holding_hours: float
    current_price: float
    current_pnl_percent: float
    last_updated: datetime
    
    def get_holding_time_hours(self) -> float:
        """Get current holding time in hours"""
        elapsed = datetime.now() - self.entry_time
        return elapsed.total_seconds() / 3600
    
    def get_remaining_time_hours(self) -> float:
        """Get remaining time before max holding time"""
        holding_time = self.get_holding_time_hours()
        return max(0.0, self.max_holding_hours - holding_time)
    
    def is_expired(self) -> bool:
        """Check if position has exceeded max holding time"""
        return self.get_holding_time_hours() >= self.max_holding_hours
    
    def get_expiry_time(self) -> datetime:
        """Get the time when position will expire"""
        return self.entry_time + timedelta(hours=self.max_holding_hours)


class MaxHoldingTimeManager:
    """Manages maximum holding time enforcement for all open positions"""
    
    def __init__(self, max_holding_hours: float = 36.0):
        """
        Initialize maximum holding time manager
        
        Args:
            max_holding_hours: Maximum hours a position can be held (default: 36)
        """
        self.max_holding_hours = max_holding_hours
        self.positions: Dict[str, HoldingTimeState] = {}
        
        logger.info(f"Initialized max holding time manager: {max_holding_hours} hours")
    
    def add_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        entry_time: Optional[datetime] = None,
        custom_max_hours: Optional[float] = None
    ):
        """
        Add a new position to track for holding time
        
        Args:
            symbol: Trading symbol
            side: 'long' or 'short'
            entry_price: Entry price
            entry_time: Entry time (default: now)
            custom_max_hours: Custom max holding time (overrides default)
        """
        if entry_time is None:
            entry_time = datetime.now()
        
        max_hours = custom_max_hours if custom_max_hours is not None else self.max_holding_hours
        
        self.positions[symbol] = HoldingTimeState(
            symbol=symbol,
            side=side,
            entry_time=entry_time,
            entry_price=entry_price,
            max_holding_hours=max_hours,
            current_price=entry_price,
            current_pnl_percent=0.0,
            last_updated=datetime.now()
        )
        
        expiry_time = entry_time + timedelta(hours=max_hours)
        logger.info(
            f"Added holding time tracking for {symbol} {side}: "
            f"Entry: {entry_time.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"Max: {max_hours}h, "
            f"Expires: {expiry_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )
    
    def update_position(self, symbol: str, current_price: float) -> Optional[Dict]:
        """
        Update position price and check holding time
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Dict with warning/expiry info if relevant, None otherwise
        """
        if symbol not in self.positions:
            return None
        
        state = self.positions[symbol]
        
        if state.side == 'long':
            pnl_percent = ((current_price - state.entry_price) / state.entry_price) * 100
        else:  # short
            pnl_percent = ((state.entry_price - current_price) / state.entry_price) * 100
        
        state.current_price = current_price
        state.current_pnl_percent = pnl_percent
        state.last_updated = datetime.now()
        
        holding_time = state.get_holding_time_hours()
        remaining_time = state.get_remaining_time_hours()
        
        if state.is_expired():
            logger.warning(
                f"Max holding time exceeded for {symbol}: "
                f"Held for {holding_time:.1f}h (max: {state.max_holding_hours}h), "
                f"P&L: {pnl_percent:.2f}%"
            )
            
            return {
                'symbol': symbol,
                'status': 'expired',
                'holding_time_hours': holding_time,
                'max_holding_hours': state.max_holding_hours,
                'exceeded_by_hours': holding_time - state.max_holding_hours,
                'current_pnl': pnl_percent,
                'entry_time': state.entry_time,
                'expiry_time': state.get_expiry_time(),
            }
        
        elif remaining_time <= 2.0:
            logger.info(
                f"Position {symbol} approaching max holding time: "
                f"{remaining_time:.1f}h remaining "
                f"(held: {holding_time:.1f}h/{state.max_holding_hours}h)"
            )
            
            return {
                'symbol': symbol,
                'status': 'approaching_expiry',
                'holding_time_hours': holding_time,
                'remaining_hours': remaining_time,
                'max_holding_hours': state.max_holding_hours,
                'current_pnl': pnl_percent,
                'expiry_time': state.get_expiry_time(),
            }
        
        return None
    
    def should_close_position(self, symbol: str) -> tuple[bool, Optional[str]]:
        """
        Check if position should be closed due to max holding time
        
        Args:
            symbol: Trading symbol
            
        Returns:
            (should_close, reason)
        """
        if symbol not in self.positions:
            return False, None
        
        state = self.positions[symbol]
        
        if state.is_expired():
            holding_time = state.get_holding_time_hours()
            reason = (
                f"Maximum holding time exceeded: "
                f"Position held for {holding_time:.1f} hours "
                f"(max: {state.max_holding_hours} hours). "
                f"Closing regardless of P&L ({state.current_pnl_percent:.2f}%)"
            )
            return True, reason
        
        return False, None
    
    def get_positions_to_close(self) -> List[str]:
        """
        Get list of symbols that should be closed due to max holding time
        
        Returns:
            List of symbols to close
        """
        return [
            symbol
            for symbol, state in self.positions.items()
            if state.is_expired()
        ]
    
    def get_position_state(self, symbol: str) -> Optional[HoldingTimeState]:
        """Get current holding time state for a position"""
        return self.positions.get(symbol)
    
    def get_holding_time_info(self, symbol: str) -> Optional[Dict]:
        """
        Get detailed holding time information for a position
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict with holding time info or None if position not tracked
        """
        if symbol not in self.positions:
            return None
        
        state = self.positions[symbol]
        holding_time = state.get_holding_time_hours()
        remaining_time = state.get_remaining_time_hours()
        
        return {
            'symbol': symbol,
            'entry_time': state.entry_time,
            'expiry_time': state.get_expiry_time(),
            'holding_time_hours': holding_time,
            'remaining_hours': remaining_time,
            'max_holding_hours': state.max_holding_hours,
            'percent_of_max_used': (holding_time / state.max_holding_hours) * 100,
            'is_expired': state.is_expired(),
            'is_approaching_expiry': remaining_time <= 2.0,
            'current_pnl': state.current_pnl_percent,
        }
    
    def remove_position(self, symbol: str):
        """Remove position from holding time tracking"""
        if symbol in self.positions:
            state = self.positions[symbol]
            holding_time = state.get_holding_time_hours()
            
            logger.info(
                f"Removed holding time tracking for {symbol}: "
                f"Held for {holding_time:.1f}h, "
                f"P&L: {state.current_pnl_percent:.2f}%"
            )
            
            del self.positions[symbol]
    
    def get_all_states(self) -> Dict[str, HoldingTimeState]:
        """Get all tracked position states"""
        return self.positions.copy()
    
    def get_statistics(self) -> Dict:
        """Get holding time statistics"""
        if not self.positions:
            return {
                'total_positions': 0,
                'expired_positions': 0,
                'approaching_expiry': 0,
                'average_holding_time_hours': 0.0,
                'average_remaining_hours': 0.0,
            }
        
        states = list(self.positions.values())
        expired = sum(1 for s in states if s.is_expired())
        approaching = sum(1 for s in states if s.get_remaining_time_hours() <= 2.0 and not s.is_expired())
        
        avg_holding = sum(s.get_holding_time_hours() for s in states) / len(states)
        avg_remaining = sum(s.get_remaining_time_hours() for s in states) / len(states)
        
        return {
            'total_positions': len(states),
            'expired_positions': expired,
            'approaching_expiry': approaching,
            'average_holding_time_hours': avg_holding,
            'average_remaining_hours': avg_remaining,
            'max_holding_hours': self.max_holding_hours,
            'holding_time_distribution': {
                '0-12h': sum(1 for s in states if s.get_holding_time_hours() < 12),
                '12-24h': sum(1 for s in states if 12 <= s.get_holding_time_hours() < 24),
                '24-36h': sum(1 for s in states if 24 <= s.get_holding_time_hours() < 36),
                '36h+': sum(1 for s in states if s.get_holding_time_hours() >= 36),
            }
        }
