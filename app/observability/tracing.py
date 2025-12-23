"""Minimal tracing primitives.

This keeps the tutorial dependency-light (no OpenTelemetry required),
but makes the architecture trace-ready.

In production, you'd likely export traces to an OTEL collector.
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Span:
    name: str
    trace_id: str
    span_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    start_ns: int = field(default_factory=time.time_ns)
    end_ns: int | None = None
    attributes: dict[str, Any] = field(default_factory=dict)

    def end(self) -> None:
        self.end_ns = time.time_ns()

    @property
    def duration_ms(self) -> float | None:
        if self.end_ns is None:
            return None
        return (self.end_ns - self.start_ns) / 1_000_000.0


def new_trace_id() -> str:
    return uuid.uuid4().hex


def log_event(event: str, *, trace_id: str, span: Span | None = None, **fields: Any) -> None:
    payload: dict[str, Any] = {'event': event, 'trace_id': trace_id, **fields}
    if span is not None:
        payload['span'] = {
            'name': span.name,
            'span_id': span.span_id,
            'duration_ms': span.duration_ms,
            'attributes': span.attributes,
        }
    print(json.dumps(payload, ensure_ascii=False))
