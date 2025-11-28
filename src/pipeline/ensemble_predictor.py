import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pandas as pd
import torch
import xgboost as xgb

from src.pipeline.feature_engineering_unified import build_features, XGB_FEATURES
from src.pipeline.utils import load_model
from src.pipeline.logger import get_logger
from src.models.tft_model import TFTQuantileModel, load_tft_model

logger = get_logger(__name__)


# -----------------------------------------------------------------------------
#  Helper: Load XGBoost quantile models
# -----------------------------------------------------------------------------
def _load_xgb_models(
    model_dir: str = "models",
    q10_name: str = "global_q10.json",
    q50_name: str = "global_q50.json",
    q90_name: str = "global_q90.json",
) -> Tuple[xgb.Booster, xgb.Booster, xgb.Booster]:

    logger.info(f"📦 Loading XGBoost models from {model_dir} ...")

    p10 = Path(model_dir) / q10_name
    p50 = Path(model_dir) / q50_name
    p90 = Path(model_dir) / q90_name

    model_q10 = load_model(str(p10))
    model_q50 = load_model(str(p50))
    model_q90 = load_model(str(p90))

    return model_q10, model_q50, model_q90


def _load_spike_model(path: str = "models/global_q50_spike.json") -> Optional[xgb.Booster]:
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


def _load_extreme_spike_model(path: str = "models/global_q50_extreme_spike.json") -> Optional[xgb.Booster]:
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


# -----------------------------------------------------------------------------
#  Helper: Load TFT model safely with fallbacks
# -----------------------------------------------------------------------------
def _load_tft_global(
    input_dim: int,
    model_path: str = "models/tft_global_q50.pth",
    device: Optional[str] = None,
) -> Optional[torch.nn.Module]:

    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    path = Path(model_path)

    # Fallback to older naming
    if not path.exists():
        legacy = Path("models/global_tft.pt")
        if legacy.exists():
            logger.info(f"🟡 TFT not found at {path}, falling back to {legacy}")
            path = legacy
        else:
            logger.warning("⚠️ No TFT model found → XGB-only ensemble will be used.")
            return None

    logger.info(f"📥 Loading TFT model from {path} on device={device} ...")

    try:
        obj = torch.load(str(path), map_location=device, weights_only=False)
    except TypeError:
        obj = torch.load(str(path), map_location=device)

    # Case A: Full torch module saved directly
    if isinstance(obj, torch.nn.Module):
        obj.to(device)
        obj.eval()
        return obj

    # Case B: state_dict saved
    try:
        model = TFTQuantileModel(input_dim)
        model.load_state_dict(obj)
        model.to(device)
        model.eval()
        return model
    except Exception as e:
        logger.warning(
            f"❌ Failed loading TFT weights ({e}) → falling back to XGB-only ensemble."
        )
        return None


# -----------------------------------------------------------------------------
#  ENSEMBLE PREDICTION
# -----------------------------------------------------------------------------
def predict_ensemble(
    df: pd.DataFrame,
    weight_tft: float = 0.6,
    device: str = "cpu"
) -> pd.DataFrame:

    logger.info("🔮 Running ensemble prediction (XGB + TFT)...")

    # --------------------- Step 1: Feature Engineering -----------------------
    X = build_features(df)
    X_np = X.to_numpy()
    dmat = xgb.DMatrix(X_np, feature_names=XGB_FEATURES)

    # --------------------- Step 2: Load XGB Models ---------------------------
    xgb_q10, xgb_q50, xgb_q90 = _load_xgb_models()

    x10 = xgb_q10.predict(dmat)
    x50 = xgb_q50.predict(dmat)
    x90 = xgb_q90.predict(dmat)

    # Apply two-stage spike correction
    spike_adj_total = np.zeros(len(x50))
    
    # First-stage spike booster
    spike_model = _load_spike_model()
    if spike_model is not None:
        spike_adj = spike_model.predict(dmat)
        
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
    
    # Second-stage EXTREME spike booster
    extreme_spike_model = _load_extreme_spike_model()
    if extreme_spike_model is not None:
        extreme_adj = extreme_spike_model.predict(dmat)
        
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
        x10 += spike_adj_total
        x50 += spike_adj_total
        x90 += spike_adj_total
        
        # Moderate quantile band widening for extreme predictions
        extreme_pred_mask = x50 > np.percentile(x50, 90) if len(x50) > 10 else x50 > 200
        if np.any(extreme_pred_mask):
            # Widen bands by 50% for extreme predictions
            band_width = x90[extreme_pred_mask] - x10[extreme_pred_mask]
            center = (x90[extreme_pred_mask] + x10[extreme_pred_mask]) / 2
            x10[extreme_pred_mask] = center - band_width * 0.75
            x90[extreme_pred_mask] = center + band_width * 0.75

    # --------------------- Step 3: Load TFT Model ---------------------------
    input_dim = X_np.shape[1]
    tft_model = _load_tft_global(input_dim=input_dim, device=device)

    if tft_model is None:
        # Use XGB median only
        logger.info("➡️ Using XGB-only predictions (no TFT).")
        return pd.DataFrame({
            "date": df["date"].values,
            "lower": x10,
            "median": x50,
            "upper": x90,
        })

    # --------------------- Step 4: TFT Inference ----------------------------
    torch_inputs = torch.from_numpy(X_np).to(device)
    tft_pred = tft_model(torch_inputs).detach().cpu().numpy()

    # --------------------- Step 5: Blend TFT + XGB Median -------------------
    w_tft = weight_tft
    w_xgb = 1.0 - w_tft

    median = (w_tft * tft_pred) + (w_xgb * x50)

    # --------------------- Step 6: FIXED QUANTILE CONSISTENCY ---------------
    # Expand lower/upper margins to prevent upper < median issues
    x10_adj = x10 - 1.5
    x90_adj = x90 + 1.5

    lower = np.minimum(x10_adj, median - 2.0)
    upper = np.maximum(x90_adj, median + 2.0)

    # Hard guarantee: upper must be above lower
    upper = np.maximum(upper, lower + 0.1)

    # --------------------- Step 7: Final Output ------------------------------
    out = pd.DataFrame({
        "date": df["date"].values,
        "lower": lower,
        "median": median,
        "upper": upper,
    })

    logger.info(f"✅ Ensemble prediction complete: {len(out)} rows")
    return out
