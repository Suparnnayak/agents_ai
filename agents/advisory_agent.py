"""Advisory agent that drafts public-facing and clinical guidance."""

from textwrap import dedent

from .llm_client import llm_client
from .schemas import AdvisoryOutput, MonitorOutput


ADVISORY_PROMPT = dedent(
    """
    You are the advisory agent for a hospital command center.

    Context:
    - Predicted inflow: {predicted_inflow} patients.
    - Alert level: {alert_level}
    - Risk factors: {risk_factors}

    Produce concise guidance:
    - publicAdvisory: Public safety message referencing pollution/weather.
    - triageRules: Short strategy for prioritizing patients.
    - teleconsultation: Recommendations for remote care load balancing.
    - pollutionCare: Advice for respiratory cases (masks, nebulizers, etc.).
    """
)


def run_advisory_agent(
    predicted_inflow: float,
    monitor_report: MonitorOutput,
) -> AdvisoryOutput:
    """Generate advisory content."""

    return llm_client.generate_structured(
        prompt_template=ADVISORY_PROMPT,
        schema=AdvisoryOutput,
        predicted_inflow=round(predicted_inflow, 1),
        alert_level=monitor_report.alertLevel,
        risk_factors=", ".join(monitor_report.riskFactors),
    )

