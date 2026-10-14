# Results — what the byte-identity gate throws away

Pre-registration: `docs/BYTE_GATE_FALSE_REJECTION_PREREG.md` (merged `34388de`,
PR `#265`), written and merged before any output in the frame was read. Frame
hash check: **PASS (5/5)**. All 218 keys located in their traces. Cost:
**zero**, with no judge, no API key and no network.

Codes were written to `_byte_gate_codes.tsv` and its sha256 was recorded
**before** the §5 ladder was computed:
`1ea48b5c66fd350a7dfd145f0c0d8815b09e6eb31b7d78a97a4f2bcd6cc4ca07`. The scorer
refuses to run if the file differs.

## 0. Verdict

| | n | SAME | UNDECIDABLE | `F` (95% CP) | `F_upper` |
|---|---:|---:|---:|---|---|
| **CC (primary)** | **92** | **2** | 2 | **0.0217** (0.0026–0.0763) | 0.0435 (0.0120–0.1076) |
| of which trace-commons 28 | 84 | 2 | 1 | 0.0238 (0.0029–0.0834) | 0.0357 |
| of which mimo 120 | 8 | 0 | 1 | 0.0000 (0.0000–0.3694) | 0.1250 |
| Toolathlon sample | 100 | 24 | 1 | 0.2400 (0.1602–0.3357) | 0.2500 |
| TRAIL gaia | 26 | 8 | 0 | 0.3077 (0.1433–0.5179) | 0.3077 |

**§6 verdict: the gate stands on CC.** SAME is 2 of 92, which is at most 9.
UNDECIDABLE is 2, below the 10 that would make the verdict undecidable. Even the
upper bound (4 of 92) sits inside the "stands" row.

Both CC SAME pairs are the same `Bash` build command run twice, where the only
difference is the build duration (`26s` vs `21s`, `26s` vs `19s`). If the gate
had accepted them, the trace-commons waste count would read 36 instead of 34.
Nothing in this document changes the published 34.

## 1. The corpora disagree, and the reason is visible

| corpus | SAME, by what differed |
|---|---|
| CC | build duration **2** |
| Toolathlon | execution time **12** (one also with a bytes-processed figure) · request/query id on an identical error **7** · temp or overflow-file name **2** · presigned-URL tokens + `last_edited_time` **1** · random form token **1** · (24 total) |
| TRAIL gaia | browsing-harness revisit notice **8** (one also with a server feature-flag list) |

On CC, the byte-differ pairs are dominated by state changes: `Read` **34/34**
CHANGED, `PowerShell` **21/21** CHANGED. A Claude Code agent mostly re-reads a
file after editing it and re-runs a build after changing code, and the outputs
differ because the world did. On Toolathlon, whole tool families embed a
per-call value in otherwise identical output: `bigquery_run_query` **7/7** SAME
and `local-python-execute` **6/6** SAME, all on execution time (one also on a bytes-processed figure). On TRAIL the
browser harness inserts a "previously visited N seconds ago" line on revisit.

⇒ 🔴 **The gate's false-rejection rate is a property of the tool output format,
not of the gate.** It is near zero where every published CC figure is measured,
and around a quarter where tool outputs carry timers and ids.

**1.1 Toolathlon, as an estimate.** 24% of 9,059 gives **≈ 2,170 pairs**
(95% CI range ≈ 1,450–3,040). That is a sample estimate. It is **not a
count** and it is not added to the published 8,042, which this study does not
touch.

## 2. Predictions scored (§7)

| # | Prediction | Measured | Verdict |
|---|---|---|---|
| **P1** | CC SAME 3–15 of 92 | **2** | 🔴 rejected (below the range) |
| **P2** | Toolathlon SAME 10–35 of 100 | **24** | ✅ held |
| **P3** | TRAIL SAME at most 5 of 26 | **8** | 🔴 rejected |
| **P4** | CC UNDECIDABLE at most 5 | **2** | ✅ held |
| **P5** | at least 90% of L2-equal pairs coded SAME | **24 of 35 = 68.6%** | 🔴 rejected |
| **P6** | CC `Read` SAME at most 3 of 39 | **0** | ✅ held |

