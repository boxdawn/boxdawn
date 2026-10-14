# Results — are the duplicates the cascade accepts avoidable?

Pre-registration: `docs/ACCEPTED_PAIR_PRECISION_PREREG.md` (merged `104dc1c`,
PR `#267`), written and merged before any pair in the frame was read. Frame hash
check: **PASS (6/6)**. All 138 keys located. Cost: **zero**, with no judge, no
API key and no network.

Codes were written to `_accepted_pair_codes.tsv` and its sha256 was recorded
**before** categories were joined back:
`c7d33d1576369eb3d13d743f27c63fa953fe7ae17f056fed3036fc55a85c05ce`. The scorer
refuses to run if the file differs.

## 0. Verdict

| | n | WASTE | JUSTIFIED | UNDECIDABLE | `P` (95% CP) | `P_upper` |
|---|---:|---:|---:|---:|---|---|
| **CC (primary)** | **38** | **13** | 23 | 2 | **0.3421** (0.1963–0.5135) | 0.3947 (0.2404–0.5661) |
| of which trace-commons (the published 34) | 34 | **9** | 23 | 2 | 0.2647 (0.1288–0.4436) | 0.3235 |
| of which mimo | 4 | 4 | 0 | 0 | 1.0000 (0.3976–1.0000) | — |
| Toolathlon sample of the 4,249 | 100 | 75 | 23 | 2 | 0.7500 (0.6534–0.8312) | 0.7700 |

🔴 **§5 verdict: the published CC count overstates avoidable waste.** WASTE is
13 of 38, inside the "≤ 18" row. UNDECIDABLE is 2, below the override of 8.
Even the upper bound (15 of 38) stays in that row.

Of the **34 waste spans** README reports for trace-commons, **9** were avoidable
when the second call was made. **23** were re-checks after something that could
have changed the result, and **2** cannot be settled from the trace.

🔴 **No published figure is edited here.** Any revision of 34, 0.80% or the
trace-commons dollar range is a product decision, per §5.

## 1. Where the 23 come from

| CC category (`enrich`) | n | WASTE | JUSTIFIED | UNDECIDABLE |
|---|---:|---:|---:|---:|
| unclassified (Bash / PowerShell) | 19 | **1** | **16** | 2 |
| side_effect (Write / Edit) | 5 | 0 | **5** | 0 |
| idempotent (Read / Glob / Grep) | 12 | 10 | 2 | 0 |
| skipped by the tool-error gate | 2 | 2 | 0 | 0 |

The JUSTIFIED pairs are one pattern: **the agent edits code, then reruns the same
build or test, and the output happens to be identical.** A clean compile prints
nothing, and a still-failing test prints the same failure. Byte identity makes
that a duplicate in hindsight. It was not avoidable, because only running it
could show the edits had not changed the result.

The rest of the JUSTIFIED pairs are writes to a generated file that a build in
between had regenerated, an `Edit` that succeeded twice (so the file had been
reverted between), and a background job started between two stop commands.

`enrich` already marks the 4 pairs where it sees an edit to the same file path:
**4 of 4** were coded JUSTIFIED. It cannot see the command case. Commands have
no file target, so the report line says *"state change uncertain"*. That line is
accurate, but the aggregate counts do not use it.

**1.1 🔴 The dollar range sits on one session that is mostly JUSTIFIED.** README
says one 18-waste-span session is **98.15%** of the trace-commons
`$12.71–$127.14` range. That session (`c99032e9`) codes as **WASTE 3 ·
JUSTIFIED 13 · UNDECIDABLE 2**. This study does not compute a revised dollar
figure, because the amplification formula was not in its pre-registration.
The count is enough to say that most of the range is priced on calls that were
not avoidable.

## 2. Toolathlon, descriptively

| category | n | WASTE | `P` |
|---|---:|---:|---|
| error_repeat | 57 | 44 | 0.7719 (0.6416–0.8726) |
| side_effect | 29 | 18 | 0.6207 (0.4226–0.7931) |
| unclassified | 14 | 13 | 0.9286 (0.6613–0.9982) |

