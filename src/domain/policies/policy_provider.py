from typing import Protocol, Any

class PolicyProvider(Protocol):
    def for_workflow(self, *, workflow: str, user_id: str | None) -> Any:
        ...
