"""
CLI entrypoint to run the autonomous agent pipeline end-to-end.

Example:
    python -m agents.run_pipeline --payload-file samples/sample_request.json
"""

import json
from pathlib import Path
from typing import Optional

import typer
from rich import print_json
from rich.console import Console

from .advisory_agent import run_advisory_agent
from .config import get_settings
from .coordinator_agent import assemble_operational_plan
from .monitor_agent import run_monitor_agent
from .planning_agent import run_staffing_planner, run_supplies_planner
from .prediction_client import prediction_client
from .schemas import AgentTraceEntry, MonitorInput

app = typer.Typer(help="Run the hospital agent pipeline.")
console = Console()


def _derive_monitor_inputs(record: dict, disease_sensitivity: float) -> MonitorInput:
    weather_risk = min(
        1.0,
        (record.get("rainfall", 0) / 60.0)
        + max(record.get("temp", 0) - 35, 0) / 25.0
        + (record.get("humidity", 0) - 70) / 40.0,
    )
    festival_score = float(record.get("festival_flag", 0))
    return MonitorInput(
        aqi=float(record.get("aqi", 100)),
        festival_score=max(0.0, min(1.0, festival_score)),
        weather_risk=max(0.0, min(1.0, weather_risk)),
        disease_sensitivity=max(0.0, min(1.0, disease_sensitivity)),
    )


@app.command()
def run(
    payload_file: Path = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Path to JSON payload for the prediction API.",
    ),
    hospital_id: str = typer.Option("HOSP-001", help="Hospital identifier."),
    disease_sensitivity: float = typer.Option(
        0.5,
        min=0.0,
        max=1.0,
        help="Sensitivity score for vulnerable patients.",
    ),
    save_artifact: Optional[Path] = typer.Option(
        None,
        help="Optional path to save the final operational plan JSON.",
    ),
):
    """Execute the complete agent workflow."""

    with payload_file.open() as f:
        payload = json.load(f)

    inferred_payload = dict(payload)
    inferred_payload.setdefault("mode", "ensemble")

    predicted_inflow = prediction_client.predict(inferred_payload)

    record = inferred_payload["data"][0]
    monitor_inputs = _derive_monitor_inputs(record, disease_sensitivity)

    trace = [AgentTraceEntry(agent="prediction_api", message="Fetched predictions")]

    monitor_report = run_monitor_agent(monitor_inputs)
    trace.append(AgentTraceEntry(agent="monitor", message=f"Alert {monitor_report.alertLevel}"))

    staffing = run_staffing_planner(predicted_inflow)
    trace.append(AgentTraceEntry(agent="staffing_planner", message="Staffing plan ready"))

    supplies = run_supplies_planner(predicted_inflow)
    trace.append(AgentTraceEntry(agent="supplies_planner", message="Supplies plan ready"))

    advisory = run_advisory_agent(predicted_inflow, monitor_report)
    trace.append(AgentTraceEntry(agent="advisory", message="Advisory drafted"))

    plan = assemble_operational_plan(
        hospital_id=hospital_id,
        predicted_inflow=predicted_inflow,
        monitor_report=monitor_report,
        staffing=staffing,
        supplies=supplies,
        advisory=advisory,
        trace=trace,
    )

    console.rule("[bold green]Operational Plan")
    print_json(plan.model_dump_json(indent=2))

    if save_artifact:
        save_artifact.parent.mkdir(parents=True, exist_ok=True)
        save_artifact.write_text(plan.model_dump_json(indent=2))
        console.print(f"[green]Saved plan to {save_artifact}")


if __name__ == "__main__":
    get_settings()  # warm up config/env
    app()

