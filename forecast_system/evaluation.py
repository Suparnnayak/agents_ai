"""
Model Evaluation Module

Comprehensive evaluation with metrics per horizon and quantile coverage.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
from pathlib import Path
import json

from forecast_system.utils import get_logger

logger = get_logger(__name__)


def calculate_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculate regression metrics."""
    mae = np.mean(np.abs(y_true - y_pred))
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    
    # MAPE (avoid division by zero)
    mask = y_true != 0
    if mask.sum() > 0:
        mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
    else:
        mape = np.nan
    
    # R2
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    
    return {
        'MAE': float(mae),
        'RMSE': float(rmse),
        'MAPE': float(mape) if not np.isnan(mape) else None,
        'R2': float(r2)
    }


def calculate_baseline_metrics(y_true: np.ndarray, 
                               X_test: pd.DataFrame,
                               naive_method: str = 'lag_1') -> Dict[str, float]:
    """
    Calculate baseline metrics using naive methods.
    
    Args:
        y_true: True values
        X_test: Test features (must contain lag columns)
        naive_method: 'lag_1' (naive) or 'lag_7' (seasonal naive)
        
    Returns:
        Dictionary with baseline metrics
    """
    if naive_method == 'lag_1' and 'lag_1' in X_test.columns:
        y_pred_baseline = X_test['lag_1'].values
    elif naive_method == 'lag_7' and 'lag_7' in X_test.columns:
        y_pred_baseline = X_test['lag_7'].values
    else:
        # Fallback: use mean
        y_pred_baseline = np.full(len(y_true), np.mean(y_true))
    
    return calculate_metrics(y_true, y_pred_baseline)


def evaluate_per_horizon(y_true: np.ndarray,
                         y_pred: np.ndarray,
                         horizons: np.ndarray) -> pd.DataFrame:
    """Evaluate metrics per horizon."""
    results = []
    
    for horizon in range(1, 8):
        mask = horizons == horizon
        
        if mask.sum() == 0:
            continue
        
        y_true_h = y_true[mask]
        y_pred_h = y_pred[mask]
        
        metrics = calculate_metrics(y_true_h, y_pred_h)
        metrics['horizon'] = horizon
        metrics['n_samples'] = int(mask.sum())
        
        results.append(metrics)
    
    return pd.DataFrame(results)


def calculate_pinball_loss(y_true: np.ndarray,
                           quantile_preds: Dict[float, np.ndarray]) -> Dict[str, float]:
    """
    Calculate pinball loss for quantile predictions.
    
    Pinball loss = max(alpha * (y - q), (1 - alpha) * (q - y))
    where alpha is the quantile level and q is the quantile prediction.
    
    Args:
        y_true: True values
        quantile_preds: Dictionary mapping quantile -> predictions
        
    Returns:
        Dictionary mapping quantile -> pinball loss
    """
    pinball_losses = {}
    
    for quantile, preds in quantile_preds.items():
        errors = y_true - preds
        loss = np.maximum(quantile * errors, (quantile - 1) * errors)
        pinball_losses[f'pinball_q{int(quantile*100)}'] = float(np.mean(loss))
    
    return pinball_losses


