"""Prompt loader and version selector."""

from __future__ import annotations

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


class PromptNotFoundError(RuntimeError):
    pass


def load_prompt(module: str, version: str) -> str:
    """Load a prompt template by module and version."""
    prompt_path = BASE_DIR / 'prompts' / module / version / 'prompt.md'
    if not prompt_path.exists():
        raise PromptNotFoundError(f'Prompt not found: {module}/{version}')
    return prompt_path.read_text(encoding='utf-8')
