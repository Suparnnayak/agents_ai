import xgboost as xgb
import lightgbm as lgb
import numpy as np
import pandas as pd
from pathlib import Path
import optuna
from sklearn.metrics import mean_absolute_error
from src.pipeline.utils import save_model
from src.pipeline.logger import get_logger

logger = get_logger(__name__)


# ----------------------------------------------
# XGBOOST — Median Model (q50) with Optuna Tuning
# ----------------------------------------------
def train_xgb_median(
    X_train, y_train, X_val, y_val,
    use_optuna=True,
    n_trials=50,
    monotonic_constraints=None
):
    """
    Train XGBoost median model with optional Optuna hyperparameter tuning.
    
    Args:
        X_train, y_train: Training data
        X_val, y_val: Validation data
        use_optuna: Whether to use Optuna for hyperparameter tuning
        n_trials: Number of Optuna trials (if use_optuna=True)
        monotonic_constraints: Dict mapping feature names to constraints (1=increasing, -1=decreasing, 0=none)
    """
    
    if use_optuna:
        logger.info(f"🔍 Starting Optuna hyperparameter tuning for XGBoost (n_trials={n_trials})...")
        
        def objective(trial):
            params = {
                "objective": "reg:squarederror",
                "eta": trial.suggest_float("eta", 0.01, 0.3, log=True),
                "max_depth": trial.suggest_int("max_depth", 4, 10),
                "subsample": trial.suggest_float("subsample", 0.6, 1.0),
                "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
                "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
                "lambda": trial.suggest_float("lambda", 1e-8, 10.0, log=True),
                "alpha": trial.suggest_float("alpha", 1e-8, 10.0, log=True),
                "tree_method": "hist",
                "eval_metric": "mae",
                "verbosity": 0
            }
            
            # Add monotonic constraints if provided
            if monotonic_constraints and isinstance(X_train, pd.DataFrame):
                feature_names = X_train.columns.tolist()
                constraints = []
                for feat in feature_names:
                    if feat in monotonic_constraints:
                        constraints.append(monotonic_constraints[feat])
                    else:
                        constraints.append(0)
                params["monotone_constraints"] = tuple(constraints)
            
            dtrain = xgb.DMatrix(X_train, label=y_train)
            dval = xgb.DMatrix(X_val, label=y_val)
            
            model = xgb.train(
                params,
                dtrain,
                num_boost_round=2000,
                evals=[(dval, "val")],
                early_stopping_rounds=100,
                verbose_eval=False
            )
            
            preds = model.predict(dval)
            mae = mean_absolute_error(y_val, preds)
            return mae
        
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
        
        best_params = study.best_params
        logger.info(f"✅ Best XGBoost params: {best_params}")
        logger.info(f"   Best MAE: {study.best_value:.4f}")
        
        # Use best params for final training
        params = {
            "objective": "reg:squarederror",
            "eta": best_params["eta"],
            "max_depth": best_params["max_depth"],
            "subsample": best_params["subsample"],
            "colsample_bytree": best_params["colsample_bytree"],
            "min_child_weight": best_params["min_child_weight"],
            "lambda": best_params["lambda"],
            "alpha": best_params["alpha"],
            "tree_method": "hist",
            "eval_metric": "mae"
        }
    else:
        # Optimized default parameters for time-series forecasting
        params = {
            "objective": "reg:squarederror",
            "eta": 0.03,
            "max_depth": 8,
            "min_child_weight": 3,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "gamma": 0.2,
            "lambda": 1.0,
            "alpha": 0.2,
            "tree_method": "hist",
            "eval_metric": "mae"
        }
    
    # Add monotonic constraints if provided and not using Optuna (Optuna handles it internally)
    if monotonic_constraints and not use_optuna and isinstance(X_train, pd.DataFrame):
        feature_names = X_train.columns.tolist()
        constraints = []
        for feat in feature_names:
            if feat in monotonic_constraints:
                constraints.append(monotonic_constraints[feat])
            else:
                constraints.append(0)
        params["monotone_constraints"] = tuple(constraints)
        logger.info(f"📊 Applied monotonic constraints: {monotonic_constraints}")
    
    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)
    
    logger.info("🚀 Training final XGBoost median model...")
    model = xgb.train(
        params,
        dtrain,
        num_boost_round=2000,
        evals=[(dtrain, "train"), (dval, "val")],
        early_stopping_rounds=200,
        verbose_eval=100
    )
    
    logger.info(f"✅ XGBoost training completed. Best iteration: {model.best_iteration}")
    return model


