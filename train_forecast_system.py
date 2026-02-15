"""
Quick Start Training Script

Simple entry point for training the forecasting system.
"""

import sys
import os
from pathlib import Path

# Robust root path injection - works in both local and CI environments
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Debug output (can be removed after fixing)
if os.getenv("GITHUB_ACTIONS"):
    print("=" * 70)
    print("DEBUG: Import Path Resolution")
    print("=" * 70)
    print(f"Script location: {__file__}")
    print(f"ROOT directory: {ROOT}")
    print(f"ROOT exists: {ROOT.exists()}")
    print(f"forecast_system exists: {(ROOT / 'forecast_system').exists()}")
    print(f"forecast_system/__init__.py exists: {(ROOT / 'forecast_system' / '__init__.py').exists()}")
    print(f"forecast_system/train_pipeline.py exists: {(ROOT / 'forecast_system' / 'train_pipeline.py').exists()}")
    print(f"Current working directory: {os.getcwd()}")
    print(f"sys.path (first 5):")
    for i, p in enumerate(sys.path[:5]):
        print(f"  [{i}] {p}")
    print("=" * 70)

from forecast_system.train_pipeline import run_training_pipeline
from forecast_system.config import DEFAULT_TRAINING_CONFIG

if __name__ == "__main__":
    print("=" * 70)
    print("HOSPITAL ADMISSIONS 7-DAY FORECASTING SYSTEM")
    print("=" * 70)
    print()
    
    # Use default config (can be customized)
    config = DEFAULT_TRAINING_CONFIG
    
    print("Configuration:")
    print(f"   Dataset: {config.csv_path}")
    print(f"   Models to compare: {config.models_to_test}")
    print(f"   Final model: {config.final_model}")
    print(f"   CV folds: {config.cv_splits}")
    print(f"   Quantile regression: {config.use_quantiles}")
    print(f"   Sample weights: {config.use_sample_weights}")
    print()
    
    # Run pipeline
    results = run_training_pipeline(
        csv_path=config.csv_path,
        compare=config.compare_models,
        models_to_test=config.models_to_test,
        final_model=config.final_model,
        use_quantiles=config.use_quantiles,
        cv_splits=config.cv_splits,
        train_years=config.train_years,
        test_years=config.test_years,
        output_dir=config.output_dir
    )
    
    print("\nTraining complete! Check results in:", config.output_dir)

