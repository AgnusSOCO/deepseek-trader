"""
Trailing Stop-Loss System - nof1.ai inspired

Implements multi-level trailing stops that protect profits as they grow.
Automatically adjusts stop-loss levels based on profit milestones.

Example (Conservative profile):
- Position reaches +6% profit → Move stop-loss to +2%
- Position reaches +12% profit → Move stop-loss to +6%
- Position reaches +20% profit → Move stop-loss to +12%
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict
import logging

from src.autonomous.trading_profiles import TrailingStopLevel, ProfileConfig


logger = logging.getLogger(__name__)


@dataclass
class TrailingStopState:
    """State tracking for a position's trailing stop"""
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    current_price: float
    current_pnl_percent: float
    peak_pnl_percent: float  # Highest profit reached
    current_stop_loss_percent: Optional[float]  # Current stop-loss level (% profit)
    active_level: int  # Which trailing stop level is active (0, 1, 2, 3)
    last_updated: datetime
    
    def should_exit(self) -> bool:
        """Check if current price has hit the trailing stop"""
        if self.current_stop_loss_percent is None:
            return False
        
        return self.current_pnl_percent <= self.current_stop_loss_percent


class TrailingStopManager:
    """Manages trailing stops for all open positions"""
    
    def __init__(self, profile_config: ProfileConfig):
        """
        Initialize trailing stop manager
        
        Args:
            profile_config: Trading profile configuration with trailing stop levels
        """
        self.profile_config = profile_config
        self.trailing_stops: Dict[str, TrailingStopState] = {}
        
    def add_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        initial_stop_loss_percent: Optional[float] = None
    ):
        """
        Add a new position to track with trailing stops
        
        Args:
            symbol: Trading symbol
            side: 'long' or 'short'
            entry_price: Entry price
            initial_stop_loss_percent: Initial stop-loss level (% profit, negative for loss)
        """
        self.trailing_stops[symbol] = TrailingStopState(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            current_price=entry_price,
            current_pnl_percent=0.0,
            peak_pnl_percent=0.0,
            current_stop_loss_percent=initial_stop_loss_percent,
            active_level=0,  # No trailing stop level active yet
            last_updated=datetime.now()
        )
        
        logger.info(f"Added trailing stop tracking for {symbol} {side} at {entry_price}, initial SL: {initial_stop_loss_percent}%")
    
    def update_position(self, symbol: str, current_price: float) -> Optional[Dict]:
        """
        Update position price and check if trailing stop should be adjusted
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Dict with update info if trailing stop was adjusted, None otherwise
        """
        if symbol not in self.trailing_stops:
            return None
        
        state = self.trailing_stops[symbol]
        
        if state.side == 'long':
            pnl_percent = ((current_price - state.entry_price) / state.entry_price) * 100
        else:  # short
            pnl_percent = ((state.entry_price - current_price) / state.entry_price) * 100
        
        state.current_price = current_price
        state.current_pnl_percent = pnl_percent
        state.last_updated = datetime.now()
        
        if pnl_percent > state.peak_pnl_percent:
            state.peak_pnl_percent = pnl_percent
        
        update_info = self._check_trailing_stop_levels(state)
        
        return update_info
    
    def _check_trailing_stop_levels(self, state: TrailingStopState) -> Optional[Dict]:
        """
        Check if current profit triggers a new trailing stop level
        
        Args:
            state: Current position state
            
        Returns:
            Dict with update info if level changed, None otherwise
        """
        levels = self.profile_config.trailing_stops
        
        for i, level in enumerate(reversed(levels), start=1):
            level_index = len(levels) - i + 1
            
            if state.current_pnl_percent >= level.trigger_profit_pct and state.active_level < level_index:
                old_stop = state.current_stop_loss_percent
                state.current_stop_loss_percent = level.stop_at_profit_pct
                state.active_level = level_index
                
                logger.info(
                    f"Trailing stop activated for {state.symbol}: "
                    f"Level {level_index} - Profit {state.current_pnl_percent:.2f}% "
                    f"→ Stop moved to +{level.stop_at_profit_pct:.2f}% "
                    f"(was {old_stop}%)"
                )
                
                return {
                    'symbol': state.symbol,
                    'level': level_index,
                    'trigger_profit': level.trigger_profit_pct,
                    'new_stop': level.stop_at_profit_pct,
                    'old_stop': old_stop,
                    'current_profit': state.current_pnl_percent,
                }
        
        return None
    
    def should_exit_position(self, symbol: str) -> tuple[bool, Optional[str]]:
        """
        Check if position should be exited due to trailing stop
        
        Args:
            symbol: Trading symbol
            
        Returns:
            (should_exit, reason)
        """
        if symbol not in self.trailing_stops:
            return False, None
        
        state = self.trailing_stops[symbol]
        
        if state.should_exit():
            reason = (
                f"Trailing stop hit: Current profit {state.current_pnl_percent:.2f}% "
                f"fell below stop level {state.current_stop_loss_percent:.2f}% "
                f"(Peak profit was {state.peak_pnl_percent:.2f}%)"
            )
            logger.warning(f"Trailing stop exit triggered for {symbol}: {reason}")
            return True, reason
        
        return False, None
    
    def get_position_state(self, symbol: str) -> Optional[TrailingStopState]:
        """Get current trailing stop state for a position"""
        return self.trailing_stops.get(symbol)
    
    def remove_position(self, symbol: str):
        """Remove position from trailing stop tracking"""
        if symbol in self.trailing_stops:
            del self.trailing_stops[symbol]
            logger.info(f"Removed trailing stop tracking for {symbol}")
    
    def get_all_states(self) -> Dict[str, TrailingStopState]:
        """Get all tracked position states"""
        return self.trailing_stops.copy()
    
    def get_statistics(self) -> Dict:
        """Get trailing stop statistics"""
        if not self.trailing_stops:
            return {
                'total_positions': 0,
                'positions_with_active_trailing_stops': 0,
                'average_profit': 0.0,
                'average_peak_profit': 0.0,
            }
        
        states = list(self.trailing_stops.values())
        active_trailing_stops = sum(1 for s in states if s.active_level > 0)
        
        return {
            'total_positions': len(states),
            'positions_with_active_trailing_stops': active_trailing_stops,
            'average_profit': sum(s.current_pnl_percent for s in states) / len(states),
            'average_peak_profit': sum(s.peak_pnl_percent for s in states) / len(states),
            'level_distribution': {
                f'level_{i}': sum(1 for s in states if s.active_level == i)
                for i in range(4)  # 0, 1, 2, 3
            }
        }
