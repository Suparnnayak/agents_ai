"""
Regime-Aware Training Module

Implements regime-aware model training:
- Separate models for normal vs surge regimes
- Regime interaction features
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple, Callable
from .utils import get_logger

logger = get_logger(__name__)


def create_regime_indicator(
    df: pd.DataFrame,
    outbreak_col: str = 'outbreak_index',
    threshold: float = 70.0
) -> pd.Series:
    """
    Create binary regime indicator based on outbreak_index.
    
    Args:
        df: DataFrame with outbreak data
        outbreak_col: Column name for outbreak index
        threshold: Threshold for surge regime
        
    Returns:
        Binary series: 1 = surge regime, 0 = normal regime
    """
    if outbreak_col not in df.columns:
        logger.warning(f"   Column '{outbreak_col}' not found, using normal regime for all")
        return pd.Series(0, index=df.index)
    
    regime = (df[outbreak_col] > threshold).astype(int)
    surge_pct = regime.mean() * 100
    
    logger.info(f"   Regime indicator: {surge_pct:.1f}% surge, {100-surge_pct:.1f}% normal")
    
    return regime


def create_enhanced_regime_features(
    df: pd.DataFrame,
    outbreak_col: str = 'outbreak_index',
    threshold: float = 70.0
) -> pd.DataFrame:
    """
    Create enhanced regime features for better robustness.
    
    Features:
    - surge_intensity: Continuous measure (0-1) of surge strength
    - regime_duration: Days since surge start (per hospital)
    - regime_transition_flag: Binary flag for regime transitions
    
    Args:
        df: DataFrame with outbreak data
        outbreak_col: Column name for outbreak index
        threshold: Threshold for surge regime
        
    Returns:
        DataFrame with added regime features
    """
    df = df.copy()
    
    logger.info("🔧 Creating enhanced regime features...")
    
    if outbreak_col not in df.columns:
        logger.warning(f"   Column '{outbreak_col}' not found, skipping enhanced regime features")
        df['surge_intensity'] = 0.0
        df['regime_duration'] = 0
        df['regime_transition_flag'] = 0
        return df
    
    # Surge intensity (continuous, normalized 0-1)
    # Normalize outbreak_index to 0-1 range based on threshold
    max_outbreak = df[outbreak_col].max()
    if max_outbreak > threshold:
        df['surge_intensity'] = np.clip(
            (df[outbreak_col] - threshold) / (max_outbreak - threshold + 1e-6),
            0.0, 1.0
        )
    else:
        df['surge_intensity'] = 0.0
    
    # Regime duration (days since surge start, per hospital)
    df = df.sort_values(['hospital_id', 'date']).reset_index(drop=True)
    df['regime_duration'] = 0
    
    for hospital_id, group in df.groupby('hospital_id'):
        group = group.sort_values('date').reset_index(drop=True)
        in_surge = False
        duration = 0
        
        for idx, row in group.iterrows():
            is_surge = row[outbreak_col] > threshold
            
            if is_surge:
                if not in_surge:
                    # Surge just started
                    duration = 1
                    in_surge = True
                else:
                    # Continue surge
                    duration += 1
            else:
                if in_surge:
                    # Surge ended
                    in_surge = False
                    duration = 0
                else:
                    duration = 0
            
            df.loc[group.index[idx], 'regime_duration'] = duration
    
    # Regime transition flag (1 if regime changed from previous day)
    df['regime_indicator'] = (df[outbreak_col] > threshold).astype(int)
    df['regime_transition_flag'] = (
        df.groupby('hospital_id')['regime_indicator'].transform(
            lambda x: (x != x.shift(1)).astype(int)
        )
    ).fillna(0)
    
    logger.info("   ✅ Enhanced regime features created:")
    logger.info(f"      - surge_intensity: mean={df['surge_intensity'].mean():.3f}, max={df['surge_intensity'].max():.3f}")
    logger.info(f"      - regime_duration: mean={df['regime_duration'].mean():.1f} days, max={df['regime_duration'].max()} days")
    logger.info(f"      - regime_transition_flag: {df['regime_transition_flag'].sum()} transitions")
    
    return df


def create_dynamic_regime_weights(
    df: pd.DataFrame,
    base_weight: float = 1.0,
    surge_intensity_col: str = 'surge_intensity',
    max_weight: float = 2.0
) -> pd.Series:
    """
    Create dynamic sample weights based on surge intensity.
    
    weight = base_weight * (1 + 0.5 * surge_intensity)
    Capped at max_weight to avoid instability.
    
    Args:
        df: DataFrame with surge_intensity
        base_weight: Base weight
        surge_intensity_col: Column name for surge intensity
        max_weight: Maximum allowed weight
        
    Returns:
        Series of weights
    """
    if surge_intensity_col not in df.columns:
        logger.warning(f"   Column '{surge_intensity_col}' not found, using base weight")
        return pd.Series(base_weight, index=df.index)
    
    weights = base_weight * (1.0 + 0.5 * df[surge_intensity_col])
    weights = np.clip(weights, base_weight, max_weight)
    
    logger.info(f"   Dynamic regime weights: mean={weights.mean():.3f}, max={weights.max():.3f}")
    
    return weights


def train_regime_separate_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_val: pd.DataFrame,
    y_val: pd.Series,
    train_model_fn: Callable,
    regime_col: str = 'regime_indicator'
) -> Dict[int, object]:
    """
    Train separate models for each regime.
    
    Args:
        X_train: Training features
        y_train: Training targets
        X_val: Validation features
        y_val: Validation targets
        train_model_fn: Function to train model (takes X, y, X_val, y_val)
        regime_col: Column name for regime indicator
        
    Returns:
        Dictionary mapping regime (0 or 1) -> trained model
    """
    logger.info("=" * 60)
    logger.info("REGIME-AWARE TRAINING: Separate Models")
    logger.info("=" * 60)
    
    if regime_col not in X_train.columns:
        logger.warning(f"   Regime column '{regime_col}' not found, training single model")
        return {0: train_model_fn(X_train, y_train, X_val, y_val)}
    
    models = {}
    
    for regime in [0, 1]:
        # Filter by regime
        train_mask = X_train[regime_col] == regime
        val_mask = X_val[regime_col] == regime
        
        if train_mask.sum() == 0:
            logger.warning(f"   No training data for regime {regime}, skipping")
            continue
        
        X_train_regime = X_train[train_mask].copy()
        y_train_regime = y_train[train_mask].copy()
        X_val_regime = X_val[val_mask].copy() if val_mask.sum() > 0 else X_train_regime.iloc[:min(100, len(X_train_regime))].copy()
        y_val_regime = y_val[val_mask].copy() if val_mask.sum() > 0 else y_train_regime.iloc[:min(100, len(y_train_regime))].copy()
        
        # Remove regime column before training (to avoid leakage)
        if regime_col in X_train_regime.columns:
            X_train_regime = X_train_regime.drop(columns=[regime_col])
        if regime_col in X_val_regime.columns:
            X_val_regime = X_val_regime.drop(columns=[regime_col])
        
        logger.info(f"   Regime {regime}: Training on {len(X_train_regime)} samples")
        
        try:
            model = train_model_fn(X_train_regime, y_train_regime, X_val_regime, y_val_regime)
            models[regime] = model
            logger.info(f"   ✅ Regime {regime} model trained")
        except Exception as e:
            logger.error(f"   ❌ Failed to train regime {regime} model: {e}")
    
    return models


def predict_with_regime_models(
    models: Dict[int, object],
    X: pd.DataFrame,
    regime_col: str = 'regime_indicator'
) -> np.ndarray:
    """
    Make predictions using regime-specific models.
    
    Args:
        models: Dictionary mapping regime -> model
        X: Features for prediction
        regime_col: Column name for regime indicator
        
    Returns:
        Predictions
    """
    if regime_col not in X.columns:
        # Fallback to regime 0 model or single model
        if 0 in models:
            return models[0].predict(X.drop(columns=[regime_col]) if regime_col in X.columns else X)
        else:
            raise ValueError("No regime model available")
    
    predictions = np.zeros(len(X))
    
    for regime in [0, 1]:
        if regime not in models:
            continue
        
        regime_mask = X[regime_col] == regime
        if not regime_mask.any():
            continue
        
        X_regime = X[regime_mask].copy()
        if regime_col in X_regime.columns:
            X_regime = X_regime.drop(columns=[regime_col])
        
        preds_regime = models[regime].predict(X_regime)
        predictions[regime_mask] = preds_regime
    
    return predictions


def add_regime_interaction_features(
    df: pd.DataFrame,
    regime_col: str = 'regime_indicator',
    feature_cols: Optional[list] = None
) -> pd.DataFrame:
    """
    Add regime interaction features.
    
    Creates: feature × regime_indicator for key features.
    
    Args:
        df: DataFrame with features and regime
        regime_col: Column name for regime indicator
        feature_cols: Features to interact with regime (if None, uses common features)
        
    Returns:
        DataFrame with added interaction features
    """
    if regime_col not in df.columns:
        return df
    
    df = df.copy()
    
    if feature_cols is None:
        # Default: interact with key features
        feature_cols = ['outbreak_index', 'aqi', 'temperature', 'rolling_std_7', 'ema_7']
        feature_cols = [col for col in feature_cols if col in df.columns]
    
    for feature in feature_cols:
        if feature in df.columns:
            interaction_col = f"{feature}_x_regime"
            df[interaction_col] = df[feature] * df[regime_col]
            logger.debug(f"   Added interaction: {interaction_col}")
    
    return df

