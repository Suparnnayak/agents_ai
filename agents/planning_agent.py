"""Planning agents for staffing and supplies."""

from textwrap import dedent

from .llm_client import llm_client
from .schemas import SuppliesPlan, StaffingPlan


STAFFING_PROMPT = dedent(
    """
    You are a hospital staffing planner. Base staffing on predicted patient inflow.

    Predicted inflow: {predicted_inflow} patients.

    Respond with valid JSON ONLY matching exactly:
    {{
      "doctorsNeeded": <int>,
      "nursesNeeded": <int>,
      "supportStaffNeeded": <int>
    }}

    Do not include explanations or markdown fences.
    Consider surge buffers when inflow > 250. Keep recommendations realistic for a large metro hospital.
    """
)


SUPPLIES_PROMPT = dedent(
    """
    You are a hospital supply planner. Plan consumables for the forecasted inflow.

    Predicted inflow: {predicted_inflow} patients.

    Respond with valid JSON ONLY matching exactly:
    {{
      "oxygenCylinders": <int>,
      "beds": <int>,
      "commonMedicines": ["...", "..."],
      "specialMedicines": ["...", "..."]
    }}

    Do not include explanations or markdown fences.
    """
)


def run_staffing_planner(predicted_inflow: float) -> StaffingPlan:
    """Return staffing plan."""

    return llm_client.generate_structured(
        prompt_template=STAFFING_PROMPT,
        schema=StaffingPlan,
        predicted_inflow=round(predicted_inflow, 1),
    )


def run_supplies_planner(predicted_inflow: float) -> SuppliesPlan:
    """Return supplies plan."""

    return llm_client.generate_structured(
        prompt_template=SUPPLIES_PROMPT,
        schema=SuppliesPlan,
        predicted_inflow=round(predicted_inflow, 1),
    )

