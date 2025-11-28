from datetime import datetime
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class MonitorInput(BaseModel):
    """Inputs for the monitor agent."""

    aqi: float = Field(..., ge=0)
    festival_score: float = Field(..., ge=0, le=1)
    weather_risk: float = Field(..., ge=0, le=1)
    disease_sensitivity: float = Field(..., ge=0, le=1)


class MonitorOutput(BaseModel):
    alertLevel: Literal["low", "moderate", "high", "critical"]
    riskFactors: List[str]
    recommendedUrgency: Literal["monitor", "prepare", "activate surge", "emergency"]


class StaffingPlan(BaseModel):
    doctorsNeeded: int
    nursesNeeded: int
    supportStaffNeeded: int


class SuppliesPlan(BaseModel):
    oxygenCylinders: int
    beds: int
    commonMedicines: List[str]
    specialMedicines: List[str]


class AdvisoryOutput(BaseModel):
    publicAdvisory: str
    triageRules: str
    teleconsultation: str
    pollutionCare: str


class AgentTraceEntry(BaseModel):
    agent: str
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CoordinatorPlan(BaseModel):
    requestId: str
    timestamp: datetime
    hospitalId: str
    predictedInflow: float
    monitorReport: MonitorOutput
    staffingPlan: StaffingPlan
    suppliesPlan: SuppliesPlan
    advisory: AdvisoryOutput
    recommendedActions: List[str]
    agentTrace: List[AgentTraceEntry]

