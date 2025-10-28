"""
Execution Simulator

Simulates order execution in demo mode with realistic slippage, fees, and partial fills.
Maintains virtual account balance and positions for testing.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import random
from loguru import logger

from .exchange_interface import ExchangeInterface


class ExecutionSimulator(ExchangeInterface):
    """
    Simulates order execution for demo/paper trading
    
    Features:
    - Realistic slippage modeling based on order size and market conditions
    - Exchange fee simulation (maker/taker fees)
    - Partial fill simulation for limit orders
    - Virtual account balance and position tracking
    """
    
    def __init__(self, 
                 initial_balance: float = 10000.0,
                 base_currency: str = 'USDT',
                 maker_fee: float = 0.0002,  # 0.02%
                 taker_fee: float = 0.0004,  # 0.04%
                 slippage_factor: float = 0.001):  # 0.1%
        """
        Initialize execution simulator
        
        Args:
            initial_balance: Starting balance in base currency
            base_currency: Base currency (e.g., 'USDT')
            maker_fee: Maker fee percentage
            taker_fee: Taker fee percentage
            slippage_factor: Base slippage factor
        """
        self.initial_balance = initial_balance
        self.base_currency = base_currency
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.slippage_factor = slippage_factor
        
        self.balance = {base_currency: initial_balance}
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.orders: Dict[str, Dict[str, Any]] = {}
        self.order_counter = 0
        
        self.market_prices: Dict[str, float] = {}
        
        logger.info(f"Initialized execution simulator with {initial_balance} {base_currency}")
    
    def update_market_price(self, symbol: str, price: float) -> None:
        """
        Update market price for a symbol
        
        Args:
            symbol: Trading pair symbol
            price: Current market price
        """
        self.market_prices[symbol] = price
    
    def _calculate_slippage(self, symbol: str, side: str, quantity: float, price: float) -> float:
        """
        Calculate realistic slippage based on order parameters
        
        Args:
            symbol: Trading pair symbol
            side: Order side ('BUY' or 'SELL')
            quantity: Order quantity
            price: Order price
            
        Returns:
            Slippage-adjusted price
        """
        slippage = self.slippage_factor
        
        size_factor = min(quantity / 10.0, 2.0)  # Cap at 2x
        slippage *= (1 + size_factor)
        
        random_factor = random.uniform(0.5, 1.5)
        slippage *= random_factor
        
        if side.upper() == 'BUY':
            adjusted_price = price * (1 + slippage)
        else:
            adjusted_price = price * (1 - slippage)
        
        return adjusted_price
    
    def _calculate_fee(self, order_type: str, quantity: float, price: float) -> float:
        """
        Calculate trading fee
        
        Args:
            order_type: Order type ('MARKET' or 'LIMIT')
            quantity: Order quantity
            price: Execution price
            
        Returns:
            Fee amount in base currency
        """
        notional_value = quantity * price
        
        if order_type == 'MARKET':
            fee = notional_value * self.taker_fee
        else:
            fee = notional_value * self.maker_fee
        
        return fee
    
    async def submit_order(self,
                          symbol: str,
                          side: str,
                          order_type: str,
                          quantity: float,
                          price: Optional[float] = None,
                          stop_price: Optional[float] = None,
                          client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Simulate order submission
        
        Args:
            symbol: Trading pair symbol
            side: Order side ('BUY' or 'SELL')
            order_type: Order type ('MARKET', 'LIMIT', etc.)
            quantity: Order quantity
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            client_order_id: Client order ID
            
        Returns:
            Simulated order response
        """
        self.order_counter += 1
        order_id = f"SIM_{self.order_counter:06d}"
        
        market_price = self.market_prices.get(symbol)
        if market_price is None:
            raise ValueError(f"No market price available for {symbol}")
        
        if order_type == 'MARKET':
            execution_price = self._calculate_slippage(symbol, side, quantity, market_price)
            status = 'FILLED'
            filled_qty = quantity
            
        elif order_type == 'LIMIT':
            if price is None:
                raise ValueError("Price required for limit orders")
            
            fill_probability = random.uniform(0.3, 1.0)
            
            if side.upper() == 'BUY' and price >= market_price:
                filled_qty = quantity * fill_probability
                execution_price = min(price, market_price)
                status = 'PARTIALLY_FILLED' if filled_qty < quantity else 'FILLED'
            elif side.upper() == 'SELL' and price <= market_price:
                filled_qty = quantity * fill_probability
                execution_price = max(price, market_price)
                status = 'PARTIALLY_FILLED' if filled_qty < quantity else 'FILLED'
            else:
                filled_qty = 0
                execution_price = price
                status = 'NEW'
        
        else:
            raise ValueError(f"Unsupported order type: {order_type}")
        
        fee = self._calculate_fee(order_type, filled_qty, execution_price) if filled_qty > 0 else 0
        
        if filled_qty > 0:
            self._execute_fill(symbol, side, filled_qty, execution_price, fee)
        
        order = {
            'order_id': order_id,
            'symbol': symbol,
            'side': side,
            'type': order_type,
            'quantity': quantity,
            'price': price,
            'stop_price': stop_price,
            'status': status,
            'filled': filled_qty,
            'remaining': quantity - filled_qty,
            'executedQty': filled_qty,
            'avgPrice': execution_price if filled_qty > 0 else None,
            'fee': fee,
            'timestamp': datetime.now().timestamp() * 1000
        }
        
        self.orders[order_id] = order
        
        logger.info(f"Simulated order: {order_id} - {side} {filled_qty}/{quantity} {symbol} @ {execution_price:.2f} "
                   f"(fee: {fee:.4f}, status: {status})")
        
        return order
    
    def _execute_fill(self, symbol: str, side: str, quantity: float, price: float, fee: float) -> None:
        """
        Execute order fill and update account state
        
        Args:
            symbol: Trading pair symbol
            side: Order side
            quantity: Filled quantity
            price: Execution price
            fee: Trading fee
        """
        base, quote = symbol.split('/')
        
        if side.upper() == 'BUY':
            cost = quantity * price + fee
            
            if self.balance.get(quote, 0) < cost:
                raise ValueError(f"Insufficient {quote} balance: need {cost}, have {self.balance.get(quote, 0)}")
            
            self.balance[quote] = self.balance.get(quote, 0) - cost
            self.balance[base] = self.balance.get(base, 0) + quantity
            
            if symbol not in self.positions:
                self.positions[symbol] = {
                    'symbol': symbol,
                    'side': 'long',
                    'quantity': 0,
                    'entry_price': 0,
                    'unrealized_pnl': 0
                }
            
            pos = self.positions[symbol]
            total_qty = pos['quantity'] + quantity
            pos['entry_price'] = ((pos['entry_price'] * pos['quantity']) + (price * quantity)) / total_qty
            pos['quantity'] = total_qty
        
        else:  # SELL
            revenue = quantity * price - fee
            
            if self.balance.get(base, 0) < quantity:
                raise ValueError(f"Insufficient {base} balance: need {quantity}, have {self.balance.get(base, 0)}")
            
            self.balance[base] = self.balance.get(base, 0) - quantity
            self.balance[quote] = self.balance.get(quote, 0) + revenue
            
            if symbol in self.positions:
                pos = self.positions[symbol]
                pos['quantity'] -= quantity
                
                if pos['quantity'] <= 0:
                    del self.positions[symbol]
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Simulate order cancellation
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        if order_id not in self.orders:
            raise ValueError(f"Order not found: {order_id}")
        
        order = self.orders[order_id]
        
        if order['status'] in ['FILLED', 'CANCELED', 'REJECTED']:
            raise ValueError(f"Cannot cancel order in status: {order['status']}")
        
        order['status'] = 'CANCELED'
        
        logger.info(f"Canceled simulated order: {order_id}")
        
        return order
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Get simulated order status
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
            
        Returns:
            Order status information
        """
        if order_id not in self.orders:
            raise ValueError(f"Order not found: {order_id}")
        
        return self.orders[order_id]
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        Get simulated account balance
        
        Returns:
            Account balance information
        """
        return {
            'total': self.balance.copy(),
            'free': self.balance.copy(),  # Simplified - assume all balance is free
            'used': {},
            'timestamp': datetime.now().timestamp() * 1000
        }
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get simulated open positions
        
        Returns:
            List of open positions
        """
        positions = []
        
        for symbol, pos in self.positions.items():
            current_price = self.market_prices.get(symbol, pos['entry_price'])
            unrealized_pnl = (current_price - pos['entry_price']) * pos['quantity']
            
            positions.append({
                'symbol': symbol,
                'side': pos['side'],
                'contracts': pos['quantity'],
                'contractSize': 1.0,
                'unrealizedPnl': unrealized_pnl,
                'percentage': (unrealized_pnl / (pos['entry_price'] * pos['quantity'])) * 100 if pos['quantity'] > 0 else 0,
                'entryPrice': pos['entry_price'],
                'markPrice': current_price,
                'liquidationPrice': None,  # Not applicable for spot
                'leverage': 1.0
            })
        
        return positions
    
    def get_account_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive account summary
        
        Returns:
            Account summary with balance, positions, and P&L
        """
        total_value = self.balance.get(self.base_currency, 0)
        
        for symbol, pos in self.positions.items():
            current_price = self.market_prices.get(symbol, pos['entry_price'])
            position_value = pos['quantity'] * current_price
            total_value += position_value
        
        total_pnl = total_value - self.initial_balance
        pnl_percentage = (total_pnl / self.initial_balance) * 100 if self.initial_balance > 0 else 0
        
        return {
            'initial_balance': self.initial_balance,
            'current_balance': self.balance.get(self.base_currency, 0),
            'total_value': total_value,
            'total_pnl': total_pnl,
            'pnl_percentage': pnl_percentage,
            'num_positions': len(self.positions),
            'num_orders': len(self.orders)
        }
    
    def reset(self) -> None:
        """Reset simulator to initial state"""
        self.balance = {self.base_currency: self.initial_balance}
        self.positions = {}
        self.orders = {}
        self.order_counter = 0
        logger.info("Reset execution simulator")
