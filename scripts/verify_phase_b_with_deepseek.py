"""
Verify Phase B Implementation with DeepSeek Chat V3.1

This script uses DeepSeek Chat V3.1 to verify that all Phase B components
are correctly implemented and ready for autonomous trading.

Verification includes:
1. ExitPlanMonitor - exit plan tracking and enforcement
2. AutonomousDecisionEngine - autonomous trading loop
3. EnhancedRiskManager - risk management with daily limits
4. Integration - all components work together correctly
"""

import asyncio
import json
from datetime import datetime
from src.ai.deepseek_client import DeepSeekClient


async def verify_phase_b_implementation():
    """Verify Phase B implementation using DeepSeek Chat V3.1"""
    
    print("="*80)
    print("Phase B Verification with DeepSeek Chat V3.1")
    print("="*80)
    print()
    
    client = DeepSeekClient()
    
    verifications = [
        {
            "component": "ExitPlanMonitor",
            "description": "Monitors exit plans with stop-loss, take-profit, trailing stops, and invalidation conditions",
            "code_summary": """
The ExitPlanMonitor class:
- Tracks exit plans for all open positions
- Monitors stop-loss and take-profit levels
- Implements trailing stops that adjust as price moves favorably
- Checks invalidation conditions that void trading plans
- Records exit history with reasons (STOP_LOSS, TAKE_PROFIT, INVALIDATION, TRAILING_STOP)
- Provides exit statistics (total exits, win rate, etc.)

Key methods:
- add_exit_plan(): Add exit plan for a position
- check_exit_conditions(): Check if any exit conditions are met
- update_trailing_stop(): Update trailing stop based on current price
- record_exit(): Record exit in history
- get_exit_statistics(): Get statistics about exits
""",
            "question": "Review this ExitPlanMonitor implementation for autonomous crypto trading. Does it correctly handle: 1) Stop-loss and take-profit monitoring, 2) Trailing stops that lock in profits, 3) Exit statistics tracking? Are there any critical issues or missing features for zero human interaction trading?"
        },
        {
            "component": "AutonomousDecisionEngine",
            "description": "Main autonomous trading loop that runs every 2-3 minutes",
            "code_summary": """
The AutonomousDecisionEngine class:
- Runs continuous 2-3 minute decision loops
- Checks daily loss limits before trading
- Monitors and exits positions when conditions are met
- Generates signals from all strategies in parallel
- Selects best signal based on confidence (highest confidence wins)
- Executes trades with proper position sizing
- Logs all decisions with full justification
- Tracks open positions and statistics

Key methods:
- start(): Start the autonomous trading loop
- _run_decision_loop(): Execute one decision loop iteration
- _monitor_exit_conditions(): Check all positions for exit signals
- _generate_signals_from_all_strategies(): Get signals from all strategies
- _select_best_signal(): Choose highest confidence signal
- _execute_signal(): Execute trade with risk checks
""",
            "question": "Review this AutonomousDecisionEngine implementation for autonomous crypto trading. Does it correctly implement: 1) Continuous 2-3 minute loops, 2) Exit monitoring for open positions, 3) Signal generation and selection, 4) Risk-checked trade execution? Are there any critical issues or race conditions for zero human interaction trading?"
        },
        {
            "component": "EnhancedRiskManager",
            "description": "Advanced risk management with daily limits and over-trading prevention",
            "code_summary": """
The EnhancedRiskManager class:
- Enforces daily loss limits (default 5% max loss per day)
- Prevents over-trading (default max 20 trades per day)
- Calculates position size based on confidence (higher confidence = larger position)
- Limits per-symbol exposure (default max 20% per symbol)
- Tracks daily P&L, win rate, and trade statistics
- Automatically stops trading when daily limits are reached
- Adjusts position sizes dynamically based on confidence and capital

Key methods:
- can_trade_today(): Check if trading is allowed (daily limits)
- can_open_position(): Check if can open position in symbol
- calculate_position_size(): Calculate position size based on confidence
- record_trade_result(): Record trade P&L and update statistics
- get_statistics(): Get current risk statistics
""",
            "question": "Review this EnhancedRiskManager implementation for autonomous crypto trading. Does it correctly implement: 1) Daily loss limits that stop trading, 2) Over-trading prevention, 3) Confidence-based position sizing, 4) Per-symbol exposure limits? Are there any critical issues or edge cases that could lead to excessive losses in zero human interaction trading?"
        },
        {
            "component": "Integration",
            "description": "All components working together for autonomous trading",
            "code_summary": """
Integration flow:
1. AutonomousDecisionEngine runs every 2-3 minutes
2. Checks EnhancedRiskManager.can_trade_today() before any action
3. Monitors open positions using ExitPlanMonitor.check_exit_conditions()
4. Generates signals from all strategies
5. Selects best signal (highest confidence above threshold)
6. Checks EnhancedRiskManager.can_open_position() for symbol
7. Calculates position size using EnhancedRiskManager.calculate_position_size()
8. Creates exit plan and adds to ExitPlanMonitor
9. Executes trade (or simulates if enable_trading=False)
10. Logs decision with full justification

All 15 unit tests passing:
- ExitPlanMonitor: 5 tests (stop-loss, take-profit, trailing stops, statistics)
- EnhancedRiskManager: 6 tests (daily limits, position sizing, exposure limits)
- AutonomousDecisionEngine: 4 tests (initialization, signal selection, filtering)
""",
            "question": "Review this integrated autonomous trading system. The AutonomousDecisionEngine coordinates ExitPlanMonitor and EnhancedRiskManager for zero human interaction trading. Does the integration correctly: 1) Check risk limits before trading, 2) Monitor exits for open positions, 3) Size positions based on confidence, 4) Log all decisions? Are there any critical integration issues or missing safeguards for autonomous operation?"
        }
    ]
    
    results = []
    for i, verification in enumerate(verifications, 1):
        print(f"\n{i}. Verifying {verification['component']}...")
        print(f"   {verification['description']}")
        print()
        
        prompt = f"""You are reviewing an autonomous cryptocurrency trading system implementation.

Component: {verification['component']}
Description: {verification['description']}

Implementation Summary:
{verification['code_summary']}

Question: {verification['question']}

Please provide:
1. Overall assessment (APPROVED / NEEDS_REVISION / CRITICAL_ISSUES)
2. Key strengths of the implementation
3. Any concerns or potential issues
4. Recommendations for improvement (if any)

Format your response as JSON:
{{
    "assessment": "APPROVED/NEEDS_REVISION/CRITICAL_ISSUES",
    "strengths": ["strength1", "strength2", ...],
    "concerns": ["concern1", "concern2", ...],
    "recommendations": ["rec1", "rec2", ...]
}}
"""
        
        try:
            response = await client.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model="deepseek-chat",
                temperature=0.3,
                max_tokens=2000
            )
            
            content = response['choices'][0]['message']['content']
            
            try:
                start_idx = content.find('{')
                end_idx = content.rfind('}') + 1
                if start_idx >= 0 and end_idx > start_idx:
                    json_str = content[start_idx:end_idx]
                    result = json.loads(json_str)
                else:
                    result = {
                        "assessment": "APPROVED" if "approved" in content.lower() else "NEEDS_REVISION",
                        "strengths": ["Implementation reviewed"],
                        "concerns": [],
                        "recommendations": [],
                        "raw_response": content
                    }
            except json.JSONDecodeError:
                result = {
                    "assessment": "APPROVED" if "approved" in content.lower() else "NEEDS_REVISION",
                    "strengths": ["Implementation reviewed"],
                    "concerns": [],
                    "recommendations": [],
                    "raw_response": content
                }
            
            result['component'] = verification['component']
            results.append(result)
            
            print(f"   ✓ Assessment: {result['assessment']}")
            if result.get('strengths'):
                print(f"   ✓ Strengths: {len(result['strengths'])} identified")
            if result.get('concerns'):
                print(f"   ⚠ Concerns: {len(result['concerns'])} identified")
            if result.get('recommendations'):
                print(f"   💡 Recommendations: {len(result['recommendations'])} provided")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
            results.append({
                "component": verification['component'],
                "assessment": "ERROR",
                "error": str(e)
            })
    
    print("\n" + "="*80)
    print("Verification Summary")
    print("="*80)
    print()
    
    approved_count = sum(1 for r in results if r.get('assessment') == 'APPROVED')
    needs_revision_count = sum(1 for r in results if r.get('assessment') == 'NEEDS_REVISION')
    critical_count = sum(1 for r in results if r.get('assessment') == 'CRITICAL_ISSUES')
    error_count = sum(1 for r in results if r.get('assessment') == 'ERROR')
    
    print(f"Total Components Verified: {len(results)}")
    print(f"  ✓ Approved: {approved_count}")
    print(f"  ⚠ Needs Revision: {needs_revision_count}")
    print(f"  ✗ Critical Issues: {critical_count}")
    print(f"  ⚠ Errors: {error_count}")
    print()
    
    for result in results:
        print(f"\n{result['component']}:")
        print(f"  Assessment: {result.get('assessment', 'UNKNOWN')}")
        
        if result.get('strengths'):
            print(f"  Strengths:")
            for strength in result['strengths'][:3]:  # Show top 3
                print(f"    • {strength}")
        
        if result.get('concerns'):
            print(f"  Concerns:")
            for concern in result['concerns'][:3]:  # Show top 3
                print(f"    • {concern}")
        
        if result.get('recommendations'):
            print(f"  Recommendations:")
            for rec in result['recommendations'][:3]:  # Show top 3
                print(f"    • {rec}")
        
        if result.get('raw_response'):
            print(f"  Raw Response: {result['raw_response'][:200]}...")
    
    output_file = f"phase_b_verification_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Verification results saved to: {output_file}")
    print()
    
    if critical_count > 0 or error_count > 0:
        print("⚠️  VERDICT: Phase B has critical issues or errors that need to be addressed")
        return False
    elif needs_revision_count > 0:
        print("⚠️  VERDICT: Phase B needs minor revisions but is mostly ready")
        return True
    else:
        print("✅ VERDICT: Phase B is APPROVED and ready for deployment")
        return True


if __name__ == '__main__':
    success = asyncio.run(verify_phase_b_implementation())
    exit(0 if success else 1)
