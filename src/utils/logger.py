"""
Logging System Module

Provides structured logging with multiple log levels, rotation, and separate log files
for different components of the trading bot.
"""

import sys
from pathlib import Path
from typing import Optional
from loguru import logger
from datetime import datetime


class TradingLogger:
    """Centralized logging system for the trading bot."""
    
    def __init__(self, log_dir: str = "logs", log_level: str = "INFO", log_format: str = "json"):
        """
        Initialize the logging system.
        
        Args:
            log_dir: Directory to store log files
            log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Log format ('json' or 'text')
        """
        self.log_dir = Path(log_dir)
        self.log_level = log_level.upper()
        self.log_format = log_format
        
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.remove()
        
        self._setup_console_logger()
        self._setup_file_loggers()
    
    def _get_format_string(self, include_extra: bool = False) -> str:
        """
        Get the format string based on configuration.
        
        Args:
            include_extra: Whether to include extra fields in the format
            
        Returns:
            Format string for loguru
        """
        if self.log_format == "json":
            if include_extra:
                return (
                    '{{"timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
                    '"level": "{level}", '
                    '"module": "{name}", '
                    '"function": "{function}", '
                    '"line": {line}, '
                    '"message": "{message}", '
                    '"extra": {extra}}}\n'
                )
            else:
                return (
                    '{{"timestamp": "{time:YYYY-MM-DD HH:mm:ss.SSS}", '
                    '"level": "{level}", '
                    '"module": "{name}", '
                    '"function": "{function}", '
                    '"line": {line}, '
                    '"message": "{message}"}}\n'
                )
        else:
            return (
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>\n"
            )
    
    def _setup_console_logger(self):
        """Setup console logger for stdout."""
        logger.add(
            sys.stdout,
            format=self._get_format_string(include_extra=False),
            level=self.log_level,
            colorize=True if self.log_format == "text" else False,
            backtrace=True,
            diagnose=True
        )
    
    def _setup_file_loggers(self):
        """Setup file loggers with rotation."""
        logger.add(
            self.log_dir / "trading_bot.log",
            format=self._get_format_string(include_extra=True),
            level=self.log_level,
            rotation="10 MB",
            retention="30 days",
            compression="zip",
            backtrace=True,
            diagnose=True
        )
        
        logger.add(
            self.log_dir / "trades.log",
            format=self._get_format_string(include_extra=True),
            level="INFO",
            rotation="10 MB",
            retention="90 days",
            compression="zip",
            filter=lambda record: "trade" in record["extra"]
        )
        
        logger.add(
            self.log_dir / "errors.log",
            format=self._get_format_string(include_extra=True),
            level="ERROR",
            rotation="10 MB",
            retention="90 days",
            compression="zip",
            backtrace=True,
            diagnose=True
        )
        
        logger.add(
            self.log_dir / "data.log",
            format=self._get_format_string(include_extra=True),
            level="DEBUG",
            rotation="10 MB",
            retention="7 days",
            compression="zip",
            filter=lambda record: "data" in record["extra"]
        )
    
    def get_logger(self):
        """Get the logger instance."""
        return logger
    
    @staticmethod
    def log_trade(symbol: str, action: str, price: float, size: float, **kwargs):
        """
        Log a trade execution.
        
        Args:
            symbol: Trading symbol
            action: Trade action (BUY/SELL)
            price: Execution price
            size: Position size
            **kwargs: Additional trade details
        """
        logger.bind(trade=True).info(
            f"Trade executed: {action} {size} {symbol} @ {price}",
            extra={
                "trade": True,
                "symbol": symbol,
                "action": action,
                "price": price,
                "size": size,
                **kwargs
            }
        )
    
    @staticmethod
    def log_data(event: str, **kwargs):
        """
        Log a data acquisition event.
        
        Args:
            event: Event description
            **kwargs: Additional event details
        """
        logger.bind(data=True).debug(
            event,
            extra={
                "data": True,
                **kwargs
            }
        )
    
    @staticmethod
    def log_decision(symbol: str, decision: str, confidence: float, **kwargs):
        """
        Log an AI trading decision.
        
        Args:
            symbol: Trading symbol
            decision: Decision (BUY/SELL/HOLD)
            confidence: Confidence score (0-1)
            **kwargs: Additional decision details
        """
        logger.info(
            f"Trading decision: {decision} {symbol} (confidence: {confidence:.2f})",
            extra={
                "decision": True,
                "symbol": symbol,
                "decision": decision,
                "confidence": confidence,
                **kwargs
            }
        )
    
    @staticmethod
    def log_error(error: Exception, context: str = "", **kwargs):
        """
        Log an error with context.
        
        Args:
            error: Exception object
            context: Context description
            **kwargs: Additional context details
        """
        logger.bind(error=True).error(
            f"Error in {context}: {str(error)}",
            extra={
                "error": True,
                "error_type": type(error).__name__,
                "context": context,
                **kwargs
            }
        )
    
    @staticmethod
    def log_performance(metric: str, value: float, **kwargs):
        """
        Log a performance metric.
        
        Args:
            metric: Metric name
            value: Metric value
            **kwargs: Additional metric details
        """
        logger.info(
            f"Performance metric: {metric} = {value}",
            extra={
                "performance": True,
                "metric": metric,
                "value": value,
                **kwargs
            }
        )


_logger_instance: Optional[TradingLogger] = None


def get_logger(log_dir: str = "logs", log_level: str = "INFO", log_format: str = "json") -> logger:
    """
    Get the global logger instance.
    
    Args:
        log_dir: Directory to store log files
        log_level: Minimum log level
        log_format: Log format ('json' or 'text')
        
    Returns:
        Loguru logger instance
    """
    global _logger_instance
    
    if _logger_instance is None:
        _logger_instance = TradingLogger(log_dir, log_level, log_format)
    
    return _logger_instance.get_logger()


def init_logger(log_dir: str = "logs", log_level: str = "INFO", log_format: str = "json") -> TradingLogger:
    """
    Initialize the global logger instance.
    
    Args:
        log_dir: Directory to store log files
        log_level: Minimum log level
        log_format: Log format ('json' or 'text')
        
    Returns:
        TradingLogger instance
    """
    global _logger_instance
    _logger_instance = TradingLogger(log_dir, log_level, log_format)
    return _logger_instance
