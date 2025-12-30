# app/security/policy_decision.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from app.schemas import ToolName


class PolicyOutcome(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


@dataclass(frozen=True)
class PolicyDecision:
    outcome: PolicyOutcome
    tool: Optional[ToolName] = None
    reason: Optional[str] = None