Three held and three rejected. P1 and P3 missed in opposite directions: CC was
cleaner than predicted and TRAIL was noisier. The TRAIL miss is one mechanism,
the revisit notice, which I had not seen in any output before freezing.

## 3. The mechanical ladder (§5) — what a rule would catch

| subset | L1-equal | L2-equal & SAME | L2-equal & **not** SAME | SAME missed by L2 |
|---|---:|---:|---:|---:|
| CC | 0 | 2 | **3** | 0 |
| Toolathlon | 0 | 22 | **4** | 2 |
| TRAIL gaia | 0 | 0 | **4** | 8 |

L1 (whitespace + ANSI) catches **nothing**: no pair in the frame differs only in
whitespace. L2 catches most of Toolathlon's SAME pairs, but it **also accepts
11 pairs that changed state**. Masking every digit run erases exactly the values
that matter: `tests=89` vs `tests=102` (three CC `gradle test` pairs),
`total_students 5 → 10`, pod readiness, a traceback line number, the id of a newly created Notion page, and a different
GitHub issue number on TRAIL (`/issues/9533` vs `/issues/22104`). The 8 TRAIL
SAME pairs it misses are the revisit line, which is not a number at all.

⇒ **A digit-masking rule would buy recall by introducing false positives on
the corpus that backs the published figures.** On CC it would add 2 true and
3 false confirmations. No rule is proposed. A future one would have to mask
named fields (execution time, request id), not character classes.

## 4. How the coding went — disclosed

- **Display.** The prereg's sheet (unified diff, 3 lines context) was generated.
  51 diffs exceed the 6,000-character display cap and were truncated in it. I
  read every pair through a condensed view of changed lines and opened full
  outputs for **35** pairs. Each opening is logged in
  `_byte_gate_full_requests.log`.
- **Rubric conflict, resolved toward UNDECIDABLE.** In two pairs the candidate
  carried strictly *less* than the origin: a Claude Code "file unchanged since
  your last Read" stub (#033), and a page snapshot missing one console 404 line
  (#138). The §3.2 question ("missing anything?") says SAME; the SAME definition
  ("differences confined to per-call values") does not cover them. Per the tie
  rule, an unsure coder codes UNDECIDABLE. A third UNDECIDABLE (#163) is a write
  reported first as "created" and then as "updated".
- **ERROR vs CHANGED convention.** ERROR was used for a *tool-level* error on
  one side (`tool_use_error`, MCP error, missing parent directory). A *process*
  result that changed (build failed → built, link error appeared) was coded
  CHANGED. Both are not-SAME, so `F` does not depend on the convention.
- **Two codes changed during coding, before the hash was recorded.** #036 went
  ERROR → CHANGED when I adopted the convention above. #033 went SAME →
  UNDECIDABLE when I hit the rubric conflict at #138 and applied it
  consistently. Neither touched `F_cc`: #033 is a mimo pair, and the change
  lowered SAME.
- **One coder, not blind to corpus.** As declared in §3.3.

## 5. What this licenses

**Does:** on Claude Code traces, the byte-identity gate's rejections are almost
all real state changes. The two exceptions are build-duration-only reruns, and
the published 34 / 0.80% are not materially understated by the gate.

🔴 **Does not:**
- Not a statement about the 8,042 pairs the gate *accepts*. Their precision is
  a separate question (§1 of the prereg).
- Not a corrected Toolathlon figure. §1.1 is an estimate with a sample interval.
- Not support for a relaxed rule. §3 shows the obvious one breaks CC.
- Not a property of "agents". The rate tracks how a tool formats its output.

Diagnostics (uncommitted, raw only): `_byte_gate_census`, `_byte_gate_frame`,
`_byte_gate_sheet`, `_byte_gate_score` and their outputs. TRAIL text is not
reproduced here beyond a one-line description of a harness notice.
