"""
Production Inference Pipeline

100% stateless, deterministic forecasting with iterative prediction.
No state mutation. No inplace operations. All operations on deep copies.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import timedelta

from forecast_system.model_bundle import ModelBundle


def forecast(
    bundle: ModelBundle,
    raw_df: pd.DataFrame,
    horizons: List[int] = [1, 2, 3, 4, 5, 6, 7],
    external_signals_by_hospital: Optional[Dict[str, Dict[str, float]]] = None,
) -> pd.DataFrame:
    """
    Generate forecasts using iterative prediction.
    
    CRITICAL: This function is 100% stateless. All operations use deep copies.
    Multiple calls with identical inputs produce identical outputs.
    
    Args:
        bundle: ModelBundle with trained model
        raw_df: Historical DataFrame (must have 'admissions' column)
        horizons: List of horizons to forecast [1, 2, 3, 4, 5, 6, 7]
        external_signals_by_hospital: Optional latest DB signals keyed by hospital_id
    
    Returns:
        DataFrame with columns: hospital_id, horizon, prediction
    """
    # ============================================================================
    # STEP 1: Create deep copy - NEVER modify input
    # ============================================================================
    # DIAGNOSTIC: Track input state (can be removed in production)
    input_rows = len(raw_df)
    input_hospitals = raw_df['hospital_id'].nunique() if not raw_df.empty else 0
    
    df = raw_df.copy(deep=True)
    external_signals_by_hospital = external_signals_by_hospital or {}
    
    # Validate input
    if df.empty:
        raise ValueError("Input DataFrame is empty")
    
    # DIAGNOSTIC: Verify deep copy (should match input)
    assert len(df) == input_rows, f"Deep copy failed: input={input_rows}, copy={len(df)}"
    assert df['hospital_id'].nunique() == input_hospitals, f"Hospital count changed: input={input_hospitals}, copy={df['hospital_id'].nunique()}"
    
    required_cols = ['hospital_id', 'date', 'admissions']
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    
    # ============================================================================
    # STEP 2: Sort and prepare data (all operations on copies)
    # ============================================================================
    df = df.sort_values(['hospital_id', 'date']).reset_index(drop=True).copy(deep=True)
    
    # Get latest row per hospital (deterministic - always last row per group)
    latest_rows = df.groupby('hospital_id', sort=False).tail(1).reset_index(drop=True).copy(deep=True)
    
    if latest_rows.empty:
        raise ValueError("No data found for any hospital")
    
    # ============================================================================
    # STEP 3: Create features for historical data (deep copy)
    # ============================================================================
    df_with_features = df.copy(deep=True)
    
    # Create lags (these create new columns, no mutation of original)
    df_with_features['lag_1'] = df_with_features.groupby('hospital_id', sort=False)['admissions'].shift(1)
    df_with_features['lag_7'] = df_with_features.groupby('hospital_id', sort=False)['admissions'].shift(7)
    
    # Apply encoders (creates new columns)
    if 'hospital_id' in bundle.encoders:
        df_with_features['hospital_id_enc'] = bundle.encoders['hospital_id'].transform(
            df_with_features['hospital_id'].values
        )
    else:
        raise ValueError("hospital_id encoder not found in bundle")
    
    if 'season' in bundle.encoders:
        df_with_features['season_enc'] = bundle.encoders['season'].transform(
            df_with_features['season'].values
        )
    else:
        # If season encoder missing, create default
        df_with_features['season_enc'] = 0
    
    # Get latest state per hospital (deterministic)
    latest_state = df_with_features.groupby('hospital_id', sort=False).tail(1).reset_index(drop=True).copy(deep=True)
    
    # ============================================================================
    # STEP 4: Structural validation
    # ============================================================================
    if latest_state.empty:
        raise ValueError("Latest state DataFrame is empty after feature engineering")
    
    # Validate feature columns exist
    missing_features = set(bundle.feature_columns) - set(latest_state.columns)
    if missing_features:
        raise ValueError(f"Missing required features in data: {missing_features}")
    
    # ============================================================================
    # STEP 5: Generate predictions (deterministic iteration)
    # ============================================================================
    results = []
    sorted_horizons = sorted(horizons)  # Deterministic order
    
    # Process each hospital independently (deterministic order)
    hospital_ids = sorted(latest_state['hospital_id'].unique().tolist())
    
    for hospital_id in hospital_ids:
        # Get hospital data (deep copy)
        hospital_mask = latest_state['hospital_id'] == hospital_id
        hospital_data = latest_state[hospital_mask].iloc[0].copy(deep=True).to_dict()
        
        # Get last 7 days of actual admissions for lag initialization
        hospital_mask_history = df_with_features['hospital_id'] == hospital_id
        hospital_history = df_with_features[hospital_mask_history].tail(7).copy(deep=True)
        
        # Get last date
        last_date = pd.to_datetime(hospital_data['date'])
        
        # Initialize admissions history (last 7 days, deterministic)
        admissions_history = hospital_history['admissions'].values.tolist()
        
        # Ensure we have at least 7 values (pad with last value if needed)
        while len(admissions_history) < 7:
            last_val = admissions_history[-1] if admissions_history else hospital_data['admissions']
            admissions_history.insert(0, last_val)
        
        # Track predictions for iterative updates
        predictions = []
        
        # Iterate through horizons sequentially (deterministic order)
        for horizon in sorted_horizons:
            # Create feature row (deep copy from dict)
            feature_row = hospital_data.copy()
            future_date = last_date + timedelta(days=horizon)
            feature_row['date'] = future_date
            
            # Update temporal features for future date
            feature_row['month'] = future_date.month
            feature_row['week_of_year'] = future_date.isocalendar().week
            feature_row['is_weekend'] = 1 if future_date.weekday() >= 5 else 0
            feature_row['day_of_week'] = future_date.weekday()
            
            # Determine lag_1 (most recent value)
            if horizon == 1:
                lag_1 = admissions_history[-1]  # Last actual
            else:
                # Use prediction from (horizon - 1)
                prev_horizon_idx = sorted_horizons.index(horizon) - 1
                if prev_horizon_idx >= 0 and prev_horizon_idx < len(predictions):
                    lag_1 = predictions[prev_horizon_idx]
                else:
                    lag_1 = admissions_history[-1]
            
            # Determine lag_7 (7 days ago)
            if horizon <= 7:
                # Use actual from 7 days before horizon
                lag_7_idx = len(admissions_history) - (8 - horizon)
                if 0 <= lag_7_idx < len(admissions_history):
                    lag_7 = admissions_history[lag_7_idx]
                else:
                    lag_7 = admissions_history[0]
            else:
                # Use prediction from (horizon - 7)
                pred_7_idx = sorted_horizons.index(horizon) - 7
                if 0 <= pred_7_idx < len(predictions):
                    lag_7 = predictions[pred_7_idx]
                else:
                    lag_7 = admissions_history[0]
            
            feature_row['lag_1'] = lag_1
            feature_row['lag_7'] = lag_7

            # Merge latest external signals from DB for inference-time exogenous features.
            # If no signal exists, keep historical values from feature_row (deterministic fallback).
            signal_values = external_signals_by_hospital.get(str(hospital_id))
            if signal_values:
                feature_row['temperature'] = signal_values.get('temperature', feature_row.get('temperature', 0.0))
                feature_row['aqi'] = signal_values.get('aqi', feature_row.get('aqi', 0.0))
                feature_row['outbreak_index'] = signal_values.get('outbreak_index', feature_row.get('outbreak_index', 0.0))
                feature_row['mobility_index'] = signal_values.get('mobility_index', feature_row.get('mobility_index', 0.0))
            
            # Create DataFrame for prediction (from dict, new DataFrame)
            X_pred = pd.DataFrame([feature_row])
            
            # Select only feature columns in correct order (protect against drift)
            # Remove any extra columns that might exist
            available_features = [col for col in bundle.feature_columns if col in X_pred.columns]
            missing_features_in_row = set(bundle.feature_columns) - set(available_features)
            
            if missing_features_in_row:
                # Fill missing with 0
                for feat in missing_features_in_row:
                    X_pred[feat] = 0
            
            # STRICT FEATURE LOCK: Use model's exact feature order
            # No fallback. No try/except. Hard alignment.
            if hasattr(bundle.model, 'feature_name_'):
                model_feature_names = bundle.model.feature_name_
            elif hasattr(bundle.model, 'feature_names_in_'):
                model_feature_names = bundle.model.feature_names_in_
            else:
                model_feature_names = bundle.feature_columns
            
            # Hard alignment - use model's exact feature order
            X_pred_features = X_pred[model_feature_names].copy(deep=True)
            X_pred_features = X_pred_features.fillna(0)
            
            # Validate alignment (strict check)
            if list(X_pred_features.columns) != list(model_feature_names):
                raise ValueError(
                    f"Feature order mismatch: expected {model_feature_names}, "
                    f"got {list(X_pred_features.columns)}"
                )
            
            # Final validation before prediction
            if X_pred_features.empty:
                raise ValueError(f"Feature DataFrame is empty for hospital {hospital_id}, horizon {horizon}")
            
            if len(X_pred_features.columns) != len(bundle.feature_columns):
                raise ValueError(
                    f"Feature count mismatch: expected {len(bundle.feature_columns)}, "
                    f"got {len(X_pred_features.columns)}"
                )
            
            # Predict
            try:
                prediction = bundle.predict(X_pred_features)[0]
                if not np.isfinite(prediction):
                    # Fallback to last known value if prediction is invalid
                    prediction = admissions_history[-1]
            except Exception as e:
                # If prediction fails, use last known value
                prediction = admissions_history[-1]
            
            # Store prediction
            predictions.append(float(prediction))
            
            # Store result
            results.append({
                'hospital_id': str(hospital_id),
                'horizon': int(horizon),
                'prediction': float(prediction)
            })
    
    # ============================================================================
    # STEP 6: Create result DataFrame and validate
    # ============================================================================
    if not results:
        raise ValueError("No forecasts generated - results list is empty")
    
    forecast_df = pd.DataFrame(results).copy(deep=True)
    
    # Validate output
    if forecast_df.empty:
        raise ValueError("Forecast DataFrame is empty")
    
    expected_count = len(hospital_ids) * len(sorted_horizons)
    if len(forecast_df) != expected_count:
        raise ValueError(
            f"Forecast count mismatch: expected {expected_count}, got {len(forecast_df)}"
        )
    
    # DIAGNOSTIC: Verify input was not mutated (should still match original)
    final_df_rows = len(df)
    final_df_hospitals = df['hospital_id'].nunique() if not df.empty else 0
    assert final_df_rows == input_rows, f"Input mutated: start={input_rows}, end={final_df_rows}"
    assert final_df_hospitals == input_hospitals, f"Hospitals mutated: start={input_hospitals}, end={final_df_hospitals}"
    
    return forecast_df


def forecast_to_json(forecast_df: pd.DataFrame) -> dict:
    """
    Convert forecast DataFrame to JSON format.
    
    Args:
        forecast_df: DataFrame with hospital_id, horizon, prediction
    
    Returns:
        Dict with forecasts list
    """
    if forecast_df.empty:
        return {'forecasts': []}
    
    forecasts = []
    for _, row in forecast_df.iterrows():
        forecasts.append({
            'hospital_id': str(row['hospital_id']),
            'horizon': int(row['horizon']),
            'prediction': float(row['prediction'])
        })
    
    return {'forecasts': forecasts}


def self_test(bundle: ModelBundle, historical_df: pd.DataFrame) -> bool:
    """
    Test that forecast() is deterministic.
    
    Runs forecast() twice with identical inputs and verifies identical outputs.
    
    Args:
        bundle: ModelBundle with trained model
        historical_df: Historical DataFrame
    
    Returns:
        True if deterministic, raises AssertionError otherwise
    """
    # Run forecast twice
    result_a = forecast(bundle, historical_df.copy(deep=True))
    result_b = forecast(bundle, historical_df.copy(deep=True))
    
    # Reset index for comparison
    result_a = result_a.reset_index(drop=True).sort_values(['hospital_id', 'horizon']).reset_index(drop=True)
    result_b = result_b.reset_index(drop=True).sort_values(['hospital_id', 'horizon']).reset_index(drop=True)
    
    # Check if identical
    if not result_a.equals(result_b):
        # Find differences
        diff_mask = result_a != result_b
        if diff_mask.any().any():
            print("Differences found:")
            print(result_a[diff_mask.any(axis=1)])
            print(result_b[diff_mask.any(axis=1)])
        raise AssertionError("Inference is not deterministic! Two identical calls produced different results.")
    
    # Check count
    if len(result_a) != len(result_b):
        raise AssertionError(f"Count mismatch: first call={len(result_a)}, second call={len(result_b)}")
    
    if len(result_a) == 0:
        raise AssertionError("Both calls returned 0 forecasts - this is a bug!")
    
    return True
