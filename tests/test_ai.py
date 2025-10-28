"""
Tests for AI Module

Tests for DeepSeek client, prompts, response parser, agents, and multi-agent system.
"""

import pytest
import pytest_asyncio
import json
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from src.ai.deepseek_client import DeepSeekClient, APIUsageStats, CacheEntry
from src.ai.prompts import PromptTemplates
from src.ai.response_parser import ResponseParser, ParseResult
from src.ai.agents import (
    TechnicalAnalystAgent,
    SentimentAnalystAgent,
    MarketStructureAgent,
    BullResearcherAgent,
    BearResearcherAgent,
    TraderAgent,
    RiskManagerAgent,
    MultiAgentSystem
)


class TestDeepSeekClient:
    """Test DeepSeek API client"""
    
    @pytest_asyncio.fixture
    async def client(self):
        """Create DeepSeek client"""
        return DeepSeekClient(
            api_key="test_key",
            enable_cache=True,
            cache_ttl=300
        )
    
    def test_client_initialization(self, client):
        """Test client initialization"""
        assert client.enable_cache is True
        assert client.cache_ttl == 300
        assert len(client._cache) == 0
        assert client.usage_stats.total_requests == 0
    
    def test_cache_key_generation(self, client):
        """Test cache key generation"""
        messages = [{"role": "user", "content": "test"}]
        key1 = client._get_cache_key("deepseek-chat", messages, 0.7)
        key2 = client._get_cache_key("deepseek-chat", messages, 0.7)
        key3 = client._get_cache_key("deepseek-chat", messages, 0.8)
        
        assert key1 == key2  # Same parameters = same key
        assert key1 != key3  # Different temperature = different key
    
    def test_cache_entry_expiration(self):
        """Test cache entry expiration"""
        entry = CacheEntry(response="test", timestamp=datetime.now(), ttl_seconds=1)
        assert not entry.is_expired()
        
        import time
        time.sleep(1.1)
        assert entry.is_expired()
    
    def test_calculate_cost(self, client):
        """Test cost calculation"""
        cost = client._calculate_cost("deepseek-chat", 1000, 500)
        expected = (1000 / 1_000_000) * 0.14 + (500 / 1_000_000) * 0.28
        assert abs(cost - expected) < 0.0001
    
    def test_usage_stats(self):
        """Test usage statistics tracking"""
        stats = APIUsageStats()
        stats.add_request("deepseek-chat", 1000, 0.5)
        stats.add_request("deepseek-chat", 500, 0.3)
        stats.add_request("deepseek-reasoner", 2000, 1.0)
        
        assert stats.total_requests == 3
        assert stats.total_tokens == 3500
        assert abs(stats.total_cost - 1.8) < 0.0001
        assert stats.requests_by_model["deepseek-chat"] == 2
        assert stats.requests_by_model["deepseek-reasoner"] == 1
    
    @pytest.mark.asyncio
    async def test_chat_completion_with_mock(self, client):
        """Test chat completion with mocked API"""
        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content='{"test": "response"}'))]
        mock_response.usage = Mock(prompt_tokens=100, completion_tokens=50)
        
        with patch.object(client.client.chat.completions, 'create', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            
            result = await client.chat_completion(
                model="deepseek-chat",
                messages=[{"role": "user", "content": "test"}],
                temperature=0.7
            )
            
            assert result['content'] == '{"test": "response"}'
            assert result['usage']['total_tokens'] == 150
            assert result['cost'] > 0


class TestPromptTemplates:
    """Test prompt templates"""
    
    def test_technical_analyst_prompt(self):
        """Test technical analyst prompt generation"""
        ohlcv_data = [
            {'open': 50000, 'high': 51000, 'low': 49500, 'close': 50500, 'volume': 1000}
        ]
        indicators = {'rsi': 45.0, 'macd': 100.0}
        
        messages = PromptTemplates.technical_analyst(
            symbol="BTC/USDT",
            timeframe="5m",
            ohlcv_data=ohlcv_data,
            indicators=indicators,
            current_price=50500.0
        )
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert 'BTC/USDT' in messages[1]['content']
        assert '50500.00' in messages[1]['content']
    
    def test_sentiment_analyst_prompt(self):
        """Test sentiment analyst prompt generation"""
        messages = PromptTemplates.sentiment_analyst(
            symbol="BTC/USDT",
            funding_rate=0.01,
            open_interest=1000000.0,
            liquidations_24h={'longs': 50000, 'shorts': 30000},
            volume_24h=5000000.0
        )
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert 'BTC/USDT' in messages[1]['content']
        assert '0.0100' in messages[1]['content']
    
    def test_market_structure_prompt(self):
        """Test market structure prompt generation"""
        order_book = {
            'bids': [{'price': 50000, 'size': 1.0}],
            'asks': [{'price': 50100, 'size': 1.0}]
        }
        
        messages = PromptTemplates.market_structure(
            symbol="BTC/USDT",
            order_book=order_book,
            bid_ask_spread=100.0,
            volume_profile={'50000': 1000}
        )
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert 'BTC/USDT' in messages[1]['content']
    
    def test_bull_researcher_prompt(self):
        """Test bull researcher prompt generation"""
        messages = PromptTemplates.bull_researcher(
            symbol="BTC/USDT",
            technical_analysis={'trend': 'bullish'},
            sentiment_analysis={'sentiment': 'bullish'},
            market_structure={'liquidity_quality': 'good'},
            portfolio_state={'total_value': 10000}
        )
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert 'BTC/USDT' in messages[1]['content']
        assert 'bullish' in messages[1]['content']
    
    def test_bear_researcher_prompt(self):
        """Test bear researcher prompt generation"""
        messages = PromptTemplates.bear_researcher(
            symbol="BTC/USDT",
            technical_analysis={'trend': 'bearish'},
            sentiment_analysis={'sentiment': 'bearish'},
            market_structure={'liquidity_quality': 'poor'},
            portfolio_state={'total_value': 10000}
        )
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert 'BTC/USDT' in messages[1]['content']
    
    def test_trader_prompt(self):
        """Test trader prompt generation"""
        messages = PromptTemplates.trader(
            symbol="BTC/USDT",
            current_price=50000.0,
            bull_thesis={'thesis': 'bullish case'},
            bear_thesis={'thesis': 'bearish case'},
            portfolio_state={'total_value': 10000},
            account_balance=10000.0
        )
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert 'BTC/USDT' in messages[1]['content']
        assert '50000.00' in messages[1]['content']
    
    def test_risk_manager_prompt(self):
        """Test risk manager prompt generation"""
        messages = PromptTemplates.risk_manager(
            symbol="BTC/USDT",
            proposed_trade={'action': 'BUY', 'position_size_pct': 10},
            portfolio_metrics={'total_value': 10000},
            account_balance=10000.0,
            current_positions=[]
        )
        
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[1]['role'] == 'user'
        assert 'BTC/USDT' in messages[1]['content']


class TestResponseParser:
    """Test response parser"""
    
    def test_extract_json_direct(self):
        """Test extracting JSON directly"""
        response = '{"test": "value"}'
        result = ResponseParser.extract_json(response)
        assert result == response
    
    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code block"""
        response = 'Some text\n```json\n{"test": "value"}\n```\nMore text'
        result = ResponseParser.extract_json(response)
        assert result == '{"test": "value"}'
    
    def test_extract_json_from_text(self):
        """Test extracting JSON from surrounding text"""
        response = 'Here is the result: {"test": "value"} end'
        result = ResponseParser.extract_json(response)
        assert result == '{"test": "value"}'
    
    def test_parse_json_success(self):
        """Test successful JSON parsing"""
        response = '{"test": "value", "number": 42}'
        result = ResponseParser.parse_json(response)
        
        assert result.success is True
        assert result.data == {"test": "value", "number": 42}
        assert result.error is None
    
    def test_parse_json_failure(self):
        """Test failed JSON parsing"""
        response = 'This is not JSON'
        result = ResponseParser.parse_json(response)
        
        assert result.success is False
        assert result.data is None
        assert result.error is not None
    
    def test_validate_schema_success(self):
        """Test successful schema validation"""
        data = {"field1": "value1", "field2": "value2"}
        result = ResponseParser.validate_schema(data, ["field1", "field2"])
        
        assert result.success is True
        assert result.data == data
    
    def test_validate_schema_failure(self):
        """Test failed schema validation"""
        data = {"field1": "value1"}
        result = ResponseParser.validate_schema(data, ["field1", "field2"])
        
        assert result.success is False
        assert "field2" in result.error
    
    def test_parse_technical_analysis(self):
        """Test parsing technical analysis response"""
        response = json.dumps({
            'trend': 'bullish',
            'trend_strength': 75,
            'support_levels': [50000, 49000],
            'resistance_levels': [51000, 52000],
            'patterns': ['ascending triangle'],
            'key_observations': ['strong momentum'],
            'confidence': 80
        })
        
        result = ResponseParser.parse_technical_analysis(response)
        assert result.success is True
        assert result.data['trend'] == 'bullish'
    
    def test_parse_sentiment_analysis(self):
        """Test parsing sentiment analysis response"""
        response = json.dumps({
            'sentiment': 'bullish',
            'sentiment_score': 60,
            'market_mood': 'greedy',
            'key_factors': ['positive funding'],
            'warnings': [],
            'confidence': 75
        })
        
        result = ResponseParser.parse_sentiment_analysis(response)
        assert result.success is True
        assert result.data['sentiment'] == 'bullish'
    
    def test_parse_trading_decision(self):
        """Test parsing trading decision response"""
        response = json.dumps({
            'action': 'BUY',
            'rationale': 'Strong bullish signals',
            'confidence': 80,
            'position_size_pct': 10,
            'entry_price': 50000,
            'stop_loss': 49000,
            'take_profit': 52000,
            'timeframe': 'swing',
            'risk_reward_ratio': 2.0,
            'key_decision_factors': ['technical', 'sentiment']
        })
        
        result = ResponseParser.parse_trading_decision(response)
        assert result.success is True
        assert result.data['action'] == 'BUY'
    
    def test_parse_trading_decision_invalid_action(self):
        """Test parsing trading decision with invalid action"""
        response = json.dumps({
            'action': 'INVALID',
            'rationale': 'test',
            'confidence': 80,
            'position_size_pct': 10,
            'entry_price': 50000,
            'stop_loss': 49000,
            'take_profit': 52000,
            'timeframe': 'swing',
            'risk_reward_ratio': 2.0,
            'key_decision_factors': []
        })
        
        result = ResponseParser.parse_trading_decision(response)
        assert result.success is False
        assert 'Invalid action' in result.error
    
    def test_parse_risk_approval(self):
        """Test parsing risk approval response"""
        response = json.dumps({
            'approved': True,
            'rationale': 'Trade meets all risk criteria',
            'risk_score': 30,
            'concerns': [],
            'confidence': 90
        })
        
        result = ResponseParser.parse_risk_approval(response)
        assert result.success is True
        assert result.data['approved'] is True


class TestAgents:
    """Test AI agents"""
    
    @pytest_asyncio.fixture
    async def mock_client(self):
        """Create mock DeepSeek client"""
        client = Mock(spec=DeepSeekClient)
        client.chat_completion = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_technical_analyst_agent(self, mock_client):
        """Test technical analyst agent"""
        mock_client.chat_completion.return_value = {
            'content': json.dumps({
                'trend': 'bullish',
                'trend_strength': 75,
                'support_levels': [50000],
                'resistance_levels': [51000],
                'patterns': [],
                'key_observations': [],
                'confidence': 80
            }),
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'cost': 0.01,
            'elapsed_seconds': 1.0
        }
        
        agent = TechnicalAnalystAgent(mock_client)
        result = await agent.analyze(
            symbol="BTC/USDT",
            timeframe="5m",
            ohlcv_data=[],
            indicators={'rsi': 45},
            current_price=50000.0
        )
        
        assert result.success is True
        assert result.data['trend'] == 'bullish'
        assert result.agent_name == 'Technical Analyst'
    
    @pytest.mark.asyncio
    async def test_sentiment_analyst_agent(self, mock_client):
        """Test sentiment analyst agent"""
        mock_client.chat_completion.return_value = {
            'content': json.dumps({
                'sentiment': 'bullish',
                'sentiment_score': 60,
                'market_mood': 'greedy',
                'key_factors': [],
                'warnings': [],
                'confidence': 75
            }),
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'cost': 0.01,
            'elapsed_seconds': 1.0
        }
        
        agent = SentimentAnalystAgent(mock_client)
        result = await agent.analyze(
            symbol="BTC/USDT",
            funding_rate=0.01,
            open_interest=1000000,
            liquidations_24h={'longs': 0, 'shorts': 0},
            volume_24h=5000000
        )
        
        assert result.success is True
        assert result.data['sentiment'] == 'bullish'
    
    @pytest.mark.asyncio
    async def test_trader_agent(self, mock_client):
        """Test trader agent"""
        mock_client.chat_completion.return_value = {
            'content': json.dumps({
                'action': 'BUY',
                'rationale': 'Strong signals',
                'confidence': 80,
                'position_size_pct': 10,
                'entry_price': 50000,
                'stop_loss': 49000,
                'take_profit': 52000,
                'timeframe': 'swing',
                'risk_reward_ratio': 2.0,
                'key_decision_factors': []
            }),
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'cost': 0.01,
            'elapsed_seconds': 1.0
        }
        
        agent = TraderAgent(mock_client)
        result = await agent.decide(
            symbol="BTC/USDT",
            current_price=50000.0,
            bull_thesis={'thesis': 'bullish'},
            bear_thesis={'thesis': 'bearish'},
            portfolio_state={'total_value': 10000},
            account_balance=10000.0
        )
        
        assert result.success is True
        assert result.data['action'] == 'BUY'
    
    @pytest.mark.asyncio
    async def test_risk_manager_agent(self, mock_client):
        """Test risk manager agent"""
        mock_client.chat_completion.return_value = {
            'content': json.dumps({
                'approved': True,
                'rationale': 'Trade approved',
                'risk_score': 30,
                'concerns': [],
                'confidence': 90
            }),
            'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
            'cost': 0.01,
            'elapsed_seconds': 1.0
        }
        
        agent = RiskManagerAgent(mock_client)
        result = await agent.review(
            symbol="BTC/USDT",
            proposed_trade={'action': 'BUY'},
            portfolio_metrics={'total_value': 10000},
            account_balance=10000.0,
            current_positions=[]
        )
        
        assert result.success is True
        assert result.data['approved'] is True


class TestMultiAgentSystem:
    """Test multi-agent system"""
    
    @pytest_asyncio.fixture
    async def mock_client(self):
        """Create mock DeepSeek client"""
        client = Mock(spec=DeepSeekClient)
        client.chat_completion = AsyncMock()
        return client
    
    @pytest.mark.asyncio
    async def test_multi_agent_system_initialization(self, mock_client):
        """Test multi-agent system initialization"""
        system = MultiAgentSystem(mock_client)
        
        assert system.technical_analyst is not None
        assert system.sentiment_analyst is not None
        assert system.market_structure is not None
        assert system.bull_researcher is not None
        assert system.bear_researcher is not None
        assert system.trader is not None
        assert system.risk_manager is not None
    
    @pytest.mark.asyncio
    async def test_multi_agent_workflow_success(self, mock_client):
        """Test successful multi-agent workflow"""
        def mock_response(model, messages, **kwargs):
            content = messages[0]['content']
            
            if 'Technical Analyst' in content:
                data = {
                    'trend': 'bullish', 'trend_strength': 75,
                    'support_levels': [50000], 'resistance_levels': [51000],
                    'patterns': [], 'key_observations': [], 'confidence': 80
                }
            elif 'Sentiment Analyst' in content:
                data = {
                    'sentiment': 'bullish', 'sentiment_score': 60,
                    'market_mood': 'greedy', 'key_factors': [],
                    'warnings': [], 'confidence': 75
                }
            elif 'Market Structure' in content:
                data = {
                    'liquidity_quality': 'good', 'bid_ask_spread_assessment': 'normal',
                    'order_book_imbalance': 0, 'execution_recommendation': 'market',
                    'slippage_estimate_pct': 0.1, 'key_observations': [], 'confidence': 80
                }
            elif 'Bull Researcher' in content:
                data = {
                    'thesis': 'bullish case', 'supporting_evidence': [],
                    'price_targets': {'conservative': 51000, 'base': 52000, 'optimistic': 53000},
                    'timeframe': 'short', 'conviction': 80, 'risks_acknowledged': []
                }
            elif 'Bear Researcher' in content:
                data = {
                    'thesis': 'bearish case', 'risk_factors': [],
                    'price_targets': {'conservative': 49000, 'base': 48000, 'pessimistic': 47000},
                    'timeframe': 'short', 'conviction': 40, 'bull_counterarguments': []
                }
            elif 'Trader' in content:
                data = {
                    'action': 'BUY', 'rationale': 'Strong signals', 'confidence': 80,
                    'position_size_pct': 10, 'entry_price': 50000, 'stop_loss': 49000,
                    'take_profit': 52000, 'timeframe': 'swing', 'risk_reward_ratio': 2.0,
                    'key_decision_factors': []
                }
            else:  # Risk Manager
                data = {
                    'approved': True, 'rationale': 'Trade approved',
                    'risk_score': 30, 'concerns': [], 'confidence': 90
                }
            
            return {
                'content': json.dumps(data),
                'usage': {'prompt_tokens': 100, 'completion_tokens': 50, 'total_tokens': 150},
                'cost': 0.01,
                'elapsed_seconds': 1.0
            }
        
        mock_client.chat_completion.side_effect = mock_response
        
        system = MultiAgentSystem(mock_client)
        
        market_data = {
            'current_price': 50000.0,
            'ohlcv': [],
            'indicators': {'rsi': 45},
            'funding_rate': 0.01,
            'open_interest': 1000000,
            'liquidations_24h': {'longs': 0, 'shorts': 0},
            'volume_24h': 5000000,
            'order_book': {'bids': [], 'asks': []},
            'bid_ask_spread': 10.0,
            'volume_profile': {}
        }
        
        result = await system.execute_workflow(
            symbol="BTC/USDT",
            timeframe="5m",
            market_data=market_data,
            portfolio_state={'total_value': 10000},
            account_balance=10000.0,
            current_positions=[]
        )
        
        assert result.success is True
        assert result.final_decision is not None
        assert result.final_decision['action'] == 'BUY'
        assert result.technical_analysis is not None
        assert result.sentiment_analysis is not None
        assert result.bull_thesis is not None
        assert result.bear_thesis is not None
        assert result.trader_decision is not None
        assert result.risk_approval is not None
