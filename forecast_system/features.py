"""
Production Feature Engineering

Frozen feature schema: Only lag_1 and lag_7.
No dynamic feature creation.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from typing import Tuple, Dict


def create_features(df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, Dict]:
    """
    Create features for training/inference.
    
    Rules:
    - Sort by hospital_id + date
    - Group by hospital_id
    - Create lag_1 and lag_7 only
    - Drop rows with NA
    - Encode hospital_id and season
    
    Args:
        df: Raw DataFrame with columns:
            date, hospital_id, admissions, season, and other base columns
    
    Returns:
        X: Feature DataFrame with feature_columns
        y: Target Series (admissions)
        encoders: Dict with 'hospital_id' and 'season' encoders
    """
    # Sort by hospital_id + date
    df = df.sort_values(['hospital_id', 'date']).copy()
    
    # Group by hospital_id to create lags
    df['lag_1'] = df.groupby('hospital_id')['admissions'].shift(1)
    df['lag_7'] = df.groupby('hospital_id')['admissions'].shift(7)
    
    # Drop rows with NA (first 7 rows per hospital)
    df = df.dropna(subset=['lag_1', 'lag_7']).copy()
    
    # Encode categoricals
    encoders = {}
    
    # Hospital ID encoding
    hospital_encoder = LabelEncoder()
    df['hospital_id_enc'] = hospital_encoder.fit_transform(df['hospital_id'])
    encoders['hospital_id'] = hospital_encoder
    
    # Season encoding
    season_encoder = LabelEncoder()
    df['season_enc'] = season_encoder.fit_transform(df['season'])
    encoders['season'] = season_encoder
    
    # Define feature columns (FROZEN SCHEMA)
    # Must match exactly what model expects
    feature_columns = [
        'lag_1',
        'lag_7',
        'hospital_id_enc',
        'season_enc',
        'day_of_week',
        'month',
        'week_of_year',
        'is_weekend',
        'temperature',
        'aqi',
        'outbreak_index',
        'mobility_index',
        'population',
        'population_density',
        'elderly_ratio',
        'hospital_capacity',
        'icu_capacity',
    ]
    
    # Ensure all required columns exist (fill missing with defaults)
    for col in feature_columns:
        if col not in df.columns:
            if col == 'day_of_week':
                df[col] = pd.to_datetime(df['date']).dt.dayofweek
            else:
                df[col] = 0
    
    # Select only available features
    available_features = [col for col in feature_columns if col in df.columns]
    
    # Create X and y
    X = df[available_features].copy()
    y = df['admissions'].copy()
    
    # Fill any remaining NaN with 0
    X = X.fillna(0)
    
    return X, y, encoders


def apply_features(df: pd.DataFrame, encoders: Dict) -> pd.DataFrame:
    """
    Apply feature engineering to new data using existing encoders.
    
    Args:
        df: Raw DataFrame
        encoders: Dict with 'hospital_id' and 'season' encoders
    
    Returns:
        X: Feature DataFrame
    """
    # Sort by hospital_id + date
    df = df.sort_values(['hospital_id', 'date']).copy()
    
    # Create lags
    df['lag_1'] = df.groupby('hospital_id')['admissions'].shift(1)
    df['lag_7'] = df.groupby('hospital_id')['admissions'].shift(7)
    
    # Apply encoders
    if 'hospital_id' in encoders:
        df['hospital_id_enc'] = encoders['hospital_id'].transform(df['hospital_id'])
    
    if 'season' in encoders:
        df['season_enc'] = encoders['season'].transform(df['season'])
    
    # Define feature columns (same as create_features)
    feature_columns = [
        'lag_1',
        'lag_7',
        'hospital_id_enc',
        'season_enc',
        'day_of_week',
        'month',
        'week_of_year',
        'is_weekend',
        'temperature',
        'aqi',
        'outbreak_index',
        'mobility_index',
        'population',
        'population_density',
        'elderly_ratio',
        'hospital_capacity',
        'icu_capacity',
    ]
    
    # Ensure all required columns exist
    for col in feature_columns:
        if col not in df.columns:
            if col == 'day_of_week':
                df[col] = pd.to_datetime(df['date']).dt.dayofweek
            else:
                df[col] = 0
    
    # Select only available features
    available_features = [col for col in feature_columns if col in df.columns]
    
    X = df[available_features].copy()
    X = X.fillna(0)
    
    return X

