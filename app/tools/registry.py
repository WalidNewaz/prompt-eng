"""
A canonical tool registry
"""

from app.schemas import ToolName

TOOL_REGISTRY = {
    ToolName.SEND_SLACK_MESSAGE.value: {
        "description": "Send a Slack message",
        "arguments": ["channel", "text", "urgency"],
    },
    ToolName.SEND_EMAIL.value: {
        "description": "Send an email",
        "arguments": ["to", "subject", "body"],
    },
    ToolName.REQUEST_MISSING_INFO.value: {
        "description": "Ask the user for missing information",
        "arguments": ["missing_fields", "question"],
    },
}
