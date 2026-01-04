"""Prompt renderer (strict placeholder substitution).

We keep rendering separate so:
- it can be tested independently
- it can be reused across orchestrators
- prompt templates stay clean and diffable
"""

from __future__ import annotations

from string import Template


class PromptRenderer:
    """Render prompt templates with strict placeholder rules."""

    def render(self, template: str, variables: dict[str, str]) -> str:
        """Render a prompt template.

        Args:
            template: Prompt template containing ${var} placeholders.
            variables: Mapping of variable names to values.

        Returns:
            Rendered prompt.

        Raises:
            ValueError: If any required template variables are missing.
        """
        try:
            return Template(template).substitute(variables)
        except KeyError as exc:
            raise ValueError(f'Missing prompt variable: {exc}') from exc
