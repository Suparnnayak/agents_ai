import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from src.pipeline.ensemble_predictor import predict_ensemble
from src.pipeline.logger import get_logger

logger = get_logger(__name__)


def compute_metrics(y_true, y_pred):
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    accuracy = (1 - (mae / np.mean(y_true))) * 100

    return {
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "Accuracy": accuracy
    }


def quantile_coverage(y_true, lower, upper):
    inside = ((y_true >= lower) & (y_true <= upper)).mean()
    return round(inside * 100, 2)


def evaluate_ensemble(csv_path: str):
    logger.info(f"📥 Loading dataset: {csv_path}")
    df = pd.read_csv(csv_path)

    if "admissions" not in df.columns:
        raise ValueError("Dataset must contain `admissions` column for evaluation.")

    y_true = df["admissions"].values

    logger.info("🔮 Running ensemble prediction…")
    pred_df = predict_ensemble(df)

    y_pred = pred_df["median"].values
    lower = pred_df["lower"].values
    upper = pred_df["upper"].values

    # Compute metrics
    metrics = compute_metrics(y_true, y_pred)
    coverage = quantile_coverage(y_true, lower, upper)

    # Spike-specific metrics
    spike_threshold = np.percentile(y_true, 75)  # Top 25% are spikes
    spike_mask = y_true > spike_threshold
    n_spikes = spike_mask.sum()
    
    if n_spikes > 0:
        spike_mae = mean_absolute_error(y_true[spike_mask], y_pred[spike_mask])
        spike_rmse = np.sqrt(mean_squared_error(y_true[spike_mask], y_pred[spike_mask]))
        spike_underpred = (y_pred[spike_mask] < y_true[spike_mask]).mean() * 100
        
        logger.info("\n📊 **Ensemble Metrics**")
        for k, v in metrics.items():
            logger.info(f"{k}: {v:.4f}")
        logger.info(f"Quantile Coverage (q10–q90): {coverage}%")
        
        logger.info(f"\n🔺 **Spike Metrics** (threshold={spike_threshold:.1f}, n={n_spikes})")
        logger.info(f"Spike MAE: {spike_mae:.2f}")
        logger.info(f"Spike RMSE: {spike_rmse:.2f}")
        logger.info(f"Spike Underprediction Rate: {spike_underpred:.1f}%")
    else:
        logger.info("\n📊 **Ensemble Metrics**")
        for k, v in metrics.items():
            logger.info(f"{k}: {v:.4f}")
        logger.info(f"Quantile Coverage (q10–q90): {coverage}%")

    # ----------- Plot 1: True vs Predicted --------------
    plt.figure(figsize=(12, 5))
    plt.plot(df["date"], y_true, label="Actual", linewidth=2)
    plt.plot(df["date"], y_pred, label="Predicted (median)", linewidth=2)
    plt.legend()
    plt.xticks(rotation=45)
    plt.title("Actual vs Ensemble Predicted Admissions")
    plt.tight_layout()
    plt.show()

    # ----------- Plot 2: Uncertainty Bands --------------
    plt.figure(figsize=(12, 5))
    plt.plot(df["date"], y_pred, label="Median", linewidth=2)
    plt.fill_between(df["date"], lower, upper, alpha=0.3, label="q10–q90 Band")
    plt.plot(df["date"], y_true, label="Actual", color="black", linewidth=1)
    plt.legend()
    plt.xticks(rotation=45)
    plt.title("Ensemble Uncertainty Band")
    plt.tight_layout()
    plt.show()

    return metrics, coverage


if __name__ == "__main__":
    # Change city CSV here
    evaluate_ensemble("generated_datasets_ml_ready/xgb/mumbai_xgb.csv")
