from typing import Iterable, Protocol, Any

from src.core.observability import Span, log_event

from .workflows import ExecutionRecord, PlannedToolCall
from .harness import ToolExecutionError
from src.tools.schemas import ToolName
from src.domain.policies import sanitize_message

class ToolHarness(Protocol):
    async def run_tool_call(self, tool_call: dict) -> dict: ...


class Policy(Protocol):
    def assert_tool_allowed(self, tool_name): ...


class PlanExecutor:
    """
    Executes a planned DAG of tool calls.

    Responsibilities:
    - Enforce policy constraints
    - Sanitize tool arguments
    - Execute tool calls via a harness
    - Support limited parallelism via parallel groups
    - Produce ExecutionRecord objects

    Non-responsibilities:
    - Planning
    - Approval workflows
    - Retries
    - Scheduling across machines
    """

    def __init__(self, *, harness: ToolHarness):
        self._harness = harness

    async def execute(
        self,
        *,
        trace_id: str,
        steps: list[PlannedToolCall],
        policy: Policy,
    ) -> list[ExecutionRecord]:
        """
        Execute a tool plan consisting of sequential steps
        and parallel groups.

        Execution order:
        1. All parallel groups (groups run sequentially, steps inside run concurrently)
        2. All sequential steps (one-by-one)

        Returns:
            A list of ExecutionRecord objects in deterministic order.
        """
        parallel_groups, sequential_steps = self._partition_steps(steps)

        records: list[ExecutionRecord] = []

        # Phase 1: parallel groups (group-by-group)
        for group_id, group_steps in parallel_groups.items():
            log_event(
                "dag.group.start",
                trace_id=trace_id,
                group=group_id,
                size=len(group_steps),
            )

            group_records = await self._execute_parallel_group(
                trace_id=trace_id,
                steps=group_steps,
                policy=policy,
            )

            records.extend(group_records)

            log_event(
                "dag.group.end",
                trace_id=trace_id,
                group=group_id,
                ok=all(r.ok for r in group_records),
            )

        # Phase 2: sequential steps
        for step in sequential_steps:
            record = await self._execute_single_step(
                trace_id=trace_id,
                step=step,
                policy=policy,
            )
            records.append(record)

        return records

    @staticmethod
    def _partition_steps(
        steps: Iterable[PlannedToolCall],
    ) -> tuple[dict[str, list[PlannedToolCall]], list[PlannedToolCall]]:
        """
        Split steps into parallel groups and sequential steps.
        """
        grouped: dict[str, list[PlannedToolCall]] = {}
        sequential: list[PlannedToolCall] = []

        for step in steps:
            if step.parallel_group:
                grouped.setdefault(step.parallel_group, []).append(step)
            else:
                sequential.append(step)

        return grouped, sequential

    async def _execute_parallel_group(
        self,
        *,
        trace_id: str,
        group_id: str,
        steps: list[PlannedToolCall],
        policy: Policy,
    ) -> list[ExecutionRecord]:
        """
        Execute all steps in a parallel group concurrently.
        """
        log_event('dag.group.start', trace_id=trace_id, group=group_id, size=len(steps))

        async def run(step: PlannedToolCall) -> ExecutionRecord:
            return await self._execute_single_step(
                trace_id=trace_id,
                step=step,
                policy=policy,
            )

        records = await self._gather_preserve_order([run(s) for s in steps])

        log_event(
            'dag.group.end',
            trace_id=trace_id,
            group=group_id,
            ok=all(r.ok for r in records),
        )

        return records

    async def _execute_single_step(
        self,
        *,
        trace_id: str,
        step: PlannedToolCall,
        policy: Policy,
    ) -> ExecutionRecord:
        """
        Execute a single tool step with policy enforcement,
        sanitization, tracing, and error handling.
        """
        log_event('dag.step.start', trace_id=trace_id, tool=step.name.value)

        policy.assert_tool_allowed(step.name)

        args = self._sanitize_args(step)

        tool_call = {
            "name": step.name.value,
            "arguments": args,
        }

        span = Span(name=f"tool.{step.name.value}", trace_id=trace_id)

        try:
            result = await self._harness.run_tool_call(tool_call)
            ok = bool(result.get("ok", False))
            return ExecutionRecord(
                name=step.name,
                ok=ok,
                result=result,
                parallel_group=step.parallel_group,
            )
        except ToolExecutionError as exc:
            return ExecutionRecord(
                name=step.name,
                ok=False,
                result={"ok": False, "error": str(exc)},
                parallel_group=step.parallel_group,
            )
        finally:
            span.end()
            log_event("span.end", trace_id=trace_id, span=span)


    @staticmethod
    def _sanitize_args(self, step: PlannedToolCall) -> dict[str, Any]:
        """
        Apply minimal sanitization for known tools.
        """
        args = dict(step.arguments)

        if step.name == ToolName.SEND_SLACK_MESSAGE and "text" in args:
            args["text"] = sanitize_message(str(args["text"]))

        if step.name == ToolName.SEND_EMAIL:
            if "subject" in args:
                args["subject"] = sanitize_message(str(args["subject"]))
            if "body" in args:
                args["body"] = sanitize_message(str(args["body"]))

        return args

    @staticmethod
    async def _gather_preserve_order(coros: list[Any]) -> list[Any]:
        """Gather coroutines concurrently while preserving input order."""
        # asyncio.gather preserves order by default, but keep a wrapper for clarity.
        import asyncio

        return await asyncio.gather(*coros)






