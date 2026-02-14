"""
Drift Detection Module

Implements two types of drift detection:
1. Data Drift (PSI - Population Stability Index)
2. Prediction Drift (Rolling MAE monitoring)
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from .utils import get_logger

logger = get_logger(__name__)


def calculate_psi(expected: np.ndarray,
                   actual: np.ndarray,
                   bins: int = 10) -> float:
    """
    Calculate Population Stability Index (PSI).
    
    PSI measures distribution shift between two datasets.
    PSI < 0.1: No significant drift
    PSI 0.1-0.2: Moderate drift
    PSI > 0.2: Significant drift (retrain recommended)
    
    Args:
        expected: Reference distribution (training data)
        actual: Current distribution (new data)
        bins: Number of bins for histogram
        
    Returns:
        PSI value
    """
    # Remove NaN and infinite values
    expected = expected[np.isfinite(expected)]
    actual = actual[np.isfinite(actual)]
    
    if len(expected) == 0 or len(actual) == 0:
        return np.nan
    
    # Create bins based on expected distribution
    breakpoints = np.percentile(expected, np.linspace(0, 100, bins + 1))
    breakpoints = np.unique(breakpoints)  # Remove duplicates
    
    if len(breakpoints) < 2:
        return np.nan
    
    # Calculate histograms
    expected_hist, _ = np.histogram(expected, breakpoints)
    actual_hist, _ = np.histogram(actual, breakpoints)
    
    # Normalize to percentages
    expected_percents = expected_hist / len(expected)
    actual_percents = actual_hist / len(actual)
    
    # Avoid division by zero
    expected_percents = np.maximum(expected_percents, 1e-6)
    actual_percents = np.maximum(actual_percents, 1e-6)
    
    # Calculate PSI
    psi = np.sum((actual_percents - expected_percents) *
                 np.log(actual_percents / expected_percents))
    
    return psi


def detect_feature_drift(
    X_train: pd.DataFrame,
    X_new: pd.DataFrame,
    features: Optional[list] = None,
    psi_threshold: float = 0.2
) -> Dict[str, Dict]:
    """
    Detect data drift for multiple features using PSI.
    
    Args:
        X_train: Training data (reference distribution)
        X_new: New data to check for drift
        features: Features to check (if None, check all numeric features)
        psi_threshold: PSI threshold for significant drift
        
    Returns:
        Dictionary mapping feature -> {'psi': value, 'drift_detected': bool}
    """
    logger.info("=" * 60)
    logger.info("🔍 FEATURE DRIFT DETECTION (PSI)")
    logger.info("=" * 60)
    
    if features is None:
        # Check all numeric features
        numeric_cols = X_train.select_dtypes(include=[np.number]).columns
        features = [col for col in numeric_cols if col not in ['horizon', 'hospital_id_enc']]
    
    drift_results = {}
    drift_count = 0
    
    for feature in features:
        if feature not in X_train.columns or feature not in X_new.columns:
            continue
        
        expected = X_train[feature].values
        actual = X_new[feature].values
        
        psi = calculate_psi(expected, actual)
        
        if np.isnan(psi):
            continue
        
        drift_detected = psi > psi_threshold
        
        drift_results[feature] = {
            'psi': psi,
            'drift_detected': drift_detected
        }
        
        if drift_detected:
            drift_count += 1
            logger.warning(f"   ⚠️  {feature}: PSI={psi:.4f} > {psi_threshold} (DRIFT DETECTED)")
        else:
            logger.info(f"   ✅ {feature}: PSI={psi:.4f} (no drift)")
    
    logger.info(f"\n   Summary: {drift_count}/{len(drift_results)} features show significant drift")
    
    return drift_results


def detect_prediction_drift(
    errors: pd.Series,
    window_days: int = 14,
    baseline_window_days: int = 90,
    drift_threshold: float = 0.2  # Changed to 20% as per requirements
) -> Dict:
    """
    Detect prediction drift by monitoring rolling MAE.
    
    If rolling MAE increases by more than threshold over baseline, drift is detected.
    
    Args:
        errors: Series of absolute errors (with date index)
        window_days: Rolling window size for current MAE
        baseline_window_days: Baseline window size for comparison
        drift_threshold: Percentage increase threshold (e.g., 0.3 = 30%)
        
    Returns:
        Dictionary with drift status and metrics
    """
    logger.info("=" * 60)
    logger.info("🔍 PREDICTION DRIFT DETECTION (Rolling MAE)")
    logger.info("=" * 60)
    
    if len(errors) < baseline_window_days:
        logger.warning(f"   Insufficient data: {len(errors)} < {baseline_window_days} days")
        return {
            'drift_detected': False,
            'current_mae': np.nan,
            'baseline_mae': np.nan,
            'mae_increase_pct': np.nan
        }
    
    # Calculate rolling MAE
    rolling_mae = errors.rolling(window=window_days, min_periods=window_days).mean()
    
    # Get baseline MAE (from earlier period)
    baseline_mae = errors.iloc[:baseline_window_days].mean()
    
    # Get current MAE (most recent window)
    current_mae = rolling_mae.iloc[-1]
    
    # Calculate percentage increase
    mae_increase_pct = (current_mae - baseline_mae) / (baseline_mae + 1e-6)
    
    drift_detected = mae_increase_pct > drift_threshold
    
    logger.info(f"   Baseline MAE ({baseline_window_days} days): {baseline_mae:.3f}")
    logger.info(f"   Current MAE ({window_days} days): {current_mae:.3f}")
    logger.info(f"   MAE increase: {mae_increase_pct*100:.1f}%")
    
    if drift_detected:
        logger.warning(f"   ⚠️  DRIFT DETECTED: MAE increased by {mae_increase_pct*100:.1f}% > {drift_threshold*100:.1f}%")
    else:
        logger.info(f"   ✅ No drift detected")
    
    return {
        'drift_detected': drift_detected,
        'current_mae': current_mae,
        'baseline_mae': baseline_mae,
        'mae_increase_pct': mae_increase_pct,
        'rolling_mae': rolling_mae
    }


def get_drift_severity(psi: float) -> str:
    """
    Classify drift severity based on PSI value.
    
    Returns:
        'LOW', 'MODERATE', or 'HIGH'
    """
    if np.isnan(psi):
        return 'UNKNOWN'
    elif psi < 0.1:
        return 'LOW'
    elif psi < 0.2:
        return 'MODERATE'
    else:
        return 'HIGH'


def monitor_drift(
    X_train: pd.DataFrame,
    X_new: pd.DataFrame,
    errors: Optional[pd.Series] = None,
    features: Optional[list] = None,
    psi_threshold: float = 0.2,
    mae_drift_threshold: float = 0.2,  # 20% as per requirements
    drift_feature_pct_threshold: float = 0.05  # 5% of features must show drift
) -> Dict:
    """
    Complete drift monitoring pipeline with separated results and severity levels.
    
    Args:
        X_train: Training data (reference)
        X_new: New data to monitor
        errors: Optional series of prediction errors (for prediction drift)
        features: Features to monitor (if None, all numeric)
        psi_threshold: PSI threshold for feature drift
        mae_drift_threshold: MAE increase threshold for prediction drift (20%)
        drift_feature_pct_threshold: Percentage of features that must show drift to trigger overall drift
        
    Returns:
        Dictionary with separated feature and prediction drift results, severity levels
    """
    logger.info("=" * 60)
    logger.info("DRIFT MONITORING: Feature + Prediction Drift")
    logger.info("=" * 60)
    
    results = {
        'feature_drift': {},
        'prediction_drift': None,
        'overall_drift_detected': False,
        'overall_severity': 'LOW'
    }
    
    # Feature drift detection (separated)
    if len(X_new) > 0:
        results['feature_drift'] = detect_feature_drift(
            X_train, X_new, features, psi_threshold
        )
    
    # Prediction drift detection (separated)
    if errors is not None and len(errors) > 0:
        results['prediction_drift'] = detect_prediction_drift(
            errors, drift_threshold=mae_drift_threshold
        )
    
    # Determine overall drift status (only trigger if conditions met)
    feature_drift_count = sum(
        1 for info in results['feature_drift'].values()
        if info.get('drift_detected', False)
    )
    feature_drift_pct = feature_drift_count / len(results['feature_drift']) if len(results['feature_drift']) > 0 else 0
    
    prediction_drift_detected = (
        results['prediction_drift'] is not None and
        results['prediction_drift'].get('drift_detected', False)
    )
    
    # Overall drift triggered only if:
    # - PSI > 0.2 for >5% of features OR
    # - Rolling MAE increases >20%
    feature_drift_triggered = feature_drift_pct > drift_feature_pct_threshold
    prediction_drift_triggered = prediction_drift_detected
    
    results['overall_drift_detected'] = feature_drift_triggered or prediction_drift_triggered
    
    # Determine overall severity
    feature_severities = [info.get('severity', 'LOW') for info in results['feature_drift'].values() if info.get('drift_detected', False)]
    prediction_severity = results['prediction_drift'].get('severity', 'LOW') if results['prediction_drift'] else 'LOW'
    
    all_severities = feature_severities + ([prediction_severity] if prediction_drift_triggered else [])
    if 'HIGH' in all_severities:
        results['overall_severity'] = 'HIGH'
    elif 'MODERATE' in all_severities:
        results['overall_severity'] = 'MODERATE'
    else:
        results['overall_severity'] = 'LOW'
    
    # Log results clearly (no contradictory outputs)
    logger.info("\n" + "=" * 60)
    logger.info("DRIFT MONITORING SUMMARY")
    logger.info("=" * 60)
    logger.info(f"   Feature Drift: {feature_drift_count} features ({feature_drift_pct:.1%}) with PSI > {psi_threshold}")
    logger.info(f"   Prediction Drift: {'DETECTED' if prediction_drift_triggered else 'NOT DETECTED'}")
    if prediction_drift_triggered and results['prediction_drift']:
        logger.info(f"      MAE increase: {results['prediction_drift']['mae_increase_pct']*100:.1f}%")
    
    if results['overall_drift_detected']:
        logger.warning(f"\n   🚨 OVERALL DRIFT DETECTED ({results['overall_severity']}) - Retraining recommended")
        logger.warning(f"   Triggered by: {'Feature drift' if feature_drift_triggered else ''} {'+' if feature_drift_triggered and prediction_drift_triggered else ''} {'Prediction drift' if prediction_drift_triggered else ''}")
    else:
        logger.info("\n   ✅ No overall drift detected")
    
    return results

