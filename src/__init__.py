"""
AI Cryptocurrency Trading Bot

A sophisticated AI-powered cryptocurrency trading bot that leverages DeepSeek LLM
for intelligent trading decisions on cryptocurrency markets.
"""

__version__ = "0.1.0"
__author__ = "AI Trading Bot Team"

from .utils.config_loader import get_config, ConfigLoader
from .utils.logger import get_logger, init_logger

__all__ = [
    'get_config',
    'ConfigLoader',
    'get_logger',
    'init_logger',
]
