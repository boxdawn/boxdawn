# Pricing Coverage Stage 1 — Pre-registration

**Status.** Pre-registration. Per rule 8 this document is pushed and
PR-opened before any pricing entry, alias, resolver change or test lands.
The entry set, the rates, the resolver rule and the predictions below are
frozen; adjusting them after seeing results is not allowed.

**Date.** 2026-10-16. Every source below was fetched on this date as the
provider's raw page (`.md` endpoint or rendered page text), not through a
summarising model.

## 0. Why, and why only this stage

A census of every model string in the local corpora (`data/`, the
Hugging Face cache, live Claude Code sessions under `~/.claude/projects`)
resolved against `src/clew/cost/pricing.py::resolve_pricing` found three
kinds of defect:

1. **Silent mispricing — `matched=True`, wrong rate.** No warning fires,
   and the report labels the figure as priced from the table.
   - `startswith` prefix capture: `gpt-5` captures `gpt-5-nano` (25× over),
     `gpt-5-pro` (12× under) and every `gpt-5.4`–`gpt-5.6` string; `o3`
     captures `o3-mini` (1.8× over) and `o3-pro` (10× under); `gpt-5.2`
     captures `gpt-5.2-pro` (12× under); `gpt-4o` captures
     `gpt-4o-2024-05-13` (2× under). `o3-mini` is observed 1,190 times
     (TRAIL).
   - Existing entries whose cache-read rate disagrees with the provider page:
     `gpt-5` 0.625 (page 0.125), `gpt-5-mini` 0.125 (0.025), `o3` 1.0 (0.50),
     `o4-mini` 0.55 (0.275), `sonnet-5.5` 0.20 (0.10 — the page's footnote 2
     prices Sonnet 5.5 cache hits at 0.05× base, like Opus 5.5).
2. **Unknown → Sonnet 4.5 fallback, observed in data.** `claude-haiku-5-5`
   (43 live CC records; 30× over on input), `dashscope/qwen3.6-plus` (5,709,
   RedundancyBench), `moonshotai/Kimi-K2.6` (93, agent-race),
   `bedrock/us.anthropic.claude-opus-4-6-v1` (26, agent-race).
3. **Prompt-length tiers the table cannot express** (one rate set per
   model): Haiku 5.5 (>100k), Qwen 3.6 Plus (>256K), OpenAI 5.4+/6.x
   (long context), Gemini 2.5 Pro / 3.1 Pro (>200k).

Measured before writing this, to decide what stage 1 must carry:

| Published figure | What it prices | Touched by stage 1? | Touched by tiers (stage 2)? |
|---|---|---|---|
| Corpus A (trace-commons, 28 CC) | `claude-opus-4-8` 56.5% / `claude-sonnet-4-6` 43.5% of $397.53 | no — both entries unchanged | no — Claude 4.6+ is single-rate to 1M (page §Long context pricing) |
| Corpus B (Toolathlon, 22 families) | base input + output only, uncached by adapter pre-commitment | no — no base/output rate of the 22 changes; cache rates unused | not applicable — per-call input is apportioned from trajectory totals, not reported (200k-window models show >272k calls) |
| Corpus C (Exgentic) | 5 models | no — none of the 5 entries changes | — |
| Corpus D (MIMO CC) | carries no `WR_cost` (its prereg §3) | no — `mimo-v2.5-pro` is excluded (§3) | — |
| trace-commons dollar range | same 28 CC sessions as A | no | no |

Stage 1 therefore corrects **live reports** — a user's trace that names one
of these models — and changes no published number. Prompt-length tiers are
stage 2 under a separate pre-registration: on the data we have they move no
published figure, and the one tiered model observed in live CC use
(Haiku 5.5) had 0 of 27 deduplicated calls over 100k.

## 1. Resolver change (frozen)

`resolve_pricing(model_key)` keeps its contract (returns
`(ModelPricing, matched)`, never raises, Sonnet 4.5 default) and changes in
two places.

### 1.1 Provider-prefix normalisation

After `strip().lower()`:

1. keep only the text after the last `/`
   (`bedrock/…`, `anthropic/…`, `openrouter/<vendor>/…`, `moonshotai/…`,
   `dashscope/…`);
2. remove a leading Bedrock inference-profile prefix
   `^(?:[a-z]{2,6}\.)?anthropic\.` (`us.anthropic.`, `eu.anthropic.`,
   `global.anthropic.`, `anthropic.`).

Regional / cross-region endpoint surcharges (+10% on Claude 4.5+) are not
modelled; a Bedrock string is priced at the first-party list rate.

