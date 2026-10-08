"""tests/detect/test_context_resend.py — Context Resend Detector v1.

Locks the behaviour defined in `docs/CONTEXT_RESEND_DETECTOR_PREREG.md` §6.1.

Fixtures are hand-constructed `Trace` objects with LLM inputs populated in
`metadata["llm_calls"]` per prereg §3 — bypassing preprocess entirely, so
each test isolates one detector concern.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pytest

from clew.detect.context_resend import find_context_resend
from clew.model import Span, Trace


# ── helpers ─────────────────────────────────────────────────────────────────

def _root_only_trace(trace_id: str, llm_calls: list[dict[str, Any]]) -> Trace:
    """Trace with a single chain root and `llm_calls` metadata populated.

    The detector reads only metadata, so span layout is irrelevant for these
    tests — a minimal 1-span root satisfies Trace validation.
    """
    root = Span(
        trace_id=trace_id,
        span_id="root",
        parent_span_id=None,
        agent_or_node_id="root",
        span_kind="chain",
        start_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        input_text="",
        output_text="[test root]",
    )
    return Trace(
        trace_id=trace_id,
        spans=[root],
        metadata={"llm_calls": llm_calls},
    )


def _mk_llm_call(
    span_id: str,
    messages: list[dict[str, str]] | str,
    *,
    input_tokens: int = 100,
    output_tokens: int = 20,
    input_cost_rate: float | None = 3e-6,
    output_cost_rate: float | None = 15e-6,
    cost_rate_legacy: float | None = None,
    model: str = "claude-sonnet-4.5",
) -> dict[str, Any]:
    input_text = messages if isinstance(messages, str) else json.dumps(messages)
    return {
        "span_id": span_id,
        "input_text": input_text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "input_cost_rate": input_cost_rate,
        "output_cost_rate": output_cost_rate,
        "cost_rate_legacy": cost_rate_legacy,
        "model": model,
        "start_time": "2026-01-01T00:00:00+00:00",
    }


# ── unit tests ──────────────────────────────────────────────────────────────

def test_identical_prompt_across_two_calls():
    """Two LLM calls with identical input list -> all chunks after first are resent."""
    msgs = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    llm_calls = [
        _mk_llm_call("llm-1", msgs),
        _mk_llm_call("llm-2", msgs),
    ]
    trace = _root_only_trace("t1", llm_calls)

    result = find_context_resend(trace)

    # 2 chunks in call 2 resent (both non-system).
    assert len(result.resent_events) == 2
    assert all(e.llm_span_id == "llm-2" for e in result.resent_events)
    assert all(e.origin_llm_span_id == "llm-1" for e in result.resent_events)
    assert result.resent_input_tokens > 0
    assert result.cost_accuracy_flag == "accurate"


def test_partially_overlapping_messages():
    """Call 2 = [a, b, c], call 1 = [a, b] -> a and b are resent, c is not."""
    a = {"role": "user", "content": "aaa"}
    b = {"role": "assistant", "content": "bbb"}
    c = {"role": "user", "content": "ccc"}
    llm_calls = [
        _mk_llm_call("llm-1", [a, b]),
        _mk_llm_call("llm-2", [a, b, c]),
    ]
    trace = _root_only_trace("t2", llm_calls)

    result = find_context_resend(trace)

    # a, b resent in call 2. c not (single occurrence).
    resent_hashes = {e.chunk_hash for e in result.resent_events}
    assert len(resent_hashes) == 2  # a and b
    assert all(e.llm_span_id == "llm-2" for e in result.resent_events)


def test_system_role_exempt():
    """System-role chunk appearing in every call -> zero resent events."""
    sysprompt = {"role": "system", "content": "You are a helpful assistant."}
    llm_calls = [
        _mk_llm_call("llm-1", [sysprompt, {"role": "user", "content": "q1"}]),
        _mk_llm_call("llm-2", [sysprompt, {"role": "user", "content": "q2"}]),
        _mk_llm_call("llm-3", [sysprompt, {"role": "user", "content": "q3"}]),
    ]
    trace = _root_only_trace("t3", llm_calls)

    result = find_context_resend(trace)

    # System chunk repeats across all calls but is exempt. Other chunks are
    # each unique per call -> no resends at all.
    assert result.resent_events == []
    assert result.resent_input_tokens == 0


def test_unparseable_input_falls_back():
    """Non-JSON input in both calls with identical content -> one fallback resent event."""
    raw = "plain text prompt not JSON at all"
    llm_calls = [
        _mk_llm_call("llm-1", raw),
        _mk_llm_call("llm-2", raw),
    ]
    trace = _root_only_trace("t4", llm_calls)

    result = find_context_resend(trace)

    # Fallback chunk = whole string. Second call's occurrence is resent.
    assert len(result.resent_events) == 1
    assert result.resent_events[0].llm_span_id == "llm-2"
    assert result.resent_events[0].chunk_role is None


def test_role_missing_no_exemption():
    """Dict chunk without `role` key repeats -> counted as resent."""
    x = {"data": "payload", "seq": 42}
    llm_calls = [
        _mk_llm_call("llm-1", [x]),
        _mk_llm_call("llm-2", [x]),
    ]
    trace = _root_only_trace("t5", llm_calls)

    result = find_context_resend(trace)

    assert len(result.resent_events) == 1
    assert result.resent_events[0].chunk_role is None


def test_no_llm_calls_returns_empty():
    """Trace with only tool spans (empty llm_calls metadata) -> empty result, no error."""
    trace = _root_only_trace("t6", [])
    result = find_context_resend(trace)

    assert result.resent_events == []
    assert result.resent_input_tokens == 0
    assert result.total_llm_input_tokens == 0
    assert result.total_llm_input_cost == 0.0


def test_single_llm_call_returns_empty():
    """One LLM call -> no repeats possible, empty result."""
    llm_calls = [
        _mk_llm_call("llm-1", [{"role": "user", "content": "solo"}]),
    ]
    trace = _root_only_trace("t7", llm_calls)

    result = find_context_resend(trace)

    assert result.resent_events == []
    assert result.total_llm_input_tokens == 100


def test_accurate_cost_path():
    """llm_calls has input_cost_rate populated -> cost_accuracy_flag == accurate."""
    msgs = [{"role": "user", "content": "same"}]
    llm_calls = [
        _mk_llm_call("llm-1", msgs, input_cost_rate=3e-6),
        _mk_llm_call("llm-2", msgs, input_cost_rate=3e-6),
    ]
    trace = _root_only_trace("t8", llm_calls)

    result = find_context_resend(trace)

    assert result.cost_accuracy_flag == "accurate"
    # cost = resent_input_tokens * 3e-6
    for e in result.resent_events:
        assert e.resent_cost == pytest.approx(e.resent_input_tokens * 3e-6)


def test_legacy_fallback_cost_path():
    """input_cost_rate=None and cost_rate_legacy present -> flag=estimated, use legacy rate."""
    msgs = [{"role": "user", "content": "same"}]
    llm_calls = [
        _mk_llm_call("llm-1", msgs, input_cost_rate=None, cost_rate_legacy=9e-6),
        _mk_llm_call("llm-2", msgs, input_cost_rate=None, cost_rate_legacy=9e-6),
    ]
    trace = _root_only_trace("t9", llm_calls)

    result = find_context_resend(trace)

    assert result.cost_accuracy_flag == "estimated"
    for e in result.resent_events:
        assert e.resent_cost == pytest.approx(e.resent_input_tokens * 9e-6)


def test_share_apportionment():
    """Call with input_tokens=99 and three roughly-equal-length chunks -> ~33 each."""
    # Three near-equal-length JSON chunks. Content differs so all three are
    # separate hashes; then a second call sends the same three chunks -> all
    # three are resent in call 2.
    a = {"role": "user", "content": "aaaaaaaaaa"}
    b = {"role": "user", "content": "bbbbbbbbbb"}
    c = {"role": "user", "content": "cccccccccc"}
    llm_calls = [
        _mk_llm_call("llm-1", [a, b, c], input_tokens=99),
        _mk_llm_call("llm-2", [a, b, c], input_tokens=99),
    ]
    trace = _root_only_trace("ta", llm_calls)

    result = find_context_resend(trace)

    # Three resent events in call 2. Each roughly 33 tokens (sums to ~99).
    assert len(result.resent_events) == 3
    total = sum(e.resent_input_tokens for e in result.resent_events)
    # Rounding may produce sums slightly off from 99; allow ±1 tolerance.
    assert 98 <= total <= 100


def test_deterministic_repeat_run():
    """Prereg §8 determinism: two runs on the same trace produce identical result."""
    msgs = [
        {"role": "user", "content": "u1"},
        {"role": "assistant", "content": "a1"},
        {"role": "user", "content": "u2"},
    ]
    llm_calls = [
        _mk_llm_call("llm-1", msgs),
        _mk_llm_call("llm-2", msgs),
    ]
    trace = _root_only_trace("td", llm_calls)

    r1 = find_context_resend(trace)
    r2 = find_context_resend(trace)

    assert repr(r1) == repr(r2)


def test_apportionment_never_exceeds_input_tokens():
    """Corpus C amendment §10.3: per-call Σ resent_toks ≤ input_tokens.

    18 tiny chunks, all resent in call 2, input_tokens=573. Pre-fix,
    `int(round(share * 573))` on each chunk summed to 576 (+3 excess).
    Post-fix, the per-call budget clamp keeps the sum at 573.
    """
    msgs = [{"role": "user", "content": f"m{i}"} for i in range(18)]
    llm_calls = [
        _mk_llm_call("llm-1", msgs, input_tokens=573),
        _mk_llm_call("llm-2", msgs, input_tokens=573),
    ]
    trace = _root_only_trace("tclamp", llm_calls)

    result = find_context_resend(trace)

    per_call_resent: dict[str, int] = {}
    for e in result.resent_events:
        per_call_resent[e.llm_span_id] = per_call_resent.get(e.llm_span_id, 0) + e.resent_input_tokens
    for span_id, r in per_call_resent.items():
        assert r <= 573, f"span {span_id}: resent={r} exceeds input_tokens=573"
    # Global invariant that the amendment §10.3 diagnostic was checking:
    assert result.resent_input_tokens <= result.total_llm_input_tokens


# ── tier apportionment (CC_USAGE_ATTRIBUTION_DECISION §11) ──────────────────

def _tiered_call(
    span_id: str,
    messages: list[dict[str, str]] | str,
    *,
    uncached: int,
    cache_read: int,
    cache_write: int = 0,
    cache_write_1h: int = 0,
    model: str = "claude-sonnet-4.5",
) -> dict[str, Any]:
    """A call that records how its input was billed, the way Claude Code does.

    `input_tokens` is the sum of the three tiers — the invariant the ingest
    layer guarantees (Cost Attribution Completion prereg §4).
    """
    call = _mk_llm_call(
        span_id,
        messages,
        input_tokens=uncached + cache_read + cache_write,
        input_cost_rate=None,
        model=model,
    )
    call["input_tokens_uncached"] = uncached
    call["input_tokens_cache_read"] = cache_read
    call["input_tokens_cache_write"] = cache_write
    call["input_tokens_cache_write_1h"] = cache_write_1h
    return call


def test_resent_tokens_are_priced_at_the_cache_read_rate_when_they_fit():
    """The defect §11 exists for.

    The second call bills 9,000 tokens as a cache hit and 1,000 as a cache
    write. Its single chunk is entirely resent, so the two bases agree on this
    call by construction — what the test pins is that the ladder reaches the
    same total as the weighted average when the whole call is resent.
    """
    from clew.cost.pricing import get_pricing

    msgs = [{"role": "user", "content": "the same long message"}]
    llm_calls = [
        _tiered_call("llm-1", msgs, uncached=10_000, cache_read=0),
        _tiered_call("llm-2", msgs, uncached=0, cache_read=9_000, cache_write=1_000),
    ]
    trace = _root_only_trace("ttier1", llm_calls)

    result = find_context_resend(trace)
    p = get_pricing("claude-sonnet-4.5")

    second = [e for e in result.resent_events if e.llm_span_id == "llm-2"]
    assert len(second) == 1
    assert second[0].resent_input_tokens == 10_000
    expected = (9_000 * p.cache_read_per_mtok
                + 1_000 * p.cache_write_5m_per_mtok) / 1_000_000.0
    assert second[0].resent_cost == pytest.approx(expected)

    blended_rate = (9_000 * p.cache_read_per_mtok
                    + 1_000 * p.cache_write_5m_per_mtok) / 10_000
    assert expected == pytest.approx(10_000 * blended_rate / 1_000_000.0), (
        "whole call resent: same total, only the split moved"
    )
    assert result.resent_tokens_over_tier_capacity == 0


def test_a_resent_chunk_smaller_than_the_cache_read_rung_pays_only_cache_read():
    """Where §11 changes the number: resent is a strict subset.

    Half the second call input is resent. The cache-read rung alone covers it,
    so none of the cache write may be charged to it. Pre-fix the chunk carried
    half of the write.
    """
    from clew.cost.pricing import get_pricing

    shared = {"role": "user", "content": "x" * 400}
    fresh = {"role": "user", "content": "y" * 400}
    llm_calls = [
        _tiered_call("llm-1", [shared], uncached=5_000, cache_read=0),
        _tiered_call("llm-2", [shared, fresh], uncached=0,
                     cache_read=5_000, cache_write=5_000),
    ]
    trace = _root_only_trace("ttier2", llm_calls)

    result = find_context_resend(trace)
    p = get_pricing("claude-sonnet-4.5")

    second = [e for e in result.resent_events if e.llm_span_id == "llm-2"]
    assert len(second) == 1
    resent = second[0].resent_input_tokens
    assert resent <= 5_000, "the shared half of a 10,000-token call"
    assert second[0].resent_cost == pytest.approx(
        resent * p.cache_read_per_mtok / 1_000_000.0
    )
    # What it used to be: the weighted average of a half-read, half-write call.
    blended_rate = (p.cache_read_per_mtok + p.cache_write_5m_per_mtok) / 2
    assert second[0].resent_cost < resent * blended_rate / 1_000_000.0


def test_the_cheapest_rung_is_not_claimed_twice_by_two_chunks():
    """Two resent chunks in one call share one ladder.

    Both chunks are resent and together they exceed the cache-read rung, so
    the ladder has to carry over: the pair total equals filling read first and
    then the write once, not each chunk filling read from zero.
    """
    from clew.cost.pricing import get_pricing

    a = {"role": "user", "content": "a" * 400}
    b = {"role": "user", "content": "b" * 400}
    llm_calls = [
        _tiered_call("llm-1", [a, b], uncached=8_000, cache_read=0),
        _tiered_call("llm-2", [a, b], uncached=0,
                     cache_read=3_000, cache_write=5_000),
    ]
    trace = _root_only_trace("ttier3", llm_calls)

    result = find_context_resend(trace)
    p = get_pricing("claude-sonnet-4.5")

    second = [e for e in result.resent_events if e.llm_span_id == "llm-2"]
    assert len(second) == 2
    resent = sum(e.resent_input_tokens for e in second)
    assert resent == 8_000, "the whole call is resent"
    expected = (3_000 * p.cache_read_per_mtok
                + 5_000 * p.cache_write_5m_per_mtok) / 1_000_000.0
    assert sum(e.resent_cost for e in second) == pytest.approx(expected)
    assert result.resent_tokens_over_tier_capacity == 0


def test_the_1h_write_rung_is_dearer_and_filled_last():
    """TTL rungs keep their order: read, then the 5m write, then the 1h write.

    Resent is a strict subset here, so the order is observable — it spills out
    of the cache-read rung into the cheaper of the two writes and stops. Had
    the walk taken the 1-hour rung first the same tokens would cost more.
    """
    from clew.cost.pricing import get_pricing

    shared = {"role": "user", "content": "x" * 400}
    fresh = {"role": "user", "content": "y" * 400}
    llm_calls = [
        _tiered_call("llm-1", [shared], uncached=9_000, cache_read=0),
        _tiered_call("llm-2", [shared, fresh], uncached=0, cache_read=3_000,
                     cache_write=6_000, cache_write_1h=4_000),
    ]
    trace = _root_only_trace("ttier4", llm_calls)

    result = find_context_resend(trace)
    p = get_pricing("claude-sonnet-4.5")

    second = [e for e in result.resent_events if e.llm_span_id == "llm-2"]
    assert len(second) == 1
    resent = second[0].resent_input_tokens
    assert 3_000 < resent < 5_000, "spills past the read rung, stops inside 5m"
    into_5m = resent - 3_000
    expected = (3_000 * p.cache_read_per_mtok
                + into_5m * p.cache_write_5m_per_mtok) / 1_000_000.0
    assert second[0].resent_cost == pytest.approx(expected)

    # Had the 1-hour rung been filled before the 5-minute one.
    wrong_order = (3_000 * p.cache_read_per_mtok
                   + into_5m * p.cache_write_1h_per_mtok) / 1_000_000.0
    assert second[0].resent_cost < wrong_order


def test_a_broken_tier_invariant_is_counted_not_dropped():
    """Guard §11.3: if an adapter reports fewer tier tokens than `input_tokens`,
    the excess is priced at the cheapest rung and the count is surfaced —
    rather than falling out of the total silently."""
    from clew.cost.pricing import get_pricing

    msgs = [{"role": "user", "content": "the same long message"}]
    llm_calls = [
        _tiered_call("llm-1", msgs, uncached=10_000, cache_read=0),
        _tiered_call("llm-2", msgs, uncached=0, cache_read=4_000),
    ]
    # Break the invariant the way a miscounting adapter would.
    llm_calls[1]["input_tokens"] = 10_000
    trace = _root_only_trace("ttier5", llm_calls)

    result = find_context_resend(trace)
    p = get_pricing("claude-sonnet-4.5")

    second = [e for e in result.resent_events if e.llm_span_id == "llm-2"]
    assert len(second) == 1
    assert second[0].resent_input_tokens == 10_000
    assert result.resent_tokens_over_tier_capacity == 6_000
    assert second[0].resent_cost == pytest.approx(
        10_000 * p.cache_read_per_mtok / 1_000_000.0
    )


def test_a_flat_rate_call_is_priced_exactly_as_before():
    """Adapters with no tier split cannot express the split, so nothing moves:
    `resent_input_tokens * input_cost_rate`, as it always was."""
    msgs = [{"role": "user", "content": "same"}]
    llm_calls = [
        _mk_llm_call("llm-1", msgs, input_cost_rate=3e-6),
        _mk_llm_call("llm-2", msgs, input_cost_rate=3e-6),
    ]
    trace = _root_only_trace("ttier6", llm_calls)

    result = find_context_resend(trace)

    assert result.resent_events
    for e in result.resent_events:
        assert e.resent_cost == pytest.approx(e.resent_input_tokens * 3e-6)
    assert result.resent_tokens_over_tier_capacity == 0
