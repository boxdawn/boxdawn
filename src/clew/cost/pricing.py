# Pricing tables — sources pinned per entry (URL + verification date).
"""Provider pricing constants for cost attribution.

Cache tier semantics (Anthropic-native, other providers approximated):
- base_input      — uncached input tokens
- cache_read      — cache hit (10% of base for Anthropic; provider-specific)
- cache_write_5m  — cache creation, 5-minute TTL (125% of base for Anthropic)
- cache_write_1h  — cache creation, 1-hour TTL (200% of base for Anthropic)
- output          — output tokens

Non-Anthropic providers: 5m/1h collapse when a provider does not price cache
writes separately (in that case both write columns equal base_input).

Model resolution (`get_pricing`): exact key → alias table → soft-fail default
(warning + Sonnet 4.5). Never raises for unknown model — always returns a
best-effort pricing so cost figures degrade gracefully.
"""
from __future__ import annotations

import re
import warnings
from dataclasses import dataclass

_USD_PER_MTOK = 1_000_000.0


@dataclass(frozen=True)
class ModelPricing:
    name: str
    base_input_per_mtok: float
    cache_read_per_mtok: float
    cache_write_5m_per_mtok: float
    cache_write_1h_per_mtok: float
    output_per_mtok: float
    # The rate set a provider charges when a request's prompt is longer than a
    # threshold. None for a model priced the same at every length. Chosen per
    # call by `pricing_for_prompt`; `resolve_pricing` keeps returning the short
    # rate (Pricing Coverage Stage 2 prereg §1).
    long_context: LongContextTier | None = None

    def base_input_cost(self, tokens: int) -> float:
        return tokens * self.base_input_per_mtok / _USD_PER_MTOK

    def cache_read_cost(self, tokens: int) -> float:
        return tokens * self.cache_read_per_mtok / _USD_PER_MTOK

    def cache_write_5m_cost(self, tokens: int) -> float:
        return tokens * self.cache_write_5m_per_mtok / _USD_PER_MTOK

    def cache_write_1h_cost(self, tokens: int) -> float:
        return tokens * self.cache_write_1h_per_mtok / _USD_PER_MTOK

    def output_cost(self, tokens: int) -> float:
        return tokens * self.output_per_mtok / _USD_PER_MTOK


@dataclass(frozen=True)
class LongContextTier:
    threshold_tokens: int
    pricing: ModelPricing


def pricing_for_prompt(pricing: ModelPricing, prompt_tokens: int) -> ModelPricing:
    """The rate set one request pays, given its prompt length.

    The whole request takes the long rate, output included, once the prompt is
    strictly over the threshold. Prompt length counts every input token, cache
    reads and writes included -- the Anthropic page's own definition, which the
    callers follow by passing uncached + cache_read + cache_write when the call
    reports the split. Below or at the threshold the same object comes back,
    so a model without a tier is priced exactly as before.
    """
    tier = pricing.long_context
    if tier is not None and prompt_tokens > tier.threshold_tokens:
        return tier.pricing
    return pricing


def tier_input_ladder(
    pricing: ModelPricing,
    *,
    uncached: int,
    cache_read: int,
    cache_write_total: int,
    cache_write_1h: int = 0,
) -> list[tuple[float, int]]:
    """One call's input as `(rate $/Mtok, token capacity)` per tier.

    Canonical order: uncached, cache_read, 5-minute write, 1-hour write.
    `tier_input_cost` is the sum of this ladder, so a caller that needs to know
    *which* tier a subset of the tokens sat in — resend apportionment prices
    only the resent part — walks the same four pairs the total was built from
    instead of a second description of them.

    `cache_write_total` is what the provider reported as cache creation;
    `cache_write_1h` is the part of it written with the 1-hour TTL, which
    bills at a higher rate (200% of base for Anthropic, vs 125% for 5m).
    Adapters that do not record the TTL leave `cache_write_1h` at 0, which
    prices the whole write at the 5-minute rate — the behaviour before the
    TTL was read at all.
    """
    w1h = max(0, min(int(cache_write_1h), int(cache_write_total)))
    w5m = int(cache_write_total) - w1h
    return [
        (pricing.base_input_per_mtok, int(uncached)),
        (pricing.cache_read_per_mtok, int(cache_read)),
        (pricing.cache_write_5m_per_mtok, w5m),
        (pricing.cache_write_1h_per_mtok, w1h),
    ]


def tier_input_cost(
    pricing: ModelPricing,
    *,
    uncached: int,
    cache_read: int,
    cache_write_total: int,
    cache_write_1h: int = 0,
) -> float:
    """Input cost for one call, each tier at its own rate.

    One function because three callers price the same call
    (`detect/context_resend.py::_rate_and_cost_for_call`, `report/_model.py`,
    and the waste-rate denominator through the first), and the formula was
    copied into two of them. A further copy for the 1-hour TTL would have let
    them drift apart.

    The summation order is the ladder's canonical order, left to right, which
    is the order this function added the four terms in before the ladder
    existed — so the figure is unchanged bit for bit.
    """
    return sum(
        rate * tokens
        for rate, tokens in tier_input_ladder(
            pricing,
            uncached=uncached,
            cache_read=cache_read,
            cache_write_total=cache_write_total,
            cache_write_1h=cache_write_1h,
        )
    ) / _USD_PER_MTOK


