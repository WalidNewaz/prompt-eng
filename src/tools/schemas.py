"""Schemas for tool calling, arguments, and results.

This chapter uses Pydantic as "real schema validation":
- ToolCall envelopes are validated strictly.
- Each tool's argument model is validated before execution.
- Each tool's result model is validated after execution.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, EmailStr, Field, ValidationError


class ToolName(str, Enum):
    """Supported tool names in this chapter's harness."""

    SEND_SLACK_MESSAGE = 'send_slack_message'
    SEND_EMAIL = 'send_email'
    REQUEST_MISSING_INFO = 'request_missing_info'


class ToolCall(BaseModel):
    """A tool call envelope produced by an LLM (or a test fixture).

    Args:
        name: Tool name to execute.
        arguments: JSON object of tool arguments.

    Examples:
        >>> ToolCall.model_validate({"name": "send_email", "arguments": {"to": "a@b.com", "subject": "Hi", "body": "Yo"}})
        ToolCall(name=<ToolName.SEND_EMAIL: 'send_email'>, arguments={'to': 'a@b.com', 'subject': 'Hi', 'body': 'Yo'})
    """

    name: ToolName
    arguments: dict[str, Any] = Field(default_factory=dict)


class SlackUrgency(str, Enum):
    LOW = 'low'
    NORMAL = 'normal'
    HIGH = 'high'


class SendSlackMessageArgs(BaseModel):
    """Arguments for sending a Slack message via an internal tool service."""

    channel: str = Field(min_length=1, description='Slack channel like #alerts.')
    text: str = Field(min_length=1, description='Message text.')
    urgency: SlackUrgency = SlackUrgency.NORMAL


class SendEmailArgs(BaseModel):
    """Arguments for sending an email via an internal tool service."""

    to: EmailStr
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)


class RequestMissingInfoArgs(BaseModel):
    """Arguments for requesting missing info from the user."""

    missing_fields: list[str] = Field(min_length=1)
    question: str = Field(min_length=1)


class ToolResultBase(BaseModel):
    """Base class for tool results."""

    ok: bool


class SendSlackMessageResult(ToolResultBase):
    """Result of sending a Slack message."""

    tool: Literal['send_slack_message'] = 'send_slack_message'
    message_id: str


class SendEmailResult(ToolResultBase):
    """Result of sending an email."""

    tool: Literal['send_email'] = 'send_email'
    provider_message_id: str


class RequestMissingInfoResult(ToolResultBase):
    """Result of requesting missing information."""

    tool: Literal['request_missing_info'] = 'request_missing_info'
    prompt_to_user: str


def validate_tool_call_payload(payload: dict[str, Any]) -> ToolCall:
    """Validate an incoming tool call payload.

    Args:
        payload: Raw tool call JSON.

    Returns:
        Validated ToolCall.

    Raises:
        ValidationError: If the payload is invalid.
    """
    return ToolCall.model_validate(payload)


def validate_tool_args(tool_name: ToolName, args: dict[str, Any]) -> BaseModel:
    """Validate tool arguments for the given tool name.

    Args:
        tool_name: ToolName enum.
        args: Raw args dict.

    Returns:
        A validated Pydantic model instance for that tool's args.

    Raises:
        ValidationError: If args are invalid for the tool.
    """
    if tool_name == ToolName.SEND_SLACK_MESSAGE:
        return SendSlackMessageArgs.model_validate(args)
    if tool_name == ToolName.SEND_EMAIL:
        return SendEmailArgs.model_validate(args)
    if tool_name == ToolName.REQUEST_MISSING_INFO:
        return RequestMissingInfoArgs.model_validate(args)
    raise ValidationError.from_exception_data(
        'ToolValidationError',
        [{'loc': ('name',), 'msg': f'Unsupported tool name: {tool_name}', 'type': 'value_error'}],
    )


def validate_tool_result(tool_name: ToolName, result_payload: dict[str, Any]) -> ToolResultBase:
    """Validate a tool result payload for the given tool.

    Args:
        tool_name: ToolName enum.
        result_payload: Raw result JSON from the tool service.

    Returns:
        A validated result model.

    Raises:
        ValidationError: If the payload is invalid for the tool.
    """
    if tool_name == ToolName.SEND_SLACK_MESSAGE:
        return SendSlackMessageResult.model_validate(result_payload)
    if tool_name == ToolName.SEND_EMAIL:
        return SendEmailResult.model_validate(result_payload)
    if tool_name == ToolName.REQUEST_MISSING_INFO:
        return RequestMissingInfoResult.model_validate(result_payload)
    raise ValidationError.from_exception_data(
        'ToolResultValidationError',
        [{'loc': ('name',), 'msg': f'Unsupported tool name: {tool_name}', 'type': 'value_error'}],
    )
