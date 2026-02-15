"""
Inference Module

Production-ready inference pipeline for making forecasts.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from pathlib import Path

from forecast_system.utils import get_logger

from forecast_system.feature_engineering import (
    engineer_features,
    create_lag_features,
    create_rolling_features,
    create_temporal_features,
    create_exogenous_lags,
    create_interaction_features,
    create_structural_shock_features,
    encode_categoricals
)
from forecast_system.models import LightGBMForecaster, XGBoostForecaster
from forecast_system.post_processing import post_process_predictions, format_forecast_output
from forecast_system.conformal_calibration import enforce_quantile_monotonicity

logger = get_logger(__name__)


def prepare_inference_data(df: pd.DataFrame, 
                          last_date: pd.Timestamp,
                          horizons: List[int] = [1, 2, 3, 4, 5, 6, 7]) -> pd.DataFrame:
    """
    Prepare data for inference (forecasting future dates).
    
    Args:
        df: Historical data with all features
        last_date: Last date in historical data
        horizons: List of horizons to forecast
        
    Returns:
        DataFrame ready for model prediction
    """
    logger.info(f"🔮 Preparing inference data for horizons {horizons}...")
    
    # Get the last row for each hospital
    last_rows = df.groupby('hospital_id').tail(1).copy()
    
    # Create future dates
    inference_rows = []
    
    for _, row in last_rows.iterrows():
        for horizon in horizons:
            future_date = last_date + pd.Timedelta(days=horizon)
            
            new_row = row.copy()
            new_row['date'] = future_date
            new_row['horizon'] = horizon
            
            # Update temporal features for future date
            new_row['month'] = future_date.month
            new_row['week_of_year'] = future_date.isocalendar().week
            new_row['quarter'] = future_date.quarter
            new_row['day_of_year'] = future_date.timetuple().tm_yday
            new_row['is_weekend'] = 1 if future_date.weekday() >= 5 else 0
            
            # Cyclical encoding
            new_row['month_sin'] = np.sin(2 * np.pi * future_date.month / 12)
            new_row['month_cos'] = np.cos(2 * np.pi * future_date.month / 12)
            new_row['day_of_year_sin'] = np.sin(2 * np.pi * new_row['day_of_year'] / 365.25)
            new_row['day_of_year_cos'] = np.cos(2 * np.pi * new_row['day_of_year'] / 365.25)
            
            inference_rows.append(new_row)
    
    inference_df = pd.DataFrame(inference_rows)
    
    logger.info(f"   Created {len(inference_df)} inference rows")
    
    return inference_df


def forecast(model,
            historical_df: pd.DataFrame,
            horizons: List[int] = [1, 2, 3, 4, 5, 6, 7],
            use_quantiles: bool = False,
            quantiles: List[float] = [0.1, 0.5, 0.9],
            hospital_ids: Optional[List] = None,
            future_exogenous: Optional[pd.DataFrame] = None,
            apply_post_processing: bool = True) -> pd.DataFrame:
    """
    Make forecasts for future horizons.
    
    Args:
        model: Trained forecasting model (can be a single model, PerHorizonForecaster, or dict of per-horizon models)
        historical_df: Historical data with features
        horizons: List of horizons to forecast
        use_quantiles: Whether to return quantile predictions
        quantiles: Quantiles to predict
        
    Returns:
        DataFrame with forecasts
    """
    logger.info("🔮 Generating forecasts...")
    
    # Defensive check: detect if model is a dict of per-horizon models
    is_per_horizon_dict = isinstance(model, dict)
    
    if is_per_horizon_dict:
        # Check if it's a metadata dict (with paths) or direct model dict
        if 'models_by_horizon_paths' in model:
            raise ValueError(
                "Model file contains metadata with paths. "
                "Use PerHorizonForecaster.load() to load the model properly."
            )
        # Validate it's a dict of models
        if not all(hasattr(m, 'predict') or hasattr(m, 'predict_quantiles') for m in model.values() if m is not None):
            raise ValueError("Expected per-horizon model dict with models that have predict/predict_quantiles methods")
        logger.info(f"   Detected per-horizon model dict with horizons: {sorted(model.keys())}")
    
    # CRITICAL: Engineer features on historical data before inference
    # The model expects all features (lags, rolling stats, encodings, etc.)
    logger.info("🔧 Engineering features on historical data...")
    historical_df_engineered = historical_df.copy()
    
    # Apply all feature engineering steps (same as training)
    historical_df_engineered = create_lag_features(historical_df_engineered)
    historical_df_engineered = create_rolling_features(historical_df_engineered)
    historical_df_engineered = create_temporal_features(historical_df_engineered)
    historical_df_engineered = create_exogenous_lags(historical_df_engineered)
    historical_df_engineered = create_interaction_features(historical_df_engineered)
    historical_df_engineered = create_structural_shock_features(historical_df_engineered)
    historical_df_engineered = encode_categoricals(historical_df_engineered)
    
    logger.info(f"   Engineered features: {historical_df_engineered.shape[1]} columns")
    
    # Get last date
    last_date = historical_df_engineered['date'].max()
    
    # Prepare inference data (now with all features)
    inference_df = prepare_inference_data(historical_df_engineered, last_date, horizons)
    
    # Add horizon-specific features (created during training horizon stacking)
    if 'horizon' in inference_df.columns:
        inference_df['horizon_squared'] = inference_df['horizon'] ** 2
        # horizon_vol_interaction = horizon * volatility_index (if available)
        if 'volatility_index' in inference_df.columns:
            inference_df['horizon_vol_interaction'] = inference_df['horizon'] * inference_df['volatility_index']
        else:
            inference_df['horizon_vol_interaction'] = 0
        logger.info("   Added horizon-specific features: horizon_squared, horizon_vol_interaction")
    
    # Add regime indicators if missing (created during training)
    if 'regime_indicator' not in inference_df.columns:
        # Create regime indicator based on outbreak_index threshold
        if 'outbreak_index' in inference_df.columns:
            inference_df['regime_indicator'] = (inference_df['outbreak_index'] > 70.0).astype(int)
            logger.info("   Added regime_indicator based on outbreak_index > 70")
        else:
            inference_df['regime_indicator'] = 0
    
    if 'high_vol_regime' not in inference_df.columns:
        # Create high volatility regime based on rolling_std_7
        if 'rolling_std_7' in inference_df.columns and 'lag_1' in inference_df.columns:
            # High vol if std > 20% of mean
            mean_proxy = inference_df['lag_1'].fillna(0)
            std_threshold = mean_proxy * 0.2
            inference_df['high_vol_regime'] = (inference_df['rolling_std_7'] > std_threshold).astype(int)
            inference_df['high_vol_regime'] = inference_df['high_vol_regime'].fillna(0)
            logger.info("   Added high_vol_regime based on rolling_std_7")
        else:
            inference_df['high_vol_regime'] = 0
    
    # Add missing rolling_mean_30 if needed (some features depend on it)
    if 'rolling_mean_30' not in inference_df.columns:
        if 'admissions' in historical_df_engineered.columns:
            # Compute rolling mean from historical data
            rolling_mean_30 = historical_df_engineered.groupby('hospital_id')['admissions'].transform(
                lambda x: x.rolling(window=30, min_periods=1).mean()
            )
            # Get last value for each hospital
            last_rolling_mean = historical_df_engineered.groupby('hospital_id')['admissions'].transform(
                lambda x: x.rolling(window=30, min_periods=1).mean().iloc[-1] if len(x) > 0 else 0
            )
            # Map to inference_df
            hospital_to_mean = historical_df_engineered.groupby('hospital_id')['admissions'].apply(
                lambda x: x.rolling(window=30, min_periods=1).mean().iloc[-1] if len(x) > 0 else 0
            ).to_dict()
            inference_df['rolling_mean_30'] = inference_df['hospital_id'].map(hospital_to_mean).fillna(0)
            logger.info("   Added rolling_mean_30 from historical data")
        else:
            inference_df['rolling_mean_30'] = 0
    
    # Select feature columns (EXACT SAME as training - from feature_engineering.py)
    feature_cols = [
        # Lags (expanded to reduce autocorrelation and CV variance)
        'lag_1', 'lag_2', 'lag_3', 'lag_5', 'lag_7', 'lag_14', 'lag_21', 'lag_30', 'lag_60', 'lag_90',
        # First difference
        'admissions_diff_1',
        # Recursive features (reduce residual autocorrelation)
        'change_from_week_ago', 'acceleration',
        # Rolling (std and mean for stability)
        'rolling_std_7', 'rolling_std_14', 'rolling_std_30',
        'rolling_mean_30',
        # EMA and slope
        'ema_7', 'rolling_slope_7',
        # Month one-hot (regime-aware, reduces CV variance)
        'month_1', 'month_2', 'month_3', 'month_4', 'month_5', 'month_6',
        'month_7', 'month_8', 'month_9', 'month_10', 'month_11', 'month_12',
        # Regime indicators
        'regime_indicator', 'high_vol_regime',
        # Horizon-specific features (helps model learn uncertainty grows nonlinearly)
        'horizon_squared', 'horizon_vol_interaction',
        # Encoded
        'hospital_id_enc', 'season_enc',
        # Temporal
        'month', 'week_of_year', 'quarter', 'day_of_year', 'is_weekend', 'day_of_week',
        'month_sin', 'month_cos', 'day_of_year_sin', 'day_of_year_cos',
        'day_of_week_sin', 'day_of_week_cos',
        # Fourier terms
        'yearly_sin_1', 'yearly_cos_1', 'yearly_sin_2', 'yearly_cos_2', 'yearly_sin_3', 'yearly_cos_3',
        'weekly_sin_1', 'weekly_cos_1', 'weekly_sin_2', 'weekly_cos_2',
        # Weather (if available)
        'temperature', 'humidity', 'rainfall', 'wind_speed', 'aqi',
        # Exogenous lags (if created)
        'aqi_lag_1', 'aqi_lag_7', 'outbreak_index_lag_1', 'outbreak_index_lag_7',
        'temperature_lag_1', 'temperature_lag_7',
        # Other
        'outbreak_index', 'mobility_index',
        'population', 'population_density', 'elderly_ratio',
        'hospital_capacity', 'icu_capacity',
        # Interactions (if created)
        'outbreak_winter', 'temp_elderly', 'mobility_weekend', 'aqi_temp', 'aqi_winter',
        # Nonlinear exogenous interactions (tree models need interaction triggers)
        'outbreak_vol_regime', 'outbreak_capacity', 'aqi_elderly',
        # Exogenous trend momentum (rate-of-change features)
        'outbreak_change_7', 'aqi_change_7',
        # Structural shock features (surge detection)
        'outbreak_acceleration', 'aqi_acceleration', 'admissions_acceleration_7', 'volatility_index',
        # Normalized features
        'aqi_normalized', 'temperature_normalized', 'outbreak_index_normalized',
        # Horizon (CRITICAL - must be last to match training order)
        'horizon'
    ]
    
    # Select only features that exist in inference_df (some may be missing if data doesn't have them)
    available_features = [col for col in feature_cols if col in inference_df.columns]
    logger.info(f"   Selected {len(available_features)} features from {len(feature_cols)} expected features")
    
    # Warn if we're missing many features
    missing_features = set(feature_cols) - set(available_features)
    if missing_features:
        logger.warning(f"   Missing {len(missing_features)} features: {sorted(list(missing_features))[:15])}")
        # Try to add missing features as zeros (model might expect them)
        for feat in missing_features:
            if feat not in inference_df.columns:
                inference_df[feat] = 0
                available_features.append(feat)
        logger.info(f"   Added {len(missing_features)} missing features as zeros. Total features: {len(available_features)}")
    
    # Ensure we have all features in the correct order
    X_inference = inference_df[feature_cols].copy().fillna(0)  # Use feature_cols order, fill missing with 0
    logger.info(f"   Final feature matrix shape: {X_inference.shape} (expected ~95 features)")
    
    # Filter by hospital_ids if provided
    if hospital_ids is not None:
        inference_df = inference_df[inference_df['hospital_id'].isin(hospital_ids)].copy()
        # FIX: Use .loc for row indexing, not column indexing
        X_inference = X_inference.loc[inference_df.index].copy()
        logger.info(f"   Filtered to {len(inference_df)} rows for {len(hospital_ids)} hospitals")
    
    # Override exogenous variables if future_exogenous provided
    if future_exogenous is not None:
        for col in future_exogenous.columns:
            if col in inference_df.columns:
                inference_df[col] = future_exogenous[col].values
                # Update feature if it's in X_inference
                if col in X_inference.columns:
                    X_inference[col] = future_exogenous[col].values
        logger.info("   Applied future exogenous scenario")
    
    # Make predictions - handle per-horizon dict vs single model
    if is_per_horizon_dict:
        # Per-horizon model dict: iterate over horizons
        all_point_preds = []
        all_quantile_preds = {q: [] for q in quantiles} if use_quantiles else None
        prediction_indices = []
        
        for horizon in horizons:
            if horizon not in model:
                logger.warning(f"   Horizon {horizon} not found in model dict, skipping")
                continue
            
            model_h = model[horizon]
            if model_h is None:
                logger.warning(f"   Model for horizon {horizon} is None, skipping")
                continue
            
            # Select rows for this horizon
            horizon_mask = inference_df['horizon'] == horizon
            if horizon_mask.sum() == 0:
                continue
            
            inference_df_h = inference_df[horizon_mask].copy()
            X_inference_h = X_inference.loc[inference_df_h.index].copy()
            
            # Remove horizon column if present (some models don't expect it)
            if 'horizon' in X_inference_h.columns:
                X_inference_h = X_inference_h.drop(columns=['horizon'])
            
            # Make predictions for this horizon
            if use_quantiles:
                quantile_preds_h = model_h.predict_quantiles(X_inference_h, quantiles=quantiles)
                point_preds_h = quantile_preds_h.get(0.5, model_h.predict(X_inference_h))
                
                # Store predictions with their original indices
                for i, idx in enumerate(inference_df_h.index):
                    prediction_indices.append(idx)
                    all_point_preds.append(point_preds_h[i])
                    
                    # Store quantile predictions with same index
                    for q in quantiles:
                        if q in quantile_preds_h:
                            all_quantile_preds[q].append((idx, quantile_preds_h[q][i]))
            else:
                point_preds_h = model_h.predict(X_inference_h)
                for i, idx in enumerate(inference_df_h.index):
                    prediction_indices.append(idx)
                    all_point_preds.append(point_preds_h[i])
            
            logger.info(f"   Horizon {horizon}: Generated {len(point_preds_h)} predictions")
        
        # Sort predictions by original index to maintain order
        if prediction_indices:
            # Sort by index to maintain DataFrame row order
            sorted_order = sorted(range(len(prediction_indices)), key=lambda i: prediction_indices[i])
            sorted_indices = [prediction_indices[i] for i in sorted_order]
            point_preds = np.array([all_point_preds[i] for i in sorted_order])
            
            if use_quantiles and all_quantile_preds:
                # Sort quantile predictions using same order as point predictions
                quantile_preds = {}
                # Create index-to-prediction dicts for each quantile
                for q in quantiles:
                    if all_quantile_preds[q]:
                        q_dict = {idx: pred for idx, pred in all_quantile_preds[q]}
                        # Use same sorted order as point predictions
                        quantile_preds[q] = np.array([q_dict[idx] for idx in sorted_indices])
                    else:
                        quantile_preds[q] = np.array([])
            else:
                quantile_preds = None
            
            # Reorder inference_df to match sorted predictions
            inference_df = inference_df.loc[sorted_indices].reset_index(drop=True)
        else:
            raise ValueError("No predictions generated for any horizon")
            
    else:
        # Single model (or PerHorizonForecaster wrapper)
        if use_quantiles:
            quantile_preds = model.predict_quantiles(X_inference, quantiles=quantiles)
            point_preds = quantile_preds.get(0.5, model.predict(X_inference))  # Use median as point estimate
        else:
            point_preds = model.predict(X_inference)
            quantile_preds = None
    
    # Post-process predictions
    if apply_post_processing:
        post_processed = post_process_predictions(
            point_preds,
            inference_df,
            use_quantiles=use_quantiles,
            quantile_preds=quantile_preds
        )
        
        forecast_df = format_forecast_output(
            inference_df[['hospital_id', 'date', 'horizon']].copy(),
            post_processed,
            include_quantiles=use_quantiles
        )
    else:
        # Create forecast DataFrame without post-processing
        forecast_df = inference_df[['hospital_id', 'date', 'horizon']].copy()
        forecast_df['forecast'] = point_preds
        if use_quantiles and quantile_preds:
            for q, preds in quantile_preds.items():
                forecast_df[f'forecast_q{int(q*100)}'] = preds
    
    logger.info(f"✅ Generated forecasts for {len(forecast_df)} rows")
    
    return forecast_df


def forecast_to_json(forecast_df: pd.DataFrame) -> Dict:
    """
    Convert forecast DataFrame to JSON-ready format.
    
    Args:
        forecast_df: Forecast DataFrame from forecast()
        
    Returns:
        Dictionary ready for JSON serialization
    """
    result = {
        'forecasts': []
    }
    
    for _, row in forecast_df.iterrows():
        forecast_entry = {
            'hospital_id': str(row['hospital_id']),
            'date': str(row['date']),
            'horizon': int(row['horizon']),
            'forecast': float(row['forecast'])
        }
        
        # Add quantiles if present
        quantile_cols = [col for col in forecast_df.columns if col.startswith('forecast_q')]
        if quantile_cols:
            forecast_entry['quantiles'] = {}
            for col in quantile_cols:
                q_level = int(col.replace('forecast_q', ''))
                forecast_entry['quantiles'][q_level] = float(row[col])
        
        # Add utilization and surge flag if present
        if 'utilization' in forecast_df.columns:
            forecast_entry['utilization'] = float(row['utilization'])
        if 'surge_flag' in forecast_df.columns:
            forecast_entry['surge_flag'] = bool(row['surge_flag'])
        
        result['forecasts'].append(forecast_entry)
    
    return result

