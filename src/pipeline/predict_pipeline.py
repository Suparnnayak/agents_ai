# src/pipeline/predict_pipeline.py

import pandas as pd
import logging
import numpy as np
import xgboost as xgb
import torch
from pathlib import Path
import sys

CURRENT_DIR = Path(__file__).resolve().parent
sys.path.append(str(CURRENT_DIR.parent))

from .feature_engineering import feature_engineering_xgb
from .utils import load_model
from ..models.tft_model import TFTQuantileModel, load_tft_model
from ..models.ensemble import predict_ensemble

logger = logging.getLogger(__name__)

# -----------------------------------------
# EXACT 40 FEATURES YOUR XGBOOST MODEL EXPECTS
# -----------------------------------------
XGB_FEATURES = [
    'lag_1_admissions', 'lag_7_admissions', 'rolling_14_admissions',
    'aqi', 'temp', 'humidity', 'rainfall', 'wind_speed',
    'mobility_index', 'outbreak_index',
    'festival_flag', 'holiday_flag', 'weekday', 'is_weekend',
    'population_density', 'hospital_beds', 'staff_count',
    'city_id', 'hospital_id_enc', 'month',

    # EXTRA ENGINEERED FEATURES YOUR MODEL REQUIRES
    'week_of_year', 'quarter', 'season',
    'day_sin', 'day_cos', 'month_sin', 'month_cos',
    'aqi_above_150', 'aqi_above_200', 'aqi_above_300', 'aqi_severity',
    'temp_humidity', 'rainfall_injury_risk', 'aqi_respiratory_ratio',
    'aqi_temp', 'mobility_outbreak', 'temp_rainfall', 'aqi_mobility',
    'lag1_aqi', 'lag7_outbreak', 'rolling_aqi'
]


def _prepare_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    
    # Create lag features if missing (for live predictions)
    if "lag_1_admissions" not in df.columns:
        if "admissions" in df.columns:
            # Use admissions column to create lags
            df["lag_1_admissions"] = df["admissions"].shift(1).fillna(df["admissions"].iloc[0] if len(df) > 0 else 150)
            df["lag_7_admissions"] = df["admissions"].shift(7).fillna(df["admissions"].iloc[0] if len(df) > 0 else 150)
            # Rolling 14-day average
            df["rolling_14_admissions"] = df["admissions"].rolling(window=14, min_periods=1).mean().fillna(df["admissions"].iloc[0] if len(df) > 0 else 150)
        else:
            # Use default values if no admissions data
            default_admissions = 150  # Average baseline
            df["lag_1_admissions"] = default_admissions
            df["lag_7_admissions"] = default_admissions
            df["rolling_14_admissions"] = default_admissions
            logger.warning("⚠️ No 'admissions' column found. Using default lag values (150). Accuracy may be reduced.")
    
    # Run feature engineering
    df_fe = feature_engineering_xgb(df)
    
    # Fill any remaining missing features with 0
    missing = [f for f in XGB_FEATURES if f not in df_fe.columns]
    if missing:
        for feat in missing:
            df_fe[feat] = 0
        logger.warning(f"⚠️ Missing features filled with 0: {missing}")
    
    return df_fe[XGB_FEATURES].copy().astype("float32")


def _load_spike_model(path: str = "models/global_q50_spike.json"):
    spike_path = Path(path)
    # Try .json first, then fallback to .model for legacy
    if not spike_path.exists():
        legacy_path = spike_path.with_suffix(".model")
        if legacy_path.exists():
            spike_path = legacy_path
        else:
            return None
    try:
        model = load_model(str(spike_path))
        logger.info(f"✅ Loaded spike correction model from {spike_path}")
        return model
    except Exception as exc:
        logger.warning(f"⚠️ Unable to load spike model ({exc}); continuing without it.")
        return None


def _load_extreme_spike_model(path: str = "models/global_q50_extreme_spike.json"):
    spike_path = Path(path)
    if not spike_path.exists():
        return None
    try:
        model = load_model(str(spike_path))
        logger.info(f"🔥 Loaded EXTREME spike correction model from {spike_path}")
        return model
    except Exception as exc:
        logger.warning(f"⚠️ Unable to load extreme spike model ({exc}); continuing without it.")
        return None