# ----------------------------------------------
# XGBOOST — Quantile Models (q10, q50, q90)
# ----------------------------------------------
def train_xgb_quantile(
    X_train, y_train, X_val, y_val,
    alpha: float,
    n_estimators: int = 600,
    monotonic_constraints=None
):
    """
    Train a single XGBoost quantile model for a given alpha (0.1, 0.5, 0.9).
    Uses the same global feature set for all cities.
    """
    logger.info(f"🚀 Training XGBoost quantile model (alpha={alpha})...")

    params = {
        # Quantile regression objective
        "objective": "reg:absoluteerror",
        # Required quantile parameter for XGBoost
        "quantile_alpha": alpha,
        # Tree configuration
        "eta": 0.03,
        "max_depth": 8,
        "min_child_weight": 3,
        "subsample": 0.9,
        "colsample_bytree": 0.9,
        "gamma": 0.2,
        # Regularization
        "lambda": 2.0,
        "alpha": 1.0,
        # Training options
        "tree_method": "hist",
        "eval_metric": "mae"
    }

    # Apply monotonic constraints if provided
    if monotonic_constraints is not None and isinstance(X_train, pd.DataFrame):
        feature_names = X_train.columns.tolist()
        constraints = []
        for feat in feature_names:
            constraints.append(monotonic_constraints.get(feat, 0))
        params["monotone_constraints"] = tuple(constraints)
        logger.info(f"📊 Applied monotonic constraints for quantile model (alpha={alpha})")

    dtrain = xgb.DMatrix(X_train, label=y_train)
    dval = xgb.DMatrix(X_val, label=y_val)

    model = xgb.train(
        params,
        dtrain,
        num_boost_round=n_estimators,
        evals=[(dtrain, "train"), (dval, "val")],
        early_stopping_rounds=200,
        verbose_eval=100
    )

    logger.info(f"✅ XGBoost quantile (alpha={alpha}) training completed, best_iteration={model.best_iteration}")
    return model


def train_spike_booster(
    X_train,
    residuals,
    mask,
    y_train=None,
    n_estimators: int = 2500,
    eta: float = 0.3,
):
    """
    Train an ULTRA-aggressive spike-correction booster using weighted training.
    Enhanced to capture extreme spikes (300-650+ admissions) with two-stage approach.
    """
    mask_array = np.asarray(mask, dtype=bool)
    n_spikes = mask_array.sum()
    
    if n_spikes < 25:
        logger.warning("⚠️ Not enough spike samples to train correction model.")
        return None

    logger.info(f"📊 Training spike booster on {n_spikes}/{len(mask_array)} spike samples")

    residuals_array = np.asarray(residuals)
    
    # ULTRA-aggressive weighting: focus heavily on largest residuals
    sample_weights = np.ones(len(mask_array))
    sample_weights[mask_array] = 15.0  # Increased from 10x
    
    # Weight by residual magnitude - extreme positive residuals get highest weight
    residual_magnitude = np.abs(residuals_array)
    
    # Extreme spikes (top 15% of residuals) get 30x weight
    extreme_mask = residual_magnitude > np.percentile(residual_magnitude, 85)
    sample_weights[extreme_mask] *= 2.0  # 30x total
    
    # Super-extreme spikes (top 5% of residuals) get 60x weight
    super_extreme_mask = residual_magnitude > np.percentile(residual_magnitude, 95)
    sample_weights[super_extreme_mask] *= 2.0  # 60x total
    
    # Ultra-extreme spikes (top 1% of residuals) get 120x weight
    ultra_extreme_mask = residual_magnitude > np.percentile(residual_magnitude, 99)
    sample_weights[ultra_extreme_mask] *= 2.0  # 120x total
    
    # Focus heavily on positive residuals (underpredictions)
    positive_residual_mask = residuals_array > 0
    sample_weights[positive_residual_mask] *= 1.5  # Increased from 1.2x
    
    # Very large positive residuals get even more weight
    large_positive_mask = residuals_array > np.percentile(residuals_array[residuals_array > 0], 90) if (residuals_array > 0).sum() > 0 else np.zeros_like(residuals_array, dtype=bool)
    sample_weights[large_positive_mask] *= 1.5  # Additional boost

    params = {
        "objective": "reg:squarederror",
        "eta": eta,  # Even higher learning rate
        "max_depth": 10,  # Deeper trees for complex patterns
        "min_child_weight": 0.1,  # Very low to allow splits on small groups
        "subsample": 0.75,  # Lower to prevent overfitting
        "colsample_bytree": 0.75,
        "lambda": 0.05,  # Minimal regularization
        "alpha": 0.0,
        "tree_method": "hist",
        "eval_metric": "mae",
        "max_delta_step": 20,  # Much larger step sizes (increased from 10)
        "gamma": 0.0,
        "scale_pos_weight": 1.0,  # Balance for positive residuals
    }

    # Train on ALL data with sample weights
    dtrain = xgb.DMatrix(X_train, label=residuals, weight=sample_weights)
    
    booster = xgb.train(
        params,
        dtrain,
        num_boost_round=n_estimators,
        verbose_eval=100,
    )
    
    # Log statistics
    spike_preds = booster.predict(xgb.DMatrix(X_train.loc[mask_array]))
    avg_spike_adj = np.mean(spike_preds)
    max_spike_adj = np.max(spike_preds)
    min_spike_adj = np.min(spike_preds)
    p95_spike_adj = np.percentile(spike_preds, 95)
    logger.info(f"✅ Spike booster trained: avg={avg_spike_adj:.2f}, max={max_spike_adj:.2f}, p95={p95_spike_adj:.2f}")
    
    return booster


