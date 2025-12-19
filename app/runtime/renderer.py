"""Prompt renderer.

Responsible for safe placeholder replacement.
"""

from __future__ import annotations

from string import Template


class PromptRenderer:
    """Render prompt templates with strict placeholder rules."""

    def render(self, template: str, variables: dict[str, str]) -> str:
        try:
            return Template(template).substitute(variables)
        except KeyError as exc:
            raise ValueError(f'Missing prompt variable: {exc}') from exc
