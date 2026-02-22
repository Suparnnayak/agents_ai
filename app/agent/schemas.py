"""Pydantic schemas for the Agent endpoint."""

from pydantic import BaseModel, Field


class AgentQueryRequest(BaseModel):
    """Request body for POST /agent/query."""

    question: str = Field(
        ...,
        min_length=5,
        max_length=500,
        description="Natural-language question about a hospital forecast. "
        "Must mention a hospital code (e.g. HOSP_1).",
        examples=[
            "Why is HOSP_3 forecast increasing over the next 7 days?",
            "Explain the admission trend for HOSP_1",
        ],
    )


class AgentQueryResponse(BaseModel):
    """Response body for POST /agent/query."""

    hospital: str = Field(..., description="Resolved hospital code")
    analysis: str = Field(..., description="LLM-generated analysis grounded in DB data")
    inference_time_seconds: float = Field(
        ..., description="Wall-clock time for the Groq API call"
    )

