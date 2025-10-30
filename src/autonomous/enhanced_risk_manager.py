"""
Enhanced Risk Manager

Advanced risk management for autonomous trading with:
- Daily loss limits (automatic shutdown)
- Over-trading prevention (max trades per day)
- Position size calculation based on confidence
- Per-symbol exposure limits
- Drawdown tracking
- Automatic risk adjustment

This is critical for zero human interaction to prevent catastrophic losses.
"""

import logging
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class DailyRiskState:
    """Daily risk tracking state"""
    date: date
    total_pnl: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    open_positions: int = 0
    symbols_traded: List[str] = field(default_factory=list)


class EnhancedRiskManager:
    """
    Enhanced risk manager for autonomous trading.
    
    Implements multiple layers of risk control:
    1. Daily loss limits - stops trading if daily loss exceeds threshold
    2. Over-trading prevention - limits number of trades per day
    3. Confidence-based position sizing - larger positions for higher confidence
    4. Per-symbol exposure limits - prevents concentration risk
    5. Drawdown tracking - monitors cumulative losses
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        max_daily_loss_pct: float = 5.0,  # 5% max daily loss
        max_daily_trades: int = 20,  # Max 20 trades per day
        max_position_size_pct: float = 10.0,  # Max 10% of capital per position
        min_position_size_pct: float = 1.0,  # Min 1% of capital per position
        max_symbol_exposure_pct: float = 20.0,  # Max 20% exposure per symbol
        confidence_scaling: bool = True,  # Scale position size by confidence
        min_confidence_for_full_size: float = 0.9,  # Confidence needed for max size
        min_trade_interval_sec: int = 1800,  # Min 30 minutes between trades per symbol
    ):
        """
        Initialize enhanced risk manager
        
        Args:
            initial_capital: Starting capital
            max_daily_loss_pct: Maximum daily loss percentage before stopping
            max_daily_trades: Maximum trades allowed per day
            max_position_size_pct: Maximum position size as % of capital
            min_position_size_pct: Minimum position size as % of capital
            max_symbol_exposure_pct: Maximum exposure per symbol as % of capital
            confidence_scaling: Whether to scale position size by confidence
            min_confidence_for_full_size: Confidence needed for maximum position size
            min_trade_interval_sec: Minimum seconds between trades per symbol (cooldown)
        """
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_daily_trades = max_daily_trades
        self.max_position_size_pct = max_position_size_pct
        self.min_position_size_pct = min_position_size_pct
        self.max_symbol_exposure_pct = max_symbol_exposure_pct
        self.confidence_scaling = confidence_scaling
        self.min_confidence_for_full_size = min_confidence_for_full_size
        self.min_trade_interval_sec = min_trade_interval_sec
        
        self.daily_state: Dict[date, DailyRiskState] = {}
        self.current_date = date.today()
        self._init_daily_state()
        
        self.symbol_exposure: Dict[str, float] = {}
        self.last_trade_time: Dict[str, datetime] = {}
        
        self.total_trades = 0
        self.total_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_capital = initial_capital
        
        logger.info(
            f"EnhancedRiskManager initialized: "
            f"capital=${initial_capital:.2f}, "
            f"max daily loss={max_daily_loss_pct}%, "
            f"max daily trades={max_daily_trades}, "
            f"position size={min_position_size_pct}-{max_position_size_pct}%, "
            f"trade cooldown={min_trade_interval_sec}s"
        )
    
    def _init_daily_state(self) -> None:
        """Initialize daily state for current date"""
        if self.current_date not in self.daily_state:
            self.daily_state[self.current_date] = DailyRiskState(date=self.current_date)
    
    def _check_new_day(self) -> None:
        """Check if it's a new day and reset daily state"""
        today = date.today()
        if today != self.current_date:
            logger.info(
                f"📅 New trading day: {today}, "
                f"Previous day P&L: ${self.daily_state[self.current_date].total_pnl:.2f}"
            )
            self.current_date = today
            self._init_daily_state()
    
    def can_trade_today(self) -> bool:
        """
        Check if trading is allowed today
        
        Returns:
            True if can trade, False if daily limits reached
        """
        self._check_new_day()
        state = self.daily_state[self.current_date]
        
        max_daily_loss = self.current_capital * (self.max_daily_loss_pct / 100.0)
        if state.total_pnl <= -max_daily_loss:
            logger.warning(
                f"🛑 Daily loss limit reached: ${state.total_pnl:.2f} <= ${-max_daily_loss:.2f}"
            )
            return False
        
        if state.total_trades >= self.max_daily_trades:
            logger.warning(
                f"🛑 Daily trade limit reached: {state.total_trades} >= {self.max_daily_trades}"
            )
            return False
        
        return True
    
    def can_trade_symbol(self, symbol: str) -> bool:
        """
        Check if we can trade this symbol (cooldown check)
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            True if enough time has passed since last trade, False otherwise
        """
        if symbol not in self.last_trade_time:
            return True
        
        elapsed = (datetime.now() - self.last_trade_time[symbol]).total_seconds()
        
        if elapsed < self.min_trade_interval_sec:
            remaining = self.min_trade_interval_sec - elapsed
            logger.debug(
                f"⏰ Symbol cooldown active for {symbol}: "
                f"{remaining:.0f}s remaining (min interval: {self.min_trade_interval_sec}s)"
            )
            return False
        
        return True
    
    def can_open_position(self, symbol: str) -> bool:
        """
        Check if we can open a position in this symbol
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            True if can open position, False otherwise
        """
        if not self.can_trade_today():
            return False
        
        if not self.can_trade_symbol(symbol):
            logger.warning(
                f"⏰ Cannot trade {symbol}: cooldown period active"
            )
            return False
        
        current_exposure = self.symbol_exposure.get(symbol, 0.0)
        max_exposure = self.current_capital * (self.max_symbol_exposure_pct / 100.0)
        
        if current_exposure >= max_exposure:
            logger.warning(
                f"⚠️  Symbol exposure limit reached for {symbol}: "
                f"${current_exposure:.2f} >= ${max_exposure:.2f}"
            )
            return False
        
        return True
    
    def calculate_position_size(
        self,
        confidence: float,
        price: float,
        symbol: Optional[str] = None
    ) -> float:
        """
        Calculate position size based on confidence and risk parameters
        
        Args:
            confidence: Signal confidence [0, 1]
            price: Current price
            symbol: Trading pair symbol (optional, for exposure checking)
            
        Returns:
            Position size in base currency units
        """
        if self.confidence_scaling:
            if confidence >= self.min_confidence_for_full_size:
                position_pct = self.max_position_size_pct
            else:
                confidence_range = self.min_confidence_for_full_size - 0.7
                confidence_above_min = max(0, confidence - 0.7)
                scale = confidence_above_min / confidence_range if confidence_range > 0 else 0
                
                position_pct = self.min_position_size_pct + (
                    (self.max_position_size_pct - self.min_position_size_pct) * scale
                )
        else:
            position_pct = self.max_position_size_pct
        
        position_value = self.current_capital * (position_pct / 100.0)
        
        if symbol:
            current_exposure = self.symbol_exposure.get(symbol, 0.0)
            max_exposure = self.current_capital * (self.max_symbol_exposure_pct / 100.0)
            available_exposure = max_exposure - current_exposure
            
            if position_value > available_exposure:
                position_value = available_exposure
                logger.info(
                    f"📊 Position size reduced to ${position_value:.2f} "
                    f"due to symbol exposure limit"
                )
        
        quantity = position_value / price if price > 0 else 0
        
        logger.info(
            f"📊 Position size calculated: "
            f"confidence={confidence:.2f}, "
            f"size={position_pct:.2f}% (${position_value:.2f}), "
            f"qty={quantity:.4f}"
        )
        
        return quantity
    
    def record_position_opened(
        self,
        symbol: str,
        position_value: float
    ) -> None:
        """
        Record that a position was opened
        
        Args:
            symbol: Trading pair symbol
            position_value: Value of the position
        """
        self._check_new_day()
        state = self.daily_state[self.current_date]
        
        self.symbol_exposure[symbol] = self.symbol_exposure.get(symbol, 0.0) + position_value
        self.last_trade_time[symbol] = datetime.now()
        
        state.open_positions += 1
        if symbol not in state.symbols_traded:
            state.symbols_traded.append(symbol)
        
        logger.info(
            f"📈 Position opened: {symbol}, "
            f"value=${position_value:.2f}, "
            f"exposure=${self.symbol_exposure[symbol]:.2f}, "
            f"cooldown={self.min_trade_interval_sec}s"
        )
    
    def record_position_closed(
        self,
        symbol: str,
        position_value: float
    ) -> None:
        """
        Record that a position was closed
        
        Args:
            symbol: Trading pair symbol
            position_value: Value of the position
        """
        state = self.daily_state[self.current_date]
        
        self.symbol_exposure[symbol] = max(0, self.symbol_exposure.get(symbol, 0.0) - position_value)
        
        state.open_positions = max(0, state.open_positions - 1)
        
        logger.info(
            f"📉 Position closed: {symbol}, "
            f"remaining exposure=${self.symbol_exposure[symbol]:.2f}"
        )
    
    def record_trade_result(
        self,
        pnl_amount: float,
        pnl_pct: float
    ) -> None:
        """
        Record the result of a completed trade
        
        Args:
            pnl_amount: Profit/loss amount in USD
            pnl_pct: Profit/loss percentage
        """
        self._check_new_day()
        state = self.daily_state[self.current_date]
        
        self.current_capital += pnl_amount
        
        state.total_pnl += pnl_amount
        state.total_trades += 1
        
        if pnl_amount > 0:
            state.winning_trades += 1
            state.largest_win = max(state.largest_win, pnl_amount)
        else:
            state.losing_trades += 1
            state.largest_loss = min(state.largest_loss, pnl_amount)
        
        self.total_trades += 1
        self.total_pnl += pnl_amount
        
        if self.current_capital > self.peak_capital:
            self.peak_capital = self.current_capital
        
        current_drawdown = (self.peak_capital - self.current_capital) / self.peak_capital * 100
        self.max_drawdown = max(self.max_drawdown, current_drawdown)
        
        logger.info(
            f"💰 Trade result recorded: "
            f"P&L=${pnl_amount:.2f} ({pnl_pct:.2f}%), "
            f"Capital=${self.current_capital:.2f}, "
            f"Daily P&L=${state.total_pnl:.2f}, "
            f"Daily Trades={state.total_trades}/{self.max_daily_trades}"
        )
        
        if not self.can_trade_today():
            logger.warning(
                f"🛑 TRADING HALTED: Daily limits reached. "
                f"P&L=${state.total_pnl:.2f}, Trades={state.total_trades}"
            )
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get risk management statistics
        
        Returns:
            Dict with statistics
        """
        self._check_new_day()
        state = self.daily_state[self.current_date]
        
        return {
            'current_capital': self.current_capital,
            'initial_capital': self.initial_capital,
            'total_pnl': self.total_pnl,
            'total_pnl_pct': (self.current_capital - self.initial_capital) / self.initial_capital * 100,
            'peak_capital': self.peak_capital,
            'max_drawdown': self.max_drawdown,
            'total_trades': self.total_trades,
            'daily_pnl': state.total_pnl,
            'daily_trades': state.total_trades,
            'daily_winning_trades': state.winning_trades,
            'daily_losing_trades': state.losing_trades,
            'daily_win_rate': state.winning_trades / state.total_trades * 100 if state.total_trades > 0 else 0,
            'can_trade_today': self.can_trade_today(),
            'open_positions': state.open_positions,
            'symbols_traded_today': len(state.symbols_traded),
            'symbol_exposure': self.symbol_exposure.copy()
        }
    
    def get_daily_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        Get daily history for the last N days
        
        Args:
            days: Number of days to retrieve
            
        Returns:
            List of daily statistics
        """
        history = []
        
        for d in sorted(self.daily_state.keys(), reverse=True)[:days]:
            state = self.daily_state[d]
            history.append({
                'date': d.isoformat(),
                'total_pnl': state.total_pnl,
                'total_trades': state.total_trades,
                'winning_trades': state.winning_trades,
                'losing_trades': state.losing_trades,
                'win_rate': state.winning_trades / state.total_trades * 100 if state.total_trades > 0 else 0,
                'largest_win': state.largest_win,
                'largest_loss': state.largest_loss,
                'symbols_traded': len(state.symbols_traded)
            })
        
        return history
    
    def reset_daily_limits(self) -> None:
        """Reset daily limits (for testing or manual override)"""
        logger.warning("⚠️  Manually resetting daily limits")
        self._init_daily_state()
    
    def adjust_risk_parameters(
        self,
        max_daily_loss_pct: Optional[float] = None,
        max_daily_trades: Optional[int] = None,
        max_position_size_pct: Optional[float] = None
    ) -> None:
        """
        Adjust risk parameters dynamically
        
        Args:
            max_daily_loss_pct: New max daily loss percentage
            max_daily_trades: New max daily trades
            max_position_size_pct: New max position size percentage
        """
        if max_daily_loss_pct is not None:
            old_val = self.max_daily_loss_pct
            self.max_daily_loss_pct = max_daily_loss_pct
            logger.info(f"📊 Adjusted max_daily_loss_pct: {old_val}% -> {max_daily_loss_pct}%")
        
        if max_daily_trades is not None:
            old_val = self.max_daily_trades
            self.max_daily_trades = max_daily_trades
            logger.info(f"📊 Adjusted max_daily_trades: {old_val} -> {max_daily_trades}")
        
        if max_position_size_pct is not None:
            old_val = self.max_position_size_pct
            self.max_position_size_pct = max_position_size_pct
            logger.info(f"📊 Adjusted max_position_size_pct: {old_val}% -> {max_position_size_pct}%")
