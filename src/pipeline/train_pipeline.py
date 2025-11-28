import os
import xgboost as xgb
import numpy as np
import pandas as pd
from sklearn.model_selection import TimeSeriesSplit
from src.components.data_ingestion import ingest_city, ingest_all_cities
from src.components.data_transformation import transform_for_xgb
from src.components.model_trainer import (
    train_xgb_median,
    train_lgb_quantile,
    train_xgb_quantile,
    train_spike_booster,
    train_extreme_spike_booster,
    save_trio,
    save_global_trio,
    save_spike_model,
)
from src.pipeline.evaluation import compute_metrics
from src.pipeline.logger import get_logger

logger = get_logger(__name__)


def get_monotonic_constraints(feature_names):
    """
    Define monotonic constraints for known relationships.
    AQI → admissions: increasing (higher AQI = more admissions)
    outbreak_index → admissions: increasing
    temp (extreme) → admissions: complex (handled by interactions)
    """
    constraints = {}
    
    for feat in feature_names:
        if 'aqi' in feat.lower() and 'above' not in feat.lower() and 'severity' not in feat.lower():
            # Base AQI features: increasing relationship
            constraints[feat] = 1
        elif feat == 'outbreak_index':
            constraints[feat] = 1
        elif 'aqi_above' in feat.lower() or 'aqi_severity' in feat.lower():
            # AQI threshold features: increasing
            constraints[feat] = 1
        elif 'aqi_respiratory' in feat.lower() or 'aqi_temp' in feat.lower():
            # AQI interactions: increasing
            constraints[feat] = 1
        # Note: temp, humidity, rainfall have complex relationships, so no constraints
    
    return constraints


def time_aware_split(X, y, df_full, train_ratio=0.85, ensure_temporal_order=True):
    """
    Perform time-aware train/validation split to prevent data leakage.
    
    Args:
        X: Feature matrix
        y: Target variable
        df_full: Full dataframe with date column
        train_ratio: Ratio of data for training
        ensure_temporal_order: Ensure data is sorted by date before splitting
    """
    if ensure_temporal_order and 'date' in df_full.columns:
        # Sort by date to ensure temporal order
        df_full = df_full.sort_values('date').reset_index(drop=True)
        sort_idx = df_full.index
        X = X.loc[sort_idx].reset_index(drop=True)
        y = y.loc[sort_idx].reset_index(drop=True)
        logger.info("📅 Data sorted by date for time-aware splitting")
    
    # Simple time-based split (no future data in training)
    split_idx = int(len(X) * train_ratio)
    
    X_train = X.iloc[:split_idx].copy()
    X_val = X.iloc[split_idx:].copy()
    y_train = y.iloc[:split_idx].copy()
    y_val = y.iloc[split_idx:].copy()
    
    logger.info(f"📊 Train/Val split: {len(X_train)}/{len(X_val)} samples ({train_ratio:.1%}/{1-train_ratio:.1%})")
    
    return X_train, X_val, y_train, y_val


