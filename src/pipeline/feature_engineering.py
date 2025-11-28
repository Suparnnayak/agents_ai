import pandas as pd
import numpy as np


XGB_FEATURES = [
    "lag_1_admissions","lag_7_admissions","rolling_14_admissions",
    "aqi","temp","humidity","rainfall","wind_speed",
    "mobility_index","outbreak_index",
    "festival_flag","holiday_flag",
    "weekday","is_weekend",
    "population_density","hospital_beds","staff_count",
    "city_id","hospital_id_enc",
    "month","week_of_year","quarter","season",
    "day_sin","day_cos","month_sin","month_cos",
    "aqi_above_150","aqi_above_200","aqi_above_300","aqi_severity",
    "temp_humidity","rainfall_injury_risk","aqi_respiratory_ratio","aqi_temp",
    "mobility_outbreak","temp_rainfall","aqi_mobility",
    "lag1_aqi","lag7_outbreak","rolling_aqi",
]


def feature_engineering_xgb(df: pd.DataFrame) -> pd.DataFrame:
    """
    Shared feature engineering for XGBoost + TFT.
    Ensures all XGB_FEATURES are present.
    """
    df = df.copy()

    # Ensure date is datetime
    df["date"] = pd.to_datetime(df["date"])

    # --- BASIC TIME FEATURES ---
    df["month"] = df["date"].dt.month
    df["week_of_year"] = df["date"].dt.isocalendar().week.astype(int)
    df["quarter"] = df["date"].dt.quarter

    # season: simple deterministic mapping
    def season(m):
        if m in [12, 1, 2]:
            return 0  # winter
        if m in [3, 4, 5]:
            return 1  # summer
        if m in [6, 7, 8]:
            return 2  # monsoon
        return 3  # post-monsoon

    df["season"] = df["month"].apply(season)

    # --- CYCLICAL FEATURES ---
    df["day_sin"] = np.sin(2 * np.pi * df["date"].dt.dayofyear / 365)
    df["day_cos"] = np.cos(2 * np.pi * df["date"].dt.dayofyear / 365)
    df["month_sin"] = np.sin(2 * np.pi * df["month"] / 12)
    df["month_cos"] = np.cos(2 * np.pi * df["month"] / 12)

    # --- AQI DERIVED FEATURES ---
    df["aqi_above_150"] = (df["aqi"] > 150).astype(int)
    df["aqi_above_200"] = (df["aqi"] > 200).astype(int)
    df["aqi_above_300"] = (df["aqi"] > 300).astype(int)

    df["aqi_severity"] = (
        0.5 * df["aqi_above_150"]
        + 1.0 * df["aqi_above_200"]
        + 1.5 * df["aqi_above_300"]
    )

    # --- MULTI-FEATURE INTERACTIONS ---
    df["temp_humidity"] = df["temp"] * df["humidity"]
    df["rainfall_injury_risk"] = df["rainfall"] * df["is_weekend"]

    # Some inference datasets may not have 'respiratory'; fall back to zeros
    if "respiratory" not in df.columns:
        df["respiratory"] = 0
    df["aqi_respiratory_ratio"] = df["aqi"] / (df["respiratory"] + 1)
    df["aqi_temp"] = df["aqi"] * df["temp"]
    df["mobility_outbreak"] = df["mobility_index"] * (1 + df["outbreak_index"])
    df["temp_rainfall"] = df["temp"] * df["rainfall"]
    df["aqi_mobility"] = df["aqi"] * df["mobility_index"]

    # --- LAG / ROLLING FEATURES FOR AQI & OUTBREAK ---
    # Create lag interaction features (lag1_aqi, lag7_outbreak, rolling_aqi)
    # These use admissions lags if available, otherwise use AQI/outbreak directly
    if "lag_1_admissions" in df.columns and "lag_7_admissions" in df.columns and "rolling_14_admissions" in df.columns:
        # Use admissions-based lag interactions (preferred)
        df["lag1_aqi"] = df["lag_1_admissions"] * (df["aqi"] / 100)
        df["lag7_outbreak"] = df["lag_7_admissions"] * (1 + df["outbreak_index"] / 100)
        df["rolling_aqi"] = df["rolling_14_admissions"] * (df["aqi"] / 100)
    else:
        # Fallback: use AQI/outbreak lags directly
        if "hospital_id" in df.columns:
            df["lag1_aqi"] = df.groupby("hospital_id")["aqi"].shift(1).bfill()
            df["lag7_outbreak"] = df.groupby("hospital_id")["outbreak_index"].shift(7).bfill()
            df["rolling_aqi"] = (
                df.groupby("hospital_id")["aqi"]
                .rolling(14, min_periods=1)
                .mean()
                .reset_index(0, drop=True)
            )
        else:
            df["lag1_aqi"] = df["aqi"]
            df["lag7_outbreak"] = df["outbreak_index"]
            df["rolling_aqi"] = df["aqi"]

    return df


def feature_engineering_tft(df: pd.DataFrame) -> pd.DataFrame:
    """
    TFT feature engineering wrapper.
    Ensures the same XGB_FEATURES exist; missing ones are filled with 0.
    """
    df_fe = feature_engineering_xgb(df)

    for col in XGB_FEATURES:
        if col not in df_fe.columns:
            df_fe[col] = 0

    return df_fe
