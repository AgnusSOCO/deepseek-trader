"""
Unit Tests for Paper Trading Engine

Tests position management, P&L calculation, fee handling, slippage simulation,
and performance metrics.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile
import shutil

from src.execution.paper_trading import PaperPosition, PaperTradingEngine


class TestPaperPosition:
    """Test PaperPosition dataclass"""
    
    def test_long_position_pnl_calculation(self):
        """Test P&L calculation for long position"""
        position = PaperPosition(
            position_id="test_long_1",
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            quantity=0.1,
            leverage=10.0
        )
        
        pnl_data = position.calculate_pnl(51000.0)
        
        assert pnl_data['price_change_pct'] == pytest.approx(2.0, rel=0.01)
        assert pnl_data['pnl_pct'] == pytest.approx(20.0, rel=0.01)
        assert pnl_data['pnl'] == pytest.approx(1000.0, rel=0.01)
    
    def test_short_position_pnl_calculation(self):
        """Test P&L calculation for short position"""
        position = PaperPosition(
            position_id="test_short_1",
            symbol="BTC/USDT",
            side="short",
            entry_price=50000.0,
            quantity=0.1,
            leverage=10.0
        )
        
        pnl_data = position.calculate_pnl(49000.0)
        
        assert pnl_data['price_change_pct'] == pytest.approx(2.0, rel=0.01)
        assert pnl_data['pnl_pct'] == pytest.approx(20.0, rel=0.01)
        assert pnl_data['pnl'] == pytest.approx(1000.0, rel=0.01)
    
    def test_long_position_loss(self):
        """Test loss calculation for long position"""
        position = PaperPosition(
            position_id="test_long_2",
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            quantity=0.1,
            leverage=5.0
        )
        
        pnl_data = position.calculate_pnl(48500.0)
        
        assert pnl_data['price_change_pct'] == pytest.approx(-3.0, rel=0.01)
        assert pnl_data['pnl_pct'] == pytest.approx(-15.0, rel=0.01)
        assert pnl_data['pnl'] < 0
    
    def test_max_min_pnl_tracking(self):
        """Test max/min P&L tracking"""
        position = PaperPosition(
            position_id="test_tracking",
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            quantity=0.1,
            leverage=10.0
        )
        
        position.calculate_pnl(51000.0)
        assert position.max_pnl == pytest.approx(20.0, rel=0.01)
        
        position.calculate_pnl(52000.0)
        assert position.max_pnl == pytest.approx(40.0, rel=0.01)
        
        position.calculate_pnl(49000.0)
        assert position.min_pnl == pytest.approx(-20.0, rel=0.01)
        assert position.max_pnl == pytest.approx(40.0, rel=0.01)
    
    def test_to_dict_serialization(self):
        """Test position serialization to dict"""
        position = PaperPosition(
            position_id="test_serialize",
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            quantity=0.1,
            leverage=10.0,
            stop_loss=48500.0,
            take_profit=54000.0,
            metadata={'strategy': 'momentum'}
        )
        
        data = position.to_dict()
        
        assert data['position_id'] == "test_serialize"
        assert data['symbol'] == "BTC/USDT"
        assert data['side'] == "long"
        assert data['entry_price'] == 50000.0
        assert data['leverage'] == 10.0
        assert data['metadata']['strategy'] == 'momentum'


class TestPaperTradingEngine:
    """Test PaperTradingEngine"""
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create temporary log directory"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def engine(self, temp_log_dir):
        """Create paper trading engine"""
        return PaperTradingEngine(
            initial_capital=10000.0,
            slippage_pct=0.05,
            maker_fee_pct=0.02,
            taker_fee_pct=0.06,
            log_dir=temp_log_dir
        )
    
    def test_engine_initialization(self, engine):
        """Test engine initialization"""
        assert engine.initial_capital == 10000.0
        assert engine.current_capital == 10000.0
        assert engine.peak_capital == 10000.0
        assert len(engine.positions) == 0
        assert len(engine.closed_positions) == 0
        assert engine.total_trades == 0
    
    def test_open_long_position(self, engine):
        """Test opening a long position"""
        position = engine.open_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size_pct=20.0,
            leverage=10.0,
            stop_loss=48500.0,
            take_profit=54000.0
        )
        
        assert position is not None
        assert position.side == "long"
        assert position.leverage == 10.0
        assert len(engine.positions) == 1
        assert engine.total_trades == 1
        
        assert engine.current_capital < 10000.0
        assert engine.current_capital == pytest.approx(9798.8, rel=0.01)
    
    def test_open_short_position(self, engine):
        """Test opening a short position"""
        position = engine.open_position(
            symbol="BTC/USDT",
            side="short",
            entry_price=50000.0,
            position_size_pct=15.0,
            leverage=5.0
        )
        
        assert position is not None
        assert position.side == "short"
        assert position.leverage == 5.0
        assert len(engine.positions) == 1
    
    def test_slippage_applied_on_entry(self, engine):
        """Test slippage is applied on position entry"""
        position = engine.open_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size_pct=10.0,
            leverage=1.0
        )
        
        assert position.entry_price > 50000.0
        assert position.entry_price == pytest.approx(50025.0, rel=0.01)
    
    def test_close_profitable_position(self, engine):
        """Test closing a profitable position"""
        position = engine.open_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size_pct=20.0,
            leverage=10.0
        )
        
        initial_capital = engine.current_capital
        
        result = engine.close_position(
            position_id=position.position_id,
            exit_price=51000.0,
            reason="take_profit"
        )
        
        assert result is not None
        assert result['pnl'] > 0
        assert result['pnl_pct'] > 0
        assert result['reason'] == "take_profit"
        
        assert engine.current_capital > initial_capital
        assert len(engine.positions) == 0
        assert len(engine.closed_positions) == 1
        assert engine.winning_trades == 1
    
    def test_close_losing_position(self, engine):
        """Test closing a losing position"""
        position = engine.open_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size_pct=20.0,
            leverage=10.0
        )
        
        initial_capital = engine.current_capital
        
        result = engine.close_position(
            position_id=position.position_id,
            exit_price=49000.0,
            reason="stop_loss"
        )
        
        assert result is not None
        assert result['pnl'] < 0
        assert result['pnl_pct'] < 0
        
        assert engine.current_capital < initial_capital
        assert engine.losing_trades == 1
    
    def test_close_nonexistent_position(self, engine):
        """Test closing nonexistent position returns None"""
        result = engine.close_position(
            position_id="nonexistent",
            exit_price=50000.0
        )
        
        assert result is None
    
    def test_update_positions_stop_loss(self, engine):
        """Test stop-loss triggering in update_positions"""
        position = engine.open_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size_pct=20.0,
            leverage=10.0,
            stop_loss=48500.0
        )
        
        positions_to_close = engine.update_positions({
            "BTC/USDT": 48400.0
        })
        
        assert len(positions_to_close) == 1
        assert positions_to_close[0]['reason'] == 'stop_loss'
        assert positions_to_close[0]['position_id'] == position.position_id
    
    def test_update_positions_take_profit(self, engine):
        """Test take-profit triggering in update_positions"""
        position = engine.open_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size_pct=20.0,
            leverage=10.0,
            take_profit=54000.0
        )
        
        positions_to_close = engine.update_positions({
            "BTC/USDT": 54100.0
        })
        
        assert len(positions_to_close) == 1
        assert positions_to_close[0]['reason'] == 'take_profit'
    
    def test_short_position_stop_loss(self, engine):
        """Test stop-loss for short position"""
        position = engine.open_position(
            symbol="BTC/USDT",
            side="short",
            entry_price=50000.0,
            position_size_pct=20.0,
            leverage=10.0,
            stop_loss=51500.0  # Stop-loss above entry for short
        )
        
        positions_to_close = engine.update_positions({
            "BTC/USDT": 51600.0
        })
        
        assert len(positions_to_close) == 1
        assert positions_to_close[0]['reason'] == 'stop_loss'
    
    def test_performance_metrics(self, engine):
        """Test performance metrics calculation"""
        
        pos1 = engine.open_position("BTC/USDT", "long", 50000.0, 10.0, 5.0)
        engine.close_position(pos1.position_id, 51000.0, "take_profit")
        
        pos2 = engine.open_position("ETH/USDT", "long", 3000.0, 10.0, 5.0)
        engine.close_position(pos2.position_id, 2950.0, "stop_loss")
        
        pos3 = engine.open_position("BTC/USDT", "short", 50000.0, 10.0, 5.0)
        engine.close_position(pos3.position_id, 49000.0, "take_profit")
        
        metrics = engine.get_performance_metrics()
        
        assert metrics['total_trades'] == 3
        assert metrics['winning_trades'] == 2
        assert metrics['losing_trades'] == 1
        assert metrics['win_rate'] == pytest.approx(66.67, rel=0.1)
        assert metrics['open_positions'] == 0
        assert 'total_return' in metrics
        assert 'total_return_pct' in metrics
        assert 'drawdown_pct' in metrics
        assert 'profit_factor' in metrics
    
    def test_peak_capital_tracking(self, engine):
        """Test peak capital tracking"""
        initial_peak = engine.peak_capital
        
        pos1 = engine.open_position("BTC/USDT", "long", 50000.0, 20.0, 10.0)
        engine.close_position(pos1.position_id, 51000.0, "take_profit")
        
        assert engine.peak_capital > initial_peak
        assert engine.peak_capital == engine.current_capital
        
        current_peak = engine.peak_capital
        pos2 = engine.open_position("BTC/USDT", "long", 50000.0, 10.0, 5.0)
        engine.close_position(pos2.position_id, 49500.0, "stop_loss")
        
        assert engine.peak_capital == current_peak
    
    def test_trade_logging(self, engine, temp_log_dir):
        """Test trade logging to file"""
        position = engine.open_position(
            symbol="BTC/USDT",
            side="long",
            entry_price=50000.0,
            position_size_pct=20.0,
            leverage=10.0
        )
        engine.close_position(position.position_id, 51000.0, "take_profit")
        
        log_files = list(Path(temp_log_dir).glob("paper_trades_*.jsonl"))
        assert len(log_files) == 1
        
        with open(log_files[0], 'r') as f:
            lines = f.readlines()
            assert len(lines) == 2  # OPEN and CLOSE
            
            open_entry = json.loads(lines[0])
            assert open_entry['action'] == 'OPEN'
            assert open_entry['position']['symbol'] == 'BTC/USDT'
            
            close_entry = json.loads(lines[1])
            assert close_entry['action'] == 'CLOSE'
            assert close_entry['position']['exit_reason'] == 'take_profit'
    
    def test_multiple_open_positions(self, engine):
        """Test managing multiple open positions"""
        pos1 = engine.open_position("BTC/USDT", "long", 50000.0, 10.0, 5.0)
        pos2 = engine.open_position("ETH/USDT", "long", 3000.0, 10.0, 5.0)
        pos3 = engine.open_position("BNB/USDT", "short", 400.0, 10.0, 5.0)
        
        assert len(engine.positions) == 3
        assert engine.total_trades == 3
        
        positions_to_close = engine.update_positions({
            "BTC/USDT": 50500.0,
            "ETH/USDT": 3050.0,
            "BNB/USDT": 405.0
        })
        
        assert len(positions_to_close) == 0
    
    def test_leverage_impact_on_pnl(self, engine):
        """Test leverage impact on P&L"""
        pos1 = engine.open_position("BTC/USDT", "long", 50000.0, 10.0, 5.0)
        initial_capital_1 = engine.current_capital
        
        result1 = engine.close_position(pos1.position_id, 51000.0)
        pnl_5x = result1['pnl']
        
        engine.current_capital = 10000.0
        pos2 = engine.open_position("BTC/USDT", "long", 50000.0, 10.0, 10.0)
        result2 = engine.close_position(pos2.position_id, 51000.0)
        pnl_10x = result2['pnl']
        
        assert pnl_10x == pytest.approx(pnl_5x * 2, rel=0.1)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
