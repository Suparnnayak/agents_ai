"""
Feature Group Management

Manages feature groups and applies group-based weights to reduce autoregressive dominance.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from .utils import get_logger

logger = get_logger(__name__)


def classify_features_by_group(X: pd.DataFrame) -> Dict[str, List[str]]:
    """
    Classify features into groups.
    
    Groups:
    - autoregressive: lags, ema, rolling features
    - exogenous: aqi, outbreak_index, temperature, etc.
    - regime: regime indicators, surge features
    - interaction: interaction features
    - temporal: temporal features (month, day_of_week, etc.)
    
    Args:
        X: Feature DataFrame
        
    Returns:
        Dictionary mapping group -> list of feature names
    """
    groups = {
        'autoregressive': [],
        'exogenous': [],
        'regime': [],
        'interaction': [],
        'temporal': []
    }
    
    for col in X.columns:
        # Autoregressive features
        if any(term in col.lower() for term in ['lag_', 'ema_', 'rolling_', 'admissions_diff', 'change_from', 'acceleration']):
            groups['autoregressive'].append(col)
        # Exogenous features
        elif any(term in col.lower() for term in ['aqi', 'outbreak_index', 'temperature', 'humidity', 'rainfall', 'wind_speed', 'mobility']):
            groups['exogenous'].append(col)
        # Regime features
        elif any(term in col.lower() for term in ['regime', 'surge', 'volatility_index']):
            groups['regime'].append(col)
        # Interaction features
        elif '_x_' in col or '_' in col and any(term in col for term in ['winter', 'elderly', 'weekend', 'temp', 'vol_regime', 'capacity']):
            groups['interaction'].append(col)
        # Temporal features
        elif any(term in col.lower() for term in ['month', 'day_of_week', 'week_of_year', 'quarter', 'day_of_year', 'is_weekend', 'sin', 'cos', 'trend']):
            groups['temporal'].append(col)
        # Default: put in autoregressive if it's a numeric feature
        elif pd.api.types.is_numeric_dtype(X[col]):
            groups['autoregressive'].append(col)
    
    # Log classification
    logger.info("=" * 60)
    logger.info("FEATURE GROUP CLASSIFICATION")
    logger.info("=" * 60)
    for group, features in groups.items():
        logger.info(f"   {group}: {len(features)} features")
        if len(features) > 0 and len(features) <= 10:
            logger.info(f"      {features}")
    
    return groups


def apply_feature_group_weights(
    X: pd.DataFrame,
    feature_group_weights: Dict[str, float],
    sample_weight: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Apply feature group weights to sample weights.
    
    Boosts samples where exogenous features are active during regime shifts.
    
    Args:
        X: Feature DataFrame
        feature_group_weights: Dictionary mapping group -> weight multiplier
        sample_weight: Existing sample weights (if any)
        
    Returns:
        Adjusted sample weights
    """
    if sample_weight is None:
        sample_weight = np.ones(len(X))
    
    groups = classify_features_by_group(X)
    
    # Compute group activity scores
    group_scores = {}
    for group, features in groups.items():
        if len(features) > 0:
            # Average absolute value of features in this group
            group_data = X[features].abs().mean(axis=1)
            group_scores[group] = group_data / (group_data.max() + 1e-6)  # Normalize 0-1
    
    # Apply weights
    adjusted_weights = sample_weight.copy()
    
    for group, weight_mult in feature_group_weights.items():
        if group in group_scores:
            # Boost samples where this group is active
            adjusted_weights *= (1.0 + (weight_mult - 1.0) * group_scores[group])
    
    # Normalize to maintain average weight
    adjusted_weights = adjusted_weights / (adjusted_weights.mean() + 1e-6) * sample_weight.mean()
    
    logger.info(f"   Applied feature group weights: mean={adjusted_weights.mean():.3f}, max={adjusted_weights.max():.3f}")
    
    return adjusted_weights


def compute_feature_group_importance(
    model,
    X: pd.DataFrame
) -> Dict[str, float]:
    """
    Compute feature importance by group.
    
    Args:
        model: Trained model with get_feature_importance method
        X: Feature DataFrame
        
    Returns:
        Dictionary mapping group -> total importance percentage
    """
    try:
        importance_df = model.get_feature_importance(X)
    except:
        logger.warning("   Could not compute feature importance")
        return {}
    
    groups = classify_features_by_group(X)
    group_importance = {}
    
    for group, features in groups.items():
        group_features = [f for f in features if f in importance_df['feature'].values]
        if len(group_features) > 0:
            group_importance[group] = importance_df[
                importance_df['feature'].isin(group_features)
            ]['importance_pct'].sum()
        else:
            group_importance[group] = 0.0
    
    logger.info("=" * 60)
    logger.info("FEATURE GROUP IMPORTANCE")
    logger.info("=" * 60)
    for group, importance in sorted(group_importance.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"   {group:20s}: {importance:6.2f}%")
    
    return group_importance