PRICING: dict[str, ModelPricing] = {
    # ── Anthropic ─────────────────────────────────────────────────────────
    # Source: https://platform.claude.com/docs/en/docs/about-claude/pricing
    # Verified: 2026-08-05
    "sonnet-4.5": ModelPricing(
        name="claude-sonnet-4-5",
        base_input_per_mtok=3.0,
        cache_read_per_mtok=0.30,
        cache_write_5m_per_mtok=3.75,
        cache_write_1h_per_mtok=6.00,
        output_per_mtok=15.0,
    ),
    "sonnet-4.6": ModelPricing(
        # Source: https://platform.claude.com/docs/en/docs/about-claude/pricing
        # Verified: 2026-08-05
        name="claude-sonnet-4-6",
        base_input_per_mtok=3.0,
        cache_read_per_mtok=0.30,
        cache_write_5m_per_mtok=3.75,
        cache_write_1h_per_mtok=6.00,
        output_per_mtok=15.0,
    ),
    "opus-4.7": ModelPricing(
        # Source: https://platform.claude.com/docs/en/docs/about-claude/pricing
        # Verified: 2026-08-05
        name="claude-opus-4-7",
        base_input_per_mtok=5.0,
        cache_read_per_mtok=0.50,
        cache_write_5m_per_mtok=6.25,
        cache_write_1h_per_mtok=10.0,
        output_per_mtok=25.0,
    ),
    "opus-5": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-08-27
        # Rates are identical to Opus 4.7 and 4.8; the entry is explicit anyway
        # because `claude-opus-5` does not match the `claude-opus-4` alias
        # prefix, so without it every Opus 5 trace priced as Sonnet 4.5 --
        # measured at 25 of 74 stored runs on 2026-08-27, each carrying an
        # `accuracy_flag` of "accurate" while the rate was a fallback.
        name="claude-opus-5",
        base_input_per_mtok=5.0,
        cache_read_per_mtok=0.50,
        cache_write_5m_per_mtok=6.25,
        cache_write_1h_per_mtok=10.0,
        output_per_mtok=25.0,
    ),
    "opus-5.5": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-10-05
        # 🔴 The first Anthropic model that is CHEAPER than its predecessor at
        # the same tier: $4/$20 against Opus 5's $5/$25. Every rate below the
        # Opus-5 entry's, so resolving an Opus 5.5 trace through the
        # `claude-opus-5` prefix OVERSTATES cost by 25% on tokens and 150% on
        # cache reads. Measured 2026-10-05, before this entry existed.
        # Cache reads are 0.05x base here, not the standard 0.1x.
        name="claude-opus-5-5",
        base_input_per_mtok=4.0,
        cache_read_per_mtok=0.20,
        cache_write_5m_per_mtok=5.0,
        cache_write_1h_per_mtok=8.0,
        output_per_mtok=20.0,
    ),
    "sonnet-5.5": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-10-05
        # Priced identically to Sonnet 5, so the `claude-sonnet-5` prefix was
        # already returning the right number -- by luck, the same luck the
        # Opus 4.8 alias note below describes. The entry exists so that if the
        # two ever diverge, this line is what changes rather than a prefix
        # quietly staying plausible.
        # Re-verified 2026-10-16 (Pricing Coverage Stage 1 prereg §2.1): the
        # page's footnote prices Sonnet 5.5 cache hits at 0.05x base, like
        # Opus 5.5 -- 0.10, not the 0.20 Sonnet 5 charges. So the two had
        # already diverged, on the one column the 2026-10-05 entry copied.
        name="claude-sonnet-5-5",
        base_input_per_mtok=2.0,
        cache_read_per_mtok=0.10,
        cache_write_5m_per_mtok=2.50,
        cache_write_1h_per_mtok=4.0,
        output_per_mtok=10.0,
    ),
    "opus-4.1": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-09-01
        # ★ Three times the price of the Opus the prefix alias used to hand it.
        # A trace naming this model was priced at 5.0 against a real 15.0,
        # silently, because a prefix match reports `matched=True` and warns
        # about nothing -- so it was not in `unpriced_models` either. Retired
        # except on Bedrock and Google Cloud, which is exactly where an old
        # trace comes from.
        name="claude-opus-4-1",
        base_input_per_mtok=15.0,
        cache_read_per_mtok=1.50,
        cache_write_5m_per_mtok=18.75,
        cache_write_1h_per_mtok=30.0,
        output_per_mtok=75.0,
    ),
    "opus-4": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-09-01 · retired except on Google Cloud
        name="claude-opus-4",
        base_input_per_mtok=15.0,
        cache_read_per_mtok=1.50,
        cache_write_5m_per_mtok=18.75,
        cache_write_1h_per_mtok=30.0,
        output_per_mtok=75.0,
    ),
    "haiku-3.5": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-09-01 · retired except on Bedrock and Google Cloud
        # Nothing matched this, so it took the Sonnet 4.5 default at 3.0
        # against a real 0.80 -- 3.75x over, the opposite direction to the
        # Opus cases and for the opposite reason.
        name="claude-haiku-3-5",
        base_input_per_mtok=0.80,
        cache_read_per_mtok=0.08,
        cache_write_5m_per_mtok=1.00,
        cache_write_1h_per_mtok=1.60,
        output_per_mtok=4.0,
    ),
    "mythos-5": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-09-01 · limited availability
        name="claude-mythos-5",
        base_input_per_mtok=10.0,
        cache_read_per_mtok=1.00,
        cache_write_5m_per_mtok=12.50,
        cache_write_1h_per_mtok=20.0,
        output_per_mtok=50.0,
    ),
    "sonnet-5": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-08-27
        # Cheaper than Sonnet 4.6, not equal to it: $2 base against $3. The
        # source page notes the $2/$10 launch pricing became the standard
        # price and the scheduled rise to $3/$15 will not happen, so this is
        # not an introductory rate with an expiry to track.
        name="claude-sonnet-5",
        base_input_per_mtok=2.0,
        cache_read_per_mtok=0.20,
        cache_write_5m_per_mtok=2.50,
        cache_write_1h_per_mtok=4.0,
        output_per_mtok=10.0,
    ),
    "fable-5": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-08-27
        # The entry that matters most for a missing-model fallback: at $10
        # base against the $3 default, an unpriced Fable 5 trace would report
        # roughly a third of its real input cost.
        name="claude-fable-5",
        base_input_per_mtok=10.0,
        cache_read_per_mtok=1.0,
        cache_write_5m_per_mtok=12.50,
        cache_write_1h_per_mtok=20.0,
        output_per_mtok=50.0,
    ),
    "fable-5.1": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-10-05
        # Token rates match Fable 5 exactly; only the cache read differs, and
        # it differs by 4x: 0.025x base ($0.25) against Fable 5's 0.1x ($1.00).
        # A cache-heavy Fable 5.1 trace priced through the `claude-fable-5`
        # prefix overstates its cache-read line by 300%.
        name="claude-fable-5-1",
        base_input_per_mtok=10.0,
        cache_read_per_mtok=0.25,
        cache_write_5m_per_mtok=12.50,
        cache_write_1h_per_mtok=20.0,
        output_per_mtok=50.0,
    ),
    "mythos-5.1": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-10-05
        # Same rates as Fable 5.1, same 0.025x cache read. Limited
        # availability (Project Glasswing), priced here for the same reason
        # `mythos-5` is: a trace we cannot price is a trace we misreport.
        name="claude-mythos-5-1",
        base_input_per_mtok=10.0,
        cache_read_per_mtok=0.25,
        cache_write_5m_per_mtok=12.50,
        cache_write_1h_per_mtok=20.0,
        output_per_mtok=50.0,
    ),
    "haiku-4.5": ModelPricing(
        # Source: https://platform.claude.com/docs/en/docs/about-claude/pricing
        # Verified: 2026-08-05
        name="claude-haiku-4-5",
        base_input_per_mtok=1.0,
        cache_read_per_mtok=0.10,
        cache_write_5m_per_mtok=1.25,
        cache_write_1h_per_mtok=2.0,
        output_per_mtok=5.0,
    ),
    "haiku-5.5": ModelPricing(
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-10-16 · Pricing Coverage Stage 1 prereg §2.1
        # Before this entry the string fell to the Sonnet 4.5 default: 30x
        # over on input. Prompts over 100,000 tokens: `long_context` below.
        name="claude-haiku-5-5",
        base_input_per_mtok=0.10,
        cache_read_per_mtok=0.01,
        cache_write_5m_per_mtok=0.125,
        cache_write_1h_per_mtok=0.20,
        output_per_mtok=0.50,
        # Source: https://platform.claude.com/docs/en/about-claude/pricing
        # Verified: 2026-10-17 · "for prompts over 100,000 tokens", the whole
        # request, cache reads and writes counted in the length (Pricing
        # Coverage Stage 2 prereg §2).
        long_context=LongContextTier(100_000, ModelPricing(
            name="claude-haiku-5-5 (>100k)",
            base_input_per_mtok=0.50,
            cache_read_per_mtok=0.05,
            cache_write_5m_per_mtok=0.625,
            cache_write_1h_per_mtok=1.0,
            output_per_mtok=2.50,
        )),
    ),
    # ── OpenAI ────────────────────────────────────────────────────────────
    # Source: https://openai.com/api/pricing/ (verified via 2026-08 secondary
    # sources; direct fetch returned 403). OpenAI cached input is 50% off base.
    # No separate 5m/1h split — both write columns equal base.
    # Verified: 2026-08-05
    "gpt-4o": ModelPricing(
        name="gpt-4o",
        base_input_per_mtok=2.50,
        cache_read_per_mtok=1.25,
        cache_write_5m_per_mtok=2.50,
        cache_write_1h_per_mtok=2.50,
        output_per_mtok=10.0,
    ),
    "gpt-4o-mini": ModelPricing(
        # Source: https://openai.com/api/pricing/ (verified via secondary 2026-08)
        # Verified: 2026-08-05
        name="gpt-4o-mini",
        base_input_per_mtok=0.15,
        cache_read_per_mtok=0.075,
        cache_write_5m_per_mtok=0.15,
        cache_write_1h_per_mtok=0.15,
        output_per_mtok=0.60,
    ),
    # ── Google Gemini ─────────────────────────────────────────────────────
    # NOTE: Gemini 1.5 family was deprecated by Google in June 2026 (returns
    # 404 on newer endpoints). Kept for historical trace analysis. Values
    # match last-published rates. Cache reads at 10% of base per Google docs.
    # Source: https://ai.google.dev/pricing (historical archived rates)
    # Verified: 2026-08-05 (deprecation note)
    "gemini-1.5-pro": ModelPricing(
        name="gemini-1.5-pro",
        base_input_per_mtok=1.25,
        cache_read_per_mtok=0.125,
        cache_write_5m_per_mtok=1.25,
        cache_write_1h_per_mtok=1.25,
        output_per_mtok=5.0,
    ),
    "gemini-1.5-flash": ModelPricing(
        # Source: https://ai.google.dev/pricing (historical archived rates)
        # Verified: 2026-08-05 (deprecated in June 2026)
        name="gemini-1.5-flash",
        base_input_per_mtok=0.075,
        cache_read_per_mtok=0.0075,
        cache_write_5m_per_mtok=0.075,
        cache_write_1h_per_mtok=0.075,
        output_per_mtok=0.30,
    ),
    # ── OpenAI GPT-5 family ───────────────────────────────────────────────
    # Source: https://openai.com/api/pricing/ (per 2026-08 aggregate published
    # rate; direct provider fetch returned 403 as with GPT-4o).
    # Verified: 2026-08-11 · Cost Table Toolathlon Expansion prereg §2.4
    # Cache reads re-verified 2026-10-16 against
    # https://developers.openai.com/api/docs/pricing (Pricing Coverage Stage 1
    # prereg §2.2): gpt-5, gpt-5-mini, o3 and o4-mini had carried the 50%-off
    # rule written for GPT-4o; the page lists 90% off for the GPT-5 family and
    # 75% off for o3 / o4-mini.
    "gpt-5": ModelPricing(
        name="gpt-5",
        base_input_per_mtok=1.25,
        cache_read_per_mtok=0.125,
        cache_write_5m_per_mtok=1.25,
        cache_write_1h_per_mtok=1.25,
        output_per_mtok=10.0,
    ),
    "gpt-5-mini": ModelPricing(
        # Source: https://openai.com/api/pricing/
        # Verified: 2026-08-11
        name="gpt-5-mini",
        base_input_per_mtok=0.25,
        cache_read_per_mtok=0.025,
        cache_write_5m_per_mtok=0.25,
        cache_write_1h_per_mtok=0.25,
        output_per_mtok=2.0,
    ),
    # ── OpenAI GPT-5.2 (Cost Table Exgentic Expansion prereg §1.2) ────────
    # Source: https://developers.openai.com/api/docs/pricing
    # Verified: 2026-08-13 · Standard tier; cache_write not separately
    # published, defaults to base_input per prereg §2.2.
    "gpt-5.2": ModelPricing(
        name="gpt-5.2",
        base_input_per_mtok=1.75,
        cache_read_per_mtok=0.175,
        cache_write_5m_per_mtok=1.75,
        cache_write_1h_per_mtok=1.75,
        output_per_mtok=14.0,
    ),
    # ── OpenAI o-series reasoning models ──────────────────────────────────
    # NOTE: o-series bills internal reasoning tokens at output rate. The
    # per-token cost figure below is the CONTRACT rate; effective cost per
    # user-facing response is higher (3-10x typical) depending on reasoning
    # depth. WR_cost aggregates over reported tokens, not reasoning-inflated
    # effective tokens; documented for reader interpretation.
    # Source: https://openai.com/api/pricing/
    # Verified: 2026-08-11
    "o3": ModelPricing(
        name="o3",
        base_input_per_mtok=2.0,
        cache_read_per_mtok=0.50,
        cache_write_5m_per_mtok=2.0,
        cache_write_1h_per_mtok=2.0,
        output_per_mtok=8.0,
    ),
    "o4-mini": ModelPricing(
        # Source: https://openai.com/api/pricing/
        # Verified: 2026-08-11
        name="o4-mini",
        base_input_per_mtok=1.10,
        cache_read_per_mtok=0.275,
        cache_write_5m_per_mtok=1.10,
        cache_write_1h_per_mtok=1.10,
        output_per_mtok=4.40,
    ),
    # ── Google Gemini 2.5 / 3.x family ────────────────────────────────────
    # Source: https://ai.google.dev/pricing
    # Verified: 2026-08-11 · Cache read at 10% of base per Google policy.
    "gemini-2.5-pro": ModelPricing(
        name="gemini-2.5-pro",
        base_input_per_mtok=1.25,
        cache_read_per_mtok=0.125,
        cache_write_5m_per_mtok=1.25,
        cache_write_1h_per_mtok=1.25,
        output_per_mtok=10.0,
        # Source: https://ai.google.dev/gemini-api/docs/pricing
        # Verified: 2026-10-17 · Standard, "prompts > 200k tokens"; the short
        # rates above re-read the same day and unchanged.
        long_context=LongContextTier(200_000, ModelPricing(
            name="gemini-2.5-pro (>200k)",
            base_input_per_mtok=2.50,
            cache_read_per_mtok=0.25,
            cache_write_5m_per_mtok=2.50,
            cache_write_1h_per_mtok=2.50,
            output_per_mtok=15.0,
        )),
    ),
    "gemini-2.5-flash": ModelPricing(
        # Source: https://ai.google.dev/pricing
        # Verified: 2026-08-11
        name="gemini-2.5-flash",
        base_input_per_mtok=0.30,
        cache_read_per_mtok=0.030,
        cache_write_5m_per_mtok=0.30,
        cache_write_1h_per_mtok=0.30,
        output_per_mtok=2.50,
    ),
    "gemini-3-pro-preview": ModelPricing(
        # Source: https://ai.google.dev/pricing (preview tier; may change on
        # general availability, forecast in prereg §1.1)
        # Verified: 2026-08-11
        name="gemini-3-pro-preview",
        base_input_per_mtok=2.0,
        cache_read_per_mtok=0.20,
        cache_write_5m_per_mtok=2.0,
        cache_write_1h_per_mtok=2.0,
        output_per_mtok=12.0,
    ),
    # ── xAI Grok family ────────────────────────────────────────────────────
    # Source: https://x.ai/api (xAI console pricing)
    # Verified: 2026-08-11 · No 5m/1h split published by xAI.
    "grok-4": ModelPricing(
        name="grok-4",
        base_input_per_mtok=3.0,
        cache_read_per_mtok=0.75,
        cache_write_5m_per_mtok=3.0,
        cache_write_1h_per_mtok=3.0,
        output_per_mtok=15.0,
    ),
    "grok-4-fast": ModelPricing(
        # Source: https://x.ai/api (Fast-tier rate published alongside Grok 4.1)
        # Verified: 2026-08-11
        name="grok-4-fast",
        base_input_per_mtok=0.20,
        cache_read_per_mtok=0.05,
        cache_write_5m_per_mtok=0.20,
        cache_write_1h_per_mtok=0.20,
        output_per_mtok=0.50,
    ),
    "grok-code-fast-1": ModelPricing(
        # Source: https://x.ai/api (code-fast tier; priced same as Fast per
        # xAI console 2026-08).
        # Verified: 2026-08-11
        name="grok-code-fast-1",
        base_input_per_mtok=0.20,
        cache_read_per_mtok=0.05,
        cache_write_5m_per_mtok=0.20,
        cache_write_1h_per_mtok=0.20,
        output_per_mtok=1.50,
    ),
    # ── DeepSeek v3.x family ──────────────────────────────────────────────
    # Source: https://api-docs.deepseek.com/quick_start/pricing
    # Verified: 2026-08-11 · Cache hit at ~10% of base per DeepSeek docs.
    "deepseek-v3.2": ModelPricing(
        name="deepseek-v3.2",
        base_input_per_mtok=0.28,
        cache_read_per_mtok=0.028,
        cache_write_5m_per_mtok=0.28,
        cache_write_1h_per_mtok=0.28,
        output_per_mtok=0.42,
    ),
    # ── Zhipu GLM ─────────────────────────────────────────────────────────
    # Source: https://open.bigmodel.cn/pricing (best-effort; provider-neutral
    # aggregator confirmation used per prereg §2.4 fallback).
    # Verified: 2026-08-11
    "glm-4.6": ModelPricing(
        name="glm-4.6",
        base_input_per_mtok=0.60,
        cache_read_per_mtok=0.60,  # provider does not publish cache tier
        cache_write_5m_per_mtok=0.60,
        cache_write_1h_per_mtok=0.60,
        output_per_mtok=2.40,
    ),
    # ── Moonshot Kimi K2.5 (Cost Table Exgentic Expansion prereg §1.1) ────
    # Source: https://openrouter.ai/moonshotai/kimi-k2.5
    # Verified: 2026-08-13 · Moonshot's own platform.kimi.ai no longer
    # lists K2.5 (superseded by K2.6 / K2.7 / K3); OpenRouter is used per
    # prereg §2.1 second-choice as a provider-facing aggregator.
    # Cache tier not published on the vendor rate — defaults to base_input
    # per prereg §2.2.
    "kimi-k2.5": ModelPricing(
        name="kimi-k2.5",
        base_input_per_mtok=0.375,
        cache_read_per_mtok=0.375,
        cache_write_5m_per_mtok=0.375,
        cache_write_1h_per_mtok=0.375,
        output_per_mtok=2.025,
    ),
    # ── Moonshot Kimi K2 ──────────────────────────────────────────────────
    # Source: https://platform.moonshot.cn/docs/pricing
    # Verified: 2026-08-11 · K2-0905 (Sep 5) family rate.
    "kimi-k2-0905": ModelPricing(
        name="kimi-k2-0905",
        base_input_per_mtok=0.50,
        cache_read_per_mtok=0.50,
        cache_write_5m_per_mtok=0.50,
        cache_write_1h_per_mtok=0.50,
        output_per_mtok=2.00,
    ),
    # ── MiniMax M2 ────────────────────────────────────────────────────────
    # Source: https://api.minimaxi.com/pricing
    # Verified: 2026-08-11 · Base M2 tier (context window ~200K).
    "minimax-m2": ModelPricing(
        name="minimax-m2",
        base_input_per_mtok=0.30,
        cache_read_per_mtok=0.30,
        cache_write_5m_per_mtok=0.30,
        cache_write_1h_per_mtok=0.30,
        output_per_mtok=1.20,
    ),
    # ── Alibaba Qwen 3 Coder ──────────────────────────────────────────────
    # Source: https://help.aliyun.com/zh/dashscope/pricing
    # Verified: 2026-08-11 · Coder-specific tier.
    "qwen-3-coder": ModelPricing(
        name="qwen-3-coder",
        base_input_per_mtok=0.22,
        cache_read_per_mtok=0.022,
        cache_write_5m_per_mtok=0.22,
        cache_write_1h_per_mtok=0.22,
        output_per_mtok=1.00,
    ),
    # ── Pricing Coverage Stage 1 (docs/PRICING_COVERAGE_STAGE1_PREREG.md §2) ──
    # OpenAI · Source: https://developers.openai.com/api/docs/pricing
    # Verified: 2026-10-16 · Standard tier. Cache write is `-` on the page for
    # every row below, so both write columns equal base; a row with no cached
    # rate published carries base in cache_read too.
    "gpt-5-nano": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="gpt-5-nano",
        base_input_per_mtok=0.05,
        cache_read_per_mtok=0.005,
        cache_write_5m_per_mtok=0.05,
        cache_write_1h_per_mtok=0.05,
        output_per_mtok=0.40,
    ),
    "gpt-5-pro": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="gpt-5-pro",
        base_input_per_mtok=15.0,
        cache_read_per_mtok=15.0,
        cache_write_5m_per_mtok=15.0,
        cache_write_1h_per_mtok=15.0,
        output_per_mtok=120.0,
    ),
    "gpt-5.2-pro": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="gpt-5.2-pro",
        base_input_per_mtok=21.0,
        cache_read_per_mtok=21.0,
        cache_write_5m_per_mtok=21.0,
        cache_write_1h_per_mtok=21.0,
        output_per_mtok=168.0,
    ),
    "gpt-5.4-mini": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="gpt-5.4-mini",
        base_input_per_mtok=0.75,
        cache_read_per_mtok=0.075,
        cache_write_5m_per_mtok=0.75,
        cache_write_1h_per_mtok=0.75,
        output_per_mtok=4.50,
    ),
    "gpt-5.4-nano": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="gpt-5.4-nano",
        base_input_per_mtok=0.20,
        cache_read_per_mtok=0.02,
        cache_write_5m_per_mtok=0.20,
        cache_write_1h_per_mtok=0.20,
        output_per_mtok=1.25,
    ),
    "gpt-4.1": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="gpt-4.1",
        base_input_per_mtok=2.0,
        cache_read_per_mtok=0.50,
        cache_write_5m_per_mtok=2.0,
        cache_write_1h_per_mtok=2.0,
        output_per_mtok=8.0,
    ),
    "gpt-4.1-mini": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="gpt-4.1-mini",
        base_input_per_mtok=0.40,
        cache_read_per_mtok=0.10,
        cache_write_5m_per_mtok=0.40,
        cache_write_1h_per_mtok=0.40,
        output_per_mtok=1.60,
    ),
    "gpt-4.1-nano": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="gpt-4.1-nano",
        base_input_per_mtok=0.10,
        cache_read_per_mtok=0.025,
        cache_write_5m_per_mtok=0.10,
        cache_write_1h_per_mtok=0.10,
        output_per_mtok=0.40,
    ),
    "gpt-4o-2024-05-13": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="gpt-4o-2024-05-13",
        base_input_per_mtok=5.0,
        cache_read_per_mtok=5.0,
        cache_write_5m_per_mtok=5.0,
        cache_write_1h_per_mtok=5.0,
        output_per_mtok=15.0,
    ),
    "o1": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="o1",
        base_input_per_mtok=15.0,
        cache_read_per_mtok=7.50,
        cache_write_5m_per_mtok=15.0,
        cache_write_1h_per_mtok=15.0,
        output_per_mtok=60.0,
    ),
    "o1-pro": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="o1-pro",
        base_input_per_mtok=150.0,
        cache_read_per_mtok=150.0,
        cache_write_5m_per_mtok=150.0,
        cache_write_1h_per_mtok=150.0,
        output_per_mtok=600.0,
    ),
    "o3-pro": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="o3-pro",
        base_input_per_mtok=20.0,
        cache_read_per_mtok=20.0,
        cache_write_5m_per_mtok=20.0,
        cache_write_1h_per_mtok=20.0,
        output_per_mtok=80.0,
    ),
    "o3-mini": ModelPricing(
        # Source: https://developers.openai.com/api/docs/pricing
        # Verified: 2026-10-16
        name="o3-mini",
        base_input_per_mtok=1.10,
        cache_read_per_mtok=0.55,
        cache_write_5m_per_mtok=1.10,
        cache_write_1h_per_mtok=1.10,
        output_per_mtok=4.40,
    ),
    # Google · Source: https://ai.google.dev/gemini-api/docs/pricing
    # Verified: 2026-10-16 · text/image/video input rate.
    "gemini-3-flash-preview": ModelPricing(
        name="gemini-3-flash-preview",
        base_input_per_mtok=0.50,
        cache_read_per_mtok=0.05,
        cache_write_5m_per_mtok=0.50,
        cache_write_1h_per_mtok=0.50,
        output_per_mtok=3.00,
    ),
    # Moonshot · Source: https://platform.moonshot.ai/docs/pricing/chat
    # Verified: 2026-10-16 · the K2-series table publishes no cache-write price.
    "kimi-k2.6": ModelPricing(
        name="kimi-k2.6",
        base_input_per_mtok=0.95,
        cache_read_per_mtok=0.16,
        cache_write_5m_per_mtok=0.95,
        cache_write_1h_per_mtok=0.95,
        output_per_mtok=4.00,
    ),
    # Alibaba · Source: https://www.alibabacloud.com/help/en/model-studio/model-pricing
    # Verified: 2026-10-16 · International, 0 < tokens <= 256K. No cache tier
    # published.
    "qwen-3.6-plus": ModelPricing(
        name="qwen-3.6-plus",
        base_input_per_mtok=0.50,
        cache_read_per_mtok=0.50,
        cache_write_5m_per_mtok=0.50,
        cache_write_1h_per_mtok=0.50,
        output_per_mtok=3.00,
        # Source: https://www.alibabacloud.com/help/en/model-studio/model-pricing
        # Verified: 2026-10-17 · International, 256K < tokens <= 1M. "K" read
        # as 1,000 (Pricing Coverage Stage 2 prereg §1).
        long_context=LongContextTier(256_000, ModelPricing(
            name="qwen-3.6-plus (>256K)",
            base_input_per_mtok=2.00,
            cache_read_per_mtok=2.00,
            cache_write_5m_per_mtok=2.00,
            cache_write_1h_per_mtok=2.00,
            output_per_mtok=6.00,
        )),
    ),
}


