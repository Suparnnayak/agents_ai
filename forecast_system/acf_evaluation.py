"""
ACF Evaluation Module

Evaluates residual autocorrelation and enforces training failure threshold.
"""

import numpy as np
import pandas as pd
from typing import Optional
from scipy.stats import pearsonr
from forecast_system.utils import get_logger

logger = get_logger(__name__)


def compute_residual_acf(
    residuals: np.ndarray,
    max_lag: int = 7
) -> Dict[int, float]:
    """
    Compute residual autocorrelation function (ACF).
    
    Args:
        residuals: Model residuals (y_true - y_pred)
        max_lag: Maximum lag to compute
        
    Returns:
        Dictionary mapping lag -> ACF value
    """
    acf_values = {}
    
    for lag in range(1, max_lag + 1):
        if len(residuals) > lag:
            # Compute correlation between residuals and lagged residuals
            r, _ = pearsonr(residuals[:-lag], residuals[lag:])
            acf_values[lag] = r if not np.isnan(r) else 0.0
        else:
            acf_values[lag] = 0.0
    
    return acf_values


def evaluate_residual_acf(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    max_acf_threshold: float = 0.35,
    max_lag: int = 7
) -> Dict:
    """
    Evaluate residual ACF and check against threshold.
    
    Args:
        y_true: True values
        y_pred: Predicted values
        max_acf_threshold: Maximum allowed lag-1 ACF (training fails if exceeded)
        max_lag: Maximum lag to compute
        
    Returns:
        Dictionary with ACF values and pass/fail status
    """
    residuals = y_true - y_pred
    
    acf_values = compute_residual_acf(residuals, max_lag=max_lag)
    
    lag_1_acf = acf_values.get(1, 0.0)
    lag_7_acf = acf_values.get(7, 0.0)
    
    passed = lag_1_acf <= max_acf_threshold
    
    logger.info("=" * 60)
    logger.info("RESIDUAL AUTOCORRELATION EVALUATION")
    logger.info("=" * 60)
    logger.info(f"   Lag-1 ACF: {lag_1_acf:.4f} (threshold: {max_acf_threshold:.4f})")
    logger.info(f"   Lag-7 ACF: {lag_7_acf:.4f}")
    
    for lag in range(2, min(8, max_lag + 1)):
        if lag != 7:
            logger.info(f"   Lag-{lag} ACF: {acf_values.get(lag, 0.0):.4f}")
    
    if passed:
        logger.info(f"   ✅ PASSED: Lag-1 ACF ({lag_1_acf:.4f}) <= threshold ({max_acf_threshold:.4f})")
    else:
        logger.error(f"   ❌ FAILED: Lag-1 ACF ({lag_1_acf:.4f}) > threshold ({max_acf_threshold:.4f})")
        logger.error("   Training should be stopped or model architecture changed")
    
    return {
        'acf_values': acf_values,
        'lag_1_acf': lag_1_acf,
        'lag_7_acf': lag_7_acf,
        'passed': passed,
        'max_acf_threshold': max_acf_threshold
    }

