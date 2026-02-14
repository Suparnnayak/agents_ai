"""
Post-Processing Module

Applies constraints and corrections to model predictions:
- Capacity cap enforcement
- Non-negative clipping
- Quantile monotonic correction
- Surge flag detection
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from .utils import get_logger

logger = get_logger(__name__)


def enforce_capacity_cap(predictions: np.ndarray,
                         capacity: np.ndarray,
                         max_utilization: float = 1.2) -> np.ndarray:
    """
    Enforce capacity constraints on predictions.
    
    Args:
        predictions: Raw predictions
        capacity: Hospital capacity values
        max_utilization: Maximum allowed utilization (default 1.2 = 120%)
        
    Returns:
        Capped predictions
    """
    max_admissions = capacity * max_utilization
    capped = np.minimum(predictions, max_admissions)
    
    n_capped = np.sum(capped < predictions)
    if n_capped > 0:
        logger.info(f"   📊 Capped {n_capped} predictions to {max_utilization*100:.0f}% capacity")
    
    return capped


def clip_non_negative(predictions: np.ndarray) -> np.ndarray:
    """
    Clip predictions to be non-negative.
    
    Args:
        predictions: Raw predictions
        
    Returns:
        Non-negative predictions
    """
    clipped = np.maximum(predictions, 0)
    
    n_clipped = np.sum(clipped > predictions)
    if n_clipped > 0:
        logger.info(f"   📊 Clipped {n_clipped} negative predictions to 0")
    
    return clipped


def correct_quantile_monotonicity(quantile_preds: Dict[float, np.ndarray]) -> Dict[float, np.ndarray]:
    """
    Ensure quantile predictions are monotonically increasing.
    
    For each sample, ensure: q10 <= q50 <= q90
    
    Args:
        quantile_preds: Dictionary mapping quantile -> predictions
        
    Returns:
        Corrected quantile predictions
    """
    quantiles = sorted(quantile_preds.keys())
    corrected = {}
    
    # Start with lowest quantile
    corrected[quantiles[0]] = quantile_preds[quantiles[0]].copy()
    
    # Ensure each quantile is >= previous
    for i in range(1, len(quantiles)):
        prev_q = quantiles[i-1]
        curr_q = quantiles[i]
        
        prev_preds = corrected[prev_q]
        curr_preds = quantile_preds[curr_q].copy()
        
        # Enforce monotonicity
        curr_preds = np.maximum(curr_preds, prev_preds)
        corrected[curr_q] = curr_preds
        
        n_corrected = np.sum(curr_preds > quantile_preds[curr_q])
        if n_corrected > 0:
            logger.info(f"   📊 Corrected {n_corrected} samples for quantile {curr_q} monotonicity")
    
    return corrected


def detect_surge(predictions: np.ndarray,
                capacity: np.ndarray,
                surge_threshold: float = 0.9) -> np.ndarray:
    """
    Detect surge conditions (high utilization).
    
    Args:
        predictions: Predicted admissions
        capacity: Hospital capacity
        surge_threshold: Utilization threshold for surge (default 0.9 = 90%)
        
    Returns:
        Binary array: 1 if surge, 0 otherwise
    """
    utilization = predictions / capacity
    surge_flags = (utilization >= surge_threshold).astype(int)
    
    n_surges = np.sum(surge_flags)
    if n_surges > 0:
        logger.info(f"   🚨 Detected {n_surges} surge conditions (utilization >= {surge_threshold*100:.0f}%)")
    
    return surge_flags


def post_process_predictions(predictions: np.ndarray,
                            df: pd.DataFrame,
                            capacity_col: str = 'hospital_capacity',
                            use_quantiles: bool = False,
                            quantile_preds: Optional[Dict[float, np.ndarray]] = None,
                            max_utilization: float = 1.2,
                            surge_threshold: float = 0.9) -> Dict:
    """
    Complete post-processing pipeline.
    
    Args:
        predictions: Point predictions
        df: DataFrame with capacity and other metadata
        capacity_col: Name of capacity column
        use_quantiles: Whether quantile predictions are provided
        quantile_preds: Dictionary of quantile predictions
        max_utilization: Maximum allowed utilization
        surge_threshold: Utilization threshold for surge detection
        
    Returns:
        Dictionary with processed predictions and metadata
    """
    logger.info("🔧 Post-processing predictions...")
    
    # Get capacity
    if capacity_col not in df.columns:
        logger.warning(f"⚠️  Capacity column '{capacity_col}' not found, skipping capacity constraints")
        capacity = np.full(len(predictions), np.inf)  # No constraint
    else:
        capacity = df[capacity_col].values
        capacity = np.where(capacity == 0, 1, capacity)  # Avoid division by zero
    
    # Process point predictions
    processed_point = predictions.copy()
    processed_point = clip_non_negative(processed_point)
    processed_point = enforce_capacity_cap(processed_point, capacity, max_utilization)
    
    # Process quantile predictions
    processed_quantiles = None
    if use_quantiles and quantile_preds is not None:
        processed_quantiles = {}
        
        for q, preds in quantile_preds.items():
            preds = clip_non_negative(preds)
            preds = enforce_capacity_cap(preds, capacity, max_utilization)
            processed_quantiles[q] = preds
        
        # Correct monotonicity
        processed_quantiles = correct_quantile_monotonicity(processed_quantiles)
    
    # Detect surges
    surge_flags = detect_surge(processed_point, capacity, surge_threshold)
    
    # Calculate utilization
    utilization = processed_point / capacity
    
    result = {
        'point_predictions': processed_point,
        'quantile_predictions': processed_quantiles,
        'surge_flags': surge_flags,
        'utilization': utilization,
        'capacity': capacity
    }
    
    logger.info("✅ Post-processing complete")
    
    return result


def format_forecast_output(forecast_df: pd.DataFrame,
                          post_processed: Dict,
                          include_quantiles: bool = True) -> pd.DataFrame:
    """
    Format post-processed predictions into clean forecast DataFrame.
    
    Args:
        forecast_df: Original forecast DataFrame with metadata
        post_processed: Output from post_process_predictions
        include_quantiles: Whether to include quantile columns
        
    Returns:
        Formatted DataFrame ready for output
    """
    output_df = forecast_df.copy()
    
    # Add point prediction
    output_df['forecast'] = post_processed['point_predictions']
    output_df['utilization'] = post_processed['utilization']
    output_df['surge_flag'] = post_processed['surge_flags']
    
    # Add quantiles if available
    if include_quantiles and post_processed['quantile_predictions'] is not None:
        for q, preds in post_processed['quantile_predictions'].items():
            output_df[f'forecast_q{int(q*100)}'] = preds
    
    return output_df

