"""
Production Training Pipeline

Simple, stable training with single LightGBM model.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from lightgbm import LGBMRegressor, early_stopping
from sklearn.model_selection import train_test_split

from forecast_system.features import create_features
from forecast_system.model_bundle import ModelBundle
from forecast_system.ingestion import load_data


def run_training_pipeline(
    csv_path: str = "dataset/synthetic_hospital_data.csv",
    output_dir: str = "models/forecast_system",
    test_size: float = 0.2,
    random_state: int = 42
):
    """
    Run production training pipeline.
    
    Steps:
    1. Load dataset
    2. Create features
    3. Train LightGBM
    4. Save ModelBundle
    
    Args:
        csv_path: Path to dataset CSV
        output_dir: Directory to save model
        test_size: Test set size (for validation)
        random_state: Random seed
    """
    print("=" * 70)
    print("PRODUCTION TRAINING PIPELINE")
    print("=" * 70)
    print()
    
    # Step 1: Load dataset
    print(f"[1/6] Loading dataset from {csv_path}...")
    df = load_data(csv_path)
    print(f"   Loaded {len(df)} rows, {len(df.columns)} columns")
    print()
    
    # Step 2: Create features
    print("[2/6] Creating features...")
    X, y, encoders = create_features(df)
    print(f"   Features: {len(X.columns)} columns")
    print(f"   Samples: {len(X)} rows")
    print(f"   Feature columns: {list(X.columns)}")
    print()
    
    # Step 3: Train/test split
    print("[3/6] Splitting data...")
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, shuffle=False
    )
    print(f"   Train: {len(X_train)} samples")
    print(f"   Test: {len(X_test)} samples")
    print()
    
    # Step 4: Train LightGBM
    print("[4/6] Training LightGBM model...")
    model = LGBMRegressor(
        n_estimators=500,
        learning_rate=0.05,
        max_depth=6,
        random_state=random_state,
        verbose=-1
    )
    
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_test, y_test)],
        eval_metric='mae',
        callbacks=[early_stopping(stopping_rounds=50, verbose=False)]
    )
    
    # Evaluate
    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)
    
    train_mae = np.mean(np.abs(train_pred - y_train))
    test_mae = np.mean(np.abs(test_pred - y_test))
    
    print(f"   Train MAE: {train_mae:.2f}")
    print(f"   Test MAE: {test_mae:.2f}")
    print()
    
    # Step 5: Create ModelBundle
    print("[5/6] Creating ModelBundle...")
    bundle = ModelBundle(
        model=model,
        feature_columns=list(X.columns),
        encoders=encoders
    )
    print(f"   Feature columns: {len(bundle.feature_columns)}")
    print()
    
    # Step 6: Save ModelBundle
    print(f"[6/6] Saving model to {output_dir}...")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    model_path = Path(output_dir) / "lightgbm_final.pkl"
    bundle.save(str(model_path))
    print(f"   Model saved: {model_path}")
    print()
    
    print("=" * 70)
    print("TRAINING COMPLETE")
    print("=" * 70)
    
    return bundle
