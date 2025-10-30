"""
Tests for AI Decision Database

Tests AI decision logging, retrieval, and statistics.
"""

import pytest
from datetime import datetime, timedelta
import json

from src.data.storage import SQLiteStorage, AIDecisionModel


@pytest.fixture
def storage():
    """Create a test SQLite storage instance"""
    storage = SQLiteStorage(db_path=":memory:")
    yield storage
    storage.close()


def test_save_ai_decision(storage):
    """Test saving an AI decision"""
    decision_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'BUY',
        'confidence': 0.85,
        'reasoning': 'Strong bullish momentum with RSI oversold',
        'market_context': json.dumps({'price': 50000, 'rsi': 35}),
        'position_size': 0.1,
        'entry_price': 50000.0,
        'stop_loss': 49000.0,
        'take_profit': 52000.0,
        'invalidation_condition': 'RSI > 70',
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    decision_id = storage.save_ai_decision(decision_data)
    
    assert decision_id > 0


def test_get_ai_decisions_empty(storage):
    """Test getting AI decisions from empty database"""
    decisions = storage.get_ai_decisions()
    
    assert decisions == []


def test_get_ai_decisions_single(storage):
    """Test getting a single AI decision"""
    decision_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'BUY',
        'confidence': 0.85,
        'reasoning': 'Strong bullish momentum',
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    storage.save_ai_decision(decision_data)
    
    decisions = storage.get_ai_decisions()
    assert len(decisions) == 1
    assert decisions[0]['symbol'] == 'BTC/USDT'
    assert decisions[0]['decision'] == 'BUY'
    assert decisions[0]['confidence'] == 0.85


def test_get_ai_decisions_multiple(storage):
    """Test getting multiple AI decisions"""
    for i in range(5):
        decision_data = {
            'timestamp': datetime.utcnow(),
            'symbol': f'BTC/USDT',
            'decision': 'BUY' if i % 2 == 0 else 'SELL',
            'confidence': 0.8 + i * 0.02,
            'reasoning': f'Decision {i}',
            'model_used': 'deepseek-chat',
            'strategy': 'SingleAgentStrategy'
        }
        storage.save_ai_decision(decision_data)
    
    decisions = storage.get_ai_decisions()
    assert len(decisions) == 5


def test_get_ai_decisions_filter_by_symbol(storage):
    """Test filtering AI decisions by symbol"""
    btc_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'BUY',
        'confidence': 0.85,
        'reasoning': 'BTC decision',
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    eth_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'ETH/USDT',
        'decision': 'SELL',
        'confidence': 0.75,
        'reasoning': 'ETH decision',
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    storage.save_ai_decision(btc_data)
    storage.save_ai_decision(eth_data)
    
    btc_decisions = storage.get_ai_decisions(symbol='BTC/USDT')
    assert len(btc_decisions) == 1
    assert btc_decisions[0]['symbol'] == 'BTC/USDT'


def test_get_ai_decisions_filter_by_strategy(storage):
    """Test filtering AI decisions by strategy"""
    strategy1_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'BUY',
        'confidence': 0.85,
        'reasoning': 'Strategy 1 decision',
        'model_used': 'deepseek-chat',
        'strategy': 'Strategy1'
    }
    
    strategy2_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'SELL',
        'confidence': 0.75,
        'reasoning': 'Strategy 2 decision',
        'model_used': 'deepseek-chat',
        'strategy': 'Strategy2'
    }
    
    storage.save_ai_decision(strategy1_data)
    storage.save_ai_decision(strategy2_data)
    
    strategy1_decisions = storage.get_ai_decisions(strategy='Strategy1')
    assert len(strategy1_decisions) == 1
    assert strategy1_decisions[0]['strategy'] == 'Strategy1'


def test_get_ai_decisions_filter_by_decision_type(storage):
    """Test filtering AI decisions by decision type"""
    buy_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'BUY',
        'confidence': 0.85,
        'reasoning': 'Buy decision',
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    sell_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'SELL',
        'confidence': 0.75,
        'reasoning': 'Sell decision',
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    storage.save_ai_decision(buy_data)
    storage.save_ai_decision(sell_data)
    
    buy_decisions = storage.get_ai_decisions(decision='BUY')
    assert len(buy_decisions) == 1
    assert buy_decisions[0]['decision'] == 'BUY'


