"""
Leverage Manager

Dynamic leverage calculation and margin management for perpetual futures trading.
Adjusts leverage based on confidence, volatility, and drawdown.
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class LeverageConfig:
    """Leverage configuration"""
    absolute_max: float = 10.0
    scalping_max: float = 5.0
    momentum_max: float = 5.0
    mean_reversion_max: float = 3.0
    margin_alert_threshold: float = 0.70
    margin_reduce_threshold: float = 0.85
    margin_buffer: float = 0.15


@dataclass
class MarginStatus:
    """Current margin status"""
    total_margin: float
    used_margin: float
    available_margin: float
    margin_ratio: float
    positions_value: float
    unrealized_pnl: float
    liquidation_price: Optional[float] = None
    
    @property
    def is_alert_level(self) -> bool:
        """Check if margin usage is at alert level"""
        return self.margin_ratio > 0.70
    
    @property
    def is_critical_level(self) -> bool:
        """Check if margin usage is at critical level"""
        return self.margin_ratio > 0.85


class LeverageManager:
    """
    Dynamic leverage manager for perpetual futures trading
    
    Calculates optimal leverage based on:
    - Strategy type
    - AI confidence level
    - Market volatility
    - Current drawdown
    - Margin usage
    """
    
    def __init__(self, config: Optional[LeverageConfig] = None):
        """
        Initialize leverage manager
        
        Args:
            config: Leverage configuration (uses defaults if None)
        """
        self.config = config or LeverageConfig()
        self.current_drawdown_pct = 0.0
        self.peak_portfolio_value = 0.0
        
        logger.info(f"LeverageManager initialized with max leverage: {self.config.absolute_max}x")
    
    def calculate_leverage(
        self,
        strategy_type: str,
        confidence: float,
        volatility_pct: float,
        drawdown_pct: float,
        base_leverage: Optional[float] = None
    ) -> float:
        """
        Calculate dynamic leverage
        
        Args:
            strategy_type: Strategy name ('scalping', 'momentum', 'mean_reversion')
            confidence: AI confidence level (0-1)
            volatility_pct: Market volatility percentage
            drawdown_pct: Current drawdown percentage (0-100)
            base_leverage: Base leverage for strategy (uses defaults if None)
        
        Returns:
            Calculated leverage (1x-10x)
        """
        if base_leverage is None:
            base_leverage = self._get_base_leverage(strategy_type)
        
        confidence_multiplier = self._calculate_confidence_multiplier(confidence)
        volatility_adjustment = self._calculate_volatility_adjustment(volatility_pct)
        drawdown_adjustment = self._calculate_drawdown_adjustment(drawdown_pct)
        
        leverage = base_leverage * confidence_multiplier * volatility_adjustment * drawdown_adjustment
        
        strategy_max = self._get_strategy_max_leverage(strategy_type)
        leverage = min(leverage, strategy_max)
        
        leverage = min(leverage, self.config.absolute_max)
        
        leverage = max(1.0, leverage)
        
        logger.debug(
            f"Leverage calculation: base={base_leverage:.1f}x, "
            f"confidence_mult={confidence_multiplier:.2f}, "
            f"volatility_adj={volatility_adjustment:.2f}, "
            f"drawdown_adj={drawdown_adjustment:.2f}, "
            f"final={leverage:.1f}x"
        )
        
        return leverage
    
    def _get_base_leverage(self, strategy_type: str) -> float:
        """Get base leverage for strategy type"""
        base_leverages = {
            'scalping': 3.0,
            'momentum': 3.0,
            'mean_reversion': 2.0,
            'ai': 2.5,
            'default': 2.0
        }
        return base_leverages.get(strategy_type.lower(), base_leverages['default'])
    
    def _get_strategy_max_leverage(self, strategy_type: str) -> float:
        """Get maximum leverage for strategy type"""
        max_leverages = {
            'scalping': self.config.scalping_max,
            'momentum': self.config.momentum_max,
            'mean_reversion': self.config.mean_reversion_max,
            'ai': self.config.momentum_max,
            'default': self.config.mean_reversion_max
        }
        return max_leverages.get(strategy_type.lower(), max_leverages['default'])
    
    def _calculate_confidence_multiplier(self, confidence: float) -> float:
        """
        Calculate confidence multiplier (0.5-1.5)
        
        Args:
            confidence: AI confidence (0-1)
        
        Returns:
            Multiplier (0.5-1.5)
        """
        return 0.5 + confidence
    
    def _calculate_volatility_adjustment(self, volatility_pct: float) -> float:
        """
        Calculate volatility adjustment (0.5-1.0)
        
        Lower leverage in high volatility to reduce risk
        
        Args:
            volatility_pct: Market volatility percentage
        
        Returns:
            Adjustment factor (0.5-1.0)
        """
        if volatility_pct > 4.0:
            return 0.5
        elif volatility_pct > 3.0:
            return 0.6
        elif volatility_pct > 2.0:
            return 0.75
        elif volatility_pct > 1.0:
            return 0.9
        else:
            return 1.0
    
    def _calculate_drawdown_adjustment(self, drawdown_pct: float) -> float:
        """
        Calculate drawdown adjustment (0.3-1.0)
        
        Lower leverage when near max drawdown to preserve capital
        
        Args:
            drawdown_pct: Current drawdown percentage (0-100)
        
        Returns:
            Adjustment factor (0.3-1.0)
        """
        if drawdown_pct > 12.0:
            return 0.3
        elif drawdown_pct > 10.0:
            return 0.4
        elif drawdown_pct > 8.0:
            return 0.5
        elif drawdown_pct > 6.0:
            return 0.7
        elif drawdown_pct > 4.0:
            return 0.85
        else:
            return 1.0
    
    def calculate_margin_status(
        self,
        account_balance: float,
        positions: list,
        leverage_by_position: Dict[str, float]
    ) -> MarginStatus:
        """
        Calculate current margin status
        
        Args:
            account_balance: Total account balance
            positions: List of open positions
            leverage_by_position: Dict mapping position ID to leverage
        
        Returns:
            MarginStatus with current margin metrics
        """
        positions_value = sum(
            abs(pos.get('size', 0) * pos.get('price', 0))
            for pos in positions
        )
        
        used_margin = 0.0
        for pos in positions:
            pos_value = abs(pos.get('size', 0) * pos.get('price', 0))
            pos_id = pos.get('id', '')
            leverage = leverage_by_position.get(pos_id, 1.0)
            used_margin += pos_value / leverage if leverage > 0 else pos_value
        
        unrealized_pnl = sum(pos.get('unrealized_pnl', 0) for pos in positions)
        
        total_margin = account_balance + unrealized_pnl
        
        available_margin = total_margin - used_margin
        
        margin_ratio = used_margin / total_margin if total_margin > 0 else 0.0
        
        return MarginStatus(
            total_margin=total_margin,
            used_margin=used_margin,
            available_margin=available_margin,
            margin_ratio=margin_ratio,
            positions_value=positions_value,
            unrealized_pnl=unrealized_pnl
        )
    
    def check_margin_requirements(
        self,
        proposed_trade_value: float,
        proposed_leverage: float,
        margin_status: MarginStatus
    ) -> tuple[bool, str]:
        """
        Check if proposed trade meets margin requirements
        
        Args:
            proposed_trade_value: Value of proposed trade
            proposed_leverage: Proposed leverage for trade
            margin_status: Current margin status
        
        Returns:
            Tuple of (approved, reason)
        """
        required_margin = proposed_trade_value / proposed_leverage if proposed_leverage > 0 else proposed_trade_value
        
        if required_margin > margin_status.available_margin:
            return False, f"Insufficient margin: required={required_margin:.2f}, available={margin_status.available_margin:.2f}"
        
        new_used_margin = margin_status.used_margin + required_margin
        new_margin_ratio = new_used_margin / margin_status.total_margin if margin_status.total_margin > 0 else 1.0
        
        if new_margin_ratio > self.config.margin_reduce_threshold:
            return False, f"Margin ratio would exceed threshold: {new_margin_ratio:.1%} > {self.config.margin_reduce_threshold:.1%}"
        
        margin_buffer = margin_status.available_margin - required_margin
        min_buffer = margin_status.total_margin * self.config.margin_buffer
        
        if margin_buffer < min_buffer:
            return False, f"Insufficient margin buffer: {margin_buffer:.2f} < {min_buffer:.2f}"
        
        return True, "Margin requirements met"
    
    def should_reduce_positions(self, margin_status: MarginStatus) -> bool:
        """
        Check if positions should be reduced due to margin pressure
        
        Args:
            margin_status: Current margin status
        
        Returns:
            True if positions should be reduced
        """
        if margin_status.is_critical_level:
            logger.warning(
                f"Critical margin level: {margin_status.margin_ratio:.1%} > "
                f"{self.config.margin_reduce_threshold:.1%}"
            )
            return True
        
        return False
    
    def should_alert_margin(self, margin_status: MarginStatus) -> bool:
        """
        Check if margin alert should be triggered
        
        Args:
            margin_status: Current margin status
        
        Returns:
            True if alert should be triggered
        """
        if margin_status.is_alert_level:
            logger.warning(
                f"Margin alert level: {margin_status.margin_ratio:.1%} > "
                f"{self.config.margin_alert_threshold:.1%}"
            )
            return True
        
        return False
    
    def calculate_position_reduction(
        self,
        margin_status: MarginStatus,
        target_margin_ratio: float = 0.70
    ) -> float:
        """
        Calculate how much positions should be reduced
        
        Args:
            margin_status: Current margin status
            target_margin_ratio: Target margin ratio after reduction
        
        Returns:
            Percentage of positions to close (0-1)
        """
        if margin_status.margin_ratio <= target_margin_ratio:
            return 0.0
        
        target_used_margin = margin_status.total_margin * target_margin_ratio
        excess_margin = margin_status.used_margin - target_used_margin
        
        reduction_pct = excess_margin / margin_status.used_margin if margin_status.used_margin > 0 else 0.0
        
        reduction_pct = min(1.0, max(0.0, reduction_pct))
        
        logger.info(
            f"Position reduction calculated: {reduction_pct:.1%} "
            f"(current ratio={margin_status.margin_ratio:.1%}, target={target_margin_ratio:.1%})"
        )
        
        return reduction_pct
    
    def update_drawdown(self, current_portfolio_value: float):
        """
        Update drawdown tracking
        
        Args:
            current_portfolio_value: Current portfolio value
        """
        if current_portfolio_value > self.peak_portfolio_value:
            self.peak_portfolio_value = current_portfolio_value
        
        if self.peak_portfolio_value > 0:
            self.current_drawdown_pct = ((self.peak_portfolio_value - current_portfolio_value) / self.peak_portfolio_value) * 100
        else:
            self.current_drawdown_pct = 0.0
    
    def get_current_drawdown(self) -> float:
        """Get current drawdown percentage"""
        return self.current_drawdown_pct
    
    def reset_peak(self):
        """Reset peak portfolio value"""
        self.peak_portfolio_value = 0.0
        self.current_drawdown_pct = 0.0
        logger.info("Peak portfolio value reset")
