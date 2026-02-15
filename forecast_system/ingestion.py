"""
Data Ingestion Module

Loads and validates hospital admissions data.
"""

import pandas as pd
from pathlib import Path
from typing import Optional
import os

from forecast_system.utils import get_logger

logger = get_logger(__name__)


def load_data(csv_path: str) -> pd.DataFrame:
    """
    Load hospital admissions dataset.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        DataFrame with validated and sorted data
    """
    # Resolve path - try multiple locations
    csv_path_obj = Path(csv_path)
    
    # Try paths in order:
    # 1. As-is (absolute or relative to current dir)
    # 2. Relative to current working directory
    # 3. Relative to agents_ai directory (where this module is)
    # 4. Relative to project root (parent of agents_ai)
    
    if not csv_path_obj.exists():
        current_dir = Path.cwd()
        agents_ai_dir = Path(__file__).parent.parent
        project_root = agents_ai_dir.parent
        
        # Try different base paths
        for base_path in [current_dir, agents_ai_dir, project_root]:
            alt_path = base_path / csv_path
            if alt_path.exists():
                csv_path_obj = alt_path
                break
        else:
            # If still not found, try with normalized path separators
            normalized_path = csv_path.replace('\\', os.sep).replace('/', os.sep)
            for base_path in [current_dir, agents_ai_dir, project_root]:
                alt_path = base_path / normalized_path
                if alt_path.exists():
                    csv_path_obj = alt_path
                    break
            else:
                raise FileNotFoundError(
                    f"CSV file not found: {csv_path}\n"
                    f"Tried locations:\n"
                    f"  - {csv_path_obj}\n"
                    f"  - {current_dir / csv_path}\n"
                    f"  - {agents_ai_dir / csv_path}\n"
                    f"  - {project_root / csv_path}"
                )
    
    csv_path = str(csv_path_obj.resolve())
    
    logger.info(f"📥 Loading dataset from {csv_path}")
    
    # Load with date parsing
    df = pd.read_csv(csv_path, parse_dates=["date"])
    
    # Ensure date is datetime
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])
    
    # Validate required columns
    required_cols = ['date', 'hospital_id', 'admissions']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Sort by hospital_id and date (CRITICAL for time-series)
    df = df.sort_values(['hospital_id', 'date']).reset_index(drop=True)
    
    # Remove duplicates
    duplicates = df.duplicated(subset=['hospital_id', 'date'], keep=False)
    if duplicates.any():
        logger.warning(f"⚠️  Found {duplicates.sum()} duplicates, keeping first")
        df = df.drop_duplicates(subset=['hospital_id', 'date'], keep='first').reset_index(drop=True)
    
    logger.info(f"✅ Loaded {df.shape[0]} rows")
    logger.info(f"   Date range: {df['date'].min()} to {df['date'].max()}")
    logger.info(f"   Hospitals: {df['hospital_id'].nunique()}")
    logger.info(f"   Columns: {df.shape[1]}")
    
    return df

