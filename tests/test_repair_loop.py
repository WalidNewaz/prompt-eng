from src.runtime.repair import build_repair_prompt


def test_build_repair_prompt_contains_error() -> None:
    prompt = build_repair_prompt(
        original_prompt='PROMPT',
        invalid_output_text=str({'foo': 'bar'}),
        error_message='Invalid schema',
        attempt=0,
        max_retries=1,
    )
    assert 'Invalid schema' in prompt
    assert 'INVALID OUTPUT' in prompt
