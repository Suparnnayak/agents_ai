"""
Feature Engineering Module

Creates lag features, temporal features, and prepares data for forecasting.
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from typing import Tuple
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .utils import get_logger

logger = get_logger(__name__)


def create_lag_features(df: pd.DataFrame, lags: list = [1, 2, 3, 5, 7, 14, 21, 30, 60, 90]) -> pd.DataFrame:
    """
    Create lag features for admissions.
    
    Also creates recursive features to reduce residual autocorrelation.
    """
    df = df.copy()
    
    logger.info(f"🔧 Creating lag features: {lags}")
    
    for lag in lags:
        df[f'lag_{lag}'] = df.groupby('hospital_id')['admissions'].shift(lag)
    
    # First difference (helps with stationarity and reduces autocorrelation)
    if 'lag_1' in df.columns:
        df['admissions_diff_1'] = df['admissions'] - df['lag_1']
        logger.info("   Added first difference feature (admissions - lag_1)")
    
    # Recursive features to capture temporal dependencies (reduces residual autocorrelation)
    # These help tree models capture residual temporal structure
    if 'lag_1' in df.columns and 'lag_7' in df.columns:
        # Change from last week
        df['change_from_week_ago'] = df['lag_1'] - df['lag_7']
        # Acceleration (change in change)
        if 'lag_2' in df.columns:
            df['acceleration'] = (df['lag_1'] - df['lag_2']) - (df['lag_2'] - df['lag_3']) if 'lag_3' in df.columns else 0
        logger.info("   Added recursive features: change_from_week_ago, acceleration")
    
    return df


def create_temporal_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create temporal features from date.
    
    Includes one-hot encoding for month (reduces CV variance by capturing seasonal regimes).
    """
    df = df.copy()
    
    logger.info("🔧 Creating temporal features...")
    
    df['month'] = df['date'].dt.month
    df['week_of_year'] = df['date'].dt.isocalendar().week
    df['quarter'] = df['date'].dt.quarter
    df['day_of_year'] = df['date'].dt.dayofyear
    df['is_weekend'] = (df['date'].dt.weekday >= 5).astype(int)
    df['day_of_week'] = df['date'].dt.dayofweek
    
    # One-hot encode month (for regime-aware modeling, reduces CV variance)
    for month in range(1, 13):
        df[f'month_{month}'] = (df['month'] == month).astype(int)
    logger.info("   Added month one-hot encoding (month_1 to month_12)")
    
    # Cyclical encoding
    df['month_sin'] = np.sin(2 * np.pi * df['month'] / 12)
    df['month_cos'] = np.cos(2 * np.pi * df['month'] / 12)
    df['day_of_year_sin'] = np.sin(2 * np.pi * df['day_of_year'] / 365.25)
    df['day_of_year_cos'] = np.cos(2 * np.pi * df['day_of_year'] / 365.25)
    df['day_of_week_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
    df['day_of_week_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
    
    # Fourier seasonal terms (yearly + weekly)
    # Yearly: multiple harmonics for capturing seasonal patterns
    for k in [1, 2, 3]:
        df[f'yearly_sin_{k}'] = np.sin(2 * np.pi * k * df['day_of_year'] / 365.25)
        df[f'yearly_cos_{k}'] = np.cos(2 * np.pi * k * df['day_of_year'] / 365.25)
    
    # Weekly: multiple harmonics
    for k in [1, 2]:
        df[f'weekly_sin_{k}'] = np.sin(2 * np.pi * k * df['day_of_week'] / 7)
        df[f'weekly_cos_{k}'] = np.cos(2 * np.pi * k * df['day_of_week'] / 7)
    
    # REMOVED: trend_index (monotonic drift feature causes structural drift)
    # Use only bounded cyclical features (Fourier terms) for temporal patterns
    
    logger.info("   Added Fourier seasonal terms (trend_index removed to prevent structural drift)")
    
    return df


def create_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create rolling window features.
    
    REDUCED DOMINANCE: Only std features (max/min/median disabled to reduce dominance).
    Added: EMA and rolling slope for trend.
    """
    df = df.copy()
    
    logger.info("🔧 Creating rolling features...")
    
    # Only rolling std (max/min/median disabled to reduce dominance)
    for window in [7, 14]:
        df[f'rolling_std_{window}'] = df.groupby('hospital_id')['admissions'].transform(
            lambda x: x.rolling(window=window, min_periods=1).std().fillna(0)
        )
    
    # Exponential Moving Average (EMA) - smoother than rolling mean
    for window in [7]:
        df[f'ema_{window}'] = df.groupby('hospital_id')['admissions'].transform(
            lambda x: x.ewm(span=window, min_periods=1, adjust=False).mean().fillna(0)
        )
    
    # Rolling slope (linear trend over last 7 days)
    def compute_slope(series):
        """Compute linear slope over window."""
        if len(series) < 2:
            return 0.0
        x = np.arange(len(series))
        if np.std(x) == 0:
            return 0.0
        slope = np.polyfit(x, series.values, 1)[0]
        return slope
    
    df['rolling_slope_7'] = df.groupby('hospital_id')['admissions'].transform(
        lambda x: x.rolling(window=7, min_periods=2).apply(compute_slope, raw=False).fillna(0)
    )
    
    logger.info("   Created rolling_std_7, rolling_std_14, ema_7, rolling_slope_7")
    logger.info("   DISABLED: rolling_max/min/median (to reduce dominance)")
    
    return df


def encode_categoricals(df: pd.DataFrame) -> pd.DataFrame:
    """Encode categorical variables."""
    df = df.copy()
    
    logger.info("🔧 Encoding categorical features...")
    
    if 'hospital_id' in df.columns:
        le_hospital = LabelEncoder()
        df['hospital_id_enc'] = le_hospital.fit_transform(df['hospital_id'])
    
    if 'season' in df.columns:
        le_season = LabelEncoder()
        df['season_enc'] = le_season.fit_transform(df['season'])
    
    return df


def create_exogenous_lags(df: pd.DataFrame, 
                         exogenous_cols: list = ['aqi', 'outbreak_index', 'temperature'],
                         lags: list = [1, 7]) -> pd.DataFrame:
    """Create lag features for exogenous variables."""
    df = df.copy()
    
    logger.info("🔧 Creating exogenous lag features...")
    
    for col in exogenous_cols:
        if col not in df.columns:
            continue
        
        for lag in lags:
            df[f'{col}_lag_{lag}'] = df.groupby('hospital_id')[col].shift(lag)
    
    logger.info(f"   Created lags {lags} for exogenous variables: {exogenous_cols}")
    
    return df


def create_interaction_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create interaction features between variables."""
    df = df.copy()
    
    logger.info("🔧 Creating interaction features...")
    
    # Outbreak × Winter (seasonal interaction)
    if 'outbreak_index' in df.columns and 'season' in df.columns:
        df['outbreak_winter'] = df['outbreak_index'] * (df['season'] == 'winter').astype(int)
    
    # Temperature × Elderly ratio
    if 'temperature' in df.columns and 'elderly_ratio' in df.columns:
        df['temp_elderly'] = df['temperature'] * df['elderly_ratio']
    
    # Mobility × Weekend
    if 'mobility_index' in df.columns and 'is_weekend' in df.columns:
        df['mobility_weekend'] = df['mobility_index'] * df['is_weekend']
    
    # AQI × Temperature (high AQI + high temp = worse)
    if 'aqi' in df.columns and 'temperature' in df.columns:
        df['aqi_temp'] = df['aqi'] * df['temperature']
    
    # AQI × Winter (AQI effects stronger in winter)
    if 'aqi' in df.columns and 'season' in df.columns:
        df['aqi_winter'] = df['aqi'] * (df['season'] == 'winter').astype(int)
    
    # Nonlinear exogenous interactions (tree models need interaction triggers)
    # Outbreak × Volatility regime (outbreak matters more during high volatility)
    if 'outbreak_index' in df.columns and 'high_vol_regime' in df.columns:
        df['outbreak_vol_regime'] = df['outbreak_index'] * df['high_vol_regime']
    
    # Outbreak × Capacity (outbreak effects scale with capacity)
    if 'outbreak_index' in df.columns and 'hospital_capacity' in df.columns:
        df['outbreak_capacity'] = df['outbreak_index'] * df['hospital_capacity']
    
    # AQI × Elderly ratio (AQI affects elderly more)
    if 'aqi' in df.columns and 'elderly_ratio' in df.columns:
        df['aqi_elderly'] = df['aqi'] * df['elderly_ratio']
    
    # Exogenous trend momentum (rate-of-change features)
    if 'outbreak_index' in df.columns:
        df['outbreak_change_7'] = df.groupby('hospital_id')['outbreak_index'].transform(
            lambda x: x - x.shift(7)
        ).fillna(0)
        logger.info("   Added outbreak_change_7 (rate-of-change feature)")
    
    if 'aqi' in df.columns:
        df['aqi_change_7'] = df.groupby('hospital_id')['aqi'].transform(
            lambda x: x - x.shift(7)
        ).fillna(0)
        logger.info("   Added aqi_change_7 (rate-of-change feature)")
    
    logger.info("   Created interaction features: outbreak×winter, temp×elderly, mobility×weekend, aqi×temp, aqi×winter")
    logger.info("   Added nonlinear interactions: outbreak×vol_regime, outbreak×capacity, aqi×elderly")
    logger.info("   Added trend momentum: outbreak_change_7, aqi_change_7")
    
    # Normalize interaction features using rolling z-score (90-day window) to prevent drift
    interaction_cols = ['aqi', 'temperature', 'outbreak_index']
    for col in interaction_cols:
        if col in df.columns:
            # Compute rolling mean and std per hospital (90-day window)
            rolling_mean = df.groupby('hospital_id')[col].transform(
                lambda x: x.rolling(window=90, min_periods=30).mean()
            )
            rolling_std = df.groupby('hospital_id')[col].transform(
                lambda x: x.rolling(window=90, min_periods=30).std()
            )
            # Z-score normalization
            df[f'{col}_normalized'] = (df[col] - rolling_mean) / (rolling_std + 1e-6)
            logger.info(f"   Added {col}_normalized (rolling z-score, 90-day window)")
    
    return df


def create_structural_shock_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create structural shock features for better surge detection.
    
    Features:
    - outbreak_acceleration: Second derivative of outbreak_index
    - aqi_acceleration: Second derivative of aqi
    - admissions_acceleration_7: 7-day second derivative of admissions
    - volatility_index: rolling_std_7 / rolling_mean_7 (coefficient of variation)
    
    These help detect upcoming surges rather than reacting late.
    """
    df = df.copy()
    
    logger.info("🔧 Creating structural shock features...")
    
    # Outbreak acceleration (second derivative)
    if 'outbreak_index' in df.columns:
        outbreak_change = df.groupby('hospital_id')['outbreak_index'].transform(
            lambda x: x - x.shift(1)
        )
        df['outbreak_acceleration'] = df.groupby('hospital_id')['outbreak_index'].transform(
            lambda x: (x - x.shift(1)) - (x.shift(1) - x.shift(2))
        ).fillna(0)
        logger.info("   Added outbreak_acceleration (second derivative)")
    
    # AQI acceleration
    if 'aqi' in df.columns:
        df['aqi_acceleration'] = df.groupby('hospital_id')['aqi'].transform(
            lambda x: (x - x.shift(1)) - (x.shift(1) - x.shift(2))
        ).fillna(0)
        logger.info("   Added aqi_acceleration (second derivative)")
    
    # Admissions acceleration (7-day second derivative)
    if 'admissions' in df.columns:
        # First derivative (7-day change)
        admissions_change_7 = df.groupby('hospital_id')['admissions'].transform(
            lambda x: x - x.shift(7)
        )
        # Second derivative (change in change)
        df['admissions_acceleration_7'] = df.groupby('hospital_id')['admissions'].transform(
            lambda x: (x - x.shift(7)) - (x.shift(7) - x.shift(14))
        ).fillna(0)
        logger.info("   Added admissions_acceleration_7 (7-day second derivative)")
    
    # Volatility index (coefficient of variation)
    if 'rolling_std_7' in df.columns and 'rolling_mean_7' in df.columns:
        df['volatility_index'] = df['rolling_std_7'] / (df['rolling_mean_7'] + 1e-6)
        logger.info("   Added volatility_index (rolling_std_7 / rolling_mean_7)")
    elif 'rolling_std_7' in df.columns:
        # Fallback: use lag_1 as proxy for mean
        if 'lag_1' in df.columns:
            df['volatility_index'] = df['rolling_std_7'] / (df['lag_1'] + 1e-6)
            logger.info("   Added volatility_index (using lag_1 as mean proxy)")
    
    logger.info("   ✅ Structural shock features created")
    
    return df


def create_horizon_stacking(df: pd.DataFrame, max_horizon: int = 7) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Create horizon stacking for multi-horizon forecasting.
    
    Returns:
        X: Features DataFrame
        y: Target Series
        dates: Date Series (for time-based splitting)
    """
    logger.info(f"🔧 Creating horizon stacking (1-{max_horizon} days)...")
    
    stacked_rows = []
    
    for hospital_id, group in df.groupby('hospital_id'):
        group = group.sort_values('date').reset_index(drop=True)
        
        for idx, row in group.iterrows():
            for horizon in range(1, max_horizon + 1):
                if idx + horizon < len(group):
                    new_row = row.copy()
                    new_row['target'] = group.iloc[idx + horizon]['admissions']
                    new_row['horizon'] = horizon
                    new_row['date'] = row['date']  # Preserve original date
                    stacked_rows.append(new_row)
    
    df_stacked = pd.DataFrame(stacked_rows)
    
    logger.info(f"   Original: {len(df)} rows → Stacked: {len(df_stacked)} rows")
    
    # Prepare features
    feature_cols = [
        # Lags (expanded to reduce autocorrelation and CV variance)
        'lag_1', 'lag_2', 'lag_3', 'lag_5', 'lag_7', 'lag_14', 'lag_21', 'lag_30', 'lag_60',
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
        # Trend index REMOVED (causes structural drift)
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
        # Error features (will be added during training/inference, not here)
        # 'prev_error_1', 'prev_error_2', 'prev_error_7', 'rolling_error_mean_7', 'rolling_error_std_7', 'error_momentum',
        # Horizon (CRITICAL)
        'horizon', 'horizon_squared', 'horizon_vol_interaction'
    ]
    
    available_features = [col for col in feature_cols if col in df_stacked.columns]
    X = df_stacked[available_features].copy().fillna(0)
    y = df_stacked['target'].copy()
    dates = df_stacked['date'].copy()
    
    # Remove rows with missing targets or critical lags
    valid_mask = ~(y.isna() | X['lag_1'].isna() | X['lag_7'].isna())
    X = X[valid_mask].copy()
    y = y[valid_mask].copy()
    dates = dates[valid_mask].copy()
    
    logger.info(f"✅ Final dataset: {len(X)} rows, {X.shape[1]} features")
    
    return X, y, dates


def engineer_features(df: pd.DataFrame,
                     include_exogenous_lags: bool = True,
                     include_interactions: bool = True) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
    """
    Complete feature engineering pipeline.
    
    Args:
        df: Input DataFrame
        include_exogenous_lags: Whether to create lags for exogenous variables
        include_interactions: Whether to create interaction features
    
    Returns:
        X: Feature DataFrame
        y: Target Series
        dates: Date Series
    """
    logger.info("🔄 Starting feature engineering pipeline...")
    
    # Step 1: Lags
    df = create_lag_features(df)
    
    # Step 2: Rolling
    df = create_rolling_features(df)
    
    # Step 3: Temporal
    df = create_temporal_features(df)
    
    # Step 4: Exogenous lags
    if include_exogenous_lags:
        df = create_exogenous_lags(df)
    
    # Step 5: Interactions
    if include_interactions:
        df = create_interaction_features(df)
    
    # Step 5.5: Structural shock features (for surge detection)
    df = create_structural_shock_features(df)
    
    # Step 6: Encode
    df = encode_categoricals(df)
    
    # Step 7: Horizon stacking
    X, y, dates = create_horizon_stacking(df)
    
    # Step 8: Error features will be added during training from OOF predictions
    # (Not added here to avoid leakage - must be computed from CV predictions)
    
    logger.info("✅ Feature engineering complete")
    logger.info("   Note: Tree-integrated error features will be added during training from OOF predictions")
    
    return X, y, dates

