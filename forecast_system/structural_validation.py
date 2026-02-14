"""
Structural Temporal Validation

Validates structural temporal properties of the model:
- Residual weekly structure test (lag-7 ACF)
- Horizon degradation ratio (H7 MAE / H1 MAE)
"""

import numpy as np
import pandas as pd
from typing import Optional, Dict
from scipy.stats import pearsonr
from .utils import get_logger

logger = get_logger(__name__)


def test_residual_weekly_structure(
    residuals: np.ndarray,
    threshold: float = 0.4
) -> Dict:
    """
    Test for residual weekly structure (lag-7 ACF).
    
    If lag-7 ACF > threshold, weekly structure is not captured.
    
    Args:
        residuals: Model residuals (y_true - y_pred)
        threshold: Threshold for lag-7 ACF (default 0.4)
        
    Returns:
        Dictionary with test results
    """
    if len(residuals) < 8:
        return {
            'lag_7_acf': np.nan,
            'weekly_structure_captured': None,
            'warning': 'Insufficient data for weekly structure test'
        }
    
    # Compute lag-7 ACF
    if len(residuals) > 7:
        r, _ = pearsonr(residuals[:-7], residuals[7:])
        lag_7_acf = r if not np.isnan(r) else 0.0
    else:
        lag_7_acf = 0.0
    
    weekly_structure_captured = lag_7_acf <= threshold
    
    logger.info("=" * 60)
    logger.info("RESIDUAL WEEKLY STRUCTURE TEST")
    logger.info("=" * 60)
    logger.info(f"   Lag-7 ACF: {lag_7_acf:.4f} (threshold: {threshold:.4f})")
    
    if not weekly_structure_captured:
        logger.warning(f"   ⚠️  WEEKLY STRUCTURE NOT CAPTURED: Lag-7 ACF ({lag_7_acf:.4f}) > {threshold:.4f}")
        logger.warning("   Model is not fully capturing weekly temporal patterns")
    else:
        logger.info(f"   ✅ Weekly structure captured (lag-7 ACF <= {threshold:.4f})")
    
    return {
        'lag_7_acf': lag_7_acf,
        'weekly_structure_captured': weekly_structure_captured,
        'threshold': threshold
    }


def compute_horizon_degradation_ratio(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    horizons: np.ndarray,
    threshold: float = 3.0
) -> Dict:
    """
    Compute horizon degradation ratio: H7 MAE / H1 MAE.
    
    If ratio > threshold, long-horizon instability is detected.
    
    Args:
        y_true: True values
        y_pred: Predicted values
        horizons: Forecast horizons (1-7)
        threshold: Threshold for degradation ratio (default 3.0)
        
    Returns:
        Dictionary with degradation metrics
    """
    logger.info("=" * 60)
    logger.info("HORIZON DEGRADATION ANALYSIS")
    logger.info("=" * 60)
    
    horizon_mae = {}
    
    for horizon in range(1, 8):
        horizon_mask = horizons == horizon
        if horizon_mask.sum() > 0:
            horizon_errors = np.abs(y_true[horizon_mask] - y_pred[horizon_mask])
            horizon_mae[horizon] = np.mean(horizon_errors)
            logger.info(f"   H{horizon} MAE: {horizon_mae[horizon]:.3f} (n={horizon_mask.sum()})")
    
    if 1 in horizon_mae and 7 in horizon_mae:
        degradation_ratio = horizon_mae[7] / horizon_mae[1] if horizon_mae[1] > 0 else np.inf
        logger.info(f"\n   Horizon Degradation Ratio (H7/H1): {degradation_ratio:.2f}")
        
        if degradation_ratio > threshold:
            logger.warning(f"   ⚠️  LONG-HORIZON INSTABILITY: H7 MAE ({horizon_mae[7]:.3f}) is {degradation_ratio:.2f}x H1 MAE ({horizon_mae[1]:.3f})")
            logger.warning(f"   Ratio ({degradation_ratio:.2f}) > threshold ({threshold:.2f})")
        else:
            logger.info(f"   ✅ Horizon degradation acceptable (ratio <= {threshold:.2f})")
        
        return {
            'horizon_mae': horizon_mae,
            'degradation_ratio': degradation_ratio,
            'long_horizon_stable': degradation_ratio <= threshold,
            'threshold': threshold
        }
    else:
        logger.warning("   Cannot compute degradation ratio: missing H1 or H7 data")
        return {
            'horizon_mae': horizon_mae,
            'degradation_ratio': np.nan,
            'long_horizon_stable': None,
            'threshold': threshold
        }


def validate_structural_temporal_properties(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    horizons: Optional[np.ndarray] = None,
    weekly_structure_threshold: float = 0.4,
    degradation_threshold: float = 3.0
) -> Dict:
    """
    Complete structural temporal validation.
    
    Args:
        y_true: True values
        y_pred: Predicted values
        horizons: Forecast horizons (1-7)
        weekly_structure_threshold: Threshold for lag-7 ACF
        degradation_threshold: Threshold for H7/H1 MAE ratio
        
    Returns:
        Dictionary with all validation results
    """
    residuals = y_true - y_pred
    
    results = {
        'weekly_structure': test_residual_weekly_structure(residuals, weekly_structure_threshold),
        'horizon_degradation': None
    }
    
    if horizons is not None:
        results['horizon_degradation'] = compute_horizon_degradation_ratio(
            y_true, y_pred, horizons, degradation_threshold
        )
    
    return results