DEFAULT_MODEL_KEY = "sonnet-4.5"


# Alias table: provider-emitted model strings → PRICING keys.
# Longest-match wins (so gpt-4o-mini-2024-07 does not incorrectly hit gpt-4o).
_ALIASES: tuple[tuple[str, str], ...] = (
    # OpenAI: gpt-4o-mini variants MUST match before gpt-4o (longest prefix)
    ("gpt-4o-mini", "gpt-4o-mini"),
    # A dated snapshot priced apart from the family: under the alias boundary
    # its date is a version suffix of `gpt-4o`, so only order keeps it out.
    ("gpt-4o-2024-05-13", "gpt-4o-2024-05-13"),
    ("gpt-4o", "gpt-4o"),
    ("gpt-4.1-mini", "gpt-4.1-mini"),
    ("gpt-4.1-nano", "gpt-4.1-nano"),
    ("gpt-4.1", "gpt-4.1"),
    # Anthropic
    ("claude-sonnet-4-5", "sonnet-4.5"),
    ("claude-sonnet-4.5", "sonnet-4.5"),
    ("claude-3-5-sonnet", "sonnet-4.5"),
    ("claude-3.5-sonnet", "sonnet-4.5"),
    ("claude-sonnet-4-6", "sonnet-4.6"),
    ("claude-sonnet-4.6", "sonnet-4.6"),
    # Sonnet 4 is priced as Sonnet 4.5; below both 4-5 and 4-6 on purpose.
    ("claude-sonnet-4", "sonnet-4.5"),
    # 🔴 Point releases sit ABOVE the release they extend. `resolve_pricing`
    # takes the FIRST matching prefix, not the longest, so order is the
    # correctness property here: with `claude-opus-5` first, every
    # `claude-opus-5-5` string resolved to Opus 5's rates -- 25% high on
    # tokens, 150% high on cache reads -- and `matched` came back True, so no
    # warning fired. An unknown model warns; a newer model whose name extends
    # an older one's does not. Measured 2026-10-05.
    ("claude-opus-5-5", "opus-5.5"),
    ("claude-opus-5.5", "opus-5.5"),
    ("claude-opus-5", "opus-5"),
    ("claude-fable-5-1", "fable-5.1"),
    ("claude-fable-5.1", "fable-5.1"),
    ("claude-fable-5", "fable-5"),
    ("claude-sonnet-5-5", "sonnet-5.5"),
    ("claude-sonnet-5.5", "sonnet-5.5"),
    ("claude-sonnet-5", "sonnet-5"),
    # Opus 4.8 already resolved through the `claude-opus-4` prefix below, and
    # by luck to the right number -- 4.7 and 4.8 are priced identically. The
    # explicit alias removes the luck: if the two ever diverge, this line is
    # what has to change, rather than a fallback quietly staying plausible.
    ("claude-opus-4-8", "opus-4.7"),
    ("claude-opus-4.8", "opus-4.7"),
    ("claude-opus-4-7", "opus-4.7"),
    ("claude-opus-4.7", "opus-4.7"),
    # Exgentic canonical `claude-opus-4-5`: Opus 4.5 rate ($5/$25 per
    # Anthropic pricing 2026-08-13) matches opus-4.7 exactly; explicit
    # alias documents intent and locks against `claude-opus-4` drift.
    ("claude-opus-4-6", "opus-4.7"),   # same rate as 4.7; see §1.3 note above
    ("claude-opus-4.6", "opus-4.7"),
    ("claude-opus-4-5", "opus-4.7"),
    ("claude-opus-4.5", "opus-4.7"),
    ("claude-opus-4-1", "opus-4.1"),
    ("claude-opus-4.1", "opus-4.1"),
    # Bare `claude-opus-4` is Opus 4 at three times the 4.x rate. Every more
    # specific Opus prefix sits above this line on purpose: `startswith` takes
    # the first match, so a 4.5 reaching here would be priced as a 4.
    ("claude-opus-4", "opus-4"),
    ("claude-haiku-4-5", "haiku-4.5"),
    ("claude-haiku-3-5", "haiku-3.5"),
    ("claude-haiku-3.5", "haiku-3.5"),
    ("claude-3-5-haiku", "haiku-3.5"),   # date-first legacy naming
    ("claude-haiku-5-5", "haiku-5.5"),
    ("claude-haiku-5.5", "haiku-5.5"),
    ("claude-mythos-5-1", "mythos-5.1"),
    ("claude-mythos-5.1", "mythos-5.1"),
    ("claude-mythos-5", "mythos-5"),
    ("claude-haiku-4.5", "haiku-4.5"),
    # Google
    ("gemini-1.5-pro", "gemini-1.5-pro"),
    ("gemini-1.5-flash", "gemini-1.5-flash"),
    # ── Toolathlon Expansion (Cost Table Toolathlon Expansion prereg §1) ──
    # These aliases resolve the 22 `modelname_run` values (including the
    # `_1`/`_2`/`_3` run-index suffix Toolathlon appends) via startswith
    # prefix match. Order matters: more-specific prefixes must precede
    # less-specific ones (e.g. gpt-5-mini before gpt-5).
    # OpenAI GPT-5 / o-series family (longest first)
    # Cost Table Exgentic Expansion prereg §1.4: gpt-5.2 must precede
    # gpt-5.1 / gpt-5-mini / gpt-5-high / gpt-5 so the Exgentic canonical
    # `gpt-5.2-2025-12-11` resolves via startswith on `gpt-5.2`.
    ("gpt-5.2-pro", "gpt-5.2-pro"),
    ("gpt-5.2", "gpt-5.2"),
    ("gpt-5.1", "gpt-5"),        # minor variant, same base rate
    ("gpt-5.4-mini", "gpt-5.4-mini"),
    ("gpt-5.4-nano", "gpt-5.4-nano"),
    ("gpt-5-mini", "gpt-5-mini"),
    ("gpt-5-nano", "gpt-5-nano"),
    ("gpt-5-pro", "gpt-5-pro"),
    ("gpt-5-high", "gpt-5"),      # high-throughput variant, same base rate
    ("gpt-5", "gpt-5"),
    ("o4-mini", "o4-mini"),
    ("o3-mini", "o3-mini"),
    ("o3-pro", "o3-pro"),
    ("o3", "o3"),
    ("o1-pro", "o1-pro"),
    ("o1", "o1"),
    # Anthropic 4.x historical model IDs Toolathlon uses
    ("claude-4.5-sonnet-0929", "sonnet-4.5"),
    ("claude-4.5-opus", "opus-4.7"),  # nearest known Opus rate
    ("claude-4.5-haiku-1001", "haiku-4.5"),
    ("claude-4-sonnet-0514", "sonnet-4.5"),  # Sonnet 4.0 (2024-05); same $3/$15 tier
    # Google Gemini 2.5 / 3.x
    ("gemini-3-pro-preview", "gemini-3-pro-preview"),
    ("gemini-3-flash-preview", "gemini-3-flash-preview"),
    ("gemini-2.5-pro", "gemini-2.5-pro"),
    ("gemini-2.5-flash", "gemini-2.5-flash"),
    # xAI Grok (longest first)
    ("grok-code-fast-1", "grok-code-fast-1"),
    ("grok-4-fast", "grok-4-fast"),
    ("grok-4", "grok-4"),
    # DeepSeek (both variants share v3.2 rate per DeepSeek pricing page)
    ("deepseek-3.2-thinking", "deepseek-v3.2"),
    ("deepseek-v3.2-exp", "deepseek-v3.2"),
    ("deepseek-v3.2", "deepseek-v3.2"),
    # Others
    ("glm-4.6", "glm-4.6"),
    # Cost Table Exgentic Expansion prereg §1.4: kimi-k2.5 must precede
    # kimi-k2-0905 (Moonshot K2.5 is a distinct rate tier from K2-0905).
    ("kimi-k2.6", "kimi-k2.6"),
    ("kimi-k2.5", "kimi-k2.5"),
    ("kimi-k2-0905", "kimi-k2-0905"),
    ("minimax-m2", "minimax-m2"),
    ("qwen-3-coder", "qwen-3-coder"),
    ("qwen-3.6-plus", "qwen-3.6-plus"),
    ("qwen3.6-plus", "qwen-3.6-plus"),
)