def _predict_xgb(df_model: pd.DataFrame):
    dmatrix = xgb.DMatrix(df_model, feature_names=XGB_FEATURES)
    model_q50 = load_model("models/global_q50.model")
    model_q10 = load_model("models/global_q10.model")
    model_q90 = load_model("models/global_q90.model")

    preds_med = model_q50.predict(dmatrix)
    preds_low = model_q10.predict(dmatrix) - 0.5
    preds_up = model_q90.predict(dmatrix) + 0.5

    # Apply first-stage spike booster
    spike_model = _load_spike_model()
    spike_adj_total = np.zeros(len(preds_med))
    
    if spike_model is not None:
        spike_adj = spike_model.predict(dmatrix)
        
        # Conservative scaling for first-stage booster
        spike_adj_scaled = spike_adj.copy()
        
        if len(spike_adj) > 10:
            # Extreme spikes (top 10%) get 2.0x multiplier
            extreme_spike_mask = spike_adj > np.percentile(spike_adj, 90)
            spike_adj_scaled[extreme_spike_mask] *= 2.0
            
            # Super-extreme spikes (top 5%) get 3.0x multiplier
            super_extreme_mask = spike_adj > np.percentile(spike_adj, 95)
            spike_adj_scaled[super_extreme_mask] *= (3.0 / 2.0)  # 3.0x total
            
            # Ultra-extreme spikes (top 1%) get 4.0x multiplier
            ultra_extreme_mask = spike_adj > np.percentile(spike_adj, 99)
            spike_adj_scaled[ultra_extreme_mask] *= (4.0 / 3.0)  # 4.0x total
        else:
            extreme_mask = spike_adj > 30
            spike_adj_scaled[extreme_mask] *= 2.0
            super_extreme_mask = spike_adj > 60
            spike_adj_scaled[super_extreme_mask] *= 2.0  # 4.0x total
        
        spike_adj_total += spike_adj_scaled
    
    # Apply second-stage EXTREME spike booster
    extreme_spike_model = _load_extreme_spike_model()
    if extreme_spike_model is not None:
        extreme_adj = extreme_spike_model.predict(dmatrix)
        
        # Moderate scaling for second-stage booster (5x-8x)
        extreme_adj_scaled = extreme_adj.copy()
        
        if len(extreme_adj) > 10:
            # Top 10% get 5.0x multiplier
            extreme_mask = extreme_adj > np.percentile(extreme_adj, 90)
            extreme_adj_scaled[extreme_mask] *= 5.0
            
            # Top 5% get 6.5x multiplier
            super_extreme_mask = extreme_adj > np.percentile(extreme_adj, 95)
            extreme_adj_scaled[super_extreme_mask] *= (6.5 / 5.0)  # 6.5x total
            
            # Top 1% get 8.0x multiplier
            ultra_extreme_mask = extreme_adj > np.percentile(extreme_adj, 99)
            extreme_adj_scaled[ultra_extreme_mask] *= (8.0 / 6.5)  # 8.0x total
        else:
            extreme_mask = extreme_adj > 20
            extreme_adj_scaled[extreme_mask] *= 5.0
            super_extreme_mask = extreme_adj > 40
            extreme_adj_scaled[super_extreme_mask] *= 1.6  # 8.0x total
        
        spike_adj_total += extreme_adj_scaled
    
    # Apply total spike adjustment
    if np.any(spike_adj_total != 0):
        preds_med += spike_adj_total
        preds_low += spike_adj_total
        preds_up += spike_adj_total
        
        # Moderate quantile band widening for extreme predictions
        extreme_pred_mask = preds_med > np.percentile(preds_med, 90) if len(preds_med) > 10 else preds_med > 200
        if np.any(extreme_pred_mask):
            # Widen bands by 50% for extreme predictions
            band_width = preds_up[extreme_pred_mask] - preds_low[extreme_pred_mask]
            center = (preds_up[extreme_pred_mask] + preds_low[extreme_pred_mask]) / 2
            preds_low[extreme_pred_mask] = center - band_width * 0.75
            preds_up[extreme_pred_mask] = center + band_width * 0.75
        
        # Log extreme adjustments
        max_adj = np.max(spike_adj_total)
        max_pred = np.max(preds_med)
        if max_adj > 50:  # Only log if significant
            logger.info(f"🔺 Extreme spike correction: max_adj={max_adj:.2f}, max_pred={max_pred:.2f}")

    preds_low = np.minimum(preds_low, preds_med - 1e-6)
    preds_up = np.maximum(preds_up, preds_med + 1e-6)

    return preds_low, preds_med, preds_up


def _predict_tft(df_model: pd.DataFrame, device: str = "cpu"):
    X_np = df_model.to_numpy().astype(np.float32)
    model = TFTQuantileModel(len(XGB_FEATURES))
    load_tft_model(model, "models/global_tft.pt", map_location=device)
    model.to(device)
    with torch.no_grad():
        preds = model(torch.from_numpy(X_np).to(device)).cpu().numpy()
    return preds


def predict_df(df: pd.DataFrame, mode: str = "xgb", weight_tft: float = 0.6):
    if mode not in {"xgb", "tft", "ensemble"}:
        raise ValueError("mode must be one of {'xgb','tft','ensemble'}")

    if mode == "ensemble":
        return predict_ensemble(df, weight_tft=weight_tft)

    logger.info(f"📌 Running prediction pipeline ({mode}) with 40 features...")
    df_model = _prepare_features(df)
    preds_low, preds_med, preds_up = _predict_xgb(df_model)

    if mode == "tft":
        tft_median = _predict_tft(df_model)
        preds_med = 0.6 * tft_median + 0.4 * preds_med

    return pd.DataFrame({
        "lower": preds_low,
        "median": preds_med,
        "upper": preds_up,
        "date": df["date"].values
    })

