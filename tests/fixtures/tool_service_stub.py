# ------------------------------------------------------------------------------
# Shared stub transport for tool HTTP calls
# ------------------------------------------------------------------------------
from httpx import Response, Request, MockTransport
import json

def tool_service_stub(request: Request) -> Response:
    """
    Stubbed HTTP transport for the internal tool service.

    IMPORTANT:
    PromptToolHarness is responsible for attaching metadata like `tool`
    to the final result. The HTTP layer should ONLY return the tool payload,
    exactly as the real service would.
    """
    assert request.method == "POST"

    path = request.url.path
    payload = json.loads(request.content.decode("utf-8"))

    # --- send email ------------------------------------------------------------
    if path == "/tools/send-email":
        if "@" not in payload.get("to", ""):
            return Response(status_code=400, json={"error": "invalid email"})

        return Response(
            status_code=200,
            json={
                "ok": True,
                "provider_message_id": "msg_123456",
                "tool": "send_email",
            },
        )

    # --- send slack ------------------------------------------------------------
    if path == "/tools/send-slack":
        return Response(
            status_code=200,
            json={
                "ok": True,
                "channel": payload["channel"],
                "message_ts": "1712345678.000100",
                "tool": "send_slack_message",
                "message_id": payload["message_id"],
            },
        )

    return Response(status_code=404, json={"error": f"Unhandled path {path}"})