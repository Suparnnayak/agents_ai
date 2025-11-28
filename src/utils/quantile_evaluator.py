from typing import Sequence
import numpy as np


def evaluate_quantile_coverage(
    y_true: Sequence[float],
    preds_low,
    preds_mid,
    preds_high
) -> float:
    """
    Percentage of targets falling between q10 and q90.
    Accepts numpy arrays or torch tensors.
    """
    y = np.asarray(y_true)
    low = np.asarray(preds_low)
    high = np.asarray(preds_high)

    coverage = np.mean((y >= low) & (y <= high))
    return coverage

