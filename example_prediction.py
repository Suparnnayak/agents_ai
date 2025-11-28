"""
Example script showing how to use the prediction pipeline for live predictions.
"""
import pandas as pd
from src.pipeline.predict_pipeline import predict_df
from src.pipeline.ensemble_predictor import predict_ensemble

def example_single_prediction():
    """Example: Predict admissions for a single day."""
    print("=" * 60)
    print("Example 1: Single Day Prediction")
    print("=" * 60)
    
    # Prepare input data
    input_data = pd.DataFrame({
        "date": ["2025-11-29"],
        "admissions": [150],  # Yesterday's admissions
        "aqi": [180],
        "temp": [28.5],
        "humidity": [65],
        "rainfall": [12.3],
        "wind_speed": [15.2],
        "mobility_index": [75],
        "outbreak_index": [30],
        "festival_flag": [0],
        "holiday_flag": [0],
        "weekday": [4],  # Friday
        "is_weekend": [0],
        "population_density": [12000],
        "hospital_beds": [500],
        "staff_count": [200],
        "city_id": [1],  # Mumbai
        "hospital_id_enc": [101],
    })
    
    # Make prediction using ensemble
    predictions = predict_ensemble(input_data)
    
    print("\n📊 Prediction Results:")
    print(predictions)
    print(f"\n✅ Median prediction: {predictions['median'].iloc[0]:.1f} admissions")
    print(f"📈 Uncertainty range: {predictions['lower'].iloc[0]:.1f} - {predictions['upper'].iloc[0]:.1f}")


def example_batch_prediction():
    """Example: Predict admissions for multiple days."""
    print("\n" + "=" * 60)
    print("Example 2: Batch Prediction (7 Days)")
    print("=" * 60)
    
    # Prepare input data for next 7 days
    dates = pd.date_range("2025-11-29", periods=7, freq="D")
    
    input_data = pd.DataFrame({
        "date": dates.strftime("%Y-%m-%d"),
        "admissions": [150, 155, 148, 152, 160, 145, 150],  # Historical
        "aqi": [180, 195, 170, 185, 200, 175, 190],
        "temp": [28.5, 29.0, 27.8, 28.2, 29.5, 27.5, 28.8],
        "humidity": [65, 70, 60, 68, 72, 58, 66],
        "rainfall": [12.3, 15.0, 8.5, 10.2, 18.5, 5.0, 14.0],
        "wind_speed": [15.2, 18.0, 12.5, 16.0, 20.0, 10.0, 17.5],
        "mobility_index": [75, 78, 72, 76, 80, 70, 74],
        "outbreak_index": [30, 35, 25, 32, 40, 28, 33],
        "festival_flag": [0, 0, 0, 0, 0, 0, 0],
        "holiday_flag": [0, 0, 0, 0, 0, 0, 0],
        "weekday": dates.weekday,
        "is_weekend": (dates.weekday >= 5).astype(int),
        "population_density": [12000] * 7,
        "hospital_beds": [500] * 7,
        "staff_count": [200] * 7,
        "city_id": [1] * 7,
        "hospital_id_enc": [101] * 7,
    })
    
    # Make prediction
    predictions = predict_ensemble(input_data)
    
    print("\n📊 Prediction Results:")
    print(predictions)
    print(f"\n📈 Average predicted admissions: {predictions['median'].mean():.1f}")


def example_xgb_only():
    """Example: Using XGBoost only (faster, no TFT dependency)."""
    print("\n" + "=" * 60)
    print("Example 3: XGBoost Only (Fast Mode)")
    print("=" * 60)
    
    # For XGBoost mode, we need historical admissions to create lag features
    # If you have historical data, provide it. Otherwise, the pipeline will use defaults.
    input_data = pd.DataFrame({
        "date": ["2025-11-29"],
        "admissions": [150],  # Current/previous day's admissions (used to create lags)
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
    
    # Use XGBoost only (faster, no TFT model needed)
    # Lag features will be auto-created from 'admissions' column
    predictions = predict_df(input_data, mode="xgb")
    
    print("\n📊 Prediction Results (XGBoost only):")
    print(predictions)


def example_with_missing_lag_data():
    """Example: Handling missing historical data."""
    print("\n" + "=" * 60)
    print("Example 4: Missing Lag Data (Use Average)")
    print("=" * 60)
    
    # If you don't have historical admissions, use average
    # (Note: This will reduce accuracy, but still works)
    avg_admissions = 150  # Use your historical average
    
    input_data = pd.DataFrame({
        "date": ["2025-11-29"],
        "admissions": [avg_admissions],  # Use average if unknown
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
    
    predictions = predict_ensemble(input_data)
    
    print("\n📊 Prediction Results (with estimated lag data):")
    print(predictions)
    print("\n⚠️  Note: Accuracy may be reduced without real historical data")


if __name__ == "__main__":
    # Run all examples
    example_single_prediction()
    example_batch_prediction()
    example_xgb_only()
    example_with_missing_lag_data()
    
    print("\n" + "=" * 60)
    print("✅ All examples completed!")
    print("=" * 60)

