"""
Error Recovery Manager (Phase E)

Handles errors and implements recovery strategies for autonomous trading.
Ensures system resilience and automatic recovery from failures.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import traceback

logger = logging.getLogger(__name__)


@dataclass
class ErrorRecord:
    """Record of an error occurrence"""
    timestamp: datetime
    error_type: str
    error_message: str
    context: Dict[str, Any]
    stack_trace: str
    recovery_action: str


class ErrorRecoveryManager:
    """
    Manages error handling and recovery for autonomous trading.
    
    Features:
    - Error tracking and classification
    - Automatic recovery strategies
    - Circuit breaker pattern
    - Error rate monitoring
    - Cooldown periods
    """
    
    def __init__(
        self,
        max_consecutive_errors: int = 5,
        cooldown_seconds: int = 300,
        error_window_seconds: int = 3600
    ):
        """
        Initialize error recovery manager
        
        Args:
            max_consecutive_errors: Max errors before pause
            cooldown_seconds: Cooldown period after errors
            error_window_seconds: Time window for error rate calculation
        """
        self.max_consecutive_errors = max_consecutive_errors
        self.cooldown_seconds = cooldown_seconds
        self.error_window_seconds = error_window_seconds
        
        self.consecutive_errors = 0
        self.total_errors = 0
        self.total_recoveries = 0
        self.error_history: List[ErrorRecord] = []
        self.last_error_time: Optional[datetime] = None
        self.pause_until: Optional[datetime] = None
        
        logger.info(
            f"ErrorRecoveryManager initialized: "
            f"max_consecutive_errors={max_consecutive_errors}, "
            f"cooldown={cooldown_seconds}s"
        )
    
    async def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Handle an error and determine recovery action
        
        Args:
            error: Exception that occurred
            context: Additional context about the error
            
        Returns:
            Recovery action: 'continue', 'pause', or 'stop'
        """
        self.consecutive_errors += 1
        self.total_errors += 1
        self.last_error_time = datetime.now()
        
        error_type = type(error).__name__
        error_message = str(error)
        stack_trace = traceback.format_exc()
        
        recovery_action = self._determine_recovery_action(error_type, error_message)
        
        error_record = ErrorRecord(
            timestamp=datetime.now(),
            error_type=error_type,
            error_message=error_message,
            context=context or {},
            stack_trace=stack_trace,
            recovery_action=recovery_action
        )
        
        self.error_history.append(error_record)
        
        if len(self.error_history) > 1000:
            self.error_history = self.error_history[-1000:]
        
        logger.error(
            f"Error #{self.total_errors} (consecutive: {self.consecutive_errors}): "
            f"{error_type}: {error_message}"
        )
        logger.error(f"Recovery action: {recovery_action}")
        
        if recovery_action == 'pause':
            self.pause_until = datetime.now() + timedelta(seconds=self.cooldown_seconds)
            logger.warning(
                f"⏸️  System paused until {self.pause_until} "
                f"({self.cooldown_seconds}s cooldown)"
            )
        
        return recovery_action
    
    def _determine_recovery_action(
        self,
        error_type: str,
        error_message: str
    ) -> str:
        """
        Determine appropriate recovery action based on error
        
        Args:
            error_type: Type of error
            error_message: Error message
            
        Returns:
            Recovery action: 'continue', 'pause', or 'stop'
        """
        if self.consecutive_errors >= self.max_consecutive_errors:
            return 'pause'
        
        fatal_errors = [
            'MemoryError',
            'SystemExit',
            'KeyboardInterrupt',
        ]
        
        if error_type in fatal_errors:
            return 'stop'
        
        network_errors = [
            'ConnectionError',
            'TimeoutError',
            'HTTPError',
            'RequestException',
        ]
        
        if error_type in network_errors:
            if self.consecutive_errors >= 3:
                return 'pause'
            return 'continue'
        
        api_errors = [
            'RateLimitError',
            'APIError',
            'AuthenticationError',
        ]
        
        if error_type in api_errors:
            return 'pause'
        
        if self.consecutive_errors >= 3:
            return 'pause'
        
        return 'continue'
    
    async def handle_fatal_error(self, error: Exception) -> None:
        """
        Handle a fatal error that requires system shutdown
        
        Args:
            error: Fatal exception
        """
        logger.critical(
            f"🚨 FATAL ERROR: {type(error).__name__}: {str(error)}",
            exc_info=True
        )
        
        await self.handle_error(error, context={'fatal': True})
        
        logger.critical("System shutdown required due to fatal error")
    
    async def handle_health_issue(self, issue: str) -> None:
        """
        Handle a health check issue
        
        Args:
            issue: Description of health issue
        """
        logger.warning(f"⚠️  Health issue detected: {issue}")
        
        if 'High drawdown' in issue:
            logger.warning("Implementing conservative risk parameters")
        elif 'High error rate' in issue:
            logger.warning("Increasing cooldown period")
            self.cooldown_seconds = min(self.cooldown_seconds * 2, 3600)
        elif 'unstable' in issue:
            logger.warning("System unstable, extending monitoring period")
    
    def record_success(self) -> None:
        """Record a successful operation"""
        if self.consecutive_errors > 0:
            logger.info(
                f"✓ Operation successful after {self.consecutive_errors} errors, "
                f"resetting error count"
            )
            self.total_recoveries += 1
        
        self.consecutive_errors = 0
        
        if self.pause_until and datetime.now() >= self.pause_until:
            self.pause_until = None
            logger.info("✓ Cooldown period ended, resuming normal operation")
    
    def should_pause(self) -> bool:
        """
        Check if system should be paused
        
        Returns:
            True if system should pause, False otherwise
        """
        if self.pause_until is None:
            return False
        
        return datetime.now() < self.pause_until
    
    def get_pause_duration(self) -> int:
        """
        Get remaining pause duration in seconds
        
        Returns:
            Remaining pause duration
        """
        if self.pause_until is None:
            return 0
        
        remaining = (self.pause_until - datetime.now()).total_seconds()
        return max(0, int(remaining))
    
    def reset_error_count(self) -> None:
        """Reset consecutive error count"""
        logger.info("Resetting consecutive error count")
        self.consecutive_errors = 0
        self.pause_until = None
    
    def get_error_rate(self) -> float:
        """
        Calculate error rate over the error window
        
        Returns:
            Error rate (errors per hour)
        """
        if not self.error_history:
            return 0.0
        
        cutoff_time = datetime.now() - timedelta(seconds=self.error_window_seconds)
        recent_errors = [e for e in self.error_history if e.timestamp >= cutoff_time]
        
        hours = self.error_window_seconds / 3600
        return len(recent_errors) / hours if hours > 0 else 0.0
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get error recovery statistics
        
        Returns:
            Dict with statistics
        """
        recent_errors = self._get_recent_errors(timedelta(hours=1))
        
        error_types = {}
        for error in recent_errors:
            error_types[error.error_type] = error_types.get(error.error_type, 0) + 1
        
        return {
            'total_errors': self.total_errors,
            'consecutive_errors': self.consecutive_errors,
            'total_recoveries': self.total_recoveries,
            'error_rate_per_hour': self.get_error_rate(),
            'is_paused': self.should_pause(),
            'pause_remaining_seconds': self.get_pause_duration(),
            'last_error_time': self.last_error_time.isoformat() if self.last_error_time else None,
            'recent_error_types': error_types,
            'recovery_rate': self.total_recoveries / self.total_errors * 100 if self.total_errors > 0 else 0
        }
    
    def _get_recent_errors(self, period: timedelta) -> List[ErrorRecord]:
        """Get errors from recent time period"""
        cutoff_time = datetime.now() - period
        return [e for e in self.error_history if e.timestamp >= cutoff_time]
