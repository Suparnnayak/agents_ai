"""Coordinator agent that aggregates all sub-agent outputs."""

import uuid
from datetime import datetime, timezone
from typing import List

from .schemas import (
    AdvisoryOutput,
    AgentTraceEntry,
    CoordinatorPlan,
    MonitorOutput,
    StaffingPlan,
    SuppliesPlan,
)


def _recommended_actions(
    monitor_report: MonitorOutput,
    staffing: StaffingPlan,
    supplies: SuppliesPlan,
) -> List[str]:
    actions = [
        f"Notify respiratory teams about alert level {monitor_report.alertLevel}",
        f"Stage {supplies.oxygenCylinders} oxygen cylinders near ER",
    ]
    if monitor_report.recommendedUrgency in {"activate surge", "emergency"}:
        actions.append("Activate surge bed protocol and inform city EMS")
    if staffing.doctorsNeeded > 40:
        actions.append("Call in locum physicians for night shift coverage")
    return actions


def assemble_operational_plan(
    *,
    hospital_id: str,
    predicted_inflow: float,
    monitor_report: MonitorOutput,
    staffing: StaffingPlan,
    supplies: SuppliesPlan,
    advisory: AdvisoryOutput,
    trace: List[AgentTraceEntry],
) -> CoordinatorPlan:
    """Assemble the final plan with metadata."""

    return CoordinatorPlan(
        requestId=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        hospitalId=hospital_id,
        predictedInflow=predicted_inflow,
        monitorReport=monitor_report,
        staffingPlan=staffing,
        suppliesPlan=supplies,
        advisory=advisory,
        recommendedActions=_recommended_actions(monitor_report, staffing, supplies),
        agentTrace=trace,
    )

