"""
Tree-Integrated Error Features

Replaces ineffective AR residual layer with tree-integrated error features.
These features are computed from past predictions and included in training.

Features:
- prev_forecast_error: Previous forecast error (lag-1)
- rolling_forecast_error_7: Rolling mean of forecast errors (7-day window)
- error_momentum: Change in error (error_t-1 - error_t-2)
- error_volatility_14: Rolling std of forecast errors (14-day window)

CRITICAL: These must be computed strictly from past predictions to avoid leakage.
"""

import numpy as np
import pandas as pd
from typing import Optional
from forecast_system.utils import get_logger

logger = get_logger(__name__)


def create_tree_error_features_from_oof(
    X: pd.DataFrame,
    y: pd.Series,
    dates: pd.Series,
    model,
    cv,
    hospital_col: str = 'hospital_id_enc',
    horizon_col: str = 'horizon'
) -> pd.DataFrame:
    """
    Create tree-integrated error features using out-of-fold predictions from CV.
    
    This ensures no data leakage - error features are computed only from past predictions.
    
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
    logger.info("CREATING TREE-INTEGRATED ERROR FEATURES FROM OOF PREDICTIONS")
    logger.info("=" * 60)
    
    # Initialize error feature columns
    error_features = pd.DataFrame(index=X.index)
    error_features['prev_forecast_error'] = 0.0
    error_features['rolling_forecast_error_7'] = 0.0
    error_features['error_momentum'] = 0.0
    error_features['error_volatility_14'] = 0.0
    
    # Get CV splits
    if hasattr(cv, 'split'):
        cv_splits = list(cv.split(X, y, dates=dates))
    else:
        cv_splits = list(cv.split(X, y, dates))
    
    # Store OOF predictions and errors per (hospital, horizon, date)
    oof_predictions = {}
    
    for fold, (train_idx, val_idx) in enumerate(cv_splits):
        logger.info(f"   Fold {fold + 1}/{len(cv_splits)}: Generating OOF predictions...")
        
        X_train = X.iloc[train_idx]
        y_train = y.iloc[train_idx]
        X_val = X.iloc[val_idx]
        y_val = y.iloc[val_idx]
        dates_val = dates.iloc[val_idx]
        
        # Train model on fold
        fold_model = model.__class__(**model.get_params() if hasattr(model, 'get_params') else {})
        fold_model.fit(X_train, y_train, X_val, y_val)
        
        # Get out-of-fold predictions
        y_pred_val = fold_model.predict(X_val)
        errors_val = y_val.values - y_pred_val
        
        # Store OOF predictions with metadata
        hospital_ids_val = X_val[hospital_col].values if hospital_col in X_val.columns else None
        horizons_val = X_val[horizon_col].values if horizon_col in X_val.columns else None
        
        if hospital_ids_val is not None and horizons_val is not None:
            for i, idx in enumerate(val_idx):
                key = (hospital_ids_val[i], horizons_val[i], dates_val.iloc[i])
                oof_predictions[key] = {
                    'error': errors_val[i],
                    'index': idx,
                    'date': dates_val.iloc[i]
                }
    
    # Sort predictions by date for each (hospital, horizon)
    predictions_by_hosp_horizon = {}
    for key, pred_data in oof_predictions.items():
        hosp_id, horizon, date = key
        group_key = (hosp_id, horizon)
        if group_key not in predictions_by_hosp_horizon:
            predictions_by_hosp_horizon[group_key] = []
        predictions_by_hosp_horizon[group_key].append(pred_data)
    
    # Sort by date for each group
    for group_key in predictions_by_hosp_horizon:
        predictions_by_hosp_horizon[group_key].sort(key=lambda x: x['date'])
    
    # Generate error features for each row
    for idx in X.index:
        hosp_id = X.loc[idx, hospital_col] if hospital_col in X.columns else None
        horizon = X.loc[idx, horizon_col] if horizon_col in X.columns else None
        date = dates.loc[idx] if dates is not None else None
        
        if hosp_id is None or horizon is None or date is None:
            continue
        
        group_key = (hosp_id, horizon)
        if group_key not in predictions_by_hosp_horizon:
            continue
        
        # Get past errors (before current date)
        past_errors = [
            p['error'] for p in predictions_by_hosp_horizon[group_key]
            if p['date'] < date and p['index'] < idx
        ]
        
        if len(past_errors) >= 1:
            error_features.loc[idx, 'prev_forecast_error'] = past_errors[-1]
        
        if len(past_errors) >= 2:
            error_features.loc[idx, 'error_momentum'] = past_errors[-1] - past_errors[-2]
        
        if len(past_errors) >= 7:
            recent_7 = past_errors[-7:]
            error_features.loc[idx, 'rolling_forecast_error_7'] = np.mean(recent_7)
        
        if len(past_errors) >= 14:
            recent_14 = past_errors[-14:]
            error_features.loc[idx, 'error_volatility_14'] = np.std(recent_14) if len(recent_14) > 1 else 0.0
    
    logger.info(f"   Generated error features for {len(error_features)} samples")
    logger.info(f"   Feature statistics:")
    logger.info(f"      prev_forecast_error: mean={error_features['prev_forecast_error'].abs().mean():.3f}")
    logger.info(f"      rolling_forecast_error_7: mean={error_features['rolling_forecast_error_7'].abs().mean():.3f}")
    logger.info(f"      error_momentum: mean={error_features['error_momentum'].abs().mean():.3f}")
    logger.info(f"      error_volatility_14: mean={error_features['error_volatility_14'].mean():.3f}")
    
    return error_features

