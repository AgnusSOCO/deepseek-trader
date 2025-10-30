"""
Tests for Phase N1: Data and Prompt Preparation

Tests:
- PriceFeed multi-timeframe data methods
- PromptBuilder nof1-style prompt generation
- Funding rate and order book fetching
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from src.data.price_feed import PriceFeed, OHLCVWindow
from src.ai.prompt_builder import PromptBuilder


class TestPriceFeedMultiTimeframe:
    """Test PriceFeed multi-timeframe methods"""
    
    def test_get_multi_timeframe_data(self):
        """Test getting data across multiple timeframes"""
        price_feed = PriceFeed(
            exchange_id='binance',
            api_key='test',
            api_secret='test',
            symbols=['BTC/USDT'],
            timeframes=['1m', '5m', '1h'],
            testnet=True
        )
        
        df_1m = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [1000, 1100, 1200]
        })
        
        df_5m = pd.DataFrame({
            'open': [100, 105],
            'high': [106, 107],
            'low': [99, 104],
            'close': [105, 106],
            'volume': [5000, 5100]
        })
        
        price_feed.ohlcv_windows[('BTC/USDT', '1m')] = OHLCVWindow(
            symbol='BTC/USDT',
            timeframe='1m',
            df=df_1m
        )
        
        price_feed.ohlcv_windows[('BTC/USDT', '5m')] = OHLCVWindow(
            symbol='BTC/USDT',
            timeframe='5m',
            df=df_5m
        )
        
        result = price_feed.get_multi_timeframe_data('BTC/USDT', ['1m', '5m'])
        
        assert '1m' in result
        assert '5m' in result
        assert len(result['1m']) == 3
        assert len(result['5m']) == 2
        assert result['1m']['close'].iloc[-1] == 102.5
        assert result['5m']['close'].iloc[-1] == 106
    
    def test_get_multi_timeframe_data_mexc_3m_fallback(self):
        """Test MEXC 3m fallback to 5m"""
        price_feed = PriceFeed(
            exchange_id='mexc',
            api_key='test',
            api_secret='test',
            symbols=['BTC/USDT'],
            timeframes=['5m'],
            testnet=True
        )
        
        df_5m = pd.DataFrame({
            'open': [100, 105],
            'high': [106, 107],
            'low': [99, 104],
            'close': [105, 106],
            'volume': [5000, 5100]
        })
        
        price_feed.ohlcv_windows[('BTC/USDT', '5m')] = OHLCVWindow(
            symbol='BTC/USDT',
            timeframe='5m',
            df=df_5m
        )
        
        result = price_feed.get_multi_timeframe_data('BTC/USDT', ['3m'])
        
        assert '3m' in result
        assert len(result['3m']) == 2
    
    def test_get_time_series_arrays(self):
        """Test getting compact time-series arrays for LLM"""
        price_feed = PriceFeed(
            exchange_id='binance',
            api_key='test',
            api_secret='test',
            symbols=['BTC/USDT'],
            timeframes=['1m'],
            testnet=True
        )
        
        df = pd.DataFrame({
            'open': [100, 101, 102],
            'high': [101, 102, 103],
            'low': [99, 100, 101],
            'close': [100.5, 101.5, 102.5],
            'volume': [1000, 1100, 1200],
            'ema_12': [100.2, 101.2, 102.2],
            'ema_26': [100.1, 101.1, 102.1],
            'rsi': [45, 50, 55],
            'macd': [0.1, 0.2, 0.3],
            'macd_signal': [0.05, 0.15, 0.25]
        })
        
        price_feed.ohlcv_windows[('BTC/USDT', '1m')] = OHLCVWindow(
            symbol='BTC/USDT',
            timeframe='1m',
            df=df
        )
        
        result = price_feed.get_time_series_arrays('BTC/USDT', ['1m'], lookback_bars=3)
        
        assert '1m' in result
        assert 'close' in result['1m']
        assert 'ema_12' in result['1m']
        assert 'rsi' in result['1m']
        assert result['1m']['close'] == [100.5, 101.5, 102.5]
        assert result['1m']['rsi'] == [45, 50, 55]
    
    @pytest.mark.asyncio
    async def test_get_funding_rate(self):
        """Test funding rate fetching"""
        price_feed = PriceFeed(
            exchange_id='binance',
            api_key='test',
            api_secret='test',
            symbols=['BTC/USDT'],
            timeframes=['1m'],
            testnet=True
        )
        
        mock_exchange = AsyncMock()
        mock_exchange.fetch_funding_rate = AsyncMock(return_value={
            'fundingRate': 0.0001,
            'fundingTimestamp': 1234567890,
            'nextFundingTime': 1234567900,
            'info': {}
        })
        
        price_feed.exchange = mock_exchange
        
        result = await price_feed.get_funding_rate('BTC/USDT')
        
        assert result is not None
        assert result['funding_rate'] == 0.0001
        assert 'next_funding_time' in result
    
    @pytest.mark.asyncio
    async def test_get_order_book(self):
        """Test order book fetching"""
        price_feed = PriceFeed(
            exchange_id='binance',
            api_key='test',
            api_secret='test',
            symbols=['BTC/USDT'],
            timeframes=['1m'],
            testnet=True
        )
        
        mock_exchange = AsyncMock()
        mock_exchange.fetch_order_book = AsyncMock(return_value={
            'timestamp': 1234567890,
            'bids': [[100, 10], [99, 20], [98, 30]],
            'asks': [[101, 5], [102, 10], [103, 15]]
        })
        
        price_feed.exchange = mock_exchange
        
        result = await price_feed.get_order_book('BTC/USDT')
        
        assert result is not None
        assert 'imbalance' in result
        assert 'spread' in result
        assert 'spread_percent' in result
        assert len(result['bids']) == 3
        assert len(result['asks']) == 3
        
        assert result['bid_volume'] == 60
        assert result['ask_volume'] == 30
        assert result['imbalance'] > 0


class TestPromptBuilder:
    """Test PromptBuilder nof1-style prompt generation"""
    
    def test_init_conservative_strategy(self):
        """Test initialization with conservative strategy"""
        builder = PromptBuilder(strategy_name='conservative', interval_minutes=5)
        
        assert builder.strategy_name == 'conservative'
        assert builder.interval_minutes == 5
        assert builder.strategy_params['leverage_min'] == 15
        assert builder.strategy_params['leverage_max'] == 20
    
    def test_init_aggressive_strategy(self):
        """Test initialization with aggressive strategy"""
        builder = PromptBuilder(strategy_name='aggressive', interval_minutes=5)
        
        assert builder.strategy_params['leverage_min'] == 20
        assert builder.strategy_params['leverage_max'] == 25
        assert builder.strategy_params['position_size_max'] == 32
    
    def test_build_prompt_basic(self):
        """Test basic prompt building"""
        builder = PromptBuilder(strategy_name='balanced', interval_minutes=5)
        
        market_data = {
            '1m': {
                'close': [100, 101, 102],
                'ema_12': [100.2, 101.2, 102.2],
                'ema_26': [100.1, 101.1, 102.1],
                'rsi': [45, 50, 55],
                'macd': [0.1, 0.2, 0.3],
                'macd_signal': [0.05, 0.15, 0.25],
                'volume': [1000, 1100, 1200],
                'volume_avg': [1000, 1050, 1100]
            }
        }
        
        account_info = {
            'balance': 10000,
            'unrealized_pnl': 100,
            'total_equity': 10100,
            'peak_equity': 10500,
            'drawdown_percent': 3.8,
            'daily_pnl': 50,
            'sharpe_ratio': 1.5
        }
        
        positions = []
        trade_history = []
        recent_decisions = []
        
        prompt = builder.build_prompt(
            symbol='BTC/USDT',
            market_data=market_data,
            account_info=account_info,
            positions=positions,
            trade_history=trade_history,
            recent_decisions=recent_decisions
        )
        
        assert 'BTC/USDT' in prompt
        assert 'Balance: $10000.00' in prompt
        assert 'Drawdown from Peak: 3.80%' in prompt
        assert 'No open positions' in prompt
        assert 'BALANCED STRATEGY' in prompt
        assert 'OPEN_LONG' in prompt
        assert 'OPEN_SHORT' in prompt
    
    def test_build_prompt_with_positions(self):
        """Test prompt with open positions"""
        builder = PromptBuilder(strategy_name='balanced', interval_minutes=5)
        
        market_data = {'1m': {'close': [100]}}
        
        account_info = {
            'balance': 10000,
            'unrealized_pnl': 200,
            'total_equity': 10200,
            'peak_equity': 10500,
            'drawdown_percent': 2.9,
            'daily_pnl': 100,
            'sharpe_ratio': 1.8
        }
        
        positions = [{
            'side': 'long',
            'symbol': 'BTC/USDT',
            'leverage': 20,
            'entry_price': 100,
            'current_price': 102,
            'unrealized_pnl': 200,
            'opened_at': datetime.now() - timedelta(hours=10),
            'peak_pnl_percent': 5.0
        }]
        
        trade_history = []
        recent_decisions = []
        
        prompt = builder.build_prompt(
            symbol='BTC/USDT',
            market_data=market_data,
            account_info=account_info,
            positions=positions,
            trade_history=trade_history,
            recent_decisions=recent_decisions
        )
        
        assert 'Position: BTC/USDT LONG' in prompt
        assert 'Leverage: 20x' in prompt
        assert 'Holding Time: 10' in prompt
        assert 'Remaining: 26' in prompt
    
    def test_build_prompt_with_drawdown_warnings(self):
        """Test prompt with drawdown warnings"""
        builder = PromptBuilder(strategy_name='balanced', interval_minutes=5)
        
        market_data = {'1m': {'close': [100]}}
        
        account_info = {
            'balance': 8500,
            'unrealized_pnl': -500,
            'total_equity': 8000,
            'peak_equity': 10000,
            'drawdown_percent': 20,
            'daily_pnl': -500,
            'sharpe_ratio': 0.5
        }
        
        positions = []
        trade_history = []
        recent_decisions = []
        
        prompt = builder.build_prompt(
            symbol='BTC/USDT',
            market_data=market_data,
            account_info=account_info,
            positions=positions,
            trade_history=trade_history,
            recent_decisions=recent_decisions
        )
        
        assert '🚨 CRITICAL WARNING' in prompt
        assert 'MUST CLOSE ALL POSITIONS' in prompt
    
    def test_build_prompt_with_trade_history(self):
        """Test prompt with trade history"""
        builder = PromptBuilder(strategy_name='balanced', interval_minutes=5)
        
        market_data = {'1m': {'close': [100]}}
        
        account_info = {
            'balance': 10000,
            'unrealized_pnl': 0,
            'total_equity': 10000,
            'peak_equity': 10000,
            'drawdown_percent': 0,
            'daily_pnl': 0,
            'sharpe_ratio': 1.0
        }
        
        positions = []
        
        trade_history = [
            {
                'side': 'long',
                'symbol': 'BTC/USDT',
                'pnl': 100,
                'pnl_percent': 5.0,
                'closed_at': '2024-01-01 10:00:00'
            },
            {
                'side': 'short',
                'symbol': 'ETH/USDT',
                'pnl': -50,
                'pnl_percent': -2.5,
                'closed_at': '2024-01-01 11:00:00'
            }
        ]
        
        recent_decisions = []
        
        prompt = builder.build_prompt(
            symbol='BTC/USDT',
            market_data=market_data,
            account_info=account_info,
            positions=positions,
            trade_history=trade_history,
            recent_decisions=recent_decisions
        )
        
        assert 'RECENT TRADES' in prompt
        assert 'WIN' in prompt
        assert 'LOSS' in prompt
        assert 'Win Rate: 50.0%' in prompt
    
    def test_format_structured_output_schema(self):
        """Test structured output schema generation"""
        builder = PromptBuilder(strategy_name='balanced', interval_minutes=5)
        
        schema = builder.format_structured_output_schema()
        
        assert schema['type'] == 'object'
        assert 'action' in schema['properties']
        assert 'leverage' in schema['properties']
        assert 'confidence' in schema['properties']
        
        assert schema['properties']['action']['enum'] == ['OPEN_LONG', 'OPEN_SHORT', 'CLOSE', 'HOLD']
        assert schema['properties']['leverage']['minimum'] == 18
        assert schema['properties']['leverage']['maximum'] == 23


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
