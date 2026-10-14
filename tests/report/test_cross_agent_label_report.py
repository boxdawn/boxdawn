"""tests/report/test_cross_agent_label_report.py — CROSS_AGENT_ATTRIBUTION_PREREG §2.3, P3, P7.

What the reader gets from a cross-agent finding is the pair of names: told that
two agents duplicated each other without being told *which two*, there is
nothing to act on. P3 fixes that as a prediction, and P7 fixes the other side —
nothing cross-agent is rendered on a trace that holds only one identity.

The JSON keys are conditional, following the `between_window` precedent: a
consumer that does not know the label sees no new keys.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from clew.detect.cascade import CascadeResult
from clew.model import Span, Trace
from clew.report._model import WasteDetail
from clew.report.json_report import render_json
from clew.report.markdown import render_markdown

T0 = datetime(2026, 10, 14, tzinfo=timezone.utc)
_SAME_INPUT = '{"file_path": "/repo/notes.md"}'


def _span(span_id: str, parent: str | None, node: str, kind: str, offset: int) -> Span:
    return Span(
        trace_id="T",
        span_id=span_id,
        parent_span_id=parent,
        agent_or_node_id=node,
        span_kind=kind,
        start_time=T0 + timedelta(seconds=offset),
        end_time=T0 + timedelta(seconds=offset + 1),
        input_text=_SAME_INPUT if kind == "tool" else "",
        output_text="the same bytes",
        token_count=10,
        model="fake",
        cost_rate=1e-6,
    )


def _two_worker_trace() -> tuple[Trace, Span, Span]:
    root = _span("root", None, "LangGraph", "chain", 0)
    wa = _span("wa", "root", "worker_a", "chain", 1)
    wb = _span("wb", "root", "worker_b", "chain", 15)
    t1 = _span("t1", "wa", "Read", "tool", 10)
    t2 = _span("t2", "wb", "Read", "tool", 20)
    return Trace(trace_id="T", spans=[root, wa, wb, t1, t2]), t1, t2


def _one_owner_trace() -> tuple[Trace, Span, Span]:
    root = _span("root", None, "session", "chain", 0)
    t1 = _span("t1", "root", "Read", "tool", 10)
    t2 = _span("t2", "root", "Read", "tool", 20)
    return Trace(trace_id="T", spans=[root, t1, t2]), t1, t2


def _cascade() -> CascadeResult:
    return CascadeResult(trace_id="T", wasteful=True)


def test_markdown_names_both_agents():
    """P3: the label names `worker_a` and `worker_b`."""
    trace, t1, t2 = _two_worker_trace()
    md = render_markdown(trace, _cascade(), [WasteDetail(t1, t2, 1.0)])

    assert "cross_agent_repeat" in md
    assert "`worker_a` ran it first, `worker_b` ran it again" in md


def test_json_carries_both_identities():
    trace, t1, t2 = _two_worker_trace()
    js = json.loads(render_json(trace, _cascade(), details=[WasteDetail(t1, t2, 1.0)]))
    (entry,) = js["waste_details"]
    assert entry["pattern_label"] == "cross_agent_repeat"
    assert entry["origin_identity"] == "worker_a"
    assert entry["candidate_identity"] == "worker_b"


def test_single_identity_trace_renders_nothing_cross_agent():
    """P7: one owner, so there is no second agent to name."""
    trace, t1, t2 = _one_owner_trace()
    details = [WasteDetail(t1, t2, 1.0)]

    md = render_markdown(trace, _cascade(), details)
    assert "cross_agent_repeat" not in md
    assert "ran it again" not in md

    js = json.loads(render_json(trace, _cascade(), details=details))
    (entry,) = js["waste_details"]
    assert entry["pattern_label"] == "requery"
    assert "origin_identity" not in entry
    assert "candidate_identity" not in entry
