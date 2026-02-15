"""
Quantile Utilities

Helper functions for quantile smoothing and monotonic enforcement.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional
from forecast_system.utils import get_logger

logger = get_logger(__name__)


def smooth_quantiles_across_horizons(
    quantile_preds: Dict[float, np.ndarray],
    horizons: np.ndarray,
    smoothing_alpha: float = 0.7,
    smoothing_horizons: List[int] = [5, 6, 7]
) -> Dict[float, np.ndarray]:
    """
    Smooth quantiles across horizons to reduce oscillation.
    
    For long horizons (5-7), apply smoothing:
    q_h = alpha * q_h + (1 - alpha) * q_(h-1)
    
    Args:
        quantile_preds: Dictionary mapping quantile -> predictions
        horizons: Forecast horizons (1-7) for each prediction
        smoothing_alpha: Smoothing factor (0.7 = 70% current, 30% previous)
        smoothing_horizons: Horizons to apply smoothing (default: [5, 6, 7])
        
    Returns:
        Smoothed quantile predictions
    """
    if len(smoothing_horizons) == 0:
        return quantile_preds
    
    smoothed = {}
    
    for q, preds in quantile_preds.items():
        smoothed_preds = preds.copy()
        
        # Sort by horizon for each hospital
        df = pd.DataFrame({
            'pred': preds,
            'horizon': horizons
        })
        
        # Apply smoothing for specified horizons
        for horizon in smoothing_horizons:
            if horizon < 2:
                continue  # Need previous horizon
            
            horizon_mask = horizons == horizon
            prev_horizon_mask = horizons == (horizon - 1)
            
            if horizon_mask.sum() > 0 and prev_horizon_mask.sum() > 0:
                # Get predictions for current and previous horizon
                # Note: This assumes predictions are ordered by hospital and horizon
                # In practice, you'd need to align by hospital_id
                # For now, we'll do a simple smoothing assuming sequential ordering
                
                # Find indices for current horizon
                current_indices = np.where(horizon_mask)[0]
                prev_indices = np.where(prev_horizon_mask)[0]
                
                # Simple smoothing: if indices are aligned (same hospital)
                # This is a simplified version - in production, align by hospital_id
                if len(current_indices) == len(prev_indices):
                    smoothed_preds[current_indices] = (
                        smoothing_alpha * smoothed_preds[current_indices] +
                        (1 - smoothing_alpha) * smoothed_preds[prev_indices]
                    )
        
        smoothed[q] = smoothed_preds
    
    logger.info(f"   Applied quantile smoothing (alpha={smoothing_alpha}) to horizons {smoothing_horizons}")
    
    return smoothed


def apply_hard_monotonic_enforcement(
    quantile_preds: Dict[float, np.ndarray]
) -> Dict[float, np.ndarray]:
    """
    Apply hard monotonic enforcement: q10 <= q50 <= q90.
    
    This is a fallback safety check, not the primary fix.
    
    Args:
        quantile_preds: Dictionary mapping quantile -> predictions
        
    Returns:
        Monotonically enforced quantile predictions
    """
    quantiles_sorted = sorted(quantile_preds.keys())
    
    if len(quantiles_sorted) < 2:
        return quantile_preds
    
    enforced = {}
    
    for q in quantiles_sorted:
        enforced[q] = quantile_preds[q].copy()
    
    # Enforce ordering
    for i in range(len(quantiles_sorted) - 1):
        q_low = quantiles_sorted[i]
        q_high = quantiles_sorted[i + 1]
        
        violations = np.sum(enforced[q_low] > enforced[q_high])
        if violations > 0:
            enforced[q_high] = np.maximum(enforced[q_high], enforced[q_low])
            logger.debug(f"   Corrected {violations} monotonicity violations: q{int(q_low*100)} > q{int(q_high*100)}")
    
    return enforced

