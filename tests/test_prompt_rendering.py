from src.runtime.prompt_renderer import PromptRenderer
import pytest


def test_prompt_rendering_ok() -> None:
    template = 'Hello ${name}'
    renderer = PromptRenderer()
    rendered = renderer.render(template, {'name': 'Alice'})
    assert rendered == 'Hello Alice'


def test_prompt_rendering_missing_variable() -> None:
    renderer = PromptRenderer()
    with pytest.raises(ValueError):
        renderer.render('Hello ${name}', {})