def analyze_autoregressive_dominance(
    model,
    X: pd.DataFrame,
    dominance_threshold: float = 0.9
) -> Dict:
    """
    Analyze autoregressive feature dominance.
    
    Args:
        model: Trained model
        X: Feature DataFrame
        dominance_threshold: Threshold for AR dominance (default 0.9 = 90%)
        
    Returns:
        Dictionary with dominance analysis
    """
    group_importance = compute_feature_group_importance(model, X)
    
    ar_importance = group_importance.get('autoregressive', 0)
    exogenous_importance = group_importance.get('exogenous', 0)
    
    dominance_ratio = ar_importance / (exogenous_importance + 1e-6) if exogenous_importance > 0 else np.inf
    
    is_dominant = ar_importance >= dominance_threshold * 100
    
    logger.info("=" * 60)
    logger.info("AUTOREGRESSIVE DOMINANCE ANALYSIS")
    logger.info("=" * 60)
    logger.info(f"   Autoregressive group: {ar_importance:.2f}%")
    logger.info(f"   Exogenous group: {exogenous_importance:.2f}%")
    logger.info(f"   Dominance ratio (AR/Exog): {dominance_ratio:.2f}")
    
    if is_dominant:
        logger.warning(f"   ⚠️  AUTOREGRESSIVE DOMINANCE: AR features ({ar_importance:.2f}%) >= {dominance_threshold*100:.1f}%")
        logger.warning("   Exogenous signals are underutilized")
    else:
        logger.info(f"   ✅ Balanced feature usage (AR < {dominance_threshold*100:.1f}%)")
    
    return {
        'group_importance': group_importance,
        'ar_importance': ar_importance,
        'exogenous_importance': exogenous_importance,
        'dominance_ratio': dominance_ratio,
        'is_dominant': is_dominant
    }


def stress_test_reduce_ar(
    model_class,
    X: pd.DataFrame,
    y: pd.Series,
    dates: pd.Series,
    cv,
    model_kwargs: dict,
    use_sample_weights: bool = True,
    sample_weight_method: str = 'inverse_capacity'
) -> Dict:
    """
    Diagnostic stress test: Temporarily drop lag_1 and ema_7, retrain, measure MAE change.
    
    If MAE increases < 30%: exogenous signals are meaningful.
    If MAE collapses: system is purely autoregressive and fragile.
    
    Args:
        model_class: Model class
        X: Features
        y: Targets
        dates: Dates
        cv: Cross-validation splitter
        model_kwargs: Model hyperparameters
        use_sample_weights: Whether to use sample weights
        sample_weight_method: Sample weight method
        
    Returns:
        Dictionary with stress test results
    """
    from .training import train_with_cv
    
    logger.info("=" * 70)
    logger.info("STRESS TEST: REDUCE AUTOREGRESSIVE FEATURES")
    logger.info("=" * 70)
    logger.info("   Temporarily dropping lag_1 and ema_7 to test exogenous signal strength")
    
    # Train baseline model (with all features)
    logger.info("\n   Step 1: Training baseline model (all features)...")
    baseline_model, baseline_cv = train_with_cv(
        model_class, X, y, dates, cv,
        use_sample_weights=use_sample_weights,
        sample_weight_method=sample_weight_method,
        **model_kwargs
    )
    baseline_mae = baseline_cv['avg_mae']
    logger.info(f"   Baseline MAE: {baseline_mae:.3f}")
    
    # Drop lag_1 and ema_7
    X_reduced = X.copy()
    features_dropped = []
    if 'lag_1' in X_reduced.columns:
        X_reduced = X_reduced.drop(columns=['lag_1'])
        features_dropped.append('lag_1')
    if 'ema_7' in X_reduced.columns:
        X_reduced = X_reduced.drop(columns=['ema_7'])
        features_dropped.append('ema_7')
    
    if len(features_dropped) == 0:
        logger.warning("   ⚠️  lag_1 and ema_7 not found in features - cannot perform stress test")
        return {
            'baseline_mae': baseline_mae,
            'reduced_mae': np.nan,
            'mae_increase_pct': np.nan,
            'exogenous_meaningful': None,
            'features_dropped': []
        }
    
    logger.info(f"   Dropped features: {features_dropped}")
    
    # Train reduced model
    logger.info("\n   Step 2: Training reduced model (without lag_1 and ema_7)...")
    reduced_model, reduced_cv = train_with_cv(
        model_class, X_reduced, y, dates, cv,
        use_sample_weights=use_sample_weights,
        sample_weight_method=sample_weight_method,
        **model_kwargs
    )
    reduced_mae = reduced_cv['avg_mae']
    logger.info(f"   Reduced MAE: {reduced_mae:.3f}")
    
    # Calculate MAE increase
    mae_increase_pct = (reduced_mae - baseline_mae) / baseline_mae if baseline_mae > 0 else np.inf
    
    logger.info("\n   Step 3: Analysis...")
    logger.info(f"   MAE increase: {mae_increase_pct*100:.1f}%")
    
    # Interpret results
    if mae_increase_pct < 0.10:  # < 10% increase
        exogenous_meaningful = False
        logger.warning("   ⚠️  DATASET TOO AUTOREGRESSIVE: MAE increase < 10%")
        logger.warning("   System is overly dependent on autoregressive features")
        logger.warning("   Exogenous signals are not meaningfully predictive")
    elif mae_increase_pct < 0.30:  # 10-30% increase
        exogenous_meaningful = True
        logger.info("   ✅ EXOGENOUS SIGNALS MEANINGFUL: MAE increase < 30%")
        logger.info("   System can leverage exogenous features effectively")
    else:  # > 30% increase
        exogenous_meaningful = True
        logger.warning("   ⚠️  SYSTEM FRAGILE: MAE increase > 30%")
        logger.warning("   System is highly dependent on autoregressive features")
        logger.warning("   Consider strengthening exogenous signal integration")
    
    return {
        'baseline_mae': baseline_mae,
        'reduced_mae': reduced_mae,
        'mae_increase_pct': mae_increase_pct,
        'exogenous_meaningful': exogenous_meaningful,
        'features_dropped': features_dropped
    }

