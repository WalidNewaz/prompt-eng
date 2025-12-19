"""Prompt loader and version selector."""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]


class PromptNotFoundError(RuntimeError):
    pass


def load_prompt(module: str, version: str) -> str:
    """Load a prompt template by module and version.

    Args:
        module: Prompt module name (e.g. "notification").
        version: Version folder name (e.g. "v1").

    Returns:
        Prompt text.

    Raises:
        PromptNotFoundError: If the prompt file is missing.
    """
    print('BASE_DIR', BASE_DIR)
    prompt_path = BASE_DIR / 'prompts' / module / version / 'prompt.md'
    print('prompt_path', prompt_path)
    if not prompt_path.exists():
        raise PromptNotFoundError(f'Prompt not found: {module}/{version}')
    return prompt_path.read_text(encoding='utf-8')
