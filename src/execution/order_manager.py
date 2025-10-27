"""
Order Manager

Handles order placement, tracking, and lifecycle management.
Supports market, limit, and stop orders with retry logic.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from uuid import uuid4
import asyncio
from loguru import logger


class OrderStatus(Enum):
    """Order status states"""
    PENDING = "PENDING"
    SUBMITTED = "SUBMITTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class OrderType(Enum):
    """Order types"""
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LIMIT = "STOP_LIMIT"


class OrderSide(Enum):
    """Order side"""
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Order:
    """
    Order representation
    
    Tracks complete order lifecycle from creation to completion.
    """
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: float = 0.0
    average_fill_price: Optional[float] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    filled_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_active(self) -> bool:
        """Check if order is still active"""
        return self.status in [OrderStatus.PENDING, OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED]
    
    def is_complete(self) -> bool:
        """Check if order is complete"""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELED, OrderStatus.REJECTED, OrderStatus.EXPIRED, OrderStatus.FAILED]
    
    def update_status(self, status: OrderStatus, filled_qty: float = 0.0, avg_price: Optional[float] = None) -> None:
        """Update order status"""
        self.status = status
        self.updated_at = datetime.now()
        
        if filled_qty > 0:
            self.filled_quantity = filled_qty
        
        if avg_price is not None:
            self.average_fill_price = avg_price
        
        if status == OrderStatus.FILLED:
            self.filled_at = datetime.now()


class OrderManager:
    """
    Manages order placement and tracking
    
    Responsibilities:
    - Place orders through exchange interface
    - Track order lifecycle
    - Handle order amendments and cancellations
    - Monitor order status
    - Implement retry logic for failed orders
    """
    
    def __init__(self, exchange_interface):
        """
        Initialize order manager
        
        Args:
            exchange_interface: Exchange interface for order execution
        """
        self.exchange = exchange_interface
        self.orders: Dict[str, Order] = {}
        self.active_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        self.max_retries = 3
        self.retry_delay = 1.0  # seconds
        
    async def place_order(self,
                         symbol: str,
                         side: OrderSide,
                         order_type: OrderType,
                         quantity: float,
                         price: Optional[float] = None,
                         stop_price: Optional[float] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> Order:
        """
        Place a new order
        
        Args:
            symbol: Trading pair symbol
            side: Order side (BUY/SELL)
            order_type: Order type (MARKET/LIMIT/etc)
            quantity: Order quantity
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            metadata: Additional order metadata
            
        Returns:
            Order object
        """
        client_order_id = f"order_{uuid4().hex[:16]}"
        
        order = Order(
            order_id="",  # Will be set by exchange
            client_order_id=client_order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            stop_price=stop_price,
            metadata=metadata or {}
        )
        
        self.orders[client_order_id] = order
        self.active_orders[client_order_id] = order
        
        logger.info(f"Placing {order_type.value} {side.value} order: {symbol} qty={quantity} "
                   f"price={price} client_id={client_order_id}")
        
        success = False
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                exchange_response = await self.exchange.submit_order(
                    symbol=symbol,
                    side=side.value,
                    order_type=order_type.value,
                    quantity=quantity,
                    price=price,
                    stop_price=stop_price,
                    client_order_id=client_order_id
                )
                
                order.order_id = exchange_response.get('order_id', client_order_id)
                order.status = OrderStatus.SUBMITTED
                order.updated_at = datetime.now()
                
                logger.info(f"Order submitted successfully: {order.order_id}")
                success = True
                break
                
            except Exception as e:
                last_error = e
                logger.warning(f"Order submission attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
        
        if not success:
            order.status = OrderStatus.FAILED
            order.metadata['error'] = str(last_error)
            logger.error(f"Order submission failed after {self.max_retries} attempts: {last_error}")
            
            if client_order_id in self.active_orders:
                del self.active_orders[client_order_id]
        
        return order
    
    async def cancel_order(self, client_order_id: str) -> bool:
        """
        Cancel an order
        
        Args:
            client_order_id: Client order ID
            
        Returns:
            True if canceled successfully, False otherwise
        """
        if client_order_id not in self.orders:
            logger.error(f"Order not found: {client_order_id}")
            return False
        
        order = self.orders[client_order_id]
        
        if not order.is_active():
            logger.warning(f"Order is not active: {client_order_id} (status: {order.status.value})")
            return False
        
        try:
            await self.exchange.cancel_order(order.symbol, order.order_id)
            
            order.update_status(OrderStatus.CANCELED)
            
            if client_order_id in self.active_orders:
                del self.active_orders[client_order_id]
            
            logger.info(f"Order canceled: {client_order_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {client_order_id}: {e}")
            return False
    
    async def update_order_status(self, client_order_id: str) -> Optional[Order]:
        """
        Update order status from exchange
        
        Args:
            client_order_id: Client order ID
            
        Returns:
            Updated order or None if not found
        """
        if client_order_id not in self.orders:
            logger.error(f"Order not found: {client_order_id}")
            return None
        
        order = self.orders[client_order_id]
        
        try:
            exchange_order = await self.exchange.get_order_status(order.symbol, order.order_id)
            
            status_map = {
                'NEW': OrderStatus.SUBMITTED,
                'PARTIALLY_FILLED': OrderStatus.PARTIALLY_FILLED,
                'FILLED': OrderStatus.FILLED,
                'CANCELED': OrderStatus.CANCELED,
                'REJECTED': OrderStatus.REJECTED,
                'EXPIRED': OrderStatus.EXPIRED
            }
            
            exchange_status = exchange_order.get('status', 'UNKNOWN')
            new_status = status_map.get(exchange_status, order.status)
            
            filled_qty = float(exchange_order.get('executedQty', 0))
            avg_price = float(exchange_order.get('avgPrice', 0)) if filled_qty > 0 else None
            
            order.update_status(new_status, filled_qty, avg_price)
            
            if order.is_complete() and client_order_id in self.active_orders:
                del self.active_orders[client_order_id]
                self.order_history.append(order)
            
            logger.debug(f"Updated order status: {client_order_id} -> {new_status.value}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to update order status {client_order_id}: {e}")
            return None
    
    async def update_all_active_orders(self) -> None:
        """Update status for all active orders"""
        for client_order_id in list(self.active_orders.keys()):
            await self.update_order_status(client_order_id)
    
    def get_order(self, client_order_id: str) -> Optional[Order]:
        """Get order by client order ID"""
        return self.orders.get(client_order_id)
    
    def get_active_orders(self, symbol: Optional[str] = None) -> List[Order]:
        """
        Get all active orders
        
        Args:
            symbol: Filter by symbol (optional)
            
        Returns:
            List of active orders
        """
        orders = list(self.active_orders.values())
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        return orders
    
    def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> List[Order]:
        """
        Get order history
        
        Args:
            symbol: Filter by symbol (optional)
            limit: Maximum number of orders to return
            
        Returns:
            List of historical orders
        """
        orders = self.order_history[-limit:]
        
        if symbol:
            orders = [o for o in orders if o.symbol == symbol]
        
        return orders
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get order statistics
        
        Returns:
            Dictionary with order statistics
        """
        total_orders = len(self.orders)
        active_orders = len(self.active_orders)
        
        status_counts = {}
        for order in self.orders.values():
            status = order.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            'total_orders': total_orders,
            'active_orders': active_orders,
            'completed_orders': total_orders - active_orders,
            'status_breakdown': status_counts
        }
