"""Main FastAPI application instance for the Hospital Forecast API."""

from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List
import os
import time
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict
import subprocess
from sqlalchemy.orm import Session

import pandas as pd
from forecast_system.inference import forecast, forecast_to_json
from forecast_system.ingestion import load_data
from forecast_system.model_bundle import ModelBundle
from forecast_system.utils import get_logger
from database.session import get_db
from database import crud
from database.models import User
from app.auth.router import router as auth_router
from app.dependencies import get_current_user, require_admin


logger = get_logger(__name__)

app = FastAPI(
    title="Hospital Forecast API",
    description="7-day hospital admissions forecasting system",
    version="1.0.0",
)

# CORS middleware — allow frontend origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://localhost:3002",
        "http://localhost:3003",
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include authentication routes
app.include_router(auth_router)

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
            Path(__file__).parent.parent / MODEL_PATH,
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
            Path(__file__).parent.parent / "dataset/synthetic_hospital_data.csv",
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

        # Initialize database (create tables if they don't exist)
        try:
            from database.session import init_db

            init_db()
            print("✅ Database initialized")
        except Exception as db_error:
            print(f"⚠️  Warning: Database initialization failed: {db_error}")
            print("   API will continue without database persistence")

    except Exception as e:
        print(f"❌ Error loading model: {e}")
        raise


class ForecastRequest(BaseModel):
    """Request model for forecast endpoint."""

    hospital_ids: Optional[List[str]] = Field(
        None, description="List of hospital IDs to forecast"
    )
    horizons: Optional[List[int]] = Field(
        [1, 2, 3, 4, 5, 6, 7], description="Forecast horizons in days"
    )

    @validator("hospital_ids")
    def validate_hospital_ids(cls, v):
        """Validate hospital_ids."""
        if v is not None:
            if len(v) == 0:
                raise ValueError("hospital_ids cannot be empty list")
            # Check for duplicates
            if len(v) != len(set(v)):
                raise ValueError("hospital_ids contains duplicates")
        return v

    @validator("horizons")
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
            "/docs": "API documentation",
        },
    }


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy" if bundle is not None else "unhealthy",
        model_loaded=bundle is not None,
        data_loaded=historical_data is not None,
    )


def check_rate_limit(request: Request):
    """Simple rate limiting middleware."""
    client_ip = request.client.host
    now = time.time()

    # Clean old entries
    rate_limit_store[client_ip] = [
        ts for ts in rate_limit_store[client_ip] if now - ts < RATE_LIMIT_WINDOW
    ]

    # Check limit
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW} seconds",
        )

    # Record request
    rate_limit_store[client_ip].append(now)
    return True


