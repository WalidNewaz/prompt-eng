class InMemoryPromptStore:
    def __init__(self, prompts: dict[tuple[str, str, str], str], schemas: dict[tuple[str, str, str], dict]):
        self._prompts = prompts
        self._schemas = schemas

    def get_prompt(self, *, workflow: str, module: str, version: str) -> str:
        return self._prompts[(workflow, module, version)]

    def get_schema(self, *, workflow: str, module: str, version: str) -> dict:
        return self._schemas[(workflow, module, version)]
