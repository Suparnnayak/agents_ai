"""
Rolling Retraining Module

Implements sliding window retraining strategy for robustness to structural shocks.
Trains on recent window (e.g., 24 months) and retrains every N days.
"""

import numpy as np
import pandas as pd
from typing import List, Tuple, Optional, Callable
from pathlib import Path
from .utils import get_logger

logger = get_logger(__name__)


def rolling_train(
    df: pd.DataFrame,
    train_model_fn: Callable,
    window_months: int = 24,
    retrain_every_days: int = 30,
    date_col: str = 'date',
    min_train_samples: int = 1000
) -> List[Tuple[pd.Timestamp, object]]:
    """
    Perform rolling retraining with sliding window.
    
    Args:
        df: Full dataset with date column
        train_model_fn: Function that takes (X_train, y_train, X_val, y_val) and returns trained model
        window_months: Training window size in months (default 24)
        retrain_every_days: Retrain frequency in days (default 30)
        date_col: Name of date column
        min_train_samples: Minimum samples required for training
        
    Returns:
        List of (retrain_date, model) tuples
    """
    logger.info("=" * 70)
    logger.info("🔄 ROLLING RETRAINING: Sliding Window Strategy")
    logger.info("=" * 70)
    
    # Ensure date column is datetime
    if not pd.api.types.is_datetime64_any_dtype(df[date_col]):
        df[date_col] = pd.to_datetime(df[date_col])
    
    df = df.sort_values(date_col).reset_index(drop=True)
    
    # Get unique dates
    unique_dates = pd.Series(df[date_col].unique()).sort_values()
    
    # Determine retrain points (every N days)
    retrain_points = []
    current_date = unique_dates.min()
    max_date = unique_dates.max()
    
    while current_date <= max_date:
        retrain_points.append(current_date)
        current_date = current_date + pd.Timedelta(days=retrain_every_days)
    
    logger.info(f"   Training window: {window_months} months")
    logger.info(f"   Retrain frequency: {retrain_every_days} days")
    logger.info(f"   Total retrain points: {len(retrain_points)}")
    logger.info(f"   Date range: {unique_dates.min().date()} to {unique_dates.max().date()}")
    
    models = []
    
    for i, retrain_date in enumerate(retrain_points):
        logger.info(f"\n   📅 Retrain Point {i+1}/{len(retrain_points)}: {retrain_date.date()}")
        
        # Calculate training window
        train_start = retrain_date - pd.DateOffset(months=window_months)
        
        # Get training data (up to retrain_date, not including it)
        train_mask = (df[date_col] >= train_start) & (df[date_col] < retrain_date)
        train_data = df[train_mask].copy()
        
        if len(train_data) < min_train_samples:
            logger.warning(f"      ⚠️  Insufficient training data: {len(train_data)} < {min_train_samples}, skipping")
            continue
        
        # Get validation data (last 30 days of training window)
        val_start = retrain_date - pd.Timedelta(days=30)
        val_mask = (df[date_col] >= val_start) & (df[date_col] < retrain_date)
        val_data = df[val_mask].copy()
        
        logger.info(f"      Train: {len(train_data)} samples ({train_data[date_col].min().date()} to {train_data[date_col].max().date()})")
        logger.info(f"      Val:   {len(val_data)} samples ({val_data[date_col].min().date() if len(val_data) > 0 else 'N/A'} to {val_data[date_col].max().date() if len(val_data) > 0 else 'N/A'})")
        
        try:
            # Train model
            model = train_model_fn(train_data, val_data)
            models.append((retrain_date, model))
            logger.info(f"      ✅ Model trained successfully")
        except Exception as e:
            logger.error(f"      ❌ Training failed: {e}")
            continue
    
    logger.info(f"\n   ✅ Rolling retraining complete: {len(models)} models trained")
    
    return models


def get_model_for_date(
    models: List[Tuple[pd.Timestamp, object]],
    target_date: pd.Timestamp
) -> Optional[object]:
    """
    Get the most recent model for a given date.
    
    Args:
        models: List of (retrain_date, model) tuples (sorted by date)
        target_date: Date to get model for
        
    Returns:
        Most recent model before or on target_date, or None
    """
    if not models:
        return None
    
    # Find most recent model that was trained before or on target_date
    valid_models = [(date, model) for date, model in models if date <= target_date]
    
    if not valid_models:
        # Use earliest model if target_date is before all retrain dates
        return models[0][1]
    
    # Return most recent model
    return max(valid_models, key=lambda x: x[0])[1]

