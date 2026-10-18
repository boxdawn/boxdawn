"""Readers that treat llm_calls as one conversation read the main one only.

Sub-agent Bundle Upload prereg §9: since 0.5.19 the Claude Code adapter
appends sub-agent calls to `llm_calls`, tagged `conversation`.
"""
from __future__ import annotations

import dataclasses
import json
from datetime import datetime, timedelta, timezone
from typing import Any

from clew.detect.llm_judge import semantic_duplicate as sd
from clew.detect.llm_judge.verification_judge import render_trace_for_judge
from clew.detect.redundant_read import find_redundant_reads
from clew.model import Span, Trace, main_conversation_calls


def _t(sec: int) -> datetime:
    return datetime(2026, 1, 1, tzinfo=timezone.utc) + timedelta(seconds=sec)


def _call(span_id: str, sec: int, messages: list[dict[str, Any]], *,
          model: str = "claude-sonnet-4-5", conversation: str | None = None) -> dict[str, Any]:
    call: dict[str, Any] = {
        "span_id": span_id, "input_text": json.dumps(messages),
        "input_tokens": 100, "output_tokens": 20,
        "input_tokens_uncached": 100, "input_tokens_cache_read": 0,
        "input_tokens_cache_write": 0, "input_cost_rate": None,
        "output_cost_rate": None, "cost_rate_legacy": None,
        "model": model, "start_time": _t(sec).isoformat(),
    }
    if conversation is not None:
        call["conversation"] = conversation
    return call


def _span(span_id: str, tool: str, inp: str, out: str, sec: int, kind: str = "tool") -> Span:
    return Span(trace_id="T", span_id=span_id, parent_span_id="root",
                agent_or_node_id=tool, span_kind=kind, start_time=_t(sec),
                end_time=_t(sec + 1), input_text=inp, output_text=out)


def _trace(spans: list[Span], calls: list[dict[str, Any]]) -> Trace:
    root = Span(trace_id="T", span_id="root", parent_span_id=None,
                agent_or_node_id="root", span_kind="chain", start_time=_t(0),
                end_time=_t(1000), input_text="", output_text="[root]")
    return Trace(trace_id="T", spans=[root] + spans, metadata={"llm_calls": calls})


def _user(text: str) -> dict[str, Any]:
    return {"role": "user", "content": [{"type": "text", "text": text}]}


def test_an_untagged_call_is_main():
    trace = _trace([], [_call("a", 1, []), _call("b", 2, [], conversation="main"),
                        _call("c", 3, [], conversation="x1")])
    assert [c["span_id"] for c in main_conversation_calls(trace)] == ["a", "b"]


def test_the_judge_does_not_read_a_subagent_prompt_as_the_user():
    edit = _span("e1", "Edit", '{"file_path": "/a.py"}', "ok", 5)
    calls = [_call("m1", 1, [_user("fix the failing test")], conversation="main"),
             _call("s1", 6, [_user("search the repo for the helper")], conversation="x1")]
    view = render_trace_for_judge(_trace([edit], calls))
    assert "fix the failing test" in view
    assert "search the repo for the helper" not in view


def test_a_late_read_is_priced_at_the_last_main_call_not_a_subagent_call():
    a = _span("a", "Read", '{"file_path": "/tmp/x.py"}', "print('hi')", 10)
    b = _span("b", "Read", '{"file_path": "/tmp/x.py"}', "print('hi')", 20)
    main = _call("m1", 5, [], conversation="main")
    sub = _call("s1", 30, [], model="claude-haiku-4-5", conversation="x1")
    with_sub = find_redundant_reads(_trace([a, b], [main, sub]))
    main_only = find_redundant_reads(_trace([a, b], [main]))
    assert with_sub.events
    assert dataclasses.asdict(with_sub) == dataclasses.asdict(main_only)


def test_semantic_pairs_stay_inside_one_conversation():
    text = "please read the config file and report the port number it uses"
    near = "please read the config file and report which port number it uses"
    calls = [_call("m1", 1, [_user(text)], conversation="main"),
             _call("s1", 2, [_user(near)], conversation="x1")]
    assert sd._candidate_pairs(sd._extract_chunks(calls), calls) == []

    calls[1]["conversation"] = "main"
    assert len(sd._candidate_pairs(sd._extract_chunks(calls), calls)) == 1
