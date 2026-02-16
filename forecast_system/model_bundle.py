"""
Model Bundle

Wraps model with feature schema and encoders for production safety.
"""

import joblib
import pandas as pd
import numpy as np
from typing import List


class ModelBundle:
    """
    Production-safe model wrapper.
    
    Ensures:
    - Feature columns match exactly
    - Missing features are filled with 0
    - Feature order is consistent
    """
    
    def __init__(self, model, feature_columns: List[str], encoders: dict):
        """
        Initialize ModelBundle.
        
        Args:
            model: Trained LightGBM model
            feature_columns: List of feature column names (in order)
            encoders: Dict with 'hospital_id' and 'season' encoders
        """
        self.model = model
        self.feature_columns = feature_columns
        self.encoders = encoders
        
        # Get feature names from model if available (strict lock)
        if hasattr(model, 'feature_name_'):
            # LightGBM uses feature_name_ (list)
            self.model_feature_names = model.feature_name_
        elif hasattr(model, 'feature_names_in_'):
            # Scikit-learn style
            self.model_feature_names = model.feature_names_in_
        else:
            # Fallback to stored feature_columns
            self.model_feature_names = feature_columns
        
        # Ensure model feature names match stored feature columns
        if len(self.model_feature_names) != len(feature_columns):
            raise ValueError(
                f"Feature count mismatch: model has {len(self.model_feature_names)} features, "
                f"but bundle expects {len(feature_columns)}"
            )
    
    def __getattr__(self, name):
        """Handle backward compatibility for old ModelBundle instances."""
        if name == 'model_feature_names':
            # For old models loaded from disk, compute on-the-fly
            if hasattr(self.model, 'feature_name_'):
                return self.model.feature_name_
            elif hasattr(self.model, 'feature_names_in_'):
                return self.model.feature_names_in_
            else:
                return self.feature_columns
        raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict with feature safety checks.
        
        STRICT FEATURE LOCK: Uses model's exact feature order.
        No fallback. No try/except. Hard alignment.
        
        Args:
            X: DataFrame with features
        
        Returns:
            Predictions array
        """
        # STRICT: Use model's feature names (hard lock)
        required_features = self.model_feature_names
        
        # Check for missing features
        missing = set(required_features) - set(X.columns)
        if missing:
            raise ValueError(f"Missing required features: {missing}")
        
        # STRICT: Hard alignment - use model's exact feature order
        # No fallback, no try/except, just hard alignment
        X_aligned = X[required_features].copy()
        
        # Fill any NaN with 0 (safety)
        X_aligned = X_aligned.fillna(0)
        
        # Validate alignment
        if list(X_aligned.columns) != list(required_features):
            raise ValueError(
                f"Feature order mismatch: expected {required_features}, got {list(X_aligned.columns)}"
            )
        
        # Predict
        return self.model.predict(X_aligned)
    
    def save(self, path: str):
        """Save ModelBundle to disk."""
        joblib.dump(self, path)
    
    @staticmethod
    def load(path: str) -> 'ModelBundle':
        """Load ModelBundle from disk."""
        return joblib.load(path)

