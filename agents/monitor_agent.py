"""Monitor agent reading contextual risk signals."""

from textwrap import dedent

from .llm_client import llm_client
from .schemas import MonitorInput, MonitorOutput


MONITOR_PROMPT = dedent(
    """
    You are a hospital monitor agent. Evaluate environmental and seasonal risks.

    Inputs:
    - Air Quality Index (AQI): {aqi}
    - Festival score (0-1): {festival_score}
    - Weather risk (0-1): {weather_risk}
    - Disease sensitivity (0-1): {disease_sensitivity}

    Produce:
    - alertLevel: choose from ["low","moderate","high","critical"]
    - riskFactors: concise bullet topics (e.g., "AQI > 200", "Heat index")
    - recommendedUrgency: choose from ["monitor","prepare","activate surge","emergency"]
    """
)


def run_monitor_agent(inputs: MonitorInput) -> MonitorOutput:
    """Invoke the monitor agent."""

    return llm_client.generate_structured(
        prompt_template=MONITOR_PROMPT,
        schema=MonitorOutput,
        aqi=round(inputs.aqi, 2),
        festival_score=round(inputs.festival_score, 2),
        weather_risk=round(inputs.weather_risk, 2),
        disease_sensitivity=round(inputs.disease_sensitivity, 2),
    )

