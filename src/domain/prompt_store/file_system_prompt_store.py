import json
from typing import Any
from pathlib import Path


class FilesystemPromptStore:
    """
    PromptStore backed by a local filesystem.

    Expected layout:
        prompts/
          <workflow>/
            <module>/
              <version>/
                prompt.md
                schema.json
    """

    def __init__(self, *, base_dir: Path) -> None:
        self._base_dir = base_dir

    def _base_path(self, workflow: str, module: str, version: str) -> Path:
        return self._base_dir / "prompts" / workflow / module / version

    def get_prompt(self, *, workflow: str, module: str, version: str) -> str:
        path = self._base_path(workflow, module, version) / "prompt.md"
        return path.read_text(encoding="utf-8")

    def get_schema(self, *, workflow: str, module: str, version: str) -> dict[str, Any]:
        path = self._base_path(workflow, module, version) / "schema.json"
        return json.loads(path.read_text(encoding="utf-8"))
