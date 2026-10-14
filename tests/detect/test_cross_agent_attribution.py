"""tests/detect/test_cross_agent_attribution.py — CROSS_AGENT_ATTRIBUTION_PREREG.

Two shipped detectors used to *drop* a candidate pair whose two spans sat under
different AGENT spans (SPEC §16). On TRAIL's gaia split that gate deleted 13
real tool repeats whose two sides were two invocations of the *same* agent kind.
The gate no longer drops tool pairs; it classifies them, and the pre-registration
freezes identity as the agent's **kind** so those 13 stay `repeat`-family rather
than being promoted to the claim the positioning already overstates.

Scope, per §8.1: tool pairs only. Non-tool groups carry no input gate, so
same-named steps under two agents reach each other on topical vocabulary alone
(the E3 case) — the gate stays exactly as shipped for them, and
`test_non_tool_pair_under_two_agents_is_still_dropped` is what holds that line.

`redundant_read` is deliberately absent from this file. §8.2: its gate drops 0
events on all three corpora, and `tests/detect/test_redundant_read.py::
test_different_agent_parents_excluded` is a shipped test asserting the drop, so
removing it would mean editing an existing assertion — §5's last KILL condition.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from clew.detect.structural import find_repeat_candidates, identity_of
from clew.model import Span, Trace
from clew.report._enrich import enrich
from clew.report._model import WasteDetail

T0 = datetime(2026, 10, 14, tzinfo=timezone.utc)

_SAME_INPUT = '{"q": "boxdawn"}'
_SAME_READ = '{"file_path": "/repo/notes.md"}'


def _span(
    span_id: str,
    parent: str | None,
    node: str,
    kind: str,
    offset: int,
    input_text: str = "",
    output_text: str = "out",
) -> Span:
    return Span(
        trace_id="t",
        span_id=span_id,
        parent_span_id=parent,
        agent_or_node_id=node,
        span_kind=kind,
        start_time=T0 + timedelta(seconds=offset),
        end_time=T0 + timedelta(seconds=offset + 1),
        input_text=input_text,
        output_text=output_text,
        token_count=10,
        model="fake",
        cost_rate=1e-6,
    )


# ── §1.3 identity ──────────────────────────────────────────────────────────

def test_identity_is_the_agent_kind_not_the_invocation():
    """Two AGENT spans of one kind return one identity — the §1.2 decision."""
    root = _span("root", None, "main", "chain", 0)
    a1 = _span("a1", "root", "ToolCallingAgent", "agent", 1)
    a2 = _span("a2", "root", "ToolCallingAgent", "agent", 5)
    t1 = _span("t1", "a1", "search", "tool", 2)
    t2 = _span("t2", "a2", "search", "tool", 6)
    by_id = {s.span_id: s for s in (root, a1, a2, t1, t2)}

    assert identity_of("a1", by_id) == "ToolCallingAgent"
    assert identity_of("a2", by_id) == "ToolCallingAgent"
    assert identity_of(t1.parent_span_id, by_id) == identity_of(t2.parent_span_id, by_id)


def test_identity_falls_back_to_the_chain_when_no_agent_span_exists():
    """Standard OpenInference instrumentation emits graph nodes as CHAIN (§1.1)."""
    root = _span("root", None, "LangGraph", "chain", 0)
    wa = _span("wa", "root", "worker_a", "chain", 1)
    wb = _span("wb", "root", "worker_b", "chain", 3)
    by_id = {s.span_id: s for s in (root, wa, wb)}

    assert identity_of("wa", by_id) == "worker_a"
    assert identity_of("wb", by_id) == "worker_b"


def test_identity_prefers_an_agent_ancestor_over_a_nearer_chain():
    """The AGENT ancestor wins wherever it sits; the chain is only a fallback."""
    agent = _span("agent", None, "Researcher", "agent", 0)
    step = _span("step", "agent", "Step 1", "chain", 1)
    by_id = {s.span_id: s for s in (agent, step)}

    assert identity_of("step", by_id) == "Researcher"


def test_identity_is_none_on_a_flat_trace():
    tool = _span("t1", None, "search", "tool", 0)
    assert identity_of(tool.parent_span_id, {"t1": tool}) is None


# ── §2.4 the gate stops dropping tool pairs ────────────────────────────────

def _two_tool_calls_under(parent_a: str, parent_b: str, spans: list[Span]) -> Trace:
    t1 = _span("t1", parent_a, "search", "tool", 10, input_text=_SAME_INPUT)
    t2 = _span("t2", parent_b, "search", "tool", 20, input_text=_SAME_INPUT)
    return Trace(trace_id="t", spans=[*spans, t1, t2])


def test_tool_pair_under_two_invocations_of_one_agent_kind_is_a_candidate():
    """TRAIL's 13: both sides are `ToolCallingAgent.run`, so the pair is ordinary."""
    root = _span("root", None, "main", "chain", 0)
    a1 = _span("a1", "root", "ToolCallingAgent", "agent", 1)
    a2 = _span("a2", "root", "ToolCallingAgent", "agent", 15)
    trace = _two_tool_calls_under("a1", "a2", [root, a1, a2])

    # The two AGENT spans are a non-tool repeat pair of their own (one kind,
    # seen twice) and always were; the tool pair is what the gate deleted.
    pairs = find_repeat_candidates(trace, n=2)
    tool_pairs = [(o.span_id, c.span_id) for o, c in pairs if o.span_kind == "tool"]
    assert tool_pairs == [("t1", "t2")]

    result = enrich(trace, [WasteDetail(trace.spans[-2], trace.spans[-1], 1.0)])
    assert [e.pattern_label for e in result.enriched] == ["requery"]


