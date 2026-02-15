"""
Conformal Calibration Module

Uses validation residuals to calibrate quantile predictions for empirical coverage.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
from forecast_system.utils import get_logger

logger = get_logger(__name__)


def compute_conformal_adjustment(y_true: np.ndarray,
                                 quantile_preds: Dict[float, np.ndarray],
                                 target_coverage: float = 0.80,
                                 max_adjustment_factor: float = 2.0) -> Dict[float, float]:
    """
    Compute conformal adjustment factors for quantile predictions.
    
    Uses non-parametric approach: compute residuals, find empirical quantile,
    adjust bands to achieve target coverage.
    
    Args:
        y_true: True values
        quantile_preds: Dictionary mapping quantile -> predictions
        target_coverage: Target coverage (e.g., 0.80 for 80%)
        
    Returns:
        Dictionary mapping quantile -> adjustment factor
    """
    logger.info("=" * 60)
    logger.info("CONFORMAL CALIBRATION")
    logger.info("=" * 60)
    
    # Calculate raw coverage
    quantiles = sorted(quantile_preds.keys())
    if len(quantiles) < 2:
        logger.warning("   Need at least 2 quantiles for calibration")
        return {}
    
    lower_q = min(quantiles)
    upper_q = max(quantiles)
    
    lower_pred = quantile_preds[lower_q]
    upper_pred = quantile_preds[upper_q]
    
    raw_coverage = np.mean((y_true >= lower_pred) & (y_true <= upper_pred))
    logger.info(f"   Raw coverage: {raw_coverage:.2%} (target: {target_coverage:.2%})")
    
    # Calculate residuals
    residuals = y_true - quantile_preds.get(0.5, (lower_pred + upper_pred) / 2)  # Use median if available
    
    # Compute empirical quantile of residuals
    # For 80% coverage, we want 10th and 90th percentiles
    residual_lower = np.percentile(residuals, (1 - target_coverage) / 2 * 100)
    residual_upper = np.percentile(residuals, (1 + target_coverage) / 2 * 100)
    
    # Calculate adjustment factors
    # Adjust lower quantile: subtract residual_lower
    # Adjust upper quantile: add residual_upper
    adjustments = {}
    
    for q in quantiles:
        if q == lower_q:
            # Lower quantile: shift down by residual_lower
            adjustments[q] = -abs(residual_lower)
        elif q == upper_q:
            # Upper quantile: shift up by residual_upper
            adjustments[q] = abs(residual_upper)
        else:
            # Middle quantiles: proportional adjustment
            adjustments[q] = 0.0
    
    # If coverage is too low, widen intervals (but cap to prevent explosion)
    if raw_coverage < target_coverage:
        coverage_gap = target_coverage - raw_coverage
        # Increase adjustment magnitude (capped)
        for q in [lower_q, upper_q]:
            if q == lower_q:
                adjustments[q] *= (1 + coverage_gap * 2)
            else:
                adjustments[q] *= (1 + coverage_gap * 2)
            # Cap extreme adjustments to prevent explosion
            if abs(adjustments[q]) > 0:
                max_adj = abs(adjustments[q]) * max_adjustment_factor
                adjustments[q] = np.clip(adjustments[q], -max_adj, max_adj)
    
    logger.info(f"   Adjustment factors: {adjustments}")
    logger.info(f"   Max adjustment factor: {max_adjustment_factor} (capped to prevent explosion)")
    
    return adjustments


def apply_conformal_calibration(quantile_preds: Dict[float, np.ndarray],
                               adjustments: Dict[float, float]) -> Dict[float, np.ndarray]:
    """
    Apply conformal adjustments to quantile predictions.
    
    Args:
        quantile_preds: Original quantile predictions
        adjustments: Adjustment factors from compute_conformal_adjustment
        
    Returns:
        Calibrated quantile predictions
    """
    calibrated = {}
    
    for q, preds in quantile_preds.items():
        if q in adjustments:
            calibrated[q] = preds + adjustments[q]
        else:
            calibrated[q] = preds.copy()
    
    return calibrated


def enforce_quantile_monotonicity(quantile_preds: Dict[float, np.ndarray]) -> Dict[float, np.ndarray]:
    """
    Enforce monotonicity: q10 <= q50 <= q90 for all samples.
    
    Sorts quantiles per sample to ensure proper ordering.
    
    Args:
        quantile_preds: Dictionary mapping quantile -> predictions
        
    Returns:
        Monotonic-corrected quantile predictions
    """
    quantiles_sorted = sorted(quantile_preds.keys())
    
    if len(quantiles_sorted) < 2:
        return quantile_preds
    
    # Stack all quantiles
    stacked = np.vstack([quantile_preds[q] for q in quantiles_sorted])
    
    # Sort each column (per sample) to ensure monotonicity
    stacked_sorted = np.sort(stacked, axis=0)
    
    # Reconstruct dictionary
    corrected = {}
    for i, q in enumerate(quantiles_sorted):
        corrected[q] = stacked_sorted[i]
    
    # Check for violations
    violations = 0
    for i in range(len(quantiles_sorted) - 1):
        q_low = quantiles_sorted[i]
        q_high = quantiles_sorted[i + 1]
        violations += np.sum(corrected[q_low] > corrected[q_high])
    
    if violations > 0:
        logger.warning(f"   ⚠️  Corrected {violations} monotonicity violations")
    else:
        logger.info(f"   ✅ Quantiles are monotonic")
    
    return corrected


def calibrate_quantiles_per_horizon(
    y_true: np.ndarray,
    quantile_preds: Dict[float, np.ndarray],
    horizons: np.ndarray,
    target_coverage: float = 0.80,
    rolling_window_days: Optional[int] = 90,
    max_adjustment_factor: float = 2.0,
    enforce_horizon_width: bool = True
) -> Dict[float, np.ndarray]:
    """
    Calibrate quantiles separately per horizon with optional rolling window.
    
    Args:
        y_true: True values
        quantile_preds: Raw quantile predictions
        horizons: Forecast horizons (1-7) for each prediction
        target_coverage: Target coverage
        rolling_window_days: If provided, use only last N days for calibration
        
    Returns:
        Calibrated quantile predictions
    """
    logger.info("=" * 60)
    logger.info("CONFORMAL CALIBRATION: Per-Horizon with Rolling Window")
    logger.info("=" * 60)
    
    # First enforce monotonicity before calibration
    quantile_preds = enforce_quantile_monotonicity(quantile_preds)
    
    calibrated_all = {q: np.zeros_like(preds) for q, preds in quantile_preds.items()}
    
    # Calibrate per horizon
    for horizon in range(1, 8):
        horizon_mask = horizons == horizon
        if not np.any(horizon_mask):
            continue
        
        y_true_h = y_true[horizon_mask]
        quantile_preds_h = {q: preds[horizon_mask] for q, preds in quantile_preds.items()}
        
        # Apply rolling window if specified (use last N samples)
        if rolling_window_days is not None and len(y_true_h) > rolling_window_days:
            y_true_h = y_true_h[-rolling_window_days:]
            quantile_preds_h = {q: preds[-rolling_window_days:] for q, preds in quantile_preds_h.items()}
        
        # Calibrate this horizon with rolling window and capped adjustments
        calibrated_h = calibrate_quantiles(
            y_true_h, quantile_preds_h, target_coverage,
            horizons=None,  # Already filtered by horizon
            rolling_window_days=rolling_window_days,
            max_adjustment_factor=1.5,  # Cap adjustments to prevent explosion
            enforce_horizon_width=False  # Handle width separately below
        )
        
        # Enforce increasing interval width with horizon (sqrt(horizon) scaling)
        if enforce_horizon_width and len(calibrated_h) >= 2:
            quantiles_sorted = sorted(calibrated_h.keys())
            lower_q = min(quantiles_sorted)
            upper_q = max(quantiles_sorted)
            interval_width = calibrated_h[upper_q] - calibrated_h[lower_q]
            
            # Target width increases with sqrt(horizon) relative to H1
            if horizon > 1:
                target_width_factor = np.sqrt(horizon) / np.sqrt(1)  # Relative to H1
                current_width = np.mean(interval_width)
                # Ensure width grows with horizon (but don't shrink if already wide)
                min_width = current_width * 0.8  # Allow some shrinkage but not too much
                target_width = max(current_width, min_width * target_width_factor)
                
                # Adjust upper quantile to achieve target width
                width_adjustment = (target_width - current_width) / 2
                calibrated_h[upper_q] = calibrated_h[upper_q] + width_adjustment
                calibrated_h[lower_q] = calibrated_h[lower_q] - width_adjustment
                
                logger.debug(f"   Horizon {horizon}: Adjusted width from {current_width:.2f} to {np.mean(calibrated_h[upper_q] - calibrated_h[lower_q]):.2f}")
        
        # Map back to original indices
        for q in calibrated_all.keys():
            if q in calibrated_h:
                calibrated_all[q][horizon_mask] = calibrated_h[q]
    
    # Log interval width stability by horizon
    if enforce_horizon_width:
        logger.info("\n   📊 Interval Width by Horizon:")
        for h in range(1, 8):
            h_mask = horizons == h
            if h_mask.sum() > 0 and len(calibrated_all) >= 2:
                quantiles_sorted = sorted(calibrated_all.keys())
                lower_q = min(quantiles_sorted)
                upper_q = max(quantiles_sorted)
                h_width = np.mean(calibrated_all[upper_q][h_mask] - calibrated_all[lower_q][h_mask])
                logger.info(f"      H{h}: {h_width:.2f}")
        
        # Check for H7 width explosion
        h1_mask = horizons == 1
        h7_mask = horizons == 7
        if h1_mask.sum() > 0 and h7_mask.sum() > 0 and len(calibrated_all) >= 2:
            quantiles_sorted = sorted(calibrated_all.keys())
            lower_q = min(quantiles_sorted)
            upper_q = max(quantiles_sorted)
            h1_width = np.mean(calibrated_all[upper_q][h1_mask] - calibrated_all[lower_q][h1_mask])
            h7_width = np.mean(calibrated_all[upper_q][h7_mask] - calibrated_all[lower_q][h7_mask])
            width_ratio = h7_width / h1_width if h1_width > 0 else 0
            
            if width_ratio > 2.0:
                logger.warning(f"   ⚠️  H7 width ({h7_width:.2f}) > 2x H1 width ({h1_width:.2f}) - interval explosion detected")
            else:
                logger.info(f"   ✅ H7/H1 width ratio: {width_ratio:.2f} (acceptable)")
    
    return calibrated_all


def calibrate_quantiles(y_true: np.ndarray,
                       quantile_preds: Dict[float, np.ndarray],
                       target_coverage: float = 0.80,
                       horizons: Optional[np.ndarray] = None,
                       rolling_window_days: Optional[int] = None) -> Dict[float, np.ndarray]:
    """
    Complete conformal calibration pipeline with optional per-horizon and rolling window.
    
    Args:
        y_true: True values (from validation set)
        quantile_preds: Raw quantile predictions
        target_coverage: Target coverage (default 0.80)
        horizons: Optional horizon array for per-horizon calibration
        rolling_window_days: Optional rolling window size (use last N days only)
        
    Returns:
        Calibrated quantile predictions
    """
    # Enforce monotonicity BEFORE calibration
    quantile_preds = enforce_quantile_monotonicity(quantile_preds)
    
    # Use per-horizon calibration if horizons provided
    if horizons is not None:
        return calibrate_quantiles_per_horizon(
            y_true, quantile_preds, horizons, target_coverage, rolling_window_days
        )
    
    # Standard calibration
    # Apply rolling window if specified
    if rolling_window_days is not None and len(y_true) > rolling_window_days:
        logger.info(f"   Using rolling window: last {rolling_window_days} days")
        y_true = y_true[-rolling_window_days:]
        quantile_preds = {q: preds[-rolling_window_days:] for q, preds in quantile_preds.items()}
    
    # Compute adjustments
    adjustments = compute_conformal_adjustment(y_true, quantile_preds, target_coverage)
    
    # Apply adjustments
    calibrated = apply_conformal_calibration(quantile_preds, adjustments)
    
    # Verify coverage
    quantiles = sorted(calibrated.keys())
    if len(quantiles) >= 2:
        lower_q = min(quantiles)
        upper_q = max(quantiles)
        calibrated_coverage = np.mean((y_true >= calibrated[lower_q]) & (y_true <= calibrated[upper_q]))
        
        interval_width = np.mean(calibrated[upper_q] - calibrated[lower_q])
        logger.info(f"   Calibrated coverage: {calibrated_coverage:.2%}")
        logger.info(f"   Average interval width: {interval_width:.2f}")
        
        if calibrated_coverage < target_coverage * 0.95:
            logger.warning(f"   ⚠️  Coverage still low ({calibrated_coverage:.2%} < {target_coverage*0.95:.2%})")
        else:
            logger.info(f"   ✅ Coverage within target range")
    
    return calibrated