def evaluate_quantile_coverage(y_true: np.ndarray,
                              quantile_preds: Dict[float, np.ndarray]) -> Dict[str, float]:
    """Evaluate quantile prediction coverage."""
    coverage_results = {}
    
    # Check coverage for different intervals
    if 0.1 in quantile_preds and 0.9 in quantile_preds:
        lower = quantile_preds[0.1]
        upper = quantile_preds[0.9]
        coverage_80 = np.mean((y_true >= lower) & (y_true <= upper))
        coverage_results['coverage_80'] = float(coverage_80)
        coverage_results['expected_coverage_80'] = 0.8
    
    if 0.05 in quantile_preds and 0.95 in quantile_preds:
        lower = quantile_preds[0.05]
        upper = quantile_preds[0.95]
        coverage_90 = np.mean((y_true >= lower) & (y_true <= upper))
        coverage_results['coverage_90'] = float(coverage_90)
        coverage_results['expected_coverage_90'] = 0.9
    
    # Calculate interval width (normalized by median)
    if 0.1 in quantile_preds and 0.9 in quantile_preds:
        interval_width = quantile_preds[0.9] - quantile_preds[0.1]
        median_width = np.median(interval_width)
        mean_width = np.mean(interval_width)
        coverage_results['interval_width_median'] = float(median_width)
        coverage_results['interval_width_mean'] = float(mean_width)
        # Normalized width (relative to median target)
        if np.median(y_true) > 0:
            normalized_width = median_width / np.median(y_true)
            coverage_results['interval_width_normalized'] = float(normalized_width)
    
    return coverage_results


