"""
Per-Horizon Forecaster

Wraps multiple models (one per horizon) for better horizon-specific learning.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import pickle
from pathlib import Path

from forecast_system.models.base_model import BaseForecaster


class PerHorizonForecaster(BaseForecaster):
    """
    Forecaster that uses separate models for each horizon.
    
    This improves horizon-specific learning compared to a single global model.
    """
    
    def __init__(self, models_by_horizon: Dict[int, BaseForecaster]):
        """
        Initialize per-horizon forecaster.
        
        Args:
            models_by_horizon: Dictionary mapping horizon (1-7) to trained model
        """
        self.models_by_horizon = models_by_horizon
        self.is_fitted = True
    
    def fit(self, X: pd.DataFrame, y: pd.Series, 
            X_val: Optional[pd.DataFrame] = None, 
            y_val: Optional[pd.Series] = None,
            sample_weight: Optional[np.ndarray] = None) -> 'PerHorizonForecaster':
        """
        Fit is not needed - models are already trained.
        This is a wrapper around pre-trained models.
        """
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make predictions using appropriate horizon model."""
        if 'horizon' not in X.columns:
            raise ValueError("'horizon' column required for per-horizon prediction")
        
        predictions = []
        
        for horizon in sorted(self.models_by_horizon.keys()):
            horizon_mask = X['horizon'] == horizon
            if horizon_mask.sum() == 0:
                continue
            
            X_h = X[horizon_mask].copy()
            if 'horizon' in X_h.columns:
                X_h = X_h.drop(columns=['horizon'])
            
            model_h = self.models_by_horizon[horizon]
            pred_h = model_h.predict(X_h)
            
            # Store predictions in correct order
            for idx, pred in zip(X_h.index, pred_h):
                predictions.append((idx, pred))
        
        # Sort by original index and return
        predictions.sort(key=lambda x: x[0])
        return np.array([p[1] for p in predictions])
    
    def predict_quantiles(self, X: pd.DataFrame, quantiles: list = [0.1, 0.5, 0.9]) -> Dict[float, np.ndarray]:
        """Make quantile predictions using appropriate horizon model."""
        if 'horizon' not in X.columns:
            raise ValueError("'horizon' column required for per-horizon prediction")
        
        results = {q: [] for q in quantiles}
        indices = []
        
        for horizon in sorted(self.models_by_horizon.keys()):
            horizon_mask = X['horizon'] == horizon
            if horizon_mask.sum() == 0:
                continue
            
            X_h = X[horizon_mask].copy()
            if 'horizon' in X_h.columns:
                X_h = X_h.drop(columns=['horizon'])
            
            model_h = self.models_by_horizon[horizon]
            pred_h = model_h.predict_quantiles(X_h, quantiles)
            
            for idx in X_h.index:
                indices.append(idx)
                for q in quantiles:
                    results[q].append(pred_h[q][X_h.index.get_loc(idx)])
        
        # Sort by original index
        sorted_indices = sorted(enumerate(indices), key=lambda x: x[1])
        for q in quantiles:
            results[q] = np.array([results[q][i] for i, _ in sorted_indices])
        
        return results
    
    def get_feature_importance(self, X: pd.DataFrame) -> pd.DataFrame:
        """Get feature importance (average across horizons)."""
        import pandas as pd
        
        importance_dfs = []
        
        for horizon, model in self.models_by_horizon.items():
            X_h = X[X['horizon'] == horizon].copy()
            if 'horizon' in X_h.columns:
                X_h = X_h.drop(columns=['horizon'])
            
            if len(X_h) > 0:
                imp_df = model.get_feature_importance(X_h)
                imp_df['horizon'] = horizon
                importance_dfs.append(imp_df)
        
        if not importance_dfs:
            return pd.DataFrame(columns=['feature', 'importance', 'importance_pct'])
        
        # Average importance across horizons
        combined = pd.concat(importance_dfs, ignore_index=True)
        avg_importance = combined.groupby('feature')['importance'].mean().reset_index()
        avg_importance['importance_pct'] = (avg_importance['importance'] / avg_importance['importance'].sum() * 100).round(2)
        avg_importance = avg_importance.sort_values('importance', ascending=False)
        
        return avg_importance
    
    def save(self, filepath: str) -> None:
        """Save per-horizon models."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        # Save each horizon model separately
        model_dir = filepath.parent / f"{filepath.stem}_horizons"
        model_dir.mkdir(exist_ok=True)
        
        saved_paths = {}
        for horizon, model in self.models_by_horizon.items():
            model_path = model_dir / f"horizon_{horizon}.pkl"
            model.save(str(model_path))
            saved_paths[horizon] = str(model_path)
        
        # Save metadata
        with open(filepath, 'wb') as f:
            pickle.dump({
                'models_by_horizon_paths': saved_paths,
                'horizons': list(self.models_by_horizon.keys())
            }, f)
    
    @classmethod
    def load(cls, filepath: str) -> 'PerHorizonForecaster':
        """Load per-horizon models."""
        from forecast_system.models.lightgbm_model import LightGBMForecaster
        from forecast_system.models.xgboost_model import XGBoostForecaster
        
        with open(filepath, 'rb') as f:
            metadata = pickle.load(f)
        
        models_by_horizon = {}
        for horizon, model_path in metadata['models_by_horizon_paths'].items():
            # Try to determine model type from path or use LightGBM as default
            if 'xgboost' in model_path.lower():
                model = XGBoostForecaster.load(model_path)
            else:
                model = LightGBMForecaster.load(model_path)
            models_by_horizon[horizon] = model
        
        return cls(models_by_horizon)

