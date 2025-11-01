"""
Trading Profiles System - nof1.ai inspired

Implements Conservative, Balanced, and Aggressive trading profiles with
strategy-specific risk parameters, leverage ranges, and position sizing rules.

Based on nof1.ai's multi-strategy approach:
- Conservative: Low risk, strict entry conditions, early profit-taking
- Balanced: Medium risk, moderate entry conditions, balanced profit-taking
- Aggressive: High risk, relaxed entry conditions, late profit-taking
"""

from dataclasses import dataclass
from typing import Dict, Literal
from enum import Enum


class TradingProfile(str, Enum):
    """Trading profile types"""
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"


@dataclass
class TrailingStopLevel:
    """Trailing stop-loss level configuration"""
    trigger_profit_pct: float  # Profit % to trigger this level
    stop_at_profit_pct: float  # Move stop-loss to this profit %


@dataclass
class PartialTakeProfitStage:
    """Partial take-profit stage configuration"""
    trigger_profit_pct: float  # Profit % to trigger this stage
    close_percent: float  # Percentage of position to close (0-100)


@dataclass
class VolatilityAdjustment:
    """Volatility-based adjustment factors"""
    leverage_factor: float  # Multiply leverage by this factor
    position_factor: float  # Multiply position size by this factor


@dataclass
class ProfileConfig:
    """Complete trading profile configuration"""
    
    name: str
    description: str
    
    leverage_min: int
    leverage_max: int
    leverage_normal: int  # For normal signals
    leverage_good: int    # For good signals
    leverage_strong: int  # For strong signals
    
    position_size_min: float
    position_size_max: float
    position_size_normal: float  # For normal signals
    position_size_good: float    # For good signals
    position_size_strong: float  # For strong signals
    
    stop_loss_low: float   # For low leverage positions
    stop_loss_mid: float   # For mid leverage positions
    stop_loss_high: float  # For high leverage positions
    
    trailing_stops: list[TrailingStopLevel]
    
    partial_take_profit: list[PartialTakeProfitStage]
    
    peak_drawdown_threshold: float
    
    high_volatility_adjustment: VolatilityAdjustment  # ATR > 5%
    normal_volatility_adjustment: VolatilityAdjustment  # ATR 2-5%
    low_volatility_adjustment: VolatilityAdjustment  # ATR < 2%
    
    min_timeframe_confirmations: int  # Minimum timeframes that must agree
    
    risk_tolerance: str
    trading_style: str
    target_monthly_return: str
    
    def get_leverage_for_signal_strength(self, strength: Literal["normal", "good", "strong"]) -> int:
        """Get recommended leverage based on signal strength"""
        if strength == "normal":
            return self.leverage_normal
        elif strength == "good":
            return self.leverage_good
        else:  # strong
            return self.leverage_strong
    
    def get_position_size_for_signal_strength(self, strength: Literal["normal", "good", "strong"]) -> float:
        """Get recommended position size based on signal strength"""
        if strength == "normal":
            return self.position_size_normal
        elif strength == "good":
            return self.position_size_good
        else:  # strong
            return self.position_size_strong
    
    def get_stop_loss_for_leverage(self, leverage: int) -> float:
        """Get recommended stop-loss based on leverage used"""
        leverage_mid = (self.leverage_min + self.leverage_max) / 2
        leverage_high_threshold = (self.leverage_min + self.leverage_max) * 0.75
        
        if leverage <= leverage_mid:
            return self.stop_loss_low
        elif leverage <= leverage_high_threshold:
            return self.stop_loss_mid
        else:
            return self.stop_loss_high
    
    def adjust_for_volatility(self, atr_percent: float, base_leverage: int, base_position_size: float) -> tuple[int, float]:
        """
        Adjust leverage and position size based on market volatility (ATR)
        
        Args:
            atr_percent: ATR as percentage of price
            base_leverage: Base leverage before adjustment
            base_position_size: Base position size before adjustment
            
        Returns:
            (adjusted_leverage, adjusted_position_size)
        """
        if atr_percent > 5.0:
            adjustment = self.high_volatility_adjustment
        elif atr_percent >= 2.0:
            adjustment = self.normal_volatility_adjustment
        else:
            adjustment = self.low_volatility_adjustment
        
        adjusted_leverage = int(base_leverage * adjustment.leverage_factor)
        adjusted_position_size = base_position_size * adjustment.position_factor
        
        adjusted_leverage = max(self.leverage_min, min(self.leverage_max, adjusted_leverage))
        
        adjusted_position_size = max(self.position_size_min, min(self.position_size_max, adjusted_position_size))
        
        return adjusted_leverage, adjusted_position_size


