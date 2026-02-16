"""
Production Training Script

Simple entry point for training the forecasting system.
"""

from forecast_system.training import run_training_pipeline
from forecast_system.config import DEFAULT_TRAINING_CONFIG

if __name__ == "__main__":
    print("=" * 70)
    print("HOSPITAL ADMISSIONS 7-DAY FORECASTING SYSTEM")
    print("=" * 70)
    print()
    
    # Use default config
    config = DEFAULT_TRAINING_CONFIG
    
    print("Configuration:")
    print(f"   Dataset: {config.csv_path}")
    print(f"   Output directory: {config.output_dir}")
    print()
    
    # Run training pipeline
    bundle = run_training_pipeline(
        csv_path=config.csv_path,
        output_dir=config.output_dir,
        test_size=config.test_size,
        random_state=config.random_state
    )
    
    print(f"\nTraining complete! Model saved to: {config.output_dir}/lightgbm_final.pkl")

