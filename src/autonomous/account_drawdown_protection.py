"""
Account-Level Drawdown Protection - nof1.ai inspired

Implements 3-tier account-level drawdown protection:
1. Warning Level (20% drawdown): Risk alert, log warning
2. No New Positions (30% drawdown): Stop opening new positions, only allow closes
3. Force Close All (50% drawdown): Emergency liquidation of all positions

Tracks account equity peak and current equity to calculate drawdown.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum
import logging


logger = logging.getLogger(__name__)


class DrawdownLevel(str, Enum):
    """Account drawdown protection levels"""
    NORMAL = "normal"  # No drawdown concerns
    WARNING = "warning"  # 20% drawdown - warning issued
    NO_NEW_POSITIONS = "no_new_positions"  # 30% drawdown - stop new positions
    FORCE_CLOSE = "force_close"  # 50% drawdown - force close all


@dataclass
class DrawdownEvent:
    """Record of a drawdown event"""
    timestamp: datetime
    level: DrawdownLevel
    peak_equity: float
    current_equity: float
    drawdown_percent: float
    action_taken: str


@dataclass
class AccountDrawdownState:
    """Current state of account drawdown protection"""
    peak_equity: float
    peak_equity_time: datetime
    current_equity: float
    current_drawdown_percent: float
    current_level: DrawdownLevel
    warning_threshold: float  # Default: 20%
    no_new_positions_threshold: float  # Default: 30%
    force_close_threshold: float  # Default: 50%
    events: List[DrawdownEvent]
    last_updated: datetime
    
    def calculate_drawdown(self) -> float:
        """
        Calculate current drawdown percentage from peak
        
        Returns:
            Drawdown % (0-100)
        """
        if self.peak_equity <= 0:
            return 0.0
        
        drawdown = ((self.peak_equity - self.current_equity) / self.peak_equity) * 100
        return max(0.0, drawdown)
    
    def determine_level(self) -> DrawdownLevel:
        """Determine current drawdown protection level"""
        drawdown = self.calculate_drawdown()
        
        if drawdown >= self.force_close_threshold:
            return DrawdownLevel.FORCE_CLOSE
        elif drawdown >= self.no_new_positions_threshold:
            return DrawdownLevel.NO_NEW_POSITIONS
        elif drawdown >= self.warning_threshold:
            return DrawdownLevel.WARNING
        else:
            return DrawdownLevel.NORMAL


class AccountDrawdownProtectionManager:
    """Manages account-level drawdown protection"""
    
    def __init__(
        self,
        initial_equity: float,
        warning_threshold: float = 20.0,
        no_new_positions_threshold: float = 30.0,
        force_close_threshold: float = 50.0
    ):
        """
        Initialize account drawdown protection manager
        
        Args:
            initial_equity: Starting account equity
            warning_threshold: Drawdown % for warning level (default: 20%)
            no_new_positions_threshold: Drawdown % to stop new positions (default: 30%)
            force_close_threshold: Drawdown % to force close all (default: 50%)
        """
        self.state = AccountDrawdownState(
            peak_equity=initial_equity,
            peak_equity_time=datetime.now(),
            current_equity=initial_equity,
            current_drawdown_percent=0.0,
            current_level=DrawdownLevel.NORMAL,
            warning_threshold=warning_threshold,
            no_new_positions_threshold=no_new_positions_threshold,
            force_close_threshold=force_close_threshold,
            events=[],
            last_updated=datetime.now()
        )
        
        logger.info(
            f"Initialized account drawdown protection: "
            f"Initial equity: ${initial_equity:.2f}, "
            f"Thresholds: {warning_threshold}%/{no_new_positions_threshold}%/{force_close_threshold}%"
        )
    
    def update_equity(self, current_equity: float) -> Optional[DrawdownEvent]:
        """
        Update current account equity and check drawdown levels
        
        Args:
            current_equity: Current account equity
            
        Returns:
            DrawdownEvent if level changed, None otherwise
        """
        old_level = self.state.current_level
        
        self.state.current_equity = current_equity
        self.state.last_updated = datetime.now()
        
        if current_equity > self.state.peak_equity:
            old_peak = self.state.peak_equity
            self.state.peak_equity = current_equity
            self.state.peak_equity_time = datetime.now()
            
            logger.info(
                f"New account equity peak: ${current_equity:.2f} "
                f"(previous: ${old_peak:.2f})"
            )
        
        self.state.current_drawdown_percent = self.state.calculate_drawdown()
        new_level = self.state.determine_level()
        self.state.current_level = new_level
        
        if new_level != old_level:
            event = self._handle_level_change(old_level, new_level)
            return event
        
        return None
    
    def _handle_level_change(
        self,
        old_level: DrawdownLevel,
        new_level: DrawdownLevel
    ) -> DrawdownEvent:
        """
        Handle drawdown level change
        
        Args:
            old_level: Previous drawdown level
            new_level: New drawdown level
            
        Returns:
            DrawdownEvent recording the change
        """
        if new_level == DrawdownLevel.WARNING:
            action = "Risk warning issued - monitor account closely"
            log_level = logging.WARNING
        elif new_level == DrawdownLevel.NO_NEW_POSITIONS:
            action = "New positions blocked - only position closes allowed"
            log_level = logging.ERROR
        elif new_level == DrawdownLevel.FORCE_CLOSE:
            action = "FORCE CLOSE ALL POSITIONS - Emergency protection activated"
            log_level = logging.CRITICAL
        else:  # NORMAL
            action = "Drawdown level returned to normal"
            log_level = logging.INFO
        
        event = DrawdownEvent(
            timestamp=datetime.now(),
            level=new_level,
            peak_equity=self.state.peak_equity,
            current_equity=self.state.current_equity,
            drawdown_percent=self.state.current_drawdown_percent,
            action_taken=action
        )
        
        self.state.events.append(event)
        
        logger.log(
            log_level,
            f"Account drawdown level changed: {old_level.value} → {new_level.value} | "
            f"Drawdown: {self.state.current_drawdown_percent:.2f}% | "
            f"Peak: ${self.state.peak_equity:.2f} → Current: ${self.state.current_equity:.2f} | "
            f"Action: {action}"
        )
        
        return event
    
    def can_open_new_position(self) -> tuple[bool, Optional[str]]:
        """
        Check if new positions can be opened
        
        Returns:
            (can_open, reason_if_blocked)
        """
        if self.state.current_level == DrawdownLevel.NORMAL:
            return True, None
        elif self.state.current_level == DrawdownLevel.WARNING:
            return True, f"Warning: Account drawdown at {self.state.current_drawdown_percent:.2f}%"
        elif self.state.current_level == DrawdownLevel.NO_NEW_POSITIONS:
            reason = (
                f"New positions blocked: Account drawdown {self.state.current_drawdown_percent:.2f}% "
                f"exceeds threshold {self.state.no_new_positions_threshold:.1f}%"
            )
            return False, reason
        else:  # FORCE_CLOSE
            reason = (
                f"EMERGENCY: Account drawdown {self.state.current_drawdown_percent:.2f}% "
                f"exceeds critical threshold {self.state.force_close_threshold:.1f}% - "
                f"All positions must be closed immediately"
            )
            return False, reason
    
    def should_force_close_all(self) -> tuple[bool, Optional[str]]:
        """
        Check if all positions should be force closed
        
        Returns:
            (should_close, reason)
        """
        if self.state.current_level == DrawdownLevel.FORCE_CLOSE:
            reason = (
                f"FORCE CLOSE ALL: Account drawdown {self.state.current_drawdown_percent:.2f}% "
                f"reached critical threshold {self.state.force_close_threshold:.1f}% | "
                f"Peak equity: ${self.state.peak_equity:.2f} → "
                f"Current equity: ${self.state.current_equity:.2f}"
            )
            return True, reason
        
        return False, None
    
    def get_current_state(self) -> AccountDrawdownState:
        """Get current drawdown state"""
        return self.state
    
    def get_drawdown_info(self) -> dict:
        """
        Get detailed drawdown information
        
        Returns:
            Dict with drawdown details
        """
        return {
            'peak_equity': self.state.peak_equity,
            'current_equity': self.state.current_equity,
            'drawdown_percent': self.state.current_drawdown_percent,
            'current_level': self.state.current_level.value,
            'can_open_new_positions': self.can_open_new_position()[0],
            'should_force_close': self.should_force_close_all()[0],
            'distance_to_warning': self.state.warning_threshold - self.state.current_drawdown_percent,
            'distance_to_no_new': self.state.no_new_positions_threshold - self.state.current_drawdown_percent,
            'distance_to_force_close': self.state.force_close_threshold - self.state.current_drawdown_percent,
            'time_since_peak': (datetime.now() - self.state.peak_equity_time).total_seconds() / 3600,  # hours
            'total_events': len(self.state.events),
        }
    
    def get_recent_events(self, limit: int = 10) -> List[DrawdownEvent]:
        """
        Get recent drawdown events
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of recent DrawdownEvent objects
        """
        return self.state.events[-limit:]
    
    def reset_to_current_equity(self):
        """
        Reset peak equity to current equity
        
        Use this to reset drawdown tracking after recovering from a drawdown
        or when starting a new trading period.
        """
        old_peak = self.state.peak_equity
        self.state.peak_equity = self.state.current_equity
        self.state.peak_equity_time = datetime.now()
        self.state.current_drawdown_percent = 0.0
        self.state.current_level = DrawdownLevel.NORMAL
        
        logger.info(
            f"Reset account drawdown protection: "
            f"Peak equity reset from ${old_peak:.2f} to ${self.state.current_equity:.2f}"
        )
    
    def get_statistics(self) -> dict:
        """Get account drawdown protection statistics"""
        if not self.state.events:
            return {
                'total_events': 0,
                'warning_events': 0,
                'no_new_positions_events': 0,
                'force_close_events': 0,
                'current_level': self.state.current_level.value,
                'current_drawdown': self.state.current_drawdown_percent,
            }
        
        events = self.state.events
        
        return {
            'total_events': len(events),
            'warning_events': sum(1 for e in events if e.level == DrawdownLevel.WARNING),
            'no_new_positions_events': sum(1 for e in events if e.level == DrawdownLevel.NO_NEW_POSITIONS),
            'force_close_events': sum(1 for e in events if e.level == DrawdownLevel.FORCE_CLOSE),
            'current_level': self.state.current_level.value,
            'current_drawdown': self.state.current_drawdown_percent,
            'peak_equity': self.state.peak_equity,
            'current_equity': self.state.current_equity,
        }
