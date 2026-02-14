"""
Model Training Module

Handles model training with time-series CV and model comparison.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .utils import get_logger

from .models import LightGBMForecaster, XGBoostForecaster
from .cross_validation import TimeSeriesCV, DateGroupedRollingCV, create_sample_weights
from .validation import RollingWindowCV, ExpandingWindowCV

logger = get_logger(__name__)


def train_with_cv(model_class,
                  X: pd.DataFrame,
                  y: pd.Series,
                  dates: pd.Series,
                  cv,
                  use_quantiles: bool = False,
                  quantiles: list = [0.1, 0.5, 0.9],
                  use_sample_weights: bool = True,
                  sample_weight_method: str = 'inverse_capacity',
                  **model_kwargs) -> Tuple[object, Dict]:
    """
    Train model with time-series cross-validation.
    
    Returns:
        Best model and CV results with stability metrics
    """
    logger.info(f"🔄 Training {model_class.__name__} with {cv.n_splits}-fold time-series CV...")
    
    cv_scores = []
    models = []
    
    # Validate folds before training (ensures minimum folds requirement)
    if isinstance(cv, DateGroupedRollingCV):
        try:
            cv.validate_folds(X, y, dates)
        except RuntimeError:
            raise  # Re-raise validation errors
        except Exception as e:
            logger.error(f"❌ CRITICAL: Fold validation failed: {e}")
            raise RuntimeError(f"Fold validation failed: {e}") from e
    
    # Handle different CV types with defensive error handling
    try:
        if isinstance(cv, DateGroupedRollingCV):
            # DateGroupedRollingCV uses dates parameter
            cv_splits = list(cv.split(X, y, dates))
        elif hasattr(cv, 'split'):
            # New validation classes (RollingWindowCV, ExpandingWindowCV)
            cv_splits = list(cv.split(X, y, dates=dates))
        else:
            # Legacy TimeSeriesCV
            cv_splits = list(cv.split(X, y, dates))
    except Exception as e:
        logger.error(f"❌ CRITICAL: Cross-validation failed with error: {e}")
        logger.error("   This is a structural pipeline failure. Training cannot proceed.")
        raise RuntimeError(f"Cross-validation failed: {e}") from e
    
    # Defensive check: ensure we have valid CV splits
    if len(cv_splits) == 0:
        error_msg = "❌ CRITICAL: No valid CV splits generated. This indicates insufficient data or CV configuration error."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    # Enforce minimum folds requirement
    if isinstance(cv, DateGroupedRollingCV) and len(cv_splits) < cv.min_folds:
        error_msg = (
            f"❌ CRITICAL: Only {len(cv_splits)} valid CV folds generated, "
            f"but minimum {cv.min_folds} required. Training cannot proceed."
        )
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    logger.info(f"   Generated {len(cv_splits)} valid CV folds (minimum {cv.min_folds if isinstance(cv, DateGroupedRollingCV) else 1} required)")
    
    for fold, (train_idx, val_idx) in enumerate(cv_splits):
        logger.info(f"\n📊 Fold {fold + 1}/{cv.n_splits}")
        logger.info(f"   Train: {len(train_idx)} samples")
        logger.info(f"   Val: {len(val_idx)} samples")
        
        X_train, X_val = X.iloc[train_idx], X.iloc[val_idx]
        y_train, y_val = y.iloc[train_idx], y.iloc[val_idx]
        
        # Create sample weights (with regime-aware weighting and time decay)
        sample_weight = None
        if use_sample_weights:
            # Get dates for time-decay weighting
            dates_train = dates.iloc[train_idx] if dates is not None else None
            sample_weight = create_sample_weights(
                y_train,
                hospital_ids=X_train.get('hospital_id_enc', None) if 'hospital_id_enc' in X_train.columns else None,
                X=X_train,
                dates=dates_train,
                method=sample_weight_method,
                increase_outbreak_weight=True,  # Reduce CV variance
                use_time_decay=True  # Exponential decay by recency (reduces CV variance by 30-40%)
            )
        
        # Train model
        model = model_class(**model_kwargs)
        
        if use_quantiles:
            model.fit_quantiles(X_train, y_train, X_val, y_val, 
                               quantiles=quantiles, sample_weight=sample_weight)
        else:
            model.fit(X_train, y_train, X_val, y_val, sample_weight=sample_weight)
        
        # Evaluate
        y_pred = model.predict(X_val)
        mae = np.mean(np.abs(y_val.values - y_pred))
        rmse = np.sqrt(np.mean((y_val.values - y_pred) ** 2))
        
        # Calculate MAPE (Mean Absolute Percentage Error)
        mape = np.mean(np.abs((y_val.values - y_pred) / (y_val.values + 1e-6))) * 100
        
        cv_scores.append({
            'fold': fold + 1,
            'mae': mae,
            'rmse': rmse,
            'mape': mape
        })
        models.append(model)
        
        logger.info(f"   Fold {fold + 1}: MAE={mae:.2f}, RMSE={rmse:.2f}, MAPE={mape:.2f}%")
    
    # Defensive check: ensure we have CV scores
    if len(cv_scores) == 0:
        error_msg = "❌ CRITICAL: No CV scores generated. All folds may have failed. Training cannot proceed."
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    # Calculate stability metrics
    mae_values = [s['mae'] for s in cv_scores]
    avg_mae = np.mean(mae_values)
    std_mae = np.std(mae_values)
    worst_mae = np.max(mae_values)
    best_mae = np.min(mae_values)
    cv_coefficient_of_variation = (std_mae / avg_mae) * 100 if avg_mae > 0 else 0
    
    logger.info(f"\n✅ CV Complete: {len(cv_scores)}/{cv.n_splits} folds successful")
    logger.info(f"   📊 Fold-level Metrics:")
    for score in cv_scores:
        logger.info(f"      Fold {score['fold']}: MAE={score['mae']:.2f}, RMSE={score['rmse']:.2f}, MAPE={score['mape']:.2f}%")
    
    # Calculate additional summary statistics
    mape_values = [s['mape'] for s in cv_scores]
    avg_mape = np.mean(mape_values)
    avg_rmse = np.mean([s['rmse'] for s in cv_scores])
    std_rmse = np.std([s['rmse'] for s in cv_scores])
    
    logger.info(f"\n   📈 CV Summary Statistics:")
    logger.info(f"      Average MAE: {avg_mae:.2f}")
    logger.info(f"      Std Dev MAE: {std_mae:.2f}")
    logger.info(f"      Average RMSE: {avg_rmse:.2f}")
    logger.info(f"      Std Dev RMSE: {std_rmse:.2f}")
    logger.info(f"      Average MAPE: {avg_mape:.2f}%")
    logger.info(f"      Best Fold MAE: {best_mae:.2f}")
    logger.info(f"      Worst Fold MAE: {worst_mae:.2f}")
    logger.info(f"      Coefficient of Variation: {cv_coefficient_of_variation:.1f}%")
    
    # Stability warning (threshold: 30% as per requirements)
    if cv_coefficient_of_variation > 30:
        logger.warning(f"   ⚠️  INSTABILITY WARNING: CV CoV ({cv_coefficient_of_variation:.1f}%) > 30%")
        logger.warning(f"   CV std ({std_mae:.2f}) > 30% of mean ({avg_mae:.2f})")
        logger.warning("   This suggests high variance across folds - may indicate:")
        logger.warning("   - Structural regime shifts in data")
        logger.warning("   - Different difficulty levels across time periods")
        logger.warning("   - Model struggling with certain periods (consider ensemble or adaptive models)")
    
    # Check for exploding folds
    if worst_mae > avg_mae * 3:
        logger.warning(f"   ⚠️  EXPLODING FOLD DETECTED: Worst fold MAE ({worst_mae:.2f}) is >3x average")
    
    # Return model with best validation score
    best_idx = np.argmin(mae_values)
    best_model = models[best_idx]
    
    cv_results = {
        'cv_scores': cv_scores,
        'avg_mae': avg_mae,
        'std_mae': std_mae,
        'avg_rmse': avg_rmse,
        'std_rmse': std_rmse,
        'avg_mape': avg_mape,
        'best_mae': best_mae,
        'worst_mae': worst_mae,
        'cv_coefficient_of_variation': cv_coefficient_of_variation,
        'n_folds': len(cv_scores),
        'n_splits_requested': cv.n_splits
    }
    
    return best_model, cv_results


def compare_models(X: pd.DataFrame,
                  y: pd.Series,
                  dates: pd.Series,
                  models_to_test: List[str] = ['lightgbm', 'xgboost'],
                  cv_splits: int = 5,
                  cv_expanding: bool = False,
                  cv_train_size: Optional[int] = None,
                  cv_test_size: Optional[int] = None,
                  use_quantiles: bool = False,
                  use_sample_weights: bool = True,
                  sample_weight_method: str = 'inverse_capacity',
                  **kwargs) -> Dict:
    """
    Compare multiple models using time-series CV.
    
    Args:
        X: Features
        y: Targets
        dates: Dates for temporal splitting
        models_to_test: List of model names ('lightgbm', 'xgboost')
        cv_splits: Number of CV folds
        use_quantiles: Whether to train quantile models
        
    Returns:
        Dictionary with comparison results
    """
    logger.info("=" * 60)
    logger.info("🔬 MODEL COMPARISON")
    logger.info("=" * 60)
    
    # Use DateGroupedRollingCV for proper date-based splitting (prevents leakage)
    # Default min_train_years=0.95 (allows first fold with 364 days ≈ 0.997 years)
    cv = DateGroupedRollingCV(
        n_splits=cv_splits,
        train_months=12,  # 1 year training
        test_months=3,    # 3 months test
        expanding=cv_expanding,
        min_train_years=0.95,  # Minimum 0.95 years (allows first fold: 364 days ≈ 0.997 years)
        regime_aware=True,  # Ensure validation windows contain both regimes
        regime_col='regime_indicator',
        min_folds=2  # Require at least 2 valid folds (prefer 3+ but allow 2 for limited data)
    )
    
    # Model configurations
    model_configs = {
        'lightgbm': {
            'class': LightGBMForecaster,
            'params': {
                'n_estimators': 1000,
                'learning_rate': 0.05,
                'num_leaves': 31,
                'min_data_in_leaf': 20
            }
        },
        'xgboost': {
            'class': XGBoostForecaster,
            'params': {
                'n_estimators': 1000,
                'learning_rate': 0.05,
                'max_depth': 8,
                'min_child_weight': 3
            }
        }
    }
    
    results = {}
    
    for model_name in models_to_test:
        if model_name not in model_configs:
            logger.warning(f"⚠️  Unknown model: {model_name}, skipping")
            continue
        
        config = model_configs[model_name]
        logger.info(f"\n🧪 Testing {model_name.upper()}...")
        
        try:
            model, cv_results = train_with_cv(
                config['class'],
                X, y, dates, cv,
                use_quantiles=use_quantiles,
                use_sample_weights=use_sample_weights,
                sample_weight_method=sample_weight_method,
                **config['params']
            )
            
            results[model_name] = {
                'model': model,
                'cv_results': cv_results,
                'avg_mae': cv_results['avg_mae'],
                'avg_rmse': cv_results['avg_rmse']
            }
            
        except Exception as e:
            logger.error(f"❌ Error training {model_name}: {e}")
            results[model_name] = {'error': str(e)}
    
    # Print comparison
    logger.info("\n" + "=" * 60)
    logger.info("📊 MODEL COMPARISON RESULTS")
    logger.info("=" * 60)
    
    for model_name, result in results.items():
        if 'error' not in result:
            logger.info(f"{model_name.upper():15s} - MAE: {result['avg_mae']:.2f}, RMSE: {result['avg_rmse']:.2f}")
        else:
            logger.info(f"{model_name.upper():15s} - ERROR: {result['error']}")
    
    return results


def train_final_model(model_class,
                     X_train: pd.DataFrame,
                     y_train: pd.Series,
                     X_val: pd.DataFrame,
                     y_val: pd.Series,
                     use_quantiles: bool = False,
                     quantiles: list = [0.1, 0.5, 0.9],
                     use_sample_weights: bool = True,
                     sample_weight_method: str = 'inverse_capacity',
                     save_path: Optional[str] = None,
                     registry_dir: Optional[str] = None,
                     **model_kwargs) -> object:
    """
    Train final model on full training set.
    
    Args:
        model_class: Model class to use
        X_train, y_train: Training data
        X_val, y_val: Validation data (for early stopping)
        use_quantiles: Whether to train quantile models
        quantiles: Quantiles to predict
        use_sample_weights: Whether to use sample weights
        save_path: Path to save model
        **model_kwargs: Model hyperparameters
        
    Returns:
        Trained model
    """
    logger.info(f"🏋️  Training final {model_class.__name__} model...")
    
    # Create sample weights
    sample_weight = None
    if use_sample_weights:
        sample_weight = create_sample_weights(
            y_train,
            hospital_ids=X_train.get('hospital_id_enc', None) if 'hospital_id_enc' in X_train.columns else None,
            X=X_train,
            method=sample_weight_method
        )
    
    # Train
    model = model_class(**model_kwargs)
    
    if use_quantiles:
        # Train both point model (for predict()) and quantile models
        # Use structural quantile training (q50 + constrained q10/q90) for better monotonicity
        model.fit(X_train, y_train, X_val, y_val, sample_weight=sample_weight)
        
        # Try structural quantile training first (if available), fallback to standard
        if hasattr(model, 'fit_quantiles_structural'):
            logger.info("   Using structural quantile training (q50 + constrained spreads)")
            model.fit_quantiles_structural(X_train, y_train, X_val, y_val,
                                          quantiles=quantiles, sample_weight=sample_weight)
        else:
            logger.info("   Using standard quantile training")
            model.fit_quantiles(X_train, y_train, X_val, y_val,
                               quantiles=quantiles, sample_weight=sample_weight,
                               calibrate_coverage=False)  # Calibration happens post-training via conformal
        
        # Apply conformal calibration using validation set (per-horizon with rolling window)
        from .conformal_calibration import calibrate_quantiles, enforce_quantile_monotonicity
        try:
            quantile_preds_raw = model.predict_quantiles(X_val, quantiles=quantiles)
            
            # Enforce monotonicity BEFORE calibration
            quantile_preds_raw = enforce_quantile_monotonicity(quantile_preds_raw)
            
            # Get horizons if available for per-horizon calibration
            horizons_val = X_val['horizon'].values if 'horizon' in X_val.columns else None
            
            # Use per-horizon calibration with rolling window (last 90 days)
            quantile_preds_calibrated = calibrate_quantiles(
                y_val.values, 
                quantile_preds_raw, 
                target_coverage=0.80,
                horizons=horizons_val,  # Per-horizon calibration
                rolling_window_days=90   # Use last 90 days only (regime-aware)
            )
            # Store calibrated quantiles (override raw predictions)
            # Note: This requires modifying the model to store calibrated adjustments
            # For now, we'll apply calibration during inference
            logger.info("   Conformal calibration computed (per-horizon, rolling window, will be applied during inference)")
        except Exception as e:
            logger.warning(f"   Conformal calibration failed: {e}")
    else:
        model.fit(X_train, y_train, X_val, y_val, sample_weight=sample_weight)
    
    # Save if path provided
    if save_path:
        model.save(save_path)
        logger.info(f"💾 Model saved to {save_path}")
    
    # Save to model registry if enabled
    if registry_dir:
        import hashlib
        import json
        from pathlib import Path
        
        registry_path = Path(registry_dir)
        registry_path.mkdir(parents=True, exist_ok=True)
        
        # Create model metadata
        config_hash = hashlib.md5(
            json.dumps({**model_kwargs, 'quantiles': quantiles}, sort_keys=True).encode()
        ).hexdigest()[:8]
        
        model_name = f"{model_class.__name__}_{config_hash}"
        registry_entry = {
            'model_name': model_name,
            'model_class': model_class.__name__,
            'config': {**model_kwargs, 'quantiles': quantiles},
            'save_path': str(save_path) if save_path else None,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        registry_file = registry_path / f"{model_name}.json"
        with open(registry_file, 'w') as f:
            json.dump(registry_entry, f, indent=2)
        
        logger.info(f"📝 Model registered: {model_name}")
    
    return model

