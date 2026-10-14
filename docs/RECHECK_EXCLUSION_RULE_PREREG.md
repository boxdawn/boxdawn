# Pre-registration — stop counting a re-check after an edit as waste

Status: **pre-registration.** The rule in §2 was drafted against the 138 pairs
already coded in `ACCEPTED_PAIR_PRECISION_RESULTS` (the **dev set**) and is frozen
here. The held-out pool in §3 was located by key and category only. No output of
it, and no call between its pairs, has been read.

Product decision of 2026-10-14 (option C): fix the README wording now (PR
`#269`), and change the engine so it stops counting re-checks as waste. This
document governs the second half.

## 0. Why this exists

On Claude Code, 23 of the 38 accepted duplicate pairs were re-checks: a build or
test re-run after an edit, or a generated file re-written after a build
regenerated it. Byte identity makes them duplicates in hindsight, but only
running the call could show that the edit had not changed the result. The
cascade counts them all, so the published 34 / 0.80% and the trace-commons
dollar range rest mostly on calls that could not have been skipped.

`enrich` already has the idea for one case, `_has_intervening_edit` (same file
path, report label only). It is not applied to commands, and it does not change
the cascade's count.

## 1. What is measured, and what is not

**Measured:** whether a frozen deterministic rule, which removes a pair from
waste when a change-capable call ran between its two calls, keeps the pairs that
are avoidable and removes the ones that are not, on pairs nobody has coded yet.

🔴 **Not measured here:**
- **Shipping.** A pass licenses an implementation PR and a release, each one
  separate. Neither is part of this document.
- **New dollar figures.** They are recomputed at release, not here.
- **Toolathlon's form, navigation and retry re-checks.** The rule does not
  target them (§2.3).

## 2. The rule, frozen

Applied to an accepted tool pair `(origin, candidate)`, i.e. byte-equal and past
the existing guards. "Between" means a tool span with
`origin.end_time ≤ start_time < candidate.start_time`, excluding the pair itself.

```
MUTATE  = {Write, Edit, MultiEdit, NotebookEdit,
           filesystem-write_file, filesystem-edit_file, filesystem-move_file,
           filesystem-copy_file, filesystem-delete_file}
COMMAND = {Bash, PowerShell, terminal-run_command, local-python-execute}
path(s) = the shipped _file_path_of(_parse_input(s.input_text))

candidate tool in COMMAND  → EXCLUDE if any MUTATE span is between
candidate tool in MUTATE   → EXCLUDE if any COMMAND span is between,
                             or a MUTATE span with path == path(candidate)
path(candidate) is not None → EXCLUDE if a MUTATE span with path == path(candidate) is between
otherwise                  → KEEP
```

The three branches are checked in this order. A pair that is not excluded is
**kept** as waste.

**2.1 Dev-set behaviour (design data, not a result).** Measured on the 138 coded
pairs before freezing:

| | KEEP (WASTE · JUSTIFIED · UNDECIDABLE) | EXCLUDE (WASTE · JUSTIFIED · UNDECIDABLE) |
|---|---|---|
| CC, 38 | 11 · 1 · 2 | **2** · 22 · 0 |
| Toolathlon, 100 | 75 · 22 · 2 | 0 · 1 · 0 |

On CC the kept set's WASTE share goes from 13/38 to 11/14. 🔴 **These numbers fit
the rule to the data it was drafted on and are never cited as its precision.**

**2.2 Known misses, named before the test.**
- A command re-run where the change between came from another **command** (a
  background job started, then stopped again) is **kept**. Including "any command
  between" would also remove looping scripts that only list files between runs.
- A write re-run with only a `mkdir` between is **excluded** (dev #044, coded
  WASTE). `COMMAND` cannot tell a `mkdir` from a build.

**2.3 Out of reach by design.** Toolathlon's JUSTIFIED pairs are mostly a form
refilled after a navigation or submit, a retry after a transient error, and
status polls. Their tools are in neither set, so the rule leaves them alone.

## 3. The held-out pool, frozen

The 897 mimo-cc-1k sessions **outside** the seed-42 sample of 120 used so far,
scanned with the same accepted-pair definition. 28 sessions yield **78** accepted
pairs. 76 of them are reported by `enrich` and 2 are skipped by the tool-error
gate.

| | n |
|---|---:|
| reported, by category | idempotent 58 · error_repeat 12 · unclassified 5 · side_effect 1 |
| reported, by tool | Read 69 · AskUserQuestion 3 · Bash 2 · Write 1 · Glob 1 |
| skipped (tool-error gate) | 2 |

Frozen by sha256 of the sorted, newline-joined keys of the 76 reported pairs
(uncommitted `_heldout_census.KEYS.json`):
`11024261276ec988c5929888e0bcc40adc15ac92906b6221efd4bdd2f1d88bb3`. The 2 skipped
pairs are keyed and hashed in the same way at sheet generation, and are coded
like the others.

🔴 **The pool is thin exactly where the rule acts most.** It has 2 command pairs
and 1 write pair, against 69 reads. The held-out test is therefore mostly a test
of the **read** branch and of the rule not removing real waste. A pass does not
validate the command branch, which rests on the dev set alone. §6 says what that
limits.

## 4. Coding

Same rubric, sheet format and blinding statement as
`ACCEPTED_PAIR_PRECISION_PREREG` §3, applied to the 78 held-out pairs, shuffled
by `random.Random(20261016)`. **The rule's decision is not shown on the sheet.**
The coder knows the rule, which is a limit stated, not removed. Codes are hashed
before the rule's decisions are joined.

## 5. Metrics and decision

- **`K_prec` = WASTE / KEPT** on the held-out pool, with Clopper–Pearson 95%
  two-sided, and `K_prec_lower` = WASTE / KEPT counting UNDECIDABLE as not WASTE.
- **`K_ret` = kept WASTE / all WASTE**: how much real waste the rule leaves in.
- Descriptive: the same two numbers on dev ∪ held-out for CC, and the KEEP count
  the rule gives on trace-commons. That count is the candidate new published
  figure, reported but not published by this document.

| condition | verdict |
|---|---|
| `K_prec ≥ 0.70` **and** `K_ret ≥ 0.85` | **pass**: implement and release as a separate PR |
| `K_prec ≥ 0.70`, `K_ret < 0.85` | rule removes real waste. Fail, revise in a new pre-registration |
| `K_prec < 0.70` | rule keeps too much non-waste. Fail, revise in a new pre-registration |

**Override:** UNDECIDABLE ≥ **12** of 78 (about 15%) ⇒ not decidable.

## 6. Predictions

| # | Prediction |
|---|---|
| **P1** | held-out WASTE share **before** the rule, between **0.50 and 0.85** (mostly Reads, which were 10 of 12 WASTE on the dev set) |
| **P2** | the rule excludes at most **8** of the 78 held-out pairs |
| **P3** | `K_prec ≥ 0.70` |
| **P4** | `K_ret ≥ 0.85` |
| **P5** | applied to all 8,042 Toolathlon accepted pairs, the rule excludes under **3%** of the 4,249 headline pairs |

P5 is a mechanical count with no coding. It is computed at results time, with the
rule exactly as frozen here.

## 7. Stop conditions

- Held-out hash mismatch: stop, run invalid.
- A key not found: stop and report.
- The rule's code is changed after the held-out sheet is generated: the run is
  invalid. A revised rule needs a new pre-registration and a new pool.

Cost: zero.
