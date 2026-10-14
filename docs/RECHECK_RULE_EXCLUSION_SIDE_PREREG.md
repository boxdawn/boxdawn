# Pre-registration — are the re-check rule's Toolathlon exclusions right?

Status: **pre-registration.** The frame in §2 was built from keys, rule branch,
category and tool name only. No output of these pairs, and no call between
them, has been read.

Product decision of 2026-10-14 (option (a)): before implementing the rule from
`RECHECK_EXCLUSION_RULE_PREREG`, check the side that moves published figures.
`RECHECK_EXCLUSION_RULE_RESULTS` passed, but its held-out pool triggered **zero**
exclusions. The rule's exclusions were validated only on the dev set it was
drafted from, and the 141 it would remove from the Toolathlon headline were
never coded.

## 1. What is measured, and what is not

**Measured:** of the accepted Toolathlon pairs the frozen rule excludes, the
share that really were re-checks, i.e. not avoidable at call time.

🔴 **Not measured:**
- **Claude Code exclusions.** No unused CC pool produces them. The held-out mimo
  pool gave 0, and the 24 trace-commons exclusions are dev-set coded (22
  JUSTIFIED). The CC side of the rule stays dev-validated, and the results must
  say so.
- **The rule's misses** (avoidable pairs it keeps). `K_ret` covered that.

## 2. The frame, frozen

The frozen rule (`_recheck_rule_dev.excluded`, unchanged since
`RECHECK_EXCLUSION_RULE_PREREG`) applied to all 8,042 Toolathlon accepted pairs
excludes **174**. Keys
`toolathlon|{file}:{line}|{origin}|{candidate}|{category}|{branch}` are kept in
the uncommitted `_tl_exclusion.KEYS.json`.

| | n | sha256 (sorted, newline-joined keys) |
|---|---:|---|
| all exclusions | **174** | `33413508c2c61846f944d9f8e041d5fa3ce6d6af05963e931e1f046953504dbe` |
| headline (non-idempotent) | **141** | `259b3d21234f78cff7ca967e8405af0a77d7fe490116c39fb90ae691ae3f58f2` |

| branch · category | n |
|---|---:|
| write · side_effect | 107 |
| write · error_repeat | 6 |
| read · idempotent | 33 |
| read · error_repeat | 4 |
| command · unclassified | 22 |
| command · error_repeat | 2 |

By candidate tool: `filesystem-write_file` 106 · `filesystem-read_file` 37 ·
`terminal-run_command` 20 · `filesystem-edit_file` 7 · `local-python-execute` 4.

**All 174 are coded** (a census, not a sample). The order is shuffled by
`random.Random(20261017)`.

## 3. Coding

Same rubric as `ACCEPTED_PAIR_PRECISION_PREREG` §3.2 (WASTE / JUSTIFIED /
UNDECIDABLE, same tie rule). One clarification is written down because this
frame invites the wrong reading:

🔴 **The rule fires on the presence of a call. The coder judges that call's
relevance.** The rule excludes a write re-run when **any** command ran between
the two writes, and a command re-run when **any** file was mutated between them.
JUSTIFIED requires that the specific call between could plausibly have changed
**this** candidate's result. Examples:
- a command that writes, deletes or regenerates the same file;
- a mutation of a file the command reads or lists;
- a mutation of the same path before a read.

A `ls` between two identical writes, or a write to an unrelated file between
two identical `git log` runs, does **not** make the pair JUSTIFIED. A coder who
reads presence as relevance would reproduce the rule and measure nothing.

The sheet shows the same fields as before, plus every call between. **The rule's
branch is not shown.** Codes are hashed before branch and category are joined.

## 4. Metrics and decision

- **Primary: `E_prec` = JUSTIFIED / 141** on the headline exclusions, with
  Clopper–Pearson 95% two-sided, and `E_prec_upper` = (JUSTIFIED + UNDECIDABLE) / 141.
- Secondary: the same on all 174 and per branch (write / read / command).

| `E_prec` (headline 141) | verdict | what follows |
|---|---|---|
| **≥ 0.70** | exclusions validated on Toolathlon | implement the rule and release, as a separate PR |
| **0.50 – 0.70** | the rule over-excludes on Toolathlon | narrow the over-excluding branch in a new pre-registration before implementing |
| **< 0.50** | the rule is wrong on Toolathlon | do not implement it as frozen. Revise in a new pre-registration |

**Override:** UNDECIDABLE ≥ **21** of 141 (about 15%) ⇒ not decidable.

A result in the middle row may still license a CC-only implementation, because
the CC exclusions are a different population. That would be a product decision
recorded in the results, not one taken by this document.

## 5. Predictions

| # | Prediction |
|---|---|
| **P1** | `E_prec` (headline 141) between **0.60 and 0.90** |
| **P2** | the **read** branch has the highest JUSTIFIED share of the three. A same-path write before a re-read is the most direct relevance |
| **P3** | the **write** branch has at least **10** WASTE pairs: identical re-writes with an irrelevant command between |
| **P4** | UNDECIDABLE at most **10** of 174 |

## 6. Stop conditions

- A frame hash mismatch, or a key not found: stop.
- The rule's code is changed: the frame is invalid.
- Codes are changed after the join: report the change and its reason.

Cost: zero.
