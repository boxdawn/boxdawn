"""Serve a repeated read from cache instead of running the tool again.

Stage 4 Phase 1. Scope fixed by the design document: LangGraph runtime,
`redundant_read` only, safety default = invalidate.

What this measures, and what it does not
----------------------------------------
It counts **tool executions avoided**. It does **not** save model input
tokens, and Phase 1 therefore reports no token or dollar figure.

The reason is in the detector's own cost model
(`detect/redundant_read.py`: `waste tokens = tokens(cand.output_text)`,
priced at the *next-turn LLM input rate*): the waste of a redundant read is
that its output enters the conversation a second time and is shipped as input
on every later turn. A cache that hands the agent **the same content** leaves
that content in the conversation, so those tokens are still shipped. Only the
tool run is avoided.

Removing the tokens would mean returning something shorter than what the tool
returned — changing what the model sees. That is the Phase 3 context-reduction
change, which the design puts behind its own pre-registration. So:

- sayable after Phase 1: "this session ran N fewer tool calls"
- NOT sayable after Phase 1: "N tokens saved", "$N saved", "N% reduction"

Suppressed calls still leave a span (design P1.4)
------------------------------------------------
A suppressed call is routed back through `BaseTool.run()` instead of returning
early, so whatever tracing the caller already runs emits a tool span for it,
carrying the cached content as the output. That content is what the agent
received, so the span is a true record of the call it made — and a trace
captured with suppression active still shows the repeat that was found. The
alternative was a trace that gets quieter the better the cache works, which
would delete the evidence the report exists to show.

The span is tagged `clew.suppressed = True` through context metadata. Nothing
in this package reads that tag yet: `ingest/*` is outside Phase 1 scope, so a
report over such a trace still counts the repeat as waste, which is true — the
agent did ask twice. Telling "found and avoided" apart from "found, still
happening" is what the tag is written for.

No tracer and no provider is constructed here. That is deliberate: it is what
lets the same code work under `capture.py`'s local provider and under a
caller's own global one, which is the question P1.7 left open.

Still open (P1.7)
-----------------
Two concurrent `ainvoke` calls on one key both miss and both run; Phase 1
takes the duplicate execution over a held lock.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from contextlib import nullcontext
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import ConfigDict

try:  # part of the same `adapter` extra as langchain-core
    from openinference.instrumentation import using_metadata
except ImportError:  # pragma: no cover - langchain without openinference
    using_metadata = None

from clew.detect.redundant_read import (
    _SHELL_TOOLS,
    _extract_target,
    _load_tool_sets,
)

# Phase 1 default, flagged open in the design (P1.7). Entries are small
# (a key and the tool's return value), and the cache lives for one
# ToolCache object, so the cap is a guard against a pathological session
# rather than a tuned figure.
_DEFAULT_MAX_ENTRIES = 256

# Marker on the suppressed call's span (design P1.4). Read by nothing in this
# package: `ingest/*` is out of Phase 1 scope, so this is written now and
# consumed later rather than being invented twice.
SUPPRESSED_ATTRIBUTE = "clew.suppressed"

# Carries the already-served value from `invoke` into `_run` for one call.
# A ContextVar rather than an attribute on the tool: one `_CachedTool` instance
# serves every call to that tool, so an attribute would let two concurrent
# calls hand each other the wrong value.
_SERVED: ContextVar[Any] = ContextVar("clew_tool_cache_served")
_NOTHING_SERVED = object()


@dataclass
class ToolCacheReport:
    """Counts for one ToolCache lifetime. Units are in the names."""

    suppressed_tool_calls_count: int = 0
    cache_miss_count: int = 0
    # Two different units, so two fields: how many times the safety default
    # fired, and how many entries it threw away. One shell call can drop a
    # whole cache, so the second number says nothing about the first.
    cache_invalidation_events: int = 0
    cache_entries_dropped_count: int = 0
    not_cacheable_count: int = 0
    suppression_window: str = ""
    suppressed_targets: list[str] = field(default_factory=list)

    def render(self) -> str:
        """Number first, population underneath (design decision 4)."""
        n = self.suppressed_tool_calls_count
        distinct = len(set(self.suppressed_targets))
        return "\n".join([
            f"      {n} tool call{'' if n == 1 else 's'} avoided",
            "   " + "-" * 25,
            f"   {self.suppression_window} · {distinct} target(s)"
            f" · {self.cache_invalidation_events} invalidation(s)",
        ])


def _serialize_input(tool_input: Any) -> str:
    """Match the adapter's tool-input serialization (`ingest/claude_code.py`).

    The key has to be the detector's key, so the string handed to
    `_extract_target` has to be the string the detector would have seen.
    """
    if isinstance(tool_input, str):
        return tool_input
    try:
        return json.dumps(tool_input, sort_keys=True, ensure_ascii=False)
    except (TypeError, ValueError):
        return ""


def _is_error_result(result: Any) -> bool:
    """A failed tool result is never cached (same rule as the §29.2 gate)."""
    status = getattr(result, "status", None)
    return status == "error"


class ToolCache:
    """Caches read-tool results for one lifetime, and counts what it avoided.

    Usage is one line at graph build time::

        cache = ToolCache()
        tools = cache.wrap(tools)
        ...
        print(cache.report().render())

    An object rather than a module global: the population of the counts is
    this object's lifetime, and two graphs in one process must not mix.
    """

    def __init__(
        self,
        *,
        window: str = "this session",
        max_entries: int = _DEFAULT_MAX_ENTRIES,
    ) -> None:
        self._window = window
        self._max_entries = max_entries
        self._entries: OrderedDict[tuple[str, str], Any] = OrderedDict()
        self._report = ToolCacheReport(suppression_window=window)

    # ── public ──────────────────────────────────────────────────────────

    def wrap(self, tools: list[BaseTool]) -> list[BaseTool]:
        """Return tools that consult this cache. Name, description and schema
        are carried over unchanged — the list the model sees must not differ.
        """
        return [_CachedTool.of(t, self) for t in tools]

    def report(self) -> ToolCacheReport:
        return self._report

    # ── internals used by the wrapper ───────────────────────────────────

    def _key_for(self, tool_name: str, tool_input: Any) -> tuple[str, str] | None:
        """The detector's key, or None when the detector would not count it."""
        read_tools, _ = _load_tool_sets()
        if tool_name not in read_tools:
            return None
        target = _extract_target(_serialize_input(tool_input))
        if target is None:
            return None
        return (tool_name, target)

    def _before_call(self, tool_name: str, tool_input: Any) -> None:
        """Invalidation runs on the way in, before the tool can change state.

        Same gates the detector uses to decide a pair does not count: an
        intervening write to that target, or any shell tool at all.
        """
        _, write_tools = _load_tool_sets()
        if tool_name in _SHELL_TOOLS:
            # Payload-opaque: what changed is unknown, so nothing survives.
            self._invalidate_all()
            return
        if tool_name in write_tools:
            target = _extract_target(_serialize_input(tool_input))
            if target is None:
                # Cannot tell what was written — invalidate rather than guess.
                self._invalidate_all()
                return
            dead = [k for k in self._entries if k[1] == target]
            for k in dead:
                del self._entries[k]
            self._report.cache_invalidation_events += 1
            self._report.cache_entries_dropped_count += len(dead)

    def _invalidate_all(self) -> None:
        self._report.cache_invalidation_events += 1
        self._report.cache_entries_dropped_count += len(self._entries)
        self._entries.clear()

    def _serve(self, key: tuple[str, str]) -> tuple[bool, Any]:
        if key in self._entries:
            self._report.suppressed_tool_calls_count += 1
            self._report.suppressed_targets.append(key[1])
            return True, self._entries[key]
        self._report.cache_miss_count += 1
        return False, None

    def _store(self, key: tuple[str, str], result: Any) -> None:
        if _is_error_result(result):
            return
        self._entries[key] = result
        while len(self._entries) > self._max_entries:
            self._entries.popitem(last=False)

    def _count_not_cacheable(self) -> None:
        self._report.not_cacheable_count += 1


