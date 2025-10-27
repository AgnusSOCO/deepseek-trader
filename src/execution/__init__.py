"""
Execution Module

This module handles order placement, tracking, and execution across exchanges.
Supports both live trading and demo mode simulation.
"""

from .order_manager import OrderManager, Order, OrderStatus, OrderType
from .exchange_interface import ExchangeInterface
from .simulator import ExecutionSimulator

__all__ = [
    'OrderManager',
    'Order',
    'OrderStatus',
    'OrderType',
    'ExchangeInterface',
    'ExecutionSimulator'
]
