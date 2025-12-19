# Prompt Execution Harness: Schemas + Tool Calling + Real Tool Execution (FastAPI)

This repo is a minimal, production-minded harness that demonstrates:

- Tool calling using a strict `ToolCall` envelope (`name` + `arguments`)
- Real schema validation of tool arguments and results using Pydantic
- Real tool execution via HTTP calls to a FastAPI "internal tools" service
- Test coverage for schema validation and end-to-end execution

## Run the tool server

```bash
poetry run uvicorn app.server.fastapi_tool_server:app --reload --port 8001
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

