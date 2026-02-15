"""
Hospital Forecast API

Production FastAPI application for hospital admissions forecasting.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict
import pandas as pd
import numpy as np
import os
from pathlib import Path

from forecast_system.inference import forecast, forecast_to_json
from forecast_system.ingestion import load_data
from forecast_system.feature_engineering import engineer_features
from forecast_system.models.per_horizon_model import PerHorizonForecaster

app = FastAPI(
    title="Hospital Forecast API",
    description="7-day hospital admissions forecasting system",
    version="1.0.0"
)

# Model path (try multiple locations)
MODEL_PATH = "models/forecast_system/lightgbm_final.pkl"

# Load model on startup
model = None
historical_data = None

@app.on_event("startup")
async def load_model():
    """Load model and historical data on startup."""
    global model, historical_data
    
    try:
        # Try multiple paths for model
        # Model is now in agents_ai/models/ so it gets deployed with the app
        model_paths = [
            MODEL_PATH,  # Relative to current working directory (agents_ai/)
            Path(__file__).parent / MODEL_PATH,  # Relative to app.py location
            f"../{MODEL_PATH}",  # One level up (fallback)
            Path(__file__).parent.parent / MODEL_PATH,  # From agents_ai to project root (fallback)
        ]
        
        model_loaded = False
        for path in model_paths:
            path_str = str(path)
            if os.path.exists(path_str):
                model = PerHorizonForecaster.load(path_str)
                print(f"✅ Model loaded from: {path_str}")
                model_loaded = True
                break
        
        if not model_loaded:
            # Debug: print current working directory and file location
            print(f"Current working directory: {os.getcwd()}")
            print(f"App file location: {Path(__file__).absolute()}")
            print(f"App file parent: {Path(__file__).parent.absolute()}")
            raise FileNotFoundError(f"Model not found. Tried: {model_paths}")
        
        # Load historical data for feature engineering
        data_paths = [
            "dataset/synthetic_hospital_data.csv",  # Relative to current working directory
            "../dataset/synthetic_hospital_data.csv",  # One level up from agents_ai
            "agents_ai/dataset/synthetic_hospital_data.csv",  # From project root
            Path(__file__).parent / "dataset/synthetic_hospital_data.csv",  # Inside agents_ai
            Path(__file__).parent.parent / "dataset/synthetic_hospital_data.csv",  # From agents_ai to project root
            # Render-specific paths
            Path("/opt/render/project") / "agents_ai" / "dataset" / "synthetic_hospital_data.csv",
            Path("/opt/render/project") / "dataset" / "synthetic_hospital_data.csv",
            Path("/opt/render/project/src") / "dataset" / "synthetic_hospital_data.csv",
        ]
        
        data_loaded = False
        for path in data_paths:
            path_str = str(path)
            if os.path.exists(path_str):
                historical_data = load_data(path_str)
                print(f"✅ Historical data loaded from: {path_str}")
                data_loaded = True
                break
        
        if not data_loaded:
            print("⚠️  Warning: Historical data not found. Some features may be unavailable.")
            historical_data = None
            
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        raise


class ForecastRequest(BaseModel):
    """Request model for forecast endpoint."""
    hospital_ids: Optional[List[str]] = None  # If None, forecast for all hospitals (e.g., ['HOSP_1', 'HOSP_2'])
    horizons: Optional[List[int]] = [1, 2, 3, 4, 5, 6, 7]  # Days ahead to forecast
    use_quantiles: bool = True
    future_exogenous: Optional[Dict] = None  # Optional future scenario data


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    model_loaded: bool
    data_loaded: bool


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "status": "Hospital Forecast API running",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check",
            "/predict": "Generate forecasts (POST)",
            "/docs": "API documentation"
        }
    }


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if model is not None else "unhealthy",
        model_loaded=model is not None,
        data_loaded=historical_data is not None
    )


@app.post("/predict")
def predict(request: ForecastRequest):
    """
    Generate hospital admissions forecasts.
    
    Args:
        request: ForecastRequest with parameters
        
    Returns:
        JSON with forecasts for requested hospitals and horizons
    """
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if historical_data is None:
        raise HTTPException(status_code=503, detail="Historical data not loaded")
    
    try:
        # Prepare future exogenous data if provided
        future_exog_df = None
        if request.future_exogenous:
            future_exog_df = pd.DataFrame([request.future_exogenous])
        
        # Generate forecasts using inference module
        forecast_df = forecast(
            model=model,
            historical_df=historical_data,
            horizons=request.horizons,
            use_quantiles=request.use_quantiles,
            hospital_ids=request.hospital_ids,
            future_exogenous=future_exog_df,
            apply_post_processing=True
        )
        
        # Convert to JSON format
        result = forecast_to_json(forecast_df)
        
        return {
            "status": "success",
            "forecasts": result["forecasts"],
            "count": len(result["forecasts"])
        }
        
    except Exception as e:
        import traceback
        print("❌ PREDICT ERROR:", str(e))
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(e)}")


@app.get("/hospitals")
def list_hospitals():
    """List all available hospitals."""
    if historical_data is None:
        raise HTTPException(status_code=503, detail="Historical data not loaded")
    
    hospitals = sorted(historical_data['hospital_id'].unique().tolist())
    return {
        "hospitals": hospitals,
        "count": len(hospitals)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)

