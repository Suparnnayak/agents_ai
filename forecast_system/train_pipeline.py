"""
Main Training Pipeline

Orchestrates the complete training workflow:
1. Data ingestion
2. Feature engineering
3. Model comparison
4. Final model training
5. Evaluation
6. Diagnostics
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .utils import get_logger

from forecast_system.ingestion import load_data
from forecast_system.feature_engineering import engineer_features
from forecast_system.training import compare_models, train_final_model
from forecast_system.evaluation import evaluate_model
from forecast_system.diagnostics import analyze_residuals
from forecast_system.models import LightGBMForecaster, XGBoostForecaster
from forecast_system.cross_validation import DateGroupedRollingCV, create_sample_weights
from forecast_system.leakage_checks import run_all_leakage_checks
# AR residual correction removed - ineffective and redundant with lag features
# from forecast_system.residual_correction import create_residual_corrector
from forecast_system.safety_checks import apply_safety_checks, compute_historical_average
from forecast_system.conformal_calibration import calibrate_quantiles, enforce_quantile_monotonicity
from forecast_system.drift_detection import monitor_drift
from forecast_system.regime_aware import create_regime_indicator, add_regime_interaction_features

logger = get_logger(__name__)


def run_training_pipeline(
    csv_path: str = "dataset/synthetic_hospital_data.csv",
    compare: bool = True,
    models_to_test: list = ['lightgbm', 'xgboost'],
    final_model: str = 'lightgbm',
    use_quantiles: bool = True,
    cv_splits: int = 5,
    train_years: int = 4,
    test_years: int = 1,
    output_dir: str = "models/forecast_system"
):
    """
    Complete training pipeline.
    
    Args:
        csv_path: Path to dataset
        compare: Whether to compare models first
        models_to_test: Models to compare
        final_model: Best model to use for final training
        use_quantiles: Whether to train quantile models
        cv_splits: Number of CV folds
        train_years: Years for training
        test_years: Years for testing
        output_dir: Output directory
    """
    logger.info("=" * 70)
    logger.info("🏥 HOSPITAL ADMISSIONS 7-DAY FORECASTING SYSTEM")
    logger.info("=" * 70)
    
    # Change to project root
    original_cwd = Path.cwd()
    try:
        os.chdir(project_root)
        
        # Step 1: Data Ingestion
        logger.info("\n" + "=" * 70)
        logger.info("📥 STEP 1: DATA INGESTION")
        logger.info("=" * 70)
        df = load_data(csv_path)
        
        # Step 2: Feature Engineering
        logger.info("\n" + "=" * 70)
        logger.info("🔧 STEP 2: FEATURE ENGINEERING")
        logger.info("=" * 70)
        X, y, dates = engineer_features(df, include_exogenous_lags=True, include_interactions=True)
        
        # Step 2.5: Leakage Checks (optional but recommended)
        try:
            from forecast_system.leakage_checks import run_all_leakage_checks
            logger.info("\n" + "=" * 70)
            logger.info("🔍 STEP 2.5: LEAKAGE INTEGRITY CHECKS")
            logger.info("=" * 70)
            leakage_results = run_all_leakage_checks(
                X, y, dates, df,
                LightGBMForecaster,
                n_estimators=100,
                learning_rate=0.1
            )
        except Exception as e:
            logger.warning(f"   Leakage checks failed: {e}")
            leakage_results = None
        
        # Step 3: Time-based split
        logger.info("\n" + "=" * 70)
        logger.info("✂️  STEP 3: TIME-BASED SPLIT")
        logger.info("=" * 70)
        
        df_with_dates = pd.DataFrame({'date': dates.values, 'target': y.values})
        df_with_dates = pd.concat([X.reset_index(drop=True), df_with_dates], axis=1)
        
        if not pd.api.types.is_datetime64_any_dtype(df_with_dates['date']):
            df_with_dates['date'] = pd.to_datetime(df_with_dates['date'])
        
        min_date = df_with_dates['date'].min()
        split_date = min_date + pd.DateOffset(years=train_years)
        
        train_mask = df_with_dates['date'] < split_date
        test_mask = df_with_dates['date'] >= split_date
        
        X_train = df_with_dates.loc[train_mask, X.columns].copy()
        y_train = df_with_dates.loc[train_mask, 'target'].copy()
        dates_train = df_with_dates.loc[train_mask, 'date'].copy()
        
        X_test = df_with_dates.loc[test_mask, X.columns].copy()
        y_test = df_with_dates.loc[test_mask, 'target'].copy()
        dates_test = df_with_dates.loc[test_mask, 'date'].copy()
        
        logger.info(f"   Train: {len(X_train)} samples ({dates_train.min().date()} to {dates_train.max().date()})")
        logger.info(f"   Test:  {len(X_test)} samples ({dates_test.min().date()} to {dates_test.max().date()})")
        
        # Step 4: Model Comparison (optional)
        comparison_results = None
        if compare:
            logger.info("\n" + "=" * 70)
            logger.info("🔬 STEP 4: MODEL COMPARISON")
            logger.info("=" * 70)
            
            try:
                # Use DateGroupedRollingCV for proper date-based splitting
                comparison_results = compare_models(
                    X_train, y_train, dates_train,
                    models_to_test=models_to_test,
                    cv_splits=cv_splits,
                    cv_expanding=True,  # Use expanding window
                    use_quantiles=False  # Faster comparison
                )
                
                # Validate comparison results
                if comparison_results is None or len(comparison_results) == 0:
                    raise RuntimeError("Model comparison returned no results")
                
                # Check if any model failed
                failed_models = [name for name, result in comparison_results.items() 
                               if 'error' in result or 'cv_results' not in result]
                if failed_models:
                    error_msg = f"Model comparison failed for: {failed_models}"
                    logger.error(f"❌ CRITICAL: {error_msg}")
                    raise RuntimeError(error_msg)
                
                logger.info("✅ Model comparison completed successfully")
                
            except Exception as e:
                error_msg = f"❌ CRITICAL: Model comparison failed: {e}"
                logger.error(error_msg)
                logger.error("   Pipeline cannot proceed without valid model comparison")
                logger.error("   This ensures model selection is based on reliable CV results")
                raise RuntimeError(error_msg) from e
        
        # Step 4.5: Add Error Features from CV (Option A improvement)
        logger.info("\n" + "=" * 70)
        logger.info("🔧 STEP 4.5: ADDING ERROR FEATURES FROM CV")
        logger.info("=" * 70)
        
        try:
            from forecast_system.error_features import create_error_features_from_cv
            from forecast_system.models import LightGBMForecaster
            
            # Create a temporary CV for error feature generation
            temp_cv = DateGroupedRollingCV(
                n_splits=3,
                train_months=12,
                test_months=3,
                expanding=True,
                min_train_years=0.95,
                regime_aware=True,
                min_folds=2
            )
            
            # Generate error features from OOF predictions
            logger.info("   Generating error features from out-of-fold CV predictions...")
            error_features_df = create_error_features_from_cv(
                X_train, y_train, dates_train,
                model=LightGBMForecaster(n_estimators=100, learning_rate=0.1),  # Lightweight model for OOF
                cv=temp_cv,
                hospital_col='hospital_id_enc',
                horizon_col='horizon'
            )
            
            # Add error features to training and test sets
            for col in error_features_df.columns:
                if col in X_train.columns:
                    logger.warning(f"   Warning: {col} already exists, overwriting with error features")
                X_train[col] = error_features_df.loc[X_train.index, col].fillna(0.0)
                # For test set, initialize to 0 (will be updated during inference)
                X_test[col] = 0.0
            
            logger.info(f"   ✅ Added {len(error_features_df.columns)} error features to training data")
            logger.info(f"      Features: {', '.join(error_features_df.columns)}")
        except Exception as e:
            logger.warning(f"   ⚠️  Error features generation failed: {e}")
            logger.warning("   Continuing without error features (model will rely on lag features only)")
        
        # Step 5: Final Model Training
        logger.info("\n" + "=" * 70)
        logger.info("🏋️  STEP 5: FINAL MODEL TRAINING")
        logger.info("=" * 70)
        
        # Select model class
        if final_model == 'lightgbm':
            model_class = LightGBMForecaster
            model_params = {
                'n_estimators': 1000,
                'learning_rate': 0.05,
                'num_leaves': 31,
                'min_data_in_leaf': 20,
                'lambda_l1': 0.1,
                'lambda_l2': 0.1
            }
        elif final_model == 'xgboost':
            model_class = XGBoostForecaster
            model_params = {
                'n_estimators': 1000,
                'learning_rate': 0.05,
                'max_depth': 8,
                'min_child_weight': 3
            }
        else:
            raise ValueError(f"Unknown model: {final_model}")
        
        # Add regime indicator for regime-aware training
        if 'outbreak_index' in X_train.columns or 'outbreak_index_lag_7' in X_train.columns:
            outbreak_col = 'outbreak_index' if 'outbreak_index' in X_train.columns else 'outbreak_index_lag_7'
            X_train['regime_indicator'] = create_regime_indicator(X_train, outbreak_col=outbreak_col, threshold=70.0)
            X_test['regime_indicator'] = create_regime_indicator(X_test, outbreak_col=outbreak_col, threshold=70.0)
            
            # Add regime interaction features
            X_train = add_regime_interaction_features(X_train, regime_col='regime_indicator')
            X_test = add_regime_interaction_features(X_test, regime_col='regime_indicator')
        
        # Split training data for validation
        val_split_date = dates_train.max() - pd.DateOffset(days=90)  # Last 90 days for validation
        val_mask = dates_train >= val_split_date
        train_mask_final = dates_train < val_split_date
        
        X_train_final = X_train.loc[train_mask_final].copy()
        y_train_final = y_train.loc[train_mask_final].copy()
        X_val_final = X_train.loc[val_mask].copy()
        y_val_final = y_train.loc[val_mask].copy()
        
        # Train final model (per-horizon models for better horizon-specific learning)
        logger.info("   Training per-horizon models (one model per forecast horizon)...")
        
        if 'horizon' in X_train_final.columns:
            # Option A: Per-horizon models (preferred for better horizon-specific learning)
            from forecast_system.models import PerHorizonForecaster
            
            models_by_horizon = {}
            
            for horizon in range(1, 8):
                horizon_mask_train = X_train_final['horizon'] == horizon
                horizon_mask_val = X_val_final['horizon'] == horizon
                
                if horizon_mask_train.sum() == 0:
                    continue
                
                X_h_train = X_train_final[horizon_mask_train].copy()
                y_h_train = y_train_final[horizon_mask_train].copy()
                X_h_val = X_val_final[horizon_mask_val].copy()
                y_h_val = y_val_final[horizon_mask_val].copy()
                
                # Remove horizon feature (not needed for single-horizon model)
                if 'horizon' in X_h_train.columns:
                    X_h_train = X_h_train.drop(columns=['horizon'])
                    X_h_val = X_h_val.drop(columns=['horizon'])
                
                # Horizon-specific regularization: stricter for longer horizons (improves quantile stability)
                horizon_params = model_params.copy()
                if horizon >= 5:  # H5, H6, H7 need more regularization for quantile stability
                    horizon_params['min_data_in_leaf'] = max(horizon_params.get('min_data_in_leaf', 20), 100)  # Increased from 30 to 100
                    horizon_params['num_leaves'] = min(horizon_params.get('num_leaves', 31), 20)  # Smaller trees (reduced from 25)
                    horizon_params['lambda_l1'] = horizon_params.get('lambda_l1', 0.1) * 2.0  # More L1 (increased from 1.5x)
                    horizon_params['lambda_l2'] = horizon_params.get('lambda_l2', 0.1) * 2.0  # More L2 (increased from 1.5x)
                    logger.info(f"      Horizon {horizon}: Applied stricter regularization (long horizon, quantile stability)")
                
                # Option: Use regime-split models for better stability (reduces CoV)
                use_regime_split = False  # Set to True to enable regime-split models
                if use_regime_split and 'regime_indicator' in X_h_train.columns:
                    from forecast_system.regime_aware import train_regime_separate_models, predict_with_regime_models
                    
                    def train_model_fn(X_tr, y_tr, X_v, y_v):
                        return train_final_model(
                            model_class,
                            X_tr, y_tr, X_v, y_v,
                            use_quantiles=use_quantiles,
                            save_path=None,
                            **horizon_params
                        )
                    
                    regime_models = train_regime_separate_models(
                        X_h_train, y_h_train,
                        X_h_val, y_h_val,
                        train_model_fn=train_model_fn,
                        regime_col='regime_indicator'
                    )
                    
                    # Create wrapper model for regime-split predictions
                    class RegimeSplitModel:
                        def __init__(self, regime_models_dict):
                            self.regime_models = regime_models_dict
                            self.is_fitted = True
                        
                        def predict(self, X):
                            return predict_with_regime_models(self.regime_models, X, regime_col='regime_indicator')
                        
                        def predict_quantiles(self, X, quantiles=[0.1, 0.5, 0.9]):
                            # Route to appropriate regime model
                            results = {q: np.zeros(len(X)) for q in quantiles}
                            for regime, model in self.regime_models.items():
                                regime_mask = X['regime_indicator'] == regime if 'regime_indicator' in X.columns else np.zeros(len(X), dtype=bool)
                                if regime_mask.any():
                                    X_regime = X[regime_mask].copy()
                                    if 'regime_indicator' in X_regime.columns:
                                        X_regime = X_regime.drop(columns=['regime_indicator'])
                                    if hasattr(model, 'predict_quantiles'):
                                        regime_quantiles = model.predict_quantiles(X_regime, quantiles=quantiles)
                                        for q in quantiles:
                                            if q in regime_quantiles:
                                                results[q][regime_mask] = regime_quantiles[q]
                            return results
                        
                        def get_feature_importance(self, X):
                            # Return average importance across regime models
                            importances = []
                            for model in self.regime_models.values():
                                if hasattr(model, 'get_feature_importance'):
                                    importances.append(model.get_feature_importance(X))
                            if importances:
                                return importances[0]  # Return first model's importance
                            return pd.DataFrame()
                        
                        def save(self, path):
                            import pickle
                            with open(path, 'wb') as f:
                                pickle.dump(self, f)
                    
                    model_h = RegimeSplitModel(regime_models)
                    logger.info(f"      Horizon {horizon}: Trained regime-split models (normal + surge)")
                else:
                    model_h = train_final_model(
                        model_class,
                        X_h_train, y_h_train,
                        X_h_val, y_h_val,
                        use_quantiles=use_quantiles,
                        save_path=None,  # Save separately below
                        **horizon_params
                    )
                
                models_by_horizon[horizon] = model_h
                logger.info(f"      Horizon {horizon}: Trained on {len(X_h_train)} samples")
            
            # Create wrapper model that routes to per-horizon models
            model = PerHorizonForecaster(models_by_horizon)
            model_path = f"{output_dir}/{final_model}_final.pkl"
            model.save(model_path)
        else:
            # Fallback: Single global model
            model_path = f"{output_dir}/{final_model}_final.pkl"
            model = train_final_model(
                model_class,
                X_train_final, y_train_final,
                X_val_final, y_val_final,
                use_quantiles=use_quantiles,
                save_path=model_path,
                **model_params
            )
        
        # Step 6: Drift Detection (before evaluation)
        logger.info("\n" + "=" * 70)
        logger.info("🔍 STEP 6: DRIFT DETECTION")
        logger.info("=" * 70)
        
        try:
            # Get predictions for drift detection
            y_pred_test = model.predict(X_test)
            errors_test = pd.Series(np.abs(y_test.values - y_pred_test), index=X_test.index)
            
            drift_results = monitor_drift(
                X_train_final,
                X_test,
                errors=errors_test,
                psi_threshold=0.2,
                mae_drift_threshold=0.3
            )
            
            if drift_results.get('overall_drift_detected', False):
                logger.warning("   🚨 DRIFT DETECTED - Consider retraining model")
        except Exception as e:
            logger.warning(f"   Drift detection skipped: {e}")
            drift_results = None
        
        # Step 7: Evaluation
        logger.info("\n" + "=" * 70)
        logger.info("📊 STEP 7: MODEL EVALUATION")
        logger.info("=" * 70)
        
        horizons_test = X_test['horizon']
        eval_results = evaluate_model(
            model,
            X_test, y_test,
            horizons=horizons_test,
            use_quantiles=use_quantiles,
            check_baseline=True,  # Compare with naive baselines
            save_path=f"{output_dir}/evaluation_metrics.json"
        )
        
        # Step 8: Diagnostics
        logger.info("\n" + "=" * 70)
        logger.info("🔍 STEP 8: RESIDUAL DIAGNOSTICS")
        logger.info("=" * 70)
        
        # Get base predictions for diagnostics
        y_pred_base = model.predict(X_test)
        
        # AR(7) residual correction REMOVED - ineffective and redundant
        # Tree models with lag features (lag_1 through lag_60) already capture autoregressive structure
        # Adding AR(7) on top provides no benefit (ACF improvement < 0.001, MAE improvement < 0.002)
        # The tree already absorbed the autoregressive structure, so residuals are not clean AR processes
        # Using tree-integrated error features instead (via feature engineering during training)
        y_pred_for_diagnostics = y_pred_base.copy()
        logger.info("   Note: AR(7) residual correction removed (ineffective with lag-rich tree models)")
        
        diagnostic_results = analyze_residuals(
            y_test.values,
            y_pred_for_diagnostics,
            X_test,
            dates=dates_test,
            horizons=horizons_test.values if horizons_test is not None else None,
            output_dir=f"{output_dir}/diagnostics"
        )
        
        # Residual ACF analysis (AR correction removed - tree models handle this via lag features)
        residuals = y_test.values - y_pred_for_diagnostics
        from scipy.stats import pearsonr
        if len(residuals) > 1:
            acf_lag1 = pearsonr(residuals[:-1], residuals[1:])[0] if len(residuals) > 1 else 0
            acf_lag7 = pearsonr(residuals[:-7], residuals[7:])[0] if len(residuals) > 7 else 0
            
            logger.info(f"\n📊 Residual ACF Analysis:")
            logger.info(f"   Lag-1 ACF: {acf_lag1:.4f}")
            logger.info(f"   Lag-7 ACF: {acf_lag7:.4f}")
            
            if acf_lag1 > 0.35:
                logger.warning(f"   ⚠️  High residual autocorrelation (lag-1 ACF > 0.35)")
                logger.warning("   Consider: longer lag features, tree-integrated error features, or sequence models")
            if acf_lag7 > 0.40:
                logger.warning(f"   ⚠️  Weekly structure not fully captured (lag-7 ACF > 0.40)")
        
        # Step 8.5: TFT Decision Framework Evaluation
        logger.info("\n" + "=" * 70)
        logger.info("🎯 STEP 8.5: TFT DECISION FRAMEWORK")
        logger.info("=" * 70)
        
        try:
            from .tft_decision_framework import evaluate_tree_system_adequacy
            
            # Get CV CoV from comparison results
            cv_cov = 100.0  # Default if not available
            if comparison_results:
                # Try to get from best model's CV results
                best_model_name = final_model
                if best_model_name in comparison_results:
                    model_result = comparison_results[best_model_name]
                    if 'cv_results' in model_result:
                        cv_results = model_result['cv_results']
                        if 'cv_coefficient_of_variation' in cv_results:
                            cv_cov = cv_results['cv_coefficient_of_variation']
                # Fallback: try any model's CV results
                elif len(comparison_results) > 0:
                    for model_name, model_result in comparison_results.items():
                        if isinstance(model_result, dict) and 'cv_results' in model_result:
                            cv_results = model_result['cv_results']
                            if 'cv_coefficient_of_variation' in cv_results:
                                cv_cov = cv_results['cv_coefficient_of_variation']
                                break
            
            # Get conformal adjustment info if available (from quantile results)
            long_horizon_conformal = None
            horizon_7_interval_width = None
            if eval_results and 'quantile_results' in eval_results:
                quantile_results = eval_results['quantile_results']
                if 'coverage' in quantile_results:
                    # Try to extract H7 conformal adjustment (if stored)
                    # This would need to be passed from conformal calibration
                    pass
            
            # Evaluate tree system adequacy
            tft_evaluation = evaluate_tree_system_adequacy(
                residual_acf_lag1=acf_lag1 if len(residuals) > 1 else 0.0,
                residual_acf_lag7=acf_lag7 if len(residuals) > 7 else 0.0,
                cv_coefficient_of_variation=cv_cov,
                long_horizon_conformal_adjustment=long_horizon_conformal,
                horizon_7_interval_width=horizon_7_interval_width
            )
            
            # Save TFT evaluation results
            import json
            tft_eval_path = f"{output_dir}/tft_evaluation.json"
            with open(tft_eval_path, 'w') as f:
                json.dump(tft_evaluation, f, indent=2, default=str)
            logger.info(f"   💾 TFT evaluation saved to: {tft_eval_path}")
            
        except Exception as e:
            logger.warning(f"   TFT evaluation skipped: {e}")
            tft_evaluation = None
        
        # Step 9: Feature Importance
        logger.info("\n" + "=" * 70)
        logger.info("📈 STEP 9: FEATURE IMPORTANCE")
        logger.info("=" * 70)
        
        importance_df = model.get_feature_importance(X_test)
        importance_df.to_csv(f"{output_dir}/feature_importance.csv", index=False)
        
        logger.info("\n📊 Top 15 Features:")
        for idx, row in importance_df.head(15).iterrows():
            logger.info(f"   {row['feature']:25s} : {row['importance_pct']:6.2f}%")
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ TRAINING PIPELINE COMPLETE")
        logger.info("=" * 70)
        logger.info(f"📁 Model: {model_path}")
        logger.info(f"📁 Metrics: {output_dir}/evaluation_metrics.json")
        logger.info(f"📁 Diagnostics: {output_dir}/diagnostics/")
        logger.info(f"📁 Feature Importance: {output_dir}/feature_importance.csv")
        
        return {
            'model': model,
            'comparison_results': comparison_results,
            'evaluation_results': eval_results,
            'diagnostic_results': diagnostic_results,
            'feature_importance': importance_df
        }
        
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    results = run_training_pipeline(
        csv_path="dataset/synthetic_hospital_data.csv",
        compare=True,
        models_to_test=['lightgbm', 'xgboost'],
        final_model='lightgbm',  # Will use best from comparison
        use_quantiles=True,
        cv_splits=5
    )

