"""
Strategy Manager

Orchestrates multiple trading strategies, routes market data, and aggregates signals.
Supports hot-swapping and lifecycle management of strategies.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
from loguru import logger

from .base_strategy import BaseStrategy, TradingSignal, SignalAction


class StrategyManager:
    """
    Manages multiple trading strategies
    
    Responsibilities:
    - Load and initialize strategies
    - Route market data to strategies
    - Aggregate signals from multiple strategies
    - Support hot-swapping of strategies
    - Manage strategy lifecycle (start, stop, pause)
    """
    
    def __init__(self):
        """Initialize strategy manager"""
        self.strategies: Dict[str, BaseStrategy] = {}
        self.active_strategies: Dict[str, bool] = {}
        self.strategy_weights: Dict[str, float] = {}
        
    def register_strategy(self, strategy: BaseStrategy, weight: float = 1.0) -> None:
        """
        Register a new strategy
        
        Args:
            strategy: Strategy instance to register
            weight: Weight for signal aggregation (default: 1.0)
        """
        if strategy.name in self.strategies:
            logger.warning(f"Strategy '{strategy.name}' already registered, replacing")
        
        self.strategies[strategy.name] = strategy
        self.active_strategies[strategy.name] = False
        self.strategy_weights[strategy.name] = weight
        
        logger.info(f"Registered strategy: {strategy.name} (weight: {weight})")
    
    def unregister_strategy(self, strategy_name: str) -> None:
        """
        Unregister a strategy
        
        Args:
            strategy_name: Name of strategy to unregister
        """
        if strategy_name not in self.strategies:
            logger.warning(f"Strategy '{strategy_name}' not found")
            return
        
        if self.active_strategies.get(strategy_name):
            self.stop_strategy(strategy_name)
        
        del self.strategies[strategy_name]
        del self.active_strategies[strategy_name]
        del self.strategy_weights[strategy_name]
        
        logger.info(f"Unregistered strategy: {strategy_name}")
    
    def start_strategy(self, strategy_name: str) -> bool:
        """
        Start a strategy
        
        Args:
            strategy_name: Name of strategy to start
            
        Returns:
            True if started successfully, False otherwise
        """
        if strategy_name not in self.strategies:
            logger.error(f"Strategy '{strategy_name}' not found")
            return False
        
        strategy = self.strategies[strategy_name]
        
        if not strategy.is_initialized:
            try:
                strategy.initialize()
                strategy.is_initialized = True
                logger.info(f"Initialized strategy: {strategy_name}")
            except Exception as e:
                logger.error(f"Failed to initialize strategy '{strategy_name}': {e}")
                return False
        
        self.active_strategies[strategy_name] = True
        logger.info(f"Started strategy: {strategy_name}")
        return True
    
    def stop_strategy(self, strategy_name: str) -> bool:
        """
        Stop a strategy
        
        Args:
            strategy_name: Name of strategy to stop
            
        Returns:
            True if stopped successfully, False otherwise
        """
        if strategy_name not in self.strategies:
            logger.error(f"Strategy '{strategy_name}' not found")
            return False
        
        self.active_strategies[strategy_name] = False
        logger.info(f"Stopped strategy: {strategy_name}")
        return True
    
    def start_all(self) -> None:
        """Start all registered strategies"""
        for strategy_name in self.strategies:
            self.start_strategy(strategy_name)
    
    def stop_all(self) -> None:
        """Stop all active strategies"""
        for strategy_name in list(self.active_strategies.keys()):
            if self.active_strategies[strategy_name]:
                self.stop_strategy(strategy_name)
    
    def process_data(self, 
                     symbol: str,
                     market_data: Dict[str, Any], 
                     indicators: Dict[str, Any]) -> None:
        """
        Process market data through all active strategies
        
        Args:
            symbol: Trading pair symbol
            market_data: Current market data
            indicators: Technical indicators
        """
        for strategy_name, is_active in self.active_strategies.items():
            if not is_active:
                continue
            
            strategy = self.strategies[strategy_name]
            
            try:
                strategy.on_data(market_data, indicators)
            except Exception as e:
                logger.error(f"Error processing data in strategy '{strategy_name}': {e}")
    
    def generate_signals(self,
                        symbol: str,
                        market_data: Dict[str, Any],
                        indicators: Dict[str, Any],
                        current_position: Optional[Dict[str, Any]] = None) -> List[TradingSignal]:
        """
        Generate signals from all active strategies
        
        Args:
            symbol: Trading pair symbol
            market_data: Current market data
            indicators: Technical indicators
            current_position: Current open position (if any)
            
        Returns:
            List of trading signals from all active strategies
        """
        signals = []
        
        for strategy_name, is_active in self.active_strategies.items():
            if not is_active:
                continue
            
            strategy = self.strategies[strategy_name]
            
            try:
                signal = strategy.generate_signal(market_data, indicators, current_position)
                strategy.record_signal(signal)
                signals.append(signal)
                
                logger.debug(f"Strategy '{strategy_name}' generated signal: {signal.action.value} "
                           f"(confidence: {signal.confidence:.2f})")
            except Exception as e:
                logger.error(f"Error generating signal in strategy '{strategy_name}': {e}")
        
        return signals
    
    def aggregate_signals(self, signals: List[TradingSignal]) -> Optional[TradingSignal]:
        """
        Aggregate multiple signals into a single signal
        
        Uses weighted voting based on strategy weights and confidence levels.
        
        Args:
            signals: List of trading signals to aggregate
            
        Returns:
            Aggregated trading signal or None if no clear consensus
        """
        if not signals:
            return None
        
        if len(signals) == 1:
            return signals[0]
        
        action_votes: Dict[SignalAction, float] = {
            SignalAction.BUY: 0.0,
            SignalAction.SELL: 0.0,
            SignalAction.HOLD: 0.0,
            SignalAction.CLOSE_LONG: 0.0,
            SignalAction.CLOSE_SHORT: 0.0
        }
        
        total_weight = 0.0
        metadata_list = []
        
        for signal in signals:
            strategy_name = signal.metadata.get('strategy_name', 'unknown')
            weight = self.strategy_weights.get(strategy_name, 1.0)
            
            vote_weight = signal.confidence * weight
            action_votes[signal.action] += vote_weight
            total_weight += weight
            
            metadata_list.append({
                'strategy': strategy_name,
                'action': signal.action.value,
                'confidence': signal.confidence,
                'weight': weight
            })
        
        winning_action = max(action_votes.items(), key=lambda x: x[1])
        action, vote_score = winning_action
        
        aggregated_confidence = vote_score / total_weight if total_weight > 0 else 0.0
        
        template_signal = signals[0]
        
        aggregated_signal = TradingSignal(
            action=action,
            confidence=aggregated_confidence,
            symbol=template_signal.symbol,
            timestamp=datetime.now(),
            metadata={
                'aggregated': True,
                'num_signals': len(signals),
                'individual_signals': metadata_list,
                'vote_distribution': {k.value: v for k, v in action_votes.items()}
            },
            price=template_signal.price,
            stop_loss=template_signal.stop_loss,
            take_profit=template_signal.take_profit,
            position_size=template_signal.position_size
        )
        
        logger.info(f"Aggregated {len(signals)} signals: {action.value} "
                   f"(confidence: {aggregated_confidence:.2f})")
        
        return aggregated_signal
    
    def get_strategy_status(self) -> Dict[str, Any]:
        """
        Get status of all strategies
        
        Returns:
            Dictionary with strategy status information
        """
        status = {}
        
        for strategy_name, strategy in self.strategies.items():
            status[strategy_name] = {
                'active': self.active_strategies[strategy_name],
                'initialized': strategy.is_initialized,
                'weight': self.strategy_weights[strategy_name],
                'last_signal': strategy.last_signal.action.value if strategy.last_signal else None,
                'signal_count': len(strategy.signal_history),
                'parameters': strategy.get_parameters()
            }
        
        return status
    
    def update_strategy_weight(self, strategy_name: str, weight: float) -> bool:
        """
        Update strategy weight for signal aggregation
        
        Args:
            strategy_name: Name of strategy
            weight: New weight value
            
        Returns:
            True if updated successfully, False otherwise
        """
        if strategy_name not in self.strategies:
            logger.error(f"Strategy '{strategy_name}' not found")
            return False
        
        if weight < 0:
            logger.error(f"Weight must be non-negative, got {weight}")
            return False
        
        self.strategy_weights[strategy_name] = weight
        logger.info(f"Updated weight for strategy '{strategy_name}': {weight}")
        return True
    
    def get_active_strategies(self) -> List[str]:
        """
        Get list of active strategy names
        
        Returns:
            List of active strategy names
        """
        return [name for name, active in self.active_strategies.items() if active]
    
    def reset_all(self) -> None:
        """Reset all strategies"""
        for strategy in self.strategies.values():
            strategy.reset()
        logger.info("Reset all strategies")
    
    
    def allocate_capital(
        self,
        total_capital: float,
        market_regime: str,
        strategy_performance: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Allocate capital across strategies based on market regime and performance
        
        Args:
            total_capital: Total capital to allocate
            market_regime: Current market regime ('high_volatility', 'trending', 'sideways')
            strategy_performance: Dict of strategy names to recent performance scores
        
        Returns:
            Dict of strategy names to allocated capital amounts
        """
        regime_preferences = {
            'high_volatility': {
                'mean_reversion': 0.5,
                'scalping': 0.3,
                'momentum': 0.2
            },
            'trending': {
                'momentum': 0.6,
                'scalping': 0.2,
                'mean_reversion': 0.2
            },
            'sideways': {
                'scalping': 0.5,
                'mean_reversion': 0.3,
                'momentum': 0.2
            }
        }
        
        preferences = regime_preferences.get(market_regime, {})
        
        allocations = {}
        total_weight = 0.0
        
        for strategy_name in self.strategies:
            base_allocation = preferences.get(strategy_name, 0.25)
            
            performance = strategy_performance.get(strategy_name, 0.0)
            performance_multiplier = 0.5 + min(1.0, max(0.0, performance))
            
            weight = base_allocation * performance_multiplier
            allocations[strategy_name] = weight
            total_weight += weight
        
        if total_weight > 0:
            for strategy_name in allocations:
                allocations[strategy_name] = (allocations[strategy_name] / total_weight) * total_capital
        
        logger.info(f"Capital allocation for {market_regime} regime: {allocations}")
        return allocations
    
    def detect_market_regime(self, indicators: Dict[str, Any]) -> str:
        """
        Detect current market regime
        
        Args:
            indicators: Technical indicators
        
        Returns:
            Market regime: 'high_volatility', 'trending', or 'sideways'
        """
        # Get key indicators
        atr = indicators.get('atr', 0)
        price = indicators.get('price', 1)
        adx = indicators.get('adx', 0)
        bb_width = indicators.get('bb_width', 0)
        
        volatility_pct = (atr / price) * 100 if price > 0 else 0
        
        if volatility_pct > 3.0 or bb_width > 0.05:
            regime = 'high_volatility'
        elif adx > 25:
            regime = 'trending'
        else:
            regime = 'sideways'
        
        logger.debug(f"Market regime detected: {regime} (volatility={volatility_pct:.2f}%, ADX={adx:.1f})")
        return regime
    
    def check_combined_exposure(
        self,
        proposed_trades: List[Dict[str, Any]],
        current_positions: List[Dict[str, Any]],
        max_exposure_pct: float = 30.0
    ) -> tuple[bool, str]:
        """
        Check if combined exposure from all strategies is within limits
        
        Args:
            proposed_trades: List of proposed trades from strategies
            current_positions: List of current open positions
            max_exposure_pct: Maximum total exposure percentage
        
        Returns:
            Tuple of (approved, reason)
        """
        current_exposure = sum(
            abs(pos.get('size', 0) * pos.get('price', 0))
            for pos in current_positions
        )
        
        proposed_exposure = sum(
            abs(trade.get('size', 0) * trade.get('price', 0))
            for trade in proposed_trades
        )
        
        total_exposure = current_exposure + proposed_exposure
        
        exposure_pct = (total_exposure / 100) * 100
        
        if exposure_pct > max_exposure_pct:
            return False, f"Combined exposure {exposure_pct:.1f}% exceeds limit {max_exposure_pct:.1f}%"
        
        return True, f"Combined exposure {exposure_pct:.1f}% within limits"
    
    def select_strategies_for_regime(
        self,
        market_regime: str,
        available_strategies: List[str]
    ) -> List[str]:
        """
        Select optimal strategies for current market regime
        
        Args:
            market_regime: Current market regime
            available_strategies: List of available strategy names
        
        Returns:
            List of strategy names to activate
        """
        regime_strategies = {
            'high_volatility': ['mean_reversion', 'scalping'],
            'trending': ['momentum', 'scalping'],
            'sideways': ['scalping', 'mean_reversion']
        }
        
        preferred = regime_strategies.get(market_regime, available_strategies)
        
        # Filter to only available strategies
        selected = [s for s in preferred if s in available_strategies]
        
        if not selected:
            selected = available_strategies
        
        logger.info(f"Selected strategies for {market_regime} regime: {selected}")
        return selected
    
    def activate_strategies_for_regime(self, market_regime: str) -> None:
        """
        Activate optimal strategies for current market regime
        
        Args:
            market_regime: Current market regime
        """
        # Get available strategies
        available = list(self.strategies.keys())
        
        selected = self.select_strategies_for_regime(market_regime, available)
        
        self.stop_all()
        
        # Start selected strategies
        for strategy_name in selected:
            if strategy_name in self.strategies:
                self.start_strategy(strategy_name)
        
        logger.info(f"Activated {len(selected)} strategies for {market_regime} regime")
