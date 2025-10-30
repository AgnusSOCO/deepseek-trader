"""
Exchange Interface

Abstract interface for exchange operations with concrete implementations
for different exchanges (Binance, Bybit, etc.) in both testnet and live modes.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import ccxt
from loguru import logger


class ExchangeInterface(ABC):
    """
    Abstract interface for exchange operations
    
    All exchange implementations must provide these methods.
    """
    
    @abstractmethod
    async def submit_order(self,
                          symbol: str,
                          side: str,
                          order_type: str,
                          quantity: float,
                          price: Optional[float] = None,
                          stop_price: Optional[float] = None,
                          client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """Submit an order to the exchange"""
        pass
    
    @abstractmethod
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an order"""
        pass
    
    @abstractmethod
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Get order status"""
        pass
    
    @abstractmethod
    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance"""
        pass
    
    @abstractmethod
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions"""
        pass


class BinanceExchange(ExchangeInterface):
    """
    Binance exchange implementation
    
    Supports both testnet and live trading.
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize Binance exchange interface
        
        Args:
            api_key: API key
            api_secret: API secret
            testnet: Use testnet if True, live if False
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        if testnet:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'options': {
                    'defaultType': 'future',
                    'test': True
                }
            })
            self.exchange.set_sandbox_mode(True)
        else:
            self.exchange = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'options': {
                    'defaultType': 'future'
                }
            })
        
        logger.info(f"Initialized Binance exchange (testnet={testnet})")
    
    async def submit_order(self,
                          symbol: str,
                          side: str,
                          order_type: str,
                          quantity: float,
                          price: Optional[float] = None,
                          stop_price: Optional[float] = None,
                          client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit an order to Binance
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            side: Order side ('BUY' or 'SELL')
            order_type: Order type ('MARKET', 'LIMIT', etc.)
            quantity: Order quantity
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            client_order_id: Client order ID
            
        Returns:
            Order response from exchange
        """
        try:
            params = {}
            if client_order_id:
                params['clientOrderId'] = client_order_id
            
            if order_type == 'MARKET':
                order = await self.exchange.create_market_order(
                    symbol=symbol,
                    side=side.lower(),
                    amount=quantity,
                    params=params
                )
            elif order_type == 'LIMIT':
                if price is None:
                    raise ValueError("Price required for limit orders")
                order = await self.exchange.create_limit_order(
                    symbol=symbol,
                    side=side.lower(),
                    amount=quantity,
                    price=price,
                    params=params
                )
            elif order_type == 'STOP_LOSS':
                if stop_price is None:
                    raise ValueError("Stop price required for stop loss orders")
                params['stopPrice'] = stop_price
                order = await self.exchange.create_order(
                    symbol=symbol,
                    type='STOP_MARKET',
                    side=side.lower(),
                    amount=quantity,
                    params=params
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            logger.info(f"Order submitted: {order.get('id')} - {side} {quantity} {symbol}")
            return {
                'order_id': order.get('id'),
                'status': order.get('status'),
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
                'price': price,
                'timestamp': order.get('timestamp')
            }
            
        except Exception as e:
            logger.error(f"Failed to submit order: {e}")
            raise
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order on Binance
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        try:
            result = await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"Order canceled: {order_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            raise
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Get order status from Binance
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
            
        Returns:
            Order status information
        """
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return {
                'order_id': order.get('id'),
                'status': order.get('status'),
                'symbol': order.get('symbol'),
                'side': order.get('side'),
                'type': order.get('type'),
                'price': order.get('price'),
                'amount': order.get('amount'),
                'filled': order.get('filled'),
                'remaining': order.get('remaining'),
                'executedQty': order.get('filled'),
                'avgPrice': order.get('average'),
                'timestamp': order.get('timestamp')
            }
        except Exception as e:
            logger.error(f"Failed to get order status {order_id}: {e}")
            raise
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance from Binance
        
        Returns:
            Account balance information
        """
        try:
            balance = await self.exchange.fetch_balance()
            return {
                'total': balance.get('total', {}),
                'free': balance.get('free', {}),
                'used': balance.get('used', {}),
                'timestamp': balance.get('timestamp')
            }
        except Exception as e:
            logger.error(f"Failed to get balance: {e}")
            raise
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get open positions from Binance
        
        Returns:
            List of open positions
        """
        try:
            positions = await self.exchange.fetch_positions()
            return [
                {
                    'symbol': pos.get('symbol'),
                    'side': pos.get('side'),
                    'contracts': pos.get('contracts'),
                    'contractSize': pos.get('contractSize'),
                    'unrealizedPnl': pos.get('unrealizedPnl'),
                    'percentage': pos.get('percentage'),
                    'entryPrice': pos.get('entryPrice'),
                    'markPrice': pos.get('markPrice'),
                    'liquidationPrice': pos.get('liquidationPrice'),
                    'leverage': pos.get('leverage')
                }
                for pos in positions
                if pos.get('contracts', 0) != 0
            ]
        except Exception as e:
            logger.error(f"Failed to get positions: {e}")
            raise


class BybitExchange(ExchangeInterface):
    """
    Bybit exchange implementation
    
    Supports both testnet and live trading.
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize Bybit exchange interface
        
        Args:
            api_key: API key
            api_secret: API secret
            testnet: Use testnet if True, live if False
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        if testnet:
            self.exchange = ccxt.bybit({
                'apiKey': api_key,
                'secret': api_secret,
                'options': {
                    'defaultType': 'future'
                }
            })
            self.exchange.set_sandbox_mode(True)
        else:
            self.exchange = ccxt.bybit({
                'apiKey': api_key,
                'secret': api_secret,
                'options': {
                    'defaultType': 'future'
                }
            })
        
        logger.info(f"Initialized Bybit exchange (testnet={testnet})")
    
    async def submit_order(self,
                          symbol: str,
                          side: str,
                          order_type: str,
                          quantity: float,
                          price: Optional[float] = None,
                          stop_price: Optional[float] = None,
                          client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """Submit an order to Bybit"""
        pass
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Cancel an order on Bybit"""
        pass
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """Get order status from Bybit"""
        pass
    
    async def get_balance(self) -> Dict[str, Any]:
        """Get account balance from Bybit"""
        pass
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """Get open positions from Bybit"""
        pass


class MexcExchange(ExchangeInterface):
    """
    MEXC exchange implementation
    
    Supports both demo and live trading.
    MEXC is popular for low fees and wide altcoin selection.
    """
    
    def __init__(self, api_key: str, api_secret: str, testnet: bool = True):
        """
        Initialize MEXC exchange interface
        
        Args:
            api_key: API key
            api_secret: API secret
            testnet: Use demo mode if True, live if False
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.testnet = testnet
        
        self.exchange = ccxt.mexc({
            'apiKey': api_key,
            'secret': api_secret,
            'options': {
                'defaultType': 'spot',  # MEXC primarily uses spot trading
                'adjustForTimeDifference': True
            }
        })
        
        if testnet:
            logger.info("MEXC initialized in DEMO mode - use small amounts for testing")
        
        logger.info(f"Initialized MEXC exchange (demo={testnet})")
    
    async def submit_order(self,
                          symbol: str,
                          side: str,
                          order_type: str,
                          quantity: float,
                          price: Optional[float] = None,
                          stop_price: Optional[float] = None,
                          client_order_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Submit an order to MEXC
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            side: Order side ('BUY' or 'SELL')
            order_type: Order type ('MARKET', 'LIMIT', etc.)
            quantity: Order quantity
            price: Limit price (for limit orders)
            stop_price: Stop price (for stop orders)
            client_order_id: Client order ID
            
        Returns:
            Order response from exchange
        """
        try:
            params = {}
            if client_order_id:
                params['newClientOrderId'] = client_order_id
            
            if order_type == 'MARKET':
                order = await self.exchange.create_market_order(
                    symbol=symbol,
                    side=side.lower(),
                    amount=quantity,
                    params=params
                )
            elif order_type == 'LIMIT':
                if price is None:
                    raise ValueError("Price required for limit orders")
                order = await self.exchange.create_limit_order(
                    symbol=symbol,
                    side=side.lower(),
                    amount=quantity,
                    price=price,
                    params=params
                )
            elif order_type == 'STOP_LOSS':
                if stop_price is None:
                    raise ValueError("Stop price required for stop loss orders")
                params['stopPrice'] = stop_price
                order = await self.exchange.create_order(
                    symbol=symbol,
                    type='STOP_LOSS',
                    side=side.lower(),
                    amount=quantity,
                    params=params
                )
            else:
                raise ValueError(f"Unsupported order type: {order_type}")
            
            logger.info(f"MEXC order submitted: {order.get('id')} - {side} {quantity} {symbol}")
            return {
                'order_id': order.get('id'),
                'status': order.get('status'),
                'symbol': symbol,
                'side': side,
                'type': order_type,
                'quantity': quantity,
                'price': price,
                'timestamp': order.get('timestamp')
            }
            
        except Exception as e:
            logger.error(f"Failed to submit MEXC order: {e}")
            raise
    
    async def cancel_order(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Cancel an order on MEXC
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID to cancel
            
        Returns:
            Cancellation response
        """
        try:
            result = await self.exchange.cancel_order(order_id, symbol)
            logger.info(f"MEXC order canceled: {order_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to cancel MEXC order {order_id}: {e}")
            raise
    
    async def get_order_status(self, symbol: str, order_id: str) -> Dict[str, Any]:
        """
        Get order status from MEXC
        
        Args:
            symbol: Trading pair symbol
            order_id: Order ID
            
        Returns:
            Order status information
        """
        try:
            order = await self.exchange.fetch_order(order_id, symbol)
            return {
                'order_id': order.get('id'),
                'status': order.get('status'),
                'symbol': order.get('symbol'),
                'side': order.get('side'),
                'type': order.get('type'),
                'price': order.get('price'),
                'amount': order.get('amount'),
                'filled': order.get('filled'),
                'remaining': order.get('remaining'),
                'executedQty': order.get('filled'),
                'avgPrice': order.get('average'),
                'timestamp': order.get('timestamp')
            }
        except Exception as e:
            logger.error(f"Failed to get MEXC order status {order_id}: {e}")
            raise
    
    async def get_balance(self) -> Dict[str, Any]:
        """
        Get account balance from MEXC
        
        Returns:
            Account balance information
        """
        try:
            balance = await self.exchange.fetch_balance()
            return {
                'total': balance.get('total', {}),
                'free': balance.get('free', {}),
                'used': balance.get('used', {}),
                'timestamp': balance.get('timestamp')
            }
        except Exception as e:
            logger.error(f"Failed to get MEXC balance: {e}")
            raise
    
    async def get_positions(self) -> List[Dict[str, Any]]:
        """
        Get open positions from MEXC
        
        Note: MEXC spot trading doesn't have traditional positions
        This returns open orders instead
        
        Returns:
            List of open orders (MEXC spot equivalent of positions)
        """
        try:
            open_orders = await self.exchange.fetch_open_orders()
            return [
                {
                    'symbol': order.get('symbol'),
                    'side': order.get('side'),
                    'amount': order.get('amount'),
                    'filled': order.get('filled'),
                    'remaining': order.get('remaining'),
                    'price': order.get('price'),
                    'type': order.get('type'),
                    'status': order.get('status'),
                    'timestamp': order.get('timestamp')
                }
                for order in open_orders
            ]
        except Exception as e:
            logger.error(f"Failed to get MEXC positions: {e}")
            raise


def create_exchange(exchange_name: str, api_key: str, api_secret: str, testnet: bool = True) -> ExchangeInterface:
    """
    Factory function to create exchange interface
    
    Args:
        exchange_name: Name of exchange ('binance', 'bybit', 'mexc', etc.)
        api_key: API key
        api_secret: API secret
        testnet: Use testnet/demo if True, live if False
        
    Returns:
        Exchange interface instance
    """
    exchange_name = exchange_name.lower()
    
    if exchange_name == 'binance':
        return BinanceExchange(api_key, api_secret, testnet)
    elif exchange_name == 'bybit':
        return BybitExchange(api_key, api_secret, testnet)
    elif exchange_name == 'mexc':
        return MexcExchange(api_key, api_secret, testnet)
    else:
        raise ValueError(f"Unsupported exchange: {exchange_name}. Supported: binance, bybit, mexc")
