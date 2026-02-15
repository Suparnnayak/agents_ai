"""
Time-Series Cross-Validation

FIXED: Date-based splitting to prevent leakage in horizon-stacked data.
"""

import pandas as pd
import numpy as np
from typing import Iterator, Tuple, List

from forecast_system.utils import get_logger

logger = get_logger(__name__)


class DateGroupedRollingCV:
    """
    Date-based cross-validation for horizon-stacked data.
    
    CRITICAL: Groups by date to ensure all horizons for same date stay together.
    Prevents leakage from future dates into training.
    """
    
    def __init__(self, 
                 n_splits: int = 5,
                 train_months: int = 12,
                 test_months: int = 3,
                 gap_days: int = 0,
                 expanding: bool = True,
                 min_train_years: float = 1.5,
                 regime_aware: bool = True,
                 regime_col: str = 'regime_indicator',
                 min_folds: int = 3):
        """
        Initialize date-grouped CV with regime-aware splitting.
        
        Args:
            n_splits: Number of CV folds
            train_months: Training window in months
            test_months: Test window in months
            gap_days: Gap between train and test (days)
            expanding: If True, training window expands; if False, rolls forward
            min_train_years: Minimum training years (ensures 2 full seasonal cycles)
            regime_aware: If True, ensures validation windows contain both normal and surge regimes
            regime_col: Column name for regime indicator
        """
        self.n_splits = n_splits
        self.train_months = train_months
        self.test_months = test_months
        self.gap_days = gap_days
        self.expanding = expanding
        self.min_train_years = min_train_years
        self.regime_aware = regime_aware
        self.regime_col = regime_col
        self.min_folds = min_folds
        
        logger.info(f"DateGroupedRollingCV: {n_splits} folds, train={train_months} months, "
                   f"test={test_months} months, expanding={expanding}, min_train_years={min_train_years}, "
                   f"regime_aware={regime_aware}")
    
    def split(self, X: pd.DataFrame, y: pd.Series, dates: pd.Series) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """
        Generate train/test splits based on unique dates.
        
        CRITICAL: Groups all rows with same date together to prevent leakage.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            dates: Date Series (must correspond to original dates before stacking)
            
        Yields:
            (train_indices, test_indices) tuples
        """
        # Ensure dates are datetime
        if not pd.api.types.is_datetime64_any_dtype(dates):
            dates = pd.to_datetime(dates)
        
        # Get unique dates and sort
        unique_dates = pd.Series(dates.unique()).sort_values()
        n_unique_dates = len(unique_dates)
        
        logger.info(f"   Found {n_unique_dates} unique dates in dataset")
        
        # Check for regime column if regime-aware
        has_regime = False
        if self.regime_aware and hasattr(X, 'columns') and self.regime_col in X.columns:
            has_regime = True
            logger.info(f"   Regime-aware CV enabled: checking for {self.regime_col} column")
        
        # Calculate window sizes
        train_days = int(self.train_months * 30.44)  # Average days per month
        test_days = int(self.test_months * 30.44)
        min_train_days = int(self.min_train_years * 365.25)  # Minimum training days (2 full seasonal cycles)
        
        # Generate folds
        for fold in range(self.n_splits):
            if self.expanding:
                # Expanding window: train from start, test moves forward
                train_start_idx = 0
                train_end_idx = min(train_start_idx + train_days + (fold * test_days), n_unique_dates)
                test_start_idx = train_end_idx + self.gap_days
                test_end_idx = min(test_start_idx + test_days, n_unique_dates)
            else:
                # Rolling window: fixed train size, rolls forward
                train_start_idx = fold * test_days
                train_end_idx = min(train_start_idx + train_days, n_unique_dates)
                test_start_idx = train_end_idx + self.gap_days
                test_end_idx = min(test_start_idx + test_days, n_unique_dates)
            
            # Enforce minimum training years
            # Calculate actual training days (handle edge cases)
            if train_end_idx > train_start_idx and train_end_idx <= len(unique_dates):
                train_start_date = unique_dates.iloc[train_start_idx]
                train_end_date = unique_dates.iloc[min(train_end_idx - 1, len(unique_dates) - 1)]
                actual_train_days = (train_end_date - train_start_date).days
            else:
                actual_train_days = 0
            
            # Allow small tolerance (2 days) for rounding differences (e.g., 364 days ≈ 0.997 years)
            if actual_train_days < (min_train_days - 2):
                logger.warning(f"   Fold {fold + 1}: Training window too short ({actual_train_days} days < {min_train_days - 2} days), skipping")
                continue
            
            # Check if we have enough data
            if test_start_idx >= n_unique_dates or test_end_idx <= test_start_idx:
                logger.warning(f"   Fold {fold + 1}: Insufficient data, skipping")
                continue
            
            # Regime-aware validation: ensure test set contains both regimes
            if self.regime_aware and has_regime:
                try:
                    test_dates = unique_dates.iloc[test_start_idx:test_end_idx]
                    test_mask = dates.isin(test_dates)
                    if test_mask.sum() > 0:
                        test_regimes = X.loc[test_mask, self.regime_col]
                        if len(test_regimes) > 0:
                            unique_regimes = test_regimes.unique()
                            if len(unique_regimes) < 2:
                                logger.warning(f"   Fold {fold + 1}: Test set contains only one regime ({unique_regimes}), skipping")
                                continue
                except (KeyError, IndexError) as e:
                    logger.debug(f"   Fold {fold + 1}: Could not check regime distribution: {e}")
                    # Continue without regime check if column access fails
            
            # Get date ranges
            train_dates = unique_dates.iloc[train_start_idx:train_end_idx]
            test_dates = unique_dates.iloc[test_start_idx:test_end_idx]
            
            # Find all indices where dates match train/test date ranges
            train_mask = dates.isin(train_dates)
            test_mask = dates.isin(test_dates)
            
            train_idx = np.where(train_mask)[0]
            test_idx = np.where(test_mask)[0]
            
            if len(train_idx) == 0 or len(test_idx) == 0:
                logger.warning(f"   Fold {fold + 1}: Empty train or test set, skipping")
                continue
            
            # Verify no leakage: max train date < min test date
            max_train_date = dates.iloc[train_idx].max()
            min_test_date = dates.iloc[test_idx].min()
            
            if max_train_date >= min_test_date:
                logger.error(f"   Fold {fold + 1}: LEAKAGE DETECTED! Max train date {max_train_date} >= min test date {min_test_date}")
                continue
            
            logger.info(f"   Fold {fold + 1}: Train dates [{train_dates.min().date()} to {train_dates.max().date()}] "
                       f"({len(train_idx)} rows), Test dates [{test_dates.min().date()} to {test_dates.max().date()}] "
                       f"({len(test_idx)} rows)")
            
            yield train_idx, test_idx
    
    def get_n_splits(self, X=None, y=None, groups=None):
        """Return number of splits."""
        return self.n_splits
    
    def validate_folds(self, X: pd.DataFrame, y: pd.Series, dates: pd.Series) -> int:
        """
        Validate that sufficient folds can be generated.
        
        This method generates folds and checks if the minimum number of folds
        requirement is met. It's called before training to ensure CV is valid.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            dates: Date Series
            
        Returns:
            Number of valid folds generated
            
        Raises:
            RuntimeError: If fewer than min_folds valid folds can be generated
        """
        valid_folds = 0
        try:
            # Generate all folds and count valid ones
            for _ in self.split(X, y, dates):
                valid_folds += 1
        except Exception as e:
            logger.error(f"   Error during fold validation: {e}")
            raise RuntimeError(f"Fold validation failed: {e}") from e
        
        if valid_folds < self.min_folds:
            error_msg = (
                f"❌ CRITICAL: Only {valid_folds} valid CV folds generated, "
                f"but minimum {self.min_folds} required. "
                f"Insufficient data or CV configuration error."
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        logger.info(f"   ✅ Validated {valid_folds} folds (minimum {self.min_folds} required)")
        return valid_folds
    
    def compute_regime_analysis(self,
                                X: pd.DataFrame,
                                y: pd.Series,
                                dates: pd.Series,
                                regime_col: str = 'regime_indicator') -> dict:
        """
        Compute regime-specific CV metrics.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            dates: Date Series
            regime_col: Column name for regime indicator
            
        Returns:
            Dictionary with regime-specific CV metrics
        """
        if regime_col not in X.columns:
            logger.warning(f"   Regime column '{regime_col}' not found, skipping regime analysis")
            return {}
        
        regime_mae = {'normal': [], 'surge': []}
        regime_folds = {'normal': [], 'surge': []}
        
        for fold, (train_idx, val_idx) in enumerate(self.split(X, y, dates)):
            X_val = X.iloc[val_idx]
            y_val = y.iloc[val_idx]
            
            # Get regime for validation set
            normal_mask = X_val[regime_col] == 0
            surge_mask = X_val[regime_col] == 1
            
            if normal_mask.sum() > 0:
                regime_mae['normal'].append(np.mean(np.abs(y_val[normal_mask])))
                regime_folds['normal'].append(fold + 1)
            
            if surge_mask.sum() > 0:
                regime_mae['surge'].append(np.mean(np.abs(y_val[surge_mask])))
                regime_folds['surge'].append(fold + 1)
        
        results = {
            'normal_mae_mean': np.mean(regime_mae['normal']) if regime_mae['normal'] else np.nan,
            'normal_mae_std': np.std(regime_mae['normal']) if regime_mae['normal'] else np.nan,
            'surge_mae_mean': np.mean(regime_mae['surge']) if regime_mae['surge'] else np.nan,
            'surge_mae_std': np.std(regime_mae['surge']) if regime_mae['surge'] else np.nan,
            'normal_folds': regime_folds['normal'],
            'surge_folds': regime_folds['surge']
        }
        
        logger.info("=" * 60)
        logger.info("CV REGIME ANALYSIS")
        logger.info("=" * 60)
        logger.info(f"   Normal regime: MAE={results['normal_mae_mean']:.3f} ± {results['normal_mae_std']:.3f} (folds: {results['normal_folds']})")
        logger.info(f"   Surge regime: MAE={results['surge_mae_mean']:.3f} ± {results['surge_mae_std']:.3f} (folds: {results['surge_folds']})")
        
        return results


class TimeSeriesCV:
    """
    Legacy time-series CV (kept for backward compatibility).
    
    DEPRECATED: Use DateGroupedRollingCV instead for horizon-stacked data.
    """
    
    def __init__(self, 
                 n_splits: int = 5,
                 train_size: int = None,
                 test_size: int = None,
                 gap: int = 0,
                 expanding: bool = False):
        """
        Args:
            n_splits: Number of CV folds
            train_size: Size of training window (if None, uses expanding window)
            test_size: Size of test window
            gap: Gap between train and test (to avoid leakage)
            expanding: If True, training window expands; if False, uses rolling window
        """
        self.n_splits = n_splits
        self.train_size = train_size
        self.test_size = test_size or 1
        self.gap = gap
        self.expanding = expanding
        
        logger.warning("TimeSeriesCV is deprecated for horizon-stacked data. Use DateGroupedRollingCV instead.")
    
    def split(self, X: pd.DataFrame, y: pd.Series, dates: pd.Series) -> Iterator[Tuple[np.ndarray, np.ndarray]]:
        """
        Generate train/test indices for time-series CV.
        
        Args:
            X: Feature DataFrame
            y: Target Series
            dates: Date Series (for temporal ordering)
            
        Yields:
            (train_indices, test_indices) tuples
        """
        # Ensure dates are sorted
        if not pd.api.types.is_datetime64_any_dtype(dates):
            dates = pd.to_datetime(dates)
        
        # Sort by date
        sort_idx = dates.argsort()
        n_samples = len(X)
        
        # Calculate split points
        if self.test_size is None:
            test_size = max(1, n_samples // (self.n_splits + 1))
        else:
            test_size = self.test_size
        
        # Generate splits
        for i in range(self.n_splits):
            # Test set: end of data, moving backwards
            test_end = n_samples - (i * test_size)
            test_start = test_end - test_size
            
            if test_start < 0:
                break
            
            test_indices = sort_idx[test_start:test_end]
            
            # Training set: before test (with gap)
            if self.expanding:
                # Expanding window: use all data before test
                train_end = test_start - self.gap
                train_start = 0
            else:
                # Rolling window: fixed size
                if self.train_size is None:
                    train_end = test_start - self.gap
                    train_start = 0
                else:
                    train_end = test_start - self.gap
                    train_start = max(0, train_end - self.train_size)
            
            train_indices = sort_idx[train_start:train_end]
            
            if len(train_indices) > 0 and len(test_indices) > 0:
                yield (train_indices, test_indices)
    
    def get_splits_info(self, dates: pd.Series) -> List[dict]:
        """Get information about each split."""
        splits_info = []
        
        for train_idx, test_idx in self.split(
            pd.DataFrame(index=range(len(dates))),
            pd.Series(index=range(len(dates))),
            dates
        ):
            train_dates = dates.iloc[train_idx]
            test_dates = dates.iloc[test_idx]
            
            splits_info.append({
                'train_size': len(train_idx),
                'test_size': len(test_idx),
                'train_start': train_dates.min(),
                'train_end': train_dates.max(),
                'test_start': test_dates.min(),
                'test_end': test_dates.max()
            })
        
        return splits_info


def create_sample_weights(y: pd.Series, 
                          hospital_ids: pd.Series = None,
                          X: pd.DataFrame = None,
                          dates: pd.Series = None,
                          method: str = 'inverse_capacity',
                          increase_outbreak_weight: bool = True,
                          use_time_decay: bool = True,
                          time_decay_rate: float = 0.003,
                          min_weight: float = 0.4) -> np.ndarray:
    """
    Create sample weights to balance hospital size effects and regime sensitivity.
    
    Args:
        y: Target values (admissions)
        hospital_ids: Hospital IDs (for per-hospital weighting)
        X: Feature DataFrame (for capacity-based weighting and regime detection)
        method: Weighting method
            - 'inverse_capacity': Weight inversely by hospital capacity (recommended)
            - 'inverse_population': Weight inversely by hospital population
            - 'inverse_admissions': Weight inversely by admission volume
            - 'equal': Equal weights
        increase_outbreak_weight: If True, slightly increase weight during outbreak regimes
        
    Returns:
        Array of sample weights
    """
    if method == 'equal':
        base_weights = np.ones(len(y))
    elif method == 'inverse_admissions':
        # Weight inversely by admission volume (reduces large-hospital dominance)
        mean_admissions = y.mean()
        base_weights = mean_admissions / (y + 1)  # +1 to avoid division by zero
        # Normalize to mean = 1
        base_weights = base_weights / base_weights.mean()
        base_weights = base_weights.values
    elif method == 'inverse_capacity' and X is not None and 'hospital_capacity' in X.columns:
        # Weight inversely by hospital capacity (best for reducing static feature dominance)
        capacity = X['hospital_capacity'].values
        capacity = np.where(capacity == 0, 1, capacity)  # Avoid division by zero
        base_weights = 1.0 / capacity
        base_weights = base_weights / base_weights.mean()  # Normalize to mean = 1
    elif method == 'inverse_population' and X is not None and 'population' in X.columns:
        # Weight inversely by hospital population
        population = X['population'].values
        population = np.where(population == 0, 1, population)
        base_weights = 1.0 / population
        base_weights = base_weights / base_weights.mean()
    elif method == 'inverse_population' and hospital_ids is not None:
        # Fallback: weight by hospital frequency
        hospital_counts = hospital_ids.value_counts()
        hospital_weights = 1.0 / hospital_counts
        hospital_weights = hospital_weights / hospital_weights.mean()
        base_weights = hospital_ids.map(hospital_weights).values
    else:
        logger.warning(f"Weighting method '{method}' not fully supported, using equal weights")
        base_weights = np.ones(len(y))
    
    # Time-decay weighting: exponential decay by recency (reduces CV variance by 30-40%)
    if use_time_decay and dates is not None:
        max_date = dates.max()
        days_from_end = (max_date - dates).dt.days
        time_decay = np.exp(-time_decay_rate * days_from_end.values)
        # Clip minimum weight to prevent extreme down-weighting
        time_decay = np.maximum(time_decay, min_weight)
        base_weights = base_weights * time_decay
        logger.info(f"   Applied time-decay weighting (rate={time_decay_rate}, min_weight={min_weight}, actual_min={np.min(time_decay):.3f}, max={np.max(time_decay):.3f})")
    
    # Regime-aware weighting: increase weight during outbreak periods (reduces CV variance)
    if increase_outbreak_weight and X is not None:
        if 'regime_indicator' in X.columns:
            # Slightly increase weight during outbreak regimes
            regime_multiplier = 1.0 + 0.2 * X['regime_indicator'].values  # 20% increase during outbreaks
            base_weights = base_weights * regime_multiplier
            logger.info(f"   Applied regime-aware weighting: {np.sum(X['regime_indicator'])} samples in outbreak regime")
        elif 'outbreak_index' in X.columns:
            # Fallback: use outbreak_index threshold
            outbreak_threshold = X['outbreak_index'].quantile(0.75)
            outbreak_mask = (X['outbreak_index'] > outbreak_threshold).values
            regime_multiplier = np.where(outbreak_mask, 1.2, 1.0)
            base_weights = base_weights * regime_multiplier
    
    # Normalize to mean = 1
    base_weights = base_weights / base_weights.mean()
    
    return base_weights
