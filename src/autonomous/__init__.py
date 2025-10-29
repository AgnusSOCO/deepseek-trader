"""
Autonomous Trading Infrastructure

Phase B: Core Autonomous Infrastructure
- ExitPlanMonitor: Monitors and enforces exit plans
- AutonomousDecisionEngine: Main decision-making loop
- EnhancedRiskManager: Advanced risk management with daily limits

Phase E: Autonomous Trading System
- AutonomousTradingSystem: Main orchestrator for complete system
- PerformanceMonitor: Performance tracking and reporting
- ErrorRecoveryManager: Error handling and recovery
- Logging: Comprehensive logging system
- Dashboard: Web-based monitoring dashboard
"""

from src.autonomous.exit_plan_monitor import ExitPlanMonitor, ExitPlan, ExitReason
from src.autonomous.autonomous_decision_engine import AutonomousDecisionEngine, Position, DecisionLog
from src.autonomous.enhanced_risk_manager import EnhancedRiskManager, DailyRiskState
from src.autonomous.autonomous_trading_system import AutonomousTradingSystem
from src.autonomous.performance_monitor import PerformanceMonitor, PerformanceSnapshot
from src.autonomous.error_recovery import ErrorRecoveryManager, ErrorRecord
from src.autonomous.logging_config import (
    setup_comprehensive_logging,
    get_trade_logger,
    log_trade_event,
    log_decision
)

__all__ = [
    'ExitPlanMonitor',
    'ExitPlan',
    'ExitReason',
    'AutonomousDecisionEngine',
    'Position',
    'DecisionLog',
    'EnhancedRiskManager',
    'DailyRiskState',
    'AutonomousTradingSystem',
    'PerformanceMonitor',
    'PerformanceSnapshot',
    'ErrorRecoveryManager',
    'ErrorRecord',
    'setup_comprehensive_logging',
    'get_trade_logger',
    'log_trade_event',
    'log_decision',
]
