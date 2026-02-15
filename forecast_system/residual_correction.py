"""
Residual Correction Module

Trains AR(7) model on residuals per hospital AND per horizon using statsmodels AutoReg.
Captures remaining temporal structure that tree models miss.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from forecast_system.utils import get_logger

# Try to import statsmodels, fallback to LinearRegression if not available
try:
    from statsmodels.tsa.ar_model import AutoReg
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    from sklearn.linear_model import LinearRegression
    logger = get_logger(__name__)
    logger.warning("   statsmodels not available, using LinearRegression for AR model")

logger = get_logger(__name__)


class ResidualCorrector:
    """
    Residual correction using AR(7) model per hospital AND per horizon.
    
    CRITICAL: Residuals differ by horizon, so we need separate AR models.
    Uses statsmodels AutoReg for proper AR modeling.
    """
    
    def __init__(self, ar_order: int = 7):
        """
        Initialize residual corrector.
        
        Args:
            ar_order: Autoregressive order (default 7 for weekly structure)
        """
        self.ar_order = ar_order
        self.models: Dict[Tuple[int, int], object] = {}  # (hospital_id, horizon) -> AR model
        self.residual_history: Dict[Tuple[int, int], np.ndarray] = {}  # Store recent residuals
        self.is_fitted = False
    
    def fit(self, 
            residuals: np.ndarray,
            hospital_ids: np.ndarray,
            horizons: np.ndarray,
            dates: pd.Series) -> 'ResidualCorrector':
        """
        Train AR(7) model on residuals per hospital AND per horizon.
        
        Args:
            residuals: Model residuals (y_true - y_pred)
            hospital_ids: Hospital IDs
            horizons: Forecast horizons (1-7)
            dates: Date series (for temporal ordering)
            
        Returns:
            Self
        """
        logger.info("=" * 60)
        logger.info("RESIDUAL CORRECTION: Training AR(7) models per (hospital, horizon)")
        logger.info("=" * 60)
        
        # Create DataFrame for easier manipulation
        df = pd.DataFrame({
            'residual': residuals,
            'hospital_id': hospital_ids,
            'horizon': horizons,
            'date': dates.values if hasattr(dates, 'values') else dates
        })
        
        # Sort by hospital, horizon, and date
        df = df.sort_values(['hospital_id', 'horizon', 'date']).reset_index(drop=True)
        
        # Train AR model per (hospital, horizon) combination
        for (hospital_id, horizon), group in df.groupby(['hospital_id', 'horizon']):
            group = group.sort_values('date').reset_index(drop=True)
            residuals_series = group['residual'].values
            
            if len(residuals_series) < self.ar_order + 10:  # Need enough data
                continue
            
            key = (hospital_id, horizon)
            
            try:
                if HAS_STATSMODELS:
                    # Use statsmodels AutoReg (proper AR model)
                    ar_model = AutoReg(residuals_series, lags=self.ar_order, trend='c')
                    ar_fitted = ar_model.fit()
                    self.models[key] = ar_fitted
                    
                    # Evaluate fit
                    y_pred_ar = ar_fitted.fittedvalues[self.ar_order:]
                    y_true_ar = residuals_series[self.ar_order:]
                    mae_ar = np.mean(np.abs(y_true_ar - y_pred_ar))
                    logger.info(f"   Hospital {hospital_id}, Horizon {horizon}: AR({self.ar_order}) MAE={mae_ar:.3f} (n={len(y_true_ar)})")
                else:
                    # Fallback to LinearRegression
                    X_ar = []
                    y_ar = []
                    for i in range(self.ar_order, len(residuals_series)):
                        X_ar.append(residuals_series[i - self.ar_order:i])
                        y_ar.append(residuals_series[i])
                    
                    X_ar = np.array(X_ar)
                    y_ar = np.array(y_ar)
                    
                    model = LinearRegression()
                    model.fit(X_ar, y_ar)
                    self.models[key] = model
                    
                    y_pred_ar = model.predict(X_ar)
                    mae_ar = np.mean(np.abs(y_ar - y_pred_ar))
                    logger.info(f"   Hospital {hospital_id}, Horizon {horizon}: AR({self.ar_order}) MAE={mae_ar:.3f} (n={len(X_ar)})")
                
                # Store recent residuals for prediction
                self.residual_history[key] = residuals_series[-self.ar_order:]
                
            except Exception as e:
                logger.warning(f"   Failed to fit AR model for Hospital {hospital_id}, Horizon {horizon}: {e}")
                continue
        
        self.is_fitted = True
        logger.info(f"   Trained AR({self.ar_order}) models for {len(self.models)} (hospital, horizon) combinations")
        
        return self
    
    def predict(self,
                hospital_ids: np.ndarray,
                horizons: np.ndarray,
                recent_residuals: Optional[Dict[Tuple[int, int], np.ndarray]] = None) -> np.ndarray:
        """
        Predict residual correction per hospital AND per horizon.
        
        Args:
            hospital_ids: Hospital IDs for each prediction
            horizons: Forecast horizons (1-7) for each prediction
            recent_residuals: Optional dict mapping (hospital_id, horizon) -> recent residual array
                            If None, uses stored residual history
            
        Returns:
            Residual corrections to add to main predictions
        """
        if not self.is_fitted:
            logger.warning("   Residual corrector not fitted, returning zeros")
            return np.zeros(len(hospital_ids))
        
        corrections = np.zeros(len(hospital_ids))
        
        # Group predictions by (hospital, horizon)
        for i, (hospital_id, horizon) in enumerate(zip(hospital_ids, horizons)):
            key = (hospital_id, horizon)
            
            if key not in self.models:
                continue  # No model for this combination
            
            model = self.models[key]
            
            # Get recent residuals for this (hospital, horizon)
            if recent_residuals is not None and key in recent_residuals:
                residual_history = recent_residuals[key]
            elif key in self.residual_history:
                residual_history = self.residual_history[key]
            else:
                continue  # No residual history available
            
            if len(residual_history) < self.ar_order:
                continue
            
            # Use last ar_order residuals for prediction
            recent = residual_history[-self.ar_order:]
            
            try:
                if HAS_STATSMODELS and hasattr(model, 'forecast'):
                    # statsmodels AutoReg: use forecast method
                    correction = model.forecast(steps=1, exog=None)[0]
                elif HAS_STATSMODELS:
                    # Alternative: use predict with last values
                    correction = model.predict(start=len(residual_history), end=len(residual_history))[0]
                else:
                    # LinearRegression fallback
                    correction = model.predict(recent.reshape(1, -1))[0]
                
                corrections[i] = correction
            except Exception as e:
                logger.debug(f"   Failed to predict correction for {key}: {e}")
                continue
        
        return corrections
    
    def correct_predictions(self,
                           y_pred: np.ndarray,
                           hospital_ids: np.ndarray,
                           horizons: np.ndarray,
                           recent_residuals: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Apply residual correction to predictions.
        
        Args:
            y_pred: Main model predictions
            hospital_ids: Hospital IDs
            horizons: Forecast horizons (1-7)
            recent_residuals: Recent residual history (optional)
            
        Returns:
            Corrected predictions: y_pred + residual_correction
        """
        corrections = self.predict(hospital_ids, horizons, recent_residuals)
        corrected = y_pred + corrections
        
        logger.info(f"   Applied residual correction: mean correction={np.mean(np.abs(corrections)):.3f}")
        
        return corrected


def create_residual_corrector(y_true: np.ndarray,
                            y_pred: np.ndarray,
                            hospital_ids: np.ndarray,
                            horizons: np.ndarray,
                            dates: pd.Series,
                            ar_order: int = 7) -> ResidualCorrector:
    """
    Create and train residual corrector per hospital AND per horizon.
    
    Args:
        y_true: True values
        y_pred: Model predictions
        hospital_ids: Hospital IDs
        horizons: Forecast horizons (1-7)
        dates: Date series
        ar_order: Autoregressive order
        
    Returns:
        Trained ResidualCorrector
    """
    residuals = y_true - y_pred
    
    corrector = ResidualCorrector(ar_order=ar_order)
    corrector.fit(residuals, hospital_ids, horizons, dates)
    
    return corrector

