# ------------------------------------
# Readiness Check
# ------------------------------------

from src.tools.contracts import REQUIRED_FIELDS
from .entities import ReadinessOutcome, ReadinessDecision



def evaluate_readiness(plan) -> ReadinessDecision:
    missing = {}

    for step in plan.steps:
        required = REQUIRED_FIELDS.get(step.name.value, [])
        absent = [f for f in required if f not in step.arguments]

        if absent:
            missing.setdefault(step.name.value, []).extend(absent)

    if missing:
        return ReadinessDecision(
            outcome=ReadinessOutcome.NEEDS_INPUT,
            missing_fields=missing,
            reason="One or more steps are missing required inputs",
        )

    return ReadinessDecision(outcome=ReadinessOutcome.READY)
