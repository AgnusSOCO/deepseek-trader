"""
Backtest Engine

Comprehensive backtesting framework for strategy validation.
Integrates with existing strategies and provides realistic simulation.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

from ..strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction
from ..data.indicators import TechnicalIndicators

logger = logging.getLogger(__name__)


@dataclass
class Trade:
    """Represents a completed trade"""
    entry_time: datetime
    exit_time: datetime
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    exit_price: float
    size: float
    leverage: float
    pnl: float
    pnl_pct: float
    fees: float
    duration_minutes: float
    exit_reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Position:
    """Represents an open position"""
    entry_time: datetime
    symbol: str
    side: str
    entry_price: float
    size: float
    leverage: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BacktestEngine:
    """
    Backtesting engine for strategy validation
    
    Features:
    - Realistic slippage modeling
    - Fee inclusion (maker/taker)
    - No look-ahead bias prevention
    - Multiple timeframe support
    - Position tracking
    - Trade logging
    """
    
    def __init__(
        self,
        initial_capital: float = 10000.0,
        maker_fee: float = 0.0002,  # 0.02%
        taker_fee: float = 0.0005,  # 0.05%
        slippage_pct: float = 0.0005,  # 0.05%
        max_positions: int = 3
    ):
        """
        Initialize backtest engine
        
        Args:
            initial_capital: Starting capital in USDT
            maker_fee: Maker fee percentage
            taker_fee: Taker fee percentage
            slippage_pct: Slippage percentage
            max_positions: Maximum concurrent positions
        """
        self.initial_capital = initial_capital
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage_pct = slippage_pct
        self.max_positions = max_positions
        
        self.capital = initial_capital
        self.positions: List[Position] = []
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        
        logger.info(
            f"BacktestEngine initialized: capital=${initial_capital}, "
            f"maker_fee={maker_fee:.4f}, taker_fee={taker_fee:.4f}, "
            f"slippage={slippage_pct:.4f}"
        )
    
    def run_backtest(
        self,
        strategy: BaseStrategy,
        data: pd.DataFrame,
        symbol: str = 'BTC/USDT'
    ) -> Dict[str, Any]:
        """
        Run backtest for a strategy on historical data
        
        Args:
            strategy: Strategy instance to backtest
            data: Historical OHLCV data with indicators
            symbol: Trading pair symbol
        
        Returns:
            Dict with backtest results and metrics
        """
        logger.info(f"Starting backtest for {strategy.name} on {symbol}")
        logger.info(f"Data period: {data.index[0]} to {data.index[-1]} ({len(data)} bars)")
        
        self.capital = self.initial_capital
        self.positions = []
        self.trades = []
        self.equity_curve = []
        
        if not strategy.is_initialized:
            strategy.initialize()
        
        for i in range(len(data)):
            timestamp = data.index[i]
            current_bar = data.iloc[i]
            
            market_data = {
                'symbol': symbol,
                'price': current_bar['close'],
                'timestamp': timestamp,
                'volume': current_bar['volume'],
                'open': current_bar['open'],
                'high': current_bar['high'],
                'low': current_bar['low']
            }
            
            indicators = {
                col: current_bar[col]
                for col in data.columns
                if col not in ['open', 'high', 'low', 'close', 'volume']
            }
            indicators['price'] = current_bar['close']
            
            self._update_positions(timestamp, current_bar)
            
            if len(self.positions) < self.max_positions:
                signal = strategy.generate_signal(market_data, indicators)
                
                if signal.action in [SignalAction.BUY, SignalAction.SELL]:
                    self._open_position(signal, timestamp, current_bar)
            
            equity = self._calculate_equity(current_bar['close'])
            self.equity_curve.append((timestamp, equity))
        
        if self.positions:
            final_bar = data.iloc[-1]
            for position in self.positions[:]:
                self._close_position(
                    position,
                    data.index[-1],
                    final_bar['close'],
                    'backtest_end'
                )
        
        results = self._calculate_results()
        
        logger.info(
            f"Backtest complete: {len(self.trades)} trades, "
            f"Final equity: ${results['final_equity']:.2f}, "
            f"Return: {results['total_return_pct']:.2f}%"
        )
        
        return results
    
    def _open_position(
        self,
        signal: TradingSignal,
        timestamp: datetime,
        current_bar: pd.Series
    ):
        """Open a new position based on signal"""
        if signal.action == SignalAction.BUY:
            entry_price = current_bar['close'] * (1 + self.slippage_pct)
            side = 'long'
        else:  # SELL
            entry_price = current_bar['close'] * (1 - self.slippage_pct)
            side = 'short'
        
        position_size_pct = signal.position_size if signal.position_size else 0.1
        leverage = signal.metadata.get('leverage', 1.0)
        
        available_capital = self.capital * position_size_pct
        position_value = available_capital * leverage
        size = position_value / entry_price
        
        fees = position_value * self.taker_fee
        
        if fees > self.capital * 0.5:  # Don't use more than 50% capital on fees
            logger.warning(f"Insufficient capital for position, skipping")
            return
        
        self.capital -= fees
        
        position = Position(
            entry_time=timestamp,
            symbol=signal.symbol,
            side=side,
            entry_price=entry_price,
            size=size,
            leverage=leverage,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            metadata={
                'strategy': signal.metadata.get('strategy', 'unknown'),
                'confidence': signal.confidence,
                'entry_fees': fees
            }
        )
        
        self.positions.append(position)
        
        logger.debug(
            f"Opened {side} position: {size:.6f} @ ${entry_price:.2f}, "
            f"leverage={leverage:.1f}x, fees=${fees:.2f}"
        )
    
    def _update_positions(self, timestamp: datetime, current_bar: pd.Series):
        """Update positions and check stop-loss/take-profit"""
        current_price = current_bar['close']
        
        for position in self.positions[:]:  # Copy list to allow removal
            if position.stop_loss:
                if position.side == 'long' and current_price <= position.stop_loss:
                    self._close_position(position, timestamp, position.stop_loss, 'stop_loss')
                    continue
                elif position.side == 'short' and current_price >= position.stop_loss:
                    self._close_position(position, timestamp, position.stop_loss, 'stop_loss')
                    continue
            
            if position.take_profit:
                if position.side == 'long' and current_price >= position.take_profit:
                    self._close_position(position, timestamp, position.take_profit, 'take_profit')
                    continue
                elif position.side == 'short' and current_price <= position.take_profit:
                    self._close_position(position, timestamp, position.take_profit, 'take_profit')
                    continue
    
    def _close_position(
        self,
        position: Position,
        timestamp: datetime,
        exit_price: float,
        exit_reason: str
    ):
        """Close a position and record trade"""
        if position.side == 'long':
            exit_price = exit_price * (1 - self.slippage_pct)
        else:
            exit_price = exit_price * (1 + self.slippage_pct)
        
        position_value = position.size * position.entry_price
        exit_value = position.size * exit_price
        
        if position.side == 'long':
            pnl_before_fees = (exit_value - position_value) * position.leverage
        else:  # short
            pnl_before_fees = (position_value - exit_value) * position.leverage
        
        exit_fees = exit_value * self.taker_fee
        
        entry_fees = position.metadata.get('entry_fees', 0)
        total_fees = entry_fees + exit_fees
        
        pnl = pnl_before_fees - exit_fees
        pnl_pct = (pnl / (position_value / position.leverage)) * 100
        
        self.capital += pnl
        
        duration = (timestamp - position.entry_time).total_seconds() / 60
        
        trade = Trade(
            entry_time=position.entry_time,
            exit_time=timestamp,
            symbol=position.symbol,
            side=position.side,
            entry_price=position.entry_price,
            exit_price=exit_price,
            size=position.size,
            leverage=position.leverage,
            pnl=pnl,
            pnl_pct=pnl_pct,
            fees=total_fees,
            duration_minutes=duration,
            exit_reason=exit_reason,
            metadata=position.metadata
        )
        
        self.trades.append(trade)
        self.positions.remove(position)
        
        logger.debug(
            f"Closed {position.side} position: P&L=${pnl:.2f} ({pnl_pct:.2f}%), "
            f"reason={exit_reason}, duration={duration:.1f}min"
        )
    
    def _calculate_equity(self, current_price: float) -> float:
        """Calculate current equity including unrealized P&L"""
        equity = self.capital
        
        for position in self.positions:
            position_value = position.size * position.entry_price
            current_value = position.size * current_price
            
            if position.side == 'long':
                unrealized_pnl = (current_value - position_value) * position.leverage
            else:
                unrealized_pnl = (position_value - current_value) * position.leverage
            
            equity += unrealized_pnl
        
        return equity
    
    def _calculate_results(self) -> Dict[str, Any]:
        """Calculate comprehensive backtest results"""
        if not self.trades:
            return {
                'final_equity': self.capital,
                'total_return_pct': 0.0,
                'num_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'sharpe_ratio': 0.0,
                'max_drawdown_pct': 0.0,
                'trades': [],
                'equity_curve': self.equity_curve
            }
        
        final_equity = self.capital
        total_return = final_equity - self.initial_capital
        total_return_pct = (total_return / self.initial_capital) * 100
        
        winning_trades = [t for t in self.trades if t.pnl > 0]
        losing_trades = [t for t in self.trades if t.pnl <= 0]
        
        num_trades = len(self.trades)
        num_wins = len(winning_trades)
        num_losses = len(losing_trades)
        win_rate = (num_wins / num_trades * 100) if num_trades > 0 else 0.0
        
        total_profit = sum(t.pnl for t in winning_trades)
        total_loss = abs(sum(t.pnl for t in losing_trades))
        profit_factor = (total_profit / total_loss) if total_loss > 0 else 0.0
        
        avg_win = (total_profit / num_wins) if num_wins > 0 else 0.0
        avg_loss = (total_loss / num_losses) if num_losses > 0 else 0.0
        avg_win_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else 0.0
        
        equity_values = [eq for _, eq in self.equity_curve]
        peak = equity_values[0]
        max_drawdown = 0.0
        
        for equity in equity_values:
            if equity > peak:
                peak = equity
            drawdown = ((peak - equity) / peak) * 100
            max_drawdown = max(max_drawdown, drawdown)
        
        if len(self.trades) > 1:
            returns = [t.pnl_pct for t in self.trades]
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe_ratio = (avg_return / std_return) if std_return > 0 else 0.0
        else:
            sharpe_ratio = 0.0
        
        return {
            'initial_capital': self.initial_capital,
            'final_equity': final_equity,
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'num_trades': num_trades,
            'num_wins': num_wins,
            'num_losses': num_losses,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'total_loss': total_loss,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_win_loss_ratio': avg_win_loss_ratio,
            'max_drawdown_pct': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'trades': self.trades,
            'equity_curve': self.equity_curve
        }
    
    def get_trade_dataframe(self) -> pd.DataFrame:
        """Convert trades to pandas DataFrame"""
        if not self.trades:
            return pd.DataFrame()
        
        trade_dicts = []
        for trade in self.trades:
            trade_dicts.append({
                'entry_time': trade.entry_time,
                'exit_time': trade.exit_time,
                'symbol': trade.symbol,
                'side': trade.side,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'size': trade.size,
                'leverage': trade.leverage,
                'pnl': trade.pnl,
                'pnl_pct': trade.pnl_pct,
                'fees': trade.fees,
                'duration_minutes': trade.duration_minutes,
                'exit_reason': trade.exit_reason
            })
        
        return pd.DataFrame(trade_dicts)
    
    def get_equity_dataframe(self) -> pd.DataFrame:
        """Convert equity curve to pandas DataFrame"""
        if not self.equity_curve:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.equity_curve, columns=['timestamp', 'equity'])
        df.set_index('timestamp', inplace=True)
        return df
