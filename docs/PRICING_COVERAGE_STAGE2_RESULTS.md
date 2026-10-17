# Pricing Coverage Stage 2 — Results

**Pre-registration.** `docs/PRICING_COVERAGE_STAGE2_PREREG.md` (commit `b7220a1`),
amended before code in its §7 (commit `2701eff`).
**Code.** commit `a16f15f` — `src/clew/cost/pricing.py`, `report/_model.py`,
`detect/context_resend.py`, `guard.py`, `ingest/toolathlon.py`,
`tests/cost/test_pricing_stage2.py`.
**Measured.** 2026-10-17, with uncommitted probe scripts, run once against
`c19fc50` (before, in a separate worktree) and once against `a16f15f`
(after).

## Verdict

P1, P2′, P3, P4 and P5 all hit. No published figure moved, and no dollar
moved on any data we hold.

## Found before code: the amendment

While wiring the call sites, before the code commit, two things in §1 turned
out wrong. Both are recorded in prereg §7.

- **Toolathlon is not a flat-rate path for these call sites.** Its calls carry
  the cache-split fields. 48 apportioned `gemini-2.5-pro` calls in 7 traces
  exceed 200,000 tokens. Under §1 as first written they would have taken the
  long rate on lengths no request had, on the path behind Corpus B's
  published `union_wr_cost`. The §5 P2 probe would not have seen it.
- **A CLI run copies the short rate into every call**, and the report reads
  output from that copy first. §1 would have priced a long request's input
  long and its output short.

The fix: one override that replaces copied rates, and a new Toolathlon marker
(`prompt_tokens_apportioned`) that keeps apportioned lengths out of any tier.

## P1 — Corpus A (published): HIT

`boxdawn analyze --json --no-snippets` on all 28 trace-commons sessions, with
`PYTHONHASHSEED=0` on both runs. All 28 exit 0 before and after. Comparing
the JSON trees field by field, the only difference in any of the 28 files is
the top-level `analyzed` timestamp. Every cost, waste-rate and detector field
is equal. The 28 `total_analyzed_cost` values sum to 397.53358535, the
published $397.53.

## P2′ — Corpus B, on the changed path: HIT

137,659 Toolathlon calls over 66 files. `_llm_call_input_cost`,
`_llm_call_output_cost` and `input_cost_for_call` are byte-identical before
and after (`repr` of each float, all 137,659 lines). That includes 1,183
calls whose apportioned input is over 200,000 tokens.

The check has teeth: with the marker removed, exactly **48** of these calls
would take a tier. They are the 48 the amendment counted.

## P3 — Corpus C (published): HIT

`DeepSeek-V3.2`, `Kimi-K2.5`, `claude-opus-4-5`, `gemini-3-pro-preview` and
`gpt-5.2-2025-12-11` resolve to the same name and rates before and after,
and all have `long_context is None`.

## P4 — live Claude Code: HIT

46 deduplicated `haiku-5.5` calls, 0 over 100,000 prompt tokens, priced
through the guard at `0.09903299000000002` before and after.

## P5 — model-string census: HIT

All 158 strings from the stage 1 census resolve to the same entry and
`matched` flag as before. Matched → unmatched: none.

## Tests

`tests/cost/test_pricing_stage2.py`: 12 new. They cover:

- each tier's rates and its boundary (at the threshold → short, one over →
  long);
- that no other entry carries a tier;
- that the report, `context_resend` and the guard each price a Haiku 5.5
  call at 100,000 short and at 100,001 long on every column, with the CLI's
  copied rates present;
- that an apportioned length never takes a tier, and that Toolathlon marks
  every call.

Full suite before adding them: 1178 passed, 1 xfailed (pre-existing), 0
failed.

## What changes for users

No published figure moves. A user's report and budget guard price a request
differently only when its prompt, cache tokens included, is over the
threshold for one of these:

- `claude-haiku-5-5` / `claude-haiku-5.5`, over 100,000 tokens: every column
  ×5, so input $0.50, cache read $0.05, output $2.50 per MTok.
- `qwen3.6-plus`, over 256K: input $2.00, output $6.00.
- `gemini-2.5-pro`, over 200k: input $2.50, cache read $0.25, output $15.00.

Before this change those requests were shown at the short rate. On our data
no request crossed any of the three thresholds.
