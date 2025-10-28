"""
Dashboard API Routes

REST API endpoints for monitoring and controlling the trading bot.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

_bot_state = {
    'running': False,
    'mode': 'demo',
    'start_time': None,
    'strategies': [],
    'positions': [],
    'balance': 0.0,
    'portfolio': None,
    'orders': []
}


class StartRequest(BaseModel):
    """Request to start trading"""
    mode: str = 'demo'
    strategies: Optional[List[str]] = None


class StopRequest(BaseModel):
    """Request to stop trading"""
    emergency: bool = False


class StrategyUpdate(BaseModel):
    """Update strategy parameters"""
    strategy_name: str
    parameters: Dict[str, Any]


@router.get("/health")
async def health():
    """System health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": (datetime.now() - _bot_state['start_time']).total_seconds() if _bot_state['start_time'] else 0
    }


@router.get("/status")
async def get_status():
    """Get current system status"""
    return {
        "running": _bot_state['running'],
        "mode": _bot_state['mode'],
        "start_time": _bot_state['start_time'].isoformat() if _bot_state['start_time'] else None,
        "active_strategies": len(_bot_state['strategies']),
        "open_positions": len(_bot_state['positions']),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/balance")
async def get_balance():
    """Get account balance"""
    return {
        "balance": _bot_state['balance'],
        "currency": "USDT",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/portfolio")
async def get_portfolio():
    """Get portfolio summary"""
    if _bot_state['portfolio'] is None:
        return {
            "total_value": _bot_state['balance'],
            "cash_balance": _bot_state['balance'],
            "positions_value": 0.0,
            "unrealized_pnl": 0.0,
            "realized_pnl": 0.0,
            "total_pnl": 0.0,
            "num_positions": 0,
            "timestamp": datetime.now().isoformat()
        }
    
    return _bot_state['portfolio']


@router.get("/performance")
async def get_performance():
    """Get performance metrics"""
    return {
        "total_return_pct": 0.0,
        "daily_return_pct": 0.0,
        "max_drawdown_pct": 0.0,
        "win_rate_pct": 0.0,
        "total_trades": 0,
        "sharpe_ratio": 0.0,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/positions")
async def get_positions():
    """Get all open positions"""
    return {
        "positions": _bot_state['positions'],
        "count": len(_bot_state['positions']),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/positions/{symbol}")
async def get_position(symbol: str):
    """Get position for specific symbol"""
    position = next((p for p in _bot_state['positions'] if p.get('symbol') == symbol), None)
    
    if position is None:
        raise HTTPException(status_code=404, detail=f"Position not found for symbol: {symbol}")
    
    return position


@router.get("/orders")
async def get_orders(status: Optional[str] = None, limit: int = 100):
    """Get order history"""
    orders = _bot_state['orders']
    
    if status:
        orders = [o for o in orders if o.get('status') == status]
    
    return {
        "orders": orders[-limit:],
        "count": len(orders),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/orders/{order_id}")
async def get_order(order_id: str):
    """Get specific order"""
    order = next((o for o in _bot_state['orders'] if o.get('order_id') == order_id), None)
    
    if order is None:
        raise HTTPException(status_code=404, detail=f"Order not found: {order_id}")
    
    return order


@router.get("/trades")
async def get_trades(symbol: Optional[str] = None, limit: int = 100):
    """Get trade history"""
    trades = []
    
    if symbol:
        trades = [t for t in trades if t.get('symbol') == symbol]
    
    return {
        "trades": trades[-limit:],
        "count": len(trades),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/strategies")
async def get_strategies():
    """Get all strategies and their status"""
    return {
        "strategies": _bot_state['strategies'],
        "count": len(_bot_state['strategies']),
        "timestamp": datetime.now().isoformat()
    }


@router.get("/strategies/{strategy_name}")
async def get_strategy(strategy_name: str):
    """Get specific strategy details"""
    strategy = next((s for s in _bot_state['strategies'] if s.get('name') == strategy_name), None)
    
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_name}")
    
    return strategy


@router.put("/strategies/{strategy_name}")
async def update_strategy(strategy_name: str, update: StrategyUpdate):
    """Update strategy parameters"""
    strategy = next((s for s in _bot_state['strategies'] if s.get('name') == strategy_name), None)
    
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Strategy not found: {strategy_name}")
    
    strategy['parameters'] = update.parameters
    
    return {
        "message": f"Strategy {strategy_name} updated successfully",
        "strategy": strategy
    }


@router.post("/start")
async def start_trading(request: StartRequest):
    """Start trading"""
    if _bot_state['running']:
        raise HTTPException(status_code=400, detail="Trading is already running")
    
    _bot_state['running'] = True
    _bot_state['mode'] = request.mode
    _bot_state['start_time'] = datetime.now()
    
    if request.strategies:
        _bot_state['strategies'] = [{'name': s, 'active': True} for s in request.strategies]
    
    return {
        "message": "Trading started successfully",
        "mode": request.mode,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/stop")
async def stop_trading(request: StopRequest):
    """Stop trading"""
    if not _bot_state['running']:
        raise HTTPException(status_code=400, detail="Trading is not running")
    
    _bot_state['running'] = False
    
    if request.emergency:
        _bot_state['positions'] = []
        message = "Emergency stop executed - all positions closed"
    else:
        message = "Trading stopped successfully"
    
    return {
        "message": message,
        "timestamp": datetime.now().isoformat()
    }


@router.post("/emergency_stop")
async def emergency_stop():
    """Emergency stop - close all positions and halt trading"""
    _bot_state['running'] = False
    _bot_state['positions'] = []
    
    return {
        "message": "Emergency stop executed - all positions closed and trading halted",
        "timestamp": datetime.now().isoformat()
    }


@router.post("/reset")
async def reset_system():
    """Reset system state (demo mode only)"""
    if _bot_state['mode'] != 'demo':
        raise HTTPException(status_code=400, detail="Reset only available in demo mode")
    
    _bot_state['running'] = False
    _bot_state['start_time'] = None
    _bot_state['strategies'] = []
    _bot_state['positions'] = []
    _bot_state['orders'] = []
    _bot_state['portfolio'] = None
    
    return {
        "message": "System reset successfully",
        "timestamp": datetime.now().isoformat()
    }


@router.get("/analytics/equity_curve")
async def get_equity_curve(period: str = '1d'):
    """Get equity curve data"""
    return {
        "period": period,
        "data": [],
        "timestamp": datetime.now().isoformat()
    }


@router.get("/analytics/drawdown")
async def get_drawdown():
    """Get drawdown analysis"""
    return {
        "current_drawdown_pct": 0.0,
        "max_drawdown_pct": 0.0,
        "drawdown_duration_days": 0,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/analytics/trade_distribution")
async def get_trade_distribution():
    """Get trade distribution statistics"""
    return {
        "by_symbol": {},
        "by_strategy": {},
        "by_hour": {},
        "timestamp": datetime.now().isoformat()
    }


@router.get("/risk/status")
async def get_risk_status():
    """Get current risk status"""
    return {
        "circuit_breaker_triggered": False,
        "daily_drawdown_pct": 0.0,
        "total_exposure_pct": 0.0,
        "leverage_ratio": 1.0,
        "margin_usage_pct": 0.0,
        "timestamp": datetime.now().isoformat()
    }


@router.get("/risk/limits")
async def get_risk_limits():
    """Get configured risk limits"""
    return {
        "max_position_risk_pct": 2.0,
        "max_daily_drawdown_pct": 5.0,
        "max_total_exposure_pct": 80.0,
        "max_leverage": 10.0,
        "timestamp": datetime.now().isoformat()
    }