The Toolathlon WASTE pairs are mostly loops: the same malformed call (a missing
`path` parameter) repeated hundreds of times, the same email resent to the same
recipient, the same empty code block executed again. Its JUSTIFIED pairs are
mostly a form refilled after a navigation or submit, a retry after the cause was
fixed (a missing file written, a parent directory created), and status polls.

Scaled to 4,249, 0.75 is **≈ 3,190 pairs** (95% CI ≈ 2,780–3,530). That is an
estimate, not a count. Under the §5 bands it falls in the "stands" row
descriptively, and no action on the Toolathlon figure follows from this
document.

⇒ **The two corpora point in opposite directions, for a reason visible in the
traces.** Toolathlon's accepted duplicates are dominated by agents stuck in
loops. Claude Code's are dominated by a working edit-and-recheck cycle.

## 3. Predictions scored (§6)

| # | Prediction | Measured | Verdict |
|---|---|---|---|
| **P1** | CC WASTE 18–30 of 38 | **13** | 🔴 rejected (below the range) |
| **P2** | Toolathlon WASTE 50–80 of 100 | **75** | ✅ held |
| **P3** | at least 3 of the 4 `modified_in_between` pairs JUSTIFIED | **4 of 4** | ✅ held |
| **P4** | Toolathlon error_repeat WASTE share > side_effect | **0.77 > 0.62** | ✅ held |
| **P5** | CC UNDECIDABLE at most 5 | **2** | ✅ held |

Four held and one was rejected. The one that failed is the one that carries the
verdict: I expected most CC duplicates to be avoidable, and fewer than half were.

## 4. How the coding went — disclosed

- **View.** The prereg sheet was generated (138 entries, every intervening call,
  each input and output capped at 200 characters). I coded from a condensed view
  of the same data: a histogram of intervening tool names, plus the full line of
  every intervening call whose input or output mentioned the pair's path or
  identifier. I opened the full intervening sequence for **25** pairs, and each
  opening is logged in `_accepted_pair_full_requests.log`.
- **Toolathlon timestamps are not usable.** Elapsed time between calls reads as
  round values (`2000.0s`, `28000.0s`) that do not track the call sequence, so
  time was never used as evidence. A status poll with **no** calls between it and
  the previous one (#012) was coded UNDECIDABLE. Polls with other calls between
  them (#034, #107) were coded JUSTIFIED.
- **Transient failures.** A retry after a timeout or a network error (#060, #061,
  #100) was coded JUSTIFIED: the rubric's "state that changes on its own"
  extended to service availability. A repeated HTTP 403 (#129) was coded WASTE,
  because a 403 does not clear on its own.
- **One rubric-literal call.** #054, a pod looked up 20 times with no create
  call in between, reads like a stuck loop. The rubric lists pods as state that
  changes on its own, so it is coded JUSTIFIED and tagged RUBRIC-LITERAL. It is
  a Toolathlon pair and does not touch `P_cc`.
- **UNDECIDABLE on CC (2).** Both are a deferred tool schema re-fetched
  (`ToolSearch select:TodoWrite`) long after the first fetch. Whether the schema
  was still available to the agent is not in the trace.
- **One coder, not blind to tool names**, as declared in §3.3. No code was
  changed after categories were joined.

## 5. What this licenses

**Does:** on Claude Code, the cascade's accepted tool duplicates are mostly
edit-then-recheck calls. Measured against avoidability at call time, the
published count of 34 has about **9** avoidable pairs (CI 4–15 of 34).

🔴 **Does not:**
- Not a statement that the detector is wrong. Byte identity is what it claims,
  and the per-pair report already hedges the command case.
- Not a revised dollar figure. §1.1 gives counts only.
- Not a Toolathlon correction. §2 is descriptive and uses a sample estimate.
- Not a judgment of the agents. "JUSTIFIED" means the call could have changed
  the result, not that it was a good call.

**What a fix would need** (named, not proposed): the command case needs what
`_has_intervening_edit` already does for file paths. That is an intervening
`Edit` or `Write` anywhere in the working tree before a rerun of a build or test
command. It is a separate pre-registration, and it would move published figures.

Diagnostics (uncommitted, raw only): `_accepted_pair_census`,
`_accepted_pair_sheet`, `_accepted_pair_score` and their outputs.
