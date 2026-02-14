"""
Drift-Triggered Retraining Module

Automatically triggers model retraining when drift is detected:
- PSI > 0.2 on critical features
- Rolling MAE > 20% above baseline
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Callable, Tuple
from .drift_detection import detect_feature_drift, detect_prediction_drift, calculate_psi
from .utils import get_logger

logger = get_logger(__name__)


def should_retrain_due_to_drift(
    X_train: pd.DataFrame,
    X_current: pd.DataFrame,
    y_true: Optional[pd.Series] = None,
    y_pred: Optional[pd.Series] = None,
    critical_features: Optional[list] = None,
    psi_threshold: float = 0.2,
    mae_increase_threshold: float = 0.20,
    baseline_mae: Optional[float] = None,
    rolling_window_days: int = 14,
    baseline_window_days: int = 90
) -> Dict[str, any]:
    """
    Check if retraining should be triggered due to drift.
    
    Args:
        X_train: Training data (baseline distribution)
        X_current: Current production data
        y_true: True values for current period (optional, for prediction drift)
        y_pred: Predicted values for current period (optional, for prediction drift)
        critical_features: List of critical feature names to monitor (default: lag features + exogenous)
        psi_threshold: PSI threshold for feature drift (default 0.2)
        mae_increase_threshold: MAE increase threshold for prediction drift (default 0.20 = 20%)
        baseline_mae: Baseline MAE (if None, computed from y_true/y_pred)
        rolling_window_days: Window for rolling MAE (default 14)
        baseline_window_days: Window for baseline MAE (default 90)
        
    Returns:
        Dictionary with:
        - should_retrain: bool
        - reasons: list of trigger reasons
        - feature_drift: dict of feature PSI values
        - prediction_drift: dict with MAE metrics
    """
    logger.info("=" * 70)
    logger.info("🔍 DRIFT-TRIGGERED RETRAINING CHECK")
    logger.info("=" * 70)
    
    result = {
        'should_retrain': False,
        'reasons': [],
        'feature_drift': {},
        'prediction_drift': {}
    }
    
    # Default critical features if not specified
    if critical_features is None:
        critical_features = [
            'lag_1', 'lag_7', 'lag_14', 'lag_30',
            'ema_7', 'rolling_std_7',
            'outbreak_index', 'aqi', 'temperature',
            'outbreak_index_lag_7', 'aqi_lag_7', 'temperature_lag_7'
        ]
    
    # Check feature drift on critical features
    logger.info("   Checking feature drift (PSI) on critical features...")
    feature_drift_detected = False
    
    for feature in critical_features:
        if feature not in X_train.columns or feature not in X_current.columns:
            continue
        
        try:
            psi = calculate_psi(X_train[feature].values, X_current[feature].values)
            result['feature_drift'][feature] = psi
            
            if psi > psi_threshold:
                feature_drift_detected = True
                result['reasons'].append(f"Feature drift: {feature} PSI={psi:.3f} > {psi_threshold}")
                logger.warning(f"      ⚠️  {feature}: PSI={psi:.3f} > {psi_threshold} (DRIFT DETECTED)")
            else:
                logger.info(f"      ✅ {feature}: PSI={psi:.3f} <= {psi_threshold}")
        except Exception as e:
            logger.warning(f"      ⚠️  Could not compute PSI for {feature}: {e}")
    
    if feature_drift_detected:
        result['should_retrain'] = True
    
    # Check prediction drift (if y_true and y_pred provided)
    if y_true is not None and y_pred is not None:
        logger.info("   Checking prediction drift (rolling MAE)...")
        
        try:
            prediction_drift_result = detect_prediction_drift(
                y_true=y_true,
                y_pred=y_pred,
                rolling_window_days=rolling_window_days,
                baseline_window_days=baseline_window_days,
                baseline_mae=baseline_mae
            )
            
            result['prediction_drift'] = prediction_drift_result
            
            current_mae = prediction_drift_result.get('current_mae')
            baseline_mae_actual = prediction_drift_result.get('baseline_mae')
            mae_increase_pct = prediction_drift_result.get('mae_increase_pct', 0)
            
            if mae_increase_pct > mae_increase_threshold * 100:  # Convert to percentage
                result['should_retrain'] = True
                result['reasons'].append(
                    f"Prediction drift: MAE increased {mae_increase_pct:.1f}% "
                    f"(current={current_mae:.2f}, baseline={baseline_mae_actual:.2f})"
                )
                logger.warning(
                    f"      ⚠️  MAE increase: {mae_increase_pct:.1f}% > {mae_increase_threshold*100:.1f}% "
                    f"(DRIFT DETECTED)"
                )
            else:
                logger.info(
                    f"      ✅ MAE increase: {mae_increase_pct:.1f}% <= {mae_increase_threshold*100:.1f}%"
                )
        except Exception as e:
            logger.warning(f"      ⚠️  Could not compute prediction drift: {e}")
    
    # Summary
    logger.info("\n" + "=" * 70)
    if result['should_retrain']:
        logger.warning("   ⚠️  RETRAINING TRIGGERED")
        logger.warning(f"   Reasons: {len(result['reasons'])}")
        for reason in result['reasons']:
            logger.warning(f"      - {reason}")
    else:
        logger.info("   ✅ No drift detected - retraining not needed")
    logger.info("=" * 70)
    
    return result


def trigger_retraining_if_needed(
    X_train: pd.DataFrame,
    X_current: pd.DataFrame,
    train_model_fn: Callable,
    y_true: Optional[pd.Series] = None,
    y_pred: Optional[pd.Series] = None,
    **drift_check_kwargs
) -> Tuple[bool, Optional[object], Dict]:
    """
    Check for drift and trigger retraining if needed.
    
    Args:
        X_train: Training data (baseline)
        X_current: Current production data
        train_model_fn: Function to train model: (X_train, y_train, X_val, y_val) -> model
        y_true: True values (optional)
        y_pred: Predicted values (optional)
        **drift_check_kwargs: Additional kwargs for should_retrain_due_to_drift
        
    Returns:
        Tuple of (retrained: bool, new_model: Optional[object], drift_check_results: Dict)
    """
    drift_check = should_retrain_due_to_drift(
        X_train=X_train,
        X_current=X_current,
        y_true=y_true,
        y_pred=y_pred,
        **drift_check_kwargs
    )
    
    if not drift_check['should_retrain']:
        return False, None, drift_check
    
    logger.info("\n" + "=" * 70)
    logger.info("🔄 TRIGGERING AUTOMATIC RETRAINING")
    logger.info("=" * 70)
    
    try:
        # Use last 30 days of training data as validation
        if 'date' in X_train.columns:
            dates = pd.to_datetime(X_train['date'])
            val_start = dates.max() - pd.Timedelta(days=30)
            val_mask = dates >= val_start
            X_val = X_train[val_mask].copy()
            X_train_new = X_train[~val_mask].copy()
        else:
            # Simple 80/20 split if no date column
            split_idx = int(len(X_train) * 0.8)
            X_train_new = X_train.iloc[:split_idx].copy()
            X_val = X_train.iloc[split_idx:].copy()
        
        # Extract targets if available
        y_train_new = None
        y_val_new = None
        if 'target' in X_train_new.columns:
            y_train_new = X_train_new.pop('target')
        if 'target' in X_val.columns:
            y_val_new = X_val.pop('target')
        
        logger.info(f"   Retraining on {len(X_train_new)} samples")
        logger.info(f"   Validation on {len(X_val)} samples")
        
        # Train new model
        new_model = train_model_fn(X_train_new, y_train_new, X_val, y_val_new)
        
        logger.info("   ✅ Retraining complete")
        return True, new_model, drift_check
        
    except Exception as e:
        logger.error(f"   ❌ Retraining failed: {e}")
        return False, None, drift_check

