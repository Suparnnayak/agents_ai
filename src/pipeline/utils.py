import pickle
import joblib
from pathlib import Path

import xgboost as xgb
import lightgbm as lgb
import torch

from .logger import get_logger

logger = get_logger(__name__)


def save_model(model, filepath: Path):
    """
    Save model to disk with standardized formats.

    - XGBoost Booster/XGBModel → .json
    - LightGBM Booster → .txt
    - PyTorch nn.Module → .pt
    - Other (sklearn etc.) → .joblib
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    base = filepath.with_suffix("")  # strip whatever suffix was passed

    try:
        # XGBoost: always JSON
        if isinstance(model, (xgb.Booster, xgb.XGBModel)):
            target = base.with_suffix(".json")
            model.save_model(str(target))
            logger.info(f"✅ Saved XGBoost model to {target}")

        # LightGBM: always TXT
        elif isinstance(model, lgb.Booster):
            target = base.with_suffix(".txt")
            model.save_model(str(target))
            logger.info(f"✅ Saved LightGBM model to {target}")

        # PyTorch/TFT: always PT
        elif isinstance(model, torch.nn.Module):
            target = base.with_suffix(".pt")
            torch.save(model.state_dict(), target)
            logger.info(f"✅ Saved Torch model state_dict to {target}")

        # Fallback: joblib for sklearn/others
        else:
            target = base.with_suffix(".joblib")
            joblib.dump(model, target)
            logger.info(f"✅ Saved generic model with joblib to {target}")

    except Exception as e:
        logger.error(f"❌ Failed to save model to {filepath}: {e}")
        raise


def _resolve_legacy_path(filepath: Path) -> Path:
    """
    Handle legacy .model paths by mapping to new standardized files if present.
    """
    if filepath.suffix.lower() != ".model":
        return filepath

    base = filepath.with_suffix("")
    # Prefer JSON (XGBoost), then TXT (LightGBM), then joblib/PT
    for ext in [".json", ".txt", ".joblib", ".pt"]:
        candidate = base.with_suffix(ext)
        if candidate.exists():
            return candidate
    return filepath


def load_model(filepath: str):
    """
    Load model from disk based on extension.

    - .json  → XGBoost Booster
    - .txt   → LightGBM Booster
    - .pt    → Torch state_dict (returned as-is)
    - .joblib → joblib-loaded object (e.g., sklearn)

    Also supports legacy .model paths by redirecting to the corresponding
    .json/.txt/.joblib/.pt file when present.
    """
    filepath = Path(filepath)

    if not filepath.exists():
        # Try resolving legacy mapping (e.g., x.model → x.json)
        resolved = _resolve_legacy_path(filepath)
        if not resolved.exists():
            raise FileNotFoundError(f"Model file not found: {filepath}")
        filepath = resolved

    suffix = filepath.suffix.lower()

    try:
        # XGBoost JSON
        if suffix == ".json":
            booster = xgb.Booster()
            booster.load_model(str(filepath))
            logger.info(f"✅ Loaded XGBoost model from {filepath}")
            return booster

        # LightGBM TXT
        if suffix == ".txt":
            booster = lgb.Booster(model_file=str(filepath))
            logger.info(f"✅ Loaded LightGBM model from {filepath}")
            return booster

        # Torch PT (return state_dict; caller must load into model)
        if suffix == ".pt":
            state = torch.load(str(filepath), map_location="cpu")
            logger.info(f"✅ Loaded Torch state_dict from {filepath}")
            return state

        # joblib
        if suffix == ".joblib":
            model = joblib.load(str(filepath))
            logger.info(f"✅ Loaded joblib model from {filepath}")
            return model

        # Legacy .model or unknown: try XGBoost → LightGBM → pickle
        try:
            booster = xgb.Booster()
            booster.load_model(str(filepath))
            logger.info(f"✅ Loaded XGBoost model from {filepath}")
            return booster
        except Exception:
            pass

        try:
            booster = lgb.Booster(model_file=str(filepath))
            logger.info(f"✅ Loaded LightGBM model from {filepath}")
            return booster
        except Exception:
            pass

        # Fallback to pickle
        with open(filepath, "rb") as f:
            model = pickle.load(f)
        logger.info(f"✅ Loaded model from {filepath} via pickle fallback")
        return model

    except Exception as e:
        logger.error(f"❌ Failed to load model from {filepath}: {e}")
        raise
