"""
Target Engineering Module

Supports multiple target formulations for forecasting:
- raw_admissions: Direct admission counts
- log_admissions: Log-transformed admissions
- utilization_ratio: admissions / hospital_capacity
- delta_admissions: Change from previous period
- multi_output_7day: Multi-output format (optional)
"""

import pandas as pd
import numpy as np
from typing import Tuple, Optional, Dict
from .utils import get_logger

logger = get_logger(__name__)


class TargetEngineer:
    """Engineer targets for different forecasting strategies."""
    
    def __init__(self, target_mode: str = 'raw_admissions'):
        """
        Initialize target engineer.
        
        Args:
            target_mode: One of:
                - 'raw_admissions': Direct admission counts
                - 'log_admissions': Log(1 + admissions)
                - 'utilization_ratio': admissions / hospital_capacity
                - 'delta_admissions': Change from lag_1
        """
        self.target_mode = target_mode
        self.scaler_params = {}  # Store scaling params for inverse transform
        
        valid_modes = ['raw_admissions', 'log_admissions', 'utilization_ratio', 'delta_admissions']
        if target_mode not in valid_modes:
            raise ValueError(f"target_mode must be one of {valid_modes}, got {target_mode}")
        
        logger.info(f"🎯 Target mode: {target_mode}")
    
    def transform(self, 
                  df: pd.DataFrame, 
                  target_col: str = 'admissions',
                  capacity_col: str = 'hospital_capacity',
                  lag_col: str = 'lag_1') -> Tuple[pd.DataFrame, pd.Series]:
        """
        Transform target according to selected mode.
        
        Args:
            df: DataFrame with target and features
            target_col: Name of target column
            capacity_col: Name of capacity column (for utilization_ratio)
            lag_col: Name of lag column (for delta_admissions)
            
        Returns:
            (df_with_features, transformed_target)
        """
        df = df.copy()
        
        if target_col not in df.columns:
            raise ValueError(f"Target column '{target_col}' not found in DataFrame")
        
        original_target = df[target_col].copy()
        
        if self.target_mode == 'raw_admissions':
            transformed_target = original_target.copy()
            self.scaler_params = {'mode': 'raw'}
            
        elif self.target_mode == 'log_admissions':
            # Log transform: log(1 + x) to handle zeros
            transformed_target = np.log1p(original_target)
            self.scaler_params = {'mode': 'log'}
            logger.info("   Applied log(1 + x) transformation")
            
        elif self.target_mode == 'utilization_ratio':
            if capacity_col not in df.columns:
                raise ValueError(f"Capacity column '{capacity_col}' not found for utilization_ratio mode")
            
            # Avoid division by zero
            capacity = df[capacity_col].copy()
            capacity = capacity.replace(0, 1)  # Replace zeros with 1 to avoid division error
            
            transformed_target = original_target / capacity
            self.scaler_params = {
                'mode': 'utilization_ratio',
                'capacity_col': capacity_col
            }
            logger.info("   Applied utilization ratio transformation (admissions / capacity)")
            
        elif self.target_mode == 'delta_admissions':
            if lag_col not in df.columns:
                # Create lag_1 if not present
                df['lag_1'] = df.groupby('hospital_id')[target_col].shift(1)
                lag_col = 'lag_1'
            
            lag_values = df[lag_col].copy()
            lag_values = lag_values.fillna(0)  # Fill NaN with 0
            
            transformed_target = original_target - lag_values
            self.scaler_params = {
                'mode': 'delta',
                'lag_col': lag_col
            }
            logger.info("   Applied delta transformation (admissions - lag_1)")
        
        # Store transformed target in DataFrame
        df['target_transformed'] = transformed_target
        
        return df, transformed_target
    
    def inverse_transform(self, 
                         predictions: np.ndarray,
                         df: pd.DataFrame,
                         capacity_col: str = 'hospital_capacity',
                         lag_col: str = 'lag_1') -> np.ndarray:
        """
        Inverse transform predictions back to original scale.
        
        Args:
            predictions: Transformed predictions
            df: DataFrame with required columns for inverse transform
            capacity_col: Name of capacity column
            lag_col: Name of lag column
            
        Returns:
            Predictions in original admission scale
        """
        if self.target_mode == 'raw_admissions':
            return predictions
            
        elif self.target_mode == 'log_admissions':
            # Inverse log: exp(x) - 1
            return np.expm1(predictions)
            
        elif self.target_mode == 'utilization_ratio':
            if capacity_col not in df.columns:
                raise ValueError(f"Capacity column '{capacity_col}' not found for inverse transform")
            
            capacity = df[capacity_col].values
            capacity = np.where(capacity == 0, 1, capacity)  # Avoid division by zero
            
            return predictions * capacity
            
        elif self.target_mode == 'delta_admissions':
            if lag_col not in df.columns:
                raise ValueError(f"Lag column '{lag_col}' not found for inverse transform")
            
            lag_values = df[lag_col].values
            lag_values = np.nan_to_num(lag_values, nan=0.0)
            
            return predictions + lag_values
        
        return predictions
    
    def get_target_info(self) -> Dict:
        """Get information about current target mode."""
        return {
            'mode': self.target_mode,
            'scaler_params': self.scaler_params
        }


def create_multi_output_targets(df: pd.DataFrame,
                               max_horizon: int = 7,
                               target_col: str = 'admissions') -> pd.DataFrame:
    """
    Create multi-output target format (alternative to horizon stacking).
    
    This creates a DataFrame where each row has targets for all horizons.
    Used for multi-output models (not currently implemented, but prepared for future).
    
    Args:
        df: DataFrame sorted by hospital_id and date
        max_horizon: Maximum forecast horizon
        target_col: Name of target column
        
    Returns:
        DataFrame with columns: target_h1, target_h2, ..., target_h7
    """
    logger.info(f"🔧 Creating multi-output targets (horizons 1-{max_horizon})...")
    
    df = df.copy()
    df = df.sort_values(['hospital_id', 'date']).reset_index(drop=True)
    
    # Create target columns for each horizon
    for h in range(1, max_horizon + 1):
        df[f'target_h{h}'] = df.groupby('hospital_id')[target_col].shift(-h)
    
    # Remove rows where any target is missing
    target_cols = [f'target_h{h}' for h in range(1, max_horizon + 1)]
    df = df.dropna(subset=target_cols)
    
    logger.info(f"   Created {len(df)} rows with multi-output targets")
    
    return df

