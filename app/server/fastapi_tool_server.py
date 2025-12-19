"""FastAPI "internal tools" service.

This stands in for a company's internal services:
- notifications service (email, Slack)
- ticketing service
- CRM actions
- workflow side effects

Important:
- The service validates inputs (Pydantic)
- Returns structured, schema-stable outputs
- Can be protected with auth, mTLS, or an API gateway in real deployments
"""

from __future__ import annotations

import uuid

from fastapi import FastAPI
from pydantic import BaseModel, EmailStr, Field

app = FastAPI(title='Internal Tool Service', version='1.0.0')


class SlackUrgency(str):
    pass


class SendSlackMessageIn(BaseModel):
    channel: str = Field(min_length=1)
    text: str = Field(min_length=1)
    urgency: str = Field(default='normal', pattern='^(low|normal|high)$')


class SendSlackMessageOut(BaseModel):
    ok: bool
    tool: str
    message_id: str


class SendEmailIn(BaseModel):
    to: EmailStr
    subject: str = Field(min_length=1)
    body: str = Field(min_length=1)


class SendEmailOut(BaseModel):
    ok: bool
    tool: str
    provider_message_id: str


class RequestMissingInfoIn(BaseModel):
    missing_fields: list[str] = Field(min_length=1)
    question: str = Field(min_length=1)


class RequestMissingInfoOut(BaseModel):
    ok: bool
    tool: str
    prompt_to_user: str


@app.post('/tools/send-slack', response_model=SendSlackMessageOut)
async def send_slack(payload: SendSlackMessageIn) -> SendSlackMessageOut:
    # In production, this might call Slack APIs or enqueue a job.
    return SendSlackMessageOut(ok=True, tool='send_slack_message', message_id=str(uuid.uuid4()))


@app.post('/tools/send-email', response_model=SendEmailOut)
async def send_email(payload: SendEmailIn) -> SendEmailOut:
    # In production, this might call SendGrid, SES, or an internal mail relay.
    return SendEmailOut(ok=True, tool='send_email', provider_message_id=f'msg_{uuid.uuid4()}')


@app.post('/tools/request-missing-info', response_model=RequestMissingInfoOut)
async def request_missing_info(payload: RequestMissingInfoIn) -> RequestMissingInfoOut:
    missing = ', '.join(payload.missing_fields)
    text = f'I need the following fields: {missing}. {payload.question}'
    return RequestMissingInfoOut(ok=True, tool='request_missing_info', prompt_to_user=text)
