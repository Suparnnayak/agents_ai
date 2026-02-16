"""
Hospital Forecast API

Production FastAPI application for hospital admissions forecasting.
"""

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import os
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import subprocess

from forecast_system.inference import forecast, forecast_to_json
from forecast_system.ingestion import load_data
from forecast_system.model_bundle import ModelBundle
from forecast_system.utils import get_logger

logger = get_logger(__name__)

app = FastAPI(
    title="Hospital Forecast API",
    description="7-day hospital admissions forecasting system",
    version="1.0.0"
)

# Model path
MODEL_PATH = "models/forecast_system/lightgbm_final.pkl"

# Load model on startup
bundle = None
historical_data = None
model_loaded_at = None
model_path_used = None

# Rate limiting (simple in-memory)
rate_limit_store = defaultdict(list)
RATE_LIMIT_REQUESTS = 50
RATE_LIMIT_WINDOW = 60  # seconds

@app.on_event("startup")
async def load_model():
    """Load model and historical data on startup."""
    global bundle, historical_data, model_loaded_at, model_path_used
    
    try:
        # Try multiple paths for model
        model_paths = [
            MODEL_PATH,
            Path(__file__).parent / MODEL_PATH,
            f"../{MODEL_PATH}",
            Path("/opt/render/project/src") / MODEL_PATH,
            Path("/opt/render/project") / MODEL_PATH,
        ]
        
        model_loaded = False
        for path in model_paths:
            path_str = str(path)
            if os.path.exists(path_str):
                bundle = ModelBundle.load(path_str)
                model_path_used = path_str
                model_loaded_at = datetime.now().isoformat()
                print(f"✅ Model loaded from: {path_str}")
                model_loaded = True
                break
        
        if not model_loaded:
            print(f"Current working directory: {os.getcwd()}")
            print(f"App file location: {Path(__file__).absolute()}")
            raise FileNotFoundError(f"Model not found. Tried: {model_paths}")
        
        # Load historical data
        data_paths = [
            "dataset/synthetic_hospital_data.csv",
            Path(__file__).parent / "dataset/synthetic_hospital_data.csv",
            Path("/opt/render/project/src") / "dataset/synthetic_hospital_data.csv",
            Path("/opt/render/project") / "dataset/synthetic_hospital_data.csv",
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
            print("⚠️  Warning: Historical data not found.")
            historical_data = None
            
    except Exception as e:
        print(f"❌ Error loading model: {e}")
        raise


class ForecastRequest(BaseModel):
    """Request model for forecast endpoint."""
    hospital_ids: Optional[List[str]] = Field(None, description="List of hospital IDs to forecast")
    horizons: Optional[List[int]] = Field([1, 2, 3, 4, 5, 6, 7], description="Forecast horizons in days")
    
    @validator('hospital_ids')
    def validate_hospital_ids(cls, v):
        """Validate hospital_ids."""
        if v is not None:
            if len(v) == 0:
                raise ValueError("hospital_ids cannot be empty list")
            # Check for duplicates
            if len(v) != len(set(v)):
                raise ValueError("hospital_ids contains duplicates")
        return v
    
    @validator('horizons')
    def validate_horizons(cls, v):
        """Validate horizons."""
        if v is None or len(v) == 0:
            raise ValueError("horizons cannot be empty")
        # Check for duplicates
        if len(v) != len(set(v)):
            raise ValueError("horizons contains duplicates")
        # Check range
        for h in v:
            if h < 1:
                raise ValueError(f"horizon must be >= 1, got {h}")
            if h > 7:
                raise ValueError(f"horizon must be <= 7, got {h}")
        return sorted(v)  # Return sorted for consistency


class HealthResponse(BaseModel):
    """Health check response."""
    model_config = {"protected_namespaces": ()}
    
    status: str
    model_loaded: bool
    data_loaded: bool


class ModelInfoResponse(BaseModel):
    """Model information response."""
    model_config = {"protected_namespaces": ()}
    
    version: str = "1.0.0"
    trained_at: Optional[str] = None
    feature_count: int
    feature_columns: List[str]
    path: Optional[str] = None
    git_commit: Optional[str] = None


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
        status="healthy" if bundle is not None else "unhealthy",
        model_loaded=bundle is not None,
        data_loaded=historical_data is not None
    )


def check_rate_limit(request: Request):
    """Simple rate limiting middleware."""
    client_ip = request.client.host
    now = time.time()
    
    # Clean old entries
    rate_limit_store[client_ip] = [
        ts for ts in rate_limit_store[client_ip] 
        if now - ts < RATE_LIMIT_WINDOW
    ]
    
    # Check limit
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds"
        )
    
    # Record request
    rate_limit_store[client_ip].append(now)
    return True


def get_git_commit() -> Optional[str]:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None


