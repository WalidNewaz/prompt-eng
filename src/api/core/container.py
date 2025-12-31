# --------------------------------
# DI container
# --------------------------------
from functools import lru_cache

from src.config import settings
from src.llm.openai_responses import OpenAIResponsesLLMClient
from src.runtime.harness import PromptToolHarness
from src.runtime.orchestrator import Orchestrator
from src.tools.http_tool import HttpToolExecutor


class Container:
    def __init__(self):
        self._llm = OpenAIResponsesLLMClient.from_env(
            model=settings.openai_model,
            settings=settings
        )
        self._harness = PromptToolHarness(
            HttpToolExecutor(base_url=settings.tool_base_url)
        )
        self._orchestrator = Orchestrator(
            llm=self._llm,
            harness=self._harness,
            # approval_repository=get_approval_repo(),
        )


    @property
    def orchestrator(self):
        return self._orchestrator


@lru_cache
def get_container():
    return Container()