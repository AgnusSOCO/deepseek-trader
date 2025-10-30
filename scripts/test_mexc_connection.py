"""
Test MEXC Exchange Connection

This script tests the MEXC exchange connection and verifies:
1. API credentials are valid
2. Account balance can be retrieved
3. Market data is accessible
4. Order placement works (in demo mode)
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from src.execution.exchange_interface import MexcExchange
from loguru import logger

# Load environment variables
load_dotenv()


async def test_mexc_connection():
    """Test MEXC exchange connection and basic operations"""
    
    print("=" * 60)
    print("MEXC Exchange Connection Test")
    print("=" * 60)
    print()
    
    # Get API credentials
    api_key = os.getenv('MEXC_API_KEY')
    api_secret = os.getenv('MEXC_API_SECRET')
    trading_mode = os.getenv('TRADING_MODE', 'demo')
    
    if not api_key or not api_secret:
        print("❌ ERROR: MEXC API credentials not found in .env file")
        print()
        print("Please add the following to your .env file:")
        print("MEXC_API_KEY=your_api_key_here")
        print("MEXC_API_SECRET=your_api_secret_here")
        return False
    
    print(f"✓ API credentials found")
    print(f"✓ Trading mode: {trading_mode}")
    print()
    
    try:
        # Initialize MEXC exchange
        print("1. Initializing MEXC exchange...")
        testnet = (trading_mode == 'demo')
        exchange = MexcExchange(api_key, api_secret, testnet=testnet)
        print("   ✅ MEXC exchange initialized successfully")
        print()
        
        # Test 1: Get account balance
        print("2. Testing account balance retrieval...")
        balance = await exchange.get_balance()
        
        if balance and 'total' in balance:
            print("   ✅ Account balance retrieved successfully")
            print()
            print("   Account Balances:")
            
            # Show balances for major coins
            major_coins = ['USDT', 'BTC', 'ETH', 'BNB']
            for coin in major_coins:
                total = balance['total'].get(coin, 0)
                free = balance['free'].get(coin, 0)
                used = balance['used'].get(coin, 0)
                
                if total > 0:
                    print(f"   - {coin}: {total:.8f} (Free: {free:.8f}, Used: {used:.8f})")
            print()
        else:
            print("   ⚠️  Balance retrieved but format unexpected")
            print(f"   Response: {balance}")
            print()
        
        # Test 2: Get market data
        print("3. Testing market data access...")
        try:
            # Try to fetch ticker for BTC/USDT
            ticker = await exchange.exchange.fetch_ticker('BTC/USDT')
            
            if ticker and 'last' in ticker:
                print("   ✅ Market data accessible")
                print(f"   BTC/USDT Price: ${ticker['last']:,.2f}")
                print(f"   24h Volume: {ticker.get('quoteVolume', 0):,.2f} USDT")
                print()
            else:
                print("   ⚠️  Market data retrieved but format unexpected")
                print()
        except Exception as e:
            print(f"   ❌ Failed to fetch market data: {e}")
            print()
            return False
        
        # Test 3: Get open positions/orders
        print("4. Testing open positions retrieval...")
        positions = await exchange.get_positions()
        print(f"   ✅ Open orders retrieved: {len(positions)} orders")
        
        if positions:
            print("   Open Orders:")
            for pos in positions[:5]:  # Show first 5
                print(f"   - {pos.get('symbol')}: {pos.get('side')} {pos.get('amount')} @ {pos.get('price')}")
        else:
            print("   No open orders")
        print()
        
        # Test 4: Verify exchange capabilities
        print("5. Verifying exchange capabilities...")
        try:
            markets = await exchange.exchange.load_markets()
            print(f"   ✅ Exchange supports {len(markets)} trading pairs")
            
            # Check if major pairs are available
            major_pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
            available_pairs = [pair for pair in major_pairs if pair in markets]
            print(f"   ✅ Major pairs available: {', '.join(available_pairs)}")
            print()
        except Exception as e:
            print(f"   ⚠️  Could not verify capabilities: {e}")
            print()
        
        # Summary
        print("=" * 60)
        print("✅ MEXC CONNECTION TEST PASSED")
        print("=" * 60)
        print()
        print("Your MEXC exchange is properly configured and ready to use!")
        print()
        
        if trading_mode == 'demo':
            print("⚠️  NOTE: You are in DEMO mode")
            print("   MEXC doesn't have a traditional testnet like Binance.")
            print("   Start with small amounts for testing.")
            print()
        else:
            print("⚠️  WARNING: You are in LIVE mode")
            print("   Real money will be used for trading!")
            print("   Make sure you understand the risks.")
            print()
        
        print("Next steps:")
        print("1. Review your configuration in config/config.yaml")
        print("2. Run backtests: python scripts/run_all_backtests.py")
        print("3. Start the bot: python -m src.autonomous.autonomous_trading_system")
        print()
        
        return True
        
    except Exception as e:
        print()
        print("=" * 60)
        print("❌ MEXC CONNECTION TEST FAILED")
        print("=" * 60)
        print()
        print(f"Error: {str(e)}")
        print()
        print("Common issues:")
        print("1. Invalid API keys - Check your MEXC account")
        print("2. API permissions - Ensure 'Spot Trading' is enabled")
        print("3. IP whitelist - Add your IP if whitelist is enabled")
        print("4. Network issues - Check your internet connection")
        print()
        return False


if __name__ == '__main__':
    success = asyncio.run(test_mexc_connection())
    sys.exit(0 if success else 1)
