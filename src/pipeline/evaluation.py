import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from .logger import get_logger

logger = get_logger(__name__)

def compute_metrics(y_true, y_pred):
    """Compute comprehensive regression metrics."""
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    # Calculate accuracy as (1 - normalized MAE) * 100
    mean_y = np.mean(y_true)
    normalized_mae = mae / mean_y if mean_y > 0 else mae
    accuracy = max(0, (1 - normalized_mae) * 100)
    
    metrics = {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "R2": round(r2, 4),
        "Accuracy": round(accuracy, 2)
    }
    
    return metrics

