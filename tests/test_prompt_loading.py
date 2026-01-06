from src.ai.prompts.loader import load_prompt, PromptNotFoundError
import pytest


def test_load_prompt_ok() -> None:
    content = load_prompt('notification', 'v1')
    assert 'AVAILABLE TOOLS' in content


def test_load_prompt_missing() -> None:
    with pytest.raises(PromptNotFoundError):
        load_prompt('does-not-exist', 'v1')
