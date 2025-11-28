import numpy as np
import pandas as pd
import torch

from .tft_model import TFTQuantileModel, load_tft_model
from src.pipeline.feature_engineering import feature_engineering_xgb
from src.pipeline.logger import get_logger
from src.pipeline.utils import load_model

logger = get_logger(__name__)

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
    "lag1_aqi","lag7_outbreak","rolling_aqi"
]


def _load_tft_global_model(input_dim: int, device: str):
    model = TFTQuantileModel(input_dim)
    load_tft_model(model, "models/global_tft.pt", map_location=device)
    model.to(device)
    return model


def predict_ensemble(df: pd.DataFrame, weight_tft: float = 0.6, device: str = "cpu") -> pd.DataFrame:
    logger.info("🔮 Running ensemble prediction (XGB + TFT)...")

    df_fe = feature_engineering_xgb(df.copy())
    missing = [f for f in XGB_FEATURES if f not in df_fe.columns]
    if missing:
        raise ValueError(f"🚨 Missing features for ensemble: {missing}")

    X = df_fe[XGB_FEATURES].astype(np.float32)
    X_np = X.to_numpy()
    torch_inputs = torch.from_numpy(X_np).to(device)

    xgb_q10 = load_model("models/global_q10.model")
    xgb_q50 = load_model("models/global_q50.model")
    xgb_q90 = load_model("models/global_q90.model")

    xgb_preds_q10 = xgb_q10.predict(X_np) - 0.5
    xgb_preds_q50 = xgb_q50.predict(X_np)
    xgb_preds_q90 = xgb_q90.predict(X_np) + 0.5

    tft_model = _load_tft_global_model(X_np.shape[1], device=device)
    tft_median = tft_model(torch_inputs).detach().cpu().numpy()

    w_tft = weight_tft
    w_xgb = 1.0 - w_tft

    median = w_tft * tft_median + w_xgb * xgb_preds_q50
    lower = np.minimum(xgb_preds_q10, median - 1.0)
    upper = np.maximum(xgb_preds_q90, median + 1.0)

    return pd.DataFrame({
        "lower": lower,
        "median": median,
        "upper": upper,
        "date": df["date"].values
    })

