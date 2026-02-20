"""
SQLAlchemy database models.

Production-grade models with UUID primary keys, foreign keys, and indexes.
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Date,
    DateTime,
    ForeignKey,
    Index,
    UniqueConstraint,
    Text,
    Boolean,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from database.base import Base


class User(Base):
    """
    User model for authentication (future use).
    """
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="analyst") # analyst, admin, superadmin
    is_active = Column(Boolean, default=True)

    # Relationships
    forecast_runs = relationship("ForecastRun", back_populates="user", cascade="all, delete-orphan")


class Hospital(Base):
    """
    Hospital information model.
    """
    __tablename__ = "hospitals"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    region = Column(String(100), nullable=True)
    capacity = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    admission_history = relationship("AdmissionHistory", back_populates="hospital", cascade="all, delete-orphan")
    forecasts = relationship("Forecast", back_populates="hospital", cascade="all, delete-orphan")
    external_signals = relationship("ExternalSignal", back_populates="hospital")
    
    # Indexes
    __table_args__ = (
        Index("idx_hospital_id", "hospital_id"),
    )


class AdmissionHistory(Base):
    """
    Historical hospital admissions data.
    """
    __tablename__ = "admission_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, nullable=False)
    admissions = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    hospital = relationship("Hospital", back_populates="admission_history")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_admission_hospital_date", "hospital_id", "date"),
        UniqueConstraint("hospital_id", "date", name="uq_hospital_date"),
    )


class ForecastRun(Base):
    """
    Metadata for each forecast run (batch of predictions).
    """
    __tablename__ = "forecast_runs"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    hospital_count = Column(Integer, nullable=False)
    horizon_count = Column(Integer, nullable=False)
    total_forecasts = Column(Integer, nullable=False)
    inference_time_seconds = Column(Float, nullable=True)
    model_version = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = relationship("User", back_populates="forecast_runs")
    forecasts = relationship("Forecast", back_populates="forecast_run", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_forecast_run_created", "created_at"),
        Index("idx_forecast_run_user", "user_id"),
    )


class Forecast(Base):
    """
    Individual forecast predictions.
    """
    __tablename__ = "forecasts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    forecast_run_id = Column(UUID(as_uuid=True), ForeignKey("forecast_runs.id", ondelete="CASCADE"), nullable=False)
    hospital_id = Column(UUID(as_uuid=True), ForeignKey("hospitals.id", ondelete="CASCADE"), nullable=False)
    horizon = Column(Integer, nullable=False)  # Days ahead (1-7)
    prediction = Column(Float, nullable=False)
    forecast_date = Column(Date, nullable=False)  # The date being forecasted
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    forecast_run = relationship("ForecastRun", back_populates="forecasts")
    hospital = relationship("Hospital", back_populates="forecasts")
    
    # Indexes and constraints
    __table_args__ = (
        Index("idx_forecast_hospital_date", "hospital_id", "forecast_date"),
        Index("idx_forecast_run", "forecast_run_id"),
        Index("idx_forecast_horizon", "horizon"),
        UniqueConstraint("hospital_id", "forecast_date", "horizon", name="uq_hospital_date_horizon"),
    )


class ExternalSignal(Base):
    """
    External exogenous signals fetched from free public APIs.
    """
    __tablename__ = "external_signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    hospital_id = Column(
        UUID(as_uuid=True),
        ForeignKey("hospitals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    date = Column(Date, nullable=False)
    temperature = Column(Float, nullable=False, default=0.0)
    aqi = Column(Float, nullable=False, default=0.0)
    outbreak_index = Column(Float, nullable=False, default=0.0)
    mobility_index = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    hospital = relationship("Hospital", back_populates="external_signals")

    __table_args__ = (
        Index("idx_external_signal_hospital_date", "hospital_id", "date"),
        UniqueConstraint("hospital_id", "date", name="uq_external_signal_hospital_date"),
    )

