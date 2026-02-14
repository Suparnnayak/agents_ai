"""
LightGBM Forecaster

Point and quantile regression using LightGBM.
"""

import lightgbm as lgb
import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from pathlib import Path
import pickle

from .base_model import BaseForecaster


class LightGBMForecaster(BaseForecaster):
    """LightGBM-based forecaster with quantile support."""
    
    def __init__(self, 
                 objective: str = 'regression',
                 n_estimators: int = 1000,
                 learning_rate: float = 0.05,
                 num_leaves: int = 31,
                 min_data_in_leaf: int = 20,
                 feature_fraction: float = 0.9,
                 bagging_fraction: float = 0.8,
                 bagging_freq: int = 5,
                 lambda_l1: float = 0.1,
                 lambda_l2: float = 0.1,
                 early_stopping_rounds: int = 100,
                 verbose: int = 100,
                 **kwargs):
        super().__init__(name='LightGBM', **kwargs)
        self.objective = objective
        self.n_estimators = n_estimators
        self.learning_rate = learning_rate
        self.num_leaves = num_leaves
        self.min_data_in_leaf = min_data_in_leaf
        self.feature_fraction = feature_fraction
        self.bagging_fraction = bagging_fraction
        self.bagging_freq = bagging_freq
        self.lambda_l1 = lambda_l1
        self.lambda_l2 = lambda_l2
        self.early_stopping_rounds = early_stopping_rounds
        self.verbose = verbose
        self.quantile_models = {}  # For quantile regression
        
    def fit(self, X_train: pd.DataFrame, y_train: pd.Series,
            X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None,
            sample_weight: Optional[np.ndarray] = None) -> 'LightGBMForecaster':
        """Train LightGBM model."""
        params = {
            'objective': self.objective,
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': self.num_leaves,
            'learning_rate': self.learning_rate,
            'feature_fraction': self.feature_fraction,
            'bagging_fraction': self.bagging_fraction,
            'bagging_freq': self.bagging_freq,
            'min_data_in_leaf': self.min_data_in_leaf,
            'lambda_l1': self.lambda_l1,
            'lambda_l2': self.lambda_l2,
            'verbosity': -1,
            'seed': 42
        }
        
        train_data = lgb.Dataset(X_train, label=y_train, weight=sample_weight)
        
        valid_sets = [train_data]
        valid_names = ['train']
        
        if X_val is not None and y_val is not None:
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
            valid_sets.append(val_data)
            valid_names.append('val')
        
        callbacks = []
        if X_val is not None and y_val is not None:
            callbacks.append(lgb.early_stopping(self.early_stopping_rounds, verbose=True))
        callbacks.append(lgb.log_evaluation(period=self.verbose))
        
        self.model = lgb.train(
            params,
            train_data,
            num_boost_round=self.n_estimators,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks
        )
        
        self.is_fitted = True
        return self
    
    def fit_quantiles(self, X_train: pd.DataFrame, y_train: pd.Series,
                     X_val: Optional[pd.DataFrame] = None, y_val: Optional[pd.Series] = None,
                     quantiles: list = [0.1, 0.5, 0.9],
                     sample_weight: Optional[np.ndarray] = None,
                     calibrate_coverage: bool = True) -> 'LightGBMForecaster':
        """
        Train quantile regression models.
        
        CRITICAL: Each quantile gets a completely separate model instance.
        No shared booster state to ensure predictions differ.
        
        Args:
            calibrate_coverage: If True, adjusts quantile alpha to achieve target coverage
        """
        from ..utils import get_logger
        logger = get_logger(__name__)
        
        # Use original quantiles (calibration happens post-training)
        for quantile in quantiles:
            # CRITICAL: Each quantile gets separate params dict and model instance
            # Stronger regularization for quantile stability
            # Identical hyperparameters across quantiles + stronger regularization
            params = {
                'objective': 'quantile',
                'alpha': quantile,  # Use exact quantile level
                'metric': 'mae',
                'boosting_type': 'gbdt',
                'num_leaves': self.num_leaves,
                'learning_rate': min(self.learning_rate, 0.01),  # Cap at 0.01 for stability
                'feature_fraction': self.feature_fraction,
                'bagging_fraction': self.bagging_fraction,
                'bagging_freq': self.bagging_freq,
                'min_data_in_leaf': max(self.min_data_in_leaf, 50),  # Minimum 50 for stability
                'lambda_l1': self.lambda_l1 * 1.5,  # Stronger L1
                'lambda_l2': self.lambda_l2 * 1.5,  # Stronger L2
                'verbosity': -1,
                'seed': 42  # Same seed for all quantiles (identical hyperparameters)
            }
            
            # CRITICAL: Create fresh Dataset for each quantile (no shared state)
            train_data = lgb.Dataset(X_train, label=y_train, weight=sample_weight, free_raw_data=False)
            
            valid_sets = [train_data]
            valid_names = ['train']
            
            if X_val is not None and y_val is not None:
                val_data = lgb.Dataset(X_val, label=y_val, reference=train_data, free_raw_data=False)
                valid_sets.append(val_data)
                valid_names.append('val')
            
            callbacks = []
            if X_val is not None and y_val is not None:
                callbacks.append(lgb.early_stopping(self.early_stopping_rounds, verbose=False))
            callbacks.append(lgb.log_evaluation(period=0))
            
            # CRITICAL: Train completely separate model instance
            model = lgb.train(
                params,
                train_data,
                num_boost_round=self.n_estimators,
                valid_sets=valid_sets,
                valid_names=valid_names,
                callbacks=callbacks
            )
            
            self.quantile_models[quantile] = model
            logger.info(f"   Trained quantile model for q{int(quantile*100)} (alpha={quantile})")
        
        # Post-training validation: ensure quantiles differ
        if X_val is not None and len(self.quantile_models) >= 2:
            sample_preds = {}
            for q in sorted(quantiles):
                sample_preds[q] = self.quantile_models[q].predict(X_val.iloc[:100])
            
            # Check monotonicity
            quantiles_sorted = sorted(quantiles)
            for i in range(len(quantiles_sorted) - 1):
                q_low = quantiles_sorted[i]
                q_high = quantiles_sorted[i + 1]
                pred_low = sample_preds[q_low]
                pred_high = sample_preds[q_high]
                
                # Check if predictions differ
                if np.allclose(pred_low, pred_high, rtol=1e-5):
                    logger.warning(f"   ⚠️  WARNING: q{int(q_low*100)} and q{int(q_high*100)} predictions are identical!")
                    logger.warning("   This indicates quantile model implementation issue")
                else:
                    logger.info(f"   ✅ q{int(q_low*100)} and q{int(q_high*100)} predictions differ (mean diff: {np.mean(pred_high - pred_low):.2f})")
                
                # Check monotonicity
                violations = np.sum(pred_low > pred_high)
                if violations > 0:
                    logger.warning(f"   ⚠️  Monotonicity violation: {violations}/{len(pred_low)} samples have q{int(q_low*100)} > q{int(q_high*100)}")
                else:
                    logger.info(f"   ✅ Monotonicity: q{int(q_low*100)} <= q{int(q_high*100)} for all samples")
        
        self.is_fitted = True
        return self
    
    def fit_quantiles_structural(self,
                                 X_train: pd.DataFrame,
                                 y_train: pd.Series,
                                 X_val: Optional[pd.DataFrame] = None,
                                 y_val: Optional[pd.Series] = None,
                                 quantiles: list = [0.1, 0.5, 0.9],
                                 sample_weight: Optional[np.ndarray] = None) -> 'LightGBMForecaster':
        """
        Train quantiles with structural monotonicity (Option B: q50 + constrained q10/q90).
        
        This enforces natural ordering structurally:
        - Train q50 model (median)
        - Train q10 and q90 using monotonic constraints relative to q50
        - Final: q10 = q50 - delta_down, q90 = q50 + delta_up
        
        This is preferred over independent quantile models for stability.
        """
        from ..utils import get_logger
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("QUANTILE STRUCTURAL TRAINING: q50 + constrained q10/q90")
        logger.info("=" * 60)
        
        if 0.5 not in quantiles:
            raise ValueError("Structural quantile training requires 0.5 (median) in quantiles")
        
        # Step 1: Train q50 model (median)
        logger.info("   Step 1: Training q50 (median) model...")
        q50_params = {
            'objective': 'quantile',
            'alpha': 0.5,
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': self.num_leaves,
            'learning_rate': min(self.learning_rate, 0.01),
            'feature_fraction': self.feature_fraction,
            'bagging_fraction': self.bagging_fraction,
            'bagging_freq': self.bagging_freq,
            'min_data_in_leaf': max(self.min_data_in_leaf, 50),
            'lambda_l1': self.lambda_l1 * 1.5,
            'lambda_l2': self.lambda_l2 * 1.5,
            'verbosity': -1,
            'seed': 42
        }
        
        train_data = lgb.Dataset(X_train, label=y_train, weight=sample_weight, free_raw_data=False)
        valid_sets = [train_data]
        valid_names = ['train']
        
        if X_val is not None and y_val is not None:
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data, free_raw_data=False)
            valid_sets.append(val_data)
            valid_names.append('val')
        
        callbacks = []
        if X_val is not None and y_val is not None:
            callbacks.append(lgb.early_stopping(self.early_stopping_rounds, verbose=False))
        callbacks.append(lgb.log_evaluation(period=0))
        
        q50_model = lgb.train(
            q50_params,
            train_data,
            num_boost_round=self.n_estimators,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks
        )
        
        self.quantile_models[0.5] = q50_model
        self.model = q50_model  # Also set as main model for point predictions
        logger.info("   ✅ q50 model trained")
        
        # Step 2: Get q50 predictions for training constrained quantiles
        q50_pred_train = q50_model.predict(X_train)
        q50_pred_val = q50_model.predict(X_val) if X_val is not None else None
        
        # Compute residuals and residual std for minimum spread floor
        residuals_train = y_train.values - q50_pred_train
        residual_std = np.std(residuals_train)
        residual_mae = np.mean(np.abs(residuals_train))
        # Use a more meaningful minimum spread: at least 5% of MAE or 10% of std, whichever is larger
        min_spread = max(0.5, min(residual_mae * 0.05, residual_std * 0.15))
        logger.info(f"   Residual std: {residual_std:.3f}, Residual MAE: {residual_mae:.3f}, Minimum spread floor: {min_spread:.3f}")
        
        # Step 3: Train delta_down model (q50 - q10) 
        # Use absolute residuals as target, with minimum floor to prevent zero predictions
        if 0.1 in quantiles:
            logger.info("   Step 2: Training delta_down model (q50 - q10)...")
            # Use absolute value of negative residuals (when q50 > y_true)
            # Add adaptive spread: scale with q50 prediction magnitude to ensure meaningful separation
            negative_residuals = np.minimum(0, residuals_train)  # Only negative residuals
            abs_negative = np.abs(negative_residuals)
            # Ensure minimum spread but also scale with prediction magnitude (at least 1% of q50)
            adaptive_min = np.maximum(min_spread, q50_pred_train * 0.01)
            delta_down_train = np.maximum(adaptive_min, abs_negative)
            delta_down_val = None
            if q50_pred_val is not None and y_val is not None:
                residuals_val = y_val.values - q50_pred_val
                negative_residuals_val = np.minimum(0, residuals_val)
                abs_negative_val = np.abs(negative_residuals_val)
                adaptive_min_val = np.maximum(min_spread, q50_pred_val * 0.01)
                delta_down_val = np.maximum(adaptive_min_val, abs_negative_val)
            
            # Use regression objective instead of quantile for spread (more stable)
            delta_down_params = q50_params.copy()
            delta_down_params['objective'] = 'regression'  # Use regression for spread prediction
            delta_down_params['seed'] = 43
            delta_down_params.pop('monotone_constraints', None)
            # Reduce regularization slightly for spread models
            delta_down_params['lambda_l1'] = delta_down_params.get('lambda_l1', 0.1) * 0.8
            delta_down_params['lambda_l2'] = delta_down_params.get('lambda_l2', 0.1) * 0.8
            
            train_data_delta = lgb.Dataset(X_train, label=delta_down_train, weight=sample_weight, free_raw_data=False)
            valid_sets_delta = [train_data_delta]
            valid_names_delta = ['train']
            
            if delta_down_val is not None:
                val_data_delta = lgb.Dataset(X_val, label=delta_down_val, reference=train_data_delta, free_raw_data=False)
                valid_sets_delta.append(val_data_delta)
                valid_names_delta.append('val')
            
            delta_down_model = lgb.train(
                delta_down_params,
                train_data_delta,
                num_boost_round=self.n_estimators,
                valid_sets=valid_sets_delta,
                valid_names=valid_names_delta,
                callbacks=callbacks
            )
            
            self.quantile_models['delta_down'] = delta_down_model
            logger.info("   ✅ delta_down model trained")
        
        # Step 4: Train delta_up model (q90 - q50)
        # Use absolute residuals above q50, with minimum floor to prevent zero predictions
        if 0.9 in quantiles:
            logger.info("   Step 3: Training delta_up model (q90 - q50)...")
            # Use absolute value of positive residuals (when y_true > q50)
            # Add adaptive spread: scale with q50 prediction magnitude to ensure meaningful separation
            positive_residuals = np.maximum(0, residuals_train)  # Only positive residuals
            # Ensure minimum spread but also scale with prediction magnitude (at least 1% of q50)
            adaptive_min = np.maximum(min_spread, q50_pred_train * 0.01)
            delta_up_train = np.maximum(adaptive_min, positive_residuals)
            delta_up_val = None
            if q50_pred_val is not None and y_val is not None:
                residuals_val = y_val.values - q50_pred_val
                positive_residuals_val = np.maximum(0, residuals_val)
                adaptive_min_val = np.maximum(min_spread, q50_pred_val * 0.01)
                delta_up_val = np.maximum(adaptive_min_val, positive_residuals_val)
            
            # Use regression objective instead of quantile for spread (more stable)
            delta_up_params = q50_params.copy()
            delta_up_params['objective'] = 'regression'  # Use regression for spread prediction
            delta_up_params['seed'] = 44
            delta_up_params.pop('monotone_constraints', None)
            # Reduce regularization slightly for spread models
            delta_up_params['lambda_l1'] = delta_up_params.get('lambda_l1', 0.1) * 0.8
            delta_up_params['lambda_l2'] = delta_up_params.get('lambda_l2', 0.1) * 0.8
            
            train_data_delta = lgb.Dataset(X_train, label=delta_up_train, weight=sample_weight, free_raw_data=False)
            valid_sets_delta = [train_data_delta]
            valid_names_delta = ['train']
            
            if delta_up_val is not None:
                val_data_delta = lgb.Dataset(X_val, label=delta_up_val, reference=train_data_delta, free_raw_data=False)
                valid_sets_delta.append(val_data_delta)
                valid_names_delta.append('val')
            
            delta_up_model = lgb.train(
                delta_up_params,
                train_data_delta,
                num_boost_round=self.n_estimators,
                valid_sets=valid_sets_delta,
                valid_names=valid_names_delta,
                callbacks=callbacks
            )
            
            self.quantile_models['delta_up'] = delta_up_model
            logger.info("   ✅ delta_up model trained")
        
        self.is_fitted = True
        logger.info("   ✅ Structural quantile training complete (monotonicity enforced structurally)")
        
        # Post-training validation: Check if quantiles differ
        if X_val is not None:
            try:
                test_preds = self.predict_quantiles_spread(X_val, quantiles=quantiles)
                q10_pred = test_preds.get(0.1)
                q50_pred = test_preds.get(0.5)
                q90_pred = test_preds.get(0.9)
                
                if q10_pred is not None and q50_pred is not None:
                    if np.allclose(q10_pred, q50_pred, rtol=1e-5, atol=1e-5):
                        logger.error("   ❌ CRITICAL: q10 and q50 predictions are IDENTICAL!")
                        logger.error("   This indicates quantile model implementation failure")
                    else:
                        mean_diff = np.mean(np.abs(q50_pred - q10_pred))
                        logger.info(f"   ✅ q10-q50 separation: mean={mean_diff:.3f}, min={np.min(np.abs(q50_pred - q10_pred)):.3f}")
                
                if q50_pred is not None and q90_pred is not None:
                    if np.allclose(q50_pred, q90_pred, rtol=1e-5, atol=1e-5):
                        logger.error("   ❌ CRITICAL: q50 and q90 predictions are IDENTICAL!")
                        logger.error("   This indicates quantile model implementation failure")
                    else:
                        mean_diff = np.mean(np.abs(q90_pred - q50_pred))
                        logger.info(f"   ✅ q50-q90 separation: mean={mean_diff:.3f}, min={np.min(np.abs(q90_pred - q50_pred)):.3f}")
            except Exception as e:
                logger.warning(f"   Post-training validation failed: {e}")
        
        return self
    
    def fit_quantiles_spread(self,
                            X_train: pd.DataFrame,
                            y_train: pd.Series,
                            X_val: Optional[pd.DataFrame] = None,
                            y_val: Optional[pd.Series] = None,
                            quantiles: list = [0.1, 0.5, 0.9],
                            sample_weight: Optional[np.ndarray] = None) -> 'LightGBMForecaster':
        """
        Train quantile models using spread approach (q50 + spread models).
        
        This enforces natural ordering structurally:
        - Train q50 model (median)
        - Train delta_up model (q90 - q50)
        - Train delta_down model (q50 - q10)
        - Final: q10 = q50 - delta_down, q90 = q50 + delta_up
        
        Args:
            X_train: Training features
            y_train: Training targets
            X_val: Validation features
            y_val: Validation targets
            quantiles: Quantiles to predict (must include 0.5)
            sample_weight: Sample weights
        """
        from ..utils import get_logger
        logger = get_logger(__name__)
        
        logger.info("=" * 60)
        logger.info("QUANTILE SPREAD TRAINING: q50 + spread models")
        logger.info("=" * 60)
        
        if 0.5 not in quantiles:
            raise ValueError("Quantile spread training requires 0.5 (median) in quantiles")
        
        # Step 1: Train q50 model (median)
        logger.info("   Step 1: Training q50 (median) model...")
        q50_params = {
            'objective': 'quantile',
            'alpha': 0.5,
            'metric': 'mae',
            'boosting_type': 'gbdt',
            'num_leaves': self.num_leaves,
            'learning_rate': self.learning_rate,
            'feature_fraction': self.feature_fraction,
            'bagging_fraction': self.bagging_fraction,
            'bagging_freq': self.bagging_freq,
            'min_data_in_leaf': self.min_data_in_leaf,
            'lambda_l1': self.lambda_l1,
            'lambda_l2': self.lambda_l2,
            'verbosity': -1,
            'seed': 42
        }
        
        train_data = lgb.Dataset(X_train, label=y_train, weight=sample_weight, free_raw_data=False)
        valid_sets = [train_data]
        valid_names = ['train']
        
        if X_val is not None and y_val is not None:
            val_data = lgb.Dataset(X_val, label=y_val, reference=train_data, free_raw_data=False)
            valid_sets.append(val_data)
            valid_names.append('val')
        
        callbacks = []
        if X_val is not None and y_val is not None:
            callbacks.append(lgb.early_stopping(self.early_stopping_rounds, verbose=False))
        callbacks.append(lgb.log_evaluation(period=0))
        
        q50_model = lgb.train(
            q50_params,
            train_data,
            num_boost_round=self.n_estimators,
            valid_sets=valid_sets,
            valid_names=valid_names,
            callbacks=callbacks
        )
        
        self.quantile_models[0.5] = q50_model
        logger.info("   ✅ q50 model trained")
        
        # Step 2: Get q50 predictions for training spread models
        q50_pred_train = q50_model.predict(X_train)
        q50_pred_val = q50_model.predict(X_val) if X_val is not None else None
        
        # Step 3: Train delta_down model (q50 - q10)
        if 0.1 in quantiles:
            logger.info("   Step 2: Training delta_down model (q50 - q10)...")
            delta_down_train = np.maximum(0, q50_pred_train - y_train.values)  # q50 - y_true (positive when q50 > y_true)
            delta_down_val = np.maximum(0, q50_pred_val - y_val.values) if (q50_pred_val is not None and y_val is not None) else None
            
            # Train model to predict delta_down
            delta_down_params = q50_params.copy()
            delta_down_params['objective'] = 'quantile'
            delta_down_params['alpha'] = 0.9  # Predict 90th percentile of delta_down (conservative)
            delta_down_params['seed'] = 43
            
            train_data_delta = lgb.Dataset(X_train, label=delta_down_train, weight=sample_weight, free_raw_data=False)
            valid_sets_delta = [train_data_delta]
            valid_names_delta = ['train']
            
            if delta_down_val is not None:
                val_data_delta = lgb.Dataset(X_val, label=delta_down_val, reference=train_data_delta, free_raw_data=False)
                valid_sets_delta.append(val_data_delta)
                valid_names_delta.append('val')
            
            delta_down_model = lgb.train(
                delta_down_params,
                train_data_delta,
                num_boost_round=self.n_estimators,
                valid_sets=valid_sets_delta,
                valid_names=valid_names_delta,
                callbacks=callbacks
            )
            
            self.quantile_models['delta_down'] = delta_down_model
            logger.info("   ✅ delta_down model trained")
        
        # Step 4: Train delta_up model (q90 - q50)
        if 0.9 in quantiles:
            logger.info("   Step 3: Training delta_up model (q90 - q50)...")
            delta_up_train = np.maximum(0, y_train.values - q50_pred_train)  # y_true - q50 (positive when y_true > q50)
            delta_up_val = np.maximum(0, y_val.values - q50_pred_val) if (q50_pred_val is not None and y_val is not None) else None
            
            # Train model to predict delta_up
            delta_up_params = q50_params.copy()
            delta_up_params['objective'] = 'quantile'
            delta_up_params['alpha'] = 0.9  # Predict 90th percentile of delta_up (conservative)
            delta_up_params['seed'] = 44
            
            train_data_delta = lgb.Dataset(X_train, label=delta_up_train, weight=sample_weight, free_raw_data=False)
            valid_sets_delta = [train_data_delta]
            valid_names_delta = ['train']
            
            if delta_up_val is not None:
                val_data_delta = lgb.Dataset(X_val, label=delta_up_val, reference=train_data_delta, free_raw_data=False)
                valid_sets_delta.append(val_data_delta)
                valid_names_delta.append('val')
            
            delta_up_model = lgb.train(
                delta_up_params,
                train_data_delta,
                num_boost_round=self.n_estimators,
                valid_sets=valid_sets_delta,
                valid_names=valid_names_delta,
                callbacks=callbacks
            )
            
            self.quantile_models['delta_up'] = delta_up_model
            logger.info("   ✅ delta_up model trained")
        
        # Also store q50 as main model for point predictions
        self.model = q50_model
        self.is_fitted = True
        
        logger.info("   ✅ Quantile spread training complete")
        
        return self
    
    def predict_quantiles_spread(self, X: pd.DataFrame, quantiles: list = [0.1, 0.5, 0.9]) -> Dict[float, np.ndarray]:
        """
        Predict quantiles using spread approach.
        
        Returns:
            Dictionary mapping quantile -> predictions
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit_quantiles_spread() first.")
        
        results = {}
        
        # Get q50 prediction
        if 0.5 in quantiles and 0.5 in self.quantile_models:
            q50_pred = self.quantile_models[0.5].predict(X)
            results[0.5] = q50_pred
        else:
            raise ValueError("q50 model not available")
        
        # Get delta_down and delta_up predictions
        delta_down_pred = None
        delta_up_pred = None
        
        if 'delta_down' in self.quantile_models:
            delta_down_pred_raw = self.quantile_models['delta_down'].predict(X)
            # Ensure minimum spread: at least 0.5 or 1% of q50, whichever is larger
            adaptive_floor = np.maximum(0.5, q50_pred * 0.01)
            delta_down_pred = np.maximum(adaptive_floor, delta_down_pred_raw)
        
        if 'delta_up' in self.quantile_models:
            delta_up_pred_raw = self.quantile_models['delta_up'].predict(X)
            # Ensure minimum spread: at least 0.5 or 1% of q50, whichever is larger
            adaptive_floor = np.maximum(0.5, q50_pred * 0.01)
            delta_up_pred = np.maximum(adaptive_floor, delta_up_pred_raw)
        
        # Construct q10 and q90
        if 0.1 in quantiles and delta_down_pred is not None:
            results[0.1] = q50_pred - delta_down_pred
        
        if 0.9 in quantiles and delta_up_pred is not None:
            results[0.9] = q50_pred + delta_up_pred
        
        # Enforce monotonicity (hard enforcement)
        if 0.1 in results and 0.5 in results:
            results[0.5] = np.maximum(results[0.5], results[0.1])
        if 0.5 in results and 0.9 in results:
            results[0.9] = np.maximum(results[0.9], results[0.5])
        
        return results
    
    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """Make point predictions."""
        if not self.is_fitted or self.model is None:
            raise ValueError("Model not fitted. Call fit() first.")
        return self.model.predict(X)
    
    def predict_quantiles(self, X: pd.DataFrame, quantiles: list = [0.1, 0.5, 0.9]) -> Dict[float, np.ndarray]:
        """
        Make quantile predictions.
        
        CRITICAL: Each quantile uses separate model instance to ensure predictions differ.
        Automatically detects if structural training was used and routes accordingly.
        """
        if not self.is_fitted:
            raise ValueError("Model not fitted. Call fit() or fit_quantiles() first.")
        
        # Check if structural training was used (has delta_down or delta_up models)
        if self.quantile_models and ('delta_down' in self.quantile_models or 'delta_up' in self.quantile_models):
            # Use structural/spread prediction method
            return self.predict_quantiles_spread(X, quantiles=quantiles)
        
        results = {}
        
        # Use quantile models if available (standard quantile training)
        if self.quantile_models:
            for q in quantiles:
                if q in self.quantile_models:
                    # CRITICAL: Each quantile model is separate instance
                    results[q] = self.quantile_models[q].predict(X)
                else:
                    # Fallback to point prediction
                    results[q] = self.predict(X)
        else:
            # Fallback: use point prediction for all quantiles
            point_pred = self.predict(X)
            for q in quantiles:
                results[q] = point_pred
        
        # Post-prediction validation: ensure quantiles differ and enforce monotonicity
        if len(results) >= 2:
            quantiles_sorted = sorted(results.keys())
            for i in range(len(quantiles_sorted) - 1):
                q_low = quantiles_sorted[i]
                q_high = quantiles_sorted[i + 1]
                pred_low = results[q_low]
                pred_high = results[q_high]
                
                # Check if predictions are identical (bug detection)
                if np.allclose(pred_low, pred_high, rtol=1e-5, atol=1e-5):
                    from ..utils import get_logger
                    logger = get_logger(__name__)
                    logger.error(f"   ❌ CRITICAL: q{int(q_low*100)} and q{int(q_high*100)} predictions are IDENTICAL!")
                    logger.error("   This indicates quantile model implementation failure")
                
                # CRITICAL: Enforce monotonicity before returning
                # q10 <= q50 <= q90 must hold for all samples
                violations = np.sum(pred_low > pred_high)
                if violations > 0:
                    # Correct monotonicity violations
                    results[q_high] = np.maximum(results[q_high], results[q_low])
                    from ..utils import get_logger
                    logger = get_logger(__name__)
                    logger.warning(f"   ⚠️  Corrected {violations} monotonicity violations: q{int(q_low*100)} > q{int(q_high*100)}")
        
        return results
    
    def get_feature_importance(self, X: pd.DataFrame) -> pd.DataFrame:
        """Get feature importance."""
        if not self.is_fitted or self.model is None:
            raise ValueError("Model not fitted.")
        
        importance = self.model.feature_importance(importance_type='gain')
        feature_names = X.columns.tolist()
        
        df = pd.DataFrame({
            'feature': feature_names,
            'importance': importance
        }).sort_values('importance', ascending=False)
        
        df['importance_pct'] = (df['importance'] / df['importance'].sum() * 100).round(2)
        
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
                    'num_leaves': self.num_leaves,
                    'min_data_in_leaf': self.min_data_in_leaf,
                }
            }, f)
    
    @classmethod
    def load(cls, filepath: str) -> 'LightGBMForecaster':
        """Load model from disk."""
        with open(filepath, 'rb') as f:
            data = pickle.load(f)
        
        model = cls(**data['params'])
        model.model = data['model']
        model.quantile_models = data.get('quantile_models', {})
        model.is_fitted = True
        
        return model

