# Spec: docs/CONTEXT_RESEND_DETECTOR_PREREG.md (pinned Rule 8 prereg).
"""Context Resend Detector — deterministic detection of resent LLM input chunks.

Given a trace with `metadata["llm_calls"]` populated (per prereg §3), the
detector flags message chunks that appear in the input of two or more LLM
calls within the same trace. Chunk boundary follows the JSON-first rule
(§2); system-role chunks are exempt (§1.2). Cost is estimated by per-call
apportionment of the provider-reported input tokens to chunks proportional
to their tokenized length (§4).

Deterministic guarantees (§8): sha256 hashing, JSON-parse chunk boundary,
tiktoken with pinned version for share calculation. No LLM-as-judge, no
embedding.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Literal

from clew.cost.pricing import (
    ModelPricing,
    get_pricing,
    tier_input_cost,
    tier_input_ladder,
)
from clew.model import Trace


CostAccuracy = Literal["accurate", "estimated"]


@dataclass
class ResentEvent:
    llm_span_id: str
    origin_llm_span_id: str
    chunk_hash: str
    chunk_role: str | None
    resent_input_tokens: int
    resent_cost: float


@dataclass
class ContextResendResult:
    trace_id: str
    resent_events: list[ResentEvent] = field(default_factory=list)
    resent_input_tokens: int = 0
    resent_cost: float = 0.0
    total_llm_input_tokens: int = 0
    total_llm_input_cost: float = 0.0
    cost_accuracy_flag: CostAccuracy = "accurate"
    # Guard (`docs/CC_USAGE_ATTRIBUTION_DECISION.md` §11.3): resent tokens that
    # exceeded the sum
    # of their call's tier capacities and were therefore priced at the call's
    # cheapest rate. Zero whenever `input_tokens == uncached + cache_read +
    # cache_write`, the invariant the ingest layer guarantees; non-zero means
    # an adapter broke it and the figure below is a floor for those tokens.
    resent_tokens_over_tier_capacity: int = 0


# ── Chunk boundary (prereg §2) ───────────────────────────────────────────────

def _chunk_boundary(input_text: str) -> list[tuple[str, str | None]]:
    """Return list of (chunk_text_for_hashing, role_or_None) per prereg §2.

    Priority (first match):
      1. JSON list -> each element is one chunk.
      2. JSON dict with `messages` key whose value is a list -> each element.
      3. Otherwise (parse failure or unrecognized shape) -> entire input as
         one chunk.

    Chunk text for hashing is json.dumps(elem, sort_keys=True,
    ensure_ascii=False) for parsed elements, or the raw string in the
    fallback case. Role extraction: dict element with "role" key -> that
    value; else None.
    """
    try:
        parsed = json.loads(input_text)
    except (json.JSONDecodeError, TypeError):
        return [(input_text, None)]

    elements: list[Any] | None = None
    if isinstance(parsed, list):
        elements = parsed
    elif isinstance(parsed, dict):
        messages = parsed.get("messages")
        if isinstance(messages, list):
            elements = messages

    if elements is None:
        # Recognized JSON but not the expected shape — treat whole string as
        # one chunk (fallback). Rehash the original input_text verbatim so
        # cross-call byte-exactness holds without re-serialization drift.
        return [(input_text, None)]

    out: list[tuple[str, str | None]] = []
    for elem in elements:
        text = json.dumps(elem, sort_keys=True, ensure_ascii=False)
        role: str | None = None
        if isinstance(elem, dict):
            r = elem.get("role")
            if isinstance(r, str):
                role = r
        out.append((text, role))
    return out


def _sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ── Token share (prereg §4) ──────────────────────────────────────────────────

def _chunk_token_len(text: str, model: str | None) -> int:
    """tiktoken length for share calculation only (prereg §4).

    Encoding pick (frozen for v1):
      - Any model containing 'gpt-4o' or 'o200k' -> o200k_base
      - Anthropic Claude family (name contains 'claude') -> cl100k_base
        (Anthropic tokenizer is not tiktoken-native; this is an
        approximation, acceptable because these values enter only into
        chunk share ratios, not absolute token counts)
      - Everything else (including gpt-4, gpt-3.5, unknown) -> cl100k_base
      - tiktoken import failure or encoding failure -> len(text) // 4 + 1

    A minimum of 1 token per non-empty chunk protects the share ratio
    from divide-by-zero when all chunks are extremely short.
    """
    try:
        import tiktoken
    except ImportError:
        return max(1, len(text) // 4) if text else 0

    if not text:
        return 0

    encoding_name = "cl100k_base"
    if model:
        low = model.lower()
        if "gpt-4o" in low or "o200k" in low:
            encoding_name = "o200k_base"

    try:
        enc = tiktoken.get_encoding(encoding_name)
        return max(1, len(enc.encode(text)))
    except Exception:
        return max(1, len(text) // 4)


# ── Detector entry point ────────────────────────────────────────────────────

def has_tier_split(call: dict[str, Any]) -> bool:
    """Whether this call records how its input was billed across cache tiers.

    The condition is named because two modules branch on it and they must
    branch identically: `_rate_and_cost_for_call` below, and the waste-rate
    denominator (WR_COST_PRICE_BASIS_AMENDMENT_PREREG §2). Adapters that do not
    record tiers leave all three fields None; Toolathlon sets them to
    uncached-only zeros, which is a tier split that happens to be flat.
    """
    return any(
        call.get(key) is not None
        for key in (
            "input_tokens_uncached",
            "input_tokens_cache_read",
            "input_tokens_cache_write",
        )
    )


def input_cost_for_call(call: dict[str, Any]) -> float:
    """What this call's input actually cost, tiers included.

    The public form of the pricing the resend numerator already uses. Exposed
    so the denominator can be computed by the same rule rather than by a second
    one that agrees with it only by accident.
    """
    _rate, cost, _pricing = _rate_and_cost_for_call(call)
    return cost


def _ladder_for_call(call: dict[str, Any]) -> list[tuple[float, int]]:
    """One call's input as `(rate $/token, token capacity)`, cheapest first.

    The same five-step resolution as `_rate_and_cost_for_call` (tier split →
    caller rate → legacy rate → pricing.py → nothing), but it keeps the tiers
    apart instead of averaging them. Resend apportionment walks this ladder:
    a resent chunk is content the call sent before, so it sits in the cheap end
    of the call's own billing, and charging it the weighted average made it
    carry a share of the cache *write* that paid for the new content.

    Cheapest first is a choice where the provider does not tell us which chunk
    sat in which tier. It follows `cache_creation_ttl_mismatch_count`'s rule
    (`ingest/claude_code.py`): where the split is undecidable, price at the
    lower rate and surface a count, never round up into the dearer tier. On the
    cited trace the mechanically-ordered alternative (cache prefix first, then
    the write, then the tail) differs by $0.00004.

    Capacity totals `input_tokens` on every branch, so the clamp that keeps
    Σ resent ≤ `input_tokens` also keeps resent inside the ladder.
    """
    input_tokens_val = call.get("input_tokens")
    input_tokens = int(input_tokens_val) if input_tokens_val is not None else 0

    if has_tier_split(call):
        model = call.get("model")
        pricing = get_pricing(model) if model else get_pricing(None)
        ladder = tier_input_ladder(
            pricing,
            uncached=int(call.get("input_tokens_uncached") or 0),
            cache_read=int(call.get("input_tokens_cache_read") or 0),
            cache_write_total=int(call.get("input_tokens_cache_write") or 0),
            cache_write_1h=int(call.get("input_tokens_cache_write_1h") or 0),
        )
        rungs = [
            (rate / 1_000_000.0, tokens) for rate, tokens in ladder if tokens > 0
        ]
    else:
        # Flat-rate branches have one tier, so the ladder reproduces the old
        # multiplication exactly; step (5) keeps its silent zero.
        rate, _cost, _pricing = _rate_and_cost_for_call(call)
        rungs = [(rate, input_tokens)]

    # Ties keep canonical tier order (sorted is stable), so the walk is
    # deterministic for providers that price two tiers the same.
    return sorted(rungs, key=lambda rung: rung[0])


def _price_against_ladder(
    rungs: list[tuple[float, int]], consumed: int, tokens: int,
) -> tuple[float, int]:
    """Cost of `tokens` starting at offset `consumed` in `rungs`.

    Returns `(cost, over_capacity_tokens)`. Tokens past the last rung are
    priced at the cheapest rate and reported, rather than silently dropped —
    a dropped token is a dollar the report never mentions.
    """
    cost = 0.0
    skip = consumed
    left = tokens
    for rate, capacity in rungs:
        if skip >= capacity:
            skip -= capacity
            continue
        available = capacity - skip
        skip = 0
        take = min(left, available)
        cost += take * rate
        left -= take
        if left <= 0:
            return cost, 0
    if rungs:
        cost += left * rungs[0][0]
    # A tier split reporting no tokens at all leaves `rungs` empty, so the
    # whole amount lands in the count rather than costing zero unremarked.
    return cost, left


def _rate_and_cost_for_call(
    call: dict[str, Any],
) -> tuple[float, float, ModelPricing | None]:
    """Resolve (per-token rate for apportionment, total-input cost for this call, pricing).

    Priority (Cost Attribution Completion prereg §4 · Context Resend prereg §4):
      1. Tier-split fields populated → pricing.py tier-accurate.
      2. Explicit `input_cost_rate` (caller override at ingest) → flat rate.
      3. `cost_rate_legacy` present → flat rate (Context Resend prereg §4
         backward compat guarantee — do NOT skip past legacy just because
         pricing.py exists; callers wired legacy for a reason).
      4. Otherwise, resolve model via `get_pricing()` → base_input flat.
      5. Nothing available → 0.0 (silent, degrade).
    """
    input_tokens_val = call.get("input_tokens")
    input_tokens = int(input_tokens_val) if input_tokens_val is not None else 0
    uncached = call.get("input_tokens_uncached")
    cache_read = call.get("input_tokens_cache_read")
    cache_write = call.get("input_tokens_cache_write")
    model = call.get("model")

    # (1) tier-split path
    if has_tier_split(call):
        pricing = get_pricing(model) if model else get_pricing(None)
        u = int(uncached or 0)
        r = int(cache_read or 0)
        w = int(cache_write or 0)
        total = u + r + w
        total_cost = tier_input_cost(
            pricing,
            uncached=u,
            cache_read=r,
            cache_write_total=w,
            cache_write_1h=int(call.get("input_tokens_cache_write_1h") or 0),
        )
        # Effective per-token rate for apportionment (weighted average).
        eff_rate = (total_cost / total) if total > 0 else 0.0
        return eff_rate, total_cost, pricing

    # (2) caller-supplied flat input rate
    input_cost_rate = call.get("input_cost_rate")
    if input_cost_rate is not None:
        rate = float(input_cost_rate)
        return rate, input_tokens * rate, None

    # (3) legacy fallback (respects Context Resend prereg §4 backward compat)
    legacy = call.get("cost_rate_legacy")
    if legacy is not None:
        rate = float(legacy)
        return rate, input_tokens * rate, None

    # (4) pricing.py default when nothing else specified
    if model:
        pricing = get_pricing(model)
        rate = pricing.base_input_per_mtok / 1_000_000.0
        return rate, input_tokens * rate, pricing

    # (5) nothing available
    return 0.0, 0.0, None


def find_context_resend(trace: Trace, n: int = 2) -> ContextResendResult:
    """Detect and cost context resend events within a single trace (prereg §1).

    Args:
        trace: post-preprocess trace with `metadata["llm_calls"]` populated.
        n: minimum occurrences (>= 2) for a chunk to be flagged. Default 2.

    Returns:
        `ContextResendResult` with per-event breakdown, sums, denominators,
        and `cost_accuracy_flag` per §4.

    Cost path (Cost Attribution Completion prereg §4):
        When tier-split token fields (`input_tokens_uncached`,
        `input_tokens_cache_read`, `input_tokens_cache_write`) are populated
        by the ingest layer, the detector reports tier-accurate cost per
        call and marks the result "accurate". Legacy path (only
        `input_tokens` populated) falls back to a flat rate and reports
        "estimated".
    """
    if n < 2:
        raise ValueError("n must be >= 2")

    llm_calls: list[dict[str, Any]] = list(trace.metadata.get("llm_calls") or [])
    result = ContextResendResult(trace_id=trace.trace_id)

    if not llm_calls:
        return result

    # Accuracy flag: "accurate" iff every call has tier-split populated OR
    # a caller-provided input_cost_rate. Any call falling back to legacy
    # cost_rate_legacy (or nothing) downgrades the whole result.
    def _is_call_accurate(c: dict[str, Any]) -> bool:
        has_split = (
            c.get("input_tokens_uncached") is not None
            or c.get("input_tokens_cache_read") is not None
            or c.get("input_tokens_cache_write") is not None
        )
        has_flat = c.get("input_cost_rate") is not None
        return has_split or has_flat

    result.cost_accuracy_flag = (
        "accurate" if all(_is_call_accurate(c) for c in llm_calls) else "estimated"
    )

    # Pre-compute per-call chunk annotations, denominators, and effective rates.
    per_call: list[list[tuple[str, str | None, int]]] = []
    per_call_ladder: list[list[tuple[float, int]]] = []
    occurrence_count: dict[str, int] = {}
    total_input_tokens = 0
    total_input_cost = 0.0

    for call in llm_calls:
        input_text: str = call.get("input_text") or ""
        model: str | None = call.get("model")
        input_tokens_val = call.get("input_tokens")
        input_tokens = int(input_tokens_val) if input_tokens_val is not None else 0

        _rate, call_cost, _pricing = _rate_and_cost_for_call(call)

        total_input_tokens += input_tokens
        total_input_cost += call_cost

        chunks = _chunk_boundary(input_text)
        annotated: list[tuple[str, str | None, int]] = []
        for chunk_text, role in chunks:
            chash = _sha256_hex(chunk_text)
            annotated.append((chunk_text, role, _chunk_token_len(chunk_text, model)))
            occurrence_count[chash] = occurrence_count.get(chash, 0) + 1
        per_call.append(annotated)
        per_call_ladder.append(_ladder_for_call(call))

    result.total_llm_input_tokens = total_input_tokens
    result.total_llm_input_cost = total_input_cost

    # Second pass — walk chunks in trace order. Count running occurrences of
    # each hash. The first `n-1` occurrences are the "origin plus any pre-n
    # repeats"; from the `n`-th occurrence onward, flag as resent (prereg §1:
    # "all occurrences after the first"). Track origin span_id for reporting.
    running_count: dict[str, int] = {}
    origin_span_for_hash: dict[str, str] = {}

    for i, call in enumerate(llm_calls):
        annotated = per_call[i]
        if not annotated:
            continue

        input_tokens_val = call.get("input_tokens")
        input_tokens = int(input_tokens_val) if input_tokens_val is not None else 0
        rungs = per_call_ladder[i]
        # How much of this call's ladder earlier chunks of the same call
        # already took, so two resent chunks cannot both claim the cheapest
        # rung.
        ladder_consumed = 0

        share_total = sum(t for _, _, t in annotated)
        if share_total == 0:
            continue

        # Per-call budget so Σ resent_toks_within_call never exceeds
        # input_tokens for that call — rounding on `int(round(share * X))`
        # can push the sum a few tokens over otherwise (Corpus C amendment
        # §10.3 · 77/10,056 sessions previously showed wr_char up to 1.0035).
        remaining_budget = input_tokens

        for chunk_text, role, chunk_toks in annotated:
            chash = _sha256_hex(chunk_text)

            new_count = running_count.get(chash, 0) + 1
            running_count[chash] = new_count

            if chash not in origin_span_for_hash:
                origin_span_for_hash[chash] = call["span_id"]

            # First occurrence never flagged (necessary payload, prereg §1).
            # And only flag if the chunk's total across-trace count reaches n.
            if new_count < n:
                continue
            if occurrence_count[chash] < n:
                continue

            # §1.2 system-role exemption
            if role == "system":
                continue

            share = chunk_toks / share_total
            resent_toks = int(round(share * input_tokens))
            # Clamp: keeps Σ_within_call ≤ input_tokens_call so per-session
            # wr_char cannot exceed 1.0. Order-deterministic (trace order).
            resent_toks = max(0, min(resent_toks, remaining_budget))
            remaining_budget -= resent_toks
            # Tier-aware apportionment walks the call's own tier ladder
            # cheapest-rung first (usage attribution decision §11.2) rather than
            # multiplying by one weighted-average rate, which made every
            # resent chunk carry a share of the cache write.
            resent_cost, over_capacity = _price_against_ladder(
                rungs, ladder_consumed, resent_toks,
            )
            ladder_consumed += resent_toks
            result.resent_tokens_over_tier_capacity += over_capacity

            result.resent_events.append(ResentEvent(
                llm_span_id=call["span_id"],
                origin_llm_span_id=origin_span_for_hash[chash],
                chunk_hash=chash,
                chunk_role=role,
                resent_input_tokens=resent_toks,
                resent_cost=resent_cost,
            ))
            result.resent_input_tokens += resent_toks
            result.resent_cost += resent_cost

    return result
