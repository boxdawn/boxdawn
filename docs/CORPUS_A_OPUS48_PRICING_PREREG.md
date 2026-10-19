# Corpus A — Opus 4.8 Sessions Left Unpriced — Pre-registration

**Scope.** Corpus A's published `union_wr_cost` (0.8449) is computed over 23
of 28 sessions. The other 5 are not unpriceable. They run `claude-opus-4-8`,
and the corpus script's fixed model list does not contain that name. This
document fixes what the corrected figure must be before the script is changed
and the README is corrected.
**Written.** 2026-10-19. Engine `main` at `1dabfe0`. Nothing changed yet.
**Results and the README correction** follow as separate commits.

## 0. What was found (2026-10-19)

- The 28 trace-commons sessions through the CLI (`boxdawn analyze`, 0.5.22):
  all 28 carry a cost, `accuracy_flag: accurate`, `unpriced_models: []`.
- The same 28 through the public-figure method
  (`field_test/diagnostics/waste_rate_metric.py`, uncommitted): 23 priced.
  The 5 others get `total_input_cost = 0` and leave the denominator.
- All 5 are `claude-opus-4-8` sessions: `2965219c`, `3be5ba0c`, `89cf9e13`,
  `comparia-voting-fields-anon`, `da5d32d6`.
- The script prices only the names in `_CC_MODEL_FAMILIES`
  (`waste_rate_metric.py:77-85`). `claude-opus-4-8` is not there.
- The CLI resolves `claude-opus-4-8` to Opus 4.7's rates
  (`src/clew/cost/pricing.py:845`). Anthropic's pricing page, read
  2026-10-19, lists Opus 4.8 and Opus 4.7 at the same five rates: $5 input,
  $6.25 5-minute cache write, $10 1-hour cache write, $0.50 cache hit, $25
  output per MTok. **The CLI is right; the script's list is stale.**
- Size: the 5 sessions' input cost is $195.66, more than the 23 sessions'
  $147.63. One session, `da5d32d6`, is $118.44 of it.
- README `:279` says *"A user running `analyze` on an unpriced trace has
  always seen no cost ratio rather than a wrong one"*. That holds in general,
  but these 5 are not unpriced for a user. They were left out of the table
  only.

## 1. The change (frozen)

Add `"claude-opus-4-8"` and `"claude-opus-4.8"` to `_CC_MODEL_FAMILIES` in
`waste_rate_metric.py`. Rates come from `get_pricing()`, as for every other
name in the list. No other change.

## 2. Predictions (frozen)

The diagnostic below was run before this document, with the two names
injected at runtime. P1 commits to its result. That makes P1 a check that
the edited script reproduces the diagnostic. It is not a blind prediction.

- **P1.** Corpus A: **28** priced, **308.4824 / 343.2929 = 0.8986**.
- **P2.** `union_wr_char` **0.9916** and `union_sdr_at_10` **0.9643** do not
  move. Both are byte- and rank-based, not priced.
- **P3.** The 23 sessions already priced keep their per-session
  `union_waste_cost` and `total_input_cost`, bit-identical.
- **P4.** Corpus B (Toolathlon) and Corpus D (MIMO) do not move. The added
  names match only a trace whose model string starts with `claude-opus-4-8`
  or `claude-opus-4.8`. The number of such model strings in either corpus is
  counted and expected to be **0**.
- **P5.** README `:232`, the single-detector line
  (`resent_cost / total_input_cost = 0.8448` over 23 sessions), recomputed
  over 28. **Value not predicted.**
- **P6.** The per-session `wr_cost` spread (p10 / median / p90, now 0.3122 /
  0.7815 / 0.9190 over 23), recomputed over 28. **Values not predicted.**

## 3. Stop conditions

- P1 off in the fourth decimal, or P2 or P3 fails: the edit changed more than
  the list. Find out why before the README changes.
- P4 finds a matching model string: B or D would move too, and this document
  is amended before going on.

## 4. What the README correction will say

A new correction section, in the shape of the 2026-10-15 one. The old value
stays visible, struck through by the new one. It names the cause (a stale
model list in the corpus script, not a missing price) and the scale (the 5
sessions are 57% of the corrected denominator, one of them 34.5%). Every
sentence that states the current figure or rests on "23 priced sessions" as
current is corrected in the same commit: `:232`, `:239`, `:251`, `:258`,
`:264`, `:266`, `:279`, `:311`. Sentences that describe the 2026-09-01 or
2026-10-15 state (`:272`, `:277`, `:287`-`:296`) stay as dated history.

## 5. Notice

Web and marketing: a public figure changes. Corpus A `union_wr_cost` and
anything quoting 84.5%.
