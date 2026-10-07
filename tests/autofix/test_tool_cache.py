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
