"""
Base Model Interface

All forecasting models inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple
import pandas as pd
import numpy as np


class BaseForecaster(ABC):
    """Base class for all forecasting models."""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.model = None
        self.is_fitted = False
        
    @abstractmethod
    def fit(self, X_train: pd.DataFrame, y_train: pd.Series,
            X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None,
            sample_weight: Optional[np.ndarray] = None) -> 'BaseForecaster':
        """Train the model."""
        pass
    
    @abstractmethod
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make point predictions."""
        pass
    
    @abstractmethod
    def predict_quantiles(self, X: pd.DataFrame, quantiles: list = [0.1, 0.5, 0.9]) -> Dict[float, np.ndarray]:
        """Make quantile predictions."""
        pass
    
    @abstractmethod
    def get_feature_importance(self, X: pd.DataFrame) -> pd.DataFrame:
        """Get feature importance."""
        pass
    
    @abstractmethod
    def save(self, filepath: str) -> None:
        """Save model to disk."""
        pass
    
    @classmethod
    @abstractmethod
    def load(cls, filepath: str) -> 'BaseForecaster':
        """Load model from disk."""
        pass

