# Pricing Coverage Stage 1 — Results

**Pre-registration.** `docs/PRICING_COVERAGE_STAGE1_PREREG.md` (commit `440d3e0`).
**Code.** commit `0321918` — `src/clew/cost/pricing.py`, `tests/cost/test_pricing.py`.
**Measured.** 2026-10-16, with the uncommitted census and probe scripts the
prereg §5 names, run once against `440d3e0` (before) and once against
`0321918` (after).

## Verdict

P1–P5 all hit. No published figure moved.

## P1 — census flips: HIT

158 distinct strings over the three roots, the same 158 before and after.
Exactly five change resolution, and they are the five the prereg listed:

| String | Observed | Before | After |
|---|---:|---|---|
| `dashscope/qwen3.6-plus` | 5,709 | default, unmatched | `qwen-3.6-plus` |
| `o3-mini` | 1,190 | `o3` | `o3-mini` |
| `moonshotai/Kimi-K2.6` | 93 | default, unmatched | `kimi-k2.6` |
| `claude-haiku-5-5` | 43 | default, unmatched | `haiku-5.5` |
| `bedrock/us.anthropic.claude-opus-4-6-v1` | 26 | default, unmatched | `opus-4.7` |

Matched → unmatched: none. Every other string resolves to the same entry
as before.

## P2 — Corpus A: HIT

28 sessions, `total_usd = 397.53358534999995` before and after; the
per-model lines (`claude-opus-4-8` 866 calls, `claude-sonnet-4-6` 3,480
calls) are identical at full float precision.

## P3 — Corpus B: HIT

66 files, `grand_usd = 8082.0503719199905` before and after; all 22
per-family totals are identical at full float precision.

## P4 — Corpus C: HIT

`DeepSeek-V3.2`, `Kimi-K2.5`, `claude-opus-4-5`, `gemini-3-pro-preview`,
`gpt-5.2-2025-12-11` resolve to the same `ModelPricing` values before and
after, all matched.

## P5 — live CC Haiku 5.5: HIT

27 deduplicated `claude-haiku-5-5` calls price at $0.0596 after the change;
0 of them exceed 100k prompt tokens. The $1.79 "before" figure is the
prereg's own measurement and was not re-run here.

## Tests

`tests/cost/test_pricing.py`: 185 passed after the change; the new tests
fail against the old table (45 failures, measured with the old
`pricing.py` swapped back in). Full suite: 1163 passed, 1 xfailed (the
pre-existing `test_seed42_manifest_sha_matches_frozen`), 0 failed.

One guard outside the pricing tests caught a gap during the change:
`tests/test_claims_are_counted.py::test_every_pricing_entry_carries_its_source_and_date`
requires a source URL and verification date inside every entry block, not
only in a group header; the 13 new OpenAI rows carry both.

## What changes for users

No published figure moves. A user's report changes priced cost when its
trace names one of these:

- `claude-haiku-5-5` / `claude-haiku-5.5` — was the Sonnet 4.5 default, now
  Haiku 5.5 (≤100k rate).
- `claude-sonnet-5-5` — cache reads 0.20 → 0.10.
- `gpt-5`, `gpt-5-mini`, `gpt-5.1`, `gpt-5-high`, `o3`, `o4-mini` — cache
  reads corrected (base and output unchanged).
- `gpt-5-nano`, `gpt-5-pro`, `gpt-5.2-pro`, `o3-mini`, `o3-pro`,
  `gpt-4o-2024-05-13` — were captured by a shorter prefix, now their own
  rows.
- `gpt-4.1*`, `gpt-5.4-mini`, `gpt-5.4-nano`, `o1`, `o1-pro`,
  `gemini-3-flash-preview`, `kimi-k2.6`, `qwen3.6-plus`, Bedrock /
  `provider/` prefixed Claude strings — were the default, now priced.
- Any `gpt-5.N`, `claude-*-N-M` or other extension of a known name that the
  table does not list (e.g. `gpt-5.4`, `gpt-5.6-*`) — was silently priced as
  the shorter name, now unmatched: warns and is listed in `unpriced_models`.
