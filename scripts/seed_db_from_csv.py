"""
One-Time Data Seed: CSV → PostgreSQL

Populates hospitals, admission_history, and external_signals tables
from the original CSV so the system can go fully DB-driven.

Usage:
    python -m scripts.seed_db_from_csv

This is a one-time operation. After seeding, the CSV is never used again
in the production path.
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy.dialects.postgresql import insert

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database.session import SessionLocal
from database.models import Hospital, AdmissionHistory, ExternalSignal
from forecast_system.utils import get_logger

logger = get_logger(__name__)

CSV_PATH = "dataset/synthetic_hospital_data.csv"


def seed(csv_path: str = CSV_PATH) -> None:
    print(f"[{datetime.now(timezone.utc).isoformat()}] Seeding DB from {csv_path} ...")

    csv_file = Path(csv_path)
    if not csv_file.exists():
        # Try relative to project root
        csv_file = Path(__file__).resolve().parent.parent / csv_path
    if not csv_file.exists():
        print(f"FATAL: CSV not found at {csv_path}")
        sys.exit(1)

    df = pd.read_csv(str(csv_file), parse_dates=["date"])
    print(f"  Loaded CSV: {len(df)} rows, {df['hospital_id'].nunique()} hospitals")

    db = SessionLocal()
    try:
        # ---------------------------------------------------------------
        # 1. Upsert Hospitals
        # ---------------------------------------------------------------
        hospital_meta = (
            df.groupby("hospital_id")
            .agg(
                {
                    "population": "first",
                    "population_density": "first",
                    "elderly_ratio": "first",
                    "hospital_capacity": "first",
                    "icu_capacity": "first",
                }
            )
            .reset_index()
        )

        hospital_map = {}  # hospital_id str -> UUID
        for _, row in hospital_meta.iterrows():
            hosp_id = row["hospital_id"]
            existing = (
                db.query(Hospital)
                .filter(Hospital.hospital_id == hosp_id)
                .first()
            )
            if existing:
                # Update metadata
                existing.capacity = int(row["hospital_capacity"])
                existing.population = int(row["population"])
                existing.population_density = float(row["population_density"])
                existing.elderly_ratio = float(row["elderly_ratio"])
                existing.icu_capacity = int(row["icu_capacity"])
                hospital_map[hosp_id] = existing.id
            else:
                new_hosp = Hospital(
                    hospital_id=hosp_id,
                    name=hosp_id.replace("_", " ").title(),
                    capacity=int(row["hospital_capacity"]),
                    population=int(row["population"]),
                    population_density=float(row["population_density"]),
                    elderly_ratio=float(row["elderly_ratio"]),
                    icu_capacity=int(row["icu_capacity"]),
                )
                db.add(new_hosp)
                db.flush()
                hospital_map[hosp_id] = new_hosp.id

        db.commit()
        print(f"  Hospitals upserted: {len(hospital_map)}")

        # ---------------------------------------------------------------
        # 2. Upsert AdmissionHistory (batch by chunks)
        # ---------------------------------------------------------------
        CHUNK = 2000
        admission_count = 0
        admission_rows = []
        for _, row in df.iterrows():
            admission_rows.append(
                {
                    "id": uuid.uuid4(),
                    "hospital_id": hospital_map[row["hospital_id"]],
                    "date": row["date"].date() if hasattr(row["date"], "date") else row["date"],
                    "admissions": int(row["admissions"]),
                    "created_at": datetime.utcnow(),
                }
            )
            if len(admission_rows) >= CHUNK:
                _upsert_admissions(db, admission_rows)
                admission_count += len(admission_rows)
                admission_rows = []

        if admission_rows:
            _upsert_admissions(db, admission_rows)
            admission_count += len(admission_rows)

        db.commit()
        print(f"  Admission history upserted: {admission_count}")

        # ---------------------------------------------------------------
        # 3. Upsert ExternalSignals (historical)
        # ---------------------------------------------------------------
        signal_count = 0
        signal_rows = []
        signal_cols = {"temperature", "aqi", "outbreak_index", "mobility_index"}
        has_signals = signal_cols.issubset(set(df.columns))

        if has_signals:
            for _, row in df.iterrows():
                signal_rows.append(
                    {
                        "id": uuid.uuid4(),
                        "hospital_id": hospital_map[row["hospital_id"]],
                        "date": row["date"].date() if hasattr(row["date"], "date") else row["date"],
                        "temperature": float(row.get("temperature", 0.0)),
                        "aqi": float(row.get("aqi", 0.0)),
                        "outbreak_index": float(row.get("outbreak_index", 0.0)),
                        "mobility_index": float(row.get("mobility_index", 0.0)),
                        "created_at": datetime.utcnow(),
                    }
                )
                if len(signal_rows) >= CHUNK:
                    _upsert_signals(db, signal_rows)
                    signal_count += len(signal_rows)
                    signal_rows = []

            if signal_rows:
                _upsert_signals(db, signal_rows)
                signal_count += len(signal_rows)

            db.commit()
            print(f"  External signals upserted: {signal_count}")
        else:
            print("  [SKIP] CSV has no external signal columns")

    except Exception as exc:
        db.rollback()
        print(f"FATAL: {exc}")
        raise
    finally:
        db.close()

    print(f"[{datetime.now(timezone.utc).isoformat()}] Seed complete.")


def _upsert_admissions(db, rows):
    stmt = insert(AdmissionHistory).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["hospital_id", "date"],
        set_={"admissions": stmt.excluded.admissions},
    )
    db.execute(stmt)


def _upsert_signals(db, rows):
    stmt = insert(ExternalSignal).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["hospital_id", "date"],
        set_={
            "temperature": stmt.excluded.temperature,
            "aqi": stmt.excluded.aqi,
            "outbreak_index": stmt.excluded.outbreak_index,
            "mobility_index": stmt.excluded.mobility_index,
            "created_at": stmt.excluded.created_at,
        },
    )
    db.execute(stmt)


if __name__ == "__main__":
    seed()

