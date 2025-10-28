# Strategy Improvement Phase Plan

## Current Status
- ✅ Fixed 3 critical bugs (UniversalMacd, VolatilitySystem, EnhancedRiskManager)
- ✅ Added HTF indicators and cooldown mechanism
- ✅ Optimized ConnorsRSI and VolatilitySystem
- ✅ Completed initial backtest optimization

## Top 3 Performers (Ready for Further Optimization)
1. **Momentum_1h**: +49%, 0.90 Sharpe, 4.85% DD
2. **UniversalMacd_5m**: +240%, 0.38 Sharpe, 50.3% DD
3. **VolatilitySystem_1h**: +7.4%, 0.24 Sharpe, 3.97% DD

## Remaining Issues
- **Momentum_15m**: -39% (wrong timeframe)
- **ConnorsRSI_15m**: -15% despite 56% reduction in trades
- **MeanReversion strategies**: Low activity (<20 trades)

---

## Phase G: Walk-Forward Optimization Framework
**Duration**: 2-3 hours
**Goal**: Implement robust walk-forward optimization to validate strategy parameters

### Tasks:
1. Create WalkForwardOptimizer class with 4-fold cross-validation
2. Implement composite objective function (Sharpe - 0.5*DD - 0.0005*trades)
3. Add parameter stability checks across folds
4. Implement robustness filters (min 30 trades per fold)
5. Test on top 3 performers with parameter ranges

### Deliverables:
- `src/backtesting/walk_forward_optimizer.py`
- Walk-forward optimization results for top 3 strategies
- Parameter stability analysis report

### Success Criteria:
- All 3 strategies pass robustness checks (≥30 trades per fold)
- Parameters stable across folds (±20% variation max)
- Out-of-sample performance within 30% of in-sample

---

## Phase H: Real Data Testing
**Duration**: 1-2 hours
**Goal**: Validate strategies on real historical data instead of synthetic

### Tasks:
1. Download real BTC/USDT and ETH/USDT data (1 year, 5m/15m/1h)
2. Verify data quality (gaps, outliers, volume)
3. Calculate all indicators including HTF
4. Run backtests on real data for top 3 strategies
5. Compare synthetic vs real data performance

### Deliverables:
- Real historical data files (CSV)
- Backtest results comparison (synthetic vs real)
- Data quality report

### Success Criteria:
- Real data performance within 50% of synthetic data performance
- No major data quality issues
- Strategies remain profitable on real data

---

## Phase I: Fix Underperforming Strategies
**Duration**: 1-2 hours
**Goal**: Fix or disable remaining unprofitable strategies

### Tasks:
1. **Momentum_15m**: Change to 1h timeframe (align with Momentum_1h success)
2. **ConnorsRSI_15m**: Either disable or add MFI confirmation + stricter filters
3. **MeanReversion strategies**: Tune parameters to increase activity or disable
4. Run backtests to verify improvements

### Deliverables:
- Updated strategy parameters
- Backtest results showing improvements
- List of strategies to disable (if any)

### Success Criteria:
- Momentum_15m turns profitable after timeframe change
- ConnorsRSI_15m either profitable or disabled
- All active strategies have ≥20 trades in 6 months

---

## Phase J: Ensemble System & Final Validation
**Duration**: 1-2 hours
**Goal**: Create ensemble weighting system and final validation

### Tasks:
1. Implement Sharpe-based ensemble weighting
2. Calculate optimal portfolio allocation (top 3 strategies)
3. Run ensemble backtest with dynamic weighting
4. Create final performance report
5. Document all changes and recommendations

### Deliverables:
- Ensemble weighting system
- Final portfolio backtest results
- Complete optimization documentation
- Recommendations for paper trading

### Success Criteria:
- Ensemble Sharpe ratio ≥ 0.50
- Ensemble max drawdown ≤ 20%
- Clear paper trading plan with 3-phase rollout

---

## Total Estimated Time: 7-10 hours

## Next Steps After Completion:
1. Begin Phase 1 of paper trading (Momentum_1h only, 2 weeks)
2. Monitor performance and adjust parameters if needed
3. Gradually add UniversalMacd_5m and VolatilitySystem_1h
4. Transition to live trading with small capital after successful paper trading

---

## Questions for User:
1. Should I proceed with Phase G (Walk-Forward Optimization) first?
2. Do you want me to download real data from a specific exchange (Binance, Bybit, etc.)?
3. Any specific date range for real data (e.g., last 12 months)?
4. Should I disable ConnorsRSI_15m immediately or try one more optimization attempt?
