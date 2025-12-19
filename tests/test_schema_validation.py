from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas import ToolName, validate_tool_args, validate_tool_call_payload, validate_tool_result


def test_validate_tool_call_payload_ok() -> None:
    # Arrange
    payload = {'name': 'send_email', 'arguments': {'to': 'dev@example.com', 'subject': 'Hi', 'body': 'Yo'}}

    # Act
    tool_call = validate_tool_call_payload(payload)

    # Assert
    assert tool_call.name == ToolName.SEND_EMAIL
    assert tool_call.arguments['subject'] == 'Hi'


def test_validate_tool_call_payload_rejects_unknown_tool_name() -> None:
    # Arrange
    payload = {'name': 'delete_production', 'arguments': {}}

    # Act / Assert
    with pytest.raises(ValidationError):
        validate_tool_call_payload(payload)


def test_validate_tool_args_email_rejects_invalid_email() -> None:
    # Arrange
    args = {'to': 'not-an-email', 'subject': 'S', 'body': 'B'}

    # Act / Assert
    with pytest.raises(ValidationError):
        validate_tool_args(ToolName.SEND_EMAIL, args)


def test_validate_tool_result_rejects_wrong_shape() -> None:
    # Arrange: missing provider_message_id for send_email result
    bad_result = {'ok': True, 'tool': 'send_email'}

    # Act / Assert
    with pytest.raises(ValidationError):
        validate_tool_result(ToolName.SEND_EMAIL, bad_result)
