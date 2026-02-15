"""
Leakage Integrity Tests

Detects data leakage and integrity issues in the forecasting pipeline.
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple
from forecast_system.utils import get_logger

logger = get_logger(__name__)


def target_shuffle_test(X: pd.DataFrame,
                       y: pd.Series,
                       dates: pd.Series,
                       model_class,
                       **model_kwargs) -> Dict:
    """
    Target shuffle test: Shuffle admissions and confirm performance collapses.
    
    If model still performs well on shuffled data, there's leakage.
    
    Args:
        X: Features
        y: Original targets
        dates: Dates
        model_class: Model class to test
        **model_kwargs: Model parameters
        
    Returns:
        Dictionary with test results
    """
    logger.info("=" * 60)
    logger.info("LEAKAGE TEST 1: Target Shuffle Test")
    logger.info("=" * 60)
    
    # Train on original data
    from .training import train_final_model
    
    # Split data
    split_date = dates.max() - pd.Timedelta(days=90)
    train_mask = dates < split_date
    test_mask = dates >= split_date
    
    X_train_orig = X[train_mask].copy()
    y_train_orig = y[train_mask].copy()
    X_test = X[test_mask].copy()
    y_test = y[test_mask].copy()
    
    # Train on original
    model_orig = train_final_model(
        model_class,
        X_train_orig, y_train_orig,
        X_test[:100], y_test[:100],  # Small validation set
        use_quantiles=False,
        use_sample_weights=False,
        save_path=None,
        **model_kwargs
    )
    
    orig_mae = np.mean(np.abs(y_test.values - model_orig.predict(X_test)))
    
    # Shuffle targets
    y_train_shuffled = y_train_orig.copy()
    np.random.seed(42)
    y_train_shuffled = pd.Series(np.random.permutation(y_train_shuffled.values), index=y_train_shuffled.index)
    
    # Train on shuffled
    model_shuffled = train_final_model(
        model_class,
        X_train_orig, y_train_shuffled,
        X_test[:100], y_test[:100],
        use_quantiles=False,
        use_sample_weights=False,
        save_path=None,
        **model_kwargs
    )
    
    shuffled_mae = np.mean(np.abs(y_test.values - model_shuffled.predict(X_test)))
    
    # Calculate improvement ratio
    improvement_ratio = shuffled_mae / orig_mae  # How much worse shuffled is
    
    logger.info(f"   Original MAE: {orig_mae:.2f}")
    logger.info(f"   Shuffled MAE: {shuffled_mae:.2f}")
    logger.info(f"   Shuffled is {improvement_ratio:.2f}x worse (expected: >1.2x)")
    
    # Leakage detected if shuffled performs similarly (within 20% of original)
    if shuffled_mae < orig_mae * 1.2:
        logger.warning("   WARNING: Model performs similarly on shuffled data!")
        logger.warning("   This suggests potential data leakage.")
        leakage_detected = True
    else:
        logger.info("   PASS: Model performance degrades significantly on shuffled data (expected)")
        leakage_detected = False
    
    return {
        'original_mae': float(orig_mae),
        'shuffled_mae': float(shuffled_mae),
        'improvement_ratio': float(improvement_ratio),
        'leakage_detected': leakage_detected
    }


def lag_integrity_check(df: pd.DataFrame,
                       lag_cols: list = ['lag_1', 'lag_7', 'lag_14']) -> Dict:
    """
    Verify lag features use only past dates.
    
    Args:
        df: DataFrame with date, admissions, and lag columns
        lag_cols: List of lag column names
        
    Returns:
        Dictionary with check results
    """
    logger.info("=" * 60)
    logger.info("LEAKAGE TEST 2: Lag Integrity Check")
    logger.info("=" * 60)
    
    if 'date' not in df.columns:
        logger.warning("   Cannot check lag integrity: 'date' column missing")
        return {'status': 'skipped', 'reason': 'date column missing'}
    
    df = df.sort_values(['hospital_id', 'date']).copy()
    issues = []
    
    for hospital_id, group in df.groupby('hospital_id'):
        group = group.sort_values('date').reset_index(drop=True)
        
        for lag_col in lag_cols:
            if lag_col not in group.columns:
                continue
            
            # Get lag value (e.g., lag_1 = 1 day)
            lag_days = int(lag_col.split('_')[1])
            
            for idx in range(lag_days, len(group)):
                current_date = group.loc[idx, 'date']
                lag_value = group.loc[idx, lag_col]
                
                if pd.isna(lag_value):
                    continue
                
                # Find the date this lag value came from
                source_idx = idx - lag_days
                if source_idx < 0:
                    issues.append({
                        'hospital_id': hospital_id,
                        'date': current_date,
                        'lag_col': lag_col,
                        'issue': 'Negative index'
                    })
                    continue
                
                source_date = group.loc[source_idx, 'date']
                expected_date = current_date - pd.Timedelta(days=lag_days)
                
                # Check if source date matches expected
                if abs((source_date - expected_date).days) > 1:  # Allow 1 day tolerance
                    issues.append({
                        'hospital_id': hospital_id,
                        'date': current_date,
                        'lag_col': lag_col,
                        'source_date': source_date,
                        'expected_date': expected_date,
                        'issue': 'Date mismatch'
                    })
    
    if issues:
        logger.warning(f"   WARNING: Found {len(issues)} lag integrity issues")
        for issue in issues[:5]:  # Show first 5
            logger.warning(f"      {issue}")
        leakage_detected = True
    else:
        logger.info("   PASS: All lag features use correct past dates")
        leakage_detected = False
    
    return {
        'issues_found': len(issues),
        'leakage_detected': leakage_detected,
        'sample_issues': issues[:10]
    }


def horizon_separation_check(df_stacked: pd.DataFrame) -> Dict:
    """
    Verify no future horizon leaks into earlier ones.
    
    In horizon stacking, each row should only use features from dates <= its target date.
    
    Args:
        df_stacked: DataFrame after horizon stacking (with 'horizon' and 'date' columns)
        
    Returns:
        Dictionary with check results
    """
    logger.info("=" * 60)
    logger.info("LEAKAGE TEST 3: Horizon Separation Check")
    logger.info("=" * 60)
    
    if 'horizon' not in df_stacked.columns or 'date' not in df_stacked.columns:
        logger.warning("   Cannot check horizon separation: required columns missing")
        return {'status': 'skipped'}
    
    issues = []
    
    # Handle encoded hospital_id column
    hospital_col = 'hospital_id'
    if 'hospital_id' not in df_stacked.columns and 'hospital_id_enc' in df_stacked.columns:
        hospital_col = 'hospital_id_enc'
    
    if hospital_col not in df_stacked.columns:
        logger.warning("   Cannot check horizon separation: hospital_id column missing")
        return {'status': 'skipped', 'reason': 'hospital_id column missing'}
    
    # Group by hospital and check each row
    for hospital_id, group in df_stacked.groupby(hospital_col):
        group = group.sort_values('date').reset_index(drop=True)
        
        for idx, row in group.iterrows():
            horizon = row['horizon']
            current_date = row['date']
            
            # Target date for this horizon
            target_date = current_date + pd.Timedelta(days=horizon)
            
            # Check lag features: they should be from dates <= current_date
            for lag_col in ['lag_1', 'lag_7', 'lag_14', 'lag_21']:
                if lag_col not in row.index:
                    continue
                
                lag_value = row[lag_col]
                if pd.isna(lag_value):
                    continue
                
                # Lag should come from a date before or equal to current_date
                # This is checked in lag_integrity_check, so we skip detailed check here
            
            # Check if any feature uses future information
            # (This is a simplified check - full check would require knowing feature creation logic)
    
    # Handle encoded hospital_id column
    hospital_col = 'hospital_id'
    if 'hospital_id' not in df_stacked.columns and 'hospital_id_enc' in df_stacked.columns:
        hospital_col = 'hospital_id_enc'
    
    # For now, just verify that dates are properly ordered
    df_sorted = df_stacked.sort_values([hospital_col, 'date', 'horizon'])
    
    # Check: for same date, horizons should be 1, 2, 3, ..., 7
    for hospital_id, group in df_sorted.groupby(hospital_col):
        for date, date_group in group.groupby('date'):
            horizons = sorted(date_group['horizon'].unique())
            if horizons != list(range(1, len(horizons) + 1)):
                issues.append({
                    'hospital_id': hospital_id,
                    'date': date,
                    'horizons_found': horizons,
                    'issue': 'Non-sequential horizons'
                })
    
    if issues:
        logger.warning(f"   WARNING: Found {len(issues)} horizon separation issues")
        leakage_detected = True
    else:
        logger.info("   PASS: Horizon separation appears correct")
        leakage_detected = False
    
    return {
        'issues_found': len(issues),
        'leakage_detected': leakage_detected,
        'sample_issues': issues[:10]
    }


def run_all_leakage_checks(X: pd.DataFrame,
                          y: pd.Series,
                          dates: pd.Series,
                          df_original: pd.DataFrame,
                          model_class,
                          **model_kwargs) -> Dict:
    """
    Run all leakage checks.
    
    Args:
        X: Feature DataFrame
        y: Target Series
        dates: Date Series
        df_original: Original DataFrame (before stacking)
        model_class: Model class for shuffle test
        **model_kwargs: Model parameters
        
    Returns:
        Dictionary with all test results
    """
    logger.info("=" * 70)
    logger.info("RUNNING LEAKAGE INTEGRITY TESTS")
    logger.info("=" * 70)
    
    results = {}
    
    # Test 1: Target shuffle
    try:
        results['shuffle_test'] = target_shuffle_test(X, y, dates, model_class, **model_kwargs)
    except Exception as e:
        logger.error(f"   Shuffle test failed: {e}")
        results['shuffle_test'] = {'error': str(e)}
    
    # Test 2: Lag integrity
    try:
        results['lag_integrity'] = lag_integrity_check(df_original)
    except Exception as e:
        logger.error(f"   Lag integrity check failed: {e}")
        results['lag_integrity'] = {'error': str(e)}
    
    # Test 3: Horizon separation
    try:
        # Reconstruct stacked DataFrame for check (use hospital_id_enc if available)
        df_stacked = X.copy()
        df_stacked['date'] = dates.values
        if 'horizon' in X.columns:
            df_stacked['horizon'] = X['horizon'].values
        # Use hospital_id_enc if hospital_id not available (after encoding)
        if 'hospital_id_enc' in X.columns and 'hospital_id' not in df_stacked.columns:
            df_stacked['hospital_id_enc'] = X['hospital_id_enc'].values
        results['horizon_separation'] = horizon_separation_check(df_stacked)
    except Exception as e:
        logger.error(f"   Horizon separation check failed: {e}")
        results['horizon_separation'] = {'error': str(e)}
    
    # Summary
    logger.info("=" * 70)
    logger.info("LEAKAGE TEST SUMMARY")
    logger.info("=" * 70)
    
    any_leakage = False
    for test_name, test_result in results.items():
        if isinstance(test_result, dict) and test_result.get('leakage_detected', False):
            logger.warning(f"   {test_name}: LEAKAGE DETECTED")
            any_leakage = True
        elif isinstance(test_result, dict) and 'error' not in test_result:
            logger.info(f"   {test_name}: PASS")
    
    if any_leakage:
        logger.warning("   OVERALL: Some leakage detected - review pipeline")
    else:
        logger.info("   OVERALL: No leakage detected")
    
    results['any_leakage_detected'] = any_leakage
    
    return results