# Pricing Coverage Stage 1 prereg §1.1: Bedrock inference-profile prefix
# (`us.anthropic.`, `global.anthropic.`, bare `anthropic.`).
_BEDROCK_PROFILE = re.compile(r"^(?:[a-z]{2,6}\.)?anthropic\.")

# Prereg §1.2: what may follow an alias prefix and still be that model --
# dates, MMDD, Google `-001`, Bedrock `-v1:0`, `-latest`, the Toolathlon run
# index `_1`, an `@provider` routing tag. Anything else (`-nano`, `-pro`,
# `.4`, `-8b`) is a different model.
_VERSION_SUFFIXES = re.compile(
    r"(?:-\d{8}|-\d{4}-\d{2}-\d{2}|-\d{4}|-\d{3}|-v\d+(?::\d+)?|-latest|_\d+|@[\w.-]+)*"
)


def build_default_cost_tables() -> tuple[dict[str, float], dict[str, float]]:
    """Build ($/input-token, $/output-token) exact-match tables covering PRICING
    canonical keys + `.name` values + `_ALIASES` prefixes, each with the
    Toolathlon run-suffix variants (`_1`, `_2`, `_3`).

    Used by the CLI (`python -m clew`) to auto-populate cost tables so `WR_cost`
    fires on default runs. Diagnostic scripts (`field_test/diagnostics/`) build
    their own tables against the same source of truth. Only `base_input_per_mtok`
    and `output_per_mtok` are exposed — cache-tier splits stay opt-in via the
    detector-side APIs.
    """
    input_ct: dict[str, float] = {}
    output_ct: dict[str, float] = {}

    seed: list[tuple[str, ModelPricing]] = []
    for canonical_key, pricing in PRICING.items():
        seed.append((canonical_key, pricing))
        seed.append((pricing.name, pricing))
    for prefix, target_key in _ALIASES:
        seed.append((prefix, PRICING[target_key]))

    for key, pricing in seed:
        input_rate = pricing.base_input_per_mtok / _USD_PER_MTOK
        output_rate = pricing.output_per_mtok / _USD_PER_MTOK
        input_ct[key] = input_rate
        output_ct[key] = output_rate
        for suffix in ("_1", "_2", "_3"):
            input_ct[key + suffix] = input_rate
            output_ct[key + suffix] = output_rate

    return input_ct, output_ct


