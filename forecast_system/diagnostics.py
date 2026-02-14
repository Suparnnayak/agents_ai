"""
Residual Diagnostics Module

Comprehensive residual analysis and model diagnostics.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from typing import Optional, Dict
from pathlib import Path
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from .utils import get_logger

logger = get_logger(__name__)

# Set style
try:
    plt.style.use('seaborn-v0_8-darkgrid')
except OSError:
    try:
        plt.style.use('seaborn-darkgrid')
    except OSError:
        plt.style.use('ggplot')


def analyze_residuals(y_true: np.ndarray,
                     y_pred: np.ndarray,
                     X_test: pd.DataFrame,
                     dates: Optional[pd.Series] = None,
                     horizons: Optional[np.ndarray] = None,
                     output_dir: str = "models/diagnostics") -> Dict:
    """
    Comprehensive residual analysis.
    
    Returns:
        Dictionary with diagnostic results
    """
    logger.info("=" * 60)
    logger.info("🔍 RESIDUAL DIAGNOSTICS")
    logger.info("=" * 60)
    
    residuals = y_true - y_pred
    abs_residuals = np.abs(residuals)
    
    # Basic statistics
    logger.info(f"\n📊 Residual Statistics:")
    logger.info(f"   Mean: {np.mean(residuals):.2f}")
    logger.info(f"   Std: {np.std(residuals):.2f}")
    logger.info(f"   Min: {np.min(residuals):.2f}")
    logger.info(f"   Max: {np.max(residuals):.2f}")
    logger.info(f"   MAE: {np.mean(abs_residuals):.2f}")
    
    # Normality test
    logger.info(f"\n🔬 Normality Tests:")
    sample_size = min(5000, len(residuals))
    shapiro_stat, shapiro_p = stats.shapiro(residuals[:sample_size])
    logger.info(f"   Shapiro-Wilk (n={sample_size}):")
    logger.info(f"      Statistic: {shapiro_stat:.4f}, p-value: {shapiro_p:.6f}")
    if shapiro_p > 0.05:
        logger.info("      ✅ Residuals appear normally distributed")
    else:
        logger.info("      ⚠️  Residuals may not be normally distributed")
    
    # Error vs admission volume
    admissions = y_true
    correlation = np.corrcoef(admissions, abs_residuals)[0, 1]
    logger.info(f"\n📈 Error vs Capacity:")
    logger.info(f"   Correlation (admissions vs |error|): {correlation:.4f}")
    if correlation > 0.3:
        logger.info("      ⚠️  Error grows significantly with volume (important for surge planning)")
    elif correlation > 0.1:
        logger.info("      ✅ Moderate correlation (some error growth)")
    else:
        logger.info("      ✅ Low correlation (stable errors)")
    
    # Outbreak analysis
    outbreak_analysis = {}
    if 'outbreak_index' in X_test.columns:
        outbreak_threshold = np.percentile(X_test['outbreak_index'], 75)
        high_outbreak_mask = X_test['outbreak_index'] > outbreak_threshold
        
        outbreak_errors = abs_residuals[high_outbreak_mask]
        normal_errors = abs_residuals[~high_outbreak_mask]
        
        logger.info(f"\n🔺 Outbreak Analysis:")
        logger.info(f"   High outbreak periods: {high_outbreak_mask.sum()} samples")
        logger.info(f"   Normal periods: {(~high_outbreak_mask).sum()} samples")
        logger.info(f"   Mean |error| during outbreaks: {np.mean(outbreak_errors):.2f}")
        logger.info(f"   Mean |error| during normal: {np.mean(normal_errors):.2f}")
        
        outbreak_analysis = {
            'outbreak_mae': float(np.mean(outbreak_errors)),
            'normal_mae': float(np.mean(normal_errors)),
            'ratio': float(np.mean(outbreak_errors) / np.mean(normal_errors)) if np.mean(normal_errors) > 0 else None
        }
    
    # Horizon-wise degradation analysis
    horizon_degradation = {}
    if horizons is not None:
        horizon_degradation = analyze_horizon_degradation(y_true, y_pred, horizons)
        logger.info(f"\n📊 Horizon Degradation:")
        for h, metrics in sorted(horizon_degradation.items()):
            logger.info(f"   Horizon {h}: MAE={metrics['mae']:.2f}, RMSE={metrics['rmse']:.2f}")
    
    # Error vs utilization analysis
    utilization_analysis = {}
    if 'hospital_capacity' in X_test.columns:
        utilization_analysis = analyze_error_vs_utilization(y_true, y_pred, X_test)
        logger.info(f"\n📊 Error vs Utilization:")
        logger.info(f"   Low utilization (<50%): MAE={utilization_analysis.get('low_mae', 0):.2f}")
        logger.info(f"   Medium utilization (50-90%): MAE={utilization_analysis.get('medium_mae', 0):.2f}")
        logger.info(f"   High utilization (>90%): MAE={utilization_analysis.get('high_mae', 0):.2f}")
    
    # Residual autocorrelation (ACF)
    autocorr_analysis = analyze_residual_autocorrelation(residuals, max_lag=7)
    logger.info(f"\n📊 Residual Autocorrelation (ACF):")
    
    lag1_autocorr = autocorr_analysis.get('lag1_autocorr', 0)
    logger.info(f"   Lag 1 autocorrelation: {lag1_autocorr:.4f}")
    
    if lag1_autocorr > 0.3:
        logger.warning(f"   ⚠️  HIGH AUTOCORRELATION: Lag-1 ACF ({lag1_autocorr:.4f}) > 0.3")
        logger.warning("   Model is missing temporal patterns - recursive features added to help")
        logger.warning("   Note: Tree models inherently struggle with residual temporal dependencies")
        logger.warning("   Consider: ensemble with ARIMA residuals or use TFT for temporal modeling")
    elif lag1_autocorr > 0.1:
        logger.info("   ⚠️  Moderate autocorrelation detected (model may be missing some temporal patterns)")
        logger.info("   Recursive features (change_from_week_ago, acceleration) help reduce this")
    else:
        logger.info("   ✅ Low autocorrelation (good temporal modeling)")
    
    # Show ACF for multiple lags
    for lag in range(1, min(8, len(autocorr_analysis) // 2 + 1)):
        acf_key = f'lag{lag}_autocorr'
        if acf_key in autocorr_analysis:
            logger.info(f"   Lag {lag} ACF: {autocorr_analysis[acf_key]:.4f}")
    
    # Create visualizations
    os.makedirs(output_dir, exist_ok=True)
    create_diagnostic_plots(residuals, abs_residuals, y_true, y_pred, 
                           X_test, dates, horizons, output_dir)
    
    return {
        'residual_stats': {
            'mean': float(np.mean(residuals)),
            'std': float(np.std(residuals)),
            'mae': float(np.mean(abs_residuals))
        },
        'normality': {
            'shapiro_stat': float(shapiro_stat),
            'shapiro_p': float(shapiro_p),
            'is_normal': shapiro_p > 0.05
        },
        'error_capacity_correlation': float(correlation),
        'outbreak_analysis': outbreak_analysis,
        'horizon_degradation': horizon_degradation,
        'utilization_analysis': utilization_analysis,
        'autocorrelation': autocorr_analysis
    }


def analyze_horizon_degradation(y_true: np.ndarray,
                                y_pred: np.ndarray,
                                horizons: np.ndarray) -> Dict[int, Dict]:
    """Analyze how error increases with forecast horizon."""
    degradation = {}
    
    for h in range(1, 8):
        mask = horizons == h
        if mask.sum() == 0:
            continue
        
        y_true_h = y_true[mask]
        y_pred_h = y_pred[mask]
        
        mae = np.mean(np.abs(y_true_h - y_pred_h))
        rmse = np.sqrt(np.mean((y_true_h - y_pred_h) ** 2))
        
        degradation[int(h)] = {
            'mae': float(mae),
            'rmse': float(rmse),
            'n_samples': int(mask.sum())
        }
    
    return degradation


def analyze_error_vs_utilization(y_true: np.ndarray,
                                 y_pred: np.ndarray,
                                 X_test: pd.DataFrame) -> Dict:
    """Analyze error patterns across utilization levels."""
    if 'hospital_capacity' not in X_test.columns:
        return {}
    
    capacity = X_test['hospital_capacity'].values
    capacity = np.where(capacity == 0, 1, capacity)
    utilization = y_true / capacity
    
    errors = np.abs(y_true - y_pred)
    
    low_mask = utilization < 0.5
    medium_mask = (utilization >= 0.5) & (utilization < 0.9)
    high_mask = utilization >= 0.9
    
    return {
        'low_mae': float(np.mean(errors[low_mask])) if low_mask.sum() > 0 else 0.0,
        'medium_mae': float(np.mean(errors[medium_mask])) if medium_mask.sum() > 0 else 0.0,
        'high_mae': float(np.mean(errors[high_mask])) if high_mask.sum() > 0 else 0.0,
        'low_samples': int(low_mask.sum()),
        'medium_samples': int(medium_mask.sum()),
        'high_samples': int(high_mask.sum())
    }


def analyze_residual_autocorrelation(residuals: np.ndarray, max_lag: int = 5) -> Dict:
    """Analyze residual autocorrelation to detect missing temporal patterns."""
    from scipy.stats import pearsonr
    
    autocorrs = {}
    
    for lag in range(1, min(max_lag + 1, len(residuals) // 10)):
        if lag >= len(residuals):
            break
        
        lagged = residuals[:-lag]
        current = residuals[lag:]
        
        if len(lagged) > 10:
            corr, p_value = pearsonr(lagged, current)
            autocorrs[f'lag{lag}_autocorr'] = float(corr)
            autocorrs[f'lag{lag}_pvalue'] = float(p_value)
    
    return autocorrs


def create_diagnostic_plots(residuals: np.ndarray,
                           abs_residuals: np.ndarray,
                           y_true: np.ndarray,
                           y_pred: np.ndarray,
                           X_test: pd.DataFrame,
                           dates: Optional[pd.Series],
                           horizons: Optional[np.ndarray],
                           output_dir: str):
    """Create diagnostic visualization plots."""
    logger.info(f"\n📊 Creating diagnostic plots...")
    
    # Main diagnostic plots (2x2)
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    
    # 1. Residual distribution
    axes[0, 0].hist(residuals, bins=50, edgecolor='black', alpha=0.7)
    axes[0, 0].axvline(0, color='red', linestyle='--', linewidth=2)
    axes[0, 0].set_xlabel('Residual (Actual - Predicted)')
    axes[0, 0].set_ylabel('Frequency')
    axes[0, 0].set_title('Residual Distribution')
    axes[0, 0].grid(True, alpha=0.3)
    
    # 2. Q-Q plot
    sample_size = min(5000, len(residuals))
    stats.probplot(residuals[:sample_size], dist="norm", plot=axes[0, 1])
    axes[0, 1].set_title('Q-Q Plot (Normality Check)')
    axes[0, 1].grid(True, alpha=0.3)
    
    # 3. Error vs Capacity
    sample_idx = np.random.choice(len(abs_residuals), min(5000, len(abs_residuals)), replace=False)
    axes[1, 0].scatter(y_true[sample_idx], abs_residuals[sample_idx], alpha=0.4, s=20)
    axes[1, 0].set_xlabel('Actual Admissions')
    axes[1, 0].set_ylabel('Absolute Error')
    axes[1, 0].set_title('Error vs Admission Volume')
    axes[1, 0].grid(True, alpha=0.3)
    
    # 4. Residuals over time or Predicted vs Actual
    if dates is not None:
        sample_idx = np.random.choice(len(residuals), min(5000, len(residuals)), replace=False)
        axes[1, 1].scatter(dates.iloc[sample_idx], residuals[sample_idx], alpha=0.3, s=10)
        axes[1, 1].axhline(0, color='red', linestyle='--', linewidth=2)
        axes[1, 1].set_xlabel('Date')
        axes[1, 1].set_ylabel('Residual')
        axes[1, 1].set_title('Residuals Over Time')
        axes[1, 1].tick_params(axis='x', rotation=45)
        axes[1, 1].grid(True, alpha=0.3)
    else:
        sample_idx = np.random.choice(len(y_pred), min(5000, len(y_pred)), replace=False)
        axes[1, 1].scatter(y_true[sample_idx], y_pred[sample_idx], alpha=0.4, s=20)
        axes[1, 1].plot([y_true.min(), y_true.max()], [y_true.min(), y_true.max()], 'r--', linewidth=2)
        axes[1, 1].set_xlabel('Actual')
        axes[1, 1].set_ylabel('Predicted')
        axes[1, 1].set_title('Predicted vs Actual')
        axes[1, 1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/residual_diagnostics.png", dpi=300, bbox_inches='tight')
    plt.close()
    
    logger.info(f"   ✅ Saved: {output_dir}/residual_diagnostics.png")
    
    # Horizon degradation plot
    if horizons is not None:
        horizon_degradation = analyze_horizon_degradation(y_true, y_pred, horizons)
        if horizon_degradation:
            fig, ax = plt.subplots(1, 1, figsize=(10, 6))
            horizons_sorted = sorted(horizon_degradation.keys())
            mae_values = [horizon_degradation[h]['mae'] for h in horizons_sorted]
            rmse_values = [horizon_degradation[h]['rmse'] for h in horizons_sorted]
            
            ax.plot(horizons_sorted, mae_values, marker='o', label='MAE', linewidth=2)
            ax.plot(horizons_sorted, rmse_values, marker='s', label='RMSE', linewidth=2)
            ax.set_xlabel('Forecast Horizon (days)')
            ax.set_ylabel('Error')
            ax.set_title('Error Degradation by Horizon')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            plt.tight_layout()
            plt.savefig(f"{output_dir}/horizon_degradation.png", dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"   ✅ Saved: {output_dir}/horizon_degradation.png")
    
    # Error vs Utilization plot
    if 'hospital_capacity' in X_test.columns:
        capacity = X_test['hospital_capacity'].values
        capacity = np.where(capacity == 0, 1, capacity)
        utilization = y_true / capacity
        
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        sample_idx = np.random.choice(len(abs_residuals), min(5000, len(abs_residuals)), replace=False)
        ax.scatter(utilization[sample_idx], abs_residuals[sample_idx], alpha=0.4, s=20)
        ax.axvline(0.9, color='red', linestyle='--', linewidth=2, label='Surge Threshold (90%)')
        ax.set_xlabel('Utilization (Admissions / Capacity)')
        ax.set_ylabel('Absolute Error')
        ax.set_title('Error vs Utilization')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(f"{output_dir}/error_vs_utilization.png", dpi=300, bbox_inches='tight')
        plt.close()
        
        logger.info(f"   ✅ Saved: {output_dir}/error_vs_utilization.png")

