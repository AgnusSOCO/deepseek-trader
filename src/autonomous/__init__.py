"""
Autonomous Trading Infrastructure

Core components for zero human interaction trading:
- ExitPlanMonitor: Monitors and enforces exit plans
- AutonomousDecisionEngine: Main decision-making loop
- EnhancedRiskManager: Advanced risk management with daily limits
"""

from src.autonomous.exit_plan_monitor import ExitPlanMonitor, ExitPlan, ExitReason
from src.autonomous.autonomous_decision_engine import AutonomousDecisionEngine
from src.autonomous.enhanced_risk_manager import EnhancedRiskManager

__all__ = [
    'ExitPlanMonitor',
    'ExitPlan',
    'ExitReason',
    'AutonomousDecisionEngine',
    'EnhancedRiskManager',
]
