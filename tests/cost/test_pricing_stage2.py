"""Pricing Coverage Stage 2 — prompt-length tiers (docs/PRICING_COVERAGE_STAGE2_PREREG.md)."""
from __future__ import annotations

import pytest

from clew.cost.pricing import (
    PRICING,
    long_context_override,
    pricing_for_prompt,
)

TIERS = {
    # key: (threshold, long base, long cache_read, long 5m, long 1h, long output)
    "haiku-5.5": (100_000, 0.50, 0.05, 0.625, 1.0, 2.50),
    "qwen-3.6-plus": (256_000, 2.00, 2.00, 2.00, 2.00, 6.00),
    "gemini-2.5-pro": (200_000, 2.50, 0.25, 2.50, 2.50, 15.0),
}


@pytest.mark.parametrize("key", sorted(TIERS))
def test_tier_rates_and_boundary(key):
    threshold, base, read, w5, w1, out = TIERS[key]
    entry = PRICING[key]
    assert entry.long_context.threshold_tokens == threshold
    assert pricing_for_prompt(entry, 0) is entry
    assert pricing_for_prompt(entry, threshold) is entry   # "over" is strict
    long = pricing_for_prompt(entry, threshold + 1)
    assert (long.base_input_per_mtok, long.cache_read_per_mtok, long.cache_write_5m_per_mtok,
            long.cache_write_1h_per_mtok, long.output_per_mtok) == (base, read, w5, w1, out)


def test_no_other_entry_carries_a_tier():
    assert sorted(k for k, v in PRICING.items() if v.long_context is not None) == sorted(TIERS)


def _haiku_call(prompt, **extra):
    """A Claude Code-shaped call: 1 uncached token, the rest cache read."""
    call = {
        "model": "claude-haiku-5-5",
        "input_tokens": prompt,
        "input_tokens_uncached": 1,
        "input_tokens_cache_read": prompt - 1,
        "input_tokens_cache_write": 0,
        "input_tokens_cache_write_1h": 0,
        "output_tokens": 1_000,
    }
    call.update(extra)
    return call


def _expected(prompt, long):
    rates = TIERS["haiku-5.5"][1:] if long else (0.10, 0.01, 0.125, 0.20, 0.50)
    base, read, _w5, _w1, out = rates
    return (1 * base + (prompt - 1) * read) / 1e6, 1_000 * out / 1e6


@pytest.mark.parametrize("prompt,long", [(100_000, False), (100_001, True)])
def test_report_prices_both_sides_at_the_tier(prompt, long):
    from clew.report._model import _llm_call_input_cost, _llm_call_output_cost

    exp_in, exp_out = _expected(prompt, long)
    # The CLI copies the short rate into every call; the tier must still win.
    call = _haiku_call(prompt, input_cost_rate=0.10 / 1e6, output_cost_rate=0.50 / 1e6)
    cost_in, accurate, substituted = _llm_call_input_cost(call)
    assert cost_in == pytest.approx(exp_in, rel=1e-12)
    assert accurate is True and substituted is None
    assert _llm_call_output_cost(call)[0] == pytest.approx(exp_out, rel=1e-12)


@pytest.mark.parametrize("prompt,long", [(100_000, False), (100_001, True)])
def test_context_resend_prices_input_at_the_tier(prompt, long):
    from clew.detect.context_resend import _ladder_for_call, input_cost_for_call

    exp_in, _ = _expected(prompt, long)
    call = _haiku_call(prompt, input_cost_rate=0.10 / 1e6)
    assert input_cost_for_call(call) == pytest.approx(exp_in, rel=1e-12)
    ladder_cost = sum(rate * tokens for rate, tokens in _ladder_for_call(call))
    assert ladder_cost == pytest.approx(exp_in, rel=1e-12)


@pytest.mark.parametrize("prompt,long", [(100_000, False), (100_001, True)])
def test_guard_prices_the_whole_request_at_the_tier(prompt, long):
    from clew.guard import _call_cost

    exp_in, exp_out = _expected(prompt, long)
    msg = {"model": "claude-haiku-5-5", "usage": {
        "input_tokens": 1, "cache_read_input_tokens": prompt - 1,
        "cache_creation_input_tokens": 0, "output_tokens": 1_000}}
    usd, _model, matched = _call_cost(msg)
    assert matched is True
    assert usd == pytest.approx(exp_in + exp_out, rel=1e-12)


def test_apportioned_length_never_takes_a_tier():
    """Toolathlon apportions a trajectory's input across calls; no request had it."""
    call = {"model": "gemini-2.5-pro_1", "input_tokens": 300_000,
            "input_tokens_uncached": 300_000, "input_tokens_cache_read": 0,
            "input_tokens_cache_write": 0, "prompt_tokens_apportioned": True}
    assert long_context_override(call) is None
    del call["prompt_tokens_apportioned"]
    assert long_context_override(call) is pricing_for_prompt(PRICING["gemini-2.5-pro"], 300_001)


def test_toolathlon_marks_every_call_apportioned():
    from clew.ingest.toolathlon import _reconstruct_llm_calls

    messages = [{"role": "user", "content": "hi"},
                {"role": "assistant", "content": "a"},
                {"role": "assistant", "content": "b"}]
    calls = _reconstruct_llm_calls(
        messages, {"input_tokens": 400_000, "output_tokens": 10, "agent_llm_requests": 2},
        "gemini-2.5-pro_1", None, None)
    assert calls and all(c["prompt_tokens_apportioned"] is True for c in calls)
