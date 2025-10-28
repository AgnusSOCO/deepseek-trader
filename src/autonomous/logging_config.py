"""
Comprehensive Logging Configuration (Phase E)

Sets up structured logging with multiple handlers for autonomous trading system.
Provides detailed audit trails and debugging capabilities.
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import json


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        if hasattr(record, 'extra'):
            log_data['extra'] = record.extra
        
        return json.dumps(log_data)


def setup_comprehensive_logging(log_dir: Path) -> None:
    """
    Setup comprehensive logging system
    
    Creates multiple log handlers:
    - Console output (INFO level, human-readable)
    - Main log file (DEBUG level, rotating)
    - Error log file (ERROR level only)
    - Trade log file (trade-specific events)
    - JSON log file (structured logging)
    
    Args:
        log_dir: Directory for log files
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    main_log_file = log_dir / 'trading_system.log'
    main_handler = RotatingFileHandler(
        main_log_file,
        maxBytes=50 * 1024 * 1024,
        backupCount=10
    )
    main_handler.setLevel(logging.DEBUG)
    main_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)-20s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    main_handler.setFormatter(main_formatter)
    root_logger.addHandler(main_handler)
    
    error_log_file = log_dir / 'errors.log'
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(main_formatter)
    root_logger.addHandler(error_handler)
    
    trade_log_file = log_dir / 'trades.log'
    trade_handler = TimedRotatingFileHandler(
        trade_log_file,
        when='midnight',
        interval=1,
        backupCount=30
    )
    trade_handler.setLevel(logging.INFO)
    trade_formatter = logging.Formatter(
        '%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    trade_handler.setFormatter(trade_formatter)
    
    trade_logger = logging.getLogger('trading')
    trade_logger.addHandler(trade_handler)
    trade_logger.setLevel(logging.INFO)
    trade_logger.propagate = False
    
    json_log_file = log_dir / 'structured.jsonl'
    json_handler = RotatingFileHandler(
        json_log_file,
        maxBytes=50 * 1024 * 1024,
        backupCount=5
    )
    json_handler.setLevel(logging.DEBUG)
    json_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(json_handler)
    
    logging.info("=" * 80)
    logging.info("📝 COMPREHENSIVE LOGGING SYSTEM INITIALIZED")
    logging.info("=" * 80)
    logging.info(f"Log Directory: {log_dir}")
    logging.info(f"Main Log: {main_log_file}")
    logging.info(f"Error Log: {error_log_file}")
    logging.info(f"Trade Log: {trade_log_file}")
    logging.info(f"JSON Log: {json_log_file}")
    logging.info("=" * 80)


def get_trade_logger() -> logging.Logger:
    """
    Get the trade-specific logger
    
    Returns:
        Trade logger instance
    """
    return logging.getLogger('trading')


def log_trade_event(
    event_type: str,
    symbol: str,
    action: str,
    price: float,
    quantity: float,
    **kwargs
) -> None:
    """
    Log a trade event
    
    Args:
        event_type: Type of event (ENTRY, EXIT, SIGNAL, etc.)
        symbol: Trading symbol
        action: Action taken (BUY, SELL, HOLD)
        price: Price
        quantity: Quantity
        **kwargs: Additional event data
    """
    trade_logger = get_trade_logger()
    
    event_data = {
        'event_type': event_type,
        'symbol': symbol,
        'action': action,
        'price': price,
        'quantity': quantity,
        **kwargs
    }
    
    trade_logger.info(json.dumps(event_data))


def log_decision(
    decision_type: str,
    symbol: str,
    confidence: float,
    justification: str,
    **kwargs
) -> None:
    """
    Log a trading decision
    
    Args:
        decision_type: Type of decision (ENTRY, EXIT, HOLD, SKIP)
        symbol: Trading symbol
        confidence: Confidence level
        justification: Justification for decision
        **kwargs: Additional decision data
    """
    trade_logger = get_trade_logger()
    
    decision_data = {
        'decision_type': decision_type,
        'symbol': symbol,
        'confidence': confidence,
        'justification': justification,
        **kwargs
    }
    
    trade_logger.info(json.dumps(decision_data))
