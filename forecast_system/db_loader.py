"""
Database-Driven Data Loader

Loads admission history, hospital metadata, and external signals from PostgreSQL.
Produces DataFrames compatible with the existing inference pipeline.

NO CSV dependency. DB is the single source of truth.
"""

import pandas as pd
from datetime import date, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import asc

from database.models import Hospital, AdmissionHistory, ExternalSignal
from forecast_system.utils import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Season helper (matches dataset_generator.py values exactly)
# ---------------------------------------------------------------------------

def get_season(month: int) -> str:
    """Map month to season string matching original training data."""
    if month in (12, 1, 2):
        return "winter"
    elif month in (6, 7, 8):
        return "summer"
    elif month in (9, 10):
        return "monsoon"
    else:
        return "spring"


# ---------------------------------------------------------------------------
# Inference loader (daily forecast job)
# ---------------------------------------------------------------------------

def load_inference_dataframe(db: Session, days: int = 60) -> pd.DataFrame:
    """
    Load the most recent `days` of admission history for ALL hospitals,
    enriched with hospital metadata and temporal features.

    The cutoff is relative to the latest admission date in the DB
    (not today's date), so it works with both historical and live data.

    Returns a DataFrame with columns matching the inference pipeline:
        hospital_id, date, admissions, season,
        temperature, aqi, outbreak_index, mobility_index,
        population, population_density, elderly_ratio,
        hospital_capacity, icu_capacity,
        day_of_week, month, week_of_year, is_weekend
    """
    from sqlalchemy import func as sa_func

    # Determine cutoff relative to latest data in DB (not today)
    max_date = db.query(sa_func.max(AdmissionHistory.date)).scalar()
    if max_date is None:
        logger.warning("No admission history found in DB")
        return pd.DataFrame()

    cutoff = max_date - timedelta(days=days)

    rows = (
        db.query(
            Hospital.hospital_id,
            AdmissionHistory.date,
            AdmissionHistory.admissions,
            Hospital.capacity,
            Hospital.population,
            Hospital.population_density,
            Hospital.elderly_ratio,
            Hospital.icu_capacity,
        )
        .join(AdmissionHistory, AdmissionHistory.hospital_id == Hospital.id)
        .filter(AdmissionHistory.date >= cutoff)
        .order_by(Hospital.hospital_id, AdmissionHistory.date)
        .all()
    )

    if not rows:
        logger.warning("No admission history found in DB")
        return pd.DataFrame()

    records = []
    for row in rows:
        d = row.date
        records.append(
            {
                "hospital_id": row.hospital_id,
                "date": d,
                "admissions": row.admissions,
                "hospital_capacity": row.capacity or 0,
                "population": row.population or 0,
                "population_density": row.population_density or 0.0,
                "elderly_ratio": row.elderly_ratio or 0.0,
                "icu_capacity": row.icu_capacity or 0,
                "day_of_week": d.weekday(),
                "month": d.month,
                "week_of_year": d.isocalendar()[1],
                "is_weekend": 1 if d.weekday() >= 5 else 0,
                "season": get_season(d.month),
                # Defaults — will be overridden if external signals exist
                "temperature": 0.0,
                "aqi": 0.0,
                "outbreak_index": 0.0,
                "mobility_index": 0.0,
            }
        )

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])

    logger.info(
        f"Loaded inference DataFrame: {len(df)} rows, "
        f"{df['hospital_id'].nunique()} hospitals"
    )
    return df


# ---------------------------------------------------------------------------
# Training loader (weekly retrain job)
# ---------------------------------------------------------------------------

