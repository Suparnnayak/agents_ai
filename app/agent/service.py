"""
Agent service — DB context fetching + Groq LLM call.

This module is intentionally self-contained:
  • fetch_agent_context()  — pulls live data from PostgreSQL
  • build_prompt()         — assembles a grounded system+user message
  • call_groq()            — sends the prompt to the Groq Chat API
"""

from __future__ import annotations

import os
import re
import time
from datetime import date
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
import httpx

# Ensure .env is loaded even if this module is imported before database.session
load_dotenv()
from fastapi import HTTPException, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from database.models import (
    AdmissionHistory,
    ExternalSignal,
    Forecast,
    ForecastRun,
    Hospital,
)
from forecast_system.utils import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Environment — read lazily so python-dotenv has time to load .env
# ---------------------------------------------------------------------------
GROQ_API_URL: str = "https://api.groq.com/openai/v1/chat/completions"


def _get_groq_api_key() -> str:
    return os.getenv("GROQ_API_KEY", "")


def _get_groq_model() -> str:
    return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


# ---------------------------------------------------------------------------
# Hospital code extraction
# ---------------------------------------------------------------------------

_HOSP_PATTERN = re.compile(r"HOSP_\d+", re.IGNORECASE)


def extract_hospital_code(text: str) -> Optional[str]:
    """Return the first HOSP_<n> code found in *text*, uppercased."""
    match = _HOSP_PATTERN.search(text)
    return match.group(0).upper() if match else None


# ---------------------------------------------------------------------------
# DB context fetching
# ---------------------------------------------------------------------------


def fetch_agent_context(db: Session, hospital_code: str) -> Dict[str, Any]:
    """
    Pull the data an analyst would need to explain a forecast.

    Returns a dict with keys:
        hospital_name, hospital_code, capacity, region,
        forecasts, admissions, external_signal

    Raises HTTP 404 if the hospital code does not exist.
    """

    # 1. Resolve hospital
    hospital: Optional[Hospital] = (
        db.query(Hospital)
        .filter(Hospital.hospital_id == hospital_code)
        .first()
    )
    if hospital is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hospital '{hospital_code}' not found in the database.",
        )

    # 2. Latest 7-day forecast
    latest_run: Optional[ForecastRun] = (
        db.query(ForecastRun)
        .order_by(desc(ForecastRun.created_at))
        .first()
    )
    forecasts: List[Dict[str, Any]] = []
    if latest_run:
        rows = (
            db.query(Forecast)
            .filter(
                Forecast.forecast_run_id == latest_run.id,
                Forecast.hospital_id == hospital.id,
            )
            .order_by(Forecast.horizon)
            .all()
        )
        forecasts = [
            {
                "horizon": f.horizon,
                "prediction": round(f.prediction, 1),
                "date": str(f.forecast_date),
            }
            for f in rows
        ]

    # 3. Most recent 14 admission records
    #    We fetch the latest 14 rows by date (not by calendar window) so
    #    the agent always has history even if the data isn't from "today".
    admissions_rows = (
        db.query(AdmissionHistory)
        .filter(AdmissionHistory.hospital_id == hospital.id)
        .order_by(desc(AdmissionHistory.date))
        .limit(14)
        .all()
    )
    admissions = [
        {"date": str(a.date), "admissions": a.admissions}
        for a in admissions_rows
    ]

    # 4. Latest external signal
    signal_row: Optional[ExternalSignal] = (
        db.query(ExternalSignal)
        .filter(ExternalSignal.hospital_id == hospital.id)
        .order_by(desc(ExternalSignal.date))
        .first()
    )
    external_signal: Dict[str, Any] = {}
    if signal_row:
        external_signal = {
            "date": str(signal_row.date),
            "temperature": signal_row.temperature,
            "aqi": signal_row.aqi,
            "outbreak_index": signal_row.outbreak_index,
            "mobility_index": signal_row.mobility_index,
        }

    return {
        "hospital_name": hospital.name or hospital_code,
        "hospital_code": hospital_code,
        "capacity": hospital.capacity,
        "region": hospital.region,
        "forecasts": forecasts,
        "admissions": admissions,
        "external_signal": external_signal,
    }


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

SYSTEM_MESSAGE = (
    "You are a senior hospital operations analyst writing a brief for hospital administrators.\n\n"
    "RULES:\n"
    "1. Use ONLY the structured data provided — never invent numbers.\n"
    "2. Be CONFIDENT and DIRECT. Do NOT say 'insufficient data' unless an entire "
    "data section is literally empty. The data you receive IS the complete picture.\n"
    "3. Provide ACTIONABLE recommendations — staffing, capacity, surge prep.\n"
    "4. Use specific numbers from the data to support every claim.\n"
    "5. Keep the response under 250 words. Use short paragraphs or bullet points.\n"
    "6. Never ask for more data. Never list what data you wish you had.\n"
    "7. Structure your response as: Trend Summary → Key Drivers → Recommendations."
)


