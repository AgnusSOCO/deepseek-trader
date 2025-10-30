"""
Tests for SingleAgentStrategy (Phase N2)

Tests:
- Strategy initialization
- LLM decision generation and validation
- JSON extraction and Pydantic validation
- Signal conversion
- Integration with PriceFeed, PerformanceMonitor, RiskManager
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.strategies.single_agent_strategy import (
    SingleAgentStrategy,
    TradingDecision
)
from src.strategies.base_strategy import TradingSignal, SignalAction


class TestTradingDecision:
    """Test Pydantic TradingDecision model"""
    
    def test_valid_open_long_decision(self):
        """Test valid OPEN_LONG decision"""
        decision = TradingDecision(
            action="OPEN_LONG",
            symbol="BTC/USDT",
            leverage=20,
            position_size_percent=25,
            stop_loss_percent=-3.0,
            take_profit_percent=8.0,
            reasoning="Strong bullish momentum across all timeframes",
            confidence=0.85
        )
        
        assert decision.action == "OPEN_LONG"
        assert decision.leverage == 20
        assert decision.confidence == 0.85
    
    def test_valid_hold_decision(self):
        """Test valid HOLD decision"""
        decision = TradingDecision(
            action="HOLD",
            reasoning="No clear setup, waiting for better opportunity",
            confidence=0.5
        )
        
        assert decision.action == "HOLD"
        assert decision.symbol is None
        assert decision.leverage is None
    
    def test_invalid_action(self):
        """Test invalid action raises ValidationError"""
        with pytest.raises(Exception):
            TradingDecision(
                action="INVALID_ACTION",
                reasoning="Test",
                confidence=0.5
            )
    
    def test_invalid_confidence_range(self):
        """Test confidence must be 0-1"""
        with pytest.raises(Exception):
            TradingDecision(
                action="HOLD",
                reasoning="Test",
                confidence=1.5
            )
    
    def test_invalid_leverage_range(self):
        """Test leverage must be 1-25"""
        with pytest.raises(Exception):
            TradingDecision(
                action="OPEN_LONG",
                symbol="BTC/USDT",
                leverage=30,
                position_size_percent=25,
                reasoning="Test",
                confidence=0.8
            )


class TestSingleAgentStrategy:
    """Test SingleAgentStrategy implementation"""
    
    def test_initialization(self):
        """Test strategy initialization"""
        strategy = SingleAgentStrategy(
            name="TestAgent",
            openrouter_api_key="test_key",
            model_name="deepseek/deepseek-chat",
            strategy_profile="balanced",
            interval_minutes=5,
            min_confidence=0.65
        )
        
        assert strategy.name == "TestAgent"
        assert strategy.strategy_profile == "balanced"
        assert strategy.min_confidence == 0.65
        assert strategy.interval_minutes == 5
    
    def test_extract_json_from_plain_response(self):
        """Test extracting JSON from plain response"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        
        response = '{"action": "HOLD", "reasoning": "Test", "confidence": 0.5}'
        
        result = strategy._extract_json_from_response(response)
        
        assert result is not None
        assert result['action'] == 'HOLD'
        assert result['confidence'] == 0.5
    
    def test_extract_json_from_markdown_response(self):
        """Test extracting JSON from markdown code block"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        
        response = '''Here's my decision:
```json
{
    "action": "OPEN_LONG",
    "symbol": "BTC/USDT",
    "leverage": 20,
    "position_size_percent": 25,
    "stop_loss_percent": -3.0,
    "take_profit_percent": 8.0,
    "reasoning": "Strong bullish momentum",
    "confidence": 0.85
}
```
'''
        
        result = strategy._extract_json_from_response(response)
        
        assert result is not None
        assert result['action'] == 'OPEN_LONG'
        assert result['leverage'] == 20
        assert result['confidence'] == 0.85
    
    def test_extract_json_invalid_response(self):
        """Test handling invalid JSON response"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        
        response = "This is not valid JSON at all"
        
        result = strategy._extract_json_from_response(response)
        
        assert result is None
    
    def test_convert_decision_to_signal_open_long(self):
        """Test converting OPEN_LONG decision to signal"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        
        decision = TradingDecision(
            action="OPEN_LONG",
            symbol="BTC/USDT",
            leverage=20,
            position_size_percent=25,
            stop_loss_percent=-3.0,
            take_profit_percent=8.0,
            reasoning="Strong bullish momentum",
            confidence=0.85
        )
        
        signal = strategy._convert_decision_to_signal("BTC/USDT", decision)
        
        assert isinstance(signal, TradingSignal)
        assert signal.action == SignalAction.BUY
        assert signal.confidence == 0.85
        assert signal.metadata['leverage'] == 20
        assert signal.position_size == 0.25
        assert signal.metadata['stop_loss_percent'] == -3.0
        assert signal.metadata['take_profit_percent'] == 8.0
    
    def test_convert_decision_to_signal_open_short(self):
        """Test converting OPEN_SHORT decision to signal"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        
        decision = TradingDecision(
            action="OPEN_SHORT",
            symbol="BTC/USDT",
            leverage=18,
            position_size_percent=20,
            stop_loss_percent=-2.5,
            take_profit_percent=6.0,
            reasoning="Strong bearish momentum",
            confidence=0.75
        )
        
        signal = strategy._convert_decision_to_signal("BTC/USDT", decision)
        
        assert signal.action == SignalAction.SELL
        assert signal.confidence == 0.75
        assert signal.metadata['leverage'] == 18
        assert signal.position_size == 0.20
    
    def test_convert_decision_to_signal_close(self):
        """Test converting CLOSE decision to signal"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        
        decision = TradingDecision(
            action="CLOSE",
            reasoning="Stop loss triggered",
            confidence=0.9
        )
        
        signal = strategy._convert_decision_to_signal("BTC/USDT", decision)
        
        assert signal.action == SignalAction.CLOSE_LONG
        assert signal.confidence == 0.9
        assert signal.metadata['reasoning'] == "Stop loss triggered"
    
    def test_record_decision(self):
        """Test recording decisions for context"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        
        decision = TradingDecision(
            action="HOLD",
            reasoning="Waiting for better setup",
            confidence=0.6
        )
        
        strategy._record_decision(decision)
        
        assert len(strategy.recent_decisions) == 1
        assert strategy.recent_decisions[0]['action'] == 'HOLD'
        assert 'timestamp' in strategy.recent_decisions[0]
    
    def test_record_decision_max_limit(self):
        """Test recent decisions are limited to max_recent_decisions"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        strategy.max_recent_decisions = 5
        
        for i in range(10):
            decision = TradingDecision(
                action="HOLD",
                reasoning=f"Decision {i}",
                confidence=0.5
            )
            strategy._record_decision(decision)
        
        assert len(strategy.recent_decisions) == 5
        assert strategy.recent_decisions[-1]['reasoning'] == "Decision 9"
    
    def test_get_account_info_no_monitor(self):
        """Test getting account info with no PerformanceMonitor"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        
        account_info = strategy._get_account_info()
        
        assert account_info['balance'] == 10000
        assert account_info['drawdown_percent'] == 0
    
    def test_get_account_info_with_monitor(self):
        """Test getting account info from PerformanceMonitor"""
        mock_monitor = Mock()
        mock_monitor.get_snapshot.return_value = {
            'capital': 12000,
            'unrealized_pnl': 500,
            'total_equity': 12500,
            'peak_capital': 13000,
            'drawdown_percent': 3.8,
            'daily_pnl': 200,
            'sharpe_ratio': 1.5
        }
        
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key",
            performance_monitor=mock_monitor
        )
        
        account_info = strategy._get_account_info()
        
        assert account_info['balance'] == 12000
        assert account_info['drawdown_percent'] == 3.8
        assert account_info['sharpe_ratio'] == 1.5
    
    def test_get_positions_no_monitor(self):
        """Test getting positions with no PerformanceMonitor"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        
        positions = strategy._get_positions("BTC/USDT")
        
        assert positions == []
    
    def test_get_positions_with_monitor(self):
        """Test getting positions from PerformanceMonitor"""
        mock_monitor = Mock()
        mock_monitor.get_snapshot.return_value = {
            'positions': [
                {'symbol': 'BTC/USDT', 'side': 'long', 'size': 0.1},
                {'symbol': 'ETH/USDT', 'side': 'short', 'size': 1.0}
            ]
        }
        
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key",
            performance_monitor=mock_monitor
        )
        
        positions = strategy._get_positions("BTC/USDT")
        
        assert len(positions) == 1
        assert positions[0]['symbol'] == 'BTC/USDT'
    
    @pytest.mark.asyncio
    async def test_call_llm_with_retry_success(self):
        """Test successful LLM call"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        
        mock_response = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'action': 'HOLD',
                        'reasoning': 'No clear setup',
                        'confidence': 0.6
                    })
                }
            }]
        }
        
        strategy.openrouter_client.chat_completion = AsyncMock(return_value=mock_response)
        
        decision = await strategy._call_llm_with_retry("Test prompt")
        
        assert decision is not None
        assert decision.action == "HOLD"
        assert decision.confidence == 0.6
    
    @pytest.mark.asyncio
    async def test_call_llm_with_retry_invalid_json(self):
        """Test LLM call with invalid JSON response"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key",
            max_retries=2
        )
        
        mock_response = {
            'choices': [{
                'message': {
                    'content': 'This is not valid JSON'
                }
            }]
        }
        
        strategy.openrouter_client.chat_completion = AsyncMock(return_value=mock_response)
        
        decision = await strategy._call_llm_with_retry("Test prompt")
        
        assert decision is None
    
    @pytest.mark.asyncio
    async def test_call_llm_with_retry_validation_error(self):
        """Test LLM call with Pydantic validation error"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key",
            max_retries=2
        )
        
        mock_response = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'action': 'INVALID_ACTION',
                        'reasoning': 'Test',
                        'confidence': 0.5
                    })
                }
            }]
        }
        
        strategy.openrouter_client.chat_completion = AsyncMock(return_value=mock_response)
        
        decision = await strategy._call_llm_with_retry("Test prompt")
        
        assert decision is None
    
    @pytest.mark.asyncio
    async def test_generate_signal_no_price_feed(self):
        """Test generate_signal with no PriceFeed"""
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key"
        )
        
        signal = await strategy.generate_signal("BTC/USDT", "1h", {})
        
        assert signal is None
    
    @pytest.mark.asyncio
    async def test_generate_signal_hold_decision(self):
        """Test generate_signal with HOLD decision"""
        mock_price_feed = Mock()
        mock_price_feed.get_time_series_arrays.return_value = {
            '1m': {'close': [100, 101, 102]}
        }
        mock_price_feed.get_funding_rate = AsyncMock(return_value=None)
        mock_price_feed.get_order_book = AsyncMock(return_value=None)
        
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key",
            price_feed=mock_price_feed
        )
        
        mock_response = {
            'choices': [{
                'message': {
                    'content': json.dumps({
                        'action': 'HOLD',
                        'reasoning': 'No clear setup',
                        'confidence': 0.6
                    })
                }
            }]
        }
        
        strategy.openrouter_client.chat_completion = AsyncMock(return_value=mock_response)
        
        signal = await strategy.generate_signal("BTC/USDT", "1h", {})
        
        assert signal is None
    
    @pytest.mark.asyncio
    async def test_generate_signal_below_min_confidence(self):
        """Test generate_signal with confidence below threshold"""
        mock_price_feed = Mock()
        mock_price_feed.get_time_series_arrays.return_value = {
            '1m': {'close': [100, 101, 102]}
        }
        mock_price_feed.get_funding_rate = AsyncMock(return_value=None)
        mock_price_feed.get_order_book = AsyncMock(return_value=None)
        
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key",
            price_feed=mock_price_feed,
            min_confidence=0.7
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
                        'reasoning': 'Weak signal',
                        'confidence': 0.6
                    })
                }
            }]
        }
        
        strategy.openrouter_client.chat_completion = AsyncMock(return_value=mock_response)
        
        signal = await strategy.generate_signal("BTC/USDT", "1h", {})
        
        assert signal is None
    
    @pytest.mark.asyncio
    async def test_generate_signal_success(self):
        """Test successful signal generation"""
        mock_price_feed = Mock()
        mock_price_feed.get_time_series_arrays.return_value = {
            '1m': {'close': [100, 101, 102]}
        }
        mock_price_feed.get_latest_price.return_value = 50000.0
        mock_price_feed.get_funding_rate = AsyncMock(return_value=None)
        mock_price_feed.get_order_book = AsyncMock(return_value=None)
        
        strategy = SingleAgentStrategy(
            openrouter_api_key="test_key",
            price_feed=mock_price_feed,
            min_confidence=0.7
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
        assert signal.action == SignalAction.BUY
        assert signal.confidence == 0.85
        assert signal.metadata['leverage'] == 20
        assert signal.position_size == 0.25
        assert len(strategy.recent_decisions) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
