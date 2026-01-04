from typing import Any

from src.schemas import ToolName
from src.security.policy import SecurityPolicy

class DefaultPolicyProvider:
    """
    PolicyProvider that delegates to existing policy builders.

    This keeps current behavior while making policy injectable.
    """

    def for_workflow(self, *, workflow: str, user_id: str | None) -> Any:
        # user_id is accepted for future RBAC/ABAC
        return self.build_policy_for_workflow(workflow)

    @staticmethod
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

