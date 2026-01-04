from typing import Protocol, Any


class PromptStore(Protocol):
    def get_prompt(self, *, workflow: str, module: str, version: str) -> str:
        ...

    def get_schema(self, *, workflow: str, module: str, version: str) -> dict[str, Any]:
        ...