@app.post("/predict")
def predict(
    request: ForecastRequest,
    rate_limit: bool = Depends(check_rate_limit)
):
    """
    Generate hospital admissions forecasts.
    
    Args:
        request: ForecastRequest with parameters
        rate_limit: Rate limiting dependency
        
    Returns:
        JSON with forecasts for requested hospitals and horizons
    """
    # Start timing
    start_time = time.time()
    request_timestamp = datetime.now().isoformat()
    
    if bundle is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    if historical_data is None:
        raise HTTPException(status_code=503, detail="Historical data not loaded")
    
    try:
        # ========================================================================
        # STRICT INPUT VALIDATION
        # ========================================================================
        
        # Get available hospitals
        available_hospitals = set(historical_data['hospital_id'].unique().tolist())
        
        # Validate hospital_ids if provided
        if request.hospital_ids is not None:
            # Check for empty list (already validated by Pydantic, but double-check)
            if len(request.hospital_ids) == 0:
                raise HTTPException(
                    status_code=400,
                    detail="hospital_ids cannot be empty list"
                )
            
            # STRICT: Max hospitals per request limit
            MAX_HOSPITALS_PER_REQUEST = 20
            if len(request.hospital_ids) > MAX_HOSPITALS_PER_REQUEST:
                raise HTTPException(
                    status_code=400,
                    detail=f"Too many hospitals requested: {len(request.hospital_ids)}. Maximum allowed: {MAX_HOSPITALS_PER_REQUEST}"
                )
            
            # Check for unknown hospitals
            requested_hospitals = set(request.hospital_ids)
            unknown_hospitals = requested_hospitals - available_hospitals
            
            if unknown_hospitals:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unknown hospital_ids: {sorted(unknown_hospitals)}. Available: {sorted(available_hospitals)}"
                )
        
        # Validate horizons (already validated by Pydantic, but ensure sorted)
        horizons = sorted(request.horizons) if request.horizons else [1, 2, 3, 4, 5, 6, 7]
        
        # Filter by hospital_ids if provided (deep copy to prevent mutation)
        raw_df = historical_data.copy(deep=True)
        hospital_count = len(available_hospitals)
        
        if request.hospital_ids:
            raw_df = raw_df[raw_df['hospital_id'].isin(request.hospital_ids)].copy(deep=True)
            hospital_count = len(request.hospital_ids)
        
        # Validate filtered data
        if raw_df.empty:
            raise HTTPException(
                status_code=400,
                detail=f"No data found for hospitals: {request.hospital_ids}"
            )
        
        # Generate forecasts (pass deep copy, never shared object)
        forecast_df = forecast(
            bundle=bundle,
            raw_df=raw_df.copy(deep=True),
            horizons=horizons
        )
        
        # Validate forecast output
        if forecast_df.empty:
            raise HTTPException(
                status_code=500,
                detail="Forecast generation returned empty results"
            )
        
        # Calculate inference time
        inference_time = time.time() - start_time
        
        # Log request metrics (structured logging)
        logger.info(
            f"Prediction successful | "
            f"hospitals={hospital_count} | "
            f"horizons={len(horizons)} | "
            f"forecasts={len(forecast_df)} | "
            f"inference_time={inference_time:.3f}s"
        )
        
        # Convert to JSON format
        result = forecast_to_json(forecast_df)
        
        return {
            "status": "success",
            "forecasts": result["forecasts"],
            "count": len(result["forecasts"]),
            "metadata": {
                "hospitals_requested": hospital_count,
                "horizons_requested": len(horizons),
                "inference_time_seconds": round(inference_time, 3)
            }
        }
        
    except HTTPException:
        # Re-raise HTTP exceptions as-is (these are intentional)
        raise
    except Exception as e:
        # Basic error guard - never leak raw stack traces
        inference_time = time.time() - start_time
        logger.exception(
            f"Prediction error | "
            f"hospitals={hospital_count if 'hospital_count' in locals() else 'unknown'} | "
            f"horizons={len(horizons) if 'horizons' in locals() else 'unknown'} | "
            f"inference_time={inference_time:.3f}s"
        )
        raise HTTPException(
            status_code=500,
            detail="Internal prediction error"
        )


def check_rate_limit(request: Request):
    """Simple rate limiting middleware."""
    client_ip = request.client.host
    now = time.time()
    
    # Clean old entries
    rate_limit_store[client_ip] = [
        ts for ts in rate_limit_store[client_ip] 
        if now - ts < RATE_LIMIT_WINDOW
    ]
    
    # Check limit
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds"
        )
    
    # Record request
    rate_limit_store[client_ip].append(now)
    return True


def get_git_commit() -> Optional[str]:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--short', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=2
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None


@app.get("/model-info", response_model=ModelInfoResponse)
def model_info():
    """Get model information."""
    if bundle is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return ModelInfoResponse(
        version="1.0.0",
        trained_at=model_loaded_at,
        feature_count=len(bundle.feature_columns),
        feature_columns=bundle.feature_columns,
        path=model_path_used,
        git_commit=get_git_commit()
    )


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

