"""tests/autofix/test_tool_cache.py — Stage 4 Phase 1 suppression + counting.

Design: docs/STAGE4_AUTOFIX_DESIGN.md Phase 1. The cache key and the
invalidation gates are the detector's, reused rather than copied, so what
gets fixed and what gets counted are the same rule.
"""
from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

langchain_core = pytest.importorskip(
    "langchain_core", reason="autofix sits on the [adapter] extra"
)
from langchain_core.tools import BaseTool  # noqa: E402

from clew.autofix import ToolCache  # noqa: E402


class _Args(BaseModel):
    file_path: str = ""
    command: str = ""


def _tool(nm: str, runs: dict[str, int], *, status: str | None = None) -> BaseTool:
    class _Impl(BaseTool):
        name: str = nm
        description: str = f"{nm} tool"
        args_schema: type = _Args

        def _run(self, file_path: str = "", command: str = "", **kw):
            runs[nm] = runs.get(nm, 0) + 1
            target = file_path or command
            body = f"{nm}:{target}:run{runs[nm]}"
            return body if status is None else _Result(body, status)

    return _Impl()


class _Result:
    """Stand-in for a tool result that carries a status, like ToolMessage."""

    def __init__(self, content: str, status: str) -> None:
        self.content = content
        self.status = status


def test_second_read_of_the_same_target_does_not_run_the_tool():
    runs: dict[str, int] = {}
    cache = ToolCache()
    (read,) = cache.wrap([_tool("Read", runs)])

    first = read.invoke({"file_path": "/x/a.txt"})
    second = read.invoke({"file_path": "/x/a.txt"})

    assert runs["Read"] == 1
    assert second == first
    assert cache.report().suppressed_tool_calls_count == 1


def test_a_write_to_that_target_sends_the_next_read_back_to_the_tool():
    runs: dict[str, int] = {}
    cache = ToolCache()
    read, write = cache.wrap([_tool("Read", runs), _tool("Write", runs)])

    read.invoke({"file_path": "/x/a.txt"})
    write.invoke({"file_path": "/x/a.txt"})
    read.invoke({"file_path": "/x/a.txt"})

    assert runs["Read"] == 2
    assert cache.report().suppressed_tool_calls_count == 0


def test_a_write_elsewhere_leaves_the_cached_target_alone():
    runs: dict[str, int] = {}
    cache = ToolCache()
    read, write = cache.wrap([_tool("Read", runs), _tool("Write", runs)])

    read.invoke({"file_path": "/x/a.txt"})
    write.invoke({"file_path": "/x/other.txt"})
    read.invoke({"file_path": "/x/a.txt"})

    assert runs["Read"] == 1
    assert cache.report().suppressed_tool_calls_count == 1


def test_a_shell_call_drops_everything_because_its_payload_is_opaque():
    runs: dict[str, int] = {}
    cache = ToolCache()
    read, bash = cache.wrap([_tool("Read", runs), _tool("Bash", runs)])

    read.invoke({"file_path": "/x/a.txt"})
    read.invoke({"file_path": "/x/b.txt"})
    bash.invoke({"command": "touch anything"})
    read.invoke({"file_path": "/x/a.txt"})
    read.invoke({"file_path": "/x/b.txt"})

    assert runs["Read"] == 4
    rep = cache.report()
    assert rep.suppressed_tool_calls_count == 0
    assert rep.cache_entries_dropped_count == 2


def test_the_two_invalidation_numbers_are_different_units():
    """One firing can drop many entries, so one count cannot stand for both."""
    runs: dict[str, int] = {}
    cache = ToolCache()
    read, bash = cache.wrap([_tool("Read", runs), _tool("Bash", runs)])

    read.invoke({"file_path": "/x/a.txt"})
    read.invoke({"file_path": "/x/b.txt"})
    read.invoke({"file_path": "/x/c.txt"})
    bash.invoke({"command": "ls"})

    rep = cache.report()
    assert rep.cache_invalidation_events == 1
    assert rep.cache_entries_dropped_count == 3


def test_a_failed_result_is_not_cached():
    runs: dict[str, int] = {}
    cache = ToolCache()
    (read,) = cache.wrap([_tool("Read", runs, status="error")])

    read.invoke({"file_path": "/x/a.txt"})
    read.invoke({"file_path": "/x/a.txt"})

    assert runs["Read"] == 2
    assert cache.report().suppressed_tool_calls_count == 0


def test_a_non_read_tool_is_passed_straight_through():
    runs: dict[str, int] = {}
    cache = ToolCache()
    (write,) = cache.wrap([_tool("Write", runs)])

    write.invoke({"file_path": "/x/a.txt"})
    write.invoke({"file_path": "/x/a.txt"})

    assert runs["Write"] == 2
    assert cache.report().not_cacheable_count == 2


def test_the_model_still_sees_the_same_tool():
    runs: dict[str, int] = {}
    original = _tool("Read", runs)
    (wrapped,) = ToolCache().wrap([original])

    assert wrapped.name == original.name
    assert wrapped.description == original.description
    assert wrapped.args_schema is original.args_schema


def test_the_report_leads_with_the_number_and_names_its_population():
    runs: dict[str, int] = {}
    cache = ToolCache(window="2026-10-08 session")
    (read,) = cache.wrap([_tool("Read", runs)])
    read.invoke({"file_path": "/x/a.txt"})
    read.invoke({"file_path": "/x/a.txt"})

    rendered = cache.report().render()
    assert rendered.splitlines()[0].strip().startswith("1 tool call avoided")
    assert "2026-10-08 session" in rendered