def train_extreme_spike_booster(
    X_train,
    residuals,
    y_train,
    n_estimators: int = 3000,
    eta: float = 0.35,
):
    """
    Train a SECOND-STAGE extreme spike booster for the top 1-2% of residuals.
    This targets only the most extreme events (600+ admissions).
    """
    residuals_array = np.asarray(residuals)
    
    # Only train on the top 1% of positive residuals (most extreme underpredictions)
    top_1_pct_threshold = np.percentile(residuals_array[residuals_array > 0], 99) if (residuals_array > 0).sum() > 0 else np.max(residuals_array)
    extreme_mask = (residuals_array > top_1_pct_threshold) & (residuals_array > 0)
    n_extreme = extreme_mask.sum()
    
    if n_extreme < 10:
        logger.warning("⚠️ Not enough extreme spike samples (< 10) to train second-stage booster.")
        return None
    
    logger.info(f"🔥 Training EXTREME spike booster on {n_extreme}/{len(residuals_array)} ultra-extreme samples")
    logger.info(f"   Target threshold: residuals > {top_1_pct_threshold:.2f}")
    
    # Ultra-extreme weighting: only the top 1% get massive weight
    sample_weights = np.ones(len(residuals_array))
    sample_weights[extreme_mask] = 200.0  # Massive weight for extreme events
    
    # Additional boost for the absolute largest residuals
    if n_extreme > 5:
        top_5_residuals = np.argsort(residuals_array)[-5:]
        sample_weights[top_5_residuals] = 500.0  # Extreme weight for top 5
    
    params = {
        "objective": "reg:squarederror",
        "eta": eta,  # Very high learning rate
        "max_depth": 12,  # Very deep trees
        "min_child_weight": 0.05,  # Extremely low
        "subsample": 0.7,
        "colsample_bytree": 0.7,
        "lambda": 0.01,  # Almost no regularization
        "alpha": 0.0,
        "tree_method": "hist",
        "eval_metric": "mae",
        "max_delta_step": 50,  # Huge step sizes for extreme corrections
        "gamma": 0.0,
    }
    
    dtrain = xgb.DMatrix(X_train, label=residuals, weight=sample_weights)
    
    booster = xgb.train(
        params,
        dtrain,
        num_boost_round=n_estimators,
        verbose_eval=200,
    )
    
    # Log statistics
    extreme_preds = booster.predict(xgb.DMatrix(X_train.loc[extreme_mask]))
    avg_extreme_adj = np.mean(extreme_preds)
    max_extreme_adj = np.max(extreme_preds)
    logger.info(f"🔥 Extreme spike booster: avg={avg_extreme_adj:.2f}, max={max_extreme_adj:.2f}")
    
    return booster


