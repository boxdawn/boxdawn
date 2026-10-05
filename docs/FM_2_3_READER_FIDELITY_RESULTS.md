# FM-2.3 reader fidelity: results

Executed 2026-10-05 against `FM_2_3_READER_FIDELITY_PREREG.md`, whose thresholds
were fixed before any call and whose §8 amendment (batch endpoint, re-baselined
call cap) was merged before the run resumed.

**Answer in one line.** Reading **(i)** — *the 19 is accounted for by the reader,
not by the line* — is what the instrument returned: **`N_R1 = 0` of 39**, against
a support threshold of ≤ 4. A strong reader applying the written definition
reproduces the hand labels (0–1 of 39). 🔴 **Arm A's 19 must not be cited as
evidence about the written line** — §2.2 fixed that consequence in advance.

🔴 **No trace content appears in this document.** TRAIL is MIT with
redistribution withheld. The per-call records hold quoted trace text and stay in
the uncommitted diagnostic; §5 below describes the reader's mechanism in
paraphrase for that reason.

---

## 1. The billing guard, before any count (§3, §6 step 5)

| | |
|---|---:|
| calls, this run | **80** (2 dry + 39 R0 + 39 R1) |
| calls, cumulative incl. the synchronous phase's billed 49 | **129** (abort above 175) |
| recorded spend, this run | **$1.420661** |
| recorded spend, cumulative | **$2.449977** (ceiling $12.00) |
| planning figure in §8.3, for comparison | $3.31 for three arms; R2 did not fire |

| §3 assertion | R0 | R1 |
|---|---|---|
| arm cost > 0 | **yes** | **yes** |
| per-request cost > 0 (need ≥ 37 of 39) | **39 of 39** | **39 of 39** |
| most expensive request < $0.50 | **$0.0160** | **$0.0899** |
| cumulative under the $12.00 ceiling | **yes** | **yes** |
| non-verdict results | **0** | **0** |

Batches ended with `succeeded=39` and zero errored, expired or canceled on both
arms. Counts below were read only after this table.

🔴 **A bookkeeping defect found and closed before this run.** The runner recorded
calls and spend only on the success path, so an abort between `batches.create()`
and the ledger write — the 24h poll guard, the join guard, a crash — left billed
calls unrecorded and the next run's §8.2 check reading a count lower than the one
already billed. A guard that reads low reports headroom that is not there. The
ledger now writes the call count at submit time and settles the spend against the
same batch id, with an unsettled phase reported loudly at startup. This changes no
threshold in §8.2 or §8.3; it makes the existing guard read its true input.

## 2. Q0 and Q0b — the controls

| | prediction | measured | |
|---|---|---:|---|
| **Q0** `max_tokens` | `\|N_R0 − 19\| ≤ 5` | **\|21 − 19\| = 2** | **pass** |
| **Q0b** endpoint | `\|N_R0batch − N_R0sync\| ≤ 5` | **\|21 − 21\| = 0** | **pass** |

Q0b is the stronger of the two results. §8.3 added the batch endpoint as a fourth
difference between arm A and R1, and the endpoint moved the count by **exactly
zero**. R1 is therefore read against R0-batch without the endpoint sitting between
them.

## 3. Q1 — the test

| | |
|---|---:|
| **N_R0batch** (haiku 4.5, baseline) | **21** of 39 |
| **N_R1** (Opus 5.5, adaptive thinking) | **0** of 39 |

`N_R1 = 0` falls in the **≤ 4** band. Per §2.2 that reads as:

> **(i) accounts for the 19.** A competent reader does reproduce the labels from
> the written line. The "written line ≠ labeller's standard" reading is
> **weakened**, and arm A's 19 must not be cited as evidence about the line.

**The disagreement is one-directional.** The two arms agree on 18 of 39. All 21
disagreements are R0-positive / R1-negative; **none** go the other way. R1's
positive set is empty and therefore a subset of R0's — the strong reader is
strictly stricter here, not differently wrong.

## 4. Q2 — R2 did not fire

The trigger fixed in §2.3 is `N_R1 ≥ 5`. `N_R1 = 0`, so **R2 was not called**, and
the $2.208 it would have cost was not spent. This is the sequential design working
as pre-registered, not a budget decision taken after seeing a number.

