# Results — are the re-check rule's Toolathlon exclusions right?

Pre-registration: `docs/RECHECK_RULE_EXCLUSION_SIDE_PREREG.md` (merged
`927a021`, PR `#272`). Frame hash check: **PASS** (174 / 141). All 174 located.
Codes were hashed before the rule's branch and category were joined:
`4190fc40c1372ad9c51f74a7831e2fd4e9b3a8d1354de44827d9eaaf3a758bf0`. Cost:
**zero**.

## 0. Verdict

| | n | JUSTIFIED | WASTE | UNDECIDABLE | `E_prec` (95% CP) |
|---|---:|---:|---:|---:|---|
| **headline (primary)** | **141** | **75** | 66 | 0 | **0.5319** (0.4461–0.6164) |
| all exclusions | 174 | 108 | 66 | 0 | 0.6207 (0.5442–0.6930) |
| idempotent only | 33 | 33 | 0 | 0 | 1.0000 (0.8942–1.0000) |

🔴 **§4 verdict: the rule over-excludes on Toolathlon.** `E_prec` is 0.53, inside
the 0.50–0.70 row. **Do not implement it as frozen.** The over-excluding branch
must be narrowed in a new pre-registration first.

Nearly half of what the rule would remove from the Toolathlon headline is real
waste. Shipping it would have moved 4,249 down to 4,108 by deleting 66 avoidable
repeats along with 75 justified ones.

## 1. Where it goes wrong, by branch

| branch | n | JUSTIFIED | WASTE | `E_prec` |
|---|---:|---:|---:|---|
| read | 37 | 33 | 4 | 0.8919 (0.7458–0.9697) |
| command | 24 | 15 | 9 | 0.6250 (0.4059–0.8120) |
| **write** | **113** | 60 | **53** | **0.5310** (0.4348–0.6255) |

The 66 wrong exclusions come from **two mechanisms**, both visible in the
traces:

**1.1 A same-content rewrite is not a change (write branch, 50 of 53).** The
rule excludes a re-write when a write to the same path ran between. In these
loops, the write between carries **the same content** as the candidate. The file
was already in the state the candidate writes, so the candidate was avoidable.
The rule reads a same-path mutation as a change without checking whether it
changed anything. The other 3 write-branch WASTE pairs had only commands between that cannot
touch the file: a failing `git clone`, a refused `bq` call, and a script that
writes a different file.

**1.2 A result the change cannot reach (command and read branches, 13).** In 10
of them the candidate's output is an error that the intervening mutation
cannot affect:
- a `bq` or `pip` call refused by the sandbox's permission policy, repeated
  after unrelated file writes;
- a `read_file` that fails because `head` and `tail` were both passed, repeated
  after an edit to that file;
In the other 3, the candidate cannot read what changed: `pwd`, an empty code
block, and a `wc -l` of a file that only read-side scripts touched between.

The rule sees a mutation between and stops looking. The result does not
depend on what was mutated.

**The read branch works** (0.89). A re-read after a different-content write to
the same file is the clearest re-check, and all 4 of its WASTE pairs are the
`head`/`tail` parameter error from 1.2.

## 2. Predictions scored (§5)

| # | Prediction | Measured | Verdict |
|---|---|---|---|
| **P1** | `E_prec` (141) between 0.60 and 0.90 | **0.5319** | 🔴 rejected (below) |
| **P2** | read branch has the highest JUSTIFIED share | read 0.89 > command 0.63 > write 0.53 | ✅ held |
| **P3** | write branch has at least 10 WASTE | **53** | ✅ held |
| **P4** | UNDECIDABLE at most 10 | **0** | ✅ held |

P3 was the warning, and I underweighted it. I expected identical rewrites to be
a minority of the write branch. They are close to half.

## 3. How the coding went — disclosed

- **Relevance, not presence** (prereg §3). For every pair I looked up the **last**
  mutation of the same path before the candidate, and whether its content
  matched the candidate's (`filesystem-write_file` content, or the
  `filesystem-edit_file` edit list). I also checked every command between that
  ran after that last mutation, and whether the candidate's own output was an
  error that does not depend on file contents. I opened the full intervening
  sequence for 6 pairs, and each is logged in `_tl_exclusion_full_requests.log`.
- **Loops are coded pair by pair.** Many JUSTIFIED write pairs sit inside a loop
  that rewrites the same file with alternating content. Each such write restores
  a state the previous write changed, so the rubric codes it JUSTIFIED. The loop
  **as a whole** is waste, but a pair-level rubric cannot see that, and neither
  can the rule. This is a limit of the pair as the unit, not of the coding.
- **No UNDECIDABLE.** Every pair had either a matching or differing last write, or
  an error whose cause was readable.

## 4. What this licenses

**Does:** the frozen rule is **not** implemented. The two failure mechanisms
are named precisely enough to pre-register a narrower rule:

1. a same-path mutation counts as a change only if its content differs from the
   candidate's (writes), or from the origin's output (reads);
2. an exclusion does not apply when the candidate's result cannot depend on the
   mutated resource. A permission refusal, an invalid-parameter error and
   `pwd` are the examples measured here.

🔴 **Does not:**
- Not a validation of a narrower rule. The two refinements are drawn from these
  174 pairs, so testing them here would be circular, and Toolathlon has no
  unused exclusion pool left. A revised rule needs a pool it was not drafted on.
- Not a statement about Claude Code. The CC exclusions (24 on trace-commons) are
  a different population, and on the dev set 22 of them were JUSTIFIED. How the
  two refinements would change them has not been measured. A CC-only
  implementation is a product decision that §4 of the prereg allows to be
  recorded, and it is not taken here.

Diagnostics (uncommitted, raw only): `_tl_exclusion.KEYS.json`,
`_tl_exclusion_sheet`, `_tl_exclusion_codes.tsv`, `_tl_exclusion_score.RESULTS.json`.
