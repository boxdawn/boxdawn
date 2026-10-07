"""tests/cost/test_tier_input_cost.py — one formula, and the 1h rate reaches it.

`cache_write_1h_per_mtok` sat in the table with no call site: every cache
write was priced at the 5-minute rate. These assert the rate is now reachable
and that the two callers price a call identically.
"""
from __future__ import annotations

from clew.cost.pricing import get_pricing, tier_input_cost
from clew.detect.context_resend import input_cost_for_call
from clew.report._model import _llm_call_input_cost


def _call(write_total: int, write_1h: int) -> dict:
    return {
        "model": "claude-opus-4-7",
        "input_tokens": 1_000 + write_total,
        "input_tokens_uncached": 1_000,
        "input_tokens_cache_read": 0,
        "input_tokens_cache_write": write_total,
        "input_tokens_cache_write_1h": write_1h,
    }


def test_the_one_hour_share_costs_more_than_the_same_tokens_at_5m():
    p = get_pricing("claude-opus-4-7")
    assert p.cache_write_1h_per_mtok > p.cache_write_5m_per_mtok

    all_5m = tier_input_cost(
        p, uncached=0, cache_read=0, cache_write_total=1_000_000, cache_write_1h=0
    )
    all_1h = tier_input_cost(
        p,
        uncached=0,
        cache_read=0,
        cache_write_total=1_000_000,
        cache_write_1h=1_000_000,
    )

    assert all_5m == p.cache_write_5m_per_mtok
    assert all_1h == p.cache_write_1h_per_mtok


def test_a_one_hour_write_is_not_priced_as_a_five_minute_one():
    cheap = input_cost_for_call(_call(write_total=100_000, write_1h=0))
    dear = input_cost_for_call(_call(write_total=100_000, write_1h=100_000))

    assert dear > cheap


def test_the_1h_share_cannot_exceed_the_write_it_is_part_of():
    """A sub-object larger than its total must not invent tokens."""
    p = get_pricing("claude-opus-4-7")

    clamped = tier_input_cost(
        p, uncached=0, cache_read=0, cache_write_total=1_000, cache_write_1h=9_999
    )

    assert clamped == tier_input_cost(
        p, uncached=0, cache_read=0, cache_write_total=1_000, cache_write_1h=1_000
    )


def test_the_detector_and_the_report_price_a_call_the_same():
    """Two callers, one formula — they used to carry separate copies of it."""
    call = _call(write_total=50_000, write_1h=30_000)

    from_detector = input_cost_for_call(call)
    from_report, was_accurate, _substituted = _llm_call_input_cost(call)

    assert was_accurate
    assert from_report == from_detector


def test_a_call_without_the_1h_field_prices_as_it_did_before():
    call = _call(write_total=50_000, write_1h=0)
    call.pop("input_tokens_cache_write_1h")

    p = get_pricing("claude-opus-4-7")
    expected = tier_input_cost(
        p, uncached=1_000, cache_read=0, cache_write_total=50_000, cache_write_1h=0
    )

    assert input_cost_for_call(call) == expected
