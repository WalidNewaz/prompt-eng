class MockPromptStore:
    @staticmethod
    def get_prompt(self, *, workflow: str, module: str, version: str) -> str:
        return 'mock prompt'

    @staticmethod
    def get_schema(self, *, workflow: str, module: str, version: str) -> dict:
        return {}