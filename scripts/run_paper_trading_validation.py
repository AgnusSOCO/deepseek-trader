#!/usr/bin/env python3
"""
Paper Trading Validation Script

Runs the autonomous trading system in paper trading mode for validation.
Supports 3-phase validation approach as outlined in nof1.ai alignment plan.

Usage:
    python scripts/run_paper_trading_validation.py --phase 1 --duration 168  # Phase 1: 1 week
    python scripts/run_paper_trading_validation.py --phase 2 --duration 168  # Phase 2: 1 week
    python scripts/run_paper_trading_validation.py --phase 3 --duration 168  # Phase 3: 1 week
"""

import asyncio
import sys
import os
import argparse
import signal
from datetime import datetime, timedelta
from pathlib import Path
import json
import logging

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.autonomous.autonomous_trading_system import AutonomousTradingSystem
from src.execution.paper_trading import PaperTradingEngine
from src.data.price_feed import PriceFeed
from src.autonomous.enhanced_risk_manager import EnhancedRiskManager
from src.autonomous.exit_plan_monitor import ExitPlanMonitor
from src.autonomous.autonomous_decision_engine import AutonomousDecisionEngine
from src.strategies.single_agent_strategy import SingleAgentStrategy


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('paper_trading_validation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class PaperTradingValidator:
    """
    Paper trading validation orchestrator
    
    Manages 3-phase validation approach:
    - Phase 1: Single strategy (Momentum_1h), conservative settings
    - Phase 2: Multiple strategies, moderate settings
    - Phase 3: Full system, production settings
    """
    
    def __init__(
        self,
        phase: int,
        duration_hours: int,
        exchange: str = 'bybit',
        testnet: bool = True,
        initial_capital: float = 10000.0,
        output_dir: str = './paper_trading_validation'
    ):
        """
        Initialize validator
        
        Args:
            phase: Validation phase (1, 2, or 3)
            duration_hours: Duration in hours
            exchange: Exchange to use
            testnet: Use testnet mode
            initial_capital: Initial capital
            output_dir: Output directory for results
        """
        self.phase = phase
        self.duration_hours = duration_hours
        self.exchange = exchange
        self.testnet = testnet
        self.initial_capital = initial_capital
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.start_time = None
        self.end_time = None
        self.paper_engine = None
        self.trading_system = None
        self.should_stop = False
        
        self.config = self._get_phase_config()
        
        logger.info(f"Initialized Paper Trading Validator - Phase {phase}")
        logger.info(f"Duration: {duration_hours} hours")
        logger.info(f"Exchange: {exchange} ({'testnet' if testnet else 'live'})")
        logger.info(f"Initial Capital: ${initial_capital:,.2f}")
    
    def _get_phase_config(self) -> dict:
        """Get phase-specific configuration"""
        if self.phase == 1:
            return {
                'name': 'Phase 1: Single Strategy Validation',
                'description': 'Conservative validation with single best-performing strategy',
                'strategies': ['momentum_1h'],
                'symbols': ['BTC/USDT'],
                'max_daily_loss_pct': 3.0,
                'max_daily_trades': 10,
                'max_position_size_pct': 15.0,
                'account_drawdown_warn_pct': 10.0,
                'account_drawdown_stop_pct': 15.0,
                'min_confidence': 0.75,
                'loop_interval': 300  # 5 minutes
            }
        elif self.phase == 2:
            return {
                'name': 'Phase 2: Multi-Strategy Validation',
                'description': 'Moderate validation with multiple strategies',
                'strategies': ['momentum_1h', 'mean_reversion_15m', 'universal_macd_5m'],
                'symbols': ['BTC/USDT', 'ETH/USDT'],
                'max_daily_loss_pct': 4.0,
                'max_daily_trades': 15,
                'max_position_size_pct': 20.0,
                'account_drawdown_warn_pct': 12.0,
                'account_drawdown_stop_pct': 18.0,
                'min_confidence': 0.70,
                'loop_interval': 300  # 5 minutes
            }
        elif self.phase == 3:
            return {
                'name': 'Phase 3: Full System Validation',
                'description': 'Production settings with full strategy suite',
                'strategies': ['all'],  # All available strategies
                'symbols': ['BTC/USDT', 'ETH/USDT', 'BNB/USDT'],
                'max_daily_loss_pct': 5.0,
                'max_daily_trades': 20,
                'max_position_size_pct': 20.0,
                'account_drawdown_warn_pct': 15.0,
                'account_drawdown_stop_pct': 20.0,
                'min_confidence': 0.65,
                'loop_interval': 300  # 5 minutes
            }
        else:
            raise ValueError(f"Invalid phase: {self.phase}. Must be 1, 2, or 3.")
    
    async def run(self):
        """Run paper trading validation"""
        logger.info(f"Starting {self.config['name']}")
        logger.info(f"Description: {self.config['description']}")
        
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=self.duration_hours)
        
        logger.info(f"Start time: {self.start_time}")
        logger.info(f"End time: {self.end_time}")
        
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        try:
            self.paper_engine = PaperTradingEngine(
                initial_capital=self.initial_capital,
                slippage_pct=0.05,
                maker_fee_pct=0.02,
                taker_fee_pct=0.06,
                log_dir=str(self.output_dir / f"phase_{self.phase}_trades")
            )
            
            price_feed = PriceFeed(
                exchange_id=self.exchange,
                testnet=self.testnet
            )
            
            risk_manager = EnhancedRiskManager(
                initial_capital=self.initial_capital,
                max_daily_loss_pct=self.config['max_daily_loss_pct'],
                max_daily_trades=self.config['max_daily_trades'],
                max_position_size_pct=self.config['max_position_size_pct'],
                account_drawdown_warn_pct=self.config['account_drawdown_warn_pct'],
                account_drawdown_stop_pct=self.config['account_drawdown_stop_pct']
            )
            
            exit_monitor = ExitPlanMonitor(
                max_holding_hours=36.0,
                tiered_trailing_enabled=True
            )
            
            strategies = self._initialize_strategies(price_feed)
            
            decision_engine = AutonomousDecisionEngine(
                strategies=strategies,
                risk_manager=risk_manager,
                exit_monitor=exit_monitor,
                price_feed=price_feed,
                loop_interval=self.config['loop_interval'],
                min_confidence=self.config['min_confidence']
            )
            
            await self._validation_loop(decision_engine, price_feed)
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}", exc_info=True)
            raise
        finally:
            self._generate_report()
    
    def _initialize_strategies(self, price_feed):
        """Initialize strategies based on phase configuration"""
        strategies = []
        
        if self.phase == 1:
            from src.strategies.momentum import MomentumStrategy
            strategies.append(MomentumStrategy(
                timeframe='1h',
                price_feed=price_feed
            ))
        elif self.phase == 2:
            from src.strategies.momentum import MomentumStrategy
            from src.strategies.mean_reversion import MeanReversionStrategy
            from src.strategies.universal_macd_strategy import UniversalMacdStrategy
            
            strategies.extend([
                MomentumStrategy(timeframe='1h', price_feed=price_feed),
                MeanReversionStrategy(timeframe='15m', price_feed=price_feed),
                UniversalMacdStrategy(timeframe='5m', price_feed=price_feed)
            ])
        elif self.phase == 3:
            from src.strategies.momentum import MomentumStrategy
            from src.strategies.mean_reversion import MeanReversionStrategy
            from src.strategies.scalping import ScalpingStrategy
            from src.strategies.universal_macd_strategy import UniversalMacdStrategy
            from src.strategies.multi_supertrend_strategy import MultiSuperTrendStrategy
            
            strategies.extend([
                MomentumStrategy(timeframe='1h', price_feed=price_feed),
                MeanReversionStrategy(timeframe='15m', price_feed=price_feed),
                ScalpingStrategy(timeframe='5m', price_feed=price_feed),
                UniversalMacdStrategy(timeframe='5m', price_feed=price_feed),
                MultiSuperTrendStrategy(timeframe='1h', price_feed=price_feed)
            ])
        
        logger.info(f"Initialized {len(strategies)} strategies for Phase {self.phase}")
        return strategies
    
    async def _validation_loop(self, decision_engine, price_feed):
        """Main validation loop"""
        iteration = 0
        
        while not self.should_stop and datetime.now() < self.end_time:
            iteration += 1
            
            try:
                current_prices = {}
                for symbol in self.config['symbols']:
                    price = price_feed.get_latest_price(symbol)
                    if price:
                        current_prices[symbol] = price
                
                positions_to_close = self.paper_engine.update_positions(current_prices)
                
                for pos_info in positions_to_close:
                    self.paper_engine.close_position(
                        pos_info['position_id'],
                        pos_info['exit_price'],
                        pos_info['reason']
                    )
                
                
                if iteration % 10 == 0:
                    metrics = self.paper_engine.get_performance_metrics()
                    logger.info(f"Iteration {iteration} - Capital: ${metrics['current_capital']:,.2f}, "
                              f"Return: {metrics['total_return_pct']:.2f}%, "
                              f"Trades: {metrics['total_trades']}, "
                              f"Win Rate: {metrics['win_rate']:.1f}%")
                
                await asyncio.sleep(self.config['loop_interval'])
                
            except Exception as e:
                logger.error(f"Error in validation loop iteration {iteration}: {str(e)}", exc_info=True)
                await asyncio.sleep(60)  # Wait 1 minute before retrying
        
        logger.info(f"Validation loop completed after {iteration} iterations")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.should_stop = True
    
    def _generate_report(self):
        """Generate validation report"""
        if not self.paper_engine:
            logger.warning("Paper engine not initialized, skipping report generation")
            return
        
        logger.info("Generating validation report...")
        
        metrics = self.paper_engine.get_performance_metrics()
        
        report = self.paper_engine.save_session_report()
        
        summary = {
            'phase': self.phase,
            'phase_name': self.config['name'],
            'phase_description': self.config['description'],
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': datetime.now().isoformat(),
            'planned_duration_hours': self.duration_hours,
            'actual_duration': str(datetime.now() - self.start_time).split('.')[0] if self.start_time else None,
            'configuration': self.config,
            'performance_metrics': metrics,
            'validation_status': self._determine_validation_status(metrics)
        }
        
        summary_file = self.output_dir / f"phase_{self.phase}_validation_summary.json"
        with open(summary_file, 'w') as f:
            json.dump(summary, f, indent=2)
        
        logger.info(f"Validation report saved to {summary_file}")
        
        self._print_summary(summary)
    
    def _determine_validation_status(self, metrics: dict) -> dict:
        """Determine if validation passed based on metrics"""
        status = {
            'passed': True,
            'issues': []
        }
        
        if metrics['total_return_pct'] < -10:
            status['passed'] = False
            status['issues'].append(f"Large loss: {metrics['total_return_pct']:.2f}%")
        
        if metrics['drawdown_pct'] > 20:
            status['passed'] = False
            status['issues'].append(f"Excessive drawdown: {metrics['drawdown_pct']:.2f}%")
        
        if metrics['total_trades'] > 10 and metrics['win_rate'] < 30:
            status['passed'] = False
            status['issues'].append(f"Low win rate: {metrics['win_rate']:.1f}%")
        
        if metrics['profit_factor'] < 0.8:
            status['passed'] = False
            status['issues'].append(f"Low profit factor: {metrics['profit_factor']:.2f}")
        
        return status
    
    def _print_summary(self, summary: dict):
        """Print validation summary"""
        print("\n" + "="*70)
        print(f"Paper Trading Validation Summary - Phase {self.phase}")
        print("="*70)
        print(f"\nPhase: {summary['phase_name']}")
        print(f"Description: {summary['phase_description']}")
        print(f"Duration: {summary['actual_duration']}")
        
        metrics = summary['performance_metrics']
        print(f"\nPerformance Metrics:")
        print(f"  Initial Capital: ${metrics['initial_capital']:,.2f}")
        print(f"  Final Capital: ${metrics['current_capital']:,.2f}")
        print(f"  Total Return: {metrics['total_return_pct']:.2f}%")
        print(f"  Max Drawdown: {metrics['drawdown_pct']:.2f}%")
        print(f"  Total Trades: {metrics['total_trades']}")
        print(f"  Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  Profit Factor: {metrics['profit_factor']:.2f}")
        
        status = summary['validation_status']
        print(f"\nValidation Status: {'✅ PASSED' if status['passed'] else '❌ FAILED'}")
        if status['issues']:
            print("Issues:")
            for issue in status['issues']:
                print(f"  - {issue}")
        
        print("\n" + "="*70 + "\n")


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run paper trading validation')
    parser.add_argument('--phase', type=int, required=True, choices=[1, 2, 3],
                       help='Validation phase (1, 2, or 3)')
    parser.add_argument('--duration', type=int, required=True,
                       help='Duration in hours')
    parser.add_argument('--exchange', default='bybit',
                       help='Exchange to use (default: bybit)')
    parser.add_argument('--live', action='store_true',
                       help='Use live mode instead of testnet')
    parser.add_argument('--capital', type=float, default=10000.0,
                       help='Initial capital (default: 10000)')
    parser.add_argument('--output-dir', default='./paper_trading_validation',
                       help='Output directory (default: ./paper_trading_validation)')
    
    args = parser.parse_args()
    
    validator = PaperTradingValidator(
        phase=args.phase,
        duration_hours=args.duration,
        exchange=args.exchange,
        testnet=not args.live,
        initial_capital=args.capital,
        output_dir=args.output_dir
    )
    
    await validator.run()


if __name__ == '__main__':
    asyncio.run(main())
