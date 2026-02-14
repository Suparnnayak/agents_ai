"""
Rolling Window Cross-Validation

Time-series CV with fixed training window size that "rolls" forward.
"""

import pandas as pd
import numpy as np
from typing import Iterator, Tuple, Optional
from sklearn.model_selection import BaseCrossValidator
from ..utils import get_logger

logger = get_logger(__name__)


class RollingWindowCV(BaseCrossValidator):
    """
    Rolling window time-series cross-validation.
    
    Training window size is fixed. Each fold moves forward by a fixed step.
    
    Example with train_size=365, test_size=90, step=90:
        Fold 1: Train [0:365], Test [365:455]
        Fold 2: Train [90:455], Test [455:545]
        Fold 3: Train [180:545], Test [545:635]
    """
    
    def __init__(self,
                 n_splits: int = 5,
                 train_size: int = 365,
                 test_size: int = 90,
                 step: Optional[int] = None,
                 gap: int = 0):
        """
        Initialize rolling window CV.
        
        Args:
            n_splits: Number of CV folds
            train_size: Size of training window (in samples)
            test_size: Size of test window (in samples)
            step: Step size between folds (defaults to test_size)
            gap: Gap between train and test (in samples)
        """
        self.n_splits = n_splits
        self.train_size = train_size
        self.test_size = test_size
        self.step = step if step is not None else test_size
        self.gap = gap
        
        logger.info(f"📊 RollingWindowCV: {n_splits} folds, train_size={train_size}, test_size={test_size}, step={self.step}")
    
    def split(self, X, y=None, groups=None, dates=None):
        """
        Generate indices for train/test splits.
        
        Args:
            X: Feature matrix
            y: Target vector
            groups: Group labels (not used, for sklearn compatibility)
            dates: Date series for time-based splitting (optional)
            
        Yields:
            (train_indices, test_indices) tuples
        """
        n_samples = len(X)
        
        # Validate parameters
        if self.train_size + self.test_size + self.gap > n_samples:
            raise ValueError(
                f"train_size ({self.train_size}) + test_size ({self.test_size}) + gap ({self.gap}) "
                f"exceeds total samples ({n_samples})"
            )
        
        # Calculate maximum start position
        max_start = n_samples - self.train_size - self.test_size - self.gap
        
        # Generate fold start positions
        if self.n_splits == 1:
            # Single fold: use maximum available data
            fold_starts = [max(0, max_start)]
        else:
            # Multiple folds: distribute evenly
            step_size = max(1, max_start // (self.n_splits - 1)) if max_start > 0 else 1
            fold_starts = [min(i * step_size, max_start) for i in range(self.n_splits)]
        
        for fold, start in enumerate(fold_starts):
            train_start = start
            train_end = train_start + self.train_size
            test_start = train_end + self.gap
            test_end = test_start + self.test_size
            
            # Ensure we don't exceed data bounds
            test_end = min(test_end, n_samples)
            
            train_idx = np.arange(train_start, train_end)
            test_idx = np.arange(test_start, test_end)
            
            if len(test_idx) == 0:
                logger.warning(f"⚠️  Fold {fold + 1}: Empty test set, skipping")
                continue
            
            logger.info(f"   Fold {fold + 1}: Train [{train_start}:{train_end}] ({len(train_idx)} samples), "
                       f"Test [{test_start}:{test_end}] ({len(test_idx)} samples)")
            
            yield train_idx, test_idx
    
    def get_n_splits(self, X=None, y=None, groups=None):
        """Return number of splits."""
        return self.n_splits


def create_time_based_splits(dates: pd.Series,
                            train_years: float = 4.0,
                            test_years: float = 1.0,
                            n_splits: int = 5) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
    """
    Create time-based splits using date information.
    
    This is a helper function that uses actual dates to create splits,
    ensuring no data leakage across time boundaries.
    
    Args:
        dates: Series of dates (must be sorted)
        train_years: Training period in years
        test_years: Test period in years
        n_splits: Number of CV folds
        
    Yields:
        (train_indices, test_indices) tuples
    """
    dates = pd.to_datetime(dates)
    dates_sorted = dates.sort_values()
    
    min_date = dates_sorted.min()
    max_date = dates_sorted.max()
    total_days = (max_date - min_date).days
    
    train_days = int(train_years * 365.25)
    test_days = int(test_years * 365.25)
    
    logger.info(f"📅 Time-based splits: train={train_years} years ({train_days} days), "
               f"test={test_years} years ({test_days} days)")
    
    for fold in range(n_splits):
        # Calculate fold start date
        fold_start_date = min_date + pd.Timedelta(days=fold * test_days)
        
        # Training period
        train_start_date = fold_start_date
        train_end_date = train_start_date + pd.Timedelta(days=train_days)
        
        # Test period
        test_start_date = train_end_date
        test_end_date = test_start_date + pd.Timedelta(days=test_days)
        
        # Ensure we don't exceed max_date
        if test_end_date > max_date:
            logger.warning(f"⚠️  Fold {fold + 1}: Test period exceeds available data, skipping")
            continue
        
        # Get indices
        train_mask = (dates_sorted >= train_start_date) & (dates_sorted < train_end_date)
        test_mask = (dates_sorted >= test_start_date) & (dates_sorted < test_end_date)
        
        train_idx = np.where(train_mask)[0]
        test_idx = np.where(test_mask)[0]
        
        if len(test_idx) == 0:
            logger.warning(f"⚠️  Fold {fold + 1}: Empty test set, skipping")
            continue
        
        logger.info(f"   Fold {fold + 1}: Train [{train_start_date.date()} to {train_end_date.date()}], "
                   f"Test [{test_start_date.date()} to {test_end_date.date()}]")
        
        yield train_idx, test_idx

