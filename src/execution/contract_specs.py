"""
Contract Specification Enforcement

Enforces exchange-specific contract specifications to prevent order rejections.
Handles tick size, step size, lot size, minimum notional, and contract multipliers.
"""

from dataclasses import dataclass
from typing import Dict, Optional
import ccxt
from loguru import logger
from decimal import Decimal, ROUND_DOWN
import math


@dataclass
class ContractSpec:
    """
    Contract specification for a trading symbol
    
    Attributes:
        symbol: Trading pair symbol (e.g., 'BTC/USDT')
        tick_size: Minimum price increment (e.g., 0.01)
        step_size: Minimum quantity increment (e.g., 0.001)
        min_notional: Minimum order value in quote currency (e.g., 10 USDT)
        lot_size: Minimum order size in base currency (e.g., 0.001 BTC)
        contract_multiplier: Contract size multiplier for futures (e.g., 1.0)
        quanto: Whether this is a quanto contract (settled in different currency)
        price_precision: Number of decimal places for price
        quantity_precision: Number of decimal places for quantity
    """
    symbol: str
    tick_size: float
    step_size: float
    min_notional: float
    lot_size: float
    contract_multiplier: float = 1.0
    quanto: bool = False
    price_precision: int = 8
    quantity_precision: int = 8


class ContractSpecManager:
    """
    Manages contract specifications for all trading symbols
    
    Fetches specs from exchange and provides rounding/validation functions.
    """
    
    def __init__(self, exchange: ccxt.Exchange):
        """
        Initialize contract spec manager
        
        Args:
            exchange: CCXT exchange instance
        """
        self.exchange = exchange
        self.specs_cache: Dict[str, ContractSpec] = {}
        logger.info("Initialized ContractSpecManager")
    
    async def fetch_specs(self, symbol: str) -> ContractSpec:
        """
        Fetch contract specifications for a symbol
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTC/USDT')
            
        Returns:
            ContractSpec with all specifications
            
        Raises:
            ValueError: If symbol not found or specs unavailable
        """
        if symbol in self.specs_cache:
            return self.specs_cache[symbol]
        
        try:
            await self.exchange.load_markets()
            
            if symbol not in self.exchange.markets:
                raise ValueError(f"Symbol {symbol} not found on exchange")
            
            market = self.exchange.markets[symbol]
            
            tick_size = market.get('precision', {}).get('price', 0.01)
            step_size = market.get('precision', {}).get('amount', 0.001)
            
            limits = market.get('limits', {})
            cost_limits = limits.get('cost', {})
            amount_limits = limits.get('amount', {})
            
            min_notional = cost_limits.get('min', 10.0)
            lot_size = amount_limits.get('min', 0.001)
            
            contract_multiplier = market.get('contractSize', 1.0)
            quanto = market.get('quanto', False)
            
            price_precision = self._calculate_precision(tick_size)
            quantity_precision = self._calculate_precision(step_size)
            
            spec = ContractSpec(
                symbol=symbol,
                tick_size=tick_size,
                step_size=step_size,
                min_notional=min_notional,
                lot_size=lot_size,
                contract_multiplier=contract_multiplier,
                quanto=quanto,
                price_precision=price_precision,
                quantity_precision=quantity_precision
            )
            
            self.specs_cache[symbol] = spec
            logger.info(f"Fetched specs for {symbol}: tick={tick_size}, step={step_size}, min_notional={min_notional}")
            
            return spec
            
        except Exception as e:
            logger.error(f"Failed to fetch specs for {symbol}: {e}")
            raise
    
    def _calculate_precision(self, value: float) -> int:
        """
        Calculate decimal precision from a value
        
        Args:
            value: Value to calculate precision from (e.g., 0.01)
            
        Returns:
            Number of decimal places (e.g., 2 for 0.01)
        """
        if value >= 1:
            return 0
        
        value_str = f"{value:.10f}".rstrip('0')
        
        if '.' in value_str:
            return len(value_str.split('.')[1])
        return 0
    
    def round_price(self, price: float, spec: ContractSpec) -> float:
        """
        Round price to exchange tick size
        
        Args:
            price: Price to round
            spec: Contract specification
            
        Returns:
            Rounded price
        """
        if spec.tick_size == 0:
            return price
        
        decimal_price = Decimal(str(price))
        decimal_tick = Decimal(str(spec.tick_size))
        
        rounded = (decimal_price / decimal_tick).quantize(Decimal('1'), rounding=ROUND_DOWN) * decimal_tick
        
        return float(rounded)
    
    def round_quantity(self, quantity: float, spec: ContractSpec) -> float:
        """
        Round quantity to exchange step size
        
        Args:
            quantity: Quantity to round
            spec: Contract specification
            
        Returns:
            Rounded quantity
        """
        if spec.step_size == 0:
            return quantity
        
        decimal_qty = Decimal(str(quantity))
        decimal_step = Decimal(str(spec.step_size))
        
        rounded = (decimal_qty / decimal_step).quantize(Decimal('1'), rounding=ROUND_DOWN) * decimal_step
        
        return float(rounded)
    
    def validate_order(self, symbol: str, side: str, quantity: float, price: Optional[float] = None) -> Dict[str, any]:
        """
        Validate order parameters against contract specs
        
        Args:
            symbol: Trading pair symbol
            side: Order side ('BUY' or 'SELL')
            quantity: Order quantity
            price: Order price (for limit orders)
            
        Returns:
            Dict with validation result:
                - valid: bool
                - errors: List[str]
                - rounded_quantity: float
                - rounded_price: Optional[float]
        """
        if symbol not in self.specs_cache:
            return {
                'valid': False,
                'errors': [f"Specs not loaded for {symbol}. Call fetch_specs() first."],
                'rounded_quantity': quantity,
                'rounded_price': price
            }
        
        spec = self.specs_cache[symbol]
        errors = []
        
        rounded_quantity = self.round_quantity(quantity, spec)
        rounded_price = self.round_price(price, spec) if price else None
        
        if rounded_quantity < spec.lot_size:
            errors.append(f"Quantity {rounded_quantity} below minimum lot size {spec.lot_size}")
        
        if price:
            notional = rounded_quantity * rounded_price
            if notional < spec.min_notional:
                errors.append(f"Notional value {notional} below minimum {spec.min_notional}")
        
        if rounded_quantity != quantity:
            logger.debug(f"Rounded quantity {quantity} -> {rounded_quantity} (step_size={spec.step_size})")
        
        if price and rounded_price != price:
            logger.debug(f"Rounded price {price} -> {rounded_price} (tick_size={spec.tick_size})")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'rounded_quantity': rounded_quantity,
            'rounded_price': rounded_price
        }
    
    def get_min_order_size(self, symbol: str, price: float) -> float:
        """
        Calculate minimum order size to meet min_notional requirement
        
        Args:
            symbol: Trading pair symbol
            price: Current price
            
        Returns:
            Minimum order size in base currency
        """
        if symbol not in self.specs_cache:
            raise ValueError(f"Specs not loaded for {symbol}")
        
        spec = self.specs_cache[symbol]
        
        min_size_from_notional = spec.min_notional / price
        
        min_size = max(spec.lot_size, min_size_from_notional)
        
        rounded_size = self.round_quantity(min_size, spec)
        
        if rounded_size * price < spec.min_notional:
            rounded_size = self.round_quantity(rounded_size + spec.step_size, spec)
        
        return rounded_size
    
    def clear_cache(self):
        """Clear the specs cache"""
        self.specs_cache.clear()
        logger.info("Cleared contract specs cache")
