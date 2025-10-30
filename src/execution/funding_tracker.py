"""
Funding Rate Tracker

Tracks funding rates for perpetual contracts and calculates funding payments.
Essential for accurate P&L calculation on perpetual futures.
"""

from datetime import datetime
from typing import Dict, Optional, List
import ccxt
from loguru import logger
from sqlalchemy.orm import Session

from ..data.storage import FundingEventModel, SQLiteStorage


class FundingTracker:
    """
    Tracks funding rates and calculates funding payments for perpetual contracts
    
    Funding payments occur every 8 hours on most exchanges.
    Long positions pay funding when rate is positive, receive when negative.
    Short positions receive funding when rate is positive, pay when negative.
    """
    
    def __init__(self, exchange: ccxt.Exchange, storage: SQLiteStorage, enabled: bool = True):
        """
        Initialize funding tracker
        
        Args:
            exchange: CCXT exchange instance
            storage: SQLite storage instance
            enabled: Whether funding tracking is enabled
        """
        self.exchange = exchange
        self.storage = storage
        self.enabled = enabled
        self.funding_cache: Dict[str, float] = {}
        
        logger.info(f"FundingTracker initialized (enabled={enabled})")
    
    async def fetch_funding_rate(self, symbol: str) -> float:
        """
        Fetch current funding rate for a symbol
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT:USDT')
            
        Returns:
            Current funding rate (e.g., 0.0001 = 0.01%)
            
        Raises:
            ValueError: If symbol not found or not a perpetual contract
        """
        if not self.enabled:
            return 0.0
        
        try:
            if symbol in self.funding_cache:
                return self.funding_cache[symbol]
            
            funding_rate_data = await self.exchange.fetch_funding_rate(symbol)
            
            funding_rate = funding_rate_data.get('fundingRate', 0.0)
            
            self.funding_cache[symbol] = funding_rate
            
            logger.debug(f"Fetched funding rate for {symbol}: {funding_rate:.6f} ({funding_rate * 100:.4f}%)")
            
            return funding_rate
            
        except Exception as e:
            logger.error(f"Failed to fetch funding rate for {symbol}: {e}")
            return 0.0
    
    def calculate_funding_payment(
        self,
        symbol: str,
        side: str,
        position_size: float,
        entry_price: float,
        funding_rate: float
    ) -> float:
        """
        Calculate funding payment for a position
        
        Args:
            symbol: Trading pair symbol
            side: Position side ('LONG' or 'SHORT')
            position_size: Position size in base currency
            entry_price: Entry price
            funding_rate: Funding rate
            
        Returns:
            Funding payment amount (positive = received, negative = paid)
        """
        if not self.enabled or funding_rate == 0.0:
            return 0.0
        
        notional_value = position_size * entry_price
        
        if side.upper() == 'LONG':
            funding_payment = -notional_value * funding_rate
        elif side.upper() == 'SHORT':
            funding_payment = notional_value * funding_rate
        else:
            logger.error(f"Invalid position side: {side}")
            return 0.0
        
        logger.debug(
            f"Funding payment calculated: {symbol} {side} "
            f"size={position_size:.4f} rate={funding_rate:.6f} "
            f"payment={funding_payment:.4f}"
        )
        
        return funding_payment
    
    async def record_funding_event(
        self,
        symbol: str,
        side: str,
        position_size: float,
        notional_value: float,
        funding_rate: float,
        funding_amount: float
    ) -> int:
        """
        Record a funding event to database
        
        Args:
            symbol: Trading pair symbol
            side: Position side ('LONG' or 'SHORT')
            position_size: Position size in base currency
            notional_value: Position notional value
            funding_rate: Funding rate
            funding_amount: Funding payment amount
            
        Returns:
            Funding event ID
        """
        if not self.enabled:
            return 0
        
        session = self.storage.SessionLocal()
        try:
            event = FundingEventModel(
                symbol=symbol,
                timestamp=datetime.utcnow(),
                funding_rate=funding_rate,
                position_size=position_size,
                notional_value=notional_value,
                funding_amount=funding_amount,
                side=side.upper()
            )
            
            session.add(event)
            session.commit()
            session.refresh(event)
            
            logger.info(
                f"Recorded funding event: {symbol} {side} "
                f"rate={funding_rate:.6f} amount={funding_amount:.4f}"
            )
            
            return event.id
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to record funding event: {e}")
            raise
        finally:
            session.close()
    
    def get_funding_events(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """
        Retrieve funding events from database
        
        Args:
            symbol: Filter by symbol (optional)
            start_time: Start time filter (optional)
            end_time: End time filter (optional)
            limit: Maximum number of records
            
        Returns:
            List of funding event dictionaries
        """
        if not self.enabled:
            return []
        
        session = self.storage.SessionLocal()
        try:
            query = session.query(FundingEventModel)
            
            if symbol:
                query = query.filter_by(symbol=symbol)
            if start_time:
                query = query.filter(FundingEventModel.timestamp >= start_time)
            if end_time:
                query = query.filter(FundingEventModel.timestamp <= end_time)
            
            query = query.order_by(FundingEventModel.timestamp.desc()).limit(limit)
            
            events = query.all()
            
            return [{
                'id': e.id,
                'symbol': e.symbol,
                'timestamp': e.timestamp,
                'funding_rate': e.funding_rate,
                'position_size': e.position_size,
                'notional_value': e.notional_value,
                'funding_amount': e.funding_amount,
                'side': e.side
            } for e in events]
            
        finally:
            session.close()
    
    def get_total_funding_pnl(
        self,
        symbol: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> float:
        """
        Calculate total funding P&L for a period
        
        Args:
            symbol: Filter by symbol (optional)
            start_time: Start time filter (optional)
            end_time: End time filter (optional)
            
        Returns:
            Total funding P&L (positive = net received, negative = net paid)
        """
        if not self.enabled:
            return 0.0
        
        events = self.get_funding_events(
            symbol=symbol,
            start_time=start_time,
            end_time=end_time,
            limit=10000
        )
        
        total_pnl = sum(e['funding_amount'] for e in events)
        
        logger.info(
            f"Total funding P&L: {total_pnl:.4f} "
            f"({len(events)} events, symbol={symbol})"
        )
        
        return total_pnl
    
    async def process_position_funding(
        self,
        symbol: str,
        side: str,
        position_size: float,
        entry_price: float
    ) -> float:
        """
        Process funding for an open position
        
        Fetches current funding rate, calculates payment, and records event.
        
        Args:
            symbol: Trading pair symbol
            side: Position side ('LONG' or 'SHORT')
            position_size: Position size in base currency
            entry_price: Entry price
            
        Returns:
            Funding payment amount
        """
        if not self.enabled:
            return 0.0
        
        try:
            funding_rate = await self.fetch_funding_rate(symbol)
            
            funding_amount = self.calculate_funding_payment(
                symbol=symbol,
                side=side,
                position_size=position_size,
                entry_price=entry_price,
                funding_rate=funding_rate
            )
            
            notional_value = position_size * entry_price
            
            await self.record_funding_event(
                symbol=symbol,
                side=side,
                position_size=position_size,
                notional_value=notional_value,
                funding_rate=funding_rate,
                funding_amount=funding_amount
            )
            
            return funding_amount
            
        except Exception as e:
            logger.error(f"Failed to process position funding: {e}")
            return 0.0
    
    def clear_cache(self):
        """Clear the funding rate cache"""
        self.funding_cache.clear()
        logger.info("Cleared funding rate cache")
