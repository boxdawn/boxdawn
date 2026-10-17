# Pricing Coverage Stage 2 — Pre-registration

**Scope.** Prompt-length rate tiers: a request whose prompt is longer than a
provider's threshold pays a different rate set. Stage 1
(`docs/PRICING_COVERAGE_STAGE1_PREREG.md` §0 item 3) deferred this because
the table holds one rate set per model.
**Written.** 2026-10-17, before any code change, on `main` at `c19fc50`.
**Code and results** follow as separate commits on the same branch.

## 0. Why, and what the data says first

Three entries already in the table carry a longer-prompt rate on their
provider's page. Today the table prices every request at the short rate:

| Key | Threshold | Short rate (in table) | Long rate (page) |
|---|---|---|---|
| `haiku-5.5` | prompt > 100,000 tokens | 0.10 / 0.01 / 0.125 / 0.20 / 0.50 | 0.50 / 0.05 / 0.625 / 1.0 / 2.50 |
| `qwen-3.6-plus` | prompt > 256K tokens | 0.50 / 0.50 / 0.50 / 0.50 / 3.00 | 2.00 / 2.00 / 2.00 / 2.00 / 6.00 |
| `gemini-2.5-pro` | prompt > 200k tokens | 1.25 / 0.125 / 1.25 / 1.25 / 10.0 | 2.50 / 0.25 / 2.50 / 2.50 / 15.0 |

Rates are $/MTok as `base / cache_read / cache_write_5m / cache_write_1h / output`.
Where a provider publishes no cache tier, the column equals base, as in
stage 1 §2. Under-pricing is the direction of the error: a long Haiku 5.5
request is billed 5× on every column, and the report shows it at 1×. The
budget guard (`clew.guard`, 0.5.18) reads the same table, so a session that
crossed its cap can read as under it.

Measured before writing this (census script, uncommitted, over
`~/.claude/projects` and `data/`; one call per `message.id`, prompt =
`input + cache_read + cache_creation`):

| Key | Calls with per-call usage | Over threshold | Max prompt |
|---|---:|---:|---:|
| `haiku-5.5` | 46 (all live Claude Code) | **0** | 55,856 |
| `qwen-3.6-plus` | 0 — its 5,709 RedundancyBench records carry no token counts | — | — |
| `gemini-2.5-pro` | 0 — seen only in Toolathlon, which prices from flat per-model tables | — | — |

On the data we have, stage 2 moves **no dollar**. It corrects what a user's
report and budget guard would say on a long request.

## 1. Mechanism (frozen)

- `ModelPricing` gains an optional field `long_context`, default `None`, of
  type `LongContextTier(threshold_tokens: int, pricing: ModelPricing)`.
- New `pricing_for_prompt(pricing, prompt_tokens) -> ModelPricing` returns
  `pricing.long_context.pricing` when `long_context` is set and
  `prompt_tokens > threshold_tokens`, and otherwise returns `pricing` itself.
  "Over" is strict: a prompt equal to the threshold pays the short rate.
- **Prompt length** is `uncached + cache_read + cache_write` when the call
  reports the cache split, otherwise `input_tokens`. Anthropic's page says
  this explicitly: the prompt length *"counts all of its input tokens,
  including cache reads and cache writes"*. The whole request takes the tier,
  output included, on all three pages.
- **`K` is read as 1,000.** Alibaba writes `256K`. The band 256,001–262,144
  is the only place a 1,024 reading would differ, and 0 calls are observed
  there.
- `resolve_pricing` is unchanged and still returns the short-rate entry.
  The tier is chosen per call, where that call's prompt length is known.

### 1.1 Where the tier is applied

| Call site | What it prices |
|---|---|
| `report/_model.py` `_llm_call_input_cost`, `_llm_call_output_cost` | report cost summary (`total_llm_input_cost`, `total_llm_output_cost`, `total_analyzed_cost`) |
| `detect/context_resend.py` `_ladder_for_call` (tier ladder) and `_rate_and_cost_for_call` branches (1) and (4) | resend dollars and the waste-rate cost denominator |
| `guard.py` `_call_cost` | budget guard total |

Through `_rate_and_cost_for_call` the tier also reaches the callers that
already share it: `metrics/waste_rate.py` (via `input_cost_for_call`),
`detect/redundant_read.py` and `llm_judge/semantic_duplicate.py`. They keep
pricing by the same rule as the resend numerator, which is why they share it.

### 1.2 Where it is not, on purpose

- **Flat-rate paths:** Toolathlon's per-model tables
  (`build_default_cost_tables`), a caller-supplied `input_cost_rate`, and
  `cost_rate_legacy`. These carry one rate by contract, and Toolathlon's
  per-call input is apportioned from trajectory totals rather than reported
  (stage 1 §0 table).
- **`cost/amplification.py`:** a structural estimate whose report text
  states the rate assumed. It is not a per-call bill.
- **The judges' own API cost** (`llm_judge/*`): one short prompt per trace
  to `claude-haiku-4-5`, which carries no tier.

## 2. Entries (frozen)

Each long-context row is attached to the existing entry, with a source URL
and a verification date inside the entry block (the
`test_claims_are_counted` rule). The short-rate rows are unchanged.

| Key | Source (fetched 2026-10-17, raw page) | Long rate |
|---|---|---|
| `haiku-5.5` | `https://platform.claude.com/docs/en/about-claude/pricing` — "Claude Haiku 5.5 (for prompts over 100,000 tokens)" | 0.50 / 0.05 / 0.625 / 1.0 / 2.50, threshold 100,000 |
| `qwen-3.6-plus` | `https://www.alibabacloud.com/help/en/model-studio/model-pricing` — International, `256K<Token≤1M` | 2.00 / 2.00 / 2.00 / 2.00 / 6.00, threshold 256,000 |
| `gemini-2.5-pro` | `https://ai.google.dev/gemini-api/docs/pricing` — Standard, "prompts > 200k tokens" | 2.50 / 0.25 / 2.50 / 2.50 / 15.0, threshold 200,000 |

