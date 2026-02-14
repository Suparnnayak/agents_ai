"""
Error Features Module

Generates recursive error features from past prediction errors.
These features allow LightGBM to learn residual correction directly.

Features:
- prev_error_1, prev_error_2, prev_error_7
- rolling_error_mean_7, rolling_error_std_7
- error_momentum = error_t-1 - error_t-2
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from collections import defaultdict
from .utils import get_logger

logger = get_logger(__name__)


class ErrorFeatureGenerator:
    """
    Generates error features from past prediction errors.
    
    Maintains rolling error buffers per (hospital, horizon) combination.
    Updates buffers after each forecast batch.
    """
    
    def __init__(self, max_history: int = 30):
        """
        Initialize error feature generator.
        
        Args:
            max_history: Maximum number of past errors to store per (hospital, horizon)
        """
        self.max_history = max_history
        # Store error history: (hospital_id, horizon) -> list of errors
        self.error_history: Dict[Tuple[int, int], list] = defaultdict(list)
        self.is_initialized = False
    
    def update_errors(self,
                     hospital_ids: np.ndarray,
                     horizons: np.ndarray,
                     y_true: np.ndarray,
                     y_pred: np.ndarray) -> None:
        """
        Update error history with new predictions.
        
        Args:
            hospital_ids: Hospital IDs
            horizons: Forecast horizons (1-7)
            y_true: True values
            y_pred: Predicted values
        """
        errors = y_true - y_pred
        
        for i, (hosp_id, horizon) in enumerate(zip(hospital_ids, horizons)):
            key = (hosp_id, horizon)
            error = errors[i]
            
            # Add to history
            self.error_history[key].append(error)
            
            # Keep only last max_history errors
            if len(self.error_history[key]) > self.max_history:
                self.error_history[key] = self.error_history[key][-self.max_history:]
        
        self.is_initialized = True
    
    def get_error_features(self,
                           hospital_ids: np.ndarray,
                           horizons: np.ndarray) -> pd.DataFrame:
        """
        Generate error features for given (hospital, horizon) combinations.
        
        Args:
            hospital_ids: Hospital IDs
            horizons: Forecast horizons (1-7)
            
        Returns:
            DataFrame with error features:
            - prev_error_1, prev_error_2, prev_error_7
            - rolling_error_mean_7, rolling_error_std_7
            - error_momentum
        """
        n_samples = len(hospital_ids)
        
        # Initialize feature arrays
        prev_error_1 = np.zeros(n_samples)
        prev_error_2 = np.zeros(n_samples)
        prev_error_7 = np.zeros(n_samples)
        rolling_error_mean_7 = np.zeros(n_samples)
        rolling_error_std_7 = np.zeros(n_samples)
        error_momentum = np.zeros(n_samples)
        
        for i, (hosp_id, horizon) in enumerate(zip(hospital_ids, horizons)):
            key = (hosp_id, horizon)
            history = self.error_history.get(key, [])
            
            if len(history) >= 1:
                prev_error_1[i] = history[-1]
            if len(history) >= 2:
                prev_error_2[i] = history[-2]
                error_momentum[i] = history[-1] - history[-2]
            if len(history) >= 7:
                prev_error_7[i] = history[-7]
            
            # Rolling statistics over last 7 errors
            if len(history) >= 7:
                recent_7 = history[-7:]
                rolling_error_mean_7[i] = np.mean(recent_7)
                rolling_error_std_7[i] = np.std(recent_7) if len(recent_7) > 1 else 0.0
        
        # Also compute residual EMA (exponential moving average) with alpha=0.3
        residual_ema_7 = np.zeros(n_samples)
        for i, (hosp_id, horizon) in enumerate(zip(hospital_ids, horizons)):
            key = (hosp_id, horizon)
            history = self.error_history.get(key, [])
            if len(history) >= 7:
                # EMA with alpha=0.3 (more weight to recent errors)
                recent_7 = history[-7:]
                alpha = 0.3
                ema = recent_7[0]
                for val in recent_7[1:]:
                    ema = alpha * val + (1 - alpha) * ema
                residual_ema_7[i] = ema
        
        return pd.DataFrame({
            'prev_error_1': prev_error_1,
            'prev_error_2': prev_error_2,
            'prev_error_7': prev_error_7,
            'rolling_error_mean_7': rolling_error_mean_7,
            'rolling_error_std_7': rolling_error_std_7,
            'error_momentum': error_momentum,
            # Tree-integrated residual features (aliases for consistency)
            'residual_lag_1': prev_error_1,
            'residual_lag_7': prev_error_7,
            'residual_ema_7': residual_ema_7
        })
    
    def reset(self) -> None:
        """Reset error history."""
        self.error_history.clear()
        self.is_initialized = False


def create_error_features_from_cv(
    X: pd.DataFrame,
    y: pd.Series,
    dates: pd.Series,
    model,
    cv,
    hospital_col: str = 'hospital_id_enc',
    horizon_col: str = 'horizon'
) -> pd.DataFrame:
    """
    Create error features using out-of-fold predictions from cross-validation.
    
    This is used during training to generate error features without data leakage.
    
    Args:
        X: Features
        y: Targets
        dates: Dates
        model: Model class (not fitted)
        cv: Cross-validation splitter
        hospital_col: Column name for hospital ID
        horizon_col: Column name for horizon
        
    Returns:
        DataFrame with error features added
    """
    logger.info("=" * 60)
    logger.info("GENERATING ERROR FEATURES FROM OUT-OF-FOLD PREDICTIONS")
    logger.info("=" * 60)
    
    error_features = pd.DataFrame(index=X.index)
    error_features['prev_error_1'] = 0.0
    error_features['prev_error_2'] = 0.0
    error_features['prev_error_7'] = 0.0
    error_features['rolling_error_mean_7'] = 0.0
    error_features['rolling_error_std_7'] = 0.0
    error_features['error_momentum'] = 0.0
    # Tree-integrated residual features (aliases for consistency)
    error_features['residual_lag_1'] = 0.0
    error_features['residual_lag_7'] = 0.0
    error_features['residual_ema_7'] = 0.0
    
    # Get CV splits
    if hasattr(cv, 'split'):
        cv_splits = list(cv.split(X, y, dates=dates))
    else:
        cv_splits = list(cv.split(X, y, dates))
    
    # Error buffer per (hospital, horizon)
    error_buffers = defaultdict(list)
    
    for fold, (train_idx, val_idx) in enumerate(cv_splits):
        logger.info(f"   Fold {fold + 1}/{len(cv_splits)}: Generating OOF predictions...")
        
        X_train = X.iloc[train_idx]
        y_train = y.iloc[train_idx]
        X_val = X.iloc[val_idx]
        y_val = y.iloc[val_idx]
        
        # Train model on fold
        fold_model = model.__class__(**model.get_params() if hasattr(model, 'get_params') else {})
        fold_model.fit(X_train, y_train, X_val, y_val)
        
        # Get out-of-fold predictions
        y_pred_val = fold_model.predict(X_val)
        errors_val = y_val.values - y_pred_val
        
        # Get hospital and horizon for validation set
        hospital_ids_val = X_val[hospital_col].values if hospital_col in X_val.columns else None
        horizons_val = X_val[horizon_col].values if horizon_col in X_val.columns else None
        
        if hospital_ids_val is not None and horizons_val is not None:
            # Update error buffers
            for i, (hosp_id, horizon) in enumerate(zip(hospital_ids_val, horizons_val)):
                key = (hosp_id, horizon)
                error_buffers[key].append({
                    'error': errors_val[i],
                    'index': val_idx[i],
                    'date': dates.iloc[val_idx[i]] if dates is not None else None
                })
    
    # Sort errors by date for each (hospital, horizon)
    for key in error_buffers:
        error_buffers[key].sort(key=lambda x: x['date'] if x['date'] is not None else pd.Timestamp.min)
    
    # Generate features from error buffers
    for key, errors_list in error_buffers.items():
        hosp_id, horizon = key
        
        # Find rows matching this (hospital, horizon)
        mask = (X[hospital_col] == hosp_id) & (X[horizon_col] == horizon)
        indices = X[mask].index
        
        # Sort by date
        if dates is not None:
            date_order = dates.loc[indices].argsort()
            indices = indices[date_order]
        
        # Generate features for each row
        for idx in indices:
            # Find errors that occurred before this row's date
            row_date = dates.loc[idx] if dates is not None else None
            past_errors = [
                e['error'] for e in errors_list
                if e['index'] < idx and (row_date is None or e['date'] < row_date)
            ]
            
            if len(past_errors) >= 1:
                error_features.loc[idx, 'prev_error_1'] = past_errors[-1]
                error_features.loc[idx, 'residual_lag_1'] = past_errors[-1]
            if len(past_errors) >= 2:
                error_features.loc[idx, 'prev_error_2'] = past_errors[-2]
                error_features.loc[idx, 'error_momentum'] = past_errors[-1] - past_errors[-2]
            if len(past_errors) >= 7:
                error_features.loc[idx, 'prev_error_7'] = past_errors[-7]
                error_features.loc[idx, 'residual_lag_7'] = past_errors[-7]
                recent_7 = past_errors[-7:]
                error_features.loc[idx, 'rolling_error_mean_7'] = np.mean(recent_7)
                error_features.loc[idx, 'rolling_error_std_7'] = np.std(recent_7) if len(recent_7) > 1 else 0.0
                # Compute residual EMA (exponential moving average) with alpha=0.3
                alpha = 0.3
                ema = recent_7[0]
                for val in recent_7[1:]:
                    ema = alpha * val + (1 - alpha) * ema
                error_features.loc[idx, 'residual_ema_7'] = ema
    
    logger.info(f"   Generated error features for {len(error_features)} samples")
    
    return error_features

