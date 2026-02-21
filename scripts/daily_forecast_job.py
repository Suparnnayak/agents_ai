"""
Daily Forecast Job — Precomputed Forecasts

Standalone script that:
  1. Loads the model bundle from disk
  2. Fetches latest admission history + hospital metadata from DB
  3. Fetches latest external signals from DB
  4. Predicts next 7 days for every hospital
  5. UPSERTs forecasts into the `forecasts` table
  6. Creates a `forecast_runs` record for traceability

Designed to run via GitHub Actions cron (daily at 2:30 AM UTC),
local scheduler, or manually.

No FastAPI dependency. Exits with code 1 on failure.

Usage:
    python -m scripts.daily_forecast_job
"""

import sys
import os
import time
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.session import SessionLocal
from database import crud
from database.models import Hospital, ExternalSignal
from forecast_system.model_bundle import ModelBundle
from forecast_system.inference import forecast
from forecast_system.db_loader import load_inference_dataframe
from app.services.external_data_service import get_latest_external_signals_by_hospital
from forecast_system.utils import get_logger

logger = get_logger(__name__)

MODEL_PATH = "models/forecast_system/lightgbm_final.pkl"
HORIZONS = [1, 2, 3, 4, 5, 6, 7]


def main() -> int:
    start = time.time()
    ts = datetime.now(timezone.utc).isoformat()
    print(f"[{ts}] Daily Forecast Job starting ...")

    # ------------------------------------------------------------------
    # 1. Load model
    # ------------------------------------------------------------------
    model_paths = [
        MODEL_PATH,
        Path(__file__).resolve().parent.parent / MODEL_PATH,
    ]
    bundle = None
    model_path_used = None
    for p in model_paths:
        p_str = str(p)
        if os.path.exists(p_str):
            bundle = ModelBundle.load(p_str)
            model_path_used = p_str
            break

    if bundle is None:
        print("FATAL: Model bundle not found")
        return 1

    print(f"  Model loaded from: {model_path_used}")

    # Determine model version
    model_version = "1.0.0"
    # Check for versioned model files
    model_dir = Path(model_path_used).parent
    if model_dir.exists():
        versioned = sorted(model_dir.glob("model_v*.pkl"))
        if versioned:
            latest = versioned[-1].stem  # e.g. model_v20260221
            model_version = latest.replace("model_", "")

    # ------------------------------------------------------------------
    # 2. Open DB session and load data
    # ------------------------------------------------------------------
    db = SessionLocal()
    try:
        hospitals = db.query(Hospital).all()
        if not hospitals:
            print("FATAL: No hospitals in database. Run seed script first.")
            return 1

        hospital_ids = sorted([h.hospital_id for h in hospitals])
        print(f"  Hospitals: {len(hospital_ids)}")

        # Load admission history from DB (last 60 days for lag computation)
        raw_df = load_inference_dataframe(db, days=60)
        if raw_df.empty:
            print("FATAL: No admission history in database. Run seed script first.")
            return 1

        # Get latest external signals
        external_signals = get_latest_external_signals_by_hospital(db, hospital_ids)
        signal_count = len(external_signals)
        print(f"  External signals available for {signal_count}/{len(hospital_ids)} hospitals")

        # Determine signal date used
        signal_date = crud.get_latest_signal_date(db)
        print(f"  Latest signal date: {signal_date}")

        # ------------------------------------------------------------------
        # 3. Run inference
        # ------------------------------------------------------------------
        print(f"  Running inference for {len(hospital_ids)} hospitals, horizons {HORIZONS} ...")
        forecast_df = forecast(
            bundle=bundle,
            raw_df=raw_df.copy(deep=True),
            horizons=HORIZONS,
            external_signals_by_hospital=external_signals,
        )

        if forecast_df.empty:
            print("FATAL: Forecast returned empty results")
            return 1

        inference_time = time.time() - start
        print(
            f"  Inference complete: {len(forecast_df)} forecasts in {inference_time:.2f}s"
        )

        # ------------------------------------------------------------------
        # 4. Create forecast_run record
        # ------------------------------------------------------------------
        forecast_run = crud.create_forecast_run(
            db=db,
            hospital_count=len(hospital_ids),
            horizon_count=len(HORIZONS),
            total_forecasts=len(forecast_df),
            inference_time_seconds=inference_time,
            model_version=model_version,
            signal_date_used=signal_date,
        )
        run_id = forecast_run.id

        # ------------------------------------------------------------------
        # 5. UPSERT forecasts
        # ------------------------------------------------------------------
        # Compute forecast_date = last admission date + horizon
        last_dates = {}
        for hosp_id in forecast_df["hospital_id"].unique():
            hosp_data = raw_df[raw_df["hospital_id"] == hosp_id]
            if not hosp_data.empty:
                import pandas as pd
                last_date = pd.to_datetime(hosp_data["date"]).max()
                last_dates[hosp_id] = last_date.to_pydatetime().date()

        forecasts_data = []
        for _, row in forecast_df.iterrows():
            hospital_id_str = str(row["hospital_id"])
            horizon = int(row["horizon"])
            prediction = float(row["prediction"])

            base_date = last_dates.get(hospital_id_str, date.today())
            forecast_date = base_date + timedelta(days=horizon)

            forecasts_data.append(
                {
                    "hospital_id": hospital_id_str,
                    "horizon": horizon,
                    "prediction": prediction,
                    "forecast_date": forecast_date,
                }
            )

        crud.create_forecasts_batch(
            db=db,
            forecast_run_id=run_id,
            forecasts_data=forecasts_data,
        )

        db.commit()

        # ------------------------------------------------------------------
        # 6. Summary
        # ------------------------------------------------------------------
        total_time = time.time() - start
        print(f"\n  === Daily Forecast Summary ===")
        print(f"  run_id            : {run_id}")
        print(f"  model_version     : {model_version}")
        print(f"  signal_date_used  : {signal_date}")
        print(f"  hospitals         : {len(hospital_ids)}")
        print(f"  forecasts_inserted: {len(forecasts_data)}")
        print(f"  total_time        : {total_time:.2f}s")
        print(f"[{datetime.now(timezone.utc).isoformat()}] Done.")
        return 0

    except Exception as exc:
        db.rollback()
        logger.exception(f"Daily forecast job failed: {exc}")
        print(f"FATAL: {exc}")
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())

