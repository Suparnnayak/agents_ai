# src/components/data_transformation.py
import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler
from src.pipeline.logger import get_logger

logger = get_logger(__name__)

# BASE FEATURES
BASE_FEATURES = [
    "lag_1_admissions", "lag_7_admissions", "rolling_14_admissions",
    "aqi", "temp", "humidity", "rainfall", "wind_speed",
    "mobility_index", "outbreak_index",
    "festival_flag", "holiday_flag",
    "weekday", "is_weekend",
    "population_density", "hospital_beds", "staff_count",
    "city_id", "hospital_id_enc"
]

def create_temporal_features(df: pd.DataFrame):
    """Create temporal features from date column."""
    df = df.copy()
    
    if 'date' not in df.columns:
        raise ValueError("'date' column required for temporal features")
    
    df['date'] = pd.to_datetime(df['date'])
    
    # Basic temporal features
    df['month'] = df['date'].dt.month
    df['week_of_year'] = df['date'].dt.isocalendar().week
    df['quarter'] = df['date'].dt.quarter
    df['day_of_year'] = df['date'].dt.dayofyear
    
    # Season (1=Spring, 2=Summer, 3=Fall, 4=Winter)
    df['season'] = df['date'].dt.month % 12 // 3 + 1
    
    # Cyclical encoding for day of year (sin/cos)
    df['day_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
    df['day_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
    
    # Cyclical encoding for month
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    
    return df

def create_aqi_interaction_features(df: pd.DataFrame):
    """Create AQI threshold-based interaction features."""
    df = df.copy()
    
    if 'aqi' not in df.columns:
        raise ValueError("'aqi' column required for AQI features")
    
    # AQI threshold flags
    df['aqi_above_150'] = (df['aqi'] > 150).astype(int)
    df['aqi_above_200'] = (df['aqi'] > 200).astype(int)
    df['aqi_above_300'] = (df['aqi'] > 300).astype(int)
    
    # AQI severity levels (0=Good, 1=Moderate, 2=Unhealthy, 3=Very Unhealthy, 4=Hazardous)
    df['aqi_severity'] = pd.cut(
        df['aqi'],
        bins=[0, 50, 100, 150, 200, 300, 1000],
        labels=[0, 1, 2, 3, 4, 5],
        include_lowest=True
    ).astype(int)
    
    return df

def create_engineered_features(df: pd.DataFrame):
    """Create interaction and engineered features."""
    df = df.copy()
    
    # Temperature * Humidity (heat index proxy)
    df['temp_humidity'] = df['temp'] * df['humidity']
    
    # Rainfall * injury risk (higher rainfall = more accidents)
    # Using a simple heuristic: injury_risk = 1 + (rainfall > 20) * 0.5
    injury_risk = 1.0 + (df['rainfall'] > 20).astype(float) * 0.5
    df['rainfall_injury_risk'] = df['rainfall'] * injury_risk
    
    # AQI * respiratory ratio (higher AQI = more respiratory issues)
    # Respiratory ratio proxy: 1 + (aqi > 100) * 0.3
    respiratory_ratio = 1.0 + (df['aqi'] > 100).astype(float) * 0.3
    df['aqi_respiratory_ratio'] = df['aqi'] * respiratory_ratio
    
    # Additional useful interactions
    df['aqi_temp'] = df['aqi'] * df['temp']
    df['mobility_outbreak'] = df['mobility_index'] * (1 + df['outbreak_index'])
    df['temp_rainfall'] = df['temp'] * df['rainfall']
    # Rainfall * is_weekend (weekend rainfall may have different impact)
    if 'is_weekend' in df.columns:
        df['rainfall_weekend'] = df['rainfall'] * df['is_weekend']
    
    # AQI * Mobility interaction (higher AQI + lower mobility = more admissions)
    df['aqi_mobility'] = df['aqi'] * (100 - df['mobility_index']) / 100
    
    # Lag interactions (temporal + environmental)
    if 'lag_1_admissions' in df.columns:
        df['lag1_aqi'] = df['lag_1_admissions'] * (df['aqi'] / 100)
        df['lag7_outbreak'] = df['lag_7_admissions'] * (1 + df['outbreak_index'])
        # Rolling average * current AQI
        if 'rolling_14_admissions' in df.columns:
            df['rolling_aqi'] = df['rolling_14_admissions'] * (df['aqi'] / 100)
    
    return df

def transform_for_xgb(df: pd.DataFrame, scale_features=False):
    """
    Prepares X and y for model training with enhanced features.
    Tree models (XGBoost/LightGBM) don't require scaling, but we keep it optional.
    
    Args:
        df: Input dataframe with date and base features
        scale_features: Whether to apply StandardScaler (default False for tree models)
    
    Returns:
        X: Feature matrix
        y: Target variable
        scaler: Fitted scaler (or None if scale_features=False)
        df_full: Full dataframe with all engineered features
    """
    df = df.copy()
    
    # Step 1: Create temporal features
    df = create_temporal_features(df)
    
    # Step 2: Create AQI interaction features
    df = create_aqi_interaction_features(df)
    
    # Step 3: Create engineered interaction features
    df = create_engineered_features(df)
    
    # Step 4: Build final feature list (ORDER MATTERS - keep consistent)
    TEMPORAL_FEATURES = [
        'month', 'week_of_year', 'quarter', 'season',
        'day_sin', 'day_cos', 'month_sin', 'month_cos'
    ]
    
    AQI_FEATURES = [
        'aqi_above_150', 'aqi_above_200', 'aqi_above_300', 'aqi_severity'
    ]
    
    ENGINEERED_FEATURES = [
        'temp_humidity', 'rainfall_injury_risk', 'aqi_respiratory_ratio',
        'aqi_temp', 'mobility_outbreak', 'temp_rainfall', 'aqi_mobility',
        'lag1_aqi', 'lag7_outbreak', 'rolling_aqi'
    ]
    
    # Combine all features in fixed order for consistency
    ALL_FEATURES = BASE_FEATURES + TEMPORAL_FEATURES + AQI_FEATURES + ENGINEERED_FEATURES
    
    # Filter to only features that exist in dataframe
    available_features = [f for f in ALL_FEATURES if f in df.columns]
    
    # Fill missing values (forward fill, then backward fill, then zero)
    df[available_features] = df[available_features].ffill().bfill().fillna(0)
    
    # Ensure numeric type
    for col in available_features:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # Extract features and target
    X = df[available_features].copy()
    y = df["admissions"].astype(int)
    
    # Optional scaling (tree models don't require it, disabled by default)
    scaler = None
    if scale_features:
        # Only scale continuous numerical features, not flags/categorical
        continuous_features = [f for f in available_features 
                              if f not in ['festival_flag', 'holiday_flag', 'is_weekend',
                                          'aqi_above_150', 'aqi_above_200', 'aqi_above_300',
                                          'city_id', 'hospital_id_enc', 'season', 'quarter']]
        if continuous_features:
            scaler = StandardScaler()
            X_scaled = X.copy()
            X_scaled[continuous_features] = scaler.fit_transform(X[continuous_features])
            X = X_scaled
    
    logger.info(f"🔧 Data transformed: X={X.shape}, y={y.shape}, features={len(available_features)}")
    
    return X, y, scaler, df

# Export feature list for use in other modules
# Note: Actual feature list is dynamically generated in transform_for_xgb
FEATURES = BASE_FEATURES

def get_feature_names(df: pd.DataFrame):
    """
    Get the complete feature list that would be generated by transform_for_xgb.
    Useful for ensuring consistent feature order in prediction.
    """
    df_temp = df.copy()
    df_temp = create_temporal_features(df_temp)
    df_temp = create_aqi_interaction_features(df_temp)
    df_temp = create_engineered_features(df_temp)
    
    TEMPORAL_FEATURES = [
        'month', 'week_of_year', 'quarter', 'season',
        'day_sin', 'day_cos', 'month_sin', 'month_cos'
    ]
    
    AQI_FEATURES = [
        'aqi_above_150', 'aqi_above_200', 'aqi_above_300', 'aqi_severity'
    ]
    
    ENGINEERED_FEATURES = [
        'temp_humidity', 'rainfall_injury_risk', 'aqi_respiratory_ratio',
        'aqi_temp', 'mobility_outbreak', 'temp_rainfall', 'aqi_mobility',
        'rainfall_weekend', 'lag1_aqi', 'lag7_outbreak', 'rolling_aqi'
    ]
    
    ALL_FEATURES = BASE_FEATURES + TEMPORAL_FEATURES + AQI_FEATURES + ENGINEERED_FEATURES
    available_features = [f for f in ALL_FEATURES if f in df_temp.columns]
    
    return available_features
