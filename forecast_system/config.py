"""
Configuration for Forecasting System

Centralized configuration for easy tuning.
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ModelConfig:
    """Model hyperparameters."""
    n_estimators: int = 1000
    learning_rate: float = 0.05
    early_stopping_rounds: int = 100


@dataclass
class LightGBMConfig(ModelConfig):
    """LightGBM specific config."""
    num_leaves: int = 31
    min_data_in_leaf: int = 20
    feature_fraction: float = 0.9
    bagging_fraction: float = 0.8
    bagging_freq: int = 5
    lambda_l1: float = 0.1
    lambda_l2: float = 0.1


@dataclass
class XGBoostConfig(ModelConfig):
    """XGBoost specific config."""
    max_depth: int = 8
    min_child_weight: int = 3
    subsample: float = 0.9
    colsample_bytree: float = 0.9
    reg_alpha: float = 0.2
    reg_lambda: float = 1.0


@dataclass
class TrainingConfig:
    """Training configuration."""
    # Data
    csv_path: str = "dataset/synthetic_hospital_data.csv"
    
    # Target engineering
    target_mode: str = 'raw_admissions'  # 'raw_admissions', 'log_admissions', 'utilization_ratio', 'delta_admissions'
    
    # Splitting
    train_years: int = 4
    test_years: int = 1
    
    # CV
    cv_splits: int = 3  # Reduced from 5 to ensure 3+ folds with 1.5 year min requirement
    cv_expanding: bool = True  # Use expanding window for better stability
    cv_train_size: Optional[int] = None
    cv_test_size: Optional[int] = None  # In samples (days)
    cv_step: Optional[int] = None  # Step between folds
    
    # Models
    compare_models: bool = True
    models_to_test: List[str] = None  # Will default to ['lightgbm', 'xgboost']
    final_model: str = 'lightgbm'
    
    # Features
    use_quantiles: bool = True
    quantiles: List[float] = None  # Will default to [0.1, 0.5, 0.9]
    include_exogenous_lags: bool = True
    include_interactions: bool = True
    
    # Weighting
    use_sample_weights: bool = True
    sample_weight_method: str = 'inverse_capacity'  # 'inverse_admissions', 'inverse_capacity', 'inverse_population', 'equal'
    
    # Post-processing
    max_utilization: float = 1.2  # Maximum allowed utilization (120%)
    surge_threshold: float = 0.9  # Utilization threshold for surge detection (90%)
    
    # Quantile training strategy
    use_quantile_spread_models: bool = True  # Use q50 + spread models instead of independent quantiles
    quantile_smoothing: bool = True  # Smooth quantiles across horizons
    quantile_smoothing_alpha: float = 0.7  # Smoothing factor (0.7 * q_h + 0.3 * q_(h-1))
    quantile_smoothing_horizons: List[int] = None  # Horizons to apply smoothing (default: [5, 6, 7])
    
    # Option A: Tree Robustness Enhancements
    use_regime_split_models: bool = False  # Train separate models for normal vs surge regimes (reduces CoV)
    use_rolling_retraining: bool = False  # Enable rolling retraining every 30 days (production robustness)
    rolling_retrain_window_months: int = 24  # Training window for rolling retraining
    rolling_retrain_frequency_days: int = 30  # Retrain frequency
    
    # TFT Decision Framework
    evaluate_tft_need: bool = True  # Evaluate if TFT is needed after Option A improvements
    tft_acf_threshold: float = 0.40  # ACF threshold for TFT recommendation
    tft_cov_threshold: float = 40.0  # CoV threshold for TFT recommendation
    
    # Feature group weights (to reduce autoregressive dominance)
    feature_group_weights: dict = None  # Will default to balanced weights
    boost_exogenous_during_regime_shifts: bool = True  # Increase weight for exogenous features during regime shifts
    
    # Residual autocorrelation threshold
    max_residual_acf: float = 0.35  # Training fails if lag-1 ACF > this threshold
    
    # CV stabilization
    cv_min_train_years: float = 0.95  # Reduced to 0.95 to allow first fold (364 days ≈ 0.997 years, close enough)
    cv_expanding_window: bool = True  # Use expanding window CV
    cv_min_folds: int = 2  # Reduced to 2 to allow CV with limited data (but still prefer 3+)
    
    # Error features
    use_error_features: bool = True  # Use recursive error features instead of AR residual layer
    
    # Diagnostic modes
    stress_test_reduce_ar: bool = False  # Run stress test: drop lag_1 and ema_7, measure MAE change
    analyze_feature_groups: bool = True  # Analyze feature importance by group (AR vs exogenous)
    
    # Hyperparameter tuning
    enable_hyperparameter_tuning: bool = False
    tuning_n_trials: int = 50
    
    # Model registry
    save_model_registry: bool = True
    registry_dir: str = "models/registry"
    
    # Output
    output_dir: str = "models/forecast_system"
    
    def __post_init__(self):
        if self.models_to_test is None:
            self.models_to_test = ['lightgbm', 'xgboost']
        if self.quantiles is None:
            self.quantiles = [0.1, 0.5, 0.9]
        if self.quantile_smoothing_horizons is None:
            self.quantile_smoothing_horizons = [5, 6, 7]
        if self.feature_group_weights is None:
            self.feature_group_weights = {
                "autoregressive": 1.0,
                "exogenous": 1.5,
                "regime": 1.2,
                "interaction": 1.0,
                "temporal": 1.0
            }


# Default configurations
DEFAULT_LIGHTGBM_CONFIG = LightGBMConfig()
DEFAULT_XGBOOST_CONFIG = XGBoostConfig()
DEFAULT_TRAINING_CONFIG = TrainingConfig()

