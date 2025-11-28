"""
Simple script to train models and save them.
Run this from the project root directory.
"""
import sys
from pathlib import Path
import os

# Add src to path
sys.path.append(str(Path(__file__).parent))

from src.pipeline.train_pipeline import run_training_for_city, train_all_cities

def main():
    print("="*70)
    print("HOSPITAL PATIENT INFLOW FORECASTING - MODEL TRAINING")
    print("="*70)
    
    # ============================================================
    # CONFIGURATION - EDIT THIS SECTION
    # ============================================================
    
    # Option 1: Train a single city
    TRAIN_SINGLE_CITY = True
    CITY_NAME = "Mumbai"  # Change to: "Delhi", "Bengaluru", "Hyderabad", or "Noida"
    
    # Option 2: Train all cities
    TRAIN_ALL_CITIES = False
    CITIES = ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Noida"]
    
    # Training settings
    USE_OPTUNA = True      # Set to False for faster training (uses optimized defaults)
    OPTUNA_TRIALS = 50     # Reduce to 20-30 for faster training
    OUTPUT_DIR = "models"  # Where to save models
    
    # ============================================================
    # END CONFIGURATION
    # ============================================================
    
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"\nOutput directory: {Path(OUTPUT_DIR).absolute()}")
    print(f"Optuna tuning: {'Yes' if USE_OPTUNA else 'No (using optimized defaults)'}")
    if USE_OPTUNA:
        print(f"Optuna trials: {OPTUNA_TRIALS}")
    print("="*70 + "\n")
    
    try:
        if TRAIN_ALL_CITIES:
            # Train all cities
            print(f"Training models for {len(CITIES)} cities...")
            results = train_all_cities(
                cities=CITIES,
                output_dir=OUTPUT_DIR,
                use_optuna=USE_OPTUNA,
                optuna_trials=OPTUNA_TRIALS,
                use_time_series_cv=False
            )
            
            # Print summary
            print("\n" + "="*70)
            print("TRAINING SUMMARY")
            print("="*70)
            for city, result in results.items():
                if "error" not in result:
                    metrics = result.get("metrics_median", {})
                    print(f"\n{city}:")
                    print(f"  ✅ Accuracy: {metrics.get('Accuracy', 'N/A')}%")
                    print(f"  ✅ MAE: {metrics.get('MAE', 'N/A')}")
                    print(f"  ✅ RMSE: {metrics.get('RMSE', 'N/A')}")
                    print(f"  ✅ Coverage: {result.get('coverage', 'N/A'):.2%}")
                else:
                    print(f"\n{city}: ❌ Error - {result['error']}")
        
        elif TRAIN_SINGLE_CITY:
            # Train single city
            print(f"Training models for {CITY_NAME}...")
            results = run_training_for_city(
                city=CITY_NAME,
                output_dir=OUTPUT_DIR,
                use_optuna=USE_OPTUNA,
                optuna_trials=OPTUNA_TRIALS,
                use_time_series_cv=False
            )
            
            # Print results
            print("\n" + "="*70)
            print("TRAINING RESULTS")
            print("="*70)
            print(f"City: {results['city']}")
            print(f"Accuracy: {results['metrics_median']['Accuracy']}%")
            print(f"MAE: {results['metrics_median']['MAE']}")
            print(f"RMSE: {results['metrics_median']['RMSE']}")
            print(f"R2 Score: {results['metrics_median']['R2']}")
            print(f"Quantile Coverage: {results['coverage']:.2%}")
            print(f"Features Used: {results['n_features']}")
            print(f"Training Samples: {results['n_train']}")
            print(f"Validation Samples: {results['n_val']}")
        
        else:
            print("❌ Please set either TRAIN_SINGLE_CITY or TRAIN_ALL_CITIES to True")
            return 1
        
        # Verify models were saved
        print("\n" + "="*70)
        print("VERIFYING SAVED MODELS")
        print("="*70)
        
        if TRAIN_SINGLE_CITY:
            city_check = [CITY_NAME.lower()]
        else:
            city_check = [c.lower() for c in CITIES]
        
        model_dir = Path(OUTPUT_DIR)
        all_saved = True
        
        for city in city_check:
            files = [
                model_dir / f"{city}_xgb_q50.model",
                model_dir / f"{city}_lgb_q10.model",
                model_dir / f"{city}_lgb_q90.model"
            ]
            
            print(f"\n{city.upper()}:")
            for f in files:
                if f.exists():
                    size_kb = f.stat().st_size / 1024
                    print(f"  ✅ {f.name} ({size_kb:.1f} KB)")
                else:
                    print(f"  ❌ {f.name} (NOT FOUND)")
                    all_saved = False
        
        if all_saved:
            print("\n" + "="*70)
            print("✅ SUCCESS! All models saved successfully!")
            print("="*70)
            print(f"\nModels location: {Path(OUTPUT_DIR).absolute()}")
            print("\nNext steps:")
            print("  1. Use predict_pipeline.py to make predictions")
            print("  2. Check RUN_GUIDE.md for more details")
            return 0
        else:
            print("\n⚠️  Some models were not saved. Check the error messages above.")
            return 1
            
    except Exception as e:
        print(f"\n❌ Error during training: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())

