from unittest.mock import AsyncMock, MagicMock

mock_summarizer = MagicMock()
mock_summarizer.summarize = AsyncMock(
    return_value={
        "ok": True,
        "summary": {"status": "ok"}
    }
)