class TradingProfileManager:
    """Manages trading profiles and provides profile-specific configurations"""
    
    PROFILES: Dict[TradingProfile, ProfileConfig] = {
        TradingProfile.CONSERVATIVE: ProfileConfig(
            name="Conservative",
            description="Low risk, strict entry conditions, early profit-taking",
            
            leverage_min=3,
            leverage_max=6,
            leverage_normal=3,
            leverage_good=4,
            leverage_strong=6,
            
            position_size_min=15.0,
            position_size_max=22.0,
            position_size_normal=16.0,
            position_size_good=18.5,
            position_size_strong=21.0,
            
            stop_loss_low=-3.5,
            stop_loss_mid=-3.0,
            stop_loss_high=-2.5,
            
            trailing_stops=[
                TrailingStopLevel(trigger_profit_pct=6.0, stop_at_profit_pct=2.0),
                TrailingStopLevel(trigger_profit_pct=12.0, stop_at_profit_pct=6.0),
                TrailingStopLevel(trigger_profit_pct=20.0, stop_at_profit_pct=12.0),
            ],
            
            partial_take_profit=[
                PartialTakeProfitStage(trigger_profit_pct=20.0, close_percent=50.0),
                PartialTakeProfitStage(trigger_profit_pct=30.0, close_percent=50.0),
                PartialTakeProfitStage(trigger_profit_pct=40.0, close_percent=100.0),
            ],
            
            peak_drawdown_threshold=25.0,
            
            high_volatility_adjustment=VolatilityAdjustment(leverage_factor=0.6, position_factor=0.7),
            normal_volatility_adjustment=VolatilityAdjustment(leverage_factor=1.0, position_factor=1.0),
            low_volatility_adjustment=VolatilityAdjustment(leverage_factor=1.0, position_factor=1.0),
            
            min_timeframe_confirmations=3,
            
            risk_tolerance="Single trade risk 15-22%, strict drawdown control",
            trading_style="Cautious trading, protect capital first, miss opportunities rather than take risks",
            target_monthly_return="10-20%",
        ),
        
        TradingProfile.BALANCED: ProfileConfig(
            name="Balanced",
            description="Medium risk, moderate entry conditions, balanced profit-taking",
            
            leverage_min=6,
            leverage_max=8,
            leverage_normal=6,
            leverage_good=7,
            leverage_strong=8,
            
            position_size_min=20.0,
            position_size_max=27.0,
            position_size_normal=21.5,
            position_size_good=24.0,
            position_size_strong=26.0,
            
            stop_loss_low=-3.0,
            stop_loss_mid=-2.5,
            stop_loss_high=-2.0,
            
            trailing_stops=[
                TrailingStopLevel(trigger_profit_pct=8.0, stop_at_profit_pct=3.0),
                TrailingStopLevel(trigger_profit_pct=15.0, stop_at_profit_pct=8.0),
                TrailingStopLevel(trigger_profit_pct=25.0, stop_at_profit_pct=15.0),
            ],
            
            partial_take_profit=[
                PartialTakeProfitStage(trigger_profit_pct=30.0, close_percent=50.0),
                PartialTakeProfitStage(trigger_profit_pct=40.0, close_percent=50.0),
                PartialTakeProfitStage(trigger_profit_pct=50.0, close_percent=100.0),
            ],
            
            peak_drawdown_threshold=30.0,
            
            high_volatility_adjustment=VolatilityAdjustment(leverage_factor=0.7, position_factor=0.8),
            normal_volatility_adjustment=VolatilityAdjustment(leverage_factor=1.0, position_factor=1.0),
            low_volatility_adjustment=VolatilityAdjustment(leverage_factor=1.1, position_factor=1.0),
            
            min_timeframe_confirmations=2,
            
            risk_tolerance="Single trade risk 20-27%, balanced risk-reward",
            trading_style="Balanced approach, controlled risk-taking, steady growth",
            target_monthly_return="20-40%",
        ),
        
        TradingProfile.AGGRESSIVE: ProfileConfig(
            name="Aggressive",
            description="High risk, relaxed entry conditions, late profit-taking",
            
            leverage_min=8,
            leverage_max=10,
            leverage_normal=8,
            leverage_good=9,
            leverage_strong=10,
            
            position_size_min=25.0,
            position_size_max=32.0,
            position_size_normal=26.5,
            position_size_good=29.0,
            position_size_strong=31.0,
            
            stop_loss_low=-2.5,
            stop_loss_mid=-2.0,
            stop_loss_high=-1.5,
            
            trailing_stops=[
                TrailingStopLevel(trigger_profit_pct=10.0, stop_at_profit_pct=4.0),
                TrailingStopLevel(trigger_profit_pct=18.0, stop_at_profit_pct=10.0),
                TrailingStopLevel(trigger_profit_pct=30.0, stop_at_profit_pct=18.0),
            ],
            
            partial_take_profit=[
                PartialTakeProfitStage(trigger_profit_pct=40.0, close_percent=50.0),
                PartialTakeProfitStage(trigger_profit_pct=50.0, close_percent=50.0),
                PartialTakeProfitStage(trigger_profit_pct=60.0, close_percent=100.0),
            ],
            
            peak_drawdown_threshold=35.0,
            
            high_volatility_adjustment=VolatilityAdjustment(leverage_factor=0.8, position_factor=0.85),
            normal_volatility_adjustment=VolatilityAdjustment(leverage_factor=1.0, position_factor=1.0),
            low_volatility_adjustment=VolatilityAdjustment(leverage_factor=1.2, position_factor=1.1),
            
            min_timeframe_confirmations=2,
            
            risk_tolerance="Single trade risk 25-32%, pursue high returns",
            trading_style="Aggressive trading, quick opportunity capture, maximize returns",
            target_monthly_return="40%+",
        ),
    }
    
    def __init__(self, profile: TradingProfile = TradingProfile.BALANCED):
        """
        Initialize trading profile manager
        
        Args:
            profile: Trading profile to use (default: BALANCED)
        """
        self.profile = profile
        self.config = self.PROFILES[profile]
    
    def get_config(self) -> ProfileConfig:
        """Get current profile configuration"""
        return self.config
    
    def set_profile(self, profile: TradingProfile):
        """Change trading profile"""
        self.profile = profile
        self.config = self.PROFILES[profile]
    
    @classmethod
    def get_all_profiles(cls) -> Dict[TradingProfile, ProfileConfig]:
        """Get all available trading profiles"""
        return cls.PROFILES
    
    def __repr__(self) -> str:
        return f"TradingProfileManager(profile={self.profile.value}, name={self.config.name})"
