# Hospital Forecasting System Improvements - Implementation Summary

## ✅ COMPLETED IMPROVEMENTS

### STEP 1: Remove Structural Drift Features ✅
- **Removed `trend_index`** (monotonic time index) from `feature_engineering.py`
- **Added rolling z-score normalization** for interaction features (aqi, temperature, outbreak_index)
  - 90-day rolling window per hospital
  - Prevents structural drift in feature distributions
  - Files: `feature_engineering.py` (lines 238-248)

### STEP 2: Remove AR(7) Residual Layer ✅
- **Created `residual_stacking.py`** with proper stacked residual modeling
- **Replaces ineffective AR(7) post-hoc correction** with LightGBM residual model
- Features: `residual_lag_1`, `residual_lag_7`, `rolling_residual_mean_7`, `horizon`
- Uses out-of-fold predictions from CV (no leakage)
- Function: `create_residual_stacker_from_cv()` for training
- Class: `ResidualStacker` for inference

### STEP 3: Stabilize CV Splitting ✅
- **Enhanced `DateGroupedRollingCV`** with:
  - `min_train_years=2` (ensures 2 full seasonal cycles)
  - `regime_aware=True` (ensures validation windows contain both normal and surge regimes)
  - Regime validation check (skips folds with only one regime)
- **Updated time-decay sample weights**:
  - `time_decay_rate=0.003` (increased from 0.002)
  - `min_weight=0.4` (clips minimum weight to prevent extreme down-weighting)
  - Formula: `weight = exp(-0.003 * days_from_end)`, clipped at 0.4
- Files: `cross_validation.py`

### STEP 4: Fix Quantile Training Stability (PARTIAL) ✅
- **Updated `fit_quantiles()`** with:
  - Stronger regularization: `min_data_in_leaf >= 50` (was 20)
  - Lower learning rate: capped at 0.01
  - Increased L1/L2: `lambda_l1/l2 * 1.5`
  - Identical seed for all quantiles (identical hyperparameters)
- **Added isotonic regression** in `predict_quantiles()` for final monotonicity enforcement
- Files: `models/lightgbm_model.py`

### STEP 5-7: PENDING
- Diagnostic experiment (drop lag_1, ema_7)
- Shock robustness mechanisms
- Before/after metrics comparison

## 📋 REMAINING TASKS

### STEP 4 (Continued): Conformal Calibration Updates
**Status**: Partially implemented
**Needed**:
1. Update `compute_conformal_adjustment()` to accept `max_adjustment_factor` parameter
2. Clip extreme adjustments in `calibrate_quantiles_per_horizon()`
3. Enforce increasing interval width with horizon (sqrt(horizon) scaling)
4. Target: coverage_80 between 75%-85%, H7 interval width < 15

**Files to update**: `conformal_calibration.py`

### STEP 5: Diagnostic Experiment
**Status**: Not started
**Needed**:
- Create function to temporarily drop `lag_1` and `ema_7`
- Retrain model
- Measure MAE change
- Return quantitative comparison
- If MAE increases < 30% → exogenous signals meaningful
- If MAE collapses → system is purely autoregressive

**File to create**: `forecast_system/diagnostics_experiments.py`

### STEP 6: Shock Robustness Mechanisms
**Status**: Not started
**Needed**:
1. Rolling retraining: Full retrain every 30 days
2. Drift monitoring: PSI monitoring weekly, alert if PSI > 0.3
3. Error monitoring: Track 14-day rolling MAE vs 90-day baseline, alert if > 40% increase
4. Horizon-specific uncertainty growth: Add sqrt(horizon) uncertainty scaling factor

**Files to create/update**:
- `forecast_system/monitoring.py` (drift + error monitoring)
- `forecast_system/rolling_retraining.py` (already exists, needs integration)
- Update `inference.py` for horizon uncertainty scaling

### STEP 7: Before/After Metrics Comparison
**Status**: Not started
**Needed**:
- Create comparison function that logs:
  - MAE (before/after)
  - RMSE (before/after)
  - coverage_80 (before/after)
  - CV CoV (before/after)
  - residual ACF lag-1 & lag-7 (before/after)
- Save to JSON file

**File to create**: `forecast_system/metrics_comparison.py`

## 🔧 INTEGRATION REQUIRED

### Update `train_pipeline.py`:
1. **Remove AR(7) residual correction calls**
   - Comment out `create_residual_corrector()` calls
   - Replace with `create_residual_stacker_from_cv()`

2. **Use enhanced regime features**
   - Call `create_enhanced_regime_features()` from `regime_aware.py`
   - Use `surge_intensity`, `regime_duration`, `regime_transition_flag`

3. **Apply time-decay weights in CV**
   - Ensure `create_sample_weights()` is called with `use_time_decay=True`, `min_weight=0.4`

4. **Use improved quantile training**
   - Ensure `fit_quantiles()` uses updated parameters (min_data_in_leaf=50, learning_rate<=0.01)
   - Apply isotonic regression post-prediction

5. **Update conformal calibration**
   - Use rolling-window conformal (last 90 days)
   - Clip extreme adjustments
   - Enforce horizon width scaling

6. **Add ACF evaluation**
   - Call `evaluate_residual_acf()` from `acf_evaluation.py`
   - Fail training if lag-1 ACF > 0.35

7. **Add diagnostic experiment**
   - Run experiment dropping lag_1 and ema_7
   - Log results

## 📊 EXPECTED IMPROVEMENTS

After full integration:
- **Residual ACF**: Lag-1 < 0.35 (from ~0.47)
- **CV CoV**: < 30% (from 54-60%)
- **Quantile coverage**: 75-85% (from ~65%)
- **H7 interval width**: < 15 (from large conformal adjustments)
- **Monotonic violations**: Reduced by 50% (via isotonic regression)

## 🚨 CRITICAL NOTES

1. **AR(7) Residual Layer**: Must be completely removed from `train_pipeline.py`
2. **Trend Index**: Already removed, verify it's not used anywhere
3. **Conformal Calibration**: Must clip adjustments to prevent H6-H7 explosion
4. **CV Regime-Aware**: Must ensure validation windows have both regimes
5. **Time-Decay Weights**: Must clip at 0.4 minimum

## 📁 FILES CREATED/MODIFIED

### New Files:
- `forecast_system/residual_stacking.py` ✅
- `forecast_system/IMPROVEMENTS_SUMMARY.md` (this file)

### Modified Files:
- `forecast_system/feature_engineering.py` ✅
- `forecast_system/cross_validation.py` ✅
- `forecast_system/models/lightgbm_model.py` ✅
- `forecast_system/conformal_calibration.py` (partial)

### Files Needing Updates:
- `forecast_system/train_pipeline.py` (integration)
- `forecast_system/inference.py` (horizon uncertainty scaling)

### Files to Create:
- `forecast_system/diagnostics_experiments.py`
- `forecast_system/monitoring.py`
- `forecast_system/metrics_comparison.py`

