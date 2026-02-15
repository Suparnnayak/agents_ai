"""
Production Safety Checks

Validates model before export to ensure production readiness.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional
from pathlib import Path
import json
from forecast_system.utils import get_logger

logger = get_logger(__name__)


def validate_production_readiness(
    cv_results: Dict,
    quantile_coverage: Optional[float] = None,
    target_coverage: float = 0.80,
    residual_acf_lag1: Optional[float] = None,
    max_residual_acf: float = 0.35,
    drift_results: Optional[Dict] = None,
    horizon_degradation_ratio: Optional[float] = None,
    degradation_threshold: float = 3.0
) -> Dict:
    """
    Validate model meets production safety requirements before export.
    
    Critical conditions (must pass):
    - At least 3 CV folds passed
    - CoV < 30%
    - Quantile monotonicity satisfied (checked separately)
    - Coverage within ±5% of target
    
    Warning conditions (log but don't fail):
    - Residual lag-1 ACF < 0.35 (warn only)
    - No severe drift detected
    
    Args:
        cv_results: CV results dictionary
        quantile_coverage: Actual quantile coverage (80% interval)
        target_coverage: Target coverage (default 0.80)
        residual_acf_lag1: Lag-1 residual ACF
        max_residual_acf: Maximum allowed ACF (default 0.35)
        drift_results: Drift detection results
        horizon_degradation_ratio: H7/H1 MAE ratio
        degradation_threshold: Maximum allowed degradation ratio
        
    Returns:
        Dictionary with validation results and pass/fail status
    """
    logger.info("=" * 70)
    logger.info("PRODUCTION SAFETY VALIDATION")
    logger.info("=" * 70)
    
    validation_results = {
        'passed': True,
        'critical_failures': [],
        'warnings': [],
        'checks': {}
    }
    
    # Check 1: At least 3 CV folds passed
    n_folds = cv_results.get('n_folds', 0)
    if n_folds < 3:
        validation_results['passed'] = False
        validation_results['critical_failures'].append(f"Insufficient CV folds: {n_folds} < 3")
        logger.error(f"   ❌ CRITICAL: Only {n_folds} CV folds passed (minimum 3 required)")
    else:
        validation_results['checks']['cv_folds'] = {'passed': True, 'value': n_folds}
        logger.info(f"   ✅ CV folds: {n_folds} >= 3")
    
    # Check 2: CoV < 30%
    cv_cov = cv_results.get('cv_coefficient_of_variation', 100)
    if cv_cov >= 30:
        validation_results['passed'] = False
        validation_results['critical_failures'].append(f"CV CoV too high: {cv_cov:.1f}% >= 30%")
        logger.error(f"   ❌ CRITICAL: CV CoV ({cv_cov:.1f}%) >= 30%")
    else:
        validation_results['checks']['cv_cov'] = {'passed': True, 'value': cv_cov}
        logger.info(f"   ✅ CV CoV: {cv_cov:.1f}% < 30%")
    
    # Check 3: Quantile coverage within ±5% of target
    if quantile_coverage is not None:
        coverage_diff = abs(quantile_coverage - target_coverage)
        if coverage_diff > 0.05:
            validation_results['passed'] = False
            validation_results['critical_failures'].append(
                f"Quantile coverage out of range: {quantile_coverage:.2%} (target: {target_coverage:.2%} ±5%)"
            )
            logger.error(f"   ❌ CRITICAL: Coverage ({quantile_coverage:.2%}) outside ±5% of target ({target_coverage:.2%})")
        else:
            validation_results['checks']['quantile_coverage'] = {'passed': True, 'value': quantile_coverage}
            logger.info(f"   ✅ Quantile coverage: {quantile_coverage:.2%} within ±5% of target ({target_coverage:.2%})")
    else:
        validation_results['warnings'].append("Quantile coverage not provided for validation")
        logger.warning("   ⚠️  Quantile coverage not provided (skipping check)")
    
    # Warning 1: Residual lag-1 ACF < 0.35 (warn only, don't fail)
    if residual_acf_lag1 is not None:
        if residual_acf_lag1 > max_residual_acf:
            validation_results['warnings'].append(
                f"Residual lag-1 ACF ({residual_acf_lag1:.4f}) > {max_residual_acf:.4f}"
            )
            logger.warning(f"   ⚠️  WARNING: Residual lag-1 ACF ({residual_acf_lag1:.4f}) > {max_residual_acf:.4f}")
        else:
            validation_results['checks']['residual_acf'] = {'passed': True, 'value': residual_acf_lag1}
            logger.info(f"   ✅ Residual lag-1 ACF: {residual_acf_lag1:.4f} <= {max_residual_acf:.4f}")
    else:
        validation_results['warnings'].append("Residual ACF not provided for validation")
        logger.warning("   ⚠️  Residual ACF not provided (skipping check)")
    
    # Warning 2: No severe drift detected
    if drift_results is not None:
        overall_severity = drift_results.get('overall_severity', 'LOW')
        if overall_severity == 'HIGH':
            validation_results['warnings'].append(f"Severe drift detected (severity: {overall_severity})")
            logger.warning(f"   ⚠️  WARNING: Severe drift detected (severity: {overall_severity})")
        else:
            validation_results['checks']['drift'] = {'passed': True, 'severity': overall_severity}
            logger.info(f"   ✅ Drift status: {overall_severity}")
    else:
        validation_results['warnings'].append("Drift results not provided for validation")
        logger.warning("   ⚠️  Drift results not provided (skipping check)")
    
    # Warning 3: Horizon degradation ratio
    if horizon_degradation_ratio is not None:
        if horizon_degradation_ratio > degradation_threshold:
            validation_results['warnings'].append(
                f"Long-horizon instability: H7/H1 ratio ({horizon_degradation_ratio:.2f}) > {degradation_threshold:.2f}"
            )
            logger.warning(f"   ⚠️  WARNING: Horizon degradation ratio ({horizon_degradation_ratio:.2f}) > {degradation_threshold:.2f}")
        else:
            validation_results['checks']['horizon_degradation'] = {'passed': True, 'value': horizon_degradation_ratio}
            logger.info(f"   ✅ Horizon degradation: {horizon_degradation_ratio:.2f} <= {degradation_threshold:.2f}")
    
    # Final summary
    logger.info("\n" + "=" * 70)
    if validation_results['passed']:
        logger.info("✅ PRODUCTION VALIDATION PASSED")
        if validation_results['warnings']:
            logger.info(f"   Warnings: {len(validation_results['warnings'])} (non-blocking)")
    else:
        logger.error("❌ PRODUCTION VALIDATION FAILED")
        logger.error(f"   Critical failures: {len(validation_results['critical_failures'])}")
        for failure in validation_results['critical_failures']:
            logger.error(f"      - {failure}")
        if validation_results['warnings']:
            logger.warning(f"   Warnings: {len(validation_results['warnings'])}")
    
    return validation_results


def save_validation_report(
    validation_results: Dict,
    output_path: str = "models/forecast_system/production_validation.json"
) -> None:
    """Save production validation report to JSON."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(validation_results, f, indent=2, default=str)
    
    logger.info(f"   💾 Validation report saved to {output_path}")