def _served_value() -> Any:
    """The value `invoke` set for this suppressed call, or a clear failure."""
    value = _SERVED.get(_NOTHING_SERVED)
    if value is _NOTHING_SERVED:
        raise NotImplementedError(
            "_CachedTool routes real calls through invoke/ainvoke; _run is "
            "only the tail of a suppressed one"
        )
    return value


class _CachedTool(BaseTool):
    """Delegates to the wrapped tool, consulting the cache first."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    inner: BaseTool
    cache: ToolCache

    @classmethod
    def of(cls, tool: BaseTool, cache: ToolCache) -> "_CachedTool":
        return cls(
            name=tool.name,
            description=tool.description,
            args_schema=tool.args_schema,
            inner=tool,
            cache=cache,
        )

    def _run(self, *args: Any, **kwargs: Any) -> Any:
        """The already-served value, for the suppressed path only.

        A cache hit is routed back through `BaseTool.run()` (see
        `_suppressed_context`) so that whatever tracing the caller already runs
        emits a tool span for the call the agent actually made. `run()` ends at
        `_run`, and the value it must return is the one `_serve` handed back —
        not a second execution of the tool.

        Reached with nothing served, it raises rather than returning something:
        that would mean `run()` was entered outside `invoke`, and answering a
        real call from here would bypass the cache silently.
        """
        return _served_value()

    async def _arun(self, *args: Any, **kwargs: Any) -> Any:
        """Async twin of `_run`. Overridden so the default does not bounce
        `_run` onto a worker thread, where the ContextVar lookup would be a
        different context."""
        return _served_value()

    def _suppressed_context(self) -> Any:
        """Tag the span `run()` is about to produce as a suppressed call.

        The attribute cannot be set from inside `_run`: measured 2026-10-13,
        `trace.get_current_span()` there is a `NonRecordingSpan` with an
        invalid context, so `set_attribute` is a no-op. The instrumentation
        builds the span from callbacks and never makes it current. Context
        metadata is the carrier that does reach it.

        No tracer and no provider is touched anywhere in this module, which is
        what lets the same code work under `capture.py`'s local provider and
        under a caller's own global one (design P1.7).
        """
        if using_metadata is None:  # pragma: no cover - no openinference
            return nullcontext()
        return using_metadata({SUPPRESSED_ATTRIBUTE: True})

    def invoke(
        self,
        input: Any,  # noqa: A002 — BaseTool's parameter name
        config: Any = None,
        **kwargs: Any,
    ) -> Any:
        self.cache._before_call(self.name, input)
        key = self.cache._key_for(self.name, input)
        if key is None:
            self.cache._count_not_cacheable()
            return self.inner.invoke(input, config, **kwargs)
        hit, value = self.cache._serve(key)
        if hit:
            token = _SERVED.set(value)
            try:
                with self._suppressed_context():
                    return super().invoke(input, config, **kwargs)
            finally:
                _SERVED.reset(token)
        # A miss delegates to the wrapped tool, which keeps its own span and
        # its own `config`; the outer `invoke` emits nothing, so either way one
        # call leaves one span.
        result = self.inner.invoke(input, config, **kwargs)
        self.cache._store(key, result)
        return result

    async def ainvoke(
        self,
        input: Any,  # noqa: A002 — BaseTool's parameter name
        config: Any = None,
        **kwargs: Any,
    ) -> Any:
        # No lock: two concurrent calls on one key both miss and both run.
        # Phase 1 takes the duplicate run over a held lock (P1.7).
        self.cache._before_call(self.name, input)
        key = self.cache._key_for(self.name, input)
        if key is None:
            self.cache._count_not_cacheable()
            return await self.inner.ainvoke(input, config, **kwargs)
        hit, value = self.cache._serve(key)
        if hit:
            token = _SERVED.set(value)
            try:
                with self._suppressed_context():
                    return await super().ainvoke(input, config, **kwargs)
            finally:
                _SERVED.reset(token)
        result = await self.inner.ainvoke(input, config, **kwargs)
        self.cache._store(key, result)
        return result