def get_git_commit() -> Optional[str]:
    """Get current git commit hash."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


@app.post("/predict")
def predict(
    request: ForecastRequest,
    rate_limit: bool = Depends(check_rate_limit),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate hospital admissions forecasts.
    """
    # Start timing
    start_time = time.time()

    if bundle is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if historical_data is None:
        raise HTTPException(status_code=503, detail="Historical data not loaded")

    try:
        # STRICT INPUT VALIDATION
        available_hospitals = set(historical_data["hospital_id"].unique().tolist())

        # Validate hospital_ids if provided
        if request.hospital_ids is not None:
            if len(request.hospital_ids) == 0:
                raise HTTPException(
                    status_code=400, detail="hospital_ids cannot be empty list"
                )

            # STRICT: Max hospitals per request limit
            MAX_HOSPITALS_PER_REQUEST = 20
            if len(request.hospital_ids) > MAX_HOSPITALS_PER_REQUEST:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Too many hospitals requested: {len(request.hospital_ids)}. "
                        f"Maximum allowed: {MAX_HOSPITALS_PER_REQUEST}"
                    ),
                )

            # Check for unknown hospitals
            requested_hospitals = set(request.hospital_ids)
            unknown_hospitals = requested_hospitals - available_hospitals

            if unknown_hospitals:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Unknown hospital_ids: {sorted(unknown_hospitals)}. "
                        f"Available: {sorted(available_hospitals)}"
                    ),
                )

        # Validate horizons
        horizons = (
            sorted(request.horizons)
            if request.horizons
            else [1, 2, 3, 4, 5, 6, 7]
        )

        # Filter by hospital_ids if provided (deep copy to prevent mutation)
        raw_df = historical_data.copy(deep=True)
        hospital_count = len(available_hospitals)

        if request.hospital_ids:
            raw_df = raw_df[
                raw_df["hospital_id"].isin(request.hospital_ids)
            ].copy(deep=True)
            hospital_count = len(request.hospital_ids)

        # Validate filtered data
        if raw_df.empty:
            raise HTTPException(
                status_code=400,
                detail=f"No data found for hospitals: {request.hospital_ids}",
            )

        # Generate forecasts (pass deep copy, never shared object)
        forecast_df = forecast(
            bundle=bundle,
            raw_df=raw_df.copy(deep=True),
            horizons=horizons,
        )

        # Validate forecast output
        if forecast_df.empty:
            raise HTTPException(
                status_code=500,
                detail="Forecast generation returned empty results",
            )

        # Calculate inference time
        inference_time = time.time() - start_time

        # SAVE FORECASTS TO DATABASE
        forecast_run_id = None
        try:
            # Get last date per hospital from historical data
            last_dates = {}
            for hosp_id in forecast_df["hospital_id"].unique():
                hosp_data = raw_df[raw_df["hospital_id"] == hosp_id]
                if not hosp_data.empty:
                    last_date = pd.to_datetime(hosp_data["date"]).max()
                    last_dates[hosp_id] = last_date.to_pydatetime().date()

            # Create forecast run record
            forecast_run = crud.create_forecast_run(
                db=db,
                hospital_count=hospital_count,
                horizon_count=len(horizons),
                total_forecasts=len(forecast_df),
                inference_time_seconds=inference_time,
                model_version="1.0.0",
                user_id=current_user.id if current_user else None,
            )
            forecast_run_id = forecast_run.id

            # Prepare forecast data for batch insert
            forecasts_data = []
            for _, row in forecast_df.iterrows():
                hospital_id_str = str(row["hospital_id"])
                horizon = int(row["horizon"])
                prediction = float(row["prediction"])

                # Calculate forecast_date = last_date + horizon days
                if hospital_id_str in last_dates:
                    forecast_date = last_dates[hospital_id_str] + timedelta(
                        days=horizon
                    )
                else:
                    # Fallback: use today + horizon
                    forecast_date = date.today() + timedelta(days=horizon)

                forecasts_data.append(
                    {
                        "hospital_id": hospital_id_str,
                        "horizon": horizon,
                        "prediction": prediction,
                        "forecast_date": forecast_date,
                    }
                )

            # Batch create forecasts
            crud.create_forecasts_batch(
                db=db,
                forecast_run_id=forecast_run_id,
                forecasts_data=forecasts_data,
            )

            # Commit transaction
            db.commit()

            logger.info(
                "Forecasts saved to database | "
                f"run_id={forecast_run_id} | "
                f"forecasts={len(forecasts_data)}"
            )

        except Exception as db_error:
            # Rollback on database error
            db.rollback()
            logger.error(f"Database save failed: {db_error}")

        # Log request metrics (structured logging)
        logger.info(
            "Prediction successful | "
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
                "inference_time_seconds": round(inference_time, 3),
                "forecast_run_id": str(forecast_run_id) if forecast_run_id else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        inference_time = time.time() - start_time
        logger.exception(
            "Prediction error | "
            f"hospitals={hospital_count if 'hospital_count' in locals() else 'unknown'} | "
            f"horizons={len(horizons) if 'horizons' in locals() else 'unknown'} | "
            f"inference_time={inference_time:.3f}s"
        )
        raise HTTPException(status_code=500, detail="Internal prediction error")


@app.get("/model-info", response_model=ModelInfoResponse, dependencies=[Depends(require_admin)])
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
        git_commit=get_git_commit(),
    )


@app.get("/hospitals")
def list_hospitals():
    """List all available hospitals."""
    if historical_data is None:
        raise HTTPException(status_code=503, detail="Historical data not loaded")

    hospitals = sorted(historical_data["hospital_id"].unique().tolist())
    return {
        "hospitals": hospitals,
        "count": len(hospitals),
    }


class ForecastResponse(BaseModel):
    """Forecast response model."""

    id: str
    hospital_id: str
    horizon: int
    prediction: float
    forecast_date: date
    created_at: datetime


class ForecastsListResponse(BaseModel):
    """Forecasts list response with pagination."""

    forecasts: List[ForecastResponse]
    total: int
    skip: int
    limit: int


@app.get("/forecasts", response_model=ForecastsListResponse)
def get_forecasts(
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    start_date: Optional[date] = Query(
        None, description="Filter forecasts >= start_date (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="Filter forecasts <= end_date (YYYY-MM-DD)"
    ),
    horizon: Optional[int] = Query(
        None, ge=1, le=7, description="Filter by horizon (1-7)"
    ),
    skip: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(100, ge=1, le=1000, description="Pagination limit (max 1000)"),
    db: Session = Depends(get_db),
):
    """
    Get stored forecasts with filtering and pagination.
    """
    try:
        forecasts = crud.get_forecasts(
            db=db,
            hospital_id=hospital_id,
            start_date=start_date,
            end_date=end_date,
            horizon=horizon,
            skip=skip,
            limit=limit,
        )

        total = crud.get_forecast_count(
            db=db,
            hospital_id=hospital_id,
            start_date=start_date,
            end_date=end_date,
            horizon=horizon,
        )

        forecast_responses = []
        for f in forecasts:
            hospital_id_str = f.hospital.hospital_id if f.hospital else "unknown"

            forecast_responses.append(
                ForecastResponse(
                    id=str(f.id),
                    hospital_id=hospital_id_str,
                    horizon=f.horizon,
                    prediction=f.prediction,
                    forecast_date=f.forecast_date,
                    created_at=f.created_at,
                )
            )

        return ForecastsListResponse(
            forecasts=forecast_responses,
            total=total,
            skip=skip,
            limit=limit,
        )

    except Exception as e:
        logger.exception(f"Error retrieving forecasts: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error retrieving forecasts",
        )



