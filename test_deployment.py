"""
Quick deployment verification script.
Run this to verify your deployment is ready.
"""
import sys
from pathlib import Path

def check_models():
    """Check if all required model files exist."""
    print("🔍 Checking model files...")
    models_dir = Path("models")
    
    required_models = [
        "global_q10.json",
        "global_q50.json",
        "global_q90.json",
        "global_q50_spike.json",
        "global_q50_extreme_spike.json",
    ]
    
    optional_models = [
        "tft_global_q50.pth",  # Optional for ensemble mode
    ]
    
    missing_required = []
    for model in required_models:
        if not (models_dir / model).exists():
            missing_required.append(model)
    
    if missing_required:
        print(f"❌ Missing required models: {missing_required}")
        return False
    
    print("✅ All required models found")
    
    missing_optional = []
    for model in optional_models:
        if not (models_dir / model).exists():
            missing_optional.append(model)
    
    if missing_optional:
        print(f"⚠️  Missing optional models (ensemble mode will use XGB-only): {missing_optional}")
    else:
        print("✅ All optional models found (ensemble mode available)")
    
    return True


def check_imports():
    """Check if all required packages can be imported."""
    print("\n🔍 Checking imports...")
    
    # Core packages (required)
    core_packages = {
        "pandas": "pandas",
        "numpy": "numpy",
        "xgboost": "xgboost",
        "torch": "torch",
    }
    
    # Optional packages (for API server)
    optional_packages = {
        "flask": "flask",
    }
    
    missing_core = []
    for name, module in core_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing_core.append(name)
    
    if missing_core:
        print(f"❌ Missing core packages: {missing_core}")
        print("   Run: pip install -r requirements.txt")
        return False
    
    print("✅ Core packages imported successfully")
    
    # Check optional packages
    missing_optional = []
    for name, module in optional_packages.items():
        try:
            __import__(module)
        except ImportError:
            missing_optional.append(name)
    
    if missing_optional:
        print(f"⚠️  Missing optional packages (API server): {missing_optional}")
        print("   Install with: pip install flask")
        print("   (API server will not work without Flask)")
    else:
        print("✅ Optional packages found (API server ready)")
    
    return True


def test_prediction():
    """Test if prediction pipeline works."""
    print("\n🔍 Testing prediction pipeline...")
    
    try:
        import pandas as pd
        from src.pipeline.predict_pipeline import predict_df
        
        # Minimal test data
        test_data = pd.DataFrame({
            "date": ["2025-11-29"],
            "admissions": [150],
            "aqi": [180],
            "temp": [28.5],
            "humidity": [65],
            "rainfall": [12.3],
            "wind_speed": [15.2],
            "mobility_index": [75],
            "outbreak_index": [30],
            "festival_flag": [0],
            "holiday_flag": [0],
            "weekday": [4],
            "is_weekend": [0],
            "population_density": [12000],
            "hospital_beds": [500],
            "staff_count": [200],
            "city_id": [1],
            "hospital_id_enc": [101],
        })
        
        # Test XGBoost mode (faster, no TFT needed)
        result = predict_df(test_data, mode="xgb")
        
        if len(result) > 0 and "median" in result.columns:
            print("✅ Prediction pipeline works!")
            print(f"   Sample prediction: {result['median'].iloc[0]:.2f} admissions")
            return True
        else:
            print("❌ Prediction returned invalid format")
            return False
            
    except Exception as e:
        print(f"❌ Prediction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all checks."""
    print("=" * 60)
    print("🚀 Deployment Verification")
    print("=" * 60)
    
    checks = [
        ("Models", check_models),
        ("Imports", check_imports),
        ("Prediction", test_prediction),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ {name} check failed with error: {e}")
            results.append((name, False))
    
    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)
    
    all_passed = True
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
        if not result:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print("🎉 All checks passed! Ready for deployment.")
        print("\nNext steps:")
        print("1. Start API server: python api_server.py")
        print("2. Test API: curl http://localhost:5000/health")
        print("3. See DEPLOYMENT_GUIDE.md for production deployment")
        return 0
    else:
        print("⚠️  Some checks failed. Please fix issues before deploying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

