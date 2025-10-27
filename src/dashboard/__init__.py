"""
Dashboard Module

FastAPI-based dashboard for monitoring and controlling the trading bot.
Provides REST API endpoints and a simple web interface.
"""

from .app import create_app

__all__ = ['create_app']