### 1.2 Alias boundary

An alias prefix matches only when the remainder of the string after it is
empty or consists solely of version suffixes:

```
(?:-\d{8}|-\d{4}-\d{2}-\d{2}|-\d{4}|-\d{3}|-v\d+(?::\d+)?|-latest|_\d+|@[\w.-]+)*
```

(dates, `MMDD`, Google `-001`, Bedrock `-v1:0`, `-latest`, Toolathlon run
index `_1`, `@provider` routing tag). A prefix whose remainder is anything
else — `-nano`, `-pro`, `-mini`, `.4`, `-8b` — does not match, and the scan
continues to later aliases; if none matches, the result is the default with
`matched=False`, which warns and is recorded in `unpriced_models`.

This turns every future `gpt-5.N` / `claude-opus-5-N` string from a silent
wrong rate into a visible unknown.

## 2. Entries (frozen)

Rates in $/MTok as `base / cache_read / cache_write_5m / cache_write_1h /
output`. Where a provider publishes no cache tier, the column takes the
`COST_TABLE_EXGENTIC_EXPANSION_PREREG.md` §2.2 default (equal to base).
Source priority as in that document §2.1: provider page first.

### 2.1 Anthropic — `https://platform.claude.com/docs/en/about-claude/pricing`

| Key | Rates | Change |
|---|---|---|
| `haiku-5.5` | 0.10 / 0.01 / 0.125 / 0.20 / 0.50 | new · prompts ≤100k only (§0, stage 2) · aliases `claude-haiku-5-5`, `claude-haiku-5.5` |
| `sonnet-5.5` | 2.0 / **0.10** / 2.50 / 4.0 / 10.0 | cache_read 0.20 → 0.10 |
| alias `claude-sonnet-4` → `sonnet-4.5` | 3 / 0.30 / 3.75 / 6 / 15 | alias only — Sonnet 4 row equals Sonnet 4.5; placed below `claude-sonnet-4-5`/`-4-6` |
| alias `claude-3-5-haiku` → `haiku-3.5` | 0.80 / 0.08 / 1.00 / 1.60 / 4.0 | alias only (date-first legacy naming) |

### 2.2 OpenAI — `https://developers.openai.com/api/docs/pricing` (Standard)

Cache write is `-` on the page for every row below → equals base.

| Key | base / cache_read / output | Change |
|---|---|---|
| `gpt-5` | 1.25 / **0.125** / 10.0 | cache_read 0.625 → 0.125 |
| `gpt-5-mini` | 0.25 / **0.025** / 2.0 | cache_read 0.125 → 0.025 |
| `o3` | 2.0 / **0.50** / 8.0 | cache_read 1.0 → 0.50 |
| `o4-mini` | 1.10 / **0.275** / 4.40 | cache_read 0.55 → 0.275 |
| `gpt-5-nano` | 0.05 / 0.005 / 0.40 | new |
| `gpt-5-pro` | 15.0 / 15.0 / 120.0 | new (no cached rate published) |
| `gpt-5.2-pro` | 21.0 / 21.0 / 168.0 | new |
| `gpt-5.4-mini` | 0.75 / 0.075 / 4.50 | new (no long-context row) |
| `gpt-5.4-nano` | 0.20 / 0.02 / 1.25 | new (no long-context row) |
| `gpt-4.1` | 2.0 / 0.50 / 8.0 | new |
| `gpt-4.1-mini` | 0.40 / 0.10 / 1.60 | new |
| `gpt-4.1-nano` | 0.10 / 0.025 / 0.40 | new |
| `gpt-4o-2024-05-13` | 5.0 / 5.0 / 15.0 | new |
| `o1` | 15.0 / 7.50 / 60.0 | new |
| `o1-pro` | 150.0 / 150.0 / 600.0 | new |
| `o3-pro` | 20.0 / 20.0 / 80.0 | new |
| `o3-mini` | 1.10 / 0.55 / 4.40 | new |

### 2.3 Google — `https://ai.google.dev/gemini-api/docs/pricing`

| Key | Rates | Change |
|---|---|---|
| `gemini-3-flash-preview` | 0.50 / 0.05 / 0.50 / 0.50 / 3.00 | new (text/image/video rate) |

Existing `gemini-2.5-pro` / `gemini-2.5-flash` rows match the page at
≤200k; unchanged.

### 2.4 Moonshot — `https://platform.moonshot.ai/docs/pricing/chat`

