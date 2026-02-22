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
from datetime import date, timedelta
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

    # 3. Last 14 days admissions
    cutoff = date.today() - timedelta(days=14)
    admissions_rows = (
        db.query(AdmissionHistory)
        .filter(
            AdmissionHistory.hospital_id == hospital.id,
            AdmissionHistory.date >= cutoff,
        )
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
    "You are a hospital operations forecasting analyst. "
    "You must only use the structured data provided below. "
    "Do not hallucinate or invent numbers. "
    "If the data is insufficient to answer, say so explicitly."
)


def build_prompt(context: Dict[str, Any], question: str) -> str:
    """Assemble the user message from DB context and the user's question."""

    forecast_lines = "\n".join(
        f"  Day {f['horizon']} ({f['date']}): {f['prediction']} predicted admissions"
        for f in context["forecasts"]
    ) or "  (no forecast data available)"

    admission_lines = "\n".join(
        f"  {a['date']}: {a['admissions']} admissions"
        for a in context["admissions"]
    ) or "  (no recent admission data)"

    sig = context.get("external_signal", {})
    if sig:
        signal_block = (
            f"  Date: {sig['date']}\n"
            f"  Temperature: {sig['temperature']}\n"
            f"  AQI: {sig['aqi']}\n"
            f"  Outbreak index: {sig['outbreak_index']}\n"
            f"  Mobility index: {sig['mobility_index']}"
        )
    else:
        signal_block = "  (no external signal data)"

    return (
        f"Hospital: {context['hospital_name']} ({context['hospital_code']})\n"
        f"Region: {context.get('region') or 'N/A'}\n"
        f"Capacity: {context.get('capacity') or 'N/A'}\n"
        f"\n"
        f"--- Forecast (next 7 days) ---\n{forecast_lines}\n"
        f"\n"
        f"--- Last 14 days admissions ---\n{admission_lines}\n"
        f"\n"
        f"--- Latest external signals ---\n{signal_block}\n"
        f"\n"
        f"Question:\n{question}\n"
        f"\n"
        f"Instructions:\n"
        f"- Explain the trend clearly.\n"
        f"- Mention possible drivers based on the data above.\n"
        f"- Be concise but analytical.\n"
        f"- If the data is insufficient, say so explicitly."
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
        "temperature": 0.2,
        "max_tokens": 500,
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