def build_prompt(context: Dict[str, Any], question: str) -> str:
    """Assemble the user message from DB context and the user's question."""

    # --- Forecasts ---
    forecasts = context["forecasts"]
    forecast_lines = "\n".join(
        f"  Day {f['horizon']} ({f['date']}): {f['prediction']} predicted admissions"
        for f in forecasts
    ) or "  (no forecast data available)"

    # Pre-compute stats the LLM can cite directly
    forecast_stats = ""
    if forecasts:
        preds = [f["prediction"] for f in forecasts]
        forecast_stats = (
            f"  Summary: min={min(preds)}, max={max(preds)}, "
            f"avg={round(sum(preds)/len(preds), 1)}\n"
        )

    # --- Admissions ---
    admissions = context["admissions"]
    admission_lines = "\n".join(
        f"  {a['date']}: {a['admissions']} admissions"
        for a in admissions
    ) or "  (no recent admission data)"

    admission_stats = ""
    if admissions:
        vals = [a["admissions"] for a in admissions]
        trend_dir = "rising" if vals[0] > vals[-1] else "falling" if vals[0] < vals[-1] else "flat"
        admission_stats = (
            f"  Summary: min={min(vals)}, max={max(vals)}, "
            f"avg={round(sum(vals)/len(vals), 1)}, recent trend={trend_dir}\n"
        )

    # --- External signals ---
    sig = context.get("external_signal", {})
    if sig:
        aqi = sig.get("aqi", 0)
        aqi_level = (
            "Good" if aqi <= 50 else "Moderate" if aqi <= 100
            else "Unhealthy-Sensitive" if aqi <= 150 else "Unhealthy" if aqi <= 200
            else "Very Unhealthy" if aqi <= 300 else "Hazardous"
        )
        signal_block = (
            f"  Date: {sig['date']}\n"
            f"  Temperature: {sig['temperature']} C\n"
            f"  AQI: {sig['aqi']} ({aqi_level})\n"
            f"  Outbreak index: {sig['outbreak_index']} (0=none, 1=severe)\n"
            f"  Mobility index: {sig['mobility_index']} (0=lockdown, 1=full movement)"
        )
    else:
        signal_block = "  (no external signal data)"

    capacity = context.get("capacity") or "N/A"

    # --- Capacity utilisation hint ---
    util_hint = ""
    if forecasts and capacity != "N/A":
        peak = max(f["prediction"] for f in forecasts)
        util_pct = round(peak / capacity * 100, 1)
        util_hint = f"\nPeak forecast vs capacity: {peak}/{capacity} = {util_pct}% utilisation\n"

    return (
        f"Hospital: {context['hospital_name']} ({context['hospital_code']})\n"
        f"Region: {context.get('region') or 'N/A'}\n"
        f"Capacity: {capacity} beds\n"
        f"{util_hint}"
        f"\n"
        f"=== Forecast (next 7 days) ===\n{forecast_lines}\n{forecast_stats}"
        f"\n"
        f"=== Recent admissions (latest {len(admissions)} records) ===\n"
        f"{admission_lines}\n{admission_stats}"
        f"\n"
        f"=== Latest external signals ===\n{signal_block}\n"
        f"\n"
        f"QUESTION: {question}\n"
        f"\n"
        f"Respond with:\n"
        f"1. **Trend Summary** — What does the 7-day forecast show vs recent history?\n"
        f"2. **Key Drivers** — Which data points (AQI, temperature, outbreak, mobility, "
        f"seasonal patterns) explain the trend? Cite specific numbers.\n"
        f"3. **Recommendations** — Concrete actions: staffing adjustments, capacity "
        f"planning, departmental alerts. Be specific to the numbers."
    )


# ---------------------------------------------------------------------------
# Groq API call
# ---------------------------------------------------------------------------


def call_groq(system_msg: str, user_msg: str) -> tuple[str, float]:
    """
    Call the Groq Chat Completions API synchronously via httpx.

    Returns (analysis_text, inference_seconds).
    Raises HTTPException on failure.
    """
    api_key = _get_groq_api_key()
    model = _get_groq_model()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Agent service unavailable: GROQ_API_KEY is not configured.",
        )

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.3,
        "max_tokens": 700,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.time()
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(GROQ_API_URL, json=payload, headers=headers)
        elapsed = round(time.time() - start, 3)

        if resp.status_code != 200:
            logger.error(
                f"[AGENT] Groq API error {resp.status_code}: {resp.text[:300]}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Groq API returned {resp.status_code}. Please try again later.",
            )

        data = resp.json()
        analysis = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        if not analysis:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Groq API returned an empty response.",
            )

        logger.info(
            f"[AGENT] Groq response OK | model={model} | "
            f"tokens_in={data.get('usage', {}).get('prompt_tokens', '?')} | "
            f"tokens_out={data.get('usage', {}).get('completion_tokens', '?')} | "
            f"time={elapsed}s"
        )
        return analysis, elapsed

    except httpx.TimeoutException:
        elapsed = round(time.time() - start, 3)
        logger.error(f"[AGENT] Groq API timed out after {elapsed}s")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Groq API request timed out. Please try again.",
        )
    except HTTPException:
        raise  # re-raise our own exceptions
    except Exception as exc:
        elapsed = round(time.time() - start, 3)
        logger.error(f"[AGENT] Groq API unexpected error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to reach Groq API. Please try again later.",
        )

