"""
Hospital Forecast API — DB-Driven Architecture

Production FastAPI application.
- NO CSV dependency
- Forecasts are precomputed by daily_forecast_job.py
- All data lives in PostgreSQL (Neon)
- Read-only forecast endpoints
- Vercel-serverless compatible (no file writes in requests,
  no background schedulers, stateless handlers)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Any
import os
import time
from pathlib import Path
from datetime import datetime, date, timedelta
from collections import defaultdict
import subprocess
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text

# ---------- lightweight internal imports (no ML libraries) ----------
from forecast_system.utils import get_logger
from database.session import get_db
from database import crud
from database.models import (
    User,
    Hospital,
    Forecast,
    ForecastRun,
    AdmissionHistory,
    ExternalSignal,
)
from app.auth.router import router as auth_router
from app.dependencies import get_current_user, require_admin
from app.services.external_data_service import (
    fetch_and_store_external_signals,
    get_latest_external_signals_by_hospital,
)

# NOTE: ModelBundle is imported lazily inside _load_model_bundle() so that
# the heavy ML stack (joblib, pandas, numpy, lightgbm, scikit-learn) is
# NOT required for the Vercel serverless deployment — where the API only
# serves pre-computed forecasts from the database.

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Module-level state — initialised once per cold start (Vercel or local)
# ---------------------------------------------------------------------------
MODEL_PATH = os.getenv(
    "MODEL_PATH", "models/forecast_system/lightgbm_final.pkl"
)

bundle: Any = None                    # Optional[ModelBundle] when ML libs are present
model_loaded_at: Optional[str] = None
model_path_used: Optional[str] = None


def _load_model_bundle() -> None:
    """
    Load the model bundle from disk (called once at cold start).

    This is fully optional.  If the ML libraries (joblib, lightgbm,
    scikit-learn …) are not installed — e.g. in Vercel serverless —
    the function logs a warning and returns.  All forecast endpoints
    serve pre-computed DB data and never touch the model.
    """
    global bundle, model_loaded_at, model_path_used

    try:
        from forecast_system.model_bundle import ModelBundle
    except ImportError as exc:
        logger.info(
            f"[SKIP] ML libraries not installed ({exc}) — "
            "model loading skipped.  All forecast endpoints still work "
            "(pre-computed data from DB)."
        )
        return

    project_root = Path(__file__).resolve().parent.parent

    candidate_paths = [
        Path(MODEL_PATH),                     # explicit / absolute
        project_root / MODEL_PATH,            # relative to project root
    ]

    for path in candidate_paths:
        path_str = str(path)
        if os.path.exists(path_str):
            try:
                bundle = ModelBundle.load(path_str)
                model_path_used = path_str
                model_loaded_at = datetime.now().isoformat()
                logger.info(f"[OK] Model loaded from: {path_str}")
            except Exception as load_exc:
                logger.warning(f"[WARN] Model load failed: {load_exc}")
            return

    logger.warning("[WARN] Model bundle not found — /model-info will be unavailable")


def _verify_db_connection() -> None:
    """
    Lightweight DB smoke-test at cold start.

    Does NOT call Base.metadata.create_all() — schema is managed
    exclusively by Alembic migrations.  This only opens one connection
    and runs ``SELECT 1`` to surface config errors early.
    """
    from database.session import SessionLocal

    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("[OK] Database connection verified")
    except Exception as exc:
        logger.warning(f"[WARN] Database connection failed: {exc}")


# Run once at module-import time so both local uvicorn and Vercel
# cold-starts get the same behavior without relying on ASGI lifespan.
_verify_db_connection()
_load_model_bundle()


# ---------------------------------------------------------------------------
# ASGI lifespan (kept for local uvicorn; Mangum uses lifespan="off")
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(application: FastAPI):
    # startup — already done at module level, nothing extra needed
    yield
    # shutdown — nothing to clean up


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001",
).split(",")

app = FastAPI(
    title="Hospital Forecast API",
    description="7-day hospital admissions forecasting system — DB-driven architecture",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS — origins driven by ALLOWED_ORIGINS env var
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# Include authentication routes
app.include_router(auth_router)

# Rate limiting (simple in-memory — resets on each cold start; fine for serverless)
rate_limit_store: defaultdict = defaultdict(list)
RATE_LIMIT_REQUESTS = 50
RATE_LIMIT_WINDOW = 60  # seconds


# ============================================================================
# UTILITY
# ============================================================================


def check_rate_limit(request: Request):
    """Simple rate limiting middleware."""
    client_ip = request.client.host
    now = time.time()
    rate_limit_store[client_ip] = [
        ts for ts in rate_limit_store[client_ip] if now - ts < RATE_LIMIT_WINDOW
    ]
    if len(rate_limit_store[client_ip]) >= RATE_LIMIT_REQUESTS:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {RATE_LIMIT_REQUESTS} requests per {RATE_LIMIT_WINDOW}s",
        )
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


# ============================================================================
# SCHEMAS
# ============================================================================


class ForecastRequest(BaseModel):
    """Request model for /predict (backward-compatible)."""

    hospital_ids: Optional[List[str]] = Field(
        None, description="List of hospital IDs to forecast"
    )
    horizons: Optional[List[int]] = Field(
        [1, 2, 3, 4, 5, 6, 7], description="Forecast horizons in days"
    )

    @validator("hospital_ids")
    def validate_hospital_ids(cls, v):
        if v is not None:
            if len(v) == 0:
                raise ValueError("hospital_ids cannot be empty list")
            if len(v) != len(set(v)):
                raise ValueError("hospital_ids contains duplicates")
        return v

    @validator("horizons")
    def validate_horizons(cls, v):
        if v is None or len(v) == 0:
            raise ValueError("horizons cannot be empty")
        if len(v) != len(set(v)):
            raise ValueError("horizons contains duplicates")
        for h in v:
            if h < 1:
                raise ValueError(f"horizon must be >= 1, got {h}")
            if h > 7:
                raise ValueError(f"horizon must be <= 7, got {h}")
        return sorted(v)


class HealthResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    status: str
    model_loaded: bool
    db_connected: bool


class ModelInfoResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    version: str = "1.0.0"
    trained_at: Optional[str] = None
    feature_count: int
    feature_columns: List[str]
    path: Optional[str] = None
    git_commit: Optional[str] = None


class SystemStatusResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    model_version: Optional[str] = None
    last_forecast_run: Optional[str] = None
    last_signal_update: Optional[str] = None
    hospitals_count: int = 0


class ExternalSignalsTaskResponse(BaseModel):
    status: str
    hospitals_total: int
    processed: int
    failed: int
    upserted: int


# ============================================================================
# BASIC ENDPOINTS
# ============================================================================


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "status": "Hospital Forecast API running",
        "version": "2.0.0",
        "architecture": "DB-driven, precomputed forecasts",
        "endpoints": {
            "/health": "Health check",
            "/hospitals": "List hospitals",
            "/forecast/latest": "Latest precomputed forecasts (GET)",
            "/forecast/history": "Admission history (GET)",
            "/system/status": "System status (GET)",
            "/predict": "Precomputed forecasts (POST, backward-compatible)",
            "/docs": "API documentation",
        },
    }


@app.get("/health", response_model=HealthResponse)
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        model_loaded=bundle is not None,
        db_connected=db_ok,
    )


# ============================================================================
# HOSPITALS (from DB, not CSV)
# ============================================================================


@app.get("/hospitals")
def list_hospitals(db: Session = Depends(get_db)):
    """List all available hospitals from database."""
    hospital_ids = crud.get_all_hospital_ids(db)
    return {"hospitals": hospital_ids, "count": len(hospital_ids)}


# ============================================================================
# FORECAST ENDPOINTS (read-only, precomputed)
# ============================================================================


@app.get("/forecast/latest")
def forecast_latest(
    hospitals: Optional[str] = Query(
        None, description="Comma-separated hospital IDs (e.g. HOSP_1,HOSP_2)"
    ),
    db: Session = Depends(get_db),
):
    """
    GET /forecast/latest — returns precomputed forecasts from the latest run.
    """
    latest_run = crud.get_latest_forecast_run(db)
    if not latest_run:
        raise HTTPException(
            status_code=404,
            detail="No forecast runs found. Run daily_forecast_job first.",
        )

    hospital_ids = None
    if hospitals:
        hospital_ids = [h.strip() for h in hospitals.split(",") if h.strip()]

    forecasts = crud.get_precomputed_forecasts(
        db=db,
        run_id=latest_run.id,
        hospital_ids=hospital_ids,
    )

    return {
        "run_id": str(latest_run.id),
        "model_version": latest_run.model_version,
        "created_at": latest_run.created_at.isoformat() if latest_run.created_at else None,
        "signal_date_used": str(latest_run.signal_date_used) if latest_run.signal_date_used else None,
        "forecasts": forecasts,
        "count": len(forecasts),
    }


@app.get("/forecast/history")
def forecast_history(
    hospitals: Optional[str] = Query(
        None, description="Comma-separated hospital IDs"
    ),
    days: int = Query(30, ge=1, le=365, description="Number of days of history"),
    db: Session = Depends(get_db),
):
    """
    GET /forecast/history — returns admission history from the database.
    """
    hospital_ids = None
    if hospitals:
        hospital_ids = [h.strip() for h in hospitals.split(",") if h.strip()]

    history = crud.get_admission_history_for_hospitals(
        db=db, hospital_ids=hospital_ids, days=days
    )

    return {"history": history, "count": len(history), "days": days}


@app.get("/system/status", response_model=SystemStatusResponse)
def system_status(db: Session = Depends(get_db)):
    """
    GET /system/status — returns system health summary.
    """
    # Latest forecast run
    latest_run = crud.get_latest_forecast_run(db)
    last_run_str = None
    model_version = None
    if latest_run:
        last_run_str = latest_run.created_at.isoformat() if latest_run.created_at else None
        model_version = latest_run.model_version

    # Latest external signal date
    signal_date = crud.get_latest_signal_date(db)
    signal_str = str(signal_date) if signal_date else None

    # Hospital count
    hosp_count = crud.get_hospital_count(db)

    return SystemStatusResponse(
        model_version=model_version,
        last_forecast_run=last_run_str,
        last_signal_update=signal_str,
        hospitals_count=hosp_count,
    )


# ============================================================================
# /predict — BACKWARD-COMPATIBLE (returns precomputed data, no live inference)
# ============================================================================


@app.post("/predict")
def predict(
    request: ForecastRequest,
    rate_limit: bool = Depends(check_rate_limit),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    POST /predict — Returns precomputed forecasts (backward-compatible).

    No live inference. Data comes from the latest forecast run in the DB.
    """
    start_time = time.time()

    # Get latest forecast run
    latest_run = crud.get_latest_forecast_run(db)
    if not latest_run:
        raise HTTPException(
            status_code=503,
            detail="No precomputed forecasts available. Waiting for daily forecast job.",
        )

    # Validate hospital_ids against DB
    available_hospitals = set(crud.get_all_hospital_ids(db))
    if not available_hospitals:
        raise HTTPException(status_code=503, detail="No hospitals in database")

    requested_hospital_ids = request.hospital_ids
    if requested_hospital_ids:
        unknown = set(requested_hospital_ids) - available_hospitals
        if unknown:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown hospital_ids: {sorted(unknown)}. Available: {sorted(available_hospitals)}",
            )
    else:
        requested_hospital_ids = sorted(available_hospitals)

    horizons = sorted(request.horizons) if request.horizons else [1, 2, 3, 4, 5, 6, 7]

    # Fetch precomputed forecasts
    forecasts = crud.get_precomputed_forecasts(
        db=db,
        run_id=latest_run.id,
        hospital_ids=requested_hospital_ids,
        horizons=horizons,
    )

    elapsed = time.time() - start_time

    logger.info(
        f"Predict (precomputed) | hospitals={len(requested_hospital_ids)} | "
        f"horizons={len(horizons)} | results={len(forecasts)} | time={elapsed:.3f}s"
    )

    return {
        "status": "success",
        "forecasts": forecasts,
        "count": len(forecasts),
        "metadata": {
            "hospitals_requested": len(requested_hospital_ids),
            "horizons_requested": len(horizons),
            "inference_time_seconds": round(elapsed, 3),
            "forecast_run_id": str(latest_run.id),
            "source": "precomputed",
        },
    }


