from __future__ import annotations

import argparse
import asyncio
import json

import httpx

from src.llm.openai_responses import OpenAIResponsesLLMClient
from src.runtime.harness import PromptToolHarness
from src.runtime.orchestrator import Orchestrator
from src.api.fastapi_tool_server import app as tool_app
from src.tools.http_tool import HttpToolExecutor


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--tool-base-url', required=True)
    parser.add_argument('--model', default='gpt-4.1')
    parser.add_argument('--user-id', default='demo_user_001')
    args = parser.parse_args()

    # Real OpenAI client (Responses API). Requires OPENAI_API_KEY in env.
    # Note: schemas for the LLM are loaded by orchestrator from prompts/.../schema.json,
    # and sent in the adapter when configured. For simplicity, this demo leaves adapter schema unset
    # and relies on our Pydantic validation + prompt constraints.
    llm = OpenAIResponsesLLMClient.from_env(model=args.model)

    # Internal tools: point to your FastAPI tool server on localhost:8001
    executor = HttpToolExecutor(base_url=args.tool_base_url)
    harness = PromptToolHarness(executor)

    orch = Orchestrator(llm=llm, harness=harness)

    user_request = (
        "Broadcast an incident: 'Production checkout errors increasing'. "
        "Send Slack to #alerts with high urgency and email dev@example.com with subject 'INCIDENT'."
    )

    result = await orch.run_incident_broadcast(
        user_request=user_request,
        user_id=args.user_id,
    )

    print("\n=== FINAL RESULT ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(main())
