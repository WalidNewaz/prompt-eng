# Prompt Execution Harness: Schemas + Tool Calling + Real Tool Execution (FastAPI + Chains + DAG + Observability + Security)

This repo is a minimal, production-minded harness that demonstrates:

- Tool calling using a strict `ToolCall` envelope (`name` + `arguments`)
- Real schema validation of tool arguments and results using Pydantic
- Real tool execution via HTTP calls to a FastAPI "internal tools" service
- Test coverage for schema validation and end-to-end execution
- Multi-step chains: Plan -> Execute -> Summarize
- DAG workflows (parallel tool calls + join)
- Observability: trace IDs + timing + structured logs
- Security boundaries: tool allowlists + input limits + sanitization
- OpenAI Responses API adapter (Responses only)

## Run the tool server

```bash
poetry run uvicorn src.main:app --reload --port 8001
```

## Run the harness demo (against the running server)

```bash
poetry run python -c "from app.runtime.harness import demo; demo('http://127.0.0.1:8001')"
```

## Run tests

```commandline
ruff check .
black --check .
pytest
```

## Run the live API demo (Responses API)

Export your API key (server-side only):

```commandline
export OPENAI_API_KEY="YOUR_KEY"
```

Run the demo:

```commandline
poetry run python -m app.scripts.live_demo \
    --tool-base-url http://127.0.0.1:8001 \
    --model gpt-4.1-mini \
    --user-id demo_user_001
```


