"""
Enhanced Health Endpoint

Provides comprehensive system health metrics including:
- System status (CPU, memory, disk)
- Trading system status (running, positions, P&L)
- Database connectivity
- Exchange connectivity
- Risk manager status
- Recent errors
"""

import psutil
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from loguru import logger

from ..data.storage import SQLiteStorage
from ..autonomous.enhanced_risk_manager import EnhancedRiskManager


class HealthMonitor:
    """
    Monitors system health and provides comprehensive health metrics
    """
    
    def __init__(
        self,
        storage: Optional[SQLiteStorage] = None,
        risk_manager: Optional[EnhancedRiskManager] = None
    ):
        """
        Initialize health monitor
        
        Args:
            storage: SQLite storage instance
            risk_manager: Enhanced risk manager instance
        """
        self.storage = storage
        self.risk_manager = risk_manager
        self.start_time = datetime.utcnow()
        self.error_log: List[Dict[str, Any]] = []
        self.max_error_log_size = 100
        
        logger.info("HealthMonitor initialized")
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """
        Get system resource metrics
        
        Returns:
            Dictionary with CPU, memory, and disk metrics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'memory_total_mb': memory.total / (1024 * 1024),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024 * 1024 * 1024),
                'disk_total_gb': disk.total / (1024 * 1024 * 1024)
            }
        except Exception as e:
            logger.error(f"Failed to get system metrics: {e}")
            return {
                'cpu_percent': 0.0,
                'memory_percent': 0.0,
                'memory_available_mb': 0.0,
                'memory_total_mb': 0.0,
                'disk_percent': 0.0,
                'disk_free_gb': 0.0,
                'disk_total_gb': 0.0,
                'error': str(e)
            }
    
    def get_database_health(self) -> Dict[str, Any]:
        """
        Check database connectivity and health
        
        Returns:
            Dictionary with database health status
        """
        if not self.storage:
            return {
                'status': 'not_configured',
                'connected': False,
                'error': 'Storage not configured'
            }
        
        try:
            trades = self.storage.get_trades(limit=1)
            
            return {
                'status': 'healthy',
                'connected': True,
                'total_trades': len(self.storage.get_trades(limit=10000))
            }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                'status': 'unhealthy',
                'connected': False,
                'error': str(e)
            }
    
    def get_risk_manager_status(self) -> Dict[str, Any]:
        """
        Get risk manager status
        
        Returns:
            Dictionary with risk manager metrics
        """
        if not self.risk_manager:
            return {
                'status': 'not_configured',
                'can_trade': False
            }
        
        try:
            current_date = datetime.utcnow().date()
            daily_state = self.risk_manager.daily_state.get(current_date)
            
            if not daily_state:
                return {
                    'status': 'healthy',
                    'can_trade': True,
                    'daily_trades': 0,
                    'daily_pnl': 0.0,
                    'open_positions': 0
                }
            
            return {
                'status': 'healthy',
                'can_trade': self.risk_manager.can_trade_today(),
                'daily_trades': daily_state.total_trades,
                'daily_pnl': daily_state.total_pnl,
                'open_positions': daily_state.open_positions,
                'max_daily_trades': self.risk_manager.max_daily_trades,
                'max_daily_loss_pct': self.risk_manager.max_daily_loss_pct,
                'current_capital': self.risk_manager.current_capital
            }
        except Exception as e:
            logger.error(f"Risk manager status check failed: {e}")
            return {
                'status': 'error',
                'can_trade': False,
                'error': str(e)
            }
    
    def get_uptime(self) -> Dict[str, Any]:
        """
        Get system uptime
        
        Returns:
            Dictionary with uptime metrics
        """
        uptime = datetime.utcnow() - self.start_time
        
        return {
            'uptime_seconds': uptime.total_seconds(),
            'uptime_hours': uptime.total_seconds() / 3600,
            'uptime_days': uptime.total_seconds() / 86400,
            'start_time': self.start_time.isoformat()
        }
    
    def log_error(self, error_type: str, message: str, details: Optional[Dict] = None):
        """
        Log an error to the health monitor
        
        Args:
            error_type: Type of error
            message: Error message
            details: Additional error details
        """
        error_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'type': error_type,
            'message': message,
            'details': details or {}
        }
        
        self.error_log.append(error_entry)
        
        if len(self.error_log) > self.max_error_log_size:
            self.error_log = self.error_log[-self.max_error_log_size:]
        
        logger.error(f"Health monitor logged error: {error_type} - {message}")
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent errors
        
        Args:
            limit: Maximum number of errors to return
            
        Returns:
            List of recent error entries
        """
        return self.error_log[-limit:]
    
    def get_comprehensive_health(self) -> Dict[str, Any]:
        """
        Get comprehensive health status
        
        Returns:
            Dictionary with all health metrics
        """
        system_metrics = self.get_system_metrics()
        database_health = self.get_database_health()
        risk_manager_status = self.get_risk_manager_status()
        uptime = self.get_uptime()
        recent_errors = self.get_recent_errors(limit=5)
        
        overall_status = 'healthy'
        
        if system_metrics.get('cpu_percent', 0) > 90:
            overall_status = 'degraded'
        if system_metrics.get('memory_percent', 0) > 90:
            overall_status = 'degraded'
        if system_metrics.get('disk_percent', 0) > 90:
            overall_status = 'degraded'
        if database_health.get('status') == 'unhealthy':
            overall_status = 'unhealthy'
        if risk_manager_status.get('status') == 'error':
            overall_status = 'unhealthy'
        if len(recent_errors) > 0:
            overall_status = 'degraded'
        
        return {
            'status': overall_status,
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': uptime,
            'system': system_metrics,
            'database': database_health,
            'risk_manager': risk_manager_status,
            'recent_errors': recent_errors,
            'error_count': len(self.error_log)
        }


_health_monitor: Optional[HealthMonitor] = None


def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = HealthMonitor()
    return _health_monitor


def set_health_monitor(monitor: HealthMonitor):
    """Set the global health monitor instance"""
    global _health_monitor
    _health_monitor = monitor
