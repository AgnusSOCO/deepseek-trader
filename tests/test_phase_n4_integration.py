"""
Phase N4 Integration Tests

Tests the complete nof1.ai alignment implementation end-to-end:
1. Structured JSON → Execution Mapping
2. Drawdown Gates (15%, 20%)
3. 36-Hour TTL Exit
4. Tiered Trailing Profit
5. Long/Short Execution
6. Exit Loop Response Time
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
import json

from src.strategies.single_agent_strategy import SingleAgentStrategy, TradingDecision
from src.strategies.base_strategy import TradingSignal, SignalAction
from src.autonomous.enhanced_risk_manager import EnhancedRiskManager
from src.autonomous.exit_plan_monitor import ExitPlanMonitor, ExitPlan, ExitReason



class TestStructuredJSONToExecution:
    """Test that LLM decisions flow correctly through the system"""
    
    @pytest.mark.asyncio
    async def test_single_agent_generates_valid_decision(self):
        """Test SingleAgentStrategy generates valid TradingDecision"""
        mock_price_feed = Mock()
        mock_price_feed.get_time_series_arrays.return_value = {
            '1m': {'close': [100, 101, 102], 'volume': [1000, 1100, 1200]}
        }
        mock_price_feed.get_latest_price.return_value = 50000.0
        mock_price_feed.get_funding_rate = AsyncMock(return_value={'funding_rate': 0.0001})
        mock_price_feed.get_order_book = AsyncMock(return_value={'bids': [[50000, 1.0]], 'asks': [[50001, 1.0]]})
        
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key",
            price_feed=mock_price_feed,
            min_confidence=0.65
        )
        
        mock_response = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'action': 'OPEN_LONG',
                        'symbol': 'BTC/USDT',
                        'leverage': 20,
                        'position_size_percent': 25,
                        'stop_loss_percent': -3.0,
                        'take_profit_percent': 8.0,
                        'reasoning': 'Strong bullish momentum',
                        'confidence': 0.85
                    })
                }
            }]
        }
        
        strategy.openrouter_client.chat_completion = AsyncMock(return_value=mock_response)
        signal = await strategy.generate_signal("BTC/USDT", "1h", {})
        
        assert signal is not None
        assert isinstance(signal, TradingSignal)
        assert signal.action == SignalAction.BUY
        assert signal.confidence == 0.85
        assert signal.metadata['leverage'] == 20
        assert signal.position_size == 0.25
    
    def test_decision_converts_to_signal_correctly(self):
        """Test TradingDecision converts to TradingSignal with correct fields"""
        strategy = SingleAgentStrategy(openrouter_api_key="test_key")
        
        decision = TradingDecision(
            action="OPEN_LONG",
            symbol="BTC/USDT",
            leverage=20,
            position_size_percent=25,
            stop_loss_percent=-3.0,
            take_profit_percent=8.0,
            reasoning="Bullish",
            confidence=0.85
        )
        
        signal = strategy._convert_decision_to_signal("BTC/USDT", decision)
        
        assert signal.action == SignalAction.BUY
        assert signal.confidence == 0.85
        assert signal.position_size == 0.25
        assert signal.metadata['leverage'] == 20
    
    def test_risk_checks_applied_before_execution(self):
        """Test risk checks are applied before execution"""
        risk_manager = EnhancedRiskManager(
            initial_capital=10000,
            max_position_size_pct=30.0,
            max_daily_loss_pct=5.0,
            max_daily_trades=20
        )
        
        assert risk_manager.can_trade_today() == True
        assert risk_manager.can_open_position("BTC/USDT") == True



class TestDrawdownGates:
    """Test account-level drawdown protection"""
    
    def test_15_percent_drawdown_sets_no_new_positions(self):
        """Test 15% drawdown sets no_new_positions flag"""
        risk_manager = EnhancedRiskManager(
            initial_capital=10000,
            account_drawdown_warn_pct=15.0,
            account_drawdown_stop_pct=20.0
        )
        
        risk_manager.peak_capital = 10000
        risk_manager.current_capital = 8500
        risk_manager.check_drawdown_protection()
        
        assert risk_manager.no_new_positions == True
        assert risk_manager.trading_paused == False
        assert risk_manager.can_open_position("BTC/USDT") == False
        assert risk_manager.can_trade_today() == True
    
    def test_20_percent_drawdown_pauses_trading(self):
        """Test 20% drawdown pauses all trading"""
        risk_manager = EnhancedRiskManager(
            initial_capital=10000,
            account_drawdown_warn_pct=15.0,
            account_drawdown_stop_pct=20.0
        )
        
        risk_manager.peak_capital = 10000
        risk_manager.current_capital = 8000
        risk_manager.check_drawdown_protection()
        
        assert risk_manager.no_new_positions == True
        assert risk_manager.trading_paused == True
        assert risk_manager.can_trade_today() == False
    
    def test_drawdown_recovery_clears_flags(self):
        """Test drawdown recovery clears protection flags"""
        risk_manager = EnhancedRiskManager(
            initial_capital=10000,
            account_drawdown_warn_pct=15.0,
            account_drawdown_stop_pct=20.0
        )
        
        risk_manager.peak_capital = 10000
        risk_manager.current_capital = 8000
        risk_manager.check_drawdown_protection()
        assert risk_manager.trading_paused == True
        
        risk_manager.current_capital = 9000
        risk_manager.check_drawdown_protection()
        
        assert risk_manager.no_new_positions == False
        assert risk_manager.trading_paused == False



class TestThirtySixHourTTL:
    """Test 36-hour max holding time enforcement"""
    
    def test_position_exits_after_36_hours(self):
        """Test position closes after 36 hours"""
        monitor = ExitPlanMonitor(max_holding_hours=36.0)
        
        created_at = datetime.now() - timedelta(hours=37)
        plan = ExitPlan(
            position_id="test_pos_1",
            symbol="BTC/USDT",
            entry_price=50000.0,
            stop_loss=48500.0,
            take_profit=54000.0,
            invalidation_conditions=["ADX < 25"],
            created_at=created_at,
            leverage=20.0
        )
        
        monitor.exit_plans["test_pos_1"] = plan
        result = monitor.check_exit_conditions("test_pos_1", 51000.0, {}, {})
        
        assert result is not None
        assert result['should_exit'] == True
        assert result['reason'] == ExitReason.TIMEOUT
    
    def test_leverage_adjusted_pnl_calculated(self):
        """Test leverage-adjusted P&L calculation at exit"""
        monitor = ExitPlanMonitor(max_holding_hours=36.0)
        
        created_at = datetime.now() - timedelta(hours=37)
        plan = ExitPlan(
            position_id="test_pos_3",
            symbol="BTC/USDT",
            entry_price=50000.0,
            stop_loss=48500.0,
            take_profit=54000.0,
            invalidation_conditions=[],
            created_at=created_at,
            leverage=20.0
        )
        
        monitor.exit_plans["test_pos_3"] = plan
        result = monitor.check_exit_conditions("test_pos_3", 51000.0, {}, {})
        
        assert result is not None
        assert 'P&L' in result['details'] or 'pnl' in result['details'].lower()



class TestTieredTrailingProfit:
    """Test tiered trailing stop-profit logic"""
    
    def test_8_percent_peak_moves_stop_to_3(self):
        """Test +8% peak moves stop to +3%"""
        monitor = ExitPlanMonitor()
        
        plan = ExitPlan(
            position_id="test_pos_4",
            symbol="BTC/USDT",
            entry_price=50000.0,
            stop_loss=48500.0,
            take_profit=54000.0,
            invalidation_conditions=[],
            leverage=20.0,
            tiered_trailing_enabled=True
        )
        
        monitor.exit_plans["test_pos_4"] = plan
        monitor.check_tiered_trailing_profit("test_pos_4", 50200.0)
        
        updated_plan = monitor.exit_plans["test_pos_4"]
        assert updated_plan.stop_loss >= 50065.0
    
    def test_30_percent_pullback_triggers_exit(self):
        """Test 30% pullback from peak triggers immediate exit"""
        monitor = ExitPlanMonitor()
        
        plan = ExitPlan(
            position_id="test_pos_7",
            symbol="BTC/USDT",
            entry_price=50000.0,
            stop_loss=48500.0,
            take_profit=54000.0,
            invalidation_conditions=[],
            leverage=20.0,
            peak_pnl_pct=20.0,
            tiered_trailing_enabled=True
        )
        
        monitor.exit_plans["test_pos_7"] = plan
        result = monitor.check_tiered_trailing_profit("test_pos_7", 50200.0)
        
        assert result is not None
        assert result['should_exit'] == True
        assert result['reason'] == ExitReason.TRAILING_STOP



class TestLongShortExecution:
    """Test both long and short position execution"""
    
    @pytest.mark.asyncio
    async def test_open_long_signal_executes(self):
        """Test OPEN_LONG signal executes correctly"""
        mock_price_feed = Mock()
        mock_price_feed.get_time_series_arrays.return_value = {'1m': {'close': [100, 101, 102]}}
        mock_price_feed.get_latest_price.return_value = 50000.0
        mock_price_feed.get_funding_rate = AsyncMock(return_value={'funding_rate': 0.0001})
        mock_price_feed.get_order_book = AsyncMock(return_value={'bids': [], 'asks': []})
        
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key",
            price_feed=mock_price_feed
        )
        
        mock_response = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'action': 'OPEN_LONG',
                        'symbol': 'BTC/USDT',
                        'leverage': 20,
                        'position_size_percent': 25,
                        'stop_loss_percent': -3.0,
                        'take_profit_percent': 8.0,
                        'reasoning': 'Bullish',
                        'confidence': 0.85
                    })
                }
            }]
        }
        
        strategy.openrouter_client.chat_completion = AsyncMock(return_value=mock_response)
        signal = await strategy.generate_signal("BTC/USDT", "1h", {})
        
        assert signal is not None
        assert signal.action == SignalAction.BUY
    
    @pytest.mark.asyncio
    async def test_open_short_signal_executes(self):
        """Test OPEN_SHORT signal executes correctly"""
        mock_price_feed = Mock()
        mock_price_feed.get_time_series_arrays.return_value = {'1m': {'close': [100, 101, 102]}}
        mock_price_feed.get_latest_price.return_value = 50000.0
        mock_price_feed.get_funding_rate = AsyncMock(return_value={'funding_rate': 0.0001})
        mock_price_feed.get_order_book = AsyncMock(return_value={'bids': [], 'asks': []})
        
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key",
            price_feed=mock_price_feed
        )
        
        mock_response = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'action': 'OPEN_SHORT',
                        'symbol': 'BTC/USDT',
                        'leverage': 18,
                        'position_size_percent': 20,
                        'stop_loss_percent': -2.5,
                        'take_profit_percent': 6.0,
                        'reasoning': 'Bearish',
                        'confidence': 0.75
                    })
                }
            }]
        }
        
        strategy.openrouter_client.chat_completion = AsyncMock(return_value=mock_response)
        signal = await strategy.generate_signal("BTC/USDT", "1h", {})
        
        assert signal is not None
        assert signal.action == SignalAction.SELL



class TestExitLoopResponseTime:
    """Test exit monitoring responds quickly"""
    
    def test_exit_monitoring_responds_quickly(self):
        """Test exit monitoring responds <3 seconds"""
        monitor = ExitPlanMonitor()
        
        for i in range(10):
            plan = ExitPlan(
                position_id=f"test_pos_{i}",
                symbol="BTC/USDT",
                entry_price=50000.0,
                stop_loss=48500.0,
                take_profit=54000.0,
                invalidation_conditions=[],
                leverage=20.0
            )
            monitor.exit_plans[f"test_pos_{i}"] = plan
        
        import time
        start_time = time.time()
        
        for i in range(10):
            monitor.check_exit_conditions(f"test_pos_{i}", 51000.0, {}, {})
        
        elapsed_time = time.time() - start_time
        assert elapsed_time < 3.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
