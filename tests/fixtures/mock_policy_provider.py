from typing import Any

from src.domain.policies import SecurityPolicy
from src.tools.schemas import ToolName

class MockPolicyProvider:
    def for_workflow(self, *, workflow: str, user_id: str | None) -> Any:
        return SecurityPolicy(
            allowed_tools={ToolName.SEND_SLACK_MESSAGE},
            approval_required_tools={ToolName.SEND_SLACK_MESSAGE},
        )