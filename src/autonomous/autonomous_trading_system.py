"""
Autonomous Trading System (Phase E)

Main orchestrator for the complete autonomous trading system.
Integrates all components for zero human interaction trading:
- Decision engine for trading loops
- Exit plan monitoring
- Risk management
- Performance tracking
- Error recovery
- Comprehensive logging

This is the top-level system that runs continuously.
"""

import logging
import asyncio
import signal
import sys
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
import json
import traceback

from src.autonomous.autonomous_decision_engine import AutonomousDecisionEngine
from src.autonomous.exit_plan_monitor import ExitPlanMonitor
from src.autonomous.enhanced_risk_manager import EnhancedRiskManager
from src.autonomous.performance_monitor import PerformanceMonitor
from src.autonomous.error_recovery import ErrorRecoveryManager
from src.autonomous.logging_config import setup_comprehensive_logging
from src.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class AutonomousTradingSystem:
    """
    Main autonomous trading system orchestrator.
    
    Coordinates all components for fully autonomous trading with:
    - Continuous trading loops
    - Real-time performance monitoring
    - Automatic error recovery
    - Comprehensive audit logging
    - Health checks and diagnostics
    """
    
    def __init__(
        self,
        strategies: List[BaseStrategy],
        initial_capital: float = 10000.0,
        loop_interval_seconds: int = 180,
        max_open_positions: int = 5,
        min_confidence_threshold: float = 0.7,
        enable_trading: bool = False,
        log_dir: str = "logs",
        data_dir: str = "data",
        enable_dashboard: bool = True,
        dashboard_port: int = 8080,
        max_consecutive_errors: int = 5,
        error_cooldown_seconds: int = 300,
    ):
        """
        Initialize autonomous trading system
        
        Args:
            strategies: List of trading strategies
            initial_capital: Starting capital
            loop_interval_seconds: Time between decision loops
            max_open_positions: Maximum concurrent positions
            min_confidence_threshold: Minimum confidence for trades
            enable_trading: Whether to execute real trades
            log_dir: Directory for log files
            data_dir: Directory for data storage
            enable_dashboard: Whether to enable web dashboard
            dashboard_port: Port for web dashboard
            max_consecutive_errors: Max errors before system pause
            error_cooldown_seconds: Cooldown period after errors
        """
        self.strategies = strategies
        self.initial_capital = initial_capital
        self.loop_interval_seconds = loop_interval_seconds
        self.max_open_positions = max_open_positions
        self.min_confidence_threshold = min_confidence_threshold
        self.enable_trading = enable_trading
        self.log_dir = Path(log_dir)
        self.data_dir = Path(data_dir)
        self.enable_dashboard = enable_dashboard
        self.dashboard_port = dashboard_port
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        setup_comprehensive_logging(self.log_dir)
        
        self.exit_monitor = ExitPlanMonitor()
        self.risk_manager = EnhancedRiskManager(initial_capital=initial_capital)
        self.decision_engine = AutonomousDecisionEngine(
            strategies=strategies,
            exit_monitor=self.exit_monitor,
            risk_manager=self.risk_manager,
            loop_interval_seconds=loop_interval_seconds,
            max_open_positions=max_open_positions,
            min_confidence_threshold=min_confidence_threshold,
            enable_trading=enable_trading,
        )
        self.performance_monitor = PerformanceMonitor(
            initial_capital=initial_capital,
            data_dir=self.data_dir
        )
        self.error_recovery = ErrorRecoveryManager(
            max_consecutive_errors=max_consecutive_errors,
            cooldown_seconds=error_cooldown_seconds
        )
        
        self.is_running = False
        self.start_time: Optional[datetime] = None
        self.shutdown_requested = False
        
        self._setup_signal_handlers()
        
        logger.info("=" * 80)
        logger.info("🚀 AUTONOMOUS TRADING SYSTEM INITIALIZED")
        logger.info("=" * 80)
        logger.info(f"Strategies: {len(strategies)}")
        logger.info(f"Initial Capital: ${initial_capital:,.2f}")
        logger.info(f"Loop Interval: {loop_interval_seconds}s")
        logger.info(f"Max Positions: {max_open_positions}")
        logger.info(f"Min Confidence: {min_confidence_threshold}")
        logger.info(f"Trading Enabled: {enable_trading}")
        logger.info(f"Dashboard Enabled: {enable_dashboard}")
        logger.info(f"Log Directory: {self.log_dir}")
        logger.info("=" * 80)
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_requested = True
            self.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    async def start(self) -> None:
        """Start the autonomous trading system"""
        if self.is_running:
            logger.warning("System already running")
            return
        
        self.is_running = True
        self.start_time = datetime.now()
        self.shutdown_requested = False
        
        logger.info("=" * 80)
        logger.info("🟢 STARTING AUTONOMOUS TRADING SYSTEM")
        logger.info(f"Start Time: {self.start_time}")
        logger.info("=" * 80)
        
        if not self.enable_trading:
            logger.warning("⚠️  TRADING DISABLED - Running in simulation mode")
        
        try:
            tasks = []
            
            tasks.append(asyncio.create_task(self._run_decision_engine()))
            
            tasks.append(asyncio.create_task(self._run_performance_monitoring()))
            
            tasks.append(asyncio.create_task(self._run_health_checks()))
            
            if self.enable_dashboard:
                tasks.append(asyncio.create_task(self._run_dashboard()))
            
            await asyncio.gather(*tasks, return_exceptions=True)
        
        except Exception as e:
            logger.error(f"Fatal error in autonomous trading system: {e}", exc_info=True)
            await self.error_recovery.handle_fatal_error(e)
        
        finally:
            await self._cleanup()
    
    async def _run_decision_engine(self) -> None:
        """Run the decision engine with error recovery"""
        logger.info("🔄 Starting decision engine...")
        
        while self.is_running and not self.shutdown_requested:
            try:
                if self.error_recovery.should_pause():
                    pause_duration = self.error_recovery.get_pause_duration()
                    logger.warning(
                        f"⏸️  System paused due to errors, "
                        f"resuming in {pause_duration}s..."
                    )
                    await asyncio.sleep(pause_duration)
                    self.error_recovery.reset_error_count()
                    continue
                
                await self.decision_engine._run_decision_loop()
                
                self.error_recovery.record_success()
                
                await self._update_performance_metrics()
            
            except Exception as e:
                logger.error(f"Error in decision loop: {e}", exc_info=True)
                
                recovery_action = await self.error_recovery.handle_error(
                    e,
                    context={'component': 'decision_engine'}
                )
                
                if recovery_action == 'stop':
                    logger.error("🛑 Stopping system due to unrecoverable errors")
                    self.stop()
                    break
                elif recovery_action == 'pause':
                    logger.warning("⏸️  Pausing system for cooldown period")
                    await asyncio.sleep(self.error_recovery.cooldown_seconds)
            
            await asyncio.sleep(self.loop_interval_seconds)
    
    async def _run_performance_monitoring(self) -> None:
        """Run continuous performance monitoring"""
        logger.info("📊 Starting performance monitoring...")
        
        while self.is_running and not self.shutdown_requested:
            try:
                await asyncio.sleep(60)
                
                await self._update_performance_metrics()
                
                self.performance_monitor.log_summary()
            
            except Exception as e:
                logger.error(f"Error in performance monitoring: {e}", exc_info=True)
    
    async def _run_health_checks(self) -> None:
        """Run periodic health checks"""
        logger.info("🏥 Starting health checks...")
        
        while self.is_running and not self.shutdown_requested:
            try:
                await asyncio.sleep(300)
                
                health_status = await self._check_system_health()
                
                if not health_status['healthy']:
                    logger.warning(
                        f"⚠️  System health check failed: {health_status['issues']}"
                    )
                    
                    for issue in health_status['issues']:
                        await self.error_recovery.handle_health_issue(issue)
            
            except Exception as e:
                logger.error(f"Error in health checks: {e}", exc_info=True)
    
    async def _run_dashboard(self) -> None:
        """Run web dashboard for monitoring"""
        logger.info(f"🌐 Starting web dashboard on port {self.dashboard_port}...")
        
        try:
            from src.autonomous.dashboard import run_dashboard
            await run_dashboard(
                self,
                port=self.dashboard_port
            )
        except ImportError:
            logger.warning("Dashboard module not available, skipping...")
        except Exception as e:
            logger.error(f"Error starting dashboard: {e}", exc_info=True)
    
    async def _update_performance_metrics(self) -> None:
        """Update performance metrics from all components"""
        try:
            engine_stats = self.decision_engine.get_statistics()
            risk_stats = self.risk_manager.get_statistics()
            exit_stats = self.exit_monitor.get_exit_statistics()
            
            self.performance_monitor.update_metrics(
                timestamp=datetime.now(),
                capital=risk_stats['current_capital'],
                open_positions=engine_stats['open_positions'],
                daily_pnl=risk_stats['daily_pnl'],
                total_pnl=risk_stats['total_pnl'],
                total_trades=risk_stats['total_trades'],
                daily_trades=risk_stats['daily_trades'],
                win_rate=risk_stats['daily_win_rate'],
                max_drawdown=risk_stats['max_drawdown'],
                decision_count=engine_stats['total_decisions'],
                loop_count=engine_stats['total_loops'],
            )
        
        except Exception as e:
            logger.error(f"Error updating performance metrics: {e}", exc_info=True)
    
    async def _check_system_health(self) -> Dict[str, Any]:
        """
        Check system health
        
        Returns:
            Dict with health status and any issues
        """
        issues = []
        
        try:
            if not self.decision_engine.is_running:
                issues.append("Decision engine not running")
            
            risk_stats = self.risk_manager.get_statistics()
            if risk_stats['max_drawdown'] > 20.0:
                issues.append(f"High drawdown: {risk_stats['max_drawdown']:.1f}%")
            
            if not risk_stats['can_trade_today']:
                issues.append("Daily trading limits reached")
            
            error_rate = self.error_recovery.get_error_rate()
            if error_rate > 0.5:
                issues.append(f"High error rate: {error_rate:.1%}")
            
            uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
            if uptime < 60 and self.error_recovery.consecutive_errors > 0:
                issues.append("System unstable after recent start")
        
        except Exception as e:
            issues.append(f"Health check error: {str(e)}")
        
        return {
            'healthy': len(issues) == 0,
            'issues': issues,
            'timestamp': datetime.now()
        }
    
    async def _cleanup(self) -> None:
        """Cleanup resources before shutdown"""
        logger.info("🧹 Cleaning up resources...")
        
        try:
            self.decision_engine.stop()
            
            await self._save_final_state()
            
            self.performance_monitor.save_metrics()
            
            logger.info("✓ Cleanup completed")
        
        except Exception as e:
            logger.error(f"Error during cleanup: {e}", exc_info=True)
    
    async def _save_final_state(self) -> None:
        """Save final system state"""
        try:
            state_file = self.data_dir / f"final_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            state = {
                'timestamp': datetime.now().isoformat(),
                'uptime_seconds': (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                'engine_stats': self.decision_engine.get_statistics(),
                'risk_stats': self.risk_manager.get_statistics(),
                'exit_stats': self.exit_monitor.get_exit_statistics(),
                'error_stats': self.error_recovery.get_statistics(),
                'performance_summary': self.performance_monitor.get_summary()
            }
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
            
            logger.info(f"✓ Final state saved to {state_file}")
        
        except Exception as e:
            logger.error(f"Error saving final state: {e}", exc_info=True)
    
    def stop(self) -> None:
        """Stop the autonomous trading system"""
        logger.info("🛑 Stopping autonomous trading system...")
        self.is_running = False
        self.shutdown_requested = True
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current system status
        
        Returns:
            Dict with comprehensive system status
        """
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            'is_running': self.is_running,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'uptime_seconds': uptime,
            'uptime_formatted': str(timedelta(seconds=int(uptime))),
            'enable_trading': self.enable_trading,
            'strategies_count': len(self.strategies),
            'engine_stats': self.decision_engine.get_statistics(),
            'risk_stats': self.risk_manager.get_statistics(),
            'exit_stats': self.exit_monitor.get_exit_statistics(),
            'error_stats': self.error_recovery.get_statistics(),
            'health': asyncio.run(self._check_system_health()) if self.is_running else None
        }
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report
        
        Returns:
            Dict with performance metrics and analysis
        """
        return self.performance_monitor.generate_report()


async def main():
    """Main entry point for autonomous trading system"""
    from src.strategies.simple_rsi import SimpleRSIStrategy
    
    strategies = [
        SimpleRSIStrategy(symbol='BTC/USDT', timeframe='1h'),
    ]
    
    system = AutonomousTradingSystem(
        strategies=strategies,
        initial_capital=10000.0,
        loop_interval_seconds=180,
        max_open_positions=5,
        min_confidence_threshold=0.7,
        enable_trading=False,
        enable_dashboard=True,
        dashboard_port=8080,
    )
    
    await system.start()


if __name__ == '__main__':
    asyncio.run(main())