def test_get_ai_decisions_filter_by_executed(storage):
    """Test filtering AI decisions by execution status"""
    executed_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'BUY',
        'confidence': 0.85,
        'reasoning': 'Executed decision',
        'executed': True,
        'trade_id': 123,
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    not_executed_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'SELL',
        'confidence': 0.75,
        'reasoning': 'Not executed decision',
        'executed': False,
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    storage.save_ai_decision(executed_data)
    storage.save_ai_decision(not_executed_data)
    
    executed_decisions = storage.get_ai_decisions(executed=True)
    assert len(executed_decisions) == 1
    assert executed_decisions[0]['executed'] is True


def test_update_ai_decision(storage):
    """Test updating an AI decision"""
    decision_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'BUY',
        'confidence': 0.85,
        'reasoning': 'Initial decision',
        'executed': False,
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    decision_id = storage.save_ai_decision(decision_data)
    
    updates = {
        'executed': True,
        'trade_id': 456,
        'entry_price': 50000.0
    }
    
    storage.update_ai_decision(decision_id, updates)
    
    decisions = storage.get_ai_decisions()
    assert decisions[0]['executed'] is True
    assert decisions[0]['trade_id'] == 456
    assert decisions[0]['entry_price'] == 50000.0


def test_update_ai_decision_with_outcome(storage):
    """Test updating an AI decision with outcome"""
    decision_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'BUY',
        'confidence': 0.85,
        'reasoning': 'Initial decision',
        'executed': True,
        'trade_id': 123,
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    decision_id = storage.save_ai_decision(decision_data)
    
    updates = {
        'outcome': 'win',
        'pnl': 500.0
    }
    
    storage.update_ai_decision(decision_id, updates)
    
    decisions = storage.get_ai_decisions()
    assert decisions[0]['outcome'] == 'win'
    assert decisions[0]['pnl'] == 500.0


def test_get_ai_decision_stats_empty(storage):
    """Test getting AI decision stats from empty database"""
    stats = storage.get_ai_decision_stats()
    
    assert stats['total_decisions'] == 0
    assert stats['executed_count'] == 0
    assert stats['execution_rate'] == 0.0
    assert stats['avg_confidence'] == 0.0
    assert stats['win_count'] == 0
    assert stats['loss_count'] == 0
    assert stats['win_rate'] == 0.0
    assert stats['total_pnl'] == 0.0


def test_get_ai_decision_stats_basic(storage):
    """Test getting basic AI decision stats"""
    for i in range(10):
        decision_data = {
            'timestamp': datetime.utcnow(),
            'symbol': 'BTC/USDT',
            'decision': 'BUY',
            'confidence': 0.8,
            'reasoning': f'Decision {i}',
            'executed': i < 5,
            'model_used': 'deepseek-chat',
            'strategy': 'SingleAgentStrategy'
        }
        storage.save_ai_decision(decision_data)
    
    stats = storage.get_ai_decision_stats()
    
    assert stats['total_decisions'] == 10
    assert stats['executed_count'] == 5
    assert stats['execution_rate'] == 0.5
    assert stats['avg_confidence'] == 0.8


def test_get_ai_decision_stats_with_outcomes(storage):
    """Test getting AI decision stats with outcomes"""
    for i in range(10):
        decision_data = {
            'timestamp': datetime.utcnow(),
            'symbol': 'BTC/USDT',
            'decision': 'BUY',
            'confidence': 0.8,
            'reasoning': f'Decision {i}',
            'executed': True,
            'outcome': 'win' if i < 7 else 'loss',
            'pnl': 100.0 if i < 7 else -50.0,
            'model_used': 'deepseek-chat',
            'strategy': 'SingleAgentStrategy'
        }
        storage.save_ai_decision(decision_data)
    
    stats = storage.get_ai_decision_stats()
    
    assert stats['total_decisions'] == 10
    assert stats['executed_count'] == 10
    assert stats['win_count'] == 7
    assert stats['loss_count'] == 3
    assert stats['win_rate'] == 0.7
    assert stats['total_pnl'] == 7 * 100.0 + 3 * (-50.0)


