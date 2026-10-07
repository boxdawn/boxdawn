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

Known gap (design P1.4 / P1.7, deliberately open)
-------------------------------------------------
A suppressed call emits no OpenTelemetry span yet, because where to attach one
is still open. Until that lands, a trace captured with suppression active has
fewer read spans, so an analyzer run over it reports *less* waste — the
report gets quieter precisely because the cache worked. `ToolCacheReport`
exists so the avoided calls are at least countable in-process.
"""
from __future__ import annotations

import json
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import ConfigDict

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

    def _run(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        # BaseTool requires it; invoke/ainvoke are overridden so it is never
        # the path taken. Raising beats silently bypassing the cache.
        raise NotImplementedError("_CachedTool routes through invoke/ainvoke")

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
            return value
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
            return value
        result = await self.inner.ainvoke(input, config, **kwargs)
        self.cache._store(key, result)
        return result
