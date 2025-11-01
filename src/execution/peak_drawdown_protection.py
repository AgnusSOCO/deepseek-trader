"""
Peak Drawdown Protection - nof1.ai inspired

Monitors positions for drawdown from peak profit and triggers exits
when profit retraces beyond threshold.

Example (Conservative profile with 25% threshold):
- Position reaches peak profit of +40%
- Current profit drops to +30%
- Drawdown from peak: (40-30)/40 = 25% → EXIT TRIGGERED

This protects profits by exiting when gains start eroding significantly.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import logging

from src.autonomous.trading_profiles import ProfileConfig


logger = logging.getLogger(__name__)


@dataclass
class PeakDrawdownState:
    """State tracking for a position's peak drawdown"""
    symbol: str
    side: str
    entry_price: float
    current_price: float
    current_pnl_percent: float
    peak_pnl_percent: float  # Highest profit ever reached
    peak_pnl_price: float  # Price at peak profit
    peak_pnl_time: datetime  # When peak was reached
    drawdown_threshold: float  # Threshold % for exit
    last_updated: datetime
    
    def calculate_drawdown_from_peak(self) -> float:
        """
        Calculate drawdown percentage from peak profit
        
        Returns:
            Drawdown % (0-100). Returns 0 if no peak profit yet.
        """
        if self.peak_pnl_percent <= 0:
            return 0.0  # No peak profit yet
        
        drawdown = ((self.peak_pnl_percent - self.current_pnl_percent) / self.peak_pnl_percent) * 100
        return max(0.0, drawdown)  # Can't be negative
    
    def should_exit(self) -> bool:
        """Check if drawdown from peak exceeds threshold"""
        drawdown = self.calculate_drawdown_from_peak()
        return drawdown >= self.drawdown_threshold


