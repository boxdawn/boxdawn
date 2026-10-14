# Results — stop counting a re-check after an edit as waste

Pre-registration: `docs/RECHECK_EXCLUSION_RULE_PREREG.md` (merged `312e802`,
PR `#270`). Held-out hash check: **PASS** (76 reported pairs), plus 2 skipped
pairs keyed at sheet generation
(`eb30b3e35e793b64b1c1ad93983d8cb9e7f6b017e127a97e422ba3c65ea65245`). All 78
located. The rule's code (`_recheck_rule_dev.excluded`) was last written before
the held-out sheet was generated and has not changed since. Codes were hashed
before the rule's decisions were joined:
`b53c7d153503c1b9bb6912f49013f42ba83fca4817789f2fc751e0a5e6311ce1`. Cost:
**zero**.

## 0. Verdict

| held-out (78) | value | bar |
|---|---|---|
| excluded by the rule | **0** | — |
| `K_prec` = WASTE / KEPT | **75/78 = 0.9615** (0.8917–0.9920) | ≥ 0.70 ✅ |
| `K_ret` = kept WASTE / all WASTE | **75/75 = 1.0000** (0.9520–1.0000) | ≥ 0.85 ✅ |
| UNDECIDABLE | 3 | override at 12 |

**§5 verdict: pass.**

🔴 **What the pass means is narrow, and it should be read that way.** The rule
excluded **nothing** in the held-out pool. That pool is 69 file re-reads with
no edit to the same file between them, and the rule correctly left all of them
in. So the held-out test establishes one thing: **the rule does not remove real
waste where it does not apply.** It provides **no** held-out evidence that its
exclusions are right. Every exclusion the rule makes on Claude Code, including
the 24 that would change the published figure, was validated only on the dev
set the rule was drafted from (22 of 24 coded JUSTIFIED there). The
pre-registration stated this limit (§3) before the test ran.

## 1. What the rule would do to published figures

Computed mechanically with the frozen rule. **Nothing here is published by this
document**, and the figures change only if an implementation is released.

| figure | now | with the rule | note |
|---|---:|---:|---|
| trace-commons waste spans | 34 | **10** | 24 excluded (dev codes: 22 JUSTIFIED, 2 WASTE) |
| CC rate (of 4,262 tool spans) | 0.80% | **0.23%** | 10 / 4,262 |
| Toolathlon accepted pairs | 8,042 | **7,868** | 174 excluded, **uncoded** |
| Toolathlon headline (non-idempotent) | 4,249 | **4,108** | 141 excluded, **uncoded**; 2.41% → 2.33% of tool spans |

The 10 trace-commons pairs that stay code as WASTE 7 · JUSTIFIED 1 ·
UNDECIDABLE 2. The 2 WASTE pairs the rule drops are dev #044 (a re-write with
only a `mkdir` between) and #110 (a directory listing re-run after a README
overwrite). Both were named in prereg §2.2 as the shape the rule gets wrong.

🔴 **The 141 Toolathlon exclusions have not been coded.** On the dev sample, the
rule excluded 1 Toolathlon pair (JUSTIFIED). Its precision on the other 140 is
unknown, so the Toolathlon change is a count, not a validated correction.

## 2. Predictions scored (§6)

| # | Prediction | Measured | Verdict |
|---|---|---|---|
| **P1** | held-out WASTE share before the rule 0.50–0.85 | **0.9615** | 🔴 rejected (above the range) |
| **P2** | rule excludes at most 8 of 78 | **0** | ✅ held |
| **P3** | `K_prec ≥ 0.70` | 0.9615 | ✅ held |
| **P4** | `K_ret ≥ 0.85` | 1.0000 | ✅ held |
| **P5** | rule excludes < 3% of the 4,249 Toolathlon headline pairs | **141 = 3.32%** | 🔴 rejected (just above) |

P1 missed because the held-out pool is almost entirely one exploration session
re-reading files it had already read, with nothing changing in between. That
is the same shape the dev set showed for CC reads (10 of 12 WASTE), but in
greater concentration than I predicted.

## 3. How the coding went — disclosed

- **Same rubric** as `ACCEPTED_PAIR_PRECISION_PREREG` §3. I coded from a
  per-pair summary: the target, the shared output head, a histogram of calls
  between, every mutation between, and every shell command between that is not
  a read-only command (`ls`, `cat`, `head`, `find`, `grep`, `git log/status/diff/show`).
  No shell command in the held-out pool fell outside that read-only set.
- **Sub-agents between two reads** ("design", "examine" or "check" tasks) were
  read as not mutating. Their own tool calls do not appear in the parent trace,
  so this is a judgment and not an observation. It affects WASTE codes on reads
  with an `Agent` call between (#008, #014, #015, #022, #028, #030, #033, #039,
  #046, #049, #055, #058, #068, #070).
- **UNDECIDABLE (3)** are all `AskUserQuestion` re-issued with nothing between.
  Whether the user had a chance to answer is not in the trace.
- **The coder knew the rule.** On this pool the rule's output is fixed by the
  absence of any mutation between, which the coder could see. That is exactly
  why the test says little about exclusions.

## 4. What this licenses

**Does:** an implementation PR and a release, per §5. The rule removes 24 of the
34 trace-commons pairs, of which the dev coding called 22 JUSTIFIED, and it
leaves real re-read waste alone.

🔴 **Does not:**
- Not held-out validation of the exclusion side, on CC or Toolathlon (§0, §1).
- Not new dollar figures. Those are recomputed at release.
- Not a Toolathlon correction. 141 exclusions remain uncoded.

**Recommended before release, not required by §5:** code a sample of the 141
Toolathlon exclusions and any CC command re-runs a larger pool can supply,
because the exclusion side is where a published number would move.

Diagnostics (uncommitted, raw only): `_heldout_census`, `_heldout_sheet`,
`_recheck_rule_dev`, `_recheck_rule_score` and their outputs.