def test_phase_1_reports_no_token_or_dollar_figure():
    """Serving the cached content leaves it in the conversation, so the input
    tokens are still shipped. Only the tool run was avoided."""
    fields = set(ToolCache().report().__dataclass_fields__)

    assert not {f for f in fields if "token" in f or "cost" in f or "usd" in f}


def test_ainvoke_suppresses_too():
    """Driven with asyncio.run — pytest-asyncio is not a dependency here."""
    runs: dict[str, int] = {}
    cache = ToolCache()
    (read,) = cache.wrap([_tool("Read", runs)])

    async def _drive():
        await read.ainvoke({"file_path": "/x/a.txt"})
        await read.ainvoke({"file_path": "/x/a.txt"})

    asyncio.run(_drive())

    assert runs["Read"] == 1
    assert cache.report().suppressed_tool_calls_count == 1


# ── P1.4: the suppressed call still leaves a span ───────────────────────────
#
# The design's choice (B): a suppressed call that left no span would make the
# trace quieter the better the cache worked, deleting the evidence the report
# exists to show. These run the real OpenInference instrumentor against an
# in-memory exporter, because the claim is about what a caller's tracing sees,
# not about what this module believes it did.

otel_sdk = pytest.importorskip(
    "opentelemetry.sdk.trace", reason="span assertions need the [adapter] extra"
)
pytest.importorskip("openinference.instrumentation.langchain")

from openinference.instrumentation.langchain import (  # noqa: E402
    LangChainInstrumentor,
)
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (  # noqa: E402
    InMemorySpanExporter,
)

from clew.autofix.tool_cache import SUPPRESSED_ATTRIBUTE  # noqa: E402


def _tool_spans(drive):
    """Run `drive()` under a live instrumentor; return the TOOL spans it made."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    instrumentor = LangChainInstrumentor()
    instrumentor.instrument(tracer_provider=provider, skip_dep_check=True)
    try:
        drive()
        provider.force_flush()
        spans = list(exporter.get_finished_spans())
    finally:
        instrumentor.uninstrument()
    return [
        s
        for s in spans
        if (s.attributes or {}).get("openinference.span.kind") == "TOOL"
    ]


def _suppressed_flag(span) -> bool:
    """The tag travels as context metadata, so it arrives JSON-encoded."""
    raw = (span.attributes or {}).get("metadata")
    return bool(raw) and SUPPRESSED_ATTRIBUTE in raw


def test_a_suppressed_call_still_leaves_a_span():
    runs: dict[str, int] = {}
    cache = ToolCache()
    (read,) = cache.wrap([_tool("Read", runs)])

    spans = _tool_spans(
        lambda: [read.invoke({"file_path": "/x/a.txt"}) for _ in range(2)]
    )

    assert runs["Read"] == 1, "the second call must not reach the tool"
    assert cache.report().suppressed_tool_calls_count == 1
    assert len(spans) == 2, (
        "two calls, two tool spans: suppressing one must not make the trace "
        "quieter than the agent's own behaviour"
    )


def test_exactly_the_suppressed_span_carries_the_tag():
    runs: dict[str, int] = {}
    cache = ToolCache()
    (read,) = cache.wrap([_tool("Read", runs)])

    spans = _tool_spans(
        lambda: [read.invoke({"file_path": "/x/a.txt"}) for _ in range(2)]
    )

    tagged = [s for s in spans if _suppressed_flag(s)]
    assert len(tagged) == 1, "the executed call must not be tagged as suppressed"


def test_the_suppressed_span_carries_the_content_the_agent_received():
    runs: dict[str, int] = {}
    cache = ToolCache()
    (read,) = cache.wrap([_tool("Read", runs)])
    seen: list[str] = []

    spans = _tool_spans(
        lambda: seen.extend(
            read.invoke({"file_path": "/x/a.txt"}) for _ in range(2)
        )
    )

    (tagged,) = [s for s in spans if _suppressed_flag(s)]
    assert seen[1] == seen[0]
    assert seen[0] in str((tagged.attributes or {}).get("output.value")), (
        "the span must record what the agent actually got, which is the "
        "cached content"
    )


def test_a_call_the_cache_cannot_serve_leaves_one_span_not_two():
    """The miss path delegates to the wrapped tool, so the wrapper must not
    also emit. One call, one span, whichever branch it takes."""
    runs: dict[str, int] = {}
    cache = ToolCache()
    (read,) = cache.wrap([_tool("Read", runs)])

    spans = _tool_spans(lambda: read.invoke({"file_path": "/x/a.txt"}))

    assert runs["Read"] == 1
    assert len(spans) == 1
    assert not _suppressed_flag(spans[0])


def test_the_async_suppressed_call_leaves_a_tagged_span_too():
    runs: dict[str, int] = {}
    cache = ToolCache()
    (read,) = cache.wrap([_tool("Read", runs)])

    async def _drive():
        await read.ainvoke({"file_path": "/x/a.txt"})
        await read.ainvoke({"file_path": "/x/a.txt"})

    spans = _tool_spans(lambda: asyncio.run(_drive()))

    assert runs["Read"] == 1
    assert len(spans) == 2
    assert len([s for s in spans if _suppressed_flag(s)]) == 1