class PeakDrawdownProtectionManager:
    """Manages peak drawdown protection for all open positions"""
    
    def __init__(self, profile_config: ProfileConfig):
        """
        Initialize peak drawdown protection manager
        
        Args:
            profile_config: Trading profile configuration with drawdown threshold
        """
        self.profile_config = profile_config
        self.positions: Dict[str, PeakDrawdownState] = {}
        
    def add_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        custom_threshold: Optional[float] = None
    ):
        """
        Add a new position to track for peak drawdown protection
        
        Args:
            symbol: Trading symbol
            side: 'long' or 'short'
            entry_price: Entry price
            custom_threshold: Custom drawdown threshold (overrides profile default)
        """
        threshold = custom_threshold if custom_threshold is not None else self.profile_config.peak_drawdown_threshold
        
        self.positions[symbol] = PeakDrawdownState(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            current_price=entry_price,
            current_pnl_percent=0.0,
            peak_pnl_percent=0.0,
            peak_pnl_price=entry_price,
            peak_pnl_time=datetime.now(),
            drawdown_threshold=threshold,
            last_updated=datetime.now()
        )
        
        logger.info(
            f"Added peak drawdown protection for {symbol} {side} "
            f"at {entry_price}, threshold: {threshold:.1f}%"
        )
    
    def update_position(self, symbol: str, current_price: float) -> Optional[Dict]:
        """
        Update position price and check for peak drawdown
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Dict with update info if peak was updated or exit triggered, None otherwise
        """
        if symbol not in self.positions:
            return None
        
        state = self.positions[symbol]
        
        if state.side == 'long':
            pnl_percent = ((current_price - state.entry_price) / state.entry_price) * 100
        else:  # short
            pnl_percent = ((state.entry_price - current_price) / state.entry_price) * 100
        
        old_peak = state.peak_pnl_percent
        state.current_price = current_price
        state.current_pnl_percent = pnl_percent
        state.last_updated = datetime.now()
        
        peak_updated = False
        if pnl_percent > state.peak_pnl_percent:
            state.peak_pnl_percent = pnl_percent
            state.peak_pnl_price = current_price
            state.peak_pnl_time = datetime.now()
            peak_updated = True
            
            logger.info(
                f"New peak profit for {symbol}: {pnl_percent:.2f}% "
                f"(previous: {old_peak:.2f}%)"
            )
        
        drawdown = state.calculate_drawdown_from_peak()
        
        if state.should_exit():
            logger.warning(
                f"Peak drawdown protection triggered for {symbol}: "
                f"Drawdown {drawdown:.2f}% from peak {state.peak_pnl_percent:.2f}% "
                f"(current: {pnl_percent:.2f}%, threshold: {state.drawdown_threshold:.1f}%)"
            )
            
            return {
                'symbol': symbol,
                'action': 'exit_triggered',
                'peak_profit': state.peak_pnl_percent,
                'current_profit': pnl_percent,
                'drawdown_percent': drawdown,
                'threshold': state.drawdown_threshold,
                'peak_price': state.peak_pnl_price,
                'current_price': current_price,
            }
        
        if peak_updated:
            return {
                'symbol': symbol,
                'action': 'peak_updated',
                'new_peak': pnl_percent,
                'old_peak': old_peak,
                'peak_price': current_price,
            }
        
        return None
    
    def should_exit_position(self, symbol: str) -> tuple[bool, Optional[str]]:
        """
        Check if position should be exited due to peak drawdown
        
        Args:
            symbol: Trading symbol
            
        Returns:
            (should_exit, reason)
        """
        if symbol not in self.positions:
            return False, None
        
        state = self.positions[symbol]
        
        if state.should_exit():
            drawdown = state.calculate_drawdown_from_peak()
            reason = (
                f"Peak drawdown protection: Profit retraced {drawdown:.2f}% "
                f"from peak {state.peak_pnl_percent:.2f}% "
                f"(current: {state.current_pnl_percent:.2f}%, "
                f"threshold: {state.drawdown_threshold:.1f}%)"
            )
            return True, reason
        
        return False, None
    
    def get_position_state(self, symbol: str) -> Optional[PeakDrawdownState]:
        """Get current peak drawdown state for a position"""
        return self.positions.get(symbol)
    
    def get_drawdown_info(self, symbol: str) -> Optional[Dict]:
        """
        Get detailed drawdown information for a position
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Dict with drawdown info or None if position not tracked
        """
        if symbol not in self.positions:
            return None
        
        state = self.positions[symbol]
        drawdown = state.calculate_drawdown_from_peak()
        
        return {
            'symbol': symbol,
            'current_profit': state.current_pnl_percent,
            'peak_profit': state.peak_pnl_percent,
            'drawdown_from_peak': drawdown,
            'threshold': state.drawdown_threshold,
            'distance_to_threshold': state.drawdown_threshold - drawdown,
            'is_at_risk': drawdown >= (state.drawdown_threshold * 0.8),  # 80% of threshold
            'peak_time': state.peak_pnl_time,
            'time_since_peak': (datetime.now() - state.peak_pnl_time).total_seconds() / 60,  # minutes
        }
    
    def remove_position(self, symbol: str):
        """Remove position from peak drawdown tracking"""
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"Removed peak drawdown protection for {symbol}")
    
    def get_all_states(self) -> Dict[str, PeakDrawdownState]:
        """Get all tracked position states"""
        return self.positions.copy()
    
    def get_statistics(self) -> Dict:
        """Get peak drawdown protection statistics"""
        if not self.positions:
            return {
                'total_positions': 0,
                'positions_with_peak_profit': 0,
                'positions_at_risk': 0,
                'average_peak_profit': 0.0,
                'average_current_profit': 0.0,
                'average_drawdown': 0.0,
            }
        
        states = list(self.positions.values())
        positions_with_peak = sum(1 for s in states if s.peak_pnl_percent > 0)
        positions_at_risk = sum(
            1 for s in states 
            if s.calculate_drawdown_from_peak() >= (s.drawdown_threshold * 0.8)
        )
        
        avg_peak = sum(s.peak_pnl_percent for s in states) / len(states)
        avg_current = sum(s.current_pnl_percent for s in states) / len(states)
        avg_drawdown = sum(s.calculate_drawdown_from_peak() for s in states) / len(states)
        
        return {
            'total_positions': len(states),
            'positions_with_peak_profit': positions_with_peak,
            'positions_at_risk': positions_at_risk,
            'average_peak_profit': avg_peak,
            'average_current_profit': avg_current,
            'average_drawdown': avg_drawdown,
        }
