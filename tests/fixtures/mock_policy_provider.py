from typing import Any

from src.security.policy import SecurityPolicy

class MockPolicyProvider:
    @staticmethod
    def for_workflow(self, *, workflow: str, user_id: str | None) -> Any:
        return SecurityPolicy(
            allowed_tools=set(),
            approval_required_tools=set(),
        )