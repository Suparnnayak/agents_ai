"""
Test script to verify inference is deterministic and stateless.

Usage:
    python test_deterministic.py
"""

from forecast_system.model_bundle import ModelBundle
from forecast_system.ingestion import load_data
from forecast_system.inference import forecast, self_test

def main():
    print("=" * 70)
    print("DETERMINISTIC INFERENCE TEST")
    print("=" * 70)
    print()
    
    # Load model and data
    print("[1/3] Loading model and data...")
    bundle = ModelBundle.load("models/forecast_system/lightgbm_final.pkl")
    historical_df = load_data("dataset/synthetic_hospital_data.csv")
    print(f"   Model loaded: {len(bundle.feature_columns)} features")
    print(f"   Data loaded: {len(historical_df)} rows")
    print()
    
    # Test 1: Deterministic test (same input, same output)
    print("[2/3] Testing determinism (self_test)...")
    try:
        self_test(bundle, historical_df)
        print("   [PASS] Inference is deterministic")
    except AssertionError as e:
        print(f"   [FAIL] {e}")
        return False
    except Exception as e:
        print(f"   [ERROR] {e}")
        return False
    print()
    
    # Test 2: Multiple consecutive calls
    print("[3/3] Testing multiple consecutive calls...")
    results = []
    for i in range(3):
        result = forecast(
            bundle=bundle,
            raw_df=historical_df.copy(deep=True),
            horizons=[1, 2, 3]
        )
        count = len(result)
        results.append(count)
        print(f"   Call {i+1}: {count} forecasts")
    
    # Check all calls produced same count
    if len(set(results)) == 1:
        print(f"   [PASS] All calls produced {results[0]} forecasts")
    else:
        print(f"   [FAIL] Inconsistent counts: {results}")
        return False
    
    print()
    print("=" * 70)
    print("ALL TESTS PASSED - Inference is stateless and deterministic!")
    print("=" * 70)
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)

