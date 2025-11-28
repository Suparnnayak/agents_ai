"""
Simple script to run the XGB + TFT ensemble predictor.

Usage:
    python run_ensemble.py
"""

import pandas as pd

from src.pipeline.ensemble_predictor import predict_ensemble


def main():
    df = pd.read_csv("generated_datasets_ml_ready/xgb/mumbai_xgb.csv")
    out = predict_ensemble(df)
    print(out.tail())


if __name__ == "__main__":
    main()


