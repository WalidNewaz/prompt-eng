from typing import Any

class FakePolicyProvider:
    def __init__(self, policy: Any):
        self._policy = policy

    def for_workflow(self, *, workflow: str, user_id: str | None) -> Any:
        return self._policy
