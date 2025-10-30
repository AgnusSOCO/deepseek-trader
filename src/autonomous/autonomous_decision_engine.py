"""
Autonomous Decision Engine

Main engine for autonomous trading with zero human interaction.
Runs continuous 2-3 minute loops to:
1. Fetch market data
2. Generate signals from all strategies
3. Make trading decisions based on confidence
4. Execute trades
5. Monitor open positions
6. Enforce exit plans

This is the core of the autonomous trading system.
"""

import logging
import time
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import uuid

from src.autonomous.exit_plan_monitor import ExitPlanMonitor, ExitPlan, ExitReason
from src.autonomous.enhanced_risk_manager import EnhancedRiskManager
from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction
from src.data.price_feed import PriceFeed

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Open trading position"""
    position_id: str
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    quantity: float
    leverage: float
    entry_time: datetime
    strategy_name: str
    confidence: float
    metadata: Dict[str, Any]


@dataclass
class DecisionLog:
    """Log entry for a trading decision"""
    timestamp: datetime
    decision_type: str  # 'ENTRY', 'EXIT', 'HOLD', 'SKIP'
    symbol: str
    action: str
    confidence: float
    justification: str
    strategy_name: str
    price: float
    metadata: Dict[str, Any]


class AutonomousDecisionEngine:
    """
    Main autonomous trading engine.
    
    Runs continuous loops to make trading decisions without human intervention.
    """
    
    def __init__(
        self,
        strategies: List[BaseStrategy],
        exit_monitor: ExitPlanMonitor,
        risk_manager: EnhancedRiskManager,
        price_feed: PriceFeed,
        loop_interval_seconds: int = 180,  # 3 minutes
        max_open_positions: int = 5,
        min_confidence_threshold: float = 0.7,
        enable_trading: bool = False,  # Safety: disabled by default
    ):
        """
        Initialize autonomous decision engine
        
        Args:
            strategies: List of trading strategies to use
            exit_monitor: Exit plan monitor instance
            risk_manager: Enhanced risk manager instance
            price_feed: Real-time price feed service
            loop_interval_seconds: Time between decision loops (default 180s = 3min)
            max_open_positions: Maximum number of concurrent positions
            min_confidence_threshold: Minimum confidence to enter trades
            enable_trading: Whether to actually execute trades (safety flag)
        """
        self.strategies = strategies
        self.exit_monitor = exit_monitor
        self.risk_manager = risk_manager
        self.price_feed = price_feed
        self.loop_interval_seconds = loop_interval_seconds
        self.max_open_positions = max_open_positions
        self.min_confidence_threshold = min_confidence_threshold
        self.enable_trading = enable_trading
        
        self.is_running = False
        self.open_positions: Dict[str, Position] = {}
        self.decision_log: List[DecisionLog] = []
        self.last_loop_time: Optional[datetime] = None
        self.total_loops = 0
        self.total_decisions = 0
        
        logger.info(
            f"AutonomousDecisionEngine initialized: "
            f"{len(strategies)} strategies, "
            f"loop interval: {loop_interval_seconds}s, "
            f"max positions: {max_open_positions}, "
            f"min confidence: {min_confidence_threshold}, "
            f"trading enabled: {enable_trading}"
        )
    
    async def start(self) -> None:
        """Start the autonomous trading loop"""
        if self.is_running:
            logger.warning("Engine already running")
            return
        
        self.is_running = True
        logger.info("🚀 Starting autonomous trading engine...")
        
        if not self.enable_trading:
            logger.warning("⚠️  TRADING DISABLED - Running in simulation mode only")
        
        try:
            while self.is_running:
                loop_start = datetime.now()
                
                try:
                    await self._run_decision_loop()
                except Exception as e:
                    logger.error(f"Error in decision loop: {e}", exc_info=True)
                
                loop_duration = (datetime.now() - loop_start).total_seconds()
                sleep_time = max(0, self.loop_interval_seconds - loop_duration)
                
                if sleep_time > 0:
                    logger.info(f"💤 Sleeping for {sleep_time:.1f}s until next loop...")
                    await asyncio.sleep(sleep_time)
                else:
                    logger.warning(
                        f"⚠️  Loop took {loop_duration:.1f}s, "
                        f"longer than interval {self.loop_interval_seconds}s"
                    )
        
        except KeyboardInterrupt:
            logger.info("Received interrupt signal, stopping...")
        finally:
            self.is_running = False
            logger.info("Autonomous trading engine stopped")
    
    def stop(self) -> None:
        """Stop the autonomous trading loop"""
        logger.info("Stopping autonomous trading engine...")
        self.is_running = False
    
    async def _run_decision_loop(self) -> None:
        """Run one iteration of the decision loop"""
        self.total_loops += 1
        self.last_loop_time = datetime.now()
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔄 Decision Loop #{self.total_loops} - {self.last_loop_time}")
        logger.info(f"{'='*80}")
        
        if not self.risk_manager.can_trade_today():
            logger.warning("🛑 Daily loss limit reached - no new trades today")
            self._log_decision(
                decision_type='SKIP',
                symbol='ALL',
                action='HOLD',
                confidence=0.0,
                justification='Daily loss limit reached',
                strategy_name='RiskManager',
                price=0.0,
                metadata={}
            )
            return
        
        await self._monitor_exit_conditions()
        
        if len(self.open_positions) >= self.max_open_positions:
            logger.info(
                f"📊 Max positions reached ({len(self.open_positions)}/{self.max_open_positions})"
            )
            return
        
        signals = await self._generate_signals_from_all_strategies()
        
        best_signal = self._select_best_signal(signals)
        
        if best_signal:
            await self._execute_signal(best_signal)
        else:
            logger.info("📊 No signals meet criteria - holding")
        
        self._log_statistics()
    
    async def _monitor_exit_conditions(self) -> None:
        """Monitor all open positions and exit if conditions met"""
        if not self.open_positions:
            return
        
        logger.info(f"👀 Monitoring {len(self.open_positions)} open positions...")
        
        positions_to_close = []
        
        for position_id, position in self.open_positions.items():
            current_price = self.price_feed.get_latest_price(position.symbol)
            
            timeframe = position.metadata.get('timeframe', '1h')
            indicators = self.price_feed.get_indicators(position.symbol, timeframe)
            
            market_data = {
                'symbol': position.symbol,
                'price': current_price,
                'timestamp': datetime.now(),
                'timeframe': timeframe
            }
            
            exit_signal = self.exit_monitor.check_exit_conditions(
                position_id,
                current_price,
                market_data,
                indicators
            )
            
            if exit_signal and exit_signal['should_exit']:
                positions_to_close.append((position, exit_signal))
        
        for position, exit_signal in positions_to_close:
            await self._close_position(position, exit_signal)
    
    async def _close_position(
        self,
        position: Position,
        exit_signal: Dict[str, Any]
    ) -> None:
        """
        Close a position
        
        Args:
            position: Position to close
            exit_signal: Exit signal with reason and details
        """
        exit_price = exit_signal['price']
        
        if position.side == 'long':
            pnl_pct = (exit_price - position.entry_price) / position.entry_price * 100
        else:
            pnl_pct = (position.entry_price - exit_price) / position.entry_price * 100
        
        pnl_amount = position.quantity * (exit_price - position.entry_price) * position.leverage
        
        logger.info(
            f"🔴 Closing {position.side} position {position.position_id}: "
            f"{position.symbol} @ ${exit_price:.2f}, "
            f"P&L: {pnl_pct:.2f}% (${pnl_amount:.2f}), "
            f"Reason: {exit_signal['reason'].value}"
        )
        
        self.exit_monitor.record_exit(
            position.position_id,
            exit_signal['reason'],
            exit_price,
            pnl_amount,
            exit_signal['details']
        )
        
        self.risk_manager.record_trade_result(pnl_amount, pnl_pct)
        
        self._log_decision(
            decision_type='EXIT',
            symbol=position.symbol,
            action='CLOSE',
            confidence=1.0,
            justification=exit_signal['details'],
            strategy_name=position.strategy_name,
            price=exit_price,
            metadata={
                'position_id': position.position_id,
                'entry_price': position.entry_price,
                'pnl_pct': pnl_pct,
                'pnl_amount': pnl_amount,
                'exit_reason': exit_signal['reason'].value
            }
        )
        
        del self.open_positions[position.position_id]
        self.exit_monitor.remove_exit_plan(position.position_id)
    
    async def _generate_signals_from_all_strategies(self) -> List[TradingSignal]:
        """
        Generate signals from all strategies
        
        Returns:
            List of trading signals
        """
        signals = []
        
        logger.info(f"📡 Generating signals from {len(self.strategies)} strategies...")
        
        for strategy in self.strategies:
            try:
                symbol = getattr(strategy, 'symbol', 'BTC/USDT')
                timeframe = getattr(strategy, 'timeframe', '1h')
                
                current_price = self.price_feed.get_latest_price(symbol)
                
                if current_price == 0:
                    logger.warning(f"No price data for {symbol}, skipping {strategy.name}")
                    continue
                
                indicators = self.price_feed.get_indicators(symbol, timeframe)
                latest_candle = self.price_feed.get_latest_candle(symbol, timeframe)
                
                market_data = {
                    'symbol': symbol,
                    'price': current_price,
                    'timestamp': datetime.now(),
                    'timeframe': timeframe,
                    'volume': latest_candle['volume'] if latest_candle else 0.0,
                    'open': latest_candle['open'] if latest_candle else current_price,
                    'high': latest_candle['high'] if latest_candle else current_price,
                    'low': latest_candle['low'] if latest_candle else current_price,
                    'close': latest_candle['close'] if latest_candle else current_price
                }
                
                has_position = any(
                    p.symbol == symbol for p in self.open_positions.values()
                )
                
                current_position = None
                if has_position:
                    current_position = {'symbol': symbol}
                
                signal = strategy.generate_signal(
                    market_data,
                    indicators,
                    current_position
                )
                
                if signal.action != SignalAction.HOLD:
                    signals.append(signal)
                    logger.info(
                        f"  ✓ {strategy.name}: {signal.action.value} "
                        f"confidence={signal.confidence:.2f} @ ${current_price:.2f}"
                    )
            
            except Exception as e:
                logger.error(f"Error generating signal from {strategy.name}: {e}")
        
        logger.info(f"📊 Generated {len(signals)} non-HOLD signals")
        return signals
    
    def _select_best_signal(
        self,
        signals: List[TradingSignal]
    ) -> Optional[TradingSignal]:
        """
        Select the best signal based on confidence
        
        Args:
            signals: List of trading signals
            
        Returns:
            Best signal or None
        """
        if not signals:
            return None
        
        valid_signals = [
            s for s in signals
            if s.confidence >= self.min_confidence_threshold
        ]
        
        if not valid_signals:
            logger.info(
                f"📊 No signals meet minimum confidence threshold "
                f"({self.min_confidence_threshold})"
            )
            return None
        
        valid_signals.sort(key=lambda s: s.confidence, reverse=True)
        
        best_signal = valid_signals[0]
        
        logger.info(
            f"🎯 Best signal: {best_signal.symbol} {best_signal.action.value} "
            f"confidence={best_signal.confidence:.2f} "
            f"from {best_signal.metadata.get('strategy', 'unknown')}"
        )
        
        return best_signal
    
    async def _execute_signal(self, signal: TradingSignal) -> None:
        """
        Execute a trading signal
        
        Args:
            signal: Trading signal to execute
        """
        self.total_decisions += 1
        
        if not self.risk_manager.can_open_position(signal.symbol):
            logger.warning(
                f"⚠️  Risk manager rejected trade for {signal.symbol}"
            )
            self._log_decision(
                decision_type='SKIP',
                symbol=signal.symbol,
                action=signal.action.value,
                confidence=signal.confidence,
                justification='Risk manager rejected',
                strategy_name=signal.metadata.get('strategy', 'unknown'),
                price=signal.price,
                metadata=signal.metadata
            )
            return
        
        position_size = self.risk_manager.calculate_position_size(
            signal.confidence,
            signal.price
        )
        
        if position_size <= 0:
            logger.warning("⚠️  Position size too small, skipping trade")
            return
        
        position_id = str(uuid.uuid4())
        
        position = Position(
            position_id=position_id,
            symbol=signal.symbol,
            side='long' if signal.action == SignalAction.BUY else 'short',
            entry_price=signal.price,
            quantity=position_size,
            leverage=signal.metadata.get('leverage', 1.0),
            entry_time=datetime.now(),
            strategy_name=signal.metadata.get('strategy', 'unknown'),
            confidence=signal.confidence,
            metadata=signal.metadata
        )
        
        exit_plan = ExitPlan(
            position_id=position_id,
            symbol=signal.symbol,
            entry_price=signal.price,
            stop_loss=signal.stop_loss or signal.price * 0.95,
            take_profit=signal.take_profit or signal.price * 1.05,
            invalidation_conditions=signal.metadata.get('invalidation_conditions', []),
            trailing_stop_pct=signal.metadata.get('trailing_stop_pct'),
            trailing_offset_pct=signal.metadata.get('trailing_offset_pct'),
            is_short=(signal.action == SignalAction.SELL),
            metadata=signal.metadata
        )
        
        if self.enable_trading:
            logger.info(
                f"🟢 EXECUTING TRADE: {position.side.upper()} {position.symbol} "
                f"@ ${position.entry_price:.2f}, "
                f"qty={position.quantity:.4f}, "
                f"leverage={position.leverage}x, "
                f"confidence={position.confidence:.2f}"
            )
            
            self.open_positions[position_id] = position
            self.exit_monitor.add_exit_plan(exit_plan)
            
            self.risk_manager.record_position_opened(signal.symbol, position_size)
        else:
            logger.info(
                f"📝 SIMULATED TRADE: {position.side.upper()} {position.symbol} "
                f"@ ${position.entry_price:.2f}, "
                f"qty={position.quantity:.4f}, "
                f"leverage={position.leverage}x, "
                f"confidence={position.confidence:.2f}"
            )
        
        self._log_decision(
            decision_type='ENTRY',
            symbol=signal.symbol,
            action=signal.action.value,
            confidence=signal.confidence,
            justification=signal.metadata.get('justification', 'No justification provided'),
            strategy_name=signal.metadata.get('strategy', 'unknown'),
            price=signal.price,
            metadata={
                'position_id': position_id,
                'position_size': position_size,
                'stop_loss': exit_plan.stop_loss,
                'take_profit': exit_plan.take_profit,
                'leverage': position.leverage
            }
        )
    
    def _log_decision(
        self,
        decision_type: str,
        symbol: str,
        action: str,
        confidence: float,
        justification: str,
        strategy_name: str,
        price: float,
        metadata: Dict[str, Any]
    ) -> None:
        """Log a trading decision"""
        decision = DecisionLog(
            timestamp=datetime.now(),
            decision_type=decision_type,
            symbol=symbol,
            action=action,
            confidence=confidence,
            justification=justification,
            strategy_name=strategy_name,
            price=price,
            metadata=metadata
        )
        
        self.decision_log.append(decision)
        
        if len(self.decision_log) > 10000:
            self.decision_log = self.decision_log[-10000:]
    
    def _log_statistics(self) -> None:
        """Log current statistics"""
        logger.info(f"\n{'='*80}")
        logger.info("📊 Current Statistics:")
        logger.info(f"  Open Positions: {len(self.open_positions)}/{self.max_open_positions}")
        logger.info(f"  Total Loops: {self.total_loops}")
        logger.info(f"  Total Decisions: {self.total_decisions}")
        
        risk_stats = self.risk_manager.get_statistics()
        logger.info(f"  Daily P&L: ${risk_stats['daily_pnl']:.2f}")
        logger.info(f"  Daily Trades: {risk_stats['daily_trades']}")
        logger.info(f"  Can Trade: {risk_stats['can_trade_today']}")
        
        exit_stats = self.exit_monitor.get_exit_statistics()
        logger.info(f"  Total Exits: {exit_stats['total_exits']}")
        if exit_stats['total_exits'] > 0:
            logger.info(f"  Stop Loss Exits: {exit_stats['stop_loss_pct']:.1f}%")
            logger.info(f"  Take Profit Exits: {exit_stats['take_profit_pct']:.1f}%")
        
        logger.info(f"{'='*80}\n")
    
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            'is_running': self.is_running,
            'total_loops': self.total_loops,
            'total_decisions': self.total_decisions,
            'open_positions': len(self.open_positions),
            'max_open_positions': self.max_open_positions,
            'last_loop_time': self.last_loop_time,
            'enable_trading': self.enable_trading,
            'decision_log_size': len(self.decision_log)
        }