def evaluate_model(model,
                   X_test: pd.DataFrame,
                   y_test: pd.Series,
                   horizons: Optional[pd.Series] = None,
                   use_quantiles: bool = False,
                   quantiles: list = [0.1, 0.5, 0.9],
                   save_path: Optional[str] = None,
                   check_baseline: bool = True) -> Dict:
    """
    Comprehensive model evaluation.
    
    Returns:
        Dictionary with all evaluation metrics
    """
    logger.info("=" * 60)
    logger.info("📊 MODEL EVALUATION")
    logger.info("=" * 60)
    
    # Point predictions
    y_pred = model.predict(X_test)
    y_true = y_test.values
    
    # Overall metrics
    overall_metrics = calculate_metrics(y_true, y_pred)
    
    logger.info("\n📈 Overall Metrics:")
    logger.info(f"   MAE:  {overall_metrics['MAE']:.2f}")
    logger.info(f"   RMSE: {overall_metrics['RMSE']:.2f}")
    logger.info(f"   MAPE: {overall_metrics['MAPE']:.2f}%" if overall_metrics['MAPE'] else "   MAPE: N/A")
    logger.info(f"   R2:   {overall_metrics['R2']:.4f}")
    
    # Baseline comparison
    baseline_results = {}
    if check_baseline:
        logger.info("\n📊 Baseline Comparison:")
        
        # Naive baseline (lag_1)
        naive_baseline = calculate_baseline_metrics(y_true, X_test, naive_method='lag_1')
        baseline_results['naive_lag1'] = naive_baseline
        
        naive_mae = naive_baseline['MAE']
        model_mae = overall_metrics['MAE']
        improvement_pct = ((naive_mae - model_mae) / naive_mae) * 100 if naive_mae > 0 else 0
        
        logger.info(f"   Naive (lag_1) MAE: {naive_mae:.2f}")
        logger.info(f"   Model MAE: {model_mae:.2f}")
        logger.info(f"   Improvement: {improvement_pct:.1f}%")
        
        if improvement_pct < 20:
            logger.warning(f"   ⚠️  WARNING: Model improvement ({improvement_pct:.1f}%) < 20%")
            logger.warning("   This may indicate model is not learning effectively")
        
        # Seasonal naive baseline (lag_7)
        if 'lag_7' in X_test.columns:
            seasonal_baseline = calculate_baseline_metrics(y_true, X_test, naive_method='lag_7')
            baseline_results['seasonal_lag7'] = seasonal_baseline
            
            seasonal_mae = seasonal_baseline['MAE']
            seasonal_improvement = ((seasonal_mae - model_mae) / seasonal_mae) * 100 if seasonal_mae > 0 else 0
            logger.info(f"   Seasonal Naive (lag_7) MAE: {seasonal_mae:.2f}")
            logger.info(f"   Improvement vs Seasonal: {seasonal_improvement:.1f}%")
    
    # Per-horizon metrics
    per_horizon_df = None
    if horizons is not None:
        per_horizon_df = evaluate_per_horizon(y_true, y_pred, horizons.values)
        
        logger.info("\n📊 Per-Horizon Metrics:")
        logger.info("   Horizon |   MAE   |   RMSE  |  MAPE   |   R2    | Samples")
        logger.info("   " + "-" * 60)
        for _, row in per_horizon_df.iterrows():
            mape_str = f"{row['MAPE']:.2f}%" if row['MAPE'] is not None else "N/A"
            logger.info(f"   {int(row['horizon']):7d} | {row['MAE']:7.2f} | {row['RMSE']:7.2f} | {mape_str:7s} | {row['R2']:7.4f} | {int(row['n_samples']):7d}")
    
    # Quantile evaluation
    quantile_results = {}
    if use_quantiles:
        try:
            quantile_preds = model.predict_quantiles(X_test, quantiles=quantiles)
            coverage = evaluate_quantile_coverage(y_true, quantile_preds)
            pinball_losses = calculate_pinball_loss(y_true, quantile_preds)
            
            quantile_results = {
                'quantile_predictions': {str(k): v.tolist() for k, v in quantile_preds.items()},
                'coverage': coverage,
                'pinball_loss': pinball_losses
            }
            
            logger.info("\n📊 Quantile Coverage:")
            coverage_80 = coverage.get('coverage_80', 0)
            for key, val in coverage.items():
                if 'coverage' in key and not 'expected' in key:
                    logger.info(f"   {key}: {val:.2%}")
            
            # Coverage calibration feedback (coverage_80 is decimal 0-1, convert to percentage for comparison)
            coverage_80_pct = coverage_80 * 100
            if coverage_80 < 0.75:
                logger.warning(f"   ⚠️  Coverage too low ({coverage_80_pct:.1f}% < 75%) - intervals too narrow")
                logger.warning("   Quantile calibration applied to widen intervals")
            elif coverage_80 < 0.78:
                logger.info(f"   ⚠️  Coverage slightly low ({coverage_80_pct:.1f}% < 78%) - consider widening intervals")
            elif coverage_80 > 0.85:
                logger.info(f"   ⚠️  Coverage high ({coverage_80_pct:.1f}% > 85%) - intervals may be too wide")
            else:
                logger.info(f"   ✅ Coverage good ({coverage_80_pct:.1f}% within 75-85% range)")
            
            logger.info("\n📊 Pinball Loss:")
            for key, val in pinball_losses.items():
                logger.info(f"   {key}: {val:.4f}")
            
            if 'interval_width_normalized' in coverage:
                logger.info(f"\n📊 Interval Width (normalized): {coverage['interval_width_normalized']:.4f}")
        except Exception as e:
            logger.warning(f"⚠️  Quantile evaluation failed: {e}")
    
    # Compile results
    results = {
        'overall': overall_metrics,
        'per_horizon': per_horizon_df.to_dict('records') if per_horizon_df is not None else None,
        'quantile_results': quantile_results,
        'baseline_comparison': baseline_results
    }
    
    # Save if path provided
    if save_path:
        save_path = Path(save_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to JSON-serializable
        json_results = {
            'overall': overall_metrics,
            'per_horizon': [
                {
                    'horizon': int(row['horizon']),
                    'MAE': float(row['MAE']),
                    'RMSE': float(row['RMSE']),
                    'MAPE': float(row['MAPE']) if row['MAPE'] is not None else None,
                    'R2': float(row['R2']),
                    'n_samples': int(row['n_samples'])
                }
                for _, row in per_horizon_df.iterrows()
            ] if per_horizon_df is not None else None,
            'quantile_results': quantile_results
        }
        
        with open(save_path, 'w') as f:
            json.dump(json_results, f, indent=2)
        
        logger.info(f"\n💾 Metrics saved to {save_path}")
    
    logger.info("=" * 60)
    logger.info("✅ EVALUATION COMPLETE")
    logger.info("=" * 60)
    
    return results

