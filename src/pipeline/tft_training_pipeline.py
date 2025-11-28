import os
from typing import Dict
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

from pathlib import Path
import pandas as pd

from .feature_engineering_unified import build_features, XGB_FEATURES
from ..models.tft_model import TFTQuantileModel
from .logger import get_logger

logger = get_logger(__name__)



def _load_tft_dataset(base_dir: str = "generated_datasets_ml_ready/tft") -> pd.DataFrame:
    """Load every *_tft.csv file and combine into one dataframe."""
    base = Path(base_dir)
    csv_files = sorted(base.glob("*_tft.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No TFT CSV files found in {base_dir}")

    frames = []
    for path in csv_files:
        df = pd.read_csv(path, parse_dates=["date"])
        df["city"] = path.stem.replace("_tft", "").capitalize()
        frames.append(df)

    df_all = pd.concat(frames, ignore_index=True)

    if "hospital_id" not in df_all.columns:
        if "group_id" in df_all.columns:
            df_all["hospital_id"] = df_all["group_id"]
        elif "hospital_id_enc" in df_all.columns:
            df_all["hospital_id"] = (
                df_all["city"].astype(str) + "_" + df_all["hospital_id_enc"].astype(str)
            )
        else:
            df_all["hospital_id"] = (
                df_all.groupby("city").cumcount().astype(str).radd(df_all["city"].astype(str) + "_")
            )

    df_all = df_all.sort_values(["city", "hospital_id", "date"]).reset_index(drop=True)
    return df_all


def run_tft_training(
    output_dir: str = "models",
    batch_size: int = 64,
    epochs: int = 30,
    lr: float = 1e-3,
    device: str = "cuda" if torch.cuda.is_available() else "cpu",
    base_dir: str = "generated_datasets_ml_ready/tft"
) -> Dict[str, float]:
    os.makedirs(output_dir, exist_ok=True)

    logger.info("📥 Loading TFT dataset (all cities)...")
    df = _load_tft_dataset(base_dir)

    logger.info("🔧 Building unified features for TFT (41 XGB features)...")
    X_np = build_features(df).astype(np.float32).values
    # Use raw admissions from the loaded TFT dataframe as target
    y_np = df["admissions"].astype(np.float32).values

    dataset = TensorDataset(torch.from_numpy(X_np), torch.from_numpy(y_np))
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

    input_dim = X_np.shape[1]  # should be 41
    model = TFTQuantileModel(input_dim=input_dim, hidden_dim=128).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = torch.nn.L1Loss()

    best_loss = float("inf")
    patience = 5
    wait = 0

    logger.info("🚀 Training global TFT median model...")
    for epoch in range(epochs):
        model.train()
        total_loss = 0.0
        for xb, yb in loader:
            xb = xb.to(device)
            yb = yb.to(device)
            optimizer.zero_grad()
            preds = model(xb)
            loss = criterion(preds, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            total_loss += loss.item()
        avg_loss = total_loss / max(len(loader), 1)
        logger.info(f"[TFT] epoch {epoch+1}/{epochs} - loss={avg_loss:.4f}")

        if avg_loss < best_loss - 1e-4:
            best_loss = avg_loss
            wait = 0
            # Save full module for prediction as requested
            save_path = os.path.join(output_dir, "tft_global_q50.pth")
            torch.save(model.cpu(), save_path)
            logger.info(f"💾 Saved TFT global median model to {save_path}")
            model.to(device)
        else:
            wait += 1
            if wait >= patience:
                logger.info(f"[TFT] Early stopping at epoch {epoch+1}")
                break

    logger.info("✅ TFT training complete (global median model).")
    return {"loss": best_loss}

