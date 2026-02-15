"""
Residual Stacking Module

Implements proper stacked residual modeling to replace ineffective AR(7) layer.

Procedure:
1. Train base model using time-series CV
2. Generate out-of-fold predictions
3. Compute residuals (y - y_pred)
4. Train secondary LightGBM model on residual features
5. At inference: final_pred = base_pred + residual_model_pred
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple
import lightgbm as lgb
from forecast_system.utils import get_logger
from forecast_system.models import LightGBMForecaster

logger = get_logger(__name__)


class ResidualStacker:
    """
    Stacked residual model for capturing remaining temporal structure.
    
    Replaces ineffective AR(7) post-hoc correction with proper LightGBM residual model.
    """
    
    def __init__(self,
                 n_estimators: int = 200,
                 learning_rate: float = 0.05,
                 num_leaves: int = 15,
                 min_data_in_leaf: int = 20,
                 lambda_l1: float = 0.1,
                 lambda_l2: float = 0.1):
        """
        Initialize residual stacker.
        
        Args:
            n_estimators: Number of trees for residual model
            learning_rate: Learning rate
            num_leaves: Number of leaves (smaller for regularization)
            min_data_in_leaf: Minimum samples per leaf
            lambda_l1: L1 regularization
            lambda_l2: L2 regularization
        """
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.min_data_in_leaf = min_data_in_leaf
        self.lambda_l1 = lambda_l1
        self.lambda_l2 = lambda_l2
        self.residual_model = None
        self.is_fitted = False
    
    def create_residual_features(self,
                                 residuals: np.ndarray,
                                 hospital_ids: np.ndarray,
                                 horizons: np.ndarray,
                                 dates: pd.Series) -> pd.DataFrame:
        """
        Create residual features from past residuals.
        
        Features:
        - residual_lag_1
        - residual_lag_7
        - rolling_residual_mean_7
        - horizon
        
        CRITICAL: Features must be computed strictly from past data (no leakage).
        
        Args:
            residuals: Residual values (y_true - y_pred)
            hospital_ids: Hospital IDs
            horizons: Forecast horizons (1-7)
            dates: Date series (for temporal ordering)
            
        Returns:
            DataFrame with residual features
        """
        df = pd.DataFrame({
            'residual': residuals,
            'hospital_id': hospital_ids,
            'horizon': horizons,
            'date': dates.values if hasattr(dates, 'values') else dates
        })
        
        # Sort by hospital, date, horizon
        df = df.sort_values(['hospital_id', 'date', 'horizon']).reset_index(drop=True)
        
        # Create lag features per hospital
        df['residual_lag_1'] = df.groupby('hospital_id')['residual'].shift(1).fillna(0)
        df['residual_lag_7'] = df.groupby('hospital_id')['residual'].shift(7).fillna(0)
        
        # Rolling mean (7-day window)
        df['rolling_residual_mean_7'] = df.groupby('hospital_id')['residual'].transform(
            lambda x: x.rolling(window=7, min_periods=1).mean().shift(1).fillna(0)
        )
        
        # Keep only feature columns
        feature_df = pd.DataFrame({
            'residual_lag_1': df['residual_lag_1'],
            'residual_lag_7': df['residual_lag_7'],
            'rolling_residual_mean_7': df['rolling_residual_mean_7'],
            'horizon': df['horizon']
        })
        
        return feature_df
    
    def fit(self,
            residuals: np.ndarray,
            hospital_ids: np.ndarray,
            horizons: np.ndarray,
            dates: pd.Series,
            sample_weight: Optional[np.ndarray] = None) -> 'ResidualStacker':
        """
        Train residual model on residual features.
        
        Args:
            residuals: Residual values (y_true - y_pred)
            hospital_ids: Hospital IDs
            horizons: Forecast horizons (1-7)
            dates: Date series
            sample_weight: Optional sample weights
            
        Returns:
            Self
        """
        logger.info("=" * 60)
        logger.info("RESIDUAL STACKING: Training secondary LightGBM model")
        logger.info("=" * 60)
        
        # Create residual features
        X_residual = self.create_residual_features(residuals, hospital_ids, horizons, dates)
        y_residual = residuals
        
        # Remove rows with all-zero features (beginning of time series)
        valid_mask = (X_residual['residual_lag_1'] != 0) | (X_residual['residual_lag_7'] != 0)
        if valid_mask.sum() < 100:
            logger.warning("   Insufficient residual history, using all samples")
            valid_mask = np.ones(len(X_residual), dtype=bool)
        
        X_residual = X_residual[valid_mask]
        y_residual = y_residual[valid_mask]
        sample_weight = sample_weight[valid_mask] if sample_weight is not None else None
        
        if len(X_residual) < 50:
            logger.warning("   Insufficient data for residual model, skipping")
            return self
        
        # Train LightGBM model
        params = {
            'objective': 'regression',
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': self.num_leaves,
            'learning_rate': self.learning_rate,
            'min_data_in_leaf': self.min_data_in_leaf,
            'lambda_l1': self.lambda_l1,
            'lambda_l2': self.lambda_l2,
            'verbosity': -1,
            'seed': 42
        }
        
        train_data = lgb.Dataset(X_residual, label=y_residual, weight=sample_weight, free_raw_data=False)
        
        callbacks = [lgb.log_evaluation(period=0)]
        
        self.residual_model = lgb.train(
            params,
            train_data,
            num_boost_round=self.n_estimators,
            callbacks=callbacks
        )
        
        # Evaluate fit
        y_pred_residual = self.residual_model.predict(X_residual)
        mae_residual = np.mean(np.abs(y_residual - y_pred_residual))
        logger.info(f"   Residual model MAE: {mae_residual:.3f} (n={len(X_residual)})")
        
        self.is_fitted = True
        logger.info("   ✅ Residual stacking model trained")
        
        return self
    
    def predict(self,
                hospital_ids: np.ndarray,
                horizons: np.ndarray,
                dates: pd.Series,
                recent_residuals: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Predict residual correction.
        
        Args:
            hospital_ids: Hospital IDs
            horizons: Forecast horizons (1-7)
            dates: Date series
            recent_residuals: Recent residual history (for feature creation)
                            If None, returns zeros
            
        Returns:
            Residual corrections to add to base predictions
        """
        if not self.is_fitted or self.residual_model is None:
            return np.zeros(len(hospital_ids))
        
        if recent_residuals is None:
            # Cannot create features without residual history
            return np.zeros(len(hospital_ids))
        
        # Create residual features from recent history
        X_residual = self.create_residual_features(
            recent_residuals, hospital_ids, horizons, dates
        )
        
        # Predict residual correction
        corrections = self.residual_model.predict(X_residual)
        
        return corrections
    
    def stack_predictions(self,
                         base_pred: np.ndarray,
                         hospital_ids: np.ndarray,
                         horizons: np.ndarray,
                         dates: pd.Series,
                         recent_residuals: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Apply residual stacking: final_pred = base_pred + residual_correction.
        
        Args:
            base_pred: Base model predictions
            hospital_ids: Hospital IDs
            horizons: Forecast horizons (1-7)
            dates: Date series
            recent_residuals: Recent residual history
            
        Returns:
            Stacked predictions
        """
        corrections = self.predict(hospital_ids, horizons, dates, recent_residuals)
        stacked_pred = base_pred + corrections
        
        logger.debug(f"   Residual stacking: mean correction={np.mean(np.abs(corrections)):.3f}")
        
        return stacked_pred


def create_residual_stacker_from_cv(
    X: pd.DataFrame,
    y: pd.Series,
    dates: pd.Series,
    base_model_class,
    base_model_params: dict,
    cv,
    hospital_col: str = 'hospital_id_enc',
    horizon_col: str = 'horizon'
) -> ResidualStacker:
    """
    Create residual stacker using out-of-fold predictions from CV.
    
    This ensures no data leakage in residual features.
    
    Args:
        X: Features
        y: Targets
        dates: Dates
        base_model_class: Base model class
        base_model_params: Base model parameters
        cv: Cross-validation splitter
        hospital_col: Column name for hospital ID
        horizon_col: Column name for horizon
        
    Returns:
        Trained ResidualStacker
    """
    logger.info("=" * 60)
    logger.info("CREATING RESIDUAL STACKER FROM OUT-OF-FOLD PREDICTIONS")
    logger.info("=" * 60)
    
    all_residuals = []
    all_hospital_ids = []
    all_horizons = []
    all_dates = []
    
    # Get CV splits
    if hasattr(cv, 'split'):
        cv_splits = list(cv.split(X, y, dates=dates))
    else:
        cv_splits = list(cv.split(X, y, dates))
    
    for fold, (train_idx, val_idx) in enumerate(cv_splits):
        logger.info(f"   Fold {fold + 1}/{len(cv_splits)}: Generating OOF predictions...")
        
        X_train = X.iloc[train_idx]
        y_train = y.iloc[train_idx]
        X_val = X.iloc[val_idx]
        y_val = y.iloc[val_idx]
        
        # Train base model on fold
        base_model = base_model_class(**base_model_params)
        base_model.fit(X_train, y_train, X_val, y_val)
        
        # Get out-of-fold predictions
        y_pred_val = base_model.predict(X_val)
        residuals_val = y_val.values - y_pred_val
        
        # Store residuals with metadata
        all_residuals.extend(residuals_val)
        all_hospital_ids.extend(X_val[hospital_col].values if hospital_col in X_val.columns else [0] * len(X_val))
        all_horizons.extend(X_val[horizon_col].values if horizon_col in X_val.columns else [1] * len(X_val))
        all_dates.extend(dates.iloc[val_idx].values if dates is not None else [pd.Timestamp.now()] * len(X_val))
    
    # Create residual stacker
    stacker = ResidualStacker()
    stacker.fit(
        np.array(all_residuals),
        np.array(all_hospital_ids),
        np.array(all_horizons),
        pd.Series(all_dates)
    )
    
    return stacker