| Key | Rates | Change |
|---|---|---|
| `kimi-k2.6` | 0.95 / 0.16 / 0.95 / 0.95 / 4.00 | new · K2-series table publishes no cache-write price |

### 2.5 Alibaba — `https://www.alibabacloud.com/help/en/model-studio/model-pricing`

| Key | Rates | Change |
|---|---|---|
| `qwen-3.6-plus` | 0.50 / 0.50 / 0.50 / 0.50 / 3.00 | new · International, 0<tokens≤256K only · alias `qwen3.6-plus` · observed max prompt 15,170 tokens over 11,418 calls |

## 3. Deliberately not in this stage

- `mimo-v2.5-pro` — Corpus D's prereg §3 states the corpus carries no
  `WR_cost`; pricing it would create a published-figure candidate outside
  that prereg. The model ID is also retired on 2026-10-21 per the provider.
- Models whose page price depends on prompt length and that are **not
  observed** in any local corpus: `gpt-5.4`, `gpt-5.4-pro`, `gpt-5.5`,
  `gpt-5.5-pro`, `gpt-5.6-*`, `gpt-6-*`, `gpt-6.1-*`, `gemini-3.1-pro-preview`.
  After §1.2 they resolve as unknown (visible), not as `gpt-5` (silent).
- Strings with no row on a fetched provider page: `claude-3-7-sonnet-*`
  (TRAIL), `DeepSeek-V3.1-Terminus` (DeepSeek's page lists only V4),
  `gemini-2.0-flash`; bare `haiku` / `sonnet`; `<synthetic>`; object
  reprs. These stay unknown.
- DeepSeek peak/off-peak, Bedrock/Vertex regional surcharges, US-only
  `inference_geo` 1.1×, fast mode, batch — not modelled.
- `report/_model.py` and the other callers: unchanged. Only the table and
  `resolve_pricing` change.

## 4. Tests

- New: each §2 rate; each §1.1 normalisation shape; each §1.2 rejection
  (`gpt-5-nano` is not `gpt-5`, `o3-pro` is not `o3`, `gpt-5.2-pro` is not
  `gpt-5.2`, `gpt-5.6-sol` and `claude-opus-5-9` are unmatched) and each
  accepted suffix shape (`-20251001`, `-2025-12-11`, `-v1:0`, `_2`,
  `@anthropic`, `-latest`, `-002`).
- Two existing assertions encode a rate the provider page contradicts and
  are changed, not deleted:
  - `get_pricing("gpt-4o-2024-05-13") is PRICING["gpt-4o"]` → the new
    `gpt-4o-2024-05-13` entry ($5/$15 on the page).
  - `("claude-sonnet-5-5", 2.0, 0.20, 10.0)` → `0.10`.
- One existing assertion becomes unmatched by §1.2 and is changed to assert
  that: `gemini-1.5-flash-8b` (a different, separately priced model, no
  longer on the page).
- Full suite must pass; no test is skipped or removed.

## 5. Predictions (frozen)

Measured with a census script (uncommitted) over the same three roots.

- **P1 — census flips.** Of the distinct observed strings, exactly these
  change resolution; every other string resolves to the identical
  `ModelPricing` object as before:
  - unmatched → matched: `claude-haiku-5-5` → `haiku-5.5`;
    `dashscope/qwen3.6-plus` → `qwen-3.6-plus`; `moonshotai/Kimi-K2.6` →
    `kimi-k2.6`; `bedrock/us.anthropic.claude-opus-4-6-v1` → `opus-4.7`.
  - matched → matched, different entry: `o3-mini` (`o3` → `o3-mini`).
  - matched → unmatched: none.
- **P2 — Corpus A** dollar total under the census probe is bit-identical
  ($397.53, 866 + 3,480 priced calls).
- **P3 — Corpus B** predicted dollar total over 66 files is bit-identical
  ($8,082.05), as is every per-family total.
- **P4 — Corpus C** the five Exgentic strings (`DeepSeek-V3.2`,
  `Kimi-K2.5`, `claude-opus-4-5`, `gemini-3-pro-preview`,
  `gpt-5.2-2025-12-11`) resolve to the same objects as before.
- **P5 — live CC** the 27 deduplicated `claude-haiku-5-5` calls price at
  $0.0596 (from $1.79); 0 of them exceed 100k.

A miss on P1–P4 means the change reaches a published figure or a string it
was not meant to reach; it stops the stage and is reported as a miss, not
widened.

## 6. After the predictions are checked

Shipped-report bug → release procedure (7 steps) and notice to the web and
marketing sessions. The notice states that no published figure moved and
lists the strings whose priced cost changes for users.
