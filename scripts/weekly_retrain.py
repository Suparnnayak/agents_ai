"""
Weekly Retrain Job

Standalone script that:
  1. Loads full admission_history from DB
  2. Performs feature engineering
  3. Trains a new LightGBM model
  4. Saves as versioned model file
  5. Copies to lightgbm_final.pkl (production pointer)

Designed to run via GitHub Actions cron (Sunday 3:00 AM UTC),
or manually.

No FastAPI dependency. Exits with code 1 on failure.

Usage:
    python -m scripts.weekly_retrain
"""

import sys
import os
import shutil
import time
import json
from datetime import datetime, date, timezone
from pathlib import Path

import numpy as np

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.session import SessionLocal
from forecast_system.db_loader import load_training_dataframe
from forecast_system.features import create_features
from forecast_system.model_bundle import ModelBundle
from forecast_system.utils import get_logger

logger = get_logger(__name__)

OUTPUT_DIR = "models/forecast_system"


def main() -> int:
    start = time.time()
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[{ts}] Weekly Retrain Job starting ...")

    # ------------------------------------------------------------------
    # 1. Load training data from DB
    # ------------------------------------------------------------------
    db = SessionLocal()
    try:
        print("  [1/5] Loading training data from database ...")
        df = load_training_dataframe(db)
    except Exception as exc:
        logger.exception(f"Failed to load training data: {exc}")
        print(f"FATAL: {exc}")
        db.close()
        return 1
    finally:
        db.close()

    if df.empty:
        print("FATAL: No training data found in database. Run seed script first.")
        return 1

    print(f"         Rows: {len(df)}, Hospitals: {df['hospital_id'].nunique()}")
    print(f"         Date range: {df['date'].min()} to {df['date'].max()}")

    # ------------------------------------------------------------------
    # 2. Feature engineering
    # ------------------------------------------------------------------
    print("  [2/5] Creating features ...")
    try:
        X, y, encoders = create_features(df)
    except Exception as exc:
        logger.exception(f"Feature engineering failed: {exc}")
        print(f"FATAL: {exc}")
        return 1

    print(f"         Features: {len(X.columns)} columns, {len(X)} samples")
    print(f"         Feature columns: {list(X.columns)}")

    # ------------------------------------------------------------------
    # 3. Train/test split + LightGBM training
    # ------------------------------------------------------------------
    print("  [3/5] Training LightGBM model ...")
    try:
        from lightgbm import LGBMRegressor, early_stopping
        from sklearn.model_selection import train_test_split

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )

        model = LGBMRegressor(
            n_estimators=500,
            learning_rate=0.05,
            max_depth=6,
            random_state=42,
            verbose=-1,
        )

        model.fit(
            X_train,
            y_train,
            eval_set=[(X_test, y_test)],
            eval_metric="mae",
            callbacks=[early_stopping(stopping_rounds=50, verbose=False)],
        )

        train_pred = model.predict(X_train)
        test_pred = model.predict(X_test)

        train_mae = float(np.mean(np.abs(train_pred - y_train)))
        test_mae = float(np.mean(np.abs(test_pred - y_test)))

        print(f"         Train MAE: {train_mae:.2f}")
        print(f"         Test MAE:  {test_mae:.2f}")

    except Exception as exc:
        logger.exception(f"Training failed: {exc}")
        print(f"FATAL: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 4. Create ModelBundle + Save versioned model
    # ------------------------------------------------------------------
    print("  [4/5] Saving model bundle ...")
    try:
        bundle = ModelBundle(
            model=model,
            feature_columns=list(X.columns),
            encoders=encoders,
        )

        output_path = Path(OUTPUT_DIR)
        output_path.mkdir(parents=True, exist_ok=True)

        # Version string: vYYYYMMDD
        version_str = f"v{date.today().strftime('%Y%m%d')}"
        versioned_path = output_path / f"model_{version_str}.pkl"
        production_path = output_path / "lightgbm_final.pkl"

        bundle.save(str(versioned_path))
        print(f"         Versioned model: {versioned_path}")

        # Copy to production pointer
        shutil.copy2(str(versioned_path), str(production_path))
        print(f"         Production model: {production_path}")

    except Exception as exc:
        logger.exception(f"Model save failed: {exc}")
        print(f"FATAL: {exc}")
        return 1

    # ------------------------------------------------------------------
    # 5. Save metrics
    # ------------------------------------------------------------------
    print("  [5/5] Saving metrics ...")
    try:
        metrics = {
            "model_version": version_str,
            "trained_at": datetime.now(timezone.utc).isoformat(),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "train_mae": train_mae,
            "test_mae": test_mae,
            "feature_count": len(X.columns),
            "feature_columns": list(X.columns),
            "hospitals": int(df["hospital_id"].nunique()),
            "date_range_start": str(df["date"].min().date()),
            "date_range_end": str(df["date"].max().date()),
            "total_rows": len(df),
        }

        metrics_path = output_path / "evaluation_metrics.json"
        with open(str(metrics_path), "w") as f:
            json.dump(metrics, f, indent=2)
        print(f"         Metrics saved: {metrics_path}")

    except Exception as exc:
        logger.warning(f"Metrics save failed (non-fatal): {exc}")

    total_time = time.time() - start
    print(f"\n  === Weekly Retrain Summary ===")
    print(f"  model_version : {version_str}")
    print(f"  train_mae     : {train_mae:.2f}")
    print(f"  test_mae      : {test_mae:.2f}")
    print(f"  total_time    : {total_time:.2f}s")
    print(f"[{datetime.now(timezone.utc).isoformat()}] Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

