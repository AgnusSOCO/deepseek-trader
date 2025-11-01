"""
Partial Take-Profit System - nof1.ai inspired

Implements staged profit-taking at multiple levels to lock in gains
while letting remaining position run for higher profits.

Example (Conservative profile):
- Position reaches +20% profit → Close 50% of position
- Position reaches +30% profit → Close 50% of remaining (75% total closed)
- Position reaches +40% profit → Close 100% (all closed)
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, List
import logging

from src.autonomous.trading_profiles import PartialTakeProfitStage, ProfileConfig


logger = logging.getLogger(__name__)


@dataclass
class TakeProfitExecution:
    """Record of a partial take-profit execution"""
    stage: int
    trigger_profit_pct: float
    close_percent: float
    execution_time: datetime
    price_at_execution: float
    pnl_at_execution: float


@dataclass
class PartialTakeProfitState:
    """State tracking for a position's partial take-profit"""
    symbol: str
    side: str
    entry_price: float
    initial_position_size: float
    current_position_size: float
    current_price: float
    current_pnl_percent: float
    completed_stages: List[TakeProfitExecution]
    next_stage_index: int  # Index of next stage to execute (0, 1, 2, ...)
    last_updated: datetime
    
    def get_remaining_position_percent(self) -> float:
        """Get percentage of original position still open"""
        if self.initial_position_size == 0:
            return 0.0
        return (self.current_position_size / self.initial_position_size) * 100
    
    def is_fully_closed(self) -> bool:
        """Check if position is fully closed"""
        return self.current_position_size <= 0


class PartialTakeProfitManager:
    """Manages partial take-profit for all open positions"""
    
    def __init__(self, profile_config: ProfileConfig):
        """
        Initialize partial take-profit manager
        
        Args:
            profile_config: Trading profile configuration with take-profit stages
        """
        self.profile_config = profile_config
        self.positions: Dict[str, PartialTakeProfitState] = {}
        
    def add_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        position_size: float
    ):
        """
        Add a new position to track for partial take-profit
        
        Args:
            symbol: Trading symbol
            side: 'long' or 'short'
            entry_price: Entry price
            position_size: Initial position size
        """
        self.positions[symbol] = PartialTakeProfitState(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            initial_position_size=position_size,
            current_position_size=position_size,
            current_price=entry_price,
            current_pnl_percent=0.0,
            completed_stages=[],
            next_stage_index=0,
            last_updated=datetime.now()
        )
        
        logger.info(
            f"Added partial take-profit tracking for {symbol} {side} "
            f"at {entry_price}, size: {position_size}"
        )
    
    def update_position(self, symbol: str, current_price: float) -> Optional[Dict]:
        """
        Update position price and check if take-profit stage should be executed
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Dict with execution info if stage triggered, None otherwise
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
        
        execution_info = self._check_take_profit_stages(state)
        
        return execution_info
    
    def _check_take_profit_stages(self, state: PartialTakeProfitState) -> Optional[Dict]:
        """
        Check if current profit triggers next take-profit stage
        
        Args:
            state: Current position state
            
        Returns:
            Dict with execution info if stage triggered, None otherwise
        """
        stages = self.profile_config.partial_take_profit
        
        if state.next_stage_index >= len(stages):
            return None  # All stages completed
        
        next_stage = stages[state.next_stage_index]
        
        if state.current_pnl_percent >= next_stage.trigger_profit_pct:
            size_to_close = state.current_position_size * (next_stage.close_percent / 100)
            
            execution = TakeProfitExecution(
                stage=state.next_stage_index + 1,
                trigger_profit_pct=next_stage.trigger_profit_pct,
                close_percent=next_stage.close_percent,
                execution_time=datetime.now(),
                price_at_execution=state.current_price,
                pnl_at_execution=state.current_pnl_percent
            )
            
            state.completed_stages.append(execution)
            state.current_position_size -= size_to_close
            state.next_stage_index += 1
            
            logger.info(
                f"Partial take-profit executed for {state.symbol}: "
                f"Stage {execution.stage} - Profit {state.current_pnl_percent:.2f}% "
                f"→ Closing {next_stage.close_percent:.0f}% "
                f"(Size: {size_to_close:.4f}, Remaining: {state.current_position_size:.4f})"
            )
            
            return {
                'symbol': state.symbol,
                'stage': execution.stage,
                'trigger_profit': next_stage.trigger_profit_pct,
                'close_percent': next_stage.close_percent,
                'size_to_close': size_to_close,
                'remaining_size': state.current_position_size,
                'remaining_percent': state.get_remaining_position_percent(),
                'current_profit': state.current_pnl_percent,
                'is_fully_closed': state.is_fully_closed()
            }
        
        return None
    
    def should_close_position(self, symbol: str) -> tuple[bool, Optional[float], Optional[str]]:
        """
        Check if position should be closed (partially or fully)
        
        Args:
            symbol: Trading symbol
            
        Returns:
            (should_close, close_percent, reason)
        """
        if symbol not in self.positions:
            return False, None, None
        
        state = self.positions[symbol]
        stages = self.profile_config.partial_take_profit
        
        if state.next_stage_index < len(stages):
            next_stage = stages[state.next_stage_index]
            
            if state.current_pnl_percent >= next_stage.trigger_profit_pct:
                reason = (
                    f"Partial take-profit stage {state.next_stage_index + 1}: "
                    f"Profit {state.current_pnl_percent:.2f}% reached "
                    f"trigger {next_stage.trigger_profit_pct:.2f}%"
                )
                return True, next_stage.close_percent, reason
        
        return False, None, None
    
    def record_partial_close(self, symbol: str, closed_size: float):
        """
        Record that a partial close was executed externally
        
        Args:
            symbol: Trading symbol
            closed_size: Size that was closed
        """
        if symbol not in self.positions:
            return
        
        state = self.positions[symbol]
        state.current_position_size -= closed_size
        
        logger.info(
            f"Recorded partial close for {symbol}: "
            f"Closed {closed_size:.4f}, Remaining {state.current_position_size:.4f}"
        )
    
    def get_position_state(self, symbol: str) -> Optional[PartialTakeProfitState]:
        """Get current partial take-profit state for a position"""
        return self.positions.get(symbol)
    
    def remove_position(self, symbol: str):
        """Remove position from partial take-profit tracking"""
        if symbol in self.positions:
            del self.positions[symbol]
            logger.info(f"Removed partial take-profit tracking for {symbol}")
    
    def get_all_states(self) -> Dict[str, PartialTakeProfitState]:
        """Get all tracked position states"""
        return self.positions.copy()
    
    def get_statistics(self) -> Dict:
        """Get partial take-profit statistics"""
        if not self.positions:
            return {
                'total_positions': 0,
                'positions_with_completed_stages': 0,
                'total_stages_completed': 0,
                'average_remaining_position_percent': 0.0,
            }
        
        states = list(self.positions.values())
        positions_with_stages = sum(1 for s in states if len(s.completed_stages) > 0)
        total_stages = sum(len(s.completed_stages) for s in states)
        avg_remaining = sum(s.get_remaining_position_percent() for s in states) / len(states)
        
        return {
            'total_positions': len(states),
            'positions_with_completed_stages': positions_with_stages,
            'total_stages_completed': total_stages,
            'average_remaining_position_percent': avg_remaining,
            'stage_distribution': {
                f'stage_{i}': sum(1 for s in states if s.next_stage_index == i)
                for i in range(len(self.profile_config.partial_take_profit) + 1)
            }
        }
