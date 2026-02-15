"""
Expanding Window Cross-Validation

Time-series CV where training window expands with each fold.
"""

import pandas as pd
import numpy as np
from typing import Iterator, Tuple, Optional
from sklearn.model_selection import BaseCrossValidator
from forecast_system.utils import get_logger

logger = get_logger(__name__)


class ExpandingWindowCV(BaseCrossValidator):
    """
    Expanding window time-series cross-validation.
    
    Training window starts small and expands with each fold.
    Test window size is fixed.
    
    Example with min_train_size=365, test_size=90:
        Fold 1: Train [0:365], Test [365:455]
        Fold 2: Train [0:455], Test [455:545]
        Fold 3: Train [0:545], Test [545:635]
    """
    
    def __init__(self,
                 n_splits: int = 5,
                 min_train_size: int = 365,
                 test_size: int = 90,
                 step: Optional[int] = None,
                 gap: int = 0):
        """
        Initialize expanding window CV.
        
        Args:
            n_splits: Number of CV folds
            min_train_size: Minimum training window size (expands with each fold)
            test_size: Size of test window (in samples)
            step: Step size between folds (defaults to test_size)
            gap: Gap between train and test (in samples)
        """
        self.n_splits = n_splits
        self.min_train_size = min_train_size
        self.test_size = test_size
        self.step = step if step is not None else test_size
        self.gap = gap
        
        logger.info(f"📊 ExpandingWindowCV: {n_splits} folds, min_train_size={min_train_size}, "
                   f"test_size={test_size}, step={self.step}")
    
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
        if self.min_train_size + self.test_size + self.gap > n_samples:
            raise ValueError(
                f"min_train_size ({self.min_train_size}) + test_size ({self.test_size}) + gap ({self.gap}) "
                f"exceeds total samples ({n_samples})"
            )
        
        # Starting position for first fold
        train_start = 0
        
        for fold in range(self.n_splits):
            # Training window expands with each fold
            train_end = self.min_train_size + (fold * self.step)
            
            # Ensure we don't exceed data bounds
            if train_end > n_samples - self.test_size - self.gap:
                logger.warning(f"⚠️  Fold {fold + 1}: Insufficient data, stopping")
                break
            
            # Test window
            test_start = train_end + self.gap
            test_end = test_start + self.test_size
            test_end = min(test_end, n_samples)
            
            train_idx = np.arange(train_start, train_end)
            test_idx = np.arange(test_start, test_end)
            
            if len(test_idx) == 0:
                logger.warning(f"⚠️  Fold {fold + 1}: Empty test set, skipping")
                continue
            
            logger.info(f"   Fold {fold + 1}: Train [0:{train_end}] ({len(train_idx)} samples), "
                       f"Test [{test_start}:{test_end}] ({len(test_idx)} samples)")
            
            yield train_idx, test_idx
    
    def get_n_splits(self, X=None, y=None, groups=None):
        """Return number of splits."""
        return self.n_splits

