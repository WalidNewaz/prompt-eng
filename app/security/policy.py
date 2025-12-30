"""Security policy for tool calling.

Core principles:
- Allowlist tools per workflow (principle of least privilege)
- Enforce size limits (avoid prompt stuffing, tool abuse)
- Sanitize user input before injecting into prompts
- Reject/contain suspicious instructions inside user data
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.schemas import ToolName
from app.security.policy_decision import PolicyDecision, PolicyOutcome

_INJECTION_PATTERNS = [
    r'(?i)\bignore\b.*\binstructions\b',
    r'(?i)\bdisregard\b.*\bsystem\b',
    r'(?i)\byou are now\b',
    r'(?i)\bact as\b.*\bsystem\b',
    r'(?i)\breveal\b.*\bprompt\b',
    r'(?i)\bexfiltrate\b',
]

_MAX_USER_CHARS = 4000
_MAX_MESSAGE_CHARS = 2000


class PolicyViolation(Exception):
    def __init__(self, tool: ToolName, workflow: str):
        self.tool = tool
        self.workflow = workflow
        super().__init__(f"Tool '{tool.value}' not allowed in workflow '{workflow}'")


@dataclass(frozen=True)
class SecurityPolicy:
    allowed_tools: set[ToolName]
    approval_required_tools: set[ToolName]

    def is_allowed(self, tool: ToolName) -> bool:
        if len(self.allowed_tools) > 0 and tool not in self.allowed_tools:
            return False
        if len(self.approval_required_tools) > 0 and tool not in self.approval_required_tools:
            return False
        return True

    def evaluate_tool(self, tool: ToolName) -> PolicyDecision:
        if tool not in self.allowed_tools:
            return PolicyDecision(
                outcome=PolicyOutcome.DENY,
                tool=tool,
                reason=f"Tool '{tool.value}' not allowed by policy"
            )

        if tool in self.approval_required_tools:
            return PolicyDecision(
                outcome=PolicyOutcome.REQUIRE_APPROVAL,
                tool=tool,
                reason=f"Tool '{tool.value}' requires human approval"
            )

        return PolicyDecision(outcome=PolicyOutcome.ALLOW)

    def assert_tool_allowed(self, tool: ToolName, workflow: str) -> None:
        if tool not in self.allowed_tools:
            raise PolicyViolation(tool, workflow)


def sanitize_user_text(user_text: str) -> str:
    """Sanitize and bound user text before inserting into prompts."""
    text = user_text.strip()
    if len(text) > _MAX_USER_CHARS:
        text = text[:_MAX_USER_CHARS] + '…'

    # Neutralize common injection vectors (we do NOT try to be perfect; we try to be safe-by-default)
    for pat in _INJECTION_PATTERNS:
        if re.search(pat, text):
            # Replace suspicious fragments with a marker; orchestrator can also route to request_missing_info
            text = re.sub(pat, '[POTENTIALLY_MALICIOUS_INSTRUCTION_REMOVED]', text)

    return text


def sanitize_message(text: str) -> str:
    """Bound outgoing message bodies (Slack/email) to reduce abuse and payload surprises."""
    t = text.strip()
    if len(t) > _MAX_MESSAGE_CHARS:
        t = t[:_MAX_MESSAGE_CHARS] + '…'
    return t


def build_policy_for_workflow(workflow: str) -> SecurityPolicy:
    """Define least-privilege tool access per workflow."""
    if workflow == 'notification_router':
        return SecurityPolicy(
            allowed_tools={
                ToolName.SEND_SLACK_MESSAGE,
                ToolName.SEND_EMAIL,
                ToolName.REQUEST_MISSING_INFO,
            },
            approval_required_tools=set(),
        )
    if workflow == "incident_broadcast":
        return SecurityPolicy(
            allowed_tools={
                ToolName.SEND_SLACK_MESSAGE,
                ToolName.SEND_EMAIL,
                ToolName.REQUEST_MISSING_INFO,
            },
            approval_required_tools={
                ToolName.SEND_SLACK_MESSAGE,
                ToolName.SEND_EMAIL,
            },
        )

    # Default: no tools
    return SecurityPolicy(
        allowed_tools=set(),
        approval_required_tools=set(),
    )


def assert_all_tools_allowed(
        policy: SecurityPolicy,
        tools: Iterable[ToolName],
        workflow: str
) -> None:
    for t in tools:
        policy.assert_tool_allowed(t, workflow=workflow)

def evaluate_plan(
    policy: SecurityPolicy,
    tools: Iterable[ToolName],
) -> list[PolicyDecision]:
    return [policy.evaluate_tool(t) for t in tools]