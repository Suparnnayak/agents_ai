"""
Agent router — POST /agent/query

Accepts a natural-language question that mentions a hospital code (HOSP_<n>),
fetches real DB data as context, and returns an LLM-generated analysis
from the Groq API.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database.session import get_db
from app.dependencies import get_current_user
from app.agent.schemas import AgentQueryRequest, AgentQueryResponse
from app.agent.service import (
    extract_hospital_code,
    fetch_agent_context,
    build_prompt,
    call_groq,
    SYSTEM_MESSAGE,
)
from forecast_system.utils import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/query", response_model=AgentQueryResponse)
def agent_query(
    body: AgentQueryRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    POST /agent/query

    Workflow:
        1. Extract hospital code from the question text
        2. Pull structured context from the database
        3. Build a grounded prompt (system + user message)
        4. Call Groq Chat Completions API
        5. Return the analysis

    Requires authentication (Bearer token).
    """

    # --- 1. Extract hospital code ---
    hospital_code = extract_hospital_code(body.question)
    if not hospital_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Could not find a hospital code in your question. "
                "Please include a code like HOSP_1, HOSP_2, etc."
            ),
        )

    logger.info(
        f"[AGENT] Query from user={current_user.email} | "
        f"hospital={hospital_code} | q={body.question[:80]}"
    )

    # --- 2. Fetch DB context ---
    context = fetch_agent_context(db, hospital_code)

    # --- 3. Build prompt ---
    user_message = build_prompt(context, body.question)

    # --- 4. Call Groq ---
    analysis, elapsed = call_groq(SYSTEM_MESSAGE, user_message)

    # --- 5. Return ---
    return AgentQueryResponse(
        hospital=hospital_code,
        analysis=analysis,
        inference_time_seconds=elapsed,
    )