🔴 **What that forgoes:** §2.3's strongest available evidence — *two independent
strong readers both diverging from the labeller* — was reachable only on the
`N_R1 ≥ 10` branch. It is not available, and was never going to be on this branch.

## 5. Q3, Q4, Q5

**Q3 — hallucinated evidence: 0 genuine, both arms.** Checked by the corrected
instrument only (§2.4), with every candidate hand-read.

| arm | positives | fragments checked | flagged absent | genuine after hand-read |
|---|---:|---:|---:|---:|
| R0 | 21 | 45 | 1 | **0** |
| R1 | 0 | 0 | 0 | **0** |

The single R0 candidate was a method name written with empty parentheses where the
view carries the same method with its argument, twice; the surrounding sentence
names it as a method rather than quoting a line. A notation form, not an absent
quote. Neither arm is voided.

🔴 The runner's own `evidence_in_view` field reported **0 of 39** in view on both
arms. That is the whole-string substring test §2.4 already recorded as broken — it
asks whether the entire multi-sentence evidence is a substring of the view, which
no narrative answer can satisfy. **It is not a Q3 result and is not reported as
one.** The instrument was pointed at this run's records with its extraction and
comparison untouched; run with its defaults it reproduces the definition A/B output
unchanged.

**Q4 — parse failures: 0 of 39 on both arms**, against a limit of ≤ 2. §2.5 put the
expectation on the record that the raised `max_tokens` cap would remove arm B's
cause of 3. It did. All 78 responses stopped at `end_turn`.

**Q5 — mechanism, descriptive.** R1's evidence field, in paraphrase: on the traces
where the two arms split, R1 names the same observable conduct the baseline names —
an answer submitted without the lookup that would support it, a tool called in
place of the intended one, a patch whose referents were never read — and then
**separates that conduct from deviation explicitly**, in the terms §13.2 of the
parent pre-registration uses: the work still aimed at the stated objective, so a
failed or unverified attempt is a failure and not a deviation. The baseline stops
at the conduct. Confidence on R1 spans 0.6–1.0 (median 0.85) rather than sitting at
a constant, median evidence length 355 characters, no empty evidence fields.

## 6. What this licenses, and what it does not

**Licensed:**

- Arm A's **19 is a reader artefact**, and §2.2's prohibition now applies: it is
  not evidence about the written line.
- Reading **(ii)** — *the written line diverges from its author's labels* — is
  **weakened** for FM-2.3. Taken with the definition A/B's `N_B − N_A = 1`, two
  independent routes now point the same way: the line is not the problem.

**Not licensed:**

- **Nothing about FM-2.3's detectability.** P2 stands at **0–1 of 39**. The axis
  remains stopped before a rule was written, and no `src/` change is authorised by
  this document or taken by it.
- **Nothing about our line versus MAST's text.** That is the definition A/B's Q2,
  answered separately.
- **Nothing about the other three stalled axes.** This run removes one specific
  suspicion — that the labeller's written line is narrower than the labeller's own
  standard — for **this axis only**. FM-1.1, FM-1.5 and FM-2.2 were not measured
  here.
- **`N_R1 = 0` sits at the far edge of its band, and the band does not
  distinguish 0 from 4.** What supports the reading is §5's mechanism rather than
  the margin: the reader articulates the exclusion the definition requires. A total
  zero on a 39-trace sample with one model and one prompt is not a precision
  figure.

## 7. 🔴 One consequence beyond this pre-registration

`DEFAULT_JUDGE_MODEL = "claude-haiku-4-5"` is frozen by prereg §3 and is the reader
used by the **verification axis** (`verification_axis.py:120`), which is live on
paid projects. On FM-2.3's definition that model returned 21 of 39 where Opus 5.5
returned 0.

**This is not a finding about FM-3.2.** FM-3.2's own precision was measured on its
own question and its own 40 hand-labelled sessions (0.9286 without the request in
the view, 1.0000 with it). Reading this run as evidence about that axis would be
comparing a measurement on one target to a claim about another.

What it does say is narrower and forward-looking: **a definition whose content is
carried by exclusion clauses should not be assumed to survive the frozen default
reader.** FM-2.3's line is of that shape — most of its work is done by what it
excludes. Any future axis of that shape needs its reader checked, not assumed, and
this run is the cheapest available way to check one.