def load_training_dataframe(db: Session) -> pd.DataFrame:
    """
    Load the FULL admission history from DB, joined with hospital metadata
    and historical external signals for training.

    This is the DB equivalent of loading the CSV for training.
    """
    rows = (
        db.query(
            Hospital.hospital_id,
            AdmissionHistory.date,
            AdmissionHistory.admissions,
            Hospital.capacity,
            Hospital.population,
            Hospital.population_density,
            Hospital.elderly_ratio,
            Hospital.icu_capacity,
        )
        .join(AdmissionHistory, AdmissionHistory.hospital_id == Hospital.id)
        .order_by(Hospital.hospital_id, AdmissionHistory.date)
        .all()
    )

    if not rows:
        logger.warning("No admission history found in DB for training")
        return pd.DataFrame()

    # Build base records
    records = []
    for row in rows:
        d = row.date
        records.append(
            {
                "hospital_id": row.hospital_id,
                "date": d,
                "admissions": row.admissions,
                "hospital_capacity": row.capacity or 0,
                "population": row.population or 0,
                "population_density": row.population_density or 0.0,
                "elderly_ratio": row.elderly_ratio or 0.0,
                "icu_capacity": row.icu_capacity or 0,
                "day_of_week": d.weekday(),
                "month": d.month,
                "week_of_year": d.isocalendar()[1],
                "is_weekend": 1 if d.weekday() >= 5 else 0,
                "season": get_season(d.month),
                "temperature": 0.0,
                "aqi": 0.0,
                "outbreak_index": 0.0,
                "mobility_index": 0.0,
            }
        )

    df = pd.DataFrame(records)
    df["date"] = pd.to_datetime(df["date"])

    # Overlay historical external signals where available
    _overlay_external_signals(db, df)

    logger.info(
        f"Loaded training DataFrame: {len(df)} rows, "
        f"{df['hospital_id'].nunique()} hospitals, "
        f"date range: {df['date'].min()} to {df['date'].max()}"
    )
    return df


def _overlay_external_signals(db: Session, df: pd.DataFrame) -> None:
    """
    Overlay external signal values onto the DataFrame in-place.
    Joins on (hospital_id, date).
    """
    if df.empty:
        return

    hospital_ids = df["hospital_id"].unique().tolist()

    # Get hospital UUID mapping
    hospitals = (
        db.query(Hospital.hospital_id, Hospital.id)
        .filter(Hospital.hospital_id.in_(hospital_ids))
        .all()
    )
    hosp_str_to_uuid = {h.hospital_id: h.id for h in hospitals}

    # Load all external signals for these hospitals
    hosp_uuids = list(hosp_str_to_uuid.values())
    if not hosp_uuids:
        return

    signals = (
        db.query(
            ExternalSignal.hospital_id,
            ExternalSignal.date,
            ExternalSignal.temperature,
            ExternalSignal.aqi,
            ExternalSignal.outbreak_index,
            ExternalSignal.mobility_index,
        )
        .filter(ExternalSignal.hospital_id.in_(hosp_uuids))
        .all()
    )

    if not signals:
        return

    # Build lookup: (hospital_uuid, date) -> signal values
    uuid_to_str = {v: k for k, v in hosp_str_to_uuid.items()}
    signal_lookup: Dict[tuple, dict] = {}
    for sig in signals:
        hosp_str = uuid_to_str.get(sig.hospital_id)
        if hosp_str:
            signal_lookup[(hosp_str, sig.date)] = {
                "temperature": float(sig.temperature),
                "aqi": float(sig.aqi),
                "outbreak_index": float(sig.outbreak_index),
                "mobility_index": float(sig.mobility_index),
            }

    if not signal_lookup:
        return

    # Apply to DataFrame
    for idx, row in df.iterrows():
        key = (row["hospital_id"], row["date"].date() if hasattr(row["date"], "date") else row["date"])
        if key in signal_lookup:
            vals = signal_lookup[key]
            df.at[idx, "temperature"] = vals["temperature"]
            df.at[idx, "aqi"] = vals["aqi"]
            df.at[idx, "outbreak_index"] = vals["outbreak_index"]
            df.at[idx, "mobility_index"] = vals["mobility_index"]

    logger.info(f"Overlaid {len(signal_lookup)} external signal records onto DataFrame")

