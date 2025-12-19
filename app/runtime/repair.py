"""Repair loop logic."""

from __future__ import annotations

from typing import Any


def build_repair_prompt(
    original_prompt: str,
    invalid_output: dict[str, Any],
    error_message: str,
) -> str:
    """Construct a repair prompt to fix invalid model output."""
    return f"""
You previously produced an invalid tool call.

ERROR:
{error_message}

INVALID OUTPUT:
{invalid_output}

INSTRUCTIONS:
- Fix the output
- Return ONLY a valid tool call
- Follow the original rules strictly

ORIGINAL PROMPT:
{original_prompt}
""".strip()
