"""
CRUD operations for database models.

Transaction-safe database operations for forecasts and related data.
"""

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, desc, func
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from uuid import UUID
import uuid

from database.models import (
    User, Hospital, AdmissionHistory, ForecastRun, Forecast
)


# ============================================================================
# Hospital CRUD
# ============================================================================

def get_hospital_by_id(db: Session, hospital_id: str) -> Optional[Hospital]:
    """Get hospital by hospital_id string."""
    return db.query(Hospital).filter(Hospital.hospital_id == hospital_id).first()


def get_or_create_hospital(db: Session, hospital_id: str, **kwargs) -> Hospital:
    """
    Get existing hospital or create new one.
    
    Args:
        db: Database session
        hospital_id: Hospital ID string
        **kwargs: Additional hospital fields (name, region, capacity)
    
    Returns:
        Hospital instance
    """
    hospital = get_hospital_by_id(db, hospital_id)
    if hospital:
        return hospital
    
    hospital = Hospital(
        hospital_id=hospital_id,
        name=kwargs.get("name"),
        region=kwargs.get("region"),
        capacity=kwargs.get("capacity")
    )
    db.add(hospital)
    db.flush()  # Flush to get ID without committing
    return hospital


def get_all_hospitals(db: Session, skip: int = 0, limit: int = 100) -> List[Hospital]:
    """Get all hospitals with pagination."""
    return db.query(Hospital).offset(skip).limit(limit).all()


# ============================================================================
# ForecastRun CRUD
# ============================================================================

def create_forecast_run(
    db: Session,
    hospital_count: int,
    horizon_count: int,
    total_forecasts: int,
    inference_time_seconds: Optional[float] = None,
    model_version: Optional[str] = None,
    user_id: Optional[UUID] = None
) -> ForecastRun:
    """
    Create a new forecast run record.
    
    Args:
        db: Database session
        hospital_count: Number of hospitals forecasted
        horizon_count: Number of horizons forecasted
        total_forecasts: Total number of forecast predictions
        inference_time_seconds: Time taken for inference
        model_version: Model version string
        user_id: Optional user ID
    
    Returns:
        ForecastRun instance
    """
    forecast_run = ForecastRun(
        user_id=user_id,
        hospital_count=hospital_count,
        horizon_count=horizon_count,
        total_forecasts=total_forecasts,
        inference_time_seconds=inference_time_seconds,
        model_version=model_version
    )
    db.add(forecast_run)
    db.flush()  # Flush to get ID without committing
    return forecast_run


def get_forecast_run(db: Session, run_id: UUID) -> Optional[ForecastRun]:
    """Get forecast run by ID."""
    return db.query(ForecastRun).filter(ForecastRun.id == run_id).first()


# ============================================================================
# Forecast CRUD
# ============================================================================

def create_forecast(
    db: Session,
    forecast_run_id: UUID,
    hospital_id: UUID,
    horizon: int,
    prediction: float,
    forecast_date: date
) -> Forecast:
    """
    Create a single forecast record.
    
    Args:
        db: Database session
        forecast_run_id: ID of the forecast run
        hospital_id: UUID of the hospital
        horizon: Forecast horizon (1-7 days)
        prediction: Predicted admissions value
        forecast_date: The date being forecasted
    
    Returns:
        Forecast instance
    """
    forecast = Forecast(
        forecast_run_id=forecast_run_id,
        hospital_id=hospital_id,
        horizon=horizon,
        prediction=prediction,
        forecast_date=forecast_date
    )
    db.add(forecast)
    return forecast


def create_forecasts_batch(
    db: Session,
    forecast_run_id: UUID,
    forecasts_data: List[Dict[str, Any]]
) -> List[Forecast]:
    """
    Create multiple forecast records in a batch.
    
    Args:
        db: Database session
        forecast_run_id: ID of the forecast run
        forecasts_data: List of dicts with keys: hospital_id (str), horizon, prediction, forecast_date
    
    Returns:
        List of Forecast instances
    """
    forecasts = []
    for data in forecasts_data:
        # Get or create hospital
        hospital = get_or_create_hospital(db, data["hospital_id"])
        
        # Create forecast
        forecast = create_forecast(
            db=db,
            forecast_run_id=forecast_run_id,
            hospital_id=hospital.id,
            horizon=data["horizon"],
            prediction=data["prediction"],
            forecast_date=data["forecast_date"]
        )
        forecasts.append(forecast)
    
    return forecasts


def get_forecasts(
    db: Session,
    hospital_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    horizon: Optional[int] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Forecast]:
    """
    Query forecasts with filtering and pagination.
    
    Args:
        db: Database session
        hospital_id: Filter by hospital ID string
        start_date: Filter forecasts >= start_date
        end_date: Filter forecasts <= end_date
        horizon: Filter by specific horizon (1-7)
        skip: Pagination offset
        limit: Pagination limit
    
    Returns:
        List of Forecast instances
    """
    query = db.query(Forecast)
    
    # Filter by hospital
    if hospital_id:
        hospital = get_hospital_by_id(db, hospital_id)
        if hospital:
            query = query.filter(Forecast.hospital_id == hospital.id)
        else:
            # Return empty if hospital not found
            return []
    
    # Filter by date range
    if start_date:
        query = query.filter(Forecast.forecast_date >= start_date)
    if end_date:
        query = query.filter(Forecast.forecast_date <= end_date)
    
    # Filter by horizon
    if horizon is not None:
        query = query.filter(Forecast.horizon == horizon)
    
    # Order by date (newest first) and apply pagination
    return query.order_by(desc(Forecast.forecast_date)).offset(skip).limit(limit).all()


def get_forecast_count(
    db: Session,
    hospital_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    horizon: Optional[int] = None
) -> int:
    """
    Get total count of forecasts matching filters.
    
    Args:
        db: Database session
        hospital_id: Filter by hospital ID string
        start_date: Filter forecasts >= start_date
        end_date: Filter forecasts <= end_date
        horizon: Filter by specific horizon (1-7)
    
    Returns:
        Total count
    """
    query = db.query(func.count(Forecast.id))
    
    # Filter by hospital
    if hospital_id:
        hospital = get_hospital_by_id(db, hospital_id)
        if hospital:
            query = query.filter(Forecast.hospital_id == hospital.id)
        else:
            return 0
    
    # Filter by date range
    if start_date:
        query = query.filter(Forecast.forecast_date >= start_date)
    if end_date:
        query = query.filter(Forecast.forecast_date <= end_date)
    
    # Filter by horizon
    if horizon is not None:
        query = query.filter(Forecast.horizon == horizon)
    
    return query.scalar() or 0


# ============================================================================
# AdmissionHistory CRUD (for future use)
# ============================================================================

def create_admission_history(
    db: Session,
    hospital_id: UUID,
    date: date,
    admissions: int
) -> AdmissionHistory:
    """Create admission history record."""
    admission = AdmissionHistory(
        hospital_id=hospital_id,
        date=date,
        admissions=admissions
    )
    db.add(admission)
    return admission