The page's short rates for these three were re-read on the same day and match
the table.

## 3. Deliberately not in this stage

- Models with a long-context tier that are **not in the table**: `gpt-5.4`,
  `gpt-5.4-pro`, `gpt-5.5`, `gpt-5.5-pro`, `gpt-5.6-*`, `gpt-6-*`,
  `gpt-6.1-*` (>272K), `gemini-3.1-pro-preview` (>200k). Stage 1 §3 left them
  unknown, and so visible, because none is observed. Adding them is coverage,
  not tiers, and stays out.
- `gemini-3-pro-preview`: in the table and used by Corpus C, but no longer on
  Google's page. No long-rate row can be verified, so the entry is unchanged.
- Batch, flex, priority and fast pricing; regional and `inference_geo`
  multipliers. Not modelled, as in stage 1.

## 4. Tests

- New: `pricing_for_prompt` returns the same object below and at the
  threshold, and the long entry above it, for each of the three keys. Every
  other entry has `long_context is None`.
- New: through each §1.1 call site, a Haiku 5.5 call at 100,000 prompt tokens
  prices at the short rate and one at 100,001 prices at the long rate, on
  every column including output.
- Full suite must pass; no test is skipped or removed.

## 5. Predictions (frozen)

- **P1 — Corpus A (published).** `boxdawn analyze --json` on the 28
  trace-commons sessions, run once on `c19fc50` and once on the code commit,
  with `PYTHONHASHSEED=0` on both: every output file is identical except the
  `analyzed` timestamp.
- **P2 — Corpus B (published).** The stage 1 Corpus B probe gives
  `grand_usd = 8082.0503719199905` before and after, with all 22 family
  totals identical.
- **P3 — Corpus C (published).** The five Exgentic strings resolve to entries
  equal to before, all with `long_context is None`.
- **P4 — live Claude Code.** The 46 `haiku-5.5` calls price to the same total
  before and after, bit for bit, because 0 of them exceed 100,000.
- **P5 — model-string census.** The stage 1 census over the same roots gives
  the same resolution for every string as on `c19fc50`. Matched → unmatched:
  none.

A miss on P1–P3 means the change reaches a published figure. It stops the
stage, and is reported as a miss rather than widened.

## 6. After the predictions are checked

No published figure is expected to move. The release notice names the three
models and thresholds whose long requests will price differently in a user's
report and budget guard, and says that on our data no request crossed them.

## 7. Amendment before code (2026-10-17, same day)

Found while wiring the call sites, before any code was committed. §1 and §5
above are kept as written. This section replaces them where it says so.

### 7.1 What §1 got wrong

- **§1.2 said Toolathlon is a flat-rate path. It is not, for these call
  sites.** The Toolathlon adapter writes the cache-split fields on every call
  (`input_tokens_uncached` = the apportioned input, the cache fields 0,
  `ingest/toolathlon.py:222`) together with `model`. So the report and
  `context_resend` both take the table branch, which is the path the
  published Corpus B `union_wr_cost` (0.9202) is computed on. Counted:
  `gemini-2.5-pro_{1,2,3}` has **48 of 4,488 calls in 7 traces** whose
  *apportioned* input is over 200,000 tokens. Applying §1 as written would
  price those 48 at the long rate on lengths no request ever had, and could
  move a published figure. §5 P2 would not have caught it, because the stage 1
  Corpus B probe prices outside these call sites.
- **§1.1 would not reach output in a CLI run.** The CLI passes the default
  cost tables (`__main__.py:162`), so the Claude Code adapter also writes
  `input_cost_rate` / `output_cost_rate`, copied from the short-rate entry.
  The report prices output from `output_cost_rate` first, so a long
  Haiku 5.5 request would have had its input at the long rate and its output
  at the short one.

### 7.2 Mechanism, replacing §1's "where applied"

- One function, `long_context_override(call) -> ModelPricing | None`, in
  `clew.cost.pricing`. It returns the long-rate entry only when all of these
  hold: the call does not carry `prompt_tokens_apportioned: True`; its
  `model` resolves to an entry with a tier; and its prompt length (§1
  definition) is over that tier's threshold. Otherwise it returns `None`.
- Where it returns an entry, that entry prices the call's input (by cache
  tier when the split is reported, otherwise `input_tokens × base`) and its
  output. It replaces the short-rate entry and any rate the adapter copied
  from that entry into `input_cost_rate` / `output_cost_rate`. Where it
  returns `None`, every code path is exactly as before.
- Call sites: `report/_model.py` `_llm_call_input_cost` and
  `_llm_call_output_cost`, and `detect/context_resend.py` `_ladder_for_call`
  and `_rate_and_cost_for_call`, which the waste-rate denominator,
  `redundant_read` and `semantic_duplicate` share. The budget guard reads raw
  usage rather than adapter calls and applies `pricing_for_prompt` directly.
- The Toolathlon adapter adds `prompt_tokens_apportioned: True` to every call
  it builds, because those lengths are apportioned, not reported. No other
  adapter apportions.

### 7.3 Predictions, replacing §5 P2

- **P2′ — Corpus B, on the changed path.** For every call of every Toolathlon
  trace that builds (66 files), the three per-call costs this stage touches —
  `_llm_call_input_cost`, `_llm_call_output_cost` and
  `context_resend.input_cost_for_call` — are bit-identical before and after,
  including the 48 calls over 200,000 tokens.
- P1, P3, P4 and P5 are unchanged. A miss on P1, P2′ or P3 stops the stage.