def run_training_for_city(
    city: str,
    output_dir="models",
    use_optuna=False,  # Default False for faster training, set True for best accuracy
    optuna_trials=30,  # Reduced default for faster training
    use_time_series_cv=False,
    n_splits=3
):
    """
    Train all three models (q10, q50, q90) for a city.
    
    Args:
        city: City name
        output_dir: Directory to save models
        use_optuna: Whether to use Optuna for hyperparameter tuning
        optuna_trials: Number of Optuna trials
        use_time_series_cv: Whether to use time-series cross-validation
        n_splits: Number of splits for time-series CV
    
    Returns:
        Dictionary with metrics and model information
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Normalize city name (handle case variations)
    city_normalized = city.capitalize()  # Mumbai, Delhi, etc.
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🏥 Training models for city: {city_normalized}")
    logger.info(f"{'='*60}\n")
    
    # STEP 1 — Ingest raw data
    logger.info("📥 Step 1: Ingesting data...")
    df = ingest_city(city_normalized)
    
    # STEP 2 — Transform with enhanced features
    logger.info("🔧 Step 2: Transforming data with enhanced features...")
    X, y, scaler, df_full = transform_for_xgb(df, scale_features=False)  # Tree models don't need scaling
    
    # Get feature names for consistent ordering (CRITICAL for prediction)
    feature_names = X.columns.tolist()
    logger.info(f"   Using {len(feature_names)} features")
    logger.info(f"   Feature order: {feature_names[:5]}..." if len(feature_names) > 5 else f"   Features: {feature_names}")
    
    # STEP 3 — Time-aware split (CRITICAL: no data leakage)
    logger.info("✂️  Step 3: Performing time-aware train/validation split...")
    # Ensure data is sorted by date before splitting
    if 'date' in df_full.columns:
        sort_idx = df_full.sort_values('date').index
        X = X.loc[sort_idx].reset_index(drop=True)
        y = y.loc[sort_idx].reset_index(drop=True)
        df_full = df_full.loc[sort_idx].reset_index(drop=True)
    X_train, X_val, y_train, y_val = time_aware_split(X, y, df_full, train_ratio=0.85, ensure_temporal_order=True)
    
    # Get monotonic constraints
    monotonic_constraints = get_monotonic_constraints(feature_names)
    if monotonic_constraints:
        logger.info(f"📊 Monotonic constraints applied to {len(monotonic_constraints)} features")
    
    # Optional: Time-series cross-validation for model selection
    if use_time_series_cv:
        logger.info(f"🔄 Using time-series cross-validation (n_splits={n_splits})...")
        tscv = TimeSeriesSplit(n_splits=n_splits)
        cv_scores = []
        
        for fold, (train_idx, val_idx) in enumerate(tscv.split(X_train)):
            logger.info(f"   Fold {fold+1}/{n_splits}")
            X_train_fold = X_train.iloc[train_idx]
            X_val_fold = X_train.iloc[val_idx]
            y_train_fold = y_train.iloc[train_idx]
            y_val_fold = y_train.iloc[val_idx]
            
            # Quick training for CV (no Optuna to save time)
            model_cv = train_xgb_median(
                X_train_fold, y_train_fold, X_val_fold, y_val_fold,
                use_optuna=False,
                monotonic_constraints=monotonic_constraints
            )
            preds_cv = model_cv.predict(xgb.DMatrix(X_val_fold))
            mae_cv = np.mean(np.abs(y_val_fold - preds_cv))
            cv_scores.append(mae_cv)
            logger.info(f"   Fold {fold+1} MAE: {mae_cv:.4f}")
        
        logger.info(f"📊 CV MAE: {np.mean(cv_scores):.4f} ± {np.std(cv_scores):.4f}")
    
    # -------------------------------------------------------------------------
    # STEP 4 — Train all three models
    logger.info("\n🚀 Step 4: Training models...")
    
    # 1) Train XGBoost Median (q50)
    logger.info("\n   [1/3] Training XGBoost median (q50)...")
    model_xgb = train_xgb_median(
        X_train, y_train, X_val, y_val,
        use_optuna=use_optuna,
        n_trials=optuna_trials,
        monotonic_constraints=monotonic_constraints
    )
    
    # 2) Train LightGBM q10
    logger.info("\n   [2/3] Training LightGBM q10 (lower bound)...")
    model_q10 = train_lgb_quantile(
        X_train, y_train, X_val, y_val,
        quantile=0.1,
        use_optuna=use_optuna,
        n_trials=optuna_trials,
        monotonic_constraints=monotonic_constraints
    )
    
    # 3) Train LightGBM q90
    logger.info("\n   [3/3] Training LightGBM q90 (upper bound)...")
    model_q90 = train_lgb_quantile(
        X_train, y_train, X_val, y_val,
        quantile=0.9,
        use_optuna=use_optuna,
        n_trials=optuna_trials,
        monotonic_constraints=monotonic_constraints
    )
    
    # -------------------------------------------------------------------------
    # STEP 5 — Save models (organized by city)
    logger.info("\n💾 Step 5: Saving models...")
    city_lower = city_normalized.lower()
    save_trio(city_lower, model_xgb, model_q10, model_q90, output_dir)
    
    # -------------------------------------------------------------------------
    # STEP 6 — Evaluate all models
    logger.info("\n📊 Step 6: Evaluating models...")
    
    # Evaluate median model
    preds_median = model_xgb.predict(xgb.DMatrix(X_val))
    metrics_median = compute_metrics(y_val, preds_median)
    logger.info(f"\n   Median (q50) Model Metrics:")
    logger.info(f"   {metrics_median}")
    
    # Evaluate quantile models (apply conservative widening)
    preds_q10 = model_q10.predict(X_val) - 0.5
    preds_q90 = model_q90.predict(X_val) + 0.5
    preds_q10 = np.minimum(preds_q10, preds_q90 - 1e-6)
    
    # Calculate coverage (how often true value falls within q10-q90 range)
    coverage = np.mean((y_val >= preds_q10) & (y_val <= preds_q90))
    logger.info(f"\n   Quantile Coverage (q10-q90): {coverage:.2%}")
    
    results = {
        "city": city_normalized,
        "metrics_median": metrics_median,
        "coverage": coverage,
        "n_features": len(feature_names),
        "n_train": len(X_train),
        "n_val": len(X_val),
        "feature_names": feature_names  # CRITICAL: preserve feature order for prediction
    }
    
    logger.info(f"\n✅ Training completed for {city_normalized}!")
    logger.info(f"{'='*60}\n")
    
    return results


def train_all_cities(cities, output_dir="models", **kwargs):
    """
    Train models for all cities.
    
    Args:
        cities: List of city names
        output_dir: Directory to save models
        **kwargs: Additional arguments passed to run_training_for_city
    
    Returns:
        Dictionary with results for all cities
    """
    all_results = {}
    
    for city in cities:
        try:
            results = run_training_for_city(city, output_dir=output_dir, **kwargs)
            all_results[city] = results
        except Exception as e:
            logger.error(f"❌ Failed to train models for {city}: {e}")
            all_results[city] = {"error": str(e)}
    
    # Summary
    logger.info("\n" + "="*60)
    logger.info("📊 TRAINING SUMMARY")
    logger.info("="*60)
    
    for city, results in all_results.items():
        if "error" not in results:
            metrics = results.get("metrics_median", {})
            logger.info(f"\n{city}:")
            logger.info(f"  Accuracy: {metrics.get('Accuracy', 'N/A')}%")
            logger.info(f"  MAE: {metrics.get('MAE', 'N/A')}")
            logger.info(f"  RMSE: {metrics.get('RMSE', 'N/A')}")
            logger.info(f"  Coverage: {results.get('coverage', 'N/A'):.2%}")
        else:
            logger.info(f"\n{city}: ❌ Error - {results['error']}")
    
    return all_results


def run_training_global(
    output_dir="models",
    use_optuna=False,
    optuna_trials=30,
    cities=None,
    base_dir="generated_datasets_ml_ready/xgb"
):
    """
    Train global models (q10, q50, q90) using data from all cities combined.
    
    Args:
        output_dir: Directory to save models
        use_optuna: Whether to use Optuna for hyperparameter tuning
        optuna_trials: Number of Optuna trials
        cities: List of city names. If None, auto-detects from directory.
        base_dir: Base directory containing city CSV files
    
    Returns:
        Dictionary with metrics and model information
    """
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"\n{'='*60}")
    logger.info(f"🌍 Training GLOBAL models (all cities combined)")
    logger.info(f"{'='*60}\n")
    
    # STEP 1 — Ingest all cities
    logger.info("📥 Step 1: Ingesting data from all cities...")
    df = ingest_all_cities(base_dir=base_dir, cities=cities)
    
    # STEP 2 — Transform with enhanced features
    logger.info("🔧 Step 2: Transforming data with enhanced features...")
    X, y, scaler, df_full = transform_for_xgb(df, scale_features=False)
    
    # Get feature names for consistent ordering (CRITICAL for prediction)
    feature_names = X.columns.tolist()
    logger.info(f"   Using {len(feature_names)} features")
    logger.info(f"   Feature order: {feature_names[:5]}..." if len(feature_names) > 5 else f"   Features: {feature_names}")
    
    # STEP 3 — Time-aware split (CRITICAL: no data leakage)
    logger.info("✂️  Step 3: Performing time-aware train/validation split...")
    # Ensure data is sorted by date before splitting
    if 'date' in df_full.columns:
        sort_idx = df_full.sort_values('date').index
        X = X.loc[sort_idx].reset_index(drop=True)
        y = y.loc[sort_idx].reset_index(drop=True)
        df_full = df_full.loc[sort_idx].reset_index(drop=True)
    X_train, X_val, y_train, y_val = time_aware_split(X, y, df_full, train_ratio=0.85, ensure_temporal_order=True)
    
    # Get monotonic constraints
    monotonic_constraints = get_monotonic_constraints(feature_names)
    if monotonic_constraints:
        logger.info(f"📊 Monotonic constraints applied to {len(monotonic_constraints)} features")
    
    # -------------------------------------------------------------------------
    # STEP 4 — Train all three global models
    logger.info("\n🚀 Step 4: Training global models...")
    
    # 1) Train XGBoost q50 (median)
    logger.info("\n   [1/3] Training XGBoost q50 (median)...")
    model_q50 = train_xgb_quantile(
        X_train, y_train, X_val, y_val,
        alpha=0.5,
        n_estimators=600,
        monotonic_constraints=monotonic_constraints
    )
    preds_train_q50 = model_q50.predict(xgb.DMatrix(X_train))
    
    # 2) Train XGBoost q10 (lower bound)
    logger.info("\n   [2/3] Training XGBoost q10 (lower bound)...")
    model_q10 = train_xgb_quantile(
        X_train, y_train, X_val, y_val,
        alpha=0.1,
        n_estimators=600,
        monotonic_constraints=monotonic_constraints
    )
    
    # 3) Train XGBoost q90 (upper bound)
    logger.info("\n   [3/3] Training XGBoost q90 (upper bound)...")
    model_q90 = train_xgb_quantile(
        X_train, y_train, X_val, y_val,
        alpha=0.9,
        n_estimators=600,
        monotonic_constraints=monotonic_constraints
    )
    
    # Spike correction booster (on training set residuals)
    residuals = y_train - preds_train_q50
    threshold = np.percentile(y_train, 70)  # Lower threshold to catch more spikes
    logger.info(f"📈 Spike threshold (70th percentile): {threshold:.2f}")
    spike_mask = (y_train > threshold).to_numpy()
    logger.info(f"📊 Found {spike_mask.sum()} spike samples out of {len(spike_mask)} total")
    spike_model = train_spike_booster(X_train, residuals, spike_mask, y_train=y_train)
    
    # Second-stage extreme spike booster (top 1% of residuals)
    logger.info("\n🔥 Training second-stage EXTREME spike booster...")
    extreme_spike_model = train_extreme_spike_booster(X_train, residuals, y_train)
    
    # -------------------------------------------------------------------------
    # STEP 5 — Save global models
    logger.info("\n💾 Step 5: Saving global models...")
    save_global_trio(model_q50, model_q10, model_q90, output_dir)
    save_spike_model(spike_model, output_dir)
    if extreme_spike_model is not None:
        save_spike_model(extreme_spike_model, output_dir, name="global_q50_extreme_spike.json")
    
    # -------------------------------------------------------------------------
    # STEP 6 — Evaluate all models
    logger.info("\n📊 Step 6: Evaluating models...")
    
    # Evaluate median model
    preds_median = model_q50.predict(xgb.DMatrix(X_val))
    if spike_model is not None:
        preds_median += spike_model.predict(xgb.DMatrix(X_val))
    metrics_median = compute_metrics(y_val, preds_median)
    logger.info(f"\n   Median (q50) Model Metrics:")
    logger.info(f"   {metrics_median}")
    
    # Evaluate quantile models (optionally widen a bit)
    preds_q10 = model_q10.predict(xgb.DMatrix(X_val))
    preds_q90 = model_q90.predict(xgb.DMatrix(X_val))
    if spike_model is not None:
        adj = spike_model.predict(xgb.DMatrix(X_val))
        preds_q10 += adj
        preds_q90 += adj
    # Small widening to improve coverage
    preds_q10 = preds_q10 - 0.5
    preds_q90 = preds_q90 + 0.5
    preds_q10 = np.minimum(preds_q10, preds_q90 - 1e-6)
    
    # Calculate coverage (how often true value falls within q10-q90 range)
    coverage = np.mean((y_val >= preds_q10) & (y_val <= preds_q90))
    logger.info(f"\n   Quantile Coverage (q10-q90): {coverage:.2%}")
    
    results = {
        "metrics_median": metrics_median,
        "coverage": coverage,
        "n_features": len(feature_names),
        "n_train": len(X_train),
        "n_val": len(X_val),
        "n_cities": len(df['city'].unique()),
        "n_hospitals": df['hospital_id'].nunique(),
        "feature_names": feature_names  # CRITICAL: preserve feature order for prediction
    }
    
    logger.info(f"\n✅ Global training completed!")
    logger.info(f"   Trained on {results['n_cities']} cities, {results['n_hospitals']} hospitals")
    logger.info(f"   Training samples: {results['n_train']}, Validation samples: {results['n_val']}")
    logger.info(f"{'='*60}\n")
    
    return results
