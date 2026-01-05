from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict

class ReadinessOutcome(str, Enum):
    READY = "READY"
    NEEDS_INPUT = "NEEDS_INPUT"


@dataclass(frozen=True)
class ReadinessDecision:
    outcome: ReadinessOutcome
    missing_fields: Optional[Dict[str, list[str]]] = None
    reason: Optional[str] = None