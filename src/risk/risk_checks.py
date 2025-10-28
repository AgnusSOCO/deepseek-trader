"""
Risk Checks

Pre-trade validation checks to ensure trades comply with risk management rules.
Validates account balance, position size, stop-loss, exposure limits, and more.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from loguru import logger


@dataclass
class RiskCheckResult:
    """Result of a risk check"""
    passed: bool
    check_name: str
    message: str
    severity: str = "ERROR"  # ERROR, WARNING, INFO


class RiskValidator:
    """
    Validates trades against risk management rules
    
    Performs comprehensive pre-trade checks:
    - Account balance verification
    - Position size validation
    - Stop-loss presence and distance
    - Risk-reward ratio check
    - Exposure limits (single asset, strategy, total)
    - Leverage limits
    - Drawdown state check
    - Fat finger detection
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize risk validator
        
        Args:
            config: Risk management configuration
        """
        self.config = config
        
        self.max_position_risk_pct = config.get('max_position_risk_pct', 0.02)  # 2%
        self.min_risk_reward_ratio = config.get('min_risk_reward_ratio', 1.5)
        self.max_single_asset_exposure = config.get('max_single_asset_exposure', 0.3)  # 30%
        self.max_strategy_exposure = config.get('max_strategy_exposure', 0.4)  # 40%
        self.max_total_exposure = config.get('max_total_exposure', 0.8)  # 80%
        self.max_leverage = config.get('max_leverage', 10.0)
        self.max_daily_drawdown_pct = config.get('max_daily_drawdown_pct', 0.05)  # 5%
        self.max_total_drawdown_pct = config.get('max_total_drawdown_pct', 0.15)  # 15%
        self.fat_finger_threshold = config.get('fat_finger_threshold', 0.5)  # 50% of account
        self.require_stop_loss = config.get('require_stop_loss', True)
        self.min_stop_loss_distance_pct = config.get('min_stop_loss_distance_pct', 0.005)  # 0.5%
        self.max_stop_loss_distance_pct = config.get('max_stop_loss_distance_pct', 0.1)  # 10%
        
    def validate_trade(self,
                      trade_params: Dict[str, Any],
                      account_balance: float,
                      current_positions: List[Dict[str, Any]],
                      portfolio_state: Dict[str, Any]) -> tuple[bool, List[RiskCheckResult]]:
        """
        Validate a trade against all risk checks
        
        Args:
            trade_params: Trade parameters (symbol, side, quantity, price, etc.)
            account_balance: Current account balance
            current_positions: List of current open positions
            portfolio_state: Current portfolio state (drawdown, exposure, etc.)
            
        Returns:
            Tuple of (passed: bool, results: List[RiskCheckResult])
        """
        results = []
        
        results.append(self._check_account_balance(trade_params, account_balance))
        results.append(self._check_position_size(trade_params, account_balance))
        results.append(self._check_stop_loss(trade_params))
        results.append(self._check_risk_reward_ratio(trade_params))
        results.append(self._check_exposure_limits(trade_params, account_balance, current_positions))
        results.append(self._check_leverage_limits(trade_params))
        results.append(self._check_drawdown_state(portfolio_state))
        results.append(self._check_fat_finger(trade_params, account_balance))
        
        critical_failures = [r for r in results if not r.passed and r.severity == "ERROR"]
        passed = len(critical_failures) == 0
        
        if not passed:
            logger.warning(f"Trade validation failed: {len(critical_failures)} critical issues")
            for result in critical_failures:
                logger.warning(f"  - {result.check_name}: {result.message}")
        else:
            warnings = [r for r in results if not r.passed and r.severity == "WARNING"]
            if warnings:
                logger.info(f"Trade validation passed with {len(warnings)} warnings")
                for result in warnings:
                    logger.info(f"  - {result.check_name}: {result.message}")
        
        return passed, results
    
    def _check_account_balance(self, trade_params: Dict[str, Any], account_balance: float) -> RiskCheckResult:
        """Check if account has sufficient balance for the trade"""
        quantity = trade_params.get('quantity', 0)
        price = trade_params.get('price', 0)
        leverage = trade_params.get('leverage', 1.0)
        
        position_value = quantity * price
        required_margin = position_value / leverage if leverage > 1 else position_value
        
        required_margin *= 1.001
        
        if required_margin > account_balance:
            return RiskCheckResult(
                passed=False,
                check_name="account_balance",
                message=f"Insufficient balance: need {required_margin:.2f}, have {account_balance:.2f}",
                severity="ERROR"
            )
        
        return RiskCheckResult(
            passed=True,
            check_name="account_balance",
            message=f"Sufficient balance: {account_balance:.2f} >= {required_margin:.2f}",
            severity="INFO"
        )
    
    def _check_position_size(self, trade_params: Dict[str, Any], account_balance: float) -> RiskCheckResult:
        """Check if position size is within limits"""
        quantity = trade_params.get('quantity', 0)
        price = trade_params.get('price', 0)
        
        position_value = quantity * price
        position_pct = position_value / account_balance if account_balance > 0 else 0
        
        if position_pct > self.max_position_risk_pct * 10:  # 10x the per-trade risk
            return RiskCheckResult(
                passed=False,
                check_name="position_size",
                message=f"Position size too large: {position_pct*100:.1f}% of account",
                severity="ERROR"
            )
        
        return RiskCheckResult(
            passed=True,
            check_name="position_size",
            message=f"Position size acceptable: {position_pct*100:.1f}% of account",
            severity="INFO"
        )
    
    def _check_stop_loss(self, trade_params: Dict[str, Any]) -> RiskCheckResult:
        """Check stop-loss presence and distance"""
        stop_loss = trade_params.get('stop_loss')
        price = trade_params.get('price', 0)
        side = trade_params.get('side', '').upper()
        
        if self.require_stop_loss and stop_loss is None:
            return RiskCheckResult(
                passed=False,
                check_name="stop_loss",
                message="Stop-loss is required but not provided",
                severity="ERROR"
            )
        
        if stop_loss is not None and price > 0:
            stop_distance_pct = abs(price - stop_loss) / price
            
            if stop_distance_pct < self.min_stop_loss_distance_pct:
                return RiskCheckResult(
                    passed=False,
                    check_name="stop_loss",
                    message=f"Stop-loss too tight: {stop_distance_pct*100:.2f}% (min: {self.min_stop_loss_distance_pct*100:.2f}%)",
                    severity="WARNING"
                )
            
            if stop_distance_pct > self.max_stop_loss_distance_pct:
                return RiskCheckResult(
                    passed=False,
                    check_name="stop_loss",
                    message=f"Stop-loss too wide: {stop_distance_pct*100:.2f}% (max: {self.max_stop_loss_distance_pct*100:.2f}%)",
                    severity="WARNING"
                )
            
            if side == 'BUY' and stop_loss >= price:
                return RiskCheckResult(
                    passed=False,
                    check_name="stop_loss",
                    message=f"Stop-loss must be below entry for BUY orders",
                    severity="ERROR"
                )
            elif side == 'SELL' and stop_loss <= price:
                return RiskCheckResult(
                    passed=False,
                    check_name="stop_loss",
                    message=f"Stop-loss must be above entry for SELL orders",
                    severity="ERROR"
                )
        
        return RiskCheckResult(
            passed=True,
            check_name="stop_loss",
            message="Stop-loss validation passed",
            severity="INFO"
        )
    
    def _check_risk_reward_ratio(self, trade_params: Dict[str, Any]) -> RiskCheckResult:
        """Check risk-reward ratio"""
        stop_loss = trade_params.get('stop_loss')
        take_profit = trade_params.get('take_profit')
        price = trade_params.get('price', 0)
        
        if stop_loss is None or take_profit is None or price == 0:
            return RiskCheckResult(
                passed=True,
                check_name="risk_reward_ratio",
                message="Risk-reward ratio not applicable (missing stop-loss or take-profit)",
                severity="INFO"
            )
        
        risk = abs(price - stop_loss)
        reward = abs(take_profit - price)
        
        if risk == 0:
            return RiskCheckResult(
                passed=False,
                check_name="risk_reward_ratio",
                message="Invalid risk-reward ratio (risk is zero)",
                severity="ERROR"
            )
        
        ratio = reward / risk
        
        if ratio < self.min_risk_reward_ratio:
            return RiskCheckResult(
                passed=False,
                check_name="risk_reward_ratio",
                message=f"Risk-reward ratio too low: {ratio:.2f} (min: {self.min_risk_reward_ratio:.2f})",
                severity="WARNING"
            )
        
        return RiskCheckResult(
            passed=True,
            check_name="risk_reward_ratio",
            message=f"Risk-reward ratio acceptable: {ratio:.2f}",
            severity="INFO"
        )
    
    def _check_exposure_limits(self,
                               trade_params: Dict[str, Any],
                               account_balance: float,
                               current_positions: List[Dict[str, Any]]) -> RiskCheckResult:
        """Check exposure limits (single asset, strategy, total)"""
        symbol = trade_params.get('symbol', '')
        quantity = trade_params.get('quantity', 0)
        price = trade_params.get('price', 0)
        strategy = trade_params.get('strategy', 'unknown')
        
        new_position_value = quantity * price
        
        total_exposure = 0
        symbol_exposure = 0
        strategy_exposure = 0
        
        for pos in current_positions:
            pos_value = pos.get('quantity', 0) * pos.get('price', 0)
            total_exposure += pos_value
            
            if pos.get('symbol') == symbol:
                symbol_exposure += pos_value
            
            if pos.get('strategy') == strategy:
                strategy_exposure += pos_value
        
        total_exposure += new_position_value
        symbol_exposure += new_position_value
        strategy_exposure += new_position_value
        
        total_exposure_pct = total_exposure / account_balance if account_balance > 0 else 0
        symbol_exposure_pct = symbol_exposure / account_balance if account_balance > 0 else 0
        strategy_exposure_pct = strategy_exposure / account_balance if account_balance > 0 else 0
        
        if symbol_exposure_pct > self.max_single_asset_exposure:
            return RiskCheckResult(
                passed=False,
                check_name="exposure_limits",
                message=f"Single asset exposure too high: {symbol_exposure_pct*100:.1f}% (max: {self.max_single_asset_exposure*100:.1f}%)",
                severity="ERROR"
            )
        
        if strategy_exposure_pct > self.max_strategy_exposure:
            return RiskCheckResult(
                passed=False,
                check_name="exposure_limits",
                message=f"Strategy exposure too high: {strategy_exposure_pct*100:.1f}% (max: {self.max_strategy_exposure*100:.1f}%)",
                severity="WARNING"
            )
        
        if total_exposure_pct > self.max_total_exposure:
            return RiskCheckResult(
                passed=False,
                check_name="exposure_limits",
                message=f"Total exposure too high: {total_exposure_pct*100:.1f}% (max: {self.max_total_exposure*100:.1f}%)",
                severity="ERROR"
            )
        
        return RiskCheckResult(
            passed=True,
            check_name="exposure_limits",
            message=f"Exposure within limits (total: {total_exposure_pct*100:.1f}%, asset: {symbol_exposure_pct*100:.1f}%)",
            severity="INFO"
        )
    
    def _check_leverage_limits(self, trade_params: Dict[str, Any]) -> RiskCheckResult:
        """Check leverage limits"""
        leverage = trade_params.get('leverage', 1.0)
        
        if leverage > self.max_leverage:
            return RiskCheckResult(
                passed=False,
                check_name="leverage_limits",
                message=f"Leverage too high: {leverage}x (max: {self.max_leverage}x)",
                severity="ERROR"
            )
        
        return RiskCheckResult(
            passed=True,
            check_name="leverage_limits",
            message=f"Leverage within limits: {leverage}x",
            severity="INFO"
        )
    
    def _check_drawdown_state(self, portfolio_state: Dict[str, Any]) -> RiskCheckResult:
        """Check if drawdown limits are exceeded"""
        daily_drawdown = portfolio_state.get('daily_drawdown_pct', 0)
        total_drawdown = portfolio_state.get('total_drawdown_pct', 0)
        
        if daily_drawdown > self.max_daily_drawdown_pct:
            return RiskCheckResult(
                passed=False,
                check_name="drawdown_state",
                message=f"Daily drawdown limit exceeded: {daily_drawdown*100:.1f}% (max: {self.max_daily_drawdown_pct*100:.1f}%)",
                severity="ERROR"
            )
        
        if total_drawdown > self.max_total_drawdown_pct:
            return RiskCheckResult(
                passed=False,
                check_name="drawdown_state",
                message=f"Total drawdown limit exceeded: {total_drawdown*100:.1f}% (max: {self.max_total_drawdown_pct*100:.1f}%)",
                severity="ERROR"
            )
        
        return RiskCheckResult(
            passed=True,
            check_name="drawdown_state",
            message=f"Drawdown within limits (daily: {daily_drawdown*100:.1f}%, total: {total_drawdown*100:.1f}%)",
            severity="INFO"
        )
    
    def _check_fat_finger(self, trade_params: Dict[str, Any], account_balance: float) -> RiskCheckResult:
        """Check for unusually large orders (fat finger detection)"""
        quantity = trade_params.get('quantity', 0)
        price = trade_params.get('price', 0)
        
        position_value = quantity * price
        position_pct = position_value / account_balance if account_balance > 0 else 0
        
        if position_pct > self.fat_finger_threshold:
            return RiskCheckResult(
                passed=False,
                check_name="fat_finger",
                message=f"Unusually large order detected: {position_pct*100:.1f}% of account (threshold: {self.fat_finger_threshold*100:.1f}%)",
                severity="ERROR"
            )
        
        return RiskCheckResult(
            passed=True,
            check_name="fat_finger",
            message="Order size normal",
            severity="INFO"
        )
    
    def get_risk_summary(self, results: List[RiskCheckResult]) -> Dict[str, Any]:
        """
        Get summary of risk check results
        
        Args:
            results: List of risk check results
            
        Returns:
            Summary dictionary
        """
        passed = all(r.passed or r.severity != "ERROR" for r in results)
        
        errors = [r for r in results if not r.passed and r.severity == "ERROR"]
        warnings = [r for r in results if not r.passed and r.severity == "WARNING"]
        
        return {
            'passed': passed,
            'total_checks': len(results),
            'errors': len(errors),
            'warnings': len(warnings),
            'error_messages': [r.message for r in errors],
            'warning_messages': [r.message for r in warnings],
            'all_results': [
                {
                    'check': r.check_name,
                    'passed': r.passed,
                    'severity': r.severity,
                    'message': r.message
                }
                for r in results
            ]
        }
