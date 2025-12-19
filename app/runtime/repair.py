"""Repair prompt builder.

A repair prompt is used when model output fails validation (invalid JSON, missing fields, etc.).
The repair prompt should include:
- the validation error
- the invalid output
- the original prompt contract
"""

from __future__ import annotations

from typing import Any


def build_repair_prompt(
    original_prompt: str,
    invalid_output: dict[str, Any],
    error_message: str,
) -> str:
    """Construct a repair prompt to fix invalid model output.

    Args:
        original_prompt: The original rendered prompt.
        invalid_output_text: The model's invalid output (raw text).
        error_message: Validation error details.

    Returns:
        A new prompt instructing the model to repair output into the required JSON shape.
    """
    return f"""
You previously produced an invalid tool call JSON.

ERROR:
{error_message}

INVALID OUTPUT (RAW TEXT):
{invalid_output}

INSTRUCTIONS:
- Return ONLY ONE valid JSON object with keys: "name" and "arguments"
- Do not include any additional keys
- Do not include prose
- Choose "request_missing_info" if required fields are missing

ORIGINAL PROMPT:
{original_prompt}
""".strip()
