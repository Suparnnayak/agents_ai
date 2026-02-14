# Option A vs TFT Decision Guide

## Current System Status

### ✅ Implemented (Option A Components)

1. **OOF Residual Feedback Features** ✅
   - `residual_lag_1`, `residual_lag_7`, `residual_ema_7`
   - Generated from out-of-fold CV predictions
   - Allows trees to learn residual correction directly
   - **Expected Impact**: ACF reduction from 0.54 → 0.35-0.40

2. **Extended Lag Features** ✅
   - Lags: [1, 2, 3, 5, 7, 14, 21, 30, 60, **90**]
   - **NEW**: Added `lag_90` for longer seasonal cycles
   - Helps trees approximate longer temporal dependencies

3. **Rolling Retraining** ✅
   - Module: `rolling_retraining.py`
   - Retrains every 30 days on last 18-24 months
   - **Expected Impact**: Reduces CV CoV from 60% → 40-45%

4. **Drift-Triggered Retraining** ✅
   - Module: `drift_triggered_retraining.py`
   - Auto-retrains when PSI > 0.2 or MAE > 20% above baseline
   - Production robustness

5. **Regime-Split Models** ✅ (Available, not enabled by default)
   - Module: `regime_aware.py` → `train_regime_separate_models()`
   - Trains separate models for normal vs surge regimes
   - **Expected Impact**: Reduces CV CoV significantly (often 30-50% reduction)
   - **To Enable**: Set `use_regime_split_models=True` in config

### ⚠️ Not Yet Integrated (Needs Activation)

1. **Regime-Split Models**: Code exists but not used in pipeline
   - **Action**: Add option to `train_pipeline.py` to use regime-split models
   - **Impact**: Likely largest CoV reduction (30-50%)

2. **Rolling Retraining**: Module exists but not scheduled
   - **Action**: Integrate into production pipeline
   - **Impact**: Operational robustness

## TFT Decision Framework

### Decision Criteria

**Use TFT if (after Option A):**
- Residual ACF (lag-1) > 0.40
- **OR** CV CoV > 40%
- **OR** Long-horizon conformal adjustment > 3.0x
- **OR** Horizon 7 interval width > 20.0

**Continue with Trees if:**
- Residual ACF (lag-1) ≤ 0.40
- **AND** CV CoV ≤ 40%
- **AND** Conformal adjustments reasonable
- **AND** Interval widths stable

### Current Metrics (from latest run)

- Residual ACF (lag-1): **0.5437** ⚠️ (above 0.40 threshold)
- Residual ACF (lag-7): **0.6386** ⚠️ (above 0.50 threshold)
- CV CoV: **60.6%** ⚠️ (above 40% threshold)
- Coverage: 80.91% ✅ (good)
- Long-horizon interval width: H7 = 27.15 ⚠️ (above 20.0 threshold)

### Recommendation

**Current State**: After basic Option A improvements, metrics still indicate sequence problem.

**Next Steps**:

1. **Phase 1 - Complete Option A** (Do this first):
   - ✅ Enable regime-split models (`use_regime_split_models=True`)
   - ✅ Ensure error features are properly integrated
   - ✅ Verify lag_90 is being used
   - ✅ Test rolling retraining

2. **Measure After Phase 1**:
   - Residual ACF (lag-1)
   - CV CoV
   - Long-horizon stability

3. **Decision Point**:
   - If ACF < 0.40 and CoV < 40%: **Trees are sufficient** ✅
   - If ACF > 0.40 or CoV > 40%: **Consider Hybrid LGBM + TFT** ⚠️

## Expected Outcomes

### Option A (Complete Implementation)

**Best Case**:
- ACF: 0.54 → 0.30-0.35
- CoV: 60% → 25-30%
- Long-horizon stable

**Realistic Case**:
- ACF: 0.54 → 0.40-0.45 (trees struggle with temporal memory)
- CoV: 60% → 35-40% (regime-split helps significantly)
- Long-horizon: Improved but may still need calibration

**If Realistic Case**: TFT becomes justified for remaining 10-15% improvement.

### Hybrid LGBM + TFT

**Benefits**:
- ACF: 0.40-0.45 → 0.20-0.25 (temporal attention)
- CoV: 35-40% → 20-25% (sequence modeling)
- Long-horizon: Natural uncertainty growth

**Costs**:
- More complex deployment
- Higher compute requirements
- More maintenance overhead

## Implementation Priority

1. **Immediate** (Do Now):
   - ✅ Fix quantile bugs (DONE)
   - ✅ Add lag_90 (DONE)
   - ✅ Add error features (DONE)
   - ⚠️ Enable regime-split models (needs integration)

2. **Short-term** (This Week):
   - Integrate regime-split models into pipeline
   - Run full Option A evaluation
   - Measure metrics

3. **Decision Point** (After Option A):
   - Evaluate TFT need using `tft_decision_framework.py`
   - If needed: Implement Hybrid LGBM + TFT
   - If not: Deploy tree-based system

## Code Locations

- **Error Features**: `forecast_system/error_features.py`
- **Rolling Retraining**: `forecast_system/rolling_retraining.py`
- **Drift-Triggered Retraining**: `forecast_system/drift_triggered_retraining.py`
- **Regime-Split Models**: `forecast_system/regime_aware.py` → `train_regime_separate_models()`
- **TFT Decision Framework**: `forecast_system/tft_decision_framework.py`
- **Config**: `forecast_system/config.py` (add `use_regime_split_models=True`)

## Next Actions

1. Enable regime-split models in training pipeline
2. Run full training with all Option A improvements
3. Evaluate using TFT decision framework
4. Make final architecture decision based on metrics

