"""
Exit Plan Monitor

Monitors open positions and enforces exit plans including:
- Stop-loss levels
- Take-profit targets
- Invalidation conditions (specific signals that void the trading plan)
- Trailing stops

This is a critical component for zero human interaction trading.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExitReason(Enum):
    """Reasons for exiting a position"""
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    INVALIDATION = "INVALIDATION"
    TRAILING_STOP = "TRAILING_STOP"
    MANUAL = "MANUAL"
    TIMEOUT = "TIMEOUT"


@dataclass
class ExitPlan:
    """
    Exit plan for an open position
    
    Attributes:
        position_id: Unique identifier for the position
        symbol: Trading pair symbol
        entry_price: Entry price of the position
        stop_loss: Stop-loss price (exit if price drops below)
        take_profit: Take-profit price (exit if price rises above)
        invalidation_conditions: List of conditions that void the plan
        trailing_stop_pct: Trailing stop percentage (optional)
        trailing_offset_pct: Trailing stop offset percentage (optional)
        highest_price: Highest price seen since entry (for trailing stop)
        lowest_price: Lowest price seen since entry (for trailing stop shorts)
        is_short: Whether this is a short position
        created_at: When the exit plan was created
        metadata: Additional information
        leverage: Position leverage (for leverage-adjusted P&L)
        peak_pnl_pct: Peak P&L percentage seen (leverage-adjusted)
        tiered_trailing_enabled: Whether to use tiered trailing stop-profit
    """
    position_id: str
    symbol: str
    entry_price: float
    stop_loss: float
    take_profit: float
    invalidation_conditions: List[str]
    trailing_stop_pct: Optional[float] = None
    trailing_offset_pct: Optional[float] = None
    highest_price: Optional[float] = None
    lowest_price: Optional[float] = None
    is_short: bool = False
    created_at: datetime = None
    metadata: Dict[str, Any] = None
    leverage: float = 1.0
    peak_pnl_pct: float = 0.0
    tiered_trailing_enabled: bool = True
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}
        if self.highest_price is None:
            self.highest_price = self.entry_price
        if self.lowest_price is None:
            self.lowest_price = self.entry_price


class ExitPlanMonitor:
    """
    Monitors exit plans for all open positions and determines when to exit.
    
    This class is responsible for:
    1. Tracking stop-loss and take-profit levels
    2. Monitoring invalidation conditions
    3. Managing trailing stops
    4. Providing exit signals when conditions are met
    """
    
    def __init__(self, max_holding_hours: float = 36.0):
        """
        Initialize the exit plan monitor
        
        Args:
            max_holding_hours: Maximum hours to hold a position (default: 36)
        """
        self.exit_plans: Dict[str, ExitPlan] = {}
        self.exit_history: List[Dict[str, Any]] = []
        self.max_holding_hours = max_holding_hours
        
        logger.info(f"ExitPlanMonitor initialized: max_holding_hours={max_holding_hours}")
    
    def add_exit_plan(self, exit_plan: ExitPlan) -> None:
        """
        Add an exit plan for a position
        
        Args:
            exit_plan: ExitPlan object with stop-loss, take-profit, etc.
        """
        self.exit_plans[exit_plan.position_id] = exit_plan
        
        logger.info(
            f"Added exit plan for {exit_plan.symbol} position {exit_plan.position_id}: "
            f"SL=${exit_plan.stop_loss:.2f}, TP=${exit_plan.take_profit:.2f}, "
            f"Invalidations={len(exit_plan.invalidation_conditions)}"
        )
    
    def remove_exit_plan(self, position_id: str) -> None:
        """
        Remove an exit plan (position closed)
        
        Args:
            position_id: Position identifier
        """
        if position_id in self.exit_plans:
            del self.exit_plans[position_id]
            logger.info(f"Removed exit plan for position {position_id}")
    
    def check_tiered_trailing_profit(
        self,
        position_id: str,
        current_price: float
    ) -> Optional[Dict[str, Any]]:
        """
        Check tiered trailing stop-profit logic (nof1-style)
        
        Implements tiered rules:
        - pnl >= +8%: Move stop to +3%
        - pnl >= +15%: Move stop to +8%
        - pnl >= +25%: Move stop to +15%
        - Peak pullback > 30%: Immediate close
        
        Args:
            position_id: Position identifier
            current_price: Current market price
            
        Returns:
            Dict with exit signal if pullback threshold exceeded, None otherwise
        """
        if position_id not in self.exit_plans:
            return None
        
        plan = self.exit_plans[position_id]
        
        if not plan.tiered_trailing_enabled:
            return None
        
        if not plan.is_short:
            price_change_pct = (current_price - plan.entry_price) / plan.entry_price * 100
        else:
            price_change_pct = (plan.entry_price - current_price) / plan.entry_price * 100
        
        pnl_pct = price_change_pct * plan.leverage
        
        if pnl_pct > plan.peak_pnl_pct:
            plan.peak_pnl_pct = pnl_pct
        
        if plan.peak_pnl_pct >= 25.0:
            new_stop_pct = 15.0
            if not plan.is_short:
                new_stop_price = plan.entry_price * (1 + new_stop_pct / 100.0)
                if new_stop_price > plan.stop_loss:
                    old_stop = plan.stop_loss
                    plan.stop_loss = new_stop_price
                    logger.info(
                        f"Tiered trailing: {plan.symbol} {position_id} peak={plan.peak_pnl_pct:.2f}% >= 25%, "
                        f"moved stop to +15% (${old_stop:.2f} -> ${new_stop_price:.2f})"
                    )
            else:
                new_stop_price = plan.entry_price * (1 - new_stop_pct / 100.0)
                if new_stop_price < plan.stop_loss:
                    plan.stop_loss = new_stop_price
        elif plan.peak_pnl_pct >= 15.0:
            new_stop_pct = 8.0
            if not plan.is_short:
                new_stop_price = plan.entry_price * (1 + new_stop_pct / 100.0)
                if new_stop_price > plan.stop_loss:
                    old_stop = plan.stop_loss
                    plan.stop_loss = new_stop_price
                    logger.info(
                        f"Tiered trailing: {plan.symbol} {position_id} peak={plan.peak_pnl_pct:.2f}% >= 15%, "
                        f"moved stop to +8% (${old_stop:.2f} -> ${new_stop_price:.2f})"
                    )
            else:
                new_stop_price = plan.entry_price * (1 - new_stop_pct / 100.0)
                if new_stop_price < plan.stop_loss:
                    plan.stop_loss = new_stop_price
        elif plan.peak_pnl_pct >= 8.0:
            new_stop_pct = 3.0
            if not plan.is_short:
                new_stop_price = plan.entry_price * (1 + new_stop_pct / 100.0)
                if new_stop_price > plan.stop_loss:
                    old_stop = plan.stop_loss
                    plan.stop_loss = new_stop_price
                    logger.info(
                        f"Tiered trailing: {plan.symbol} {position_id} peak={plan.peak_pnl_pct:.2f}% >= 8%, "
                        f"moved stop to +3% (${old_stop:.2f} -> ${new_stop_price:.2f})"
                    )
            else:
                new_stop_price = plan.entry_price * (1 - new_stop_pct / 100.0)
                if new_stop_price < plan.stop_loss:
                    plan.stop_loss = new_stop_price
        
        if plan.peak_pnl_pct > 0:
            pullback_pct = ((plan.peak_pnl_pct - pnl_pct) / plan.peak_pnl_pct) * 100
            
            if pullback_pct > 30.0:
                return {
                    'should_exit': True,
                    'reason': ExitReason.TRAILING_STOP,
                    'price': current_price,
                    'details': f"Peak pullback exceeded 30%: peak={plan.peak_pnl_pct:.2f}%, current={pnl_pct:.2f}%, pullback={pullback_pct:.2f}%"
                }
        
        return None
    
    def update_trailing_stop(
        self,
        position_id: str,
        current_price: float
    ) -> None:
        """
        Update trailing stop levels based on current price
        
        Args:
            position_id: Position identifier
            current_price: Current market price
        """
        if position_id not in self.exit_plans:
            return
        
        plan = self.exit_plans[position_id]
        
        if plan.trailing_stop_pct is None:
            return
        
        if not plan.is_short:
            if current_price > plan.highest_price:
                plan.highest_price = current_price
                
                if plan.trailing_offset_pct:
                    profit_pct = (current_price - plan.entry_price) / plan.entry_price
                    if profit_pct >= plan.trailing_offset_pct:
                        new_stop = plan.highest_price * (1 - plan.trailing_stop_pct)
                        if new_stop > plan.stop_loss:
                            old_stop = plan.stop_loss
                            plan.stop_loss = new_stop
                            logger.info(
                                f"Updated trailing stop for {plan.symbol} {position_id}: "
                                f"${old_stop:.2f} -> ${new_stop:.2f} "
                                f"(highest: ${plan.highest_price:.2f})"
                            )
                else:
                    new_stop = plan.highest_price * (1 - plan.trailing_stop_pct)
                    if new_stop > plan.stop_loss:
                        plan.stop_loss = new_stop
        else:
            if current_price < plan.lowest_price:
                plan.lowest_price = current_price
                
                if plan.trailing_offset_pct:
                    profit_pct = (plan.entry_price - current_price) / plan.entry_price
                    if profit_pct >= plan.trailing_offset_pct:
                        new_stop = plan.lowest_price * (1 + plan.trailing_stop_pct)
                        if new_stop < plan.stop_loss:
                            plan.stop_loss = new_stop
                else:
                    new_stop = plan.lowest_price * (1 + plan.trailing_stop_pct)
                    if new_stop < plan.stop_loss:
                        plan.stop_loss = new_stop
    
    def check_exit_conditions(
        self,
        position_id: str,
        current_price: float,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Check if any exit conditions are met for a position
        
        Args:
            position_id: Position identifier
            current_price: Current market price
            market_data: Current market data
            indicators: Current technical indicators
            
        Returns:
            Dict with exit signal if conditions met, None otherwise
            Format: {
                'should_exit': bool,
                'reason': ExitReason,
                'price': float,
                'details': str
            }
        """
        if position_id not in self.exit_plans:
            return None
        
        plan = self.exit_plans[position_id]
        
        holding_hours = (datetime.now() - plan.created_at).total_seconds() / 3600
        if holding_hours >= self.max_holding_hours:
            if not plan.is_short:
                pnl_pct = (current_price - plan.entry_price) / plan.entry_price * 100
            else:
                pnl_pct = (plan.entry_price - current_price) / plan.entry_price * 100
            
            return {
                'should_exit': True,
                'reason': ExitReason.TIMEOUT,
                'price': current_price,
                'details': f"Max holding time exceeded: {holding_hours:.1f}h >= {self.max_holding_hours}h, P&L: {pnl_pct:.2f}%"
            }
        
        if holding_hours >= (self.max_holding_hours - 2):
            logger.warning(
                f"⚠️  Position {position_id} approaching max holding time: "
                f"{holding_hours:.1f}h / {self.max_holding_hours}h"
            )
        
        tiered_exit = self.check_tiered_trailing_profit(position_id, current_price)
        if tiered_exit:
            return tiered_exit
        
        self.update_trailing_stop(position_id, current_price)
        
        if not plan.is_short:
            if current_price <= plan.stop_loss:
                loss_pct = (current_price - plan.entry_price) / plan.entry_price * 100
                return {
                    'should_exit': True,
                    'reason': ExitReason.STOP_LOSS,
                    'price': current_price,
                    'details': f"Stop-loss triggered at ${current_price:.2f} (${plan.stop_loss:.2f}), loss: {loss_pct:.2f}%"
                }
            
            if current_price >= plan.take_profit:
                profit_pct = (current_price - plan.entry_price) / plan.entry_price * 100
                return {
                    'should_exit': True,
                    'reason': ExitReason.TAKE_PROFIT,
                    'price': current_price,
                    'details': f"Take-profit triggered at ${current_price:.2f} (${plan.take_profit:.2f}), profit: {profit_pct:.2f}%"
                }
        else:
            if current_price >= plan.stop_loss:
                loss_pct = (plan.entry_price - current_price) / plan.entry_price * 100
                return {
                    'should_exit': True,
                    'reason': ExitReason.STOP_LOSS,
                    'price': current_price,
                    'details': f"Stop-loss triggered at ${current_price:.2f} (${plan.stop_loss:.2f}), loss: {loss_pct:.2f}%"
                }
            
            if current_price <= plan.take_profit:
                profit_pct = (plan.entry_price - current_price) / plan.entry_price * 100
                return {
                    'should_exit': True,
                    'reason': ExitReason.TAKE_PROFIT,
                    'price': current_price,
                    'details': f"Take-profit triggered at ${current_price:.2f} (${plan.take_profit:.2f}), profit: {profit_pct:.2f}%"
                }
        
        
        return None
    
    def get_exit_plan(self, position_id: str) -> Optional[ExitPlan]:
        """
        Get exit plan for a position
        
        Args:
            position_id: Position identifier
            
        Returns:
            ExitPlan if exists, None otherwise
        """
        return self.exit_plans.get(position_id)
    
    def get_all_exit_plans(self) -> Dict[str, ExitPlan]:
        """Get all active exit plans"""
        return self.exit_plans.copy()
    
    def record_exit(
        self,
        position_id: str,
        exit_reason: ExitReason,
        exit_price: float,
        profit_loss: float,
        details: str
    ) -> None:
        """
        Record an exit in history
        
        Args:
            position_id: Position identifier
            exit_reason: Reason for exit
            exit_price: Exit price
            profit_loss: Profit/loss amount
            details: Additional details
        """
        exit_record = {
            'position_id': position_id,
            'exit_reason': exit_reason.value,
            'exit_price': exit_price,
            'profit_loss': profit_loss,
            'details': details,
            'timestamp': datetime.now()
        }
        
        self.exit_history.append(exit_record)
        
        if len(self.exit_history) > 1000:
            self.exit_history = self.exit_history[-1000:]
        
        logger.info(
            f"Recorded exit for position {position_id}: "
            f"{exit_reason.value} at ${exit_price:.2f}, P&L: ${profit_loss:.2f}"
        )
    
    def get_exit_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about exits
        
        Returns:
            Dict with exit statistics
        """
        if not self.exit_history:
            return {
                'total_exits': 0,
                'stop_loss_exits': 0,
                'take_profit_exits': 0,
                'invalidation_exits': 0,
                'trailing_stop_exits': 0,
                'avg_profit_loss': 0.0
            }
        
        stop_loss_count = sum(1 for e in self.exit_history if e['exit_reason'] == ExitReason.STOP_LOSS.value)
        take_profit_count = sum(1 for e in self.exit_history if e['exit_reason'] == ExitReason.TAKE_PROFIT.value)
        invalidation_count = sum(1 for e in self.exit_history if e['exit_reason'] == ExitReason.INVALIDATION.value)
        trailing_stop_count = sum(1 for e in self.exit_history if e['exit_reason'] == ExitReason.TRAILING_STOP.value)
        
        avg_pl = sum(e['profit_loss'] for e in self.exit_history) / len(self.exit_history)
        
        return {
            'total_exits': len(self.exit_history),
            'stop_loss_exits': stop_loss_count,
            'take_profit_exits': take_profit_count,
            'invalidation_exits': invalidation_count,
            'trailing_stop_exits': trailing_stop_count,
            'avg_profit_loss': avg_pl,
            'stop_loss_pct': stop_loss_count / len(self.exit_history) * 100,
            'take_profit_pct': take_profit_count / len(self.exit_history) * 100
        }
