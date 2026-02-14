"""
TFT Decision Framework

Implements measurement framework to decide when to move from tree-based models to TFT.

Decision Criteria (from expert analysis):
- If residual ACF > 0.4 after Option A improvements → sequence problem → use TFT
- If CV CoV > 40% after Option A improvements → regime instability → use TFT
- If long-horizon conformal adjustments > 3x → uncertainty modeling failure → use TFT

Otherwise: Tree-based system is sufficient.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from .utils import get_logger

logger = get_logger(__name__)


def evaluate_tree_system_adequacy(
    residual_acf_lag1: float,
    residual_acf_lag7: float,
    cv_coefficient_of_variation: float,
    long_horizon_conformal_adjustment: Optional[float] = None,
    horizon_7_interval_width: Optional[float] = None,
    acf_threshold: float = 0.40,
    cov_threshold: float = 40.0,
    conformal_threshold: float = 3.0,
    interval_width_threshold: float = 20.0
) -> Dict[str, any]:
    """
    Evaluate whether tree-based system is adequate or TFT is needed.
    
    Args:
        residual_acf_lag1: Lag-1 residual autocorrelation
        residual_acf_lag7: Lag-7 residual autocorrelation
        cv_coefficient_of_variation: CV coefficient of variation (percentage)
        long_horizon_conformal_adjustment: Maximum conformal adjustment factor for H7 (optional)
        horizon_7_interval_width: Average interval width for horizon 7 (optional)
        acf_threshold: ACF threshold for TFT recommendation (default 0.40)
        cov_threshold: CoV threshold for TFT recommendation (default 40%)
        conformal_threshold: Conformal adjustment threshold (default 3.0x)
        interval_width_threshold: Interval width threshold for H7 (default 20.0)
        
    Returns:
        Dictionary with:
        - tree_system_adequate: bool
        - recommendation: str ('continue_trees' or 'consider_tft')
        - reasons: list of issues
        - metrics: dict of all metrics
        - score: float (0-1, higher = more need for TFT)
    """
    logger.info("=" * 70)
    logger.info("🔍 TREE SYSTEM ADEQUACY EVALUATION")
    logger.info("=" * 70)
    
    result = {
        'tree_system_adequate': True,
        'recommendation': 'continue_trees',
        'reasons': [],
        'metrics': {
            'residual_acf_lag1': residual_acf_lag1,
            'residual_acf_lag7': residual_acf_lag7,
            'cv_coefficient_of_variation': cv_coefficient_of_variation,
            'long_horizon_conformal_adjustment': long_horizon_conformal_adjustment,
            'horizon_7_interval_width': horizon_7_interval_width
        },
        'score': 0.0  # 0 = trees fine, 1 = definitely need TFT
    }
    
    issues = []
    score_components = []
    
    # Check 1: Residual Autocorrelation (Lag-1)
    logger.info(f"   📊 Residual ACF (Lag-1): {residual_acf_lag1:.3f}")
    if residual_acf_lag1 > acf_threshold:
        issues.append(f"High residual autocorrelation (lag-1: {residual_acf_lag1:.3f} > {acf_threshold})")
        score_components.append(min(1.0, (residual_acf_lag1 - acf_threshold) / 0.2))  # Normalize to 0-1
        logger.warning(f"      ⚠️  ACF too high: {residual_acf_lag1:.3f} > {acf_threshold}")
    else:
        logger.info(f"      ✅ ACF acceptable: {residual_acf_lag1:.3f} <= {acf_threshold}")
    
    # Check 2: Weekly Structure (Lag-7 ACF)
    logger.info(f"   📊 Residual ACF (Lag-7): {residual_acf_lag7:.3f}")
    if residual_acf_lag7 > 0.50:  # Stricter threshold for weekly structure
        issues.append(f"Weekly structure not captured (lag-7 ACF: {residual_acf_lag7:.3f} > 0.50)")
        score_components.append(min(1.0, (residual_acf_lag7 - 0.50) / 0.2))
        logger.warning(f"      ⚠️  Weekly structure weak: {residual_acf_lag7:.3f} > 0.50")
    else:
        logger.info(f"      ✅ Weekly structure captured: {residual_acf_lag7:.3f} <= 0.50")
    
    # Check 3: CV Stability
    logger.info(f"   📊 CV Coefficient of Variation: {cv_coefficient_of_variation:.1f}%")
    if cv_coefficient_of_variation > cov_threshold:
        issues.append(f"High CV instability (CoV: {cv_coefficient_of_variation:.1f}% > {cov_threshold}%)")
        score_components.append(min(1.0, (cv_coefficient_of_variation - cov_threshold) / 30.0))
        logger.warning(f"      ⚠️  CV instability: {cv_coefficient_of_variation:.1f}% > {cov_threshold}%")
    else:
        logger.info(f"      ✅ CV stable: {cv_coefficient_of_variation:.1f}% <= {cov_threshold}%")
    
    # Check 4: Long-Horizon Conformal Adjustment (if available)
    if long_horizon_conformal_adjustment is not None:
        logger.info(f"   📊 Long-Horizon Conformal Adjustment: {long_horizon_conformal_adjustment:.2f}x")
        if long_horizon_conformal_adjustment > conformal_threshold:
            issues.append(
                f"Long-horizon uncertainty under-modeled "
                f"(conformal adjustment: {long_horizon_conformal_adjustment:.2f}x > {conformal_threshold}x)"
            )
            score_components.append(min(1.0, (long_horizon_conformal_adjustment - conformal_threshold) / 2.0))
            logger.warning(f"      ⚠️  Conformal adjustment too large: {long_horizon_conformal_adjustment:.2f}x > {conformal_threshold}x")
        else:
            logger.info(f"      ✅ Conformal adjustment reasonable: {long_horizon_conformal_adjustment:.2f}x <= {conformal_threshold}x")
    
    # Check 5: Horizon 7 Interval Width (if available)
    if horizon_7_interval_width is not None:
        logger.info(f"   📊 Horizon 7 Interval Width: {horizon_7_interval_width:.2f}")
        if horizon_7_interval_width > interval_width_threshold:
            issues.append(
                f"Long-horizon intervals too wide "
                f"(H7 width: {horizon_7_interval_width:.2f} > {interval_width_threshold})"
            )
            score_components.append(min(1.0, (horizon_7_interval_width - interval_width_threshold) / 10.0))
            logger.warning(f"      ⚠️  Interval width too large: {horizon_7_interval_width:.2f} > {interval_width_threshold}")
        else:
            logger.info(f"      ✅ Interval width reasonable: {horizon_7_interval_width:.2f} <= {interval_width_threshold}")
    
    # Calculate overall score (weighted average)
    if score_components:
        result['score'] = np.mean(score_components)
    else:
        result['score'] = 0.0
    
    # Make recommendation
    if issues:
        result['tree_system_adequate'] = False
        result['recommendation'] = 'consider_tft'
        result['reasons'] = issues
    else:
        result['tree_system_adequate'] = True
        result['recommendation'] = 'continue_trees'
        result['reasons'] = ["All metrics within acceptable ranges"]
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("📊 EVALUATION SUMMARY")
    logger.info("=" * 70)
    logger.info(f"   Tree System Adequate: {result['tree_system_adequate']}")
    logger.info(f"   Recommendation: {result['recommendation'].upper()}")
    logger.info(f"   TFT Need Score: {result['score']:.2f} (0 = trees fine, 1 = need TFT)")
    logger.info(f"   Issues Found: {len(issues)}")
    
    if result['recommendation'] == 'consider_tft':
        logger.warning("\n   ⚠️  RECOMMENDATION: Consider Hybrid LGBM + TFT")
        logger.warning("   Reasons:")
        for reason in issues:
            logger.warning(f"      - {reason}")
        logger.warning("\n   TFT will help with:")
        logger.warning("      - Temporal sequence modeling")
        logger.warning("      - Residual autocorrelation reduction")
        logger.warning("      - Long-horizon uncertainty modeling")
        logger.warning("      - Regime transition handling")
    else:
        logger.info("\n   ✅ RECOMMENDATION: Continue with Tree-Based System")
        logger.info("   Current system is adequate for production use.")
        logger.info("   Monitor metrics and re-evaluate if conditions change.")
    
    logger.info("=" * 70)
    
    return result


def should_use_tft(
    residual_acf_lag1: float,
    residual_acf_lag7: float,
    cv_coefficient_of_variation: float,
    **kwargs
) -> bool:
    """
    Simple boolean check: Should we use TFT?
    
    Returns True if any critical threshold is exceeded.
    """
    result = evaluate_tree_system_adequacy(
        residual_acf_lag1=residual_acf_lag1,
        residual_acf_lag7=residual_acf_lag7,
        cv_coefficient_of_variation=cv_coefficient_of_variation,
        **kwargs
    )
    return not result['tree_system_adequate']


def get_tft_recommendation_summary(
    evaluation_result: Dict
) -> str:
    """
    Generate human-readable recommendation summary.
    
    Args:
        evaluation_result: Result from evaluate_tree_system_adequacy()
        
    Returns:
        Formatted string summary
    """
    if evaluation_result['recommendation'] == 'continue_trees':
        return (
            "✅ Tree-based system is adequate.\n"
            "   Continue with current LightGBM/XGBoost approach.\n"
            "   Monitor metrics and re-evaluate if conditions change."
        )
    else:
        return (
            "⚠️  Consider Hybrid LGBM + TFT approach.\n"
            f"   TFT Need Score: {evaluation_result['score']:.2f}/1.0\n"
            "   Issues:\n" +
            "\n".join(f"      - {reason}" for reason in evaluation_result['reasons'])
        )

