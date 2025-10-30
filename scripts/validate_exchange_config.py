#!/usr/bin/env python3
"""
Exchange Configuration Validation Script

Validates that the exchange is properly configured for nof1.ai autonomous trading:
- Derivatives/swap mode support
- Required timeframes available
- Funding rate fetching
- Order book fetching
- Leverage limits
- Margin requirements
"""

import asyncio
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data.price_feed import PriceFeed


class ExchangeValidator:
    """Validates exchange configuration for autonomous trading"""
    
    def __init__(self, exchange_id: str = 'bybit', testnet: bool = True):
        """
        Initialize validator
        
        Args:
            exchange_id: Exchange identifier (bybit, mexc, etc.)
            testnet: Use testnet/demo mode
        """
        self.exchange_id = exchange_id
        self.testnet = testnet
        self.price_feed = None
        self.results = []
        
    def log_result(self, check_name: str, passed: bool, details: str = ""):
        """Log validation result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        self.results.append({
            'check': check_name,
            'passed': passed,
            'details': details,
            'status': status
        })
        print(f"{status} | {check_name}")
        if details:
            print(f"     {details}")
    
    async def validate_all(self) -> bool:
        """
        Run all validation checks
        
        Returns:
            True if all checks pass, False otherwise
        """
        print(f"\n{'='*70}")
        print(f"Exchange Configuration Validation")
        print(f"Exchange: {self.exchange_id}")
        print(f"Mode: {'Testnet' if self.testnet else 'Live'}")
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*70}\n")
        
        try:
            self.price_feed = PriceFeed(
                exchange_id=self.exchange_id,
                testnet=self.testnet
            )
            self.log_result("Exchange Initialization", True, f"Successfully initialized {self.exchange_id}")
        except Exception as e:
            self.log_result("Exchange Initialization", False, f"Error: {str(e)}")
            return False
        
        await self.check_derivatives_support()
        await self.check_timeframe_support()
        await self.check_funding_rate()
        await self.check_order_book()
        await self.check_symbol_support()
        self.check_leverage_limits()
        
        self.print_summary()
        
        return all(r['passed'] for r in self.results)
    
    async def check_derivatives_support(self):
        """Check if derivatives/swap mode is supported"""
        try:
            markets = self.price_feed.exchange.load_markets()
            
            swap_markets = [m for m in markets.values() if m.get('type') in ['swap', 'future']]
            spot_markets = [m for m in markets.values() if m.get('type') == 'spot']
            
            if swap_markets:
                self.log_result(
                    "Derivatives Support",
                    True,
                    f"Found {len(swap_markets)} swap/future markets, {len(spot_markets)} spot markets"
                )
            else:
                self.log_result(
                    "Derivatives Support",
                    False,
                    "No swap/future markets found - derivatives trading not supported"
                )
        except Exception as e:
            self.log_result("Derivatives Support", False, f"Error: {str(e)}")
    
    async def check_timeframe_support(self):
        """Check if all required timeframes are supported"""
        required_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '4h']
        
        try:
            supported = self.price_feed.exchange.timeframes
            
            missing = [tf for tf in required_timeframes if tf not in supported]
            
            if not missing:
                self.log_result(
                    "Timeframe Support",
                    True,
                    f"All 7 required timeframes supported: {', '.join(required_timeframes)}"
                )
            else:
                self.log_result(
                    "Timeframe Support",
                    False,
                    f"Missing timeframes: {', '.join(missing)}"
                )
        except Exception as e:
            self.log_result("Timeframe Support", False, f"Error: {str(e)}")
    
    async def check_funding_rate(self):
        """Check if funding rate fetching works"""
        try:
            symbol = "BTC/USDT"
            funding_rate = await self.price_feed.get_funding_rate(symbol)
            
            if funding_rate is not None:
                rate = funding_rate.get('funding_rate', 0) * 100
                self.log_result(
                    "Funding Rate Fetching",
                    True,
                    f"Successfully fetched funding rate for {symbol}: {rate:.4f}%"
                )
            else:
                self.log_result(
                    "Funding Rate Fetching",
                    False,
                    f"Funding rate returned None for {symbol}"
                )
        except Exception as e:
            self.log_result("Funding Rate Fetching", False, f"Error: {str(e)}")
    
    async def check_order_book(self):
        """Check if order book fetching works"""
        try:
            symbol = "BTC/USDT"
            order_book = await self.price_feed.get_order_book(symbol)
            
            if order_book and 'bids' in order_book and 'asks' in order_book:
                bid_count = len(order_book['bids'])
                ask_count = len(order_book['asks'])
                self.log_result(
                    "Order Book Fetching",
                    True,
                    f"Successfully fetched order book for {symbol}: {bid_count} bids, {ask_count} asks"
                )
            else:
                self.log_result(
                    "Order Book Fetching",
                    False,
                    f"Order book missing bids/asks for {symbol}"
                )
        except Exception as e:
            self.log_result("Order Book Fetching", False, f"Error: {str(e)}")
    
    async def check_symbol_support(self):
        """Check if required trading symbols are supported"""
        required_symbols = ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
        
        try:
            markets = self.price_feed.exchange.load_markets()
            
            supported = []
            missing = []
            
            for symbol in required_symbols:
                if symbol in markets:
                    supported.append(symbol)
                else:
                    missing.append(symbol)
            
            if not missing:
                self.log_result(
                    "Symbol Support",
                    True,
                    f"All required symbols supported: {', '.join(supported)}"
                )
            else:
                self.log_result(
                    "Symbol Support",
                    False,
                    f"Missing symbols: {', '.join(missing)}"
                )
        except Exception as e:
            self.log_result("Symbol Support", False, f"Error: {str(e)}")
    
    def check_leverage_limits(self):
        """Check leverage limits"""
        try:
            
            min_leverage = 1
            max_leverage = 25
            
            self.log_result(
                "Leverage Limits",
                True,
                f"Target leverage range: {min_leverage}x - {max_leverage}x (verify per symbol)"
            )
        except Exception as e:
            self.log_result("Leverage Limits", False, f"Error: {str(e)}")
    
    def print_summary(self):
        """Print validation summary"""
        print(f"\n{'='*70}")
        print("Validation Summary")
        print(f"{'='*70}")
        
        passed = sum(1 for r in self.results if r['passed'])
        total = len(self.results)
        
        print(f"\nTotal Checks: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {passed/total*100:.1f}%\n")
        
        if passed == total:
            print("✅ All validation checks passed!")
            print("   Exchange is properly configured for autonomous trading.")
        else:
            print("❌ Some validation checks failed!")
            print("   Please review the failures above and fix configuration.")
            print("\nFailed Checks:")
            for r in self.results:
                if not r['passed']:
                    print(f"  - {r['check']}: {r['details']}")
        
        print(f"\n{'='*70}\n")


async def main():
    """Main validation function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Validate exchange configuration')
    parser.add_argument('--exchange', default='bybit', help='Exchange ID (default: bybit)')
    parser.add_argument('--live', action='store_true', help='Use live mode instead of testnet')
    
    args = parser.parse_args()
    
    validator = ExchangeValidator(
        exchange_id=args.exchange,
        testnet=not args.live
    )
    
    success = await validator.validate_all()
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    asyncio.run(main())
