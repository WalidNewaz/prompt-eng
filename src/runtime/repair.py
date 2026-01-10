"""Repair prompt builder.

A repair prompt is used when model output fails validation (invalid JSON, missing fields, etc.).
The repair prompt should include:
- the validation error
- the invalid output
- the original prompt contract
"""

from __future__ import annotations


def build_repair_prompt(
    original_prompt: str,
    invalid_output_text: str,
    error_message: str,
    attempt: int,
    max_retries: int,
) -> str:
    """Construct a repair prompt to fix invalid model output.

    Args:
        original_prompt: The original rendered prompt.
        attempt: The number of attempts to repair the prompt.
        max_retries: The maximum number of attempts to repair the prompt.
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
{invalid_output_text}

ATTEMPTS:
This is repair attempt #{attempt + 1} of {max_retries}.

INSTRUCTIONS:
- Return ONLY ONE valid JSON object with keys: "name" and "arguments"
- Do not include any additional keys
- Do not include prose
- Choose "request_missing_info" if required fields are missing
- Do NOT change the intent or tool choice unless required to fix the error.

ORIGINAL PROMPT:
{original_prompt}
""".strip()