# ----------------------------------------------
# LIGHTGBM — Quantile Models (q10, q90) with Optuna Tuning
# ----------------------------------------------
def train_lgb_quantile(
    X_train, y_train, X_val, y_val,
    quantile,
    use_optuna=True,
    n_trials=50,
    monotonic_constraints=None
):
    """
    Train LightGBM quantile model with optional Optuna hyperparameter tuning.
    
    Args:
        X_train, y_train: Training data
        X_val, y_val: Validation data
        quantile: Target quantile (0.1 for q10, 0.9 for q90)
        use_optuna: Whether to use Optuna for hyperparameter tuning
        n_trials: Number of Optuna trials (if use_optuna=True)
        monotonic_constraints: Dict mapping feature names to constraints
    """
    
    if use_optuna:
        logger.info(f"🔍 Starting Optuna hyperparameter tuning for LightGBM q{int(quantile*100)} (n_trials={n_trials})...")
        
        def objective(trial):
            params = {
                "objective": "quantile",
                "alpha": quantile,
                "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
                "num_leaves": trial.suggest_int("num_leaves", 16, 128),
                "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 10, 100),
                "feature_fraction": trial.suggest_float("feature_fraction", 0.6, 1.0),
                "bagging_fraction": trial.suggest_float("bagging_fraction", 0.6, 1.0),
                "bagging_freq": trial.suggest_int("bagging_freq", 1, 7),
                "lambda_l1": trial.suggest_float("lambda_l1", 1e-8, 10.0, log=True),
                "lambda_l2": trial.suggest_float("lambda_l2", 1e-8, 10.0, log=True),
                "metric": "mae",
                "verbosity": -1
            }
            
            # NOTE: LightGBM quantile objective does NOT support monotonic constraints
            # Monotonic constraints are skipped for quantile models
            
            train_ds = lgb.Dataset(X_train, label=y_train)
            val_ds = lgb.Dataset(X_val, label=y_val, reference=train_ds)
            
            model = lgb.train(
                params,
                train_ds,
                num_boost_round=2000,
                valid_sets=[val_ds],
                callbacks=[lgb.early_stopping(100), lgb.log_evaluation(0)]
            )
            
            preds = model.predict(X_val)
            mae = mean_absolute_error(y_val, preds)
            return mae
        
        study = optuna.create_study(direction="minimize")
        study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
        
        best_params = study.best_params
        logger.info(f"✅ Best LightGBM q{int(quantile*100)} params: {best_params}")
        logger.info(f"   Best MAE: {study.best_value:.4f}")
        
        # Use best params for final training
        params = {
            "objective": "quantile",
            "alpha": quantile,
            "learning_rate": best_params["learning_rate"],
            "num_leaves": best_params["num_leaves"],
            "min_data_in_leaf": best_params["min_data_in_leaf"],
            "feature_fraction": best_params["feature_fraction"],
            "bagging_fraction": best_params["bagging_fraction"],
            "bagging_freq": best_params["bagging_freq"],
            "lambda_l1": best_params["lambda_l1"],
            "lambda_l2": best_params["lambda_l2"],
            "metric": "mae"
        }
    else:
        # Default optimized parameters for quantile models
        params = {
            "objective": "quantile",
            "alpha": quantile,
            "learning_rate": 0.01,
            "num_leaves": 128,
            "min_child_samples": 40,
            "min_child_weight": 5,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "bagging_fraction": 0.9,
            "feature_fraction": 0.9,
            "max_depth": -1,
            "reg_alpha": 0.5,
            "reg_lambda": 1.0,
            "metric": "mae"
        }
    
    # NOTE: LightGBM quantile objective does NOT support monotonic constraints
    # Monotonic constraints are only applied to XGBoost median model
    # For quantile models, we skip constraints to avoid LightGBM error
    
    train_ds = lgb.Dataset(X_train, label=y_train)
    val_ds = lgb.Dataset(X_val, label=y_val, reference=train_ds)
    
    logger.info(f"🚀 Training final LightGBM q{int(quantile*100)} model...")
    model = lgb.train(
        params,
        train_ds,
        num_boost_round=5000,
        valid_sets=[train_ds, val_ds],
        callbacks=[
            lgb.early_stopping(200, verbose=False),
            lgb.log_evaluation(100)
        ]
    )
    
    logger.info(f"✅ LightGBM q{int(quantile*100)} training completed. Best iteration: {model.best_iteration}")
    return model


# ----------------------------------------------
# SAVE MODELS
# ----------------------------------------------
def save_trio(city, model_xgb, model_q10, model_q90, outdir="models"):
    """Save all three models for a city."""
    Path(outdir).mkdir(exist_ok=True)
    
    city_lower = city.lower()
    save_model(model_xgb, Path(outdir) / f"{city_lower}_xgb_q50.model")
    save_model(model_q10, Path(outdir) / f"{city_lower}_lgb_q10.model")
    save_model(model_q90, Path(outdir) / f"{city_lower}_lgb_q90.model")
    
    logger.info(f"✅ Saved all 3 quantile models for {city} in {outdir}/")

def save_global_trio(model_xgb, model_q10, model_q90, outdir="models"):
    """Save all three global models (q10, q50, q90)."""
    Path(outdir).mkdir(exist_ok=True)
    
    save_model(model_xgb, Path(outdir) / "global_q50.model")
    save_model(model_q10, Path(outdir) / "global_q10.model")
    save_model(model_q90, Path(outdir) / "global_q90.model")
    
    logger.info(f"✅ Saved all 3 global quantile models in {outdir}/")


def save_spike_model(model_spike, outdir="models", name="global_q50_spike.json"):
    if model_spike is None:
        return
    Path(outdir).mkdir(exist_ok=True)
    save_model(model_spike, Path(outdir) / name)
    logger.info(f"✅ Saved spike correction model to {outdir}/{name}")