def test_tool_pair_under_two_different_agents_is_labelled_cross_agent():
    root = _span("root", None, "main", "chain", 0)
    a1 = _span("a1", "root", "worker_a", "agent", 1)
    a2 = _span("a2", "root", "worker_b", "agent", 15)
    trace = _two_tool_calls_under("a1", "a2", [root, a1, a2])

    pairs = find_repeat_candidates(trace, n=2)
    assert [(o.span_id, c.span_id) for o, c in pairs] == [("t1", "t2")]

    result = enrich(trace, [WasteDetail(trace.spans[-2], trace.spans[-1], 1.0)])
    (ed,) = result.enriched
    assert ed.pattern_label == "cross_agent_repeat"
    assert (ed.origin_identity, ed.candidate_identity) == ("worker_a", "worker_b")


def test_chain_identities_are_enough_no_agent_span_needed():
    """§1.1's shape: the workers arrive as CHAIN and the pair is still attributed."""
    root = _span("root", None, "LangGraph", "chain", 0)
    wa = _span("wa", "root", "worker_a", "chain", 1)
    wb = _span("wb", "root", "worker_b", "chain", 15)
    trace = _two_tool_calls_under("wa", "wb", [root, wa, wb])

    result = enrich(trace, [WasteDetail(trace.spans[-2], trace.spans[-1], 1.0)])
    (ed,) = result.enriched
    assert ed.pattern_label == "cross_agent_repeat"
    assert (ed.origin_identity, ed.candidate_identity) == ("worker_a", "worker_b")


def test_one_side_without_an_identity_is_not_cross_agent():
    """§2.2: `None` on either side means the pair is not the cross-agent case.

    `t1` is the root, so it has no ancestor of either kind and its identity is
    `None`; `t2` sits under an agent. The shipped gate dropped this shape too
    (the mixed-depth case) and for tool pairs it no longer does — but an absent
    identity is not a second agent, so the label stays as it was.
    """
    t1 = _span("t1", None, "search", "tool", 10, input_text=_SAME_INPUT)
    agent = _span("a1", "t1", "worker_a", "agent", 15)
    t2 = _span("t2", "a1", "search", "tool", 20, input_text=_SAME_INPUT)
    trace = Trace(trace_id="t", spans=[t1, agent, t2])

    result = enrich(trace, [WasteDetail(t1, t2, 1.0)])
    assert [e.pattern_label for e in result.enriched] == ["requery"]


def test_non_tool_pair_under_two_agents_is_still_dropped():
    """§8.1: the partition is scoped to tool pairs; the E3 gate is untouched.

    Measured before the implementation: removing the gate for non-tool kinds
    puts 86 `chain`/`chain` pairs on TRAIL gaia into `cross_agent_repeat`, a
    corpus the pre-registration measured as 0 (§8).
    """
    root = _span("root", None, "main", "chain", 0)
    a1 = _span("a1", "root", "CodeAgent", "agent", 1)
    a2 = _span("a2", "root", "ToolCallingAgent", "agent", 15)
    s1 = _span("s1", "a1", "Step 1", "chain", 2, output_text="Execution logs")
    s2 = _span("s2", "a2", "Step 1", "chain", 16, output_text="Address: google")
    trace = Trace(trace_id="t", spans=[root, a1, a2, s1, s2])

    assert find_repeat_candidates(trace, n=2) == []
