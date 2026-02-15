"""
Production Safety Checks

Ensures forecasts meet production requirements:
- Non-negative admissions
- Capacity constraints
- Drift detection
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
from forecast_system.utils import get_logger

logger = get_logger(__name__)


def apply_safety_checks(predictions: np.ndarray,
                       quantile_preds: Optional[Dict[float, np.ndarray]] = None,
                       X: Optional[pd.DataFrame] = None,
                       historical_avg: Optional[float] = None,
                       max_utilization: float = 1.2) -> Dict:
    """
    Apply production safety checks to predictions.
    
    Args:
        predictions: Point predictions
        quantile_preds: Quantile predictions (optional)
        X: Feature DataFrame (for capacity)
        historical_avg: Historical 30-day average (for drift detection)
        max_utilization: Maximum allowed utilization (default 1.2 = 120%)
        
    Returns:
        Dictionary with:
        - 'point_predictions': Safety-checked point predictions
        - 'quantile_predictions': Safety-checked quantile predictions (if provided)
        - 'safety_stats': Statistics about applied checks
    """
    logger.info("=" * 60)
    logger.info("PRODUCTION SAFETY CHECKS")
    logger.info("=" * 60)
    
    safety_stats = {
        'n_negative_clipped': 0,
        'n_capacity_capped': 0,
        'drift_detected': False,
        'drift_magnitude': 0.0
    }
    
    # 1. Non-negative clipping
    n_negative_before = np.sum(predictions < 0)
    predictions = np.maximum(predictions, 0)
    safety_stats['n_negative_clipped'] = int(n_negative_before)
    
    if n_negative_before > 0:
        logger.info(f"   📊 Clipped {n_negative_before} negative predictions to 0")
    
    # 2. Capacity clipping
    if X is not None and 'hospital_capacity' in X.columns:
        capacity = X['hospital_capacity'].values
        capacity = np.where(capacity == 0, 1, capacity)  # Avoid division by zero
        max_admissions = capacity * max_utilization
        
        n_capped_before = np.sum(predictions > max_admissions)
        predictions = np.minimum(predictions, max_admissions)
        safety_stats['n_capacity_capped'] = int(n_capped_before)
        
        if n_capped_before > 0:
            logger.info(f"   📊 Capped {n_capped_before} predictions to {max_utilization*100:.0f}% capacity")
    
    # 3. Drift detection
    if historical_avg is not None and historical_avg > 0:
        current_avg = np.mean(predictions)
        drift_ratio = abs(current_avg - historical_avg) / historical_avg
        
        if drift_ratio > 0.3:  # More than 30% drift
            safety_stats['drift_detected'] = True
            safety_stats['drift_magnitude'] = float(drift_ratio)
            logger.warning(f"   ⚠️  DRIFT DETECTED: Forecast avg ({current_avg:.1f}) differs from historical ({historical_avg:.1f}) by {drift_ratio*100:.1f}%")
        else:
            logger.info(f"   ✅ No significant drift (forecast avg: {current_avg:.1f}, historical: {historical_avg:.1f})")
    
    # Apply same checks to quantiles
    quantile_preds_checked = None
    if quantile_preds is not None:
        quantile_preds_checked = {}
        
        for q, preds in quantile_preds.items():
            # Non-negative
            preds = np.maximum(preds, 0)
            
            # Capacity cap
            if X is not None and 'hospital_capacity' in X.columns:
                capacity = X['hospital_capacity'].values
                capacity = np.where(capacity == 0, 1, capacity)
                max_admissions = capacity * max_utilization
                preds = np.minimum(preds, max_admissions)
            
            quantile_preds_checked[q] = preds
        
        # Ensure monotonicity after safety checks
        quantiles_sorted = sorted(quantile_preds_checked.keys())
        for i in range(len(quantiles_sorted) - 1):
            q_low = quantiles_sorted[i]
            q_high = quantiles_sorted[i + 1]
            quantile_preds_checked[q_high] = np.maximum(
                quantile_preds_checked[q_high],
                quantile_preds_checked[q_low]
            )
    
    logger.info("   ✅ Safety checks complete")
    
    return {
        'point_predictions': predictions,
        'quantile_predictions': quantile_preds_checked,
        'safety_stats': safety_stats
    }


def compute_historical_average(X: pd.DataFrame,
                               y: np.ndarray,
                               dates: pd.Series,
                               window_days: int = 30) -> float:
    """
    Compute historical average for drift detection.
    
    Args:
        X: Feature DataFrame
        y: Target values
        dates: Date series
        window_days: Window size in days (default 30)
        
    Returns:
        Historical average
    """
    if len(y) == 0:
        return 0.0
    
    # Get last window_days of data
    dates_sorted = dates.sort_values()
    cutoff_date = dates_sorted.max() - pd.Timedelta(days=window_days)
    
    mask = dates >= cutoff_date
    if mask.sum() == 0:
        return np.mean(y)
    
    return float(np.mean(y[mask]))

