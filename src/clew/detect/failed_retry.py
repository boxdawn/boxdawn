# Spec: docs/FAILED_RETRY_DETECTOR_PREREG.md (frozen).
"""Failed Retry Detector — a tool call failed, and the next call to the same
tool failed again.

OpenTelemetry / OpenInference traces only (prereg §0): on Claude Code the
same rule counts consecutive failing shell commands, which the TRAIL
validation (`FAILED_RETRY_PREREG.md` §9) says nothing about.

A count. No cost is attached and nothing here feeds the waste totals.
"""
from __future__ import annotations

from clew.model import Span, Trace

# `trace.metadata["source"]` of the three OpenTelemetry entry points (prereg §1).
OTEL_SOURCES = frozenset({"otel_json", "openinference_json", "otel_adapter"})


def find_failed_retries(trace: Trace) -> list[tuple[Span, Span]]:
    """Adjacent tool calls `(a, b)` where both failed and `b` calls `a`'s tool.

    Tool spans are taken in `(start_time, span_id)` order. Failure is
    `trace.metadata["error_span_ids"]`, which the adapter fills from span
    status. Returns `[]` for any source outside `OTEL_SOURCES`.
    """
    if trace.metadata.get("source") not in OTEL_SOURCES:
        return []
    failed = set(trace.metadata.get("error_span_ids") or [])
    if not failed:
        return []
    tools = sorted(
        (s for s in trace.spans if s.span_kind == "tool"),
        key=lambda s: (s.start_time, s.span_id),
    )
    return [
        (a, b)
        for a, b in zip(tools, tools[1:])
        if a.span_id in failed
        and b.span_id in failed
        and a.agent_or_node_id == b.agent_or_node_id
    ]
