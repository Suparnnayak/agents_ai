"""
XGBoost Forecaster

Point and quantile regression using XGBoost.
"""

import xgboost as xgb
import pandas as pd
import numpy as np
from typing import Dict, Optional
from pathlib import Path
import pickle

from .base_model import BaseForecaster


class XGBoostForecaster(BaseForecaster):
    """XGBoost-based forecaster with quantile support."""
    
    def __init__(self,
                 objective: str = 'reg:squarederror',
                 n_estimators: int = 1000,
                 learning_rate: float = 0.05,
                 max_depth: int = 8,
                 min_child_weight: int = 3,
                 subsample: float = 0.9,
                 colsample_bytree: float = 0.9,
                 reg_alpha: float = 0.2,
                 reg_lambda: float = 1.0,
                 early_stopping_rounds: int = 100,
                 verbose: int = 100,
                 **kwargs):
        super().__init__(name='XGBoost', **kwargs)
        self.objective = objective
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.max_depth = max_depth
        self.min_child_weight = min_child_weight
        self.subsample = subsample
        self.colsample_bytree = colsample_bytree
        self.reg_alpha = reg_alpha
        self.reg_lambda = reg_lambda
        self.early_stopping_rounds = early_stopping_rounds
        self.verbose = verbose
        self.quantile_models = {}
        
    def fit(self, X_train: pd.DataFrame, y_train: pd.Series,
            X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None,
            sample_weight: Optional[np.ndarray] = None) -> 'XGBoostForecaster':
        """Train XGBoost model."""
        params = {
            'objective': self.objective,
            'eval_metric': 'mae',
            'eta': self.learning_rate,
            'max_depth': self.max_depth,
            'min_child_weight': self.min_child_weight,
            'subsample': self.subsample,
            'colsample_bytree': self.colsample_bytree,
            'alpha': self.reg_alpha,
            'lambda': self.reg_lambda,
            'tree_method': 'hist',
            'verbosity': 0
        }
        
        dtrain = xgb.DMatrix(X_train, label=y_train, weight=sample_weight)
        
        evals = [(dtrain, 'train')]
        if X_val is not None and y_val is not None:
            dval = xgb.DMatrix(X_val, label=y_val)
            evals.append((dval, 'val'))
        
        self.model = xgb.train(
            params,
            dtrain,
            num_boost_round=self.n_estimators,
            evals=evals,
            early_stopping_rounds=self.early_stopping_rounds if X_val is not None else None,
            verbose_eval=self.verbose
        )
        
        self.is_fitted = True
        return self
    
    def fit_quantiles(self, X_train: pd.DataFrame, y_train: pd.Series,
                     X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None,
                     quantiles: list = [0.1, 0.5, 0.9],
                     sample_weight: Optional[np.ndarray] = None) -> 'XGBoostForecaster':
        """Train quantile regression models."""
        for quantile in quantiles:
            params = {
                'objective': 'reg:absoluteerror',
                'quantile_alpha': quantile,
                'eval_metric': 'mae',
                'eta': self.learning_rate,
                'max_depth': self.max_depth,
                'min_child_weight': self.min_child_weight,
                'subsample': self.subsample,
                'colsample_bytree': self.colsample_bytree,
                'alpha': self.reg_alpha,
                'lambda': self.reg_lambda,
                'tree_method': 'hist',
                'verbosity': 0
            }
            
            dtrain = xgb.DMatrix(X_train, label=y_train, weight=sample_weight)
            
            evals = [(dtrain, 'train')]
            if X_val is not None and y_val is not None:
                dval = xgb.DMatrix(X_val, label=y_val)
                evals.append((dval, 'val'))
            
            model = xgb.train(
                params,
                dtrain,
                num_boost_round=self.n_estimators,
                evals=evals,
                early_stopping_rounds=self.early_stopping_rounds if X_val is not None else None,
                verbose_eval=0
            )
            
            self.quantile_models[quantile] = model
        
        self.is_fitted = True
        return self
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make point predictions."""
        if not self.is_fitted or self.model is None:
            raise ValueError("Model not fitted.")
        dtest = xgb.DMatrix(X)
        return self.model.predict(dtest)
    
    def predict_quantiles(self, X: pd.DataFrame, quantiles: list = [0.1, 0.5, 0.9]) -> Dict[float, np.ndarray]:
        """Make quantile predictions."""
        if not self.is_fitted:
            raise ValueError("Model not fitted.")
        
        results = {}
        
        if self.quantile_models:
            dtest = xgb.DMatrix(X)
            for q in quantiles:
                if q in self.quantile_models:
                    results[q] = self.quantile_models[q].predict(dtest)
                else:
                    results[q] = self.predict(X)
        else:
            point_pred = self.predict(X)
            for q in quantiles:
                results[q] = point_pred
        
        return results
    
    def get_feature_importance(self, X: pd.DataFrame) -> pd.DataFrame:
        """Get feature importance."""
        if not self.is_fitted or self.model is None:
            raise ValueError("Model not fitted.")
        
        importance = self.model.get_score(importance_type='gain')
        feature_names = X.columns.tolist()
        
        # Convert to DataFrame
        importance_dict = {name: importance.get(f'f{i}', 0) for i, name in enumerate(feature_names)}
        
        df = pd.DataFrame({
            'feature': feature_names,
            'importance': [importance_dict.get(name, 0) for name in feature_names]
        }).sort_values('importance', ascending=False)
        
        total = df['importance'].sum()
        if total > 0:
            df['importance_pct'] = (df['importance'] / total * 100).round(2)
        else:
            df['importance_pct'] = 0.0
        
        return df
    
    def save(self, filepath: str) -> None:
        """Save model to disk."""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            pickle.dump({
                'model': self.model,
                'quantile_models': self.quantile_models,
                'params': {
                    'objective': self.objective,
                    'n_estimators': self.n_estimators,
                    'learning_rate': self.learning_rate,
                    'max_depth': self.max_depth,
                }
            }, f)
    
    @classmethod
    def load(cls, filepath: str) -> 'XGBoostForecaster':
        """Load model from disk."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        model = cls(**data['params'])
        model.model = data['model']
        model.quantile_models = data.get('quantile_models', {})
        model.is_fitted = True
        
        return model

