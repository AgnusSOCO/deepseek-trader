"""
Performance Monitoring Dashboard (Phase E)

Web-based dashboard for real-time monitoring of autonomous trading system.
Provides visualization of metrics, trades, and system health.
"""

import logging
from typing import Any
from datetime import datetime
import json

logger = logging.getLogger(__name__)


async def run_dashboard(trading_system: Any, port: int = 8080) -> None:
    """
    Run web dashboard for monitoring
    
    Args:
        trading_system: AutonomousTradingSystem instance
        port: Port to run dashboard on
    """
    try:
        from aiohttp import web
        
        async def handle_index(request):
            """Serve dashboard HTML"""
            html = """
<!DOCTYPE html>
<html>
<head>
    <title>Autonomous Trading System Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #0f172a;
            color: #e2e8f0;
            padding: 20px;
        }
        .container { max-width: 1400px; margin: 0 auto; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
        }
        .header h1 { font-size: 32px; margin-bottom: 10px; }
        .header .status { font-size: 18px; opacity: 0.9; }
        .grid { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
            margin-bottom: 30px;
        }
        .card {
            background: #1e293b;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.2);
            border: 1px solid #334155;
        }
        .card h2 {
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
            color: #94a3b8;
            margin-bottom: 15px;
        }
        .metric {
            font-size: 36px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        .metric.positive { color: #10b981; }
        .metric.negative { color: #ef4444; }
        .metric.neutral { color: #3b82f6; }
        .label { font-size: 14px; color: #94a3b8; }
        .stats-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-top: 15px;
        }
        .stat-item {
            padding: 12px;
            background: #0f172a;
            border-radius: 8px;
        }
        .stat-label { font-size: 12px; color: #94a3b8; margin-bottom: 5px; }
        .stat-value { font-size: 20px; font-weight: 600; }
        .refresh-info {
            text-align: center;
            color: #64748b;
            margin-top: 20px;
            font-size: 14px;
        }
        .badge {
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 10px;
        }
        .badge.success { background: #10b981; color: white; }
        .badge.warning { background: #f59e0b; color: white; }
        .badge.danger { background: #ef4444; color: white; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 Autonomous Trading System</h1>
            <div class="status">
                <span id="status">Loading...</span>
                <span id="trading-badge" class="badge"></span>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>💰 Capital</h2>
                <div class="metric neutral" id="capital">$0.00</div>
                <div class="label">Current Capital</div>
            </div>
            
            <div class="card">
                <h2>📈 Total P&L</h2>
                <div class="metric" id="total-pnl">$0.00</div>
                <div class="label" id="total-pnl-pct">0.00%</div>
            </div>
            
            <div class="card">
                <h2>📊 Daily P&L</h2>
                <div class="metric" id="daily-pnl">$0.00</div>
                <div class="label">Today's Performance</div>
            </div>
            
            <div class="card">
                <h2>🎯 Open Positions</h2>
                <div class="metric neutral" id="open-positions">0</div>
                <div class="label" id="max-positions">/ 0 Max</div>
            </div>
        </div>
        
        <div class="grid">
            <div class="card">
                <h2>📊 Trading Statistics</h2>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Total Trades</div>
                        <div class="stat-value" id="total-trades">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Win Rate</div>
                        <div class="stat-value" id="win-rate">0%</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Daily Trades</div>
                        <div class="stat-value" id="daily-trades">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Max Drawdown</div>
                        <div class="stat-value" id="max-drawdown">0%</div>
                    </div>
                </div>
            </div>
            
            <div class="card">
                <h2>⚙️ System Status</h2>
                <div class="stats-grid">
                    <div class="stat-item">
                        <div class="stat-label">Uptime</div>
                        <div class="stat-value" id="uptime">0s</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Total Loops</div>
                        <div class="stat-value" id="total-loops">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Decisions</div>
                        <div class="stat-value" id="total-decisions">0</div>
                    </div>
                    <div class="stat-item">
                        <div class="stat-label">Strategies</div>
                        <div class="stat-value" id="strategies-count">0</div>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="refresh-info">
            Dashboard auto-refreshes every 5 seconds | Last updated: <span id="last-update">Never</span>
        </div>
    </div>
    
    <script>
        async function updateDashboard() {
            try {
                const response = await fetch('/api/status');
                const data = await response.json();
                
                document.getElementById('status').textContent = 
                    data.is_running ? '🟢 System Running' : '🔴 System Stopped';
                
                const tradingBadge = document.getElementById('trading-badge');
                if (data.enable_trading) {
                    tradingBadge.textContent = 'LIVE TRADING';
                    tradingBadge.className = 'badge danger';
                } else {
                    tradingBadge.textContent = 'SIMULATION';
                    tradingBadge.className = 'badge warning';
                }
                
                const riskStats = data.risk_stats || {};
                const engineStats = data.engine_stats || {};
                
                document.getElementById('capital').textContent = 
                    '$' + (riskStats.current_capital || 0).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                
                const totalPnl = riskStats.total_pnl || 0;
                const totalPnlPct = riskStats.total_pnl_pct || 0;
                const totalPnlEl = document.getElementById('total-pnl');
                totalPnlEl.textContent = '$' + totalPnl.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                totalPnlEl.className = 'metric ' + (totalPnl >= 0 ? 'positive' : 'negative');
                document.getElementById('total-pnl-pct').textContent = totalPnlPct.toFixed(2) + '%';
                
                const dailyPnl = riskStats.daily_pnl || 0;
                const dailyPnlEl = document.getElementById('daily-pnl');
                dailyPnlEl.textContent = '$' + dailyPnl.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                dailyPnlEl.className = 'metric ' + (dailyPnl >= 0 ? 'positive' : 'negative');
                
                document.getElementById('open-positions').textContent = engineStats.open_positions || 0;
                document.getElementById('max-positions').textContent = '/ ' + (engineStats.max_open_positions || 0) + ' Max';
                
                document.getElementById('total-trades').textContent = riskStats.total_trades || 0;
                document.getElementById('win-rate').textContent = (riskStats.daily_win_rate || 0).toFixed(1) + '%';
                document.getElementById('daily-trades').textContent = riskStats.daily_trades || 0;
                document.getElementById('max-drawdown').textContent = (riskStats.max_drawdown || 0).toFixed(2) + '%';
                
                document.getElementById('uptime').textContent = data.uptime_formatted || '0s';
                document.getElementById('total-loops').textContent = engineStats.total_loops || 0;
                document.getElementById('total-decisions').textContent = engineStats.total_decisions || 0;
                document.getElementById('strategies-count').textContent = data.strategies_count || 0;
                
                document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
            } catch (error) {
                console.error('Error updating dashboard:', error);
            }
        }
        
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
            """
            return web.Response(text=html, content_type='text/html')
        
        async def handle_status(request):
            """Serve status JSON"""
            try:
                status = trading_system.get_status()
                return web.json_response(status)
            except Exception as e:
                logger.error(f"Error getting status: {e}")
                return web.json_response({'error': str(e)}, status=500)
        
        async def handle_performance(request):
            """Serve performance report JSON"""
            try:
                report = trading_system.get_performance_report()
                return web.json_response(report)
            except Exception as e:
                logger.error(f"Error getting performance report: {e}")
                return web.json_response({'error': str(e)}, status=500)
        
        app = web.Application()
        app.router.add_get('/', handle_index)
        app.router.add_get('/api/status', handle_status)
        app.router.add_get('/api/performance', handle_performance)
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        
        logger.info(f"🌐 Dashboard running on http://0.0.0.0:{port}")
        
        while trading_system.is_running:
            await asyncio.sleep(1)
        
        await runner.cleanup()
    
    except ImportError:
        logger.error("aiohttp not installed, dashboard unavailable")
        logger.info("Install with: pip install aiohttp")
    except Exception as e:
        logger.error(f"Error running dashboard: {e}", exc_info=True)


import asyncio