# ============================================================================
# MODEL INFO
# ============================================================================


@app.get(
    "/model-info",
    response_model=ModelInfoResponse,
    dependencies=[Depends(require_admin)],
)
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


# ============================================================================
# STORED FORECASTS BROWSER (pagination)
# ============================================================================


class ForecastResponse(BaseModel):
    id: str
    hospital_id: str
    horizon: int
    prediction: float
    forecast_date: date
    created_at: datetime


class ForecastsListResponse(BaseModel):
    forecasts: List[ForecastResponse]
    total: int
    skip: int
    limit: int


@app.get("/forecasts", response_model=ForecastsListResponse)
def get_forecasts(
    hospital_id: Optional[str] = Query(None, description="Filter by hospital ID"),
    start_date: Optional[date] = Query(None, description="Filter >= start_date"),
    end_date: Optional[date] = Query(None, description="Filter <= end_date"),
    horizon: Optional[int] = Query(None, ge=1, le=7, description="Filter by horizon"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """Get stored forecasts with filtering and pagination."""
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
            forecasts=forecast_responses, total=total, skip=skip, limit=limit
        )
    except Exception as e:
        logger.exception(f"Error retrieving forecasts: {e}")
        raise HTTPException(status_code=500, detail="Error retrieving forecasts")


# ============================================================================
# EXTERNAL SIGNALS TASK
# ============================================================================


@app.post(
    "/tasks/fetch-external-signals",
    response_model=ExternalSignalsTaskResponse,
    dependencies=[Depends(require_admin)],
)
def run_fetch_external_signals_task(db: Session = Depends(get_db)):
    """Fetch external signals for all hospitals and upsert into DB."""
    try:
        summary = fetch_and_store_external_signals(db)
        return ExternalSignalsTaskResponse(
            status="success",
            hospitals_total=summary["hospitals_total"],
            processed=summary["processed"],
            failed=summary["failed"],
            upserted=summary["upserted"],
        )
    except Exception as e:
        logger.exception(f"External signal task failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch external signals")
