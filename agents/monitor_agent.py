"""Monitor agent reading contextual risk signals."""

from textwrap import dedent

from langchain_core.exceptions import OutputParserException

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

    Produce a JSON object ONLY with these exact keys:
    - alertLevel: one of "low", "moderate", "high", "critical"
    - riskFactors: JSON array of short strings (e.g., ["AQI > 200", "Heat index"])
    - recommendedUrgency: one of "monitor", "prepare", "activate surge", "emergency"

    Do NOT return variable names like alert_level or risk_factors.
    Return a single valid JSON object, nothing else.
    """
)


def _rule_based_fallback(inputs: MonitorInput) -> MonitorOutput:
    """
    Deterministic fallback if the LLM output can't be parsed.
    Uses simple thresholds on AQI, weather, and festivals.
    """

    aqi = inputs.aqi
    festival = inputs.festival_score
    weather = inputs.weather_risk

    risk_factors = []

    if aqi >= 300:
        alert = "critical"
        urgency = "emergency"
        risk_factors.append("AQI >= 300 (hazardous air quality)")
    elif aqi >= 200:
        alert = "high"
        urgency = "activate surge"
        risk_factors.append("AQI >= 200 (very unhealthy)")
    elif aqi >= 150:
        alert = "moderate"
        urgency = "prepare"
        risk_factors.append("AQI >= 150 (unhealthy)")
    else:
        alert = "low"
        urgency = "monitor"

    if festival > 0.6:
        risk_factors.append("Major festival / crowding risk")
        if alert == "low":
            alert = "moderate"
            urgency = "prepare"

    if weather > 0.6:
        risk_factors.append("Adverse weather conditions")
        if alert == "low":
            alert = "moderate"
            urgency = "prepare"

    if not risk_factors:
        risk_factors.append("No major risk factors detected")

    return MonitorOutput(
        alertLevel=alert,
        riskFactors=risk_factors,
        recommendedUrgency=urgency,
    )


def run_monitor_agent(inputs: MonitorInput) -> MonitorOutput:
    """Invoke the monitor agent with robust fallback if LLM JSON parsing fails."""

    try:
        return llm_client.generate_structured(
            prompt_template=MONITOR_PROMPT,
            schema=MonitorOutput,
            aqi=round(inputs.aqi, 2),
            festival_score=round(inputs.festival_score, 2),
            weather_risk=round(inputs.weather_risk, 2),
            disease_sensitivity=round(inputs.disease_sensitivity, 2),
        )
    except OutputParserException:
        # If Groq (or any LLM) returns invalid JSON, fall back to safe rule-based logic
        return _rule_based_fallback(inputs)

