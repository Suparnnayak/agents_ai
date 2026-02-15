"""
Temporal Fusion Transformer (TFT) Forecaster

Deep learning model for time-series forecasting with quantile support.
Note: Requires PyTorch and pytorch-forecasting.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from pathlib import Path

from forecast_system.models.base_model import BaseForecaster


class TFTForecaster(BaseForecaster):
    """
    Temporal Fusion Transformer for time-series forecasting.
    
    Note: This is a placeholder. Full TFT implementation requires:
    - pytorch-forecasting library
    - Proper time-series data structure
    - GPU support recommended
    """
    
    def __init__(self, **kwargs):
        super().__init__(name='TFT', **kwargs)
        raise NotImplementedError(
            "TFT implementation requires pytorch-forecasting library.\n"
            "Install with: pip install pytorch-forecasting\n"
            "This is a complex deep learning model best suited for:\n"
            "- Very large datasets (>100k samples)\n"
            "- Complex temporal patterns\n"
            "- When tree-based models plateau\n\n"
            "For now, use LightGBM or XGBoost which are more practical."
        )
    
    def fit(self, X_train, y_train, X_val=None, y_val=None, sample_weight=None):
        raise NotImplementedError("TFT not implemented. Use LightGBM or XGBoost.")
    
    def predict(self, X):
        raise NotImplementedError("TFT not implemented.")
    
    def predict_quantiles(self, X, quantiles=[0.1, 0.5, 0.9]):
        raise NotImplementedError("TFT not implemented.")
    
    def get_feature_importance(self, X):
        raise NotImplementedError("TFT not implemented.")
    
    def save(self, filepath):
        raise NotImplementedError("TFT not implemented.")
    
    @classmethod
    def load(cls, filepath):
        raise NotImplementedError("TFT not implemented.")