def get_pricing(model_key: str | None = None) -> ModelPricing:
    """Resolve a model identifier to a `ModelPricing` entry.

    Priority (per Cost Attribution Completion prereg §3):
      1. `None` → default (Sonnet 4.5)
      2. Exact key match against PRICING
      3. Longest-prefix alias match (case-insensitive, whitespace-stripped)
      4. Unknown → emit UserWarning, return default (soft-fail)

    Never raises. Callers get a best-effort pricing rather than a crash.
    """
    pricing, matched = resolve_pricing(model_key)
    if not matched and model_key is not None:
        warnings.warn(
            f"pricing: unknown model {model_key!r}; using default "
            f"{DEFAULT_MODEL_KEY!r} (Sonnet 4.5 rates)",
            stacklevel=2,
        )
    return pricing


def resolve_pricing(model_key: str | None) -> tuple[ModelPricing, bool]:
    """Same resolution as `get_pricing`, and whether it found anything.

    Two callers need different things from one lookup. A human at a terminal
    wants the warning; a report needs to record that a rate was substituted, in
    a field a downstream consumer can read -- the warning goes to stderr, where
    the storage layer and the dashboard never see it. Measured 2026-08-27: 25 of
    74 stored runs were priced at the default and labeled `accurate`, and
    nothing in the report said so.

    `matched` is False when the default was substituted, including when
    `model_key` is None -- an absent model is not a priced one.

    The default is Sonnet 4.5, which is *cheaper* than the Opus tier it most
    often stands in for, so a substituted rate understates cost rather than
    inflating it. Those 25 runs were priced at 60% of the correct rate.
    """
    if model_key is None:
        return PRICING[DEFAULT_MODEL_KEY], False

    normalized = model_key.strip().lower()
    # Provider routing (`bedrock/`, `openrouter/<vendor>/`, `dashscope/`) and a
    # Bedrock profile prefix name where the call went, not what it cost.
    normalized = normalized.rsplit("/", 1)[-1]
    normalized = _BEDROCK_PROFILE.sub("", normalized)

    if normalized in PRICING:
        return PRICING[normalized], True

    # First alias whose remainder is only version suffixes. A bare
    # `startswith` let `gpt-5` answer for `gpt-5-nano` (25x over) and `o3`
    # for `o3-pro` (10x under) with `matched=True` and no warning; now a name
    # the table does not know comes back unmatched, which is visible.
    for prefix, target_key in _ALIASES:
        if normalized.startswith(prefix) and _VERSION_SUFFIXES.fullmatch(
            normalized[len(prefix):]
        ):
            return PRICING[target_key], True

    return PRICING[DEFAULT_MODEL_KEY], False


def call_prompt_tokens(call: dict) -> int:
    """One adapter call's prompt length: the cache split when reported, else input_tokens."""
    split = (call.get("input_tokens_uncached"), call.get("input_tokens_cache_read"),
             call.get("input_tokens_cache_write"))
    if any(v is not None for v in split):
        return sum(int(v or 0) for v in split)
    return int(call.get("input_tokens") or 0)


def long_context_override(call: dict) -> ModelPricing | None:
    """The long-rate entry this call pays, or None when nothing changes.

    One rule for every adapter call site (Pricing Coverage Stage 2 prereg §7.2).
    The entry it returns replaces both the short-rate entry and any rate an
    adapter copied from it into `input_cost_rate` / `output_cost_rate` -- the
    CLI copies the default tables into every call, so without the replacement
    a long request would get its input at the long rate and its output at the
    short one. A call whose length was apportioned rather than reported
    (Toolathlon) never takes a tier: no request had that length.
    """
    if call.get("prompt_tokens_apportioned"):
        return None
    model = call.get("model")
    if not isinstance(model, str) or not model:
        return None
    pricing, _matched = resolve_pricing(model)
    chosen = pricing_for_prompt(pricing, call_prompt_tokens(call))
    return chosen if chosen is not pricing else None
