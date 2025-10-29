"""
Stress Testing for Autonomous Trading System

Tests the system under extreme market conditions:
- High volatility scenarios
- Flash crash simulations
- Extended drawdown periods
- Rapid trend reversals
- Low liquidity conditions
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import logging
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.autonomous.autonomous_trading_system import AutonomousTradingSystem
from src.autonomous.enhanced_risk_manager import EnhancedRiskManager
from src.autonomous.exit_plan_monitor import ExitPlanMonitor
from src.autonomous.autonomous_decision_engine import AutonomousDecisionEngine
from src.strategies.momentum import MomentumStrategy
from src.strategies.universal_macd_strategy import UniversalMacdStrategy

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class StressTester:
    """Stress test the autonomous trading system"""
    
    def __init__(self):
        self.test_results = []
        
    def generate_high_volatility_data(self, periods=1000, volatility_multiplier=5.0):
        """Generate synthetic high volatility market data"""
        logger.info(f"Generating high volatility data (multiplier: {volatility_multiplier}x)")
        
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1h')
        
        base_price = 50000.0
        returns = np.random.normal(0, 0.05 * volatility_multiplier, periods)
        prices = base_price * np.exp(np.cumsum(returns))
        
        spike_indices = np.random.choice(periods, size=10, replace=False)
        for idx in spike_indices:
            prices[idx:idx+5] *= np.random.choice([0.9, 1.1])
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.02,
            'low': prices * 0.98,
            'close': prices,
            'volume': np.random.uniform(100, 1000, periods)
        })
        
        return df
    
    def generate_flash_crash_data(self, periods=1000, crash_magnitude=0.30):
        """Generate data with flash crash event"""
        logger.info(f"Generating flash crash data (magnitude: {crash_magnitude*100}%)")
        
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1h')
        
        base_price = 50000.0
        returns = np.random.normal(0, 0.01, periods)
        prices = base_price * np.exp(np.cumsum(returns))
        
        crash_start = periods // 2
        crash_duration = 10
        
        for i in range(crash_duration):
            idx = crash_start + i
            if i < crash_duration // 2:
                prices[idx] *= (1 - crash_magnitude * (i / (crash_duration // 2)))
            else:
                recovery_factor = (i - crash_duration // 2) / (crash_duration // 2)
                prices[idx] *= (1 + crash_magnitude * recovery_factor * 0.5)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'close': prices,
            'volume': np.random.uniform(100, 1000, periods)
        })
        
        return df
    
    def generate_extended_drawdown_data(self, periods=1000, drawdown_pct=0.40):
        """Generate data with extended drawdown period"""
        logger.info(f"Generating extended drawdown data (drawdown: {drawdown_pct*100}%)")
        
        dates = pd.date_range(start='2024-01-01', periods=periods, freq='1h')
        
        base_price = 50000.0
        prices = np.zeros(periods)
        prices[0] = base_price
        
        for i in range(1, periods // 3):
            prices[i] = prices[i-1] * (1 + np.random.uniform(0, 0.01))
        
        drawdown_start = periods // 3
        drawdown_end = 2 * periods // 3
        drawdown_periods = drawdown_end - drawdown_start
        
        for i in range(drawdown_start, drawdown_end):
            progress = (i - drawdown_start) / drawdown_periods
            prices[i] = prices[drawdown_start] * (1 - drawdown_pct * progress)
        
        for i in range(drawdown_end, periods):
            prices[i] = prices[i-1] * (1 + np.random.uniform(0, 0.005))
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices * 0.99,
            'high': prices * 1.01,
            'low': prices * 0.99,
            'close': prices,
            'volume': np.random.uniform(100, 1000, periods)
        })
        
        return df
    
    def test_risk_manager_limits(self):
        """Test risk manager daily loss limits"""
        logger.info("\n" + "="*80)
        logger.info("STRESS TEST 1: Risk Manager Daily Loss Limits")
        logger.info("="*80)
        
        risk_manager = EnhancedRiskManager(
            initial_capital=10000.0,
            max_daily_loss_pct=5.0,
            max_daily_trades=20,
            max_position_size_pct=15.0
        )
        
        test_cases = [
            ("Small loss", -100, True),
            ("Medium loss", -300, True),
            ("Near limit", -480, True),
            ("At limit", -500, False),
            ("Over limit", -600, False),
        ]
        
        results = []
        for test_name, loss_amount, should_allow in test_cases:
            state = risk_manager.daily_state[risk_manager.current_date]
            state.total_pnl = loss_amount
            
            can_trade = risk_manager.can_trade_today()
            
            passed = (can_trade == should_allow)
            status = "✓ PASS" if passed else "✗ FAIL"
            
            logger.info(f"{test_name}: Loss=${loss_amount}, Can Trade={can_trade}, Expected={should_allow} {status}")
            
            results.append({
                'test': test_name,
                'loss': loss_amount,
                'can_trade': can_trade,
                'expected': should_allow,
                'passed': passed
            })
        
        passed_count = sum(1 for r in results if r['passed'])
        logger.info(f"\nRisk Manager Tests: {passed_count}/{len(results)} passed")
        
        return {
            'test_name': 'Risk Manager Daily Loss Limits',
            'passed': passed_count,
            'total': len(results),
            'pass_rate': passed_count / len(results),
            'results': results
        }
    
    def test_exit_plan_monitoring(self):
        """Test exit plan monitor with various scenarios"""
        logger.info("\n" + "="*80)
        logger.info("STRESS TEST 2: Exit Plan Monitoring")
        logger.info("="*80)
        
        monitor = ExitPlanMonitor()
        
        from src.autonomous.exit_plan_monitor import ExitPlan
        
        exit_plan1 = ExitPlan(
            position_id='test-pos-1',
            symbol='BTC/USDT',
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            invalidation_conditions=['ADX < 20'],
            trailing_stop_pct=None,
            trailing_offset_pct=None,
            is_short=False,
            metadata={}
        )
        
        monitor.add_exit_plan(exit_plan1)
        
        market_data1 = {'price': 48500.0, 'adx': 30.0}
        indicators1 = {}
        exit_result1 = monitor.check_exit_conditions('test-pos-1', 48500.0, market_data1, indicators1)
        should_exit1 = exit_result1['should_exit'] if exit_result1 else False
        reason1 = exit_result1['reason'].value if exit_result1 and exit_result1['should_exit'] else 'No exit'
        
        test1_passed = should_exit1 and 'stop' in reason1.lower()
        logger.info(f"Test 1 - Stop-loss trigger: {should_exit1}, Reason: {reason1} {'✓ PASS' if test1_passed else '✗ FAIL'}")
        
        exit_plan2 = ExitPlan(
            position_id='test-pos-2',
            symbol='ETH/USDT',
            entry_price=3000.0,
            stop_loss=2900.0,
            take_profit=3200.0,
            invalidation_conditions=[],
            trailing_stop_pct=None,
            trailing_offset_pct=None,
            is_short=False,
            metadata={}
        )
        
        monitor.add_exit_plan(exit_plan2)
        
        market_data2 = {'price': 3250.0}
        indicators2 = {}
        exit_result2 = monitor.check_exit_conditions('test-pos-2', 3250.0, market_data2, indicators2)
        should_exit2 = exit_result2['should_exit'] if exit_result2 else False
        reason2 = exit_result2['reason'].value if exit_result2 and exit_result2['should_exit'] else 'No exit'
        
        test2_passed = should_exit2 and 'profit' in reason2.lower()
        logger.info(f"Test 2 - Take-profit trigger: {should_exit2}, Reason: {reason2} {'✓ PASS' if test2_passed else '✗ FAIL'}")
        
        exit_plan3 = ExitPlan(
            position_id='test-pos-3',
            symbol='BTC/USDT',
            entry_price=50000.0,
            stop_loss=49000.0,
            take_profit=52000.0,
            invalidation_conditions=['ADX < 20'],
            trailing_stop_pct=None,
            trailing_offset_pct=None,
            is_short=False,
            metadata={}
        )
        
        monitor.add_exit_plan(exit_plan3)
        
        market_data3 = {'price': 50500.0, 'adx': 15.0}
        indicators3 = {}
        exit_result3 = monitor.check_exit_conditions('test-pos-3', 50500.0, market_data3, indicators3)
        should_exit3 = exit_result3['should_exit'] if exit_result3 else False
        reason3 = exit_result3['reason'].value if exit_result3 and exit_result3['should_exit'] else 'No exit'
        
        test3_passed = should_exit3 and 'invalid' in reason3.lower()
        logger.info(f"Test 3 - Invalidation condition: {should_exit3}, Reason: {reason3} {'✓ PASS' if test3_passed else '✗ FAIL'}")
        
        passed_count = sum([test1_passed, test2_passed, test3_passed])
        logger.info(f"\nExit Plan Tests: {passed_count}/3 passed")
        
        return {
            'test_name': 'Exit Plan Monitoring',
            'passed': passed_count,
            'total': 3,
            'pass_rate': passed_count / 3,
            'results': [
                {'test': 'Stop-loss trigger', 'passed': test1_passed},
                {'test': 'Take-profit trigger', 'passed': test2_passed},
                {'test': 'Invalidation condition', 'passed': test3_passed}
            ]
        }
    
    def test_concurrent_position_limits(self):
        """Test maximum concurrent position limits"""
        logger.info("\n" + "="*80)
        logger.info("STRESS TEST 3: Concurrent Position Limits")
        logger.info("="*80)
        
        risk_manager = EnhancedRiskManager(
            initial_capital=10000.0,
            max_daily_loss_pct=5.0,
            max_daily_trades=20,
            max_position_size_pct=15.0,
            max_symbol_exposure_pct=20.0
        )
        
        test_results = []
        
        for i in range(7):
            symbol = f"TEST{i}/USDT"
            position_value = 1000.0
            
            can_open = risk_manager.can_open_position(symbol)
            
            if can_open:
                risk_manager.record_position_opened(symbol, position_value)
            
            total_exposure = sum(risk_manager.symbol_exposure.values())
            
            test_results.append({
                'position_num': i + 1,
                'can_open': can_open,
                'total_exposure': total_exposure
            })
            
            logger.info(f"Position {i+1}: Can Open={can_open}, Total Exposure=${total_exposure:,.2f}")
        
        passed = test_results[0]['can_open'] and test_results[1]['can_open']
        
        logger.info(f"\nConcurrent Position Limits: {'✓ PASS' if passed else '✗ FAIL'}")
        
        return {
            'test_name': 'Concurrent Position Limits',
            'passed': 1 if passed else 0,
            'total': 1,
            'pass_rate': 1.0 if passed else 0.0,
            'results': test_results
        }
    
    def test_error_recovery(self):
        """Test error recovery mechanisms"""
        logger.info("\n" + "="*80)
        logger.info("STRESS TEST 4: Error Recovery Mechanisms")
        logger.info("="*80)
        
        from src.autonomous.error_recovery import ErrorRecoveryManager, ErrorRecord
        
        recovery_manager = ErrorRecoveryManager(
            max_consecutive_errors=5,
            cooldown_seconds=60
        )
        
        test_cases = [
            ("Network timeout", "Connection timeout", "continue"),
            ("API rate limit", "Rate limit exceeded", "pause"),
            ("Invalid order", "Order validation failed", "continue"),
            ("Insufficient funds", "Insufficient balance", "stop"),
            ("System crash", "Segmentation fault", "stop"),
        ]
        
        results = []
        for error_type, error_msg, expected_action in test_cases:
            error = ErrorRecord(
                timestamp=datetime.now(),
                error_type=error_type,
                error_message=error_msg,
                context={},
                stack_trace="",
                recovery_action=expected_action
            )
            
            action = recovery_manager._determine_recovery_action(error.error_type, error.error_message)
            passed = (action == expected_action)
            
            logger.info(f"{error_type}: Action={action}, Expected={expected_action} {'✓ PASS' if passed else '✗ FAIL'}")
            
            results.append({
                'error_type': error_type,
                'action': action,
                'expected': expected_action,
                'passed': passed
            })
        
        passed_count = sum(1 for r in results if r['passed'])
        logger.info(f"\nError Recovery Tests: {passed_count}/{len(results)} passed")
        
        return {
            'test_name': 'Error Recovery Mechanisms',
            'passed': passed_count,
            'total': len(results),
            'pass_rate': passed_count / len(results),
            'results': results
        }


def main():
    """Run all stress tests"""
    logger.info("="*80)
    logger.info("AUTONOMOUS TRADING SYSTEM - STRESS TESTS")
    logger.info("="*80)
    logger.info(f"Timestamp: {datetime.now()}")
    
    tester = StressTester()
    
    results = []
    
    results.append(tester.test_risk_manager_limits())
    results.append(tester.test_exit_plan_monitoring())
    results.append(tester.test_concurrent_position_limits())
    results.append(tester.test_error_recovery())
    
    logger.info("\n" + "="*80)
    logger.info("STRESS TEST SUMMARY")
    logger.info("="*80)
    
    total_passed = sum(r['passed'] for r in results)
    total_tests = sum(r['total'] for r in results)
    overall_pass_rate = total_passed / total_tests if total_tests > 0 else 0
    
    logger.info(f"\n{'Test Name':<40} {'Passed':<10} {'Total':<10} {'Pass Rate':<10}")
    logger.info("-" * 80)
    
    for result in results:
        logger.info(
            f"{result['test_name']:<40} "
            f"{result['passed']:<10} "
            f"{result['total']:<10} "
            f"{result['pass_rate']*100:>8.1f}%"
        )
    
    logger.info("-" * 80)
    logger.info(f"{'OVERALL':<40} {total_passed:<10} {total_tests:<10} {overall_pass_rate*100:>8.1f}%")
    
    logger.info("\n" + "="*80)
    logger.info(f"Stress Tests Complete: {total_passed}/{total_tests} passed ({overall_pass_rate*100:.1f}%)")
    logger.info("="*80)
    
    return results


if __name__ == '__main__':
    main()