def test_get_ai_decision_stats_filter_by_strategy(storage):
    """Test getting AI decision stats filtered by strategy"""
    for i in range(5):
        decision_data = {
            'timestamp': datetime.utcnow(),
            'symbol': 'BTC/USDT',
            'decision': 'BUY',
            'confidence': 0.8,
            'reasoning': f'Decision {i}',
            'executed': True,
            'outcome': 'win',
            'pnl': 100.0,
            'model_used': 'deepseek-chat',
            'strategy': 'Strategy1'
        }
        storage.save_ai_decision(decision_data)
    
    for i in range(3):
        decision_data = {
            'timestamp': datetime.utcnow(),
            'symbol': 'BTC/USDT',
            'decision': 'BUY',
            'confidence': 0.7,
            'reasoning': f'Decision {i}',
            'executed': True,
            'outcome': 'loss',
            'pnl': -50.0,
            'model_used': 'deepseek-chat',
            'strategy': 'Strategy2'
        }
        storage.save_ai_decision(decision_data)
    
    stats1 = storage.get_ai_decision_stats(strategy='Strategy1')
    assert stats1['total_decisions'] == 5
    assert stats1['win_count'] == 5
    assert stats1['win_rate'] == 1.0
    
    stats2 = storage.get_ai_decision_stats(strategy='Strategy2')
    assert stats2['total_decisions'] == 3
    assert stats2['loss_count'] == 3
    assert stats2['win_rate'] == 0.0


def test_ai_decision_with_market_context(storage):
    """Test saving and retrieving AI decision with market context"""
    market_context = {
        'price': 50000.0,
        'rsi': 35.5,
        'macd': 120.3,
        'volume': 1000000
    }
    
    decision_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'BUY',
        'confidence': 0.85,
        'reasoning': 'Strong bullish momentum',
        'market_context': json.dumps(market_context),
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    storage.save_ai_decision(decision_data)
    
    decisions = storage.get_ai_decisions()
    assert len(decisions) == 1
    
    retrieved_context = json.loads(decisions[0]['market_context'])
    assert retrieved_context['price'] == 50000.0
    assert retrieved_context['rsi'] == 35.5


def test_ai_decision_with_invalidation_condition(storage):
    """Test saving and retrieving AI decision with invalidation condition"""
    decision_data = {
        'timestamp': datetime.utcnow(),
        'symbol': 'BTC/USDT',
        'decision': 'BUY',
        'confidence': 0.85,
        'reasoning': 'Strong bullish momentum',
        'invalidation_condition': 'Price drops below 49000 or RSI > 70',
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    storage.save_ai_decision(decision_data)
    
    decisions = storage.get_ai_decisions()
    assert decisions[0]['invalidation_condition'] == 'Price drops below 49000 or RSI > 70'


def test_ai_decision_limit(storage):
    """Test AI decision retrieval limit"""
    for i in range(150):
        decision_data = {
            'timestamp': datetime.utcnow(),
            'symbol': 'BTC/USDT',
            'decision': 'BUY',
            'confidence': 0.8,
            'reasoning': f'Decision {i}',
            'model_used': 'deepseek-chat',
            'strategy': 'SingleAgentStrategy'
        }
        storage.save_ai_decision(decision_data)
    
    decisions = storage.get_ai_decisions(limit=50)
    assert len(decisions) == 50


def test_ai_decision_time_filter(storage):
    """Test AI decision time filtering"""
    now = datetime.utcnow()
    
    old_decision = {
        'timestamp': now - timedelta(days=2),
        'symbol': 'BTC/USDT',
        'decision': 'BUY',
        'confidence': 0.8,
        'reasoning': 'Old decision',
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    recent_decision = {
        'timestamp': now - timedelta(hours=1),
        'symbol': 'BTC/USDT',
        'decision': 'SELL',
        'confidence': 0.75,
        'reasoning': 'Recent decision',
        'model_used': 'deepseek-chat',
        'strategy': 'SingleAgentStrategy'
    }
    
    storage.save_ai_decision(old_decision)
    storage.save_ai_decision(recent_decision)
    
    recent_decisions = storage.get_ai_decisions(
        start_time=now - timedelta(hours=2)
    )
    
    assert len(recent_decisions) == 1
    assert recent_decisions[0]['reasoning'] == 'Recent decision'
