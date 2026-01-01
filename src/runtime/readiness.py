# ------------------------------------
# Readiness Check
# ------------------------------------

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any
from src.tools.contracts import REQUIRED_FIELDS

class ReadinessOutcome(str, Enum):
    READY = "READY"
    NEEDS_INPUT = "NEEDS_INPUT"


@dataclass(frozen=True)
class ReadinessDecision:
    outcome: ReadinessOutcome
    missing_fields: Optional[Dict[str, list[str]]] = None
    reason: Optional[str] = None


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
