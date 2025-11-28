# src/components/data_ingestion.py
from pathlib import Path
import pandas as pd
from src.pipeline.logger import get_logger

logger = get_logger(__name__)

REQUIRED_COLUMNS = [
    "date","city","city_id","hospital_id","hospital_id_enc","admissions",
    "lag_1_admissions","lag_7_admissions","rolling_14_admissions",
    "aqi","temp","humidity","rainfall","wind_speed",
    "mobility_index","outbreak_index",
    "festival_flag","holiday_flag",
    "weekday","is_weekend",
    "population_density","hospital_beds","staff_count"
]

def ingest_city(city: str, base_dir="generated_datasets_ml_ready/xgb"):
    """
    Loads XGB-ready CSV for a given city.
    Ensures column presence and sorts by hospital/date.
    """

    logger.info(f"📥 Ingesting city={city} from {base_dir}")
    
    path = Path(base_dir) / f"{city.lower()}_xgb.csv"
    if not path.exists():
        raise FileNotFoundError(f"CSV not found: {path}")

    df = pd.read_csv(path, parse_dates=["date"])

    # Validate required columns
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            raise ValueError(f"❌ Missing required column: {col}")

    # Sort chronologically per hospital (CRITICAL for time-series)
    df = df.sort_values(["hospital_id", "date"]).reset_index(drop=True)
    
    # Validate date column is properly parsed
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    # Ensure no duplicate date+hospital combinations
    duplicates = df.duplicated(subset=["hospital_id", "date"], keep=False)
    if duplicates.any():
        logger.warning(f"⚠️  Found {duplicates.sum()} duplicate hospital_id+date combinations, keeping first")
        df = df.drop_duplicates(subset=["hospital_id", "date"], keep='first').reset_index(drop=True)
    
    logger.info(f"✅ Loaded {df.shape[0]} rows for city={city}")
    logger.info(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    return df

def ingest_all_cities(base_dir="generated_datasets_ml_ready/xgb", cities=None):
    """
    Loads all city CSVs and combines into one DataFrame for global training.
    Ensures column presence, sorts by hospital/date, and validates data.
    
    Args:
        base_dir: Base directory containing city CSV files
        cities: List of city names. If None, auto-detects from directory.
    
    Returns:
        Combined DataFrame with all cities' data
    """
    base_path = Path(base_dir)
    
    # Auto-detect cities if not provided
    if cities is None:
        csv_files = list(base_path.glob("*_xgb.csv"))
        cities = [f.stem.replace("_xgb", "").capitalize() for f in csv_files]
        logger.info(f"🔍 Auto-detected cities: {cities}")
    
    all_dfs = []
    
    for city in cities:
        try:
            df_city = ingest_city(city, base_dir)
            all_dfs.append(df_city)
        except Exception as e:
            logger.warning(f"⚠️  Skipping {city}: {e}")
            continue
    
    if not all_dfs:
        raise ValueError("❌ No city data loaded. Check base_dir and city names.")
    
    # Combine all DataFrames
    df_combined = pd.concat(all_dfs, ignore_index=True)
    
    # Sort chronologically per hospital (CRITICAL for time-series)
    df_combined = df_combined.sort_values(["hospital_id", "date"]).reset_index(drop=True)
    
    # Validate date column
    if not pd.api.types.is_datetime64_any_dtype(df_combined['date']):
        df_combined['date'] = pd.to_datetime(df_combined['date'])
    
    # Remove duplicates
    duplicates = df_combined.duplicated(subset=["hospital_id", "date"], keep=False)
    if duplicates.any():
        logger.warning(f"⚠️  Found {duplicates.sum()} duplicate hospital_id+date combinations, keeping first")
        df_combined = df_combined.drop_duplicates(subset=["hospital_id", "date"], keep='first').reset_index(drop=True)
    
    logger.info(f"✅ Combined dataset: {df_combined.shape[0]} rows from {len(cities)} cities")
    logger.info(f"   Date range: {df_combined['date'].min()} to {df_combined['date'].max()}")
    logger.info(f"   Cities: {df_combined['city'].unique().tolist()}")
    logger.info(f"   Hospitals: {df_combined['hospital_id'].nunique()} unique hospitals")
    
    return df_combined
