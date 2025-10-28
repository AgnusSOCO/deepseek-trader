"""
Simple RSI test strategy to validate backtesting engine
Buy when RSI < 30, Sell when RSI > 70
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
from datetime import datetime
from typing import Dict, Any

from src.backtesting.backtest_engine import BacktestEngine
from src.backtesting.performance import PerformanceMetrics
from src.backtesting.data_downloader import DataDownloader
from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalAction

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class SimpleRSIStrategy(BaseStrategy):
    """Simple RSI strategy for testing: Buy RSI<30, Sell RSI>70"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.rsi_oversold = config.get('rsi_oversold', 30)
        self.rsi_overbought = config.get('rsi_overbought', 70)
        self.profit_target_pct = config.get('profit_target_pct', 2.0)
        self.stop_loss_pct = config.get('stop_loss_pct', 1.5)
    
    def initialize(self) -> None:
        self.is_initialized = True
        logger.info(f"SimpleRSIStrategy '{self.name}' initialized")
    
    def on_data(self, market_data: Dict[str, Any], indicators: Dict[str, Any]) -> None:
        pass
    
    def get_parameters(self) -> Dict[str, Any]:
        return {
            'rsi_oversold': self.rsi_oversold,
            'rsi_overbought': self.rsi_overbought,
            'profit_target_pct': self.profit_target_pct,
            'stop_loss_pct': self.stop_loss_pct
        }
    
    def generate_signal(
        self,
        market_data: Dict[str, Any],
        indicators: Dict[str, Any]
    ) -> TradingSignal:
        symbol = market_data['symbol']
        current_price = market_data['price']
        timestamp = market_data.get('timestamp', datetime.now())
        
        rsi = indicators.get('rsi', 50)
        
        if rsi < self.rsi_oversold:
            action = SignalAction.BUY
            confidence = (self.rsi_oversold - rsi) / self.rsi_oversold
            stop_loss = current_price * (1 - self.stop_loss_pct / 100)
            take_profit = current_price * (1 + self.profit_target_pct / 100)
            position_size = 0.1
        elif rsi > self.rsi_overbought:
            action = SignalAction.SELL
            confidence = (rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
            stop_loss = current_price * (1 + self.stop_loss_pct / 100)
            take_profit = current_price * (1 - self.profit_target_pct / 100)
            position_size = 0.1
        else:
            action = SignalAction.HOLD
            confidence = 0.5
            stop_loss = None
            take_profit = None
            position_size = 0.0
        
        return TradingSignal(
            action=action,
            confidence=confidence,
            symbol=symbol,
            timestamp=timestamp,
            price=current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            position_size=position_size,
            metadata={
                'strategy': 'simple_rsi',
                'rsi': rsi,
                'leverage': 1.0
            }
        )


def main():
    """Test simple RSI strategy"""
    
    logger.info("="*60)
    logger.info("Testing Simple RSI Strategy")
    logger.info("="*60)
    
    engine = BacktestEngine(
        initial_capital=10000.0,
        maker_fee=0.0002,
        taker_fee=0.0005,
        slippage_pct=0.0005,
        max_positions=3
    )
    
    downloader = DataDownloader('binance')
    
    logger.info("\nLoading BTC/USDT 5m data...")
    data = downloader.load_data(symbol='BTC/USDT', timeframe='5m')
    
    logger.info(f"Data loaded: {len(data)} rows from {data.index[0]} to {data.index[-1]}")
    logger.info(f"RSI range: {data['rsi'].min():.2f} - {data['rsi'].max():.2f}")
    logger.info(f"RSI < 30 count: {(data['rsi'] < 30).sum()}")
    logger.info(f"RSI > 70 count: {(data['rsi'] > 70).sum()}")
    
    config = {
        'rsi_oversold': 30,
        'rsi_overbought': 70,
        'profit_target_pct': 2.0,
        'stop_loss_pct': 1.5
    }
    
    strategy = SimpleRSIStrategy('SimpleRSI', config)
    
    logger.info("\nRunning backtest...")
    results = engine.run_backtest(strategy, data, 'BTC/USDT')
    
    logger.info("\n" + "="*60)
    logger.info("BACKTEST RESULTS")
    logger.info("="*60)
    
    metrics = PerformanceMetrics.calculate_all_metrics(
        trades=results['trades'],
        equity_curve=results['equity_curve'],
        initial_capital=engine.initial_capital
    )
    
    PerformanceMetrics.print_summary(metrics)
    
    if len(results['trades']) > 0:
        logger.info("\nFirst 5 trades:")
        for i, trade in enumerate(results['trades'][:5]):
            logger.info(
                f"  {i+1}. {trade.side.upper()} @ ${trade.entry_price:.2f} -> ${trade.exit_price:.2f}, "
                f"P&L: ${trade.pnl:.2f} ({trade.pnl_pct:.2f}%), "
                f"Duration: {trade.duration_minutes:.1f}min, "
                f"Exit: {trade.exit_reason}"
            )
    else:
        logger.warning("\n⚠️  NO TRADES GENERATED - Engine may still have issues")


if __name__ == '__main__':
    main()
