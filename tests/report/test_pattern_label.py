"""tests/report/test_pattern_label.py — the report names the detector that fired.

`pingpong` used to be given to any llm/llm pair. That is wider than the
detector: `find_repeat_candidates` groups two calls of the *same* node, and two
such llm spans came out of the report headed `pingpong` while the Snippets
block called the same finding `repeat`. Reproduced 2026-09-09 against the
hosted analyzer, which returned `"pattern_label": "pingpong"` for a trace whose
pingpong detector never fired.

It is not only a wrong word. `find_pingpong_candidates` is left out of the
waste-rate metric because it has never fired outside synthetic traces
(WASTE_RATE_METRIC_PREREG, "Explicitly EXCLUDED"), so a report printing the
name anyway is evidence against a claim we make about our own discipline.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from clew.model import Span, Trace
from clew.report._enrich import enrich
from clew.report._model import WasteDetail

T0 = datetime(2026, 9, 9, tzinfo=timezone.utc)


def _span(span_id: str, node: str, kind: str, offset: int, output: str) -> Span:
    return Span(
        trace_id="t",
        span_id=span_id,
        parent_span_id="root",
        agent_or_node_id=node,
        span_kind=kind,
        start_time=T0 + timedelta(seconds=offset),
        end_time=T0 + timedelta(seconds=offset + 1),
        input_text="summarise the plan",
        output_text=output,
    )


def _trace(spans: list[Span]) -> Trace:
    root = Span(
        trace_id="t",
        span_id="root",
        parent_span_id=None,
        agent_or_node_id="session",
        span_kind="chain",
        start_time=T0,
        end_time=T0 + timedelta(minutes=1),
        input_text="",
        output_text="",
    )
    return Trace(trace_id="t", spans=[root, *spans])


def test_same_node_llm_repeat_is_not_called_pingpong():
    """Two llm calls of one node. The pingpong detector never sees this shape."""
    a1 = _span("a1", "planner", "llm", 1, "build, verify, promote.")
    a2 = _span("a2", "planner", "llm", 10, "build, verify, promote.")
    result = enrich(_trace([a1, a2]), [WasteDetail(a1, a2, 1.0)])

    assert [e.pattern_label for e in result.enriched] == ["repeat"]


def test_alternation_the_detector_produced_is_called_pingpong():
    """A->B->A->B across two nodes, which is what `find_pingpong_candidates` emits."""
    a1 = _span("a1", "planner", "llm", 1, "still thinking about the plan.")
    b1 = _span("b1", "critic", "llm", 2, "say more about the plan.")
    a2 = _span("a2", "planner", "llm", 3, "still thinking about the plan.")
    b2 = _span("b2", "critic", "llm", 4, "say more about the plan.")
    result = enrich(_trace([a1, b1, a2, b2]), [WasteDetail(a1, a2, 1.0)])

    assert [e.pattern_label for e in result.enriched] == ["pingpong"]


def test_tool_pair_with_matching_input_is_still_requery():
    """The tool branch is untouched: it is checked before the pingpong set."""
    t1 = _span("t1", "Read", "tool", 1, "file contents")
    t2 = _span("t2", "Read", "tool", 10, "file contents")
    result = enrich(_trace([t1, t2]), [WasteDetail(t1, t2, 1.0)])

    assert [e.pattern_label for e in result.enriched] == ["requery"]
