"""
Simple RSI Strategy

A basic RSI-based trading strategy for testing the complete trading pipeline.
- Buy when RSI < 30 (oversold)
- Sell when RSI > 70 (overbought)
"""

from typing import Dict, Any, Optional
from datetime import datetime

from .base_strategy import BaseStrategy, TradingSignal, SignalAction


class SimpleRSIStrategy(BaseStrategy):
    """
    Simple RSI strategy for testing
    
    Strategy Rules:
    - BUY when RSI < oversold_threshold (default: 30)
    - SELL when RSI > overbought_threshold (default: 70)
    - HOLD otherwise
    - Close positions when opposite signal occurs
    """
    
    def __init__(self, name: str = "SimpleRSI", config: Optional[Dict[str, Any]] = None):
        """
        Initialize Simple RSI Strategy
        
        Args:
            name: Strategy name
            config: Strategy configuration
        """
        default_config = {
            'rsi_period': 14,
            'oversold_threshold': 30,
            'overbought_threshold': 70,
            'min_confidence': 0.6,
            'stop_loss_pct': 0.02,  # 2% stop loss
            'take_profit_pct': 0.04,  # 4% take profit (2:1 risk-reward)
            'position_size': 0.1  # 10% of capital per trade
        }
        
        if config:
            default_config.update(config)
        
        super().__init__(name, default_config)
        
        self.last_rsi: Optional[float] = None
        self.last_price: Optional[float] = None
    
    def initialize(self) -> None:
        """Initialize strategy"""
        self.last_rsi = None
        self.last_price = None
        self.is_initialized = True
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        """
        Process new market data
        
        Args:
            market_data: Current market data
            indicators: Technical indicators
        """
        self.last_price = market_data.get('price', market_data.get('close'))
        self.last_rsi = indicators.get('rsi')
    
    def generate_signal(self,
                       market_data: Dict[str, Any],
                       indicators: Dict[str, Any],
                       current_position: Optional[Dict[str, Any]] = None) -> TradingSignal:
        """
        Generate trading signal based on RSI
        
        Args:
            market_data: Current market data
            indicators: Technical indicators
            current_position: Current open position (if any)
            
        Returns:
            TradingSignal with action and parameters
        """
        price = market_data.get('price', market_data.get('close'))
        rsi = indicators.get('rsi')
        symbol = market_data.get('symbol', 'UNKNOWN')
        
        action = SignalAction.HOLD
        confidence = 0.5
        metadata = {
            'strategy_name': self.name,
            'rsi': rsi,
            'price': price
        }
        
        if rsi is None:
            return TradingSignal(
                action=action,
                confidence=confidence,
                symbol=symbol,
                timestamp=datetime.now(),
                metadata={**metadata, 'reason': 'No RSI data available'},
                price=price
            )
        
        oversold = self.config['oversold_threshold']
        overbought = self.config['overbought_threshold']
        
        has_position = current_position is not None and current_position.get('quantity', 0) != 0
        position_side = current_position.get('side') if has_position else None
        
        if rsi < oversold:
            if not has_position or position_side == 'short':
                action = SignalAction.BUY
                confidence = min(0.9, 0.6 + (oversold - rsi) / oversold * 0.3)
                metadata['reason'] = f'RSI oversold ({rsi:.2f} < {oversold})'
                
                if position_side == 'short':
                    action = SignalAction.CLOSE_SHORT
                    metadata['reason'] = f'Close short - RSI oversold ({rsi:.2f})'
        
        elif rsi > overbought:
            if not has_position or position_side == 'long':
                action = SignalAction.SELL
                confidence = min(0.9, 0.6 + (rsi - overbought) / (100 - overbought) * 0.3)
                metadata['reason'] = f'RSI overbought ({rsi:.2f} > {overbought})'
                
                if position_side == 'long':
                    action = SignalAction.CLOSE_LONG
                    metadata['reason'] = f'Close long - RSI overbought ({rsi:.2f})'
        
        else:
            action = SignalAction.HOLD
            confidence = 0.5
            metadata['reason'] = f'RSI neutral ({rsi:.2f})'
        
        stop_loss = None
        take_profit = None
        
        if action in [SignalAction.BUY, SignalAction.CLOSE_SHORT]:
            stop_loss = price * (1 - self.config['stop_loss_pct'])
            take_profit = price * (1 + self.config['take_profit_pct'])
        elif action in [SignalAction.SELL, SignalAction.CLOSE_LONG]:
            stop_loss = price * (1 + self.config['stop_loss_pct'])
            take_profit = price * (1 - self.config['take_profit_pct'])
        
        signal = TradingSignal(
            action=action,
            confidence=confidence,
            symbol=symbol,
            timestamp=datetime.now(),
            metadata=metadata,
            price=price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=self.config['position_size']
        )
        
        return signal
    
    def get_parameters(self) -> Dict[str, Any]:
        """
        Get strategy parameters
        
        Returns:
            Dictionary of strategy parameters
        """
        return {
            'rsi_period': self.config['rsi_period'],
            'oversold_threshold': self.config['oversold_threshold'],
            'overbought_threshold': self.config['overbought_threshold'],
            'min_confidence': self.config['min_confidence'],
            'stop_loss_pct': self.config['stop_loss_pct'],
            'take_profit_pct': self.config['take_profit_pct'],
            'position_size': self.config['position_size'],
            'last_rsi': self.last_rsi,
            'last_price': self.last_price
        }
