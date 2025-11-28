"""
Unified feature engineering for XGBoost and TFT.

This module exposes:

    - XGB_FEATURES: canonical 41-feature list used by global XGB models
    - build_features(df): returns a DataFrame with exactly these features

All training and inference code for XGB and TFT should use this to ensure
identical feature definitions and ordering.
"""

from typing import List

import numpy as np
import pandas as pd

from .feature_engineering import feature_engineering_xgb


XGB_FEATURES: List[str] = [
    "lag_1_admissions", "lag_7_admissions", "rolling_14_admissions",
    "aqi", "temp", "humidity", "rainfall", "wind_speed",
    "mobility_index", "outbreak_index",
    "festival_flag", "holiday_flag",
    "weekday", "is_weekend",
    "population_density", "hospital_beds", "staff_count",
    "city_id", "hospital_id_enc",
    "month", "week_of_year", "quarter", "season",
    "day_sin", "day_cos", "month_sin", "month_cos",
    "aqi_above_150", "aqi_above_200", "aqi_above_300", "aqi_severity",
    "temp_humidity", "rainfall_injury_risk", "aqi_respiratory_ratio", "aqi_temp",
    "mobility_outbreak", "temp_rainfall", "aqi_mobility",
    "lag1_aqi", "lag7_outbreak", "rolling_aqi",
]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run unified feature engineering and return a DataFrame containing
    exactly the 41 XGB_FEATURES in the correct order.

    Any missing engineered columns are created and filled with 0 so that
    TFT and XGB always see the same feature space.
    """
    df_fe = feature_engineering_xgb(df.copy())

    for col in XGB_FEATURES:
        if col not in df_fe.columns:
            # Safe default for missing engineered feature
            df_fe[col] = 0

    X = df_fe[XGB_FEATURES].copy().astype("float32")
    return X


