"""
Data Storage Module

Provides database interfaces for storing and retrieving market data, trade history,
and performance metrics using SQLite and Redis.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import redis.asyncio as aioredis

from ..utils.logger import get_logger

logger = get_logger()

Base = declarative_base()


class MarketDataModel(Base):
    """Model for storing OHLCV market data."""
    __tablename__ = 'market_data'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class TradeModel(Base):
    """Model for storing trade history."""
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    side = Column(String(10), nullable=False)  # BUY or SELL
    order_type = Column(String(20), nullable=False)  # market, limit
    size = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    leverage = Column(Float, default=1.0)
    pnl = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    status = Column(String(20), nullable=False)  # open, closed, canceled
    strategy = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    entry_time = Column(DateTime, nullable=False, index=True)
    exit_time = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class PerformanceMetricModel(Base):
    """Model for storing performance metrics."""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(50), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    symbol = Column(String(20), nullable=True, index=True)
    strategy = Column(String(50), nullable=True, index=True)
    timeframe = Column(String(10), nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    extra_metadata = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow)


class SystemLogModel(Base):
    """Model for storing system logs."""
    __tablename__ = 'system_logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    log_level = Column(String(20), nullable=False, index=True)
    module = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    extra_metadata = Column(Text, nullable=True)  # JSON string for additional data
    created_at = Column(DateTime, default=datetime.utcnow)


class FundingEventModel(Base):
    """Model for storing funding rate events for perpetual contracts."""
    __tablename__ = 'funding_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    funding_rate = Column(Float, nullable=False)  # Funding rate (e.g., 0.0001 = 0.01%)
    position_size = Column(Float, nullable=False)  # Position size in base currency
    notional_value = Column(Float, nullable=False)  # Position notional value in quote currency
    funding_amount = Column(Float, nullable=False)  # Funding payment (positive = received, negative = paid)
    side = Column(String(10), nullable=False)  # LONG or SHORT
    created_at = Column(DateTime, default=datetime.utcnow)


class AIDecisionModel(Base):
    """Model for storing AI trading decisions and their outcomes."""
    __tablename__ = 'ai_decisions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)
    decision = Column(String(10), nullable=False)  # BUY, SELL, HOLD, CLOSE
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    reasoning = Column(Text, nullable=False)  # AI's reasoning/justification
    market_context = Column(Text, nullable=True)  # JSON: price, indicators, market conditions
    position_size = Column(Float, nullable=True)  # Recommended position size
    entry_price = Column(Float, nullable=True)  # Entry price (if executed)
    stop_loss = Column(Float, nullable=True)  # Stop-loss price
    take_profit = Column(Float, nullable=True)  # Take-profit price
    invalidation_condition = Column(Text, nullable=True)  # Condition that invalidates the trade
    executed = Column(Boolean, default=False)  # Whether decision was executed
    trade_id = Column(Integer, nullable=True)  # Link to TradeModel if executed
    outcome = Column(String(20), nullable=True)  # win, loss, breakeven (after trade closes)
    pnl = Column(Float, nullable=True)  # P&L if trade was executed and closed
    model_used = Column(String(50), nullable=True)  # AI model used (e.g., "deepseek-chat")
    strategy = Column(String(50), nullable=True, index=True)  # Strategy that generated decision
    created_at = Column(DateTime, default=datetime.utcnow)


class SQLiteStorage:
    """SQLite database interface for persistent storage."""
    
    def __init__(self, db_path: str = "./data/trading_bot.db"):
        """
        Initialize SQLite storage.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_engine(
            f'sqlite:///{self.db_path}',
            connect_args={'check_same_thread': False},
            poolclass=StaticPool
        )
        
        Base.metadata.create_all(self.engine)
        
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        logger.info(f"SQLite storage initialized at {self.db_path}")
    
    def save_market_data(self, symbol: str, timeframe: str, ohlcv_data: List[Dict[str, Any]]):
        """
        Save OHLCV market data to database.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., '1m', '5m', '1h')
            ohlcv_data: List of OHLCV dictionaries
        """
        session = self.SessionLocal()
        try:
            for candle in ohlcv_data:
                existing = session.query(MarketDataModel).filter_by(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=candle['timestamp']
                ).first()
                
                if not existing:
                    record = MarketDataModel(
                        symbol=symbol,
                        timeframe=timeframe,
                        timestamp=candle['timestamp'],
                        open=candle['open'],
                        high=candle['high'],
                        low=candle['low'],
                        close=candle['close'],
                        volume=candle['volume']
                    )
                    session.add(record)
            
            session.commit()
            logger.bind(data=True).debug(f"Saved {len(ohlcv_data)} candles for {symbol} {timeframe}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving market data: {e}")
            raise
        finally:
            session.close()
    
    def get_market_data(self, symbol: str, timeframe: str, start_time: Optional[datetime] = None,
                       end_time: Optional[datetime] = None, limit: int = 1000) -> pd.DataFrame:
        """
        Retrieve market data from database.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            start_time: Start time filter (optional)
            end_time: End time filter (optional)
            limit: Maximum number of records to retrieve
            
        Returns:
            DataFrame with OHLCV data
        """
        session = self.SessionLocal()
        try:
            query = session.query(MarketDataModel).filter_by(
                symbol=symbol,
                timeframe=timeframe
            )
            
            if start_time:
                query = query.filter(MarketDataModel.timestamp >= start_time)
            if end_time:
                query = query.filter(MarketDataModel.timestamp <= end_time)
            
            query = query.order_by(MarketDataModel.timestamp.desc()).limit(limit)
            
            records = query.all()
            
            if not records:
                return pd.DataFrame()
            
            data = [{
                'timestamp': r.timestamp,
                'open': r.open,
                'high': r.high,
                'low': r.low,
                'close': r.close,
                'volume': r.volume
            } for r in records]
            
            df = pd.DataFrame(data)
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            return df
        finally:
            session.close()
    
    def save_trade(self, trade_data: Dict[str, Any]) -> int:
        """
        Save a trade to database.
        
        Args:
            trade_data: Dictionary containing trade information
            
        Returns:
            Trade ID
        """
        session = self.SessionLocal()
        try:
            trade = TradeModel(**trade_data)
            session.add(trade)
            session.commit()
            session.refresh(trade)
            
            logger.bind(trade=True).info(f"Saved trade: {trade.side} {trade.size} {trade.symbol} @ {trade.entry_price}")
            
            return trade.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving trade: {e}")
            raise
        finally:
            session.close()
    
    def update_trade(self, trade_id: int, updates: Dict[str, Any]):
        """
        Update an existing trade.
        
        Args:
            trade_id: Trade ID
            updates: Dictionary of fields to update
        """
        session = self.SessionLocal()
        try:
            trade = session.query(TradeModel).filter_by(id=trade_id).first()
            if trade:
                for key, value in updates.items():
                    setattr(trade, key, value)
                session.commit()
                logger.bind(trade=True).info(f"Updated trade {trade_id}")
            else:
                logger.warning(f"Trade {trade_id} not found")
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating trade: {e}")
            raise
        finally:
            session.close()
    
    def get_trades(self, symbol: Optional[str] = None, status: Optional[str] = None,
                   start_time: Optional[datetime] = None, end_time: Optional[datetime] = None,
                   limit: int = 100) -> List[Dict[str, Any]]:
        """
        Retrieve trades from database.
        
        Args:
            symbol: Filter by symbol (optional)
            status: Filter by status (optional)
            start_time: Start time filter (optional)
            end_time: End time filter (optional)
            limit: Maximum number of records
            
        Returns:
            List of trade dictionaries
        """
        session = self.SessionLocal()
        try:
            query = session.query(TradeModel)
            
            if symbol:
                query = query.filter_by(symbol=symbol)
            if status:
                query = query.filter_by(status=status)
            if start_time:
                query = query.filter(TradeModel.entry_time >= start_time)
            if end_time:
                query = query.filter(TradeModel.entry_time <= end_time)
            
            query = query.order_by(TradeModel.entry_time.desc()).limit(limit)
            
            trades = query.all()
            
            return [{
                'id': t.id,
                'symbol': t.symbol,
                'side': t.side,
                'order_type': t.order_type,
                'size': t.size,
                'entry_price': t.entry_price,
                'exit_price': t.exit_price,
                'stop_loss': t.stop_loss,
                'take_profit': t.take_profit,
                'leverage': t.leverage,
                'pnl': t.pnl,
                'pnl_pct': t.pnl_pct,
                'status': t.status,
                'strategy': t.strategy,
                'confidence': t.confidence,
                'entry_time': t.entry_time,
                'exit_time': t.exit_time,
                'notes': t.notes
            } for t in trades]
        finally:
            session.close()
    
    def save_performance_metric(self, metric_name: str, metric_value: float,
                               symbol: Optional[str] = None, strategy: Optional[str] = None,
                               timeframe: Optional[str] = None, metadata: Optional[Dict] = None):
        """
        Save a performance metric.
        
        Args:
            metric_name: Name of the metric
            metric_value: Value of the metric
            symbol: Associated symbol (optional)
            strategy: Associated strategy (optional)
            timeframe: Associated timeframe (optional)
            metadata: Additional metadata (optional)
        """
        session = self.SessionLocal()
        try:
            metric = PerformanceMetricModel(
                metric_name=metric_name,
                metric_value=metric_value,
                symbol=symbol,
                strategy=strategy,
                timeframe=timeframe,
                timestamp=datetime.utcnow(),
                metadata=json.dumps(metadata) if metadata else None
            )
            session.add(metric)
            session.commit()
            
            logger.bind(performance=True).info(f"Saved metric: {metric_name} = {metric_value}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving performance metric: {e}")
            raise
        finally:
            session.close()
    
    def save_ai_decision(self, decision_data: Dict[str, Any]) -> int:
        """
        Save an AI trading decision to database.
        
        Args:
            decision_data: Dictionary containing decision information
            
        Returns:
            Decision ID
        """
        session = self.SessionLocal()
        try:
            decision = AIDecisionModel(**decision_data)
            session.add(decision)
            session.commit()
            session.refresh(decision)
            
            logger.bind(ai=True).info(
                f"Saved AI decision: {decision.decision} {decision.symbol} "
                f"confidence={decision.confidence:.2f}"
            )
            
            return decision.id
        except Exception as e:
            session.rollback()
            logger.error(f"Error saving AI decision: {e}")
            raise
        finally:
            session.close()
    
    def update_ai_decision(self, decision_id: int, updates: Dict[str, Any]):
        """
        Update an existing AI decision.
        
        Args:
            decision_id: Decision ID
            updates: Dictionary of fields to update
        """
        session = self.SessionLocal()
        try:
            decision = session.query(AIDecisionModel).filter_by(id=decision_id).first()
            if decision:
                for key, value in updates.items():
                    setattr(decision, key, value)
                session.commit()
                logger.bind(ai=True).info(f"Updated AI decision {decision_id}")
            else:
                logger.warning(f"AI decision {decision_id} not found")
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating AI decision: {e}")
            raise
        finally:
            session.close()
    
    def get_ai_decisions(
        self,
        symbol: Optional[str] = None,
        strategy: Optional[str] = None,
        decision: Optional[str] = None,
        executed: Optional[bool] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve AI decisions from database.
        
        Args:
            symbol: Filter by symbol (optional)
            strategy: Filter by strategy (optional)
            decision: Filter by decision type (optional)
            executed: Filter by execution status (optional)
            start_time: Start time filter (optional)
            end_time: End time filter (optional)
            limit: Maximum number of records
            
        Returns:
            List of AI decision dictionaries
        """
        session = self.SessionLocal()
        try:
            query = session.query(AIDecisionModel)
            
            if symbol:
                query = query.filter_by(symbol=symbol)
            if strategy:
                query = query.filter_by(strategy=strategy)
            if decision:
                query = query.filter_by(decision=decision)
            if executed is not None:
                query = query.filter_by(executed=executed)
            if start_time:
                query = query.filter(AIDecisionModel.timestamp >= start_time)
            if end_time:
                query = query.filter(AIDecisionModel.timestamp <= end_time)
            
            query = query.order_by(AIDecisionModel.timestamp.desc()).limit(limit)
            
            decisions = query.all()
            
            return [{
                'id': d.id,
                'timestamp': d.timestamp,
                'symbol': d.symbol,
                'decision': d.decision,
                'confidence': d.confidence,
                'reasoning': d.reasoning,
                'market_context': d.market_context,
                'position_size': d.position_size,
                'entry_price': d.entry_price,
                'stop_loss': d.stop_loss,
                'take_profit': d.take_profit,
                'invalidation_condition': d.invalidation_condition,
                'executed': d.executed,
                'trade_id': d.trade_id,
                'outcome': d.outcome,
                'pnl': d.pnl,
                'model_used': d.model_used,
                'strategy': d.strategy
            } for d in decisions]
        finally:
            session.close()
    
    def get_ai_decision_stats(
        self,
        strategy: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for AI decisions.
        
        Args:
            strategy: Filter by strategy (optional)
            start_time: Start time filter (optional)
            end_time: End time filter (optional)
            
        Returns:
            Dictionary with decision statistics
        """
        session = self.SessionLocal()
        try:
            query = session.query(AIDecisionModel)
            
            if strategy:
                query = query.filter_by(strategy=strategy)
            if start_time:
                query = query.filter(AIDecisionModel.timestamp >= start_time)
            if end_time:
                query = query.filter(AIDecisionModel.timestamp <= end_time)
            
            decisions = query.all()
            
            if not decisions:
                return {
                    'total_decisions': 0,
                    'executed_count': 0,
                    'execution_rate': 0.0,
                    'avg_confidence': 0.0,
                    'win_count': 0,
                    'loss_count': 0,
                    'win_rate': 0.0,
                    'total_pnl': 0.0
                }
            
            executed = [d for d in decisions if d.executed]
            closed = [d for d in executed if d.outcome is not None]
            wins = [d for d in closed if d.outcome == 'win']
            losses = [d for d in closed if d.outcome == 'loss']
            
            return {
                'total_decisions': len(decisions),
                'executed_count': len(executed),
                'execution_rate': len(executed) / len(decisions) if decisions else 0.0,
                'avg_confidence': sum(d.confidence for d in decisions) / len(decisions),
                'win_count': len(wins),
                'loss_count': len(losses),
                'win_rate': len(wins) / len(closed) if closed else 0.0,
                'total_pnl': sum(d.pnl for d in closed if d.pnl is not None)
            }
        finally:
            session.close()
    
    def close(self):
        """Close database connection."""
        self.engine.dispose()
        logger.info("SQLite storage closed")


class RedisCache:
    """Redis cache interface for real-time data."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379/0"):
        """
        Initialize Redis cache.
        
        Args:
            redis_url: Redis connection URL
        """
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None
        logger.info(f"Redis cache configured with URL: {redis_url}")
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
            await self.redis.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis cache disconnected")
    
    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        """
        Set a value in cache.
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            expire: Expiration time in seconds (optional)
        """
        if not self.redis:
            await self.connect()
        
        try:
            serialized = json.dumps(value)
            await self.redis.set(key, serialized, ex=expire)
            logger.bind(data=True).debug(f"Cached: {key}")
        except Exception as e:
            logger.error(f"Error setting cache key {key}: {e}")
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found
        """
        if not self.redis:
            await self.connect()
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Error getting cache key {key}: {e}")
            return None
    
    async def delete(self, key: str):
        """
        Delete a key from cache.
        
        Args:
            key: Cache key
        """
        if not self.redis:
            await self.connect()
        
        try:
            await self.redis.delete(key)
            logger.bind(data=True).debug(f"Deleted cache key: {key}")
        except Exception as e:
            logger.error(f"Error deleting cache key {key}: {e}")
    
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists, False otherwise
        """
        if not self.redis:
            await self.connect()
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Error checking cache key {key}: {e}")
            return False
    
    async def set_market_data(self, symbol: str, timeframe: str, data: Dict[str, Any], expire: int = 300):
        """
        Cache market data.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            data: Market data dictionary
            expire: Expiration time in seconds (default 5 minutes)
        """
        key = f"market:{symbol}:{timeframe}"
        await self.set(key, data, expire)
    
    async def get_market_data(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """
        Get cached market data.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            
        Returns:
            Market data dictionary or None
        """
        key = f"market:{symbol}:{timeframe}"
        return await self.get(key)
    
    async def set_indicator(self, symbol: str, timeframe: str, indicator_name: str,
                           value: Any, expire: int = 300):
        """
        Cache technical indicator value.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            indicator_name: Name of the indicator
            value: Indicator value
            expire: Expiration time in seconds
        """
        key = f"indicator:{symbol}:{timeframe}:{indicator_name}"
        await self.set(key, value, expire)
    
    async def get_indicator(self, symbol: str, timeframe: str, indicator_name: str) -> Optional[Any]:
        """
        Get cached indicator value.
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            indicator_name: Name of the indicator
            
        Returns:
            Indicator value or None
        """
        key = f"indicator:{symbol}:{timeframe}:{indicator_name}"
        return await self.get(key)
