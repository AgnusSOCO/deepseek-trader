"""
Position Sizing

Calculates optimal position sizes based on risk parameters, account balance,
volatility, and leverage constraints.
"""

from typing import Dict, Any, Optional
from loguru import logger
import math


class PositionSizer:
    """
    Calculates position sizes based on risk management rules
    
    Supports multiple position sizing methods:
    - Fixed percentage of capital
    - Risk-based sizing (based on stop-loss distance)
    - Volatility-adjusted sizing (ATR-based)
    - Kelly Criterion (optional)
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize position sizer
        
        Args:
            config: Position sizing configuration
        """
        self.config = config
        self.default_risk_pct = config.get('default_risk_pct', 0.01)  # 1% per trade
        self.max_position_pct = config.get('max_position_pct', 0.1)  # 10% max position
        self.min_position_size = config.get('min_position_size', 0.001)
        self.use_kelly = config.get('use_kelly', False)
        
    def calculate_position_size(self,
                                account_balance: float,
                                entry_price: float,
                                stop_loss: Optional[float] = None,
                                atr: Optional[float] = None,
                                leverage: float = 1.0,
                                risk_pct: Optional[float] = None,
                                win_rate: Optional[float] = None,
                                avg_win_loss_ratio: Optional[float] = None) -> Dict[str, Any]:
        """
        Calculate position size based on risk parameters
        
        Args:
            account_balance: Current account balance
            entry_price: Entry price for the position
            stop_loss: Stop-loss price (optional)
            atr: Average True Range for volatility adjustment (optional)
            leverage: Leverage to use (default: 1.0)
            risk_pct: Risk percentage override (optional)
            win_rate: Historical win rate for Kelly Criterion (optional)
            avg_win_loss_ratio: Average win/loss ratio for Kelly (optional)
            
        Returns:
            Dictionary with position size and related information
        """
        risk_percentage = risk_pct if risk_pct is not None else self.default_risk_pct
        
        risk_amount = account_balance * risk_percentage
        
        if stop_loss is not None:
            position_size_risk = self._calculate_risk_based_size(
                risk_amount, entry_price, stop_loss, leverage
            )
        else:
            position_size_risk = None
        
        position_size_fixed = self._calculate_fixed_percentage_size(
            account_balance, entry_price, leverage
        )
        
        if atr is not None:
            position_size_volatility = self._calculate_volatility_adjusted_size(
                account_balance, entry_price, atr, leverage
            )
        else:
            position_size_volatility = None
        
        if self.use_kelly and win_rate is not None and avg_win_loss_ratio is not None:
            position_size_kelly = self._calculate_kelly_size(
                account_balance, entry_price, win_rate, avg_win_loss_ratio, leverage
            )
        else:
            position_size_kelly = None
        
        if position_size_risk is not None:
            final_size = position_size_risk
            method = 'risk_based'
        elif position_size_volatility is not None:
            final_size = position_size_volatility
            method = 'volatility_adjusted'
        else:
            final_size = position_size_fixed
            method = 'fixed_percentage'
        
        if self.use_kelly and position_size_kelly is not None:
            kelly_fraction = 0.25
            final_size = min(final_size, position_size_kelly * kelly_fraction)
            method = f'{method}_kelly_adjusted'
        
        final_size = self._apply_constraints(final_size, account_balance, entry_price, leverage)
        
        position_value = final_size * entry_price
        margin_required = position_value / leverage if leverage > 1 else position_value
        
        risk_reward_ratio = None
        if stop_loss is not None:
            risk_per_unit = abs(entry_price - stop_loss)
            risk_reward_ratio = risk_per_unit / entry_price
        
        result = {
            'position_size': final_size,
            'position_value': position_value,
            'margin_required': margin_required,
            'risk_amount': risk_amount,
            'risk_percentage': risk_percentage,
            'leverage': leverage,
            'method': method,
            'risk_reward_ratio': risk_reward_ratio,
            'calculations': {
                'risk_based': position_size_risk,
                'fixed_percentage': position_size_fixed,
                'volatility_adjusted': position_size_volatility,
                'kelly': position_size_kelly
            }
        }
        
        logger.debug(f"Calculated position size: {final_size:.6f} (method: {method}, "
                    f"value: {position_value:.2f}, margin: {margin_required:.2f})")
        
        return result
    
    def _calculate_risk_based_size(self,
                                   risk_amount: float,
                                   entry_price: float,
                                   stop_loss: float,
                                   leverage: float) -> float:
        """
        Calculate position size based on risk amount and stop-loss distance
        
        Position Size = Risk Amount / (Entry Price - Stop Loss) * Leverage
        """
        if entry_price <= 0 or stop_loss <= 0:
            return 0.0
        
        risk_per_unit = abs(entry_price - stop_loss)
        
        if risk_per_unit == 0:
            return 0.0
        
        position_size = (risk_amount / risk_per_unit) * leverage
        
        return position_size
    
    def _calculate_fixed_percentage_size(self,
                                        account_balance: float,
                                        entry_price: float,
                                        leverage: float) -> float:
        """
        Calculate position size as fixed percentage of account balance
        
        Position Size = (Account Balance * Max Position %) / Entry Price * Leverage
        """
        if entry_price <= 0:
            return 0.0
        
        position_value = account_balance * self.max_position_pct
        position_size = (position_value / entry_price) * leverage
        
        return position_size
    
    def _calculate_volatility_adjusted_size(self,
                                           account_balance: float,
                                           entry_price: float,
                                           atr: float,
                                           leverage: float) -> float:
        """
        Calculate position size adjusted for volatility (ATR)
        
        Higher volatility = smaller position size
        """
        if entry_price <= 0 or atr <= 0:
            return 0.0
        
        volatility_pct = atr / entry_price
        
        volatility_factor = max(volatility_pct * 100, 1.0)  # Normalize
        
        base_position_value = account_balance * self.max_position_pct
        adjusted_position_value = base_position_value / volatility_factor
        
        position_size = (adjusted_position_value / entry_price) * leverage
        
        return position_size
    
    def _calculate_kelly_size(self,
                             account_balance: float,
                             entry_price: float,
                             win_rate: float,
                             avg_win_loss_ratio: float,
                             leverage: float) -> float:
        """
        Calculate position size using Kelly Criterion
        
        Kelly % = W - [(1 - W) / R]
        where W = win rate, R = avg win/loss ratio
        """
        if entry_price <= 0 or win_rate <= 0 or win_rate >= 1:
            return 0.0
        
        if avg_win_loss_ratio <= 0:
            return 0.0
        
        kelly_pct = win_rate - ((1 - win_rate) / avg_win_loss_ratio)
        
        kelly_pct = max(0.0, min(kelly_pct, 1.0))
        
        position_value = account_balance * kelly_pct
        position_size = (position_value / entry_price) * leverage
        
        return position_size
    
    def _apply_constraints(self,
                          position_size: float,
                          account_balance: float,
                          entry_price: float,
                          leverage: float) -> float:
        """
        Apply position size constraints
        
        - Minimum position size
        - Maximum position size (as % of account)
        - Round to appropriate precision
        """
        if position_size < self.min_position_size:
            position_size = 0.0
            logger.warning(f"Position size below minimum ({self.min_position_size}), setting to 0")
        
        max_position_value = account_balance * self.max_position_pct
        max_position_size = (max_position_value / entry_price) * leverage
        
        if position_size > max_position_size:
            logger.warning(f"Position size {position_size:.6f} exceeds maximum {max_position_size:.6f}, capping")
            position_size = max_position_size
        
        position_size = round(position_size, 6)
        
        return position_size
    
    def calculate_stop_loss(self,
                           entry_price: float,
                           side: str,
                           atr: Optional[float] = None,
                           risk_pct: float = 0.02) -> float:
        """
        Calculate stop-loss price
        
        Args:
            entry_price: Entry price
            side: Position side ('BUY' or 'SELL')
            atr: Average True Range (optional, for ATR-based stops)
            risk_pct: Risk percentage for fixed stops (default: 2%)
            
        Returns:
            Stop-loss price
        """
        if atr is not None:
            stop_distance = atr * 2
        else:
            stop_distance = entry_price * risk_pct
        
        if side.upper() == 'BUY':
            stop_loss = entry_price - stop_distance
        else:  # SELL
            stop_loss = entry_price + stop_distance
        
        return max(stop_loss, 0.0)  # Ensure non-negative
    
    def calculate_take_profit(self,
                             entry_price: float,
                             stop_loss: float,
                             side: str,
                             risk_reward_ratio: float = 2.0) -> float:
        """
        Calculate take-profit price based on risk-reward ratio
        
        Args:
            entry_price: Entry price
            stop_loss: Stop-loss price
            side: Position side ('BUY' or 'SELL')
            risk_reward_ratio: Desired risk-reward ratio (default: 2.0)
            
        Returns:
            Take-profit price
        """
        risk_distance = abs(entry_price - stop_loss)
        reward_distance = risk_distance * risk_reward_ratio
        
        if side.upper() == 'BUY':
            take_profit = entry_price + reward_distance
        else:  # SELL
            take_profit = entry_price - reward_distance
        
        return max(take_profit, 0.0)  # Ensure non-negative
