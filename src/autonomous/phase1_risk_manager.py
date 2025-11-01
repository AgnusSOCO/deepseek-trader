"""
Phase 1 Integrated Risk Management System

Integrates all Phase 1 nof1.ai-inspired risk management features:
1. Trading profiles (Conservative/Balanced/Aggressive)
2. Trailing stop-loss system (3-level, profit-based)
3. Partial take-profit system (staged profit-taking)
4. Peak drawdown protection (from profit peak)
5. Account-level drawdown protection (3-tier)
6. Maximum holding time enforcement (36-hour limit)

This manager coordinates all Phase 1 components and provides a unified
interface for the autonomous trading system.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from src.autonomous.trading_profiles import (
    TradingProfile,
    TradingProfileManager,
    ProfileConfig
)
from src.execution.trailing_stops import TrailingStopManager
from src.execution.partial_take_profit import PartialTakeProfitManager
from src.execution.peak_drawdown_protection import PeakDrawdownProtectionManager
from src.autonomous.account_drawdown_protection import (
    AccountDrawdownProtectionManager,
    DrawdownLevel
)
from src.execution.max_holding_time import MaxHoldingTimeManager


logger = logging.getLogger(__name__)


@dataclass
class PositionRiskState:
    """Complete risk state for a position"""
    symbol: str
    side: str
    entry_price: float
    current_price: float
    current_pnl_percent: float
    
    trailing_stop_active: bool
    trailing_stop_level: int
    current_stop_loss_percent: Optional[float]
    
    partial_tp_stages_completed: int
    remaining_position_percent: float
    
    peak_profit_percent: float
    drawdown_from_peak: float
    
    holding_time_hours: float
    remaining_time_hours: float
    is_expired: bool
    
    should_exit: bool
    exit_reasons: List[str]


class Phase1RiskManager:
    """
    Integrated Phase 1 Risk Management System
    
    Coordinates all Phase 1 risk management components and provides
    unified interface for position monitoring and exit decisions.
    """
    
    def __init__(
        self,
        profile: TradingProfile = TradingProfile.BALANCED,
        initial_equity: float = 10000.0,
        max_holding_hours: float = 36.0,
        account_drawdown_warning: float = 20.0,
        account_drawdown_no_new: float = 30.0,
        account_drawdown_force_close: float = 50.0
    ):
        """
        Initialize Phase 1 risk management system
        
        Args:
            profile: Trading profile to use
            initial_equity: Starting account equity
            max_holding_hours: Maximum hours to hold positions
            account_drawdown_warning: Account drawdown % for warning
            account_drawdown_no_new: Account drawdown % to stop new positions
            account_drawdown_force_close: Account drawdown % to force close all
        """
        self.profile_manager = TradingProfileManager(profile)
        self.profile_config = self.profile_manager.get_config()
        
        self.trailing_stops = TrailingStopManager(self.profile_config)
        self.partial_take_profit = PartialTakeProfitManager(self.profile_config)
        self.peak_drawdown = PeakDrawdownProtectionManager(self.profile_config)
        self.max_holding_time = MaxHoldingTimeManager(max_holding_hours)
        self.account_drawdown = AccountDrawdownProtectionManager(
            initial_equity=initial_equity,
            warning_threshold=account_drawdown_warning,
            no_new_positions_threshold=account_drawdown_no_new,
            force_close_threshold=account_drawdown_force_close
        )
        
        logger.info(
            f"Initialized Phase 1 Risk Manager: "
            f"Profile={profile.value}, "
            f"Initial Equity=${initial_equity:.2f}, "
            f"Max Holding={max_holding_hours}h"
        )
    
    def add_position(
        self,
        symbol: str,
        side: str,
        entry_price: float,
        position_size: float,
        initial_stop_loss_percent: Optional[float] = None,
        entry_time: Optional[datetime] = None
    ):
        """
        Add a new position to all risk management components
        
        Args:
            symbol: Trading symbol
            side: 'long' or 'short'
            entry_price: Entry price
            position_size: Position size
            initial_stop_loss_percent: Initial stop-loss % (optional)
            entry_time: Entry time (default: now)
        """
        self.trailing_stops.add_position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            initial_stop_loss_percent=initial_stop_loss_percent
        )
        
        self.partial_take_profit.add_position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            position_size=position_size
        )
        
        self.peak_drawdown.add_position(
            symbol=symbol,
            side=side,
            entry_price=entry_price
        )
        
        self.max_holding_time.add_position(
            symbol=symbol,
            side=side,
            entry_price=entry_price,
            entry_time=entry_time
        )
        
        logger.info(
            f"Added position to Phase 1 risk management: "
            f"{symbol} {side} @ {entry_price}, size: {position_size}"
        )
    
    def update_position(self, symbol: str, current_price: float) -> Dict:
        """
        Update position price across all risk management components
        
        Args:
            symbol: Trading symbol
            current_price: Current market price
            
        Returns:
            Dict with all update information
        """
        updates = {
            'symbol': symbol,
            'current_price': current_price,
            'trailing_stop_update': None,
            'partial_tp_update': None,
            'peak_drawdown_update': None,
            'holding_time_update': None,
        }
        
        updates['trailing_stop_update'] = self.trailing_stops.update_position(symbol, current_price)
        updates['partial_tp_update'] = self.partial_take_profit.update_position(symbol, current_price)
        updates['peak_drawdown_update'] = self.peak_drawdown.update_position(symbol, current_price)
        updates['holding_time_update'] = self.max_holding_time.update_position(symbol, current_price)
        
        return updates
    
    def update_account_equity(self, current_equity: float):
        """
        Update account equity for account-level drawdown protection
        
        Args:
            current_equity: Current account equity
        """
        event = self.account_drawdown.update_equity(current_equity)
        
        if event:
            logger.warning(
                f"Account drawdown event: {event.level.value} - "
                f"Drawdown: {event.drawdown_percent:.2f}%, "
                f"Action: {event.action_taken}"
            )
    
    def should_exit_position(self, symbol: str) -> Tuple[bool, List[str]]:
        """
        Check if position should be exited based on all risk criteria
        
        Args:
            symbol: Trading symbol
            
        Returns:
            (should_exit, list_of_reasons)
        """
        reasons = []
        
        ts_exit, ts_reason = self.trailing_stops.should_exit_position(symbol)
        if ts_exit and ts_reason:
            reasons.append(f"Trailing Stop: {ts_reason}")
        
        pd_exit, pd_reason = self.peak_drawdown.should_exit_position(symbol)
        if pd_exit and pd_reason:
            reasons.append(f"Peak Drawdown: {pd_reason}")
        
        mht_exit, mht_reason = self.max_holding_time.should_close_position(symbol)
        if mht_exit and mht_reason:
            reasons.append(f"Max Holding Time: {mht_reason}")
        
        force_close, fc_reason = self.account_drawdown.should_force_close_all()
        if force_close and fc_reason:
            reasons.append(f"Account Force Close: {fc_reason}")
        
        should_exit = len(reasons) > 0
        
        if should_exit:
            logger.warning(
                f"Exit recommended for {symbol}: {len(reasons)} reasons - "
                f"{'; '.join(reasons)}"
            )
        
        return should_exit, reasons
    
    def should_partial_close(self, symbol: str) -> Tuple[bool, Optional[float], Optional[str]]:
        """
        Check if position should be partially closed for take-profit
        
        Args:
            symbol: Trading symbol
            
        Returns:
            (should_close, close_percent, reason)
        """
        return self.partial_take_profit.should_close_position(symbol)
    
    def can_open_new_position(self) -> Tuple[bool, Optional[str]]:
        """
        Check if new positions can be opened (account-level check)
        
        Returns:
            (can_open, reason_if_blocked)
        """
        return self.account_drawdown.can_open_new_position()
    
    def get_position_risk_state(self, symbol: str) -> Optional[PositionRiskState]:
        """
        Get complete risk state for a position
        
        Args:
            symbol: Trading symbol
            
        Returns:
            PositionRiskState with all risk information
        """
        ts_state = self.trailing_stops.get_position_state(symbol)
        ptp_state = self.partial_take_profit.get_position_state(symbol)
        pd_state = self.peak_drawdown.get_position_state(symbol)
        mht_state = self.max_holding_time.get_position_state(symbol)
        
        if not all([ts_state, ptp_state, pd_state, mht_state]):
            return None
        
        should_exit, exit_reasons = self.should_exit_position(symbol)
        
        return PositionRiskState(
            symbol=symbol,
            side=ts_state.side,
            entry_price=ts_state.entry_price,
            current_price=ts_state.current_price,
            current_pnl_percent=ts_state.current_pnl_percent,
            
            trailing_stop_active=ts_state.active_level > 0,
            trailing_stop_level=ts_state.active_level,
            current_stop_loss_percent=ts_state.current_stop_loss_percent,
            
            partial_tp_stages_completed=ptp_state.next_stage_index,
            remaining_position_percent=ptp_state.get_remaining_position_percent(),
            
            peak_profit_percent=pd_state.peak_pnl_percent,
            drawdown_from_peak=pd_state.calculate_drawdown_from_peak(),
            
            holding_time_hours=mht_state.get_holding_time_hours(),
            remaining_time_hours=mht_state.get_remaining_time_hours(),
            is_expired=mht_state.is_expired(),
            
            should_exit=should_exit,
            exit_reasons=exit_reasons
        )
    
    def remove_position(self, symbol: str):
        """
        Remove position from all risk management components
        
        Args:
            symbol: Trading symbol
        """
        self.trailing_stops.remove_position(symbol)
        self.partial_take_profit.remove_position(symbol)
        self.peak_drawdown.remove_position(symbol)
        self.max_holding_time.remove_position(symbol)
        
        logger.info(f"Removed position from Phase 1 risk management: {symbol}")
    
    def get_profile_config(self) -> ProfileConfig:
        """Get current trading profile configuration"""
        return self.profile_config
    
    def set_profile(self, profile: TradingProfile):
        """
        Change trading profile
        
        Args:
            profile: New trading profile
        """
        old_profile = self.profile_manager.profile
        self.profile_manager.set_profile(profile)
        self.profile_config = self.profile_manager.get_config()
        
        self.trailing_stops = TrailingStopManager(self.profile_config)
        self.partial_take_profit = PartialTakeProfitManager(self.profile_config)
        self.peak_drawdown = PeakDrawdownProtectionManager(self.profile_config)
        
        logger.info(
            f"Changed trading profile: {old_profile.value} → {profile.value}"
        )
    
    def get_comprehensive_statistics(self) -> Dict:
        """Get comprehensive statistics from all risk components"""
        return {
            'profile': {
                'name': self.profile_config.name,
                'type': self.profile_manager.profile.value,
                'leverage_range': f"{self.profile_config.leverage_min}-{self.profile_config.leverage_max}x",
                'position_size_range': f"{self.profile_config.position_size_min}-{self.profile_config.position_size_max}%",
            },
            'trailing_stops': self.trailing_stops.get_statistics(),
            'partial_take_profit': self.partial_take_profit.get_statistics(),
            'peak_drawdown': self.peak_drawdown.get_statistics(),
            'max_holding_time': self.max_holding_time.get_statistics(),
            'account_drawdown': self.account_drawdown.get_statistics(),
        }
    
    def get_all_position_states(self) -> Dict[str, PositionRiskState]:
        """Get risk states for all tracked positions"""
        symbols = set()
        symbols.update(self.trailing_stops.get_all_states().keys())
        symbols.update(self.partial_take_profit.get_all_states().keys())
        symbols.update(self.peak_drawdown.get_all_states().keys())
        symbols.update(self.max_holding_time.get_all_states().keys())
        
        states = {}
        for symbol in symbols:
            state = self.get_position_risk_state(symbol)
            if state:
                states[symbol] = state
        
        return states
